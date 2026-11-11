use std::rc::Rc;

use crate::batch::Batch;
use crate::context::Context;
use crate::error::{Error, Result};
use crate::gemv::{Act, GemvInput, MAX_BATCH};
use crate::kernels::{launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

/// State rows per `delta_rule` block; must match the kernel.
const RULE_ROWS: usize = 16;
const RULE_THREADS: u32 = 128;
/// The only key head size the recurrence kernel handles: four values per lane.
const HEAD_K_DIM: usize = 128;
/// Tokens per chunk of the large-batch recurrence; must match DCHUNK in
/// delta_chunk.cuh, which also needs value heads of HEAD_K_DIM.
const CHUNK: usize = 32;
/// State rows and threads per block of the chunk scan; must match
/// delta_scan.cuh.
const SCAN_ROWS: usize = 32;
const SCAN_THREADS: usize = 64;
const RING_THREADS: usize = 256;

/// The fixed shape of a gated delta-rule layer.
#[derive(Clone, Copy, Debug)]
pub struct DeltaShape {
    pub n_k_heads: usize,
    pub n_v_heads: usize,
    /// 128.
    pub head_k_dim: usize,
    /// A multiple of 32.
    pub head_v_dim: usize,
    pub conv_taps: usize,
    pub eps: f32,
}

impl DeltaShape {
    fn key_dim(&self) -> usize {
        self.n_k_heads * self.head_k_dim
    }

    pub fn value_dim(&self) -> usize {
        self.n_v_heads * self.head_v_dim
    }

    /// Convolution channels: queries, keys and values.
    pub fn channels(&self) -> usize {
        2 * self.key_dim() + self.value_dim()
    }

    /// Scratch values [`Kernels::delta_net`] needs for a batch of `tokens`:
    /// the recurrence output, and for batches larger than [`MAX_BATCH`] the
    /// convolved channels and the per-chunk products.
    pub fn scratch_len(&self, tokens: usize) -> usize {
        if tokens <= MAX_BATCH {
            return tokens * self.value_dim();
        }
        let per_head = self.head_k_dim + self.head_v_dim + CHUNK + 1;
        tokens * (self.channels() + self.n_v_heads * per_head)
    }

    fn state_len(&self) -> usize {
        self.n_v_heads * self.head_v_dim * self.head_k_dim
    }

    fn journal_stride(&self) -> usize {
        self.channels() + 2 * self.n_v_heads
    }

    fn check(&self) -> Result<()> {
        let ok = self.head_k_dim == HEAD_K_DIM
            && self.head_v_dim.is_multiple_of(RULE_ROWS)
            && self.head_v_dim.is_multiple_of(32)
            && self.head_v_dim <= 1024
            && self.n_k_heads > 0
            && self.n_v_heads.is_multiple_of(self.n_k_heads)
            && self.value_dim().is_multiple_of(self.head_k_dim)
            && 2 * self.n_v_heads <= self.head_k_dim
            && self.conv_taps > 0;
        if ok {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "unsupported delta-rule shape {self:?}"
            )))
        }
    }
}

/// The small per-layer tensors of a delta-rule layer.
#[derive(Clone, Copy)]
pub struct DeltaParams<'a> {
    pub shape: &'a DeltaShape,
    /// `conv_taps` weights per channel, oldest input first.
    pub conv: &'a DeviceBuffer<f32>,
    pub dt_bias: &'a DeviceBuffer<f32>,
    /// `-exp(A_log)` per value head.
    pub a: &'a DeviceBuffer<f32>,
    /// RMS norm of each value head's output.
    pub norm: &'a DeviceBuffer<f32>,
}

/// The projections a pass reads and the buffers it writes.
pub struct DeltaIo<'a> {
    pub qkv: &'a DeviceBuffer<f32>,
    pub z: &'a DeviceBuffer<f32>,
    pub alpha: &'a DeviceBuffer<f32>,
    pub beta: &'a DeviceBuffer<f32>,
    /// At least [`DeltaShape::scratch_len`] values.
    pub scratch: &'a mut DeviceBuffer<f32>,
    pub out: &'a mut GemvInput,
}

/// How a pass treats the recurrent state.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Flow {
    /// Advance the state; nothing can be undone.
    Commit,
    /// Leave the state as it was at the checkpoint, keep the advanced one
    /// aside and record the inputs from journal row `first`, the number of
    /// tokens run since the checkpoint, so that
    /// [`Kernels::delta_replay`] can advance the state by any prefix.
    Record { first: usize },
}

/// The convolution window, the per-head recurrent state and a journal of
/// the recurrence inputs since the last checkpoint.
pub struct DeltaState {
    ring: DeviceBuffer<f32>,
    journal: DeviceBuffer<f32>,
    state: DeviceBuffer<f32>,
    spare: DeviceBuffer<f32>,
    ring_len: usize,
    max_tokens: usize,
}

impl DeltaState {
    /// A zero state that records up to `max_tokens` tokens between a
    /// checkpoint and its rollback, and runs up to that many per pass.
    pub fn new(ctx: &Rc<Context>, shape: &DeltaShape, max_tokens: usize) -> Result<DeltaState> {
        shape.check()?;
        let ring_len = shape.conv_taps - 1 + max_tokens;
        let mut ring = DeviceBuffer::new(ctx, ring_len * shape.channels())?;
        let mut state = DeviceBuffer::new(ctx, shape.state_len())?;
        ring.zero()?;
        state.zero()?;
        Ok(DeltaState {
            ring,
            journal: DeviceBuffer::new(ctx, max_tokens * shape.journal_stride())?,
            state,
            spare: DeviceBuffer::new(ctx, shape.state_len())?,
            ring_len,
            max_tokens,
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

    /// Replaces the ring and the state with a copy from [`DeltaState::save`].
    pub fn load(&mut self, host: &HostState) -> Result<()> {
        check_rows(host, self.ring_len)?;
        self.ring.copy_from(&host.ring)?;
        self.state.copy_from(&host.state)
    }
}

/// Fails unless `host` has a ring of `rows` rows.
pub(crate) fn check_rows(host: &HostState, rows: usize) -> Result<()> {
    if host.ring_rows == rows {
        Ok(())
    } else {
        Err(Error::Shape(format!(
            "a ring of {} rows into one of {rows}",
            host.ring_rows
        )))
    }
}

/// A host copy of a recurrent layer's state: the ring of recent convolution
/// inputs, whose row `pos % ring_rows` holds the input at position `pos`,
/// and the per-head state, empty for a short convolution.
#[derive(Clone, Debug, Default)]
pub struct HostState {
    pub ring: Vec<f32>,
    pub ring_rows: usize,
    pub state: Vec<f32>,
}

#[repr(C)]
struct DeltaArgs {
    batch: u64,
    qkv: u64,
    alpha: u64,
    beta: u64,
    conv: u64,
    ring: u64,
    journal: u64,
    dt_bias: u64,
    a: u64,
    s_in: u64,
    s_out: u64,
    out: u64,
    z: u64,
    norm: u64,
    gated: Act,
    n: u32,
    first: u32,
    channels: u32,
    taps: u32,
    ring_len: u32,
    n_k_heads: u32,
    n_v_heads: u32,
    head_k_dim: u32,
    head_v_dim: u32,
    eps: f32,
    q_scale: f32,
}

impl DeltaArgs {
    fn new(p: &DeltaParams, state: &DeltaState, n: usize, first: usize) -> DeltaArgs {
        let s = p.shape;
        DeltaArgs {
            batch: 0,
            qkv: 0,
            alpha: 0,
            beta: 0,
            conv: p.conv.device_ptr(),
            ring: state.ring.device_ptr(),
            journal: state.journal.device_ptr(),
            dt_bias: p.dt_bias.device_ptr(),
            a: p.a.device_ptr(),
            s_in: state.state.device_ptr(),
            s_out: state.state.device_ptr(),
            out: 0,
            z: 0,
            norm: p.norm.device_ptr(),
            gated: Act::NULL,
            n: n as u32,
            first: first as u32,
            channels: s.channels() as u32,
            taps: s.conv_taps as u32,
            ring_len: state.ring_len as u32,
            n_k_heads: s.n_k_heads as u32,
            n_v_heads: s.n_v_heads as u32,
            head_k_dim: s.head_k_dim as u32,
            head_v_dim: s.head_v_dim as u32,
            eps: s.eps,
            q_scale: 1.0 / (s.head_k_dim as f32).sqrt(),
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

fn check_params(p: &DeltaParams, state: &DeltaState) -> Result<()> {
    let s = p.shape;
    s.check()?;
    let ok = p.conv.len() == s.channels() * s.conv_taps
        && p.dt_bias.len() == s.n_v_heads
        && p.a.len() == s.n_v_heads
        && p.norm.len() == s.head_v_dim
        && state.state.len() == s.state_len()
        && state.ring.len() == state.ring_len * s.channels()
        && state.journal.len() == state.max_tokens * s.journal_stride();
    if ok {
        Ok(())
    } else {
        Err(Error::Shape(format!(
            "delta-rule tensors or state do not fit {s:?}"
        )))
    }
}

impl Kernels {
    /// Queues a delta-rule pass over every token of `batch`: convolution and
    /// norms, the recurrence as `flow` says, then the gated output norm into
    /// `io.out`.
    ///
    /// Batches of more than [`MAX_BATCH`] tokens must commit and have value
    /// heads of 128; they run the recurrence in chunks on tensor cores, as
    /// accurate as f32 arithmetic but in another order, so their results
    /// differ slightly from smaller batches.
    pub fn delta_net(
        &self,
        params: DeltaParams,
        io: DeltaIo,
        state: &mut DeltaState,
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
        io.qkv
            .check_holds(n * s.channels(), "delta-rule projections")?;
        io.z.check_holds(n * s.value_dim(), "delta-rule gate")?;
        io.alpha.check_holds(n * s.n_v_heads, "delta-rule alpha")?;
        io.beta.check_holds(n * s.n_v_heads, "delta-rule beta")?;
        io.scratch
            .check_holds(s.scratch_len(n), "delta-rule scratch")?;
        if io.out.width() != s.value_dim() {
            return Err(Error::Shape(format!(
                "delta-rule output of {} into inputs of {}",
                s.value_dim(),
                io.out.width()
            )));
        }
        io.out.check_rows(n)?;
        if n > MAX_BATCH {
            return self.delta_batch(params, io, state, flow, batch, stream);
        }
        if first + n > state.max_tokens {
            return Err(Error::Shape(format!(
                "{} tokens since the checkpoint where the journal holds {}",
                first + n,
                state.max_tokens
            )));
        }

        let mut args = DeltaArgs::new(&params, state, n, first);
        args.batch = batch.device_ptr();
        args.qkv = io.qkv.device_ptr();
        args.alpha = io.alpha.device_ptr();
        args.beta = io.beta.device_ptr();
        args.out = io.scratch.device_ptr();
        args.z = io.z.device_ptr();
        args.gated = io.out.act();
        if let Flow::Record { first } = flow {
            if first > 0 {
                args.s_in = state.spare.device_ptr();
            }
            args.s_out = state.spare.device_ptr();
        }
        // SAFETY: the kernels take `DeltaArgs`. Every buffer was checked to
        // hold what `n` tokens of this shape touch; journal rows stay below
        // `max_tokens` and ring rows wrap below `ring_len`.
        unsafe {
            launch_struct(
                &self.delta_conv,
                config([s.channels() / s.head_k_dim, 1], s.head_k_dim),
                stream,
                &args,
            )?;
            launch_struct(
                &self.delta_rule,
                config(
                    [s.n_v_heads, s.head_v_dim / RULE_ROWS],
                    RULE_THREADS as usize,
                ),
                stream,
                &args,
            )?;
            launch_struct(
                &self.delta_gated_norm,
                config([n, s.n_v_heads], s.head_v_dim),
                stream,
                &args,
            )
        }
    }

    /// [`Kernels::delta_net`] for more than [`MAX_BATCH`] tokens, whose
    /// buffers the caller checked: the convolution per token and the
    /// recurrence in chunks, committed.
    fn delta_batch(
        &self,
        params: DeltaParams,
        io: DeltaIo,
        state: &mut DeltaState,
        flow: Flow,
        batch: &Batch,
        stream: &Stream,
    ) -> Result<()> {
        let s = params.shape;
        let n = batch.len();
        if flow != Flow::Commit || s.head_v_dim != HEAD_K_DIM {
            return Err(Error::Shape(format!(
                "{n} tokens of {s:?} in one pass need committed value heads of {HEAD_K_DIM}"
            )));
        }

        let mut args = DeltaArgs::new(&params, state, n, 0);
        args.batch = batch.device_ptr();
        args.qkv = io.qkv.device_ptr();
        args.alpha = io.alpha.device_ptr();
        args.beta = io.beta.device_ptr();
        args.journal = io.scratch.device_ptr();
        args.z = io.z.device_ptr();
        // The gated norm reads each recurrence output before it writes the
        // same element, so the output's own f32 values can hold them.
        args.gated = io.out.act();
        args.out = args.gated.x;
        let channels = s.channels();
        // SAFETY: the kernels take `DeltaArgs`. Every buffer was checked to
        // hold what `n` tokens of this shape touch, the scratch the layout of
        // delta_chunk.cuh for `n` tokens; ring rows wrap below `ring_len`.
        unsafe {
            launch_struct(
                &self.delta_conv_batch,
                config([channels / s.head_k_dim, n], s.head_k_dim),
                stream,
                &args,
            )?;
            launch_struct(
                &self.delta_ring_store,
                config([channels.div_ceil(RING_THREADS), 1], RING_THREADS),
                stream,
                &args,
            )?;
            launch_struct(
                &self.delta_chunk_prep,
                config([s.n_v_heads, n.div_ceil(CHUNK)], RULE_THREADS as usize),
                stream,
                &args,
            )?;
            launch_struct(
                &self.delta_chunk_scan,
                config([s.n_v_heads, s.head_v_dim / SCAN_ROWS], SCAN_THREADS),
                stream,
                &args,
            )?;
            launch_struct(
                &self.delta_gated_norm,
                config([n, s.n_v_heads], s.head_v_dim),
                stream,
                &args,
            )
        }
    }

    /// Advances the state saved at the checkpoint by the first `keep`
    /// recorded tokens, with the same arithmetic as the recorded pass, so it
    /// is bit-identical to having run only those tokens.
    pub fn delta_replay(
        &self,
        params: DeltaParams,
        state: &mut DeltaState,
        keep: usize,
        stream: &Stream,
    ) -> Result<()> {
        check_params(&params, state)?;
        if keep == 0 {
            return Ok(());
        }
        if keep > state.max_tokens {
            return Err(Error::Shape(format!(
                "replay of {keep} tokens from a journal of {}",
                state.max_tokens
            )));
        }
        let s = params.shape;
        let args = DeltaArgs::new(&params, state, keep, 0);
        // SAFETY: as in `delta_net`; with no output buffer the kernel only
        // reads `keep` journal rows and rewrites the state in place.
        unsafe {
            launch_struct(
                &self.delta_rule,
                config(
                    [s.n_v_heads, s.head_v_dim / RULE_ROWS],
                    RULE_THREADS as usize,
                ),
                stream,
                &args,
            )
        }
    }
}
