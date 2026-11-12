use std::rc::Rc;

use crate::batch::Batch;
use crate::context::Context;
use crate::delta_net::{check_rows, Flow, HostState};
use crate::error::{Error, Result};
use crate::gemv::{Act, GemvInput, MAX_BATCH};
use crate::kernels::{launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

/// State rows per `ssm_scan` block and threads; must match ssm.cuh.
const SCAN_ROWS: usize = 16;
const SCAN_THREADS: usize = 128;
const CONV_THREADS: usize = 128;
const NORM_THREADS: usize = 256;

/// The fixed shape of a Mamba-2 mixer.
#[derive(Clone, Copy, Debug)]
pub struct SsmShape {
    pub n_head: usize,
    /// A multiple of 16.
    pub head_dim: usize,
    pub n_group: usize,
    /// 64, 128 or 256.
    pub d_state: usize,
    pub conv_taps: usize,
    pub eps: f32,
}

impl SsmShape {
    /// Values of the scan input and output per token.
    pub fn inner(&self) -> usize {
        self.n_head * self.head_dim
    }

    /// Convolution channels: `x`, then `B` and `C` of every group.
    pub fn channels(&self) -> usize {
        self.inner() + 2 * self.n_group * self.d_state
    }

    /// Projected values per token: `z`, the convolution input and a step
    /// size per head.
    pub fn proj_len(&self) -> usize {
        self.inner() + self.channels() + self.n_head
    }

    fn journal_stride(&self) -> usize {
        self.channels() + self.n_head
    }

    /// Scratch values [`Kernels::ssm`] needs for a batch of `tokens`: the
    /// scan output, and for batches larger than [`MAX_BATCH`] their journal.
    pub fn scratch_len(&self, tokens: usize) -> usize {
        let journal = if tokens > MAX_BATCH {
            self.journal_stride()
        } else {
            0
        };
        tokens * (self.inner() + journal)
    }

    fn state_len(&self) -> usize {
        self.inner() * self.d_state
    }

    fn check(&self) -> Result<()> {
        let ok = matches!(self.d_state, 64 | 128 | 256)
            && self.head_dim.is_multiple_of(SCAN_ROWS)
            && self.n_group > 0
            && self.n_head.is_multiple_of(self.n_group)
            && (self.inner() / self.n_group).is_multiple_of(32)
            && self.conv_taps > 0;
        if ok {
            Ok(())
        } else {
            Err(Error::Shape(format!("unsupported Mamba-2 shape {self:?}")))
        }
    }
}

/// The small per-layer tensors of a Mamba-2 mixer.
#[derive(Clone, Copy)]
pub struct SsmParams<'a> {
    pub shape: &'a SsmShape,
    /// `conv_taps` weights per channel, oldest input first.
    pub conv: &'a DeviceBuffer<f32>,
    pub conv_bias: &'a DeviceBuffer<f32>,
    pub dt_bias: &'a DeviceBuffer<f32>,
    /// `-exp(A_log)` per head.
    pub a: &'a DeviceBuffer<f32>,
    /// The skip `D` per head.
    pub d: &'a DeviceBuffer<f32>,
    /// RMS norm of each group of the gated output.
    pub norm: Option<&'a DeviceBuffer<f32>>,
}

/// The convolution window, the per-head state and a journal of the scan
/// inputs since the last checkpoint.
pub struct SsmState {
    ring: DeviceBuffer<f32>,
    journal: DeviceBuffer<f32>,
    state: DeviceBuffer<f32>,
    spare: DeviceBuffer<f32>,
    ring_len: usize,
}

impl SsmState {
    /// A zero state that records up to [`MAX_BATCH`] tokens between a
    /// checkpoint and its rollback.
    pub fn new(ctx: &Rc<Context>, shape: &SsmShape) -> Result<SsmState> {
        shape.check()?;
        let ring_len = shape.conv_taps - 1 + MAX_BATCH;
        let mut ring = DeviceBuffer::new(ctx, ring_len * shape.channels())?;
        let mut state = DeviceBuffer::new(ctx, shape.state_len())?;
        ring.zero()?;
        state.zero()?;
        Ok(SsmState {
            ring,
            journal: DeviceBuffer::new(ctx, MAX_BATCH * shape.journal_stride())?,
            state,
            spare: DeviceBuffer::new(ctx, shape.state_len())?,
            ring_len,
        })
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        4 * (self.ring.len() + self.journal.len() + self.state.len() + self.spare.len())
    }

    /// Queues zeroing the ring and the state, as in a new sequence.
    pub fn clear(&mut self, stream: &Stream) -> Result<()> {
        self.ring.zero_prefix(self.ring.len(), stream)?;
        self.state.zero_prefix(self.state.len(), stream)
    }

    /// Rows of the convolution ring; see [`HostState`].
    pub fn ring_rows(&self) -> usize {
        self.ring_len
    }

    /// Copies the ring and the state to the host.
    pub fn save(&self) -> Result<HostState> {
        Ok(HostState {
            ring: self.ring.to_vec()?,
            ring_rows: self.ring_len,
            state: self.state.to_vec()?,
        })
    }

    /// Replaces the ring and the state with a copy from [`SsmState::save`].
    pub fn load(&mut self, host: &HostState) -> Result<()> {
        check_rows(host, self.ring_len)?;
        self.ring.copy_from(&host.ring)?;
        self.state.copy_from(&host.state)
    }
}

#[repr(C)]
struct SsmArgs {
    batch: u64,
    proj: u64,
    conv: u64,
    conv_bias: u64,
    ring: u64,
    journal: u64,
    dt_bias: u64,
    a: u64,
    d: u64,
    s_in: u64,
    s_out: u64,
    out: u64,
    norm: u64,
    gated: Act,
    n: u32,
    first: u32,
    width: u32,
    channels: u32,
    taps: u32,
    ring_len: u32,
    n_head: u32,
    head_dim: u32,
    n_group: u32,
    d_state: u32,
    eps: f32,
}

impl SsmArgs {
    fn new(p: &SsmParams, state: &SsmState, n: usize, first: usize) -> SsmArgs {
        let s = p.shape;
        SsmArgs {
            batch: 0,
            proj: 0,
            conv: p.conv.device_ptr(),
            conv_bias: p.conv_bias.device_ptr(),
            ring: state.ring.device_ptr(),
            journal: state.journal.device_ptr(),
            dt_bias: p.dt_bias.device_ptr(),
            a: p.a.device_ptr(),
            d: p.d.device_ptr(),
            s_in: state.state.device_ptr(),
            s_out: state.state.device_ptr(),
            out: 0,
            norm: p.norm.map_or(0, DeviceBuffer::device_ptr),
            gated: Act::NULL,
            n: n as u32,
            first: first as u32,
            width: s.proj_len() as u32,
            channels: s.channels() as u32,
            taps: s.conv_taps as u32,
            ring_len: state.ring_len as u32,
            n_head: s.n_head as u32,
            head_dim: s.head_dim as u32,
            n_group: s.n_group as u32,
            d_state: s.d_state as u32,
            eps: s.eps,
        }
    }
}

fn config(grid: [usize; 2], threads: usize) -> LaunchConfig {
    LaunchConfig {
        grid: [grid[0] as u32, grid[1] as u32, 1],
        block: [threads as u32, 1, 1],
        shared_bytes: 0,
    }
}

fn check_params(p: &SsmParams, state: &SsmState) -> Result<()> {
    let s = p.shape;
    s.check()?;
    let ok = p.conv.len() == s.channels() * s.conv_taps
        && p.conv_bias.len() == s.channels()
        && [p.dt_bias, p.a, p.d].iter().all(|v| v.len() == s.n_head)
        && p.norm.is_none_or(|w| w.len() == s.inner())
        && state.state.len() == s.state_len()
        && state.ring.len() == state.ring_len * s.channels()
        && state.journal.len() == MAX_BATCH * s.journal_stride();
    if ok {
        Ok(())
    } else {
        Err(Error::Shape(format!(
            "Mamba-2 tensors or state do not fit {s:?}"
        )))
    }
}

impl Kernels {
    /// Queues a Mamba-2 pass over every token of `batch`, whose projections
    /// `proj` holds: convolution, the scan as `flow` says, then the gated
    /// norm into `out`.
    ///
    /// Batches of more than [`MAX_BATCH`] tokens must commit; they run the
    /// same kernels with the journal in `scratch`, so their results equal
    /// those of smaller batches.
    #[allow(clippy::too_many_arguments)]
    pub fn ssm(
        &self,
        params: SsmParams,
        proj: &DeviceBuffer<f32>,
        scratch: &mut DeviceBuffer<f32>,
        out: &mut GemvInput,
        state: &mut SsmState,
        flow: Flow,
        batch: &Batch,
        stream: &Stream,
    ) -> Result<()> {
        check_params(&params, state)?;
        let s = params.shape;
        let n = batch.len();
        let first = match flow {
            Flow::Commit => 0,
            Flow::Record { first } => first,
        };
        if n > MAX_BATCH && flow != Flow::Commit {
            return Err(Error::Shape(format!("{n} tokens in one pass must commit")));
        }
        if n <= MAX_BATCH && first + n > MAX_BATCH {
            return Err(Error::Shape(format!(
                "{} tokens since the checkpoint where the journal holds {MAX_BATCH}",
                first + n
            )));
        }
        proj.check_holds(n * s.proj_len(), "Mamba-2 projections")?;
        scratch.check_holds(s.scratch_len(n), "Mamba-2 scratch")?;
        if out.width() != s.inner() {
            return Err(Error::Shape(format!(
                "Mamba-2 output of {} into inputs of {}",
                s.inner(),
                out.width()
            )));
        }
        out.check_rows(n)?;

        let mut args = SsmArgs::new(&params, state, n, first);
        args.batch = batch.device_ptr();
        args.proj = proj.device_ptr();
        args.out = scratch.device_ptr();
        args.gated = out.act();
        if n > MAX_BATCH {
            args.journal = scratch.ptr_at(n * s.inner());
        }
        if let Flow::Record { first } = flow {
            if first > 0 {
                args.s_in = state.spare.device_ptr();
            }
            args.s_out = state.spare.device_ptr();
        }
        let channels = s.channels();
        // SAFETY: the kernels take `SsmArgs`. Every buffer was checked to
        // hold what `n` tokens of this shape touch; journal rows stay below
        // `MAX_BATCH` in the state or `n` in the scratch, and ring rows wrap
        // below `ring_len`.
        unsafe {
            launch_struct(
                &self.ssm_conv,
                config([channels.div_ceil(CONV_THREADS), n], CONV_THREADS),
                stream,
                &args,
            )?;
            launch_struct(
                &self.ssm_ring_store,
                config([channels.div_ceil(CONV_THREADS), 1], CONV_THREADS),
                stream,
                &args,
            )?;
            launch_struct(
                &self.ssm_scan,
                config([s.n_head, s.head_dim / SCAN_ROWS], SCAN_THREADS),
                stream,
                &args,
            )?;
            launch_struct(
                &self.ssm_gated_norm,
                config([n, s.n_group], NORM_THREADS),
                stream,
                &args,
            )
        }
    }

    /// Advances the state saved at the checkpoint by the first `keep`
    /// recorded tokens, with the same arithmetic as the recorded pass, so it
    /// is bit-identical to having run only those tokens.
    pub fn ssm_replay(
        &self,
        params: SsmParams,
        state: &mut SsmState,
        keep: usize,
        stream: &Stream,
    ) -> Result<()> {
        check_params(&params, state)?;
        if keep == 0 {
            return Ok(());
        }
        if keep > MAX_BATCH {
            return Err(Error::Shape(format!(
                "replay of {keep} tokens from a journal of {MAX_BATCH}"
            )));
        }
        let s = params.shape;
        let args = SsmArgs::new(&params, state, keep, 0);
        // SAFETY: as in `ssm`; with no output buffer the kernel only reads
        // `keep` journal rows and rewrites the state in place.
        unsafe {
            launch_struct(
                &self.ssm_scan,
                config([s.n_head, s.head_dim / SCAN_ROWS], SCAN_THREADS),
                stream,
                &args,
            )
        }
    }
}
