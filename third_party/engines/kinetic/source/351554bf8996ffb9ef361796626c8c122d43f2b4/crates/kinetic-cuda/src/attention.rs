use std::ops::Range;
use std::rc::Rc;

use half::f16;

use crate::batch::Batch;
use crate::context::Context;
use crate::error::{Error, Result};
use crate::gemv::{Act, GemvInput, MAX_BATCH};
use crate::kernels::{arg, launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

/// Positions per attention chunk; must match ATTN_CHUNK in attention.cuh.
const CHUNK: usize = 64;
/// Warps per chunk block, each attending its own chunks; must match
/// ATTN_WARPS in attention.cuh.
const CHUNK_WARPS: u32 = 4;
/// Most blocks along the chunks of a token's heads; each warp takes every
/// `CHUNK_WARPS * CHUNK_BLOCKS`th chunk, so a short sequence in a long cache
/// launches few idle blocks.
const CHUNK_BLOCKS: u32 = 128;
const NORM_ROWS_THREADS: u32 = 256;
/// Head elements per combine block; must match ATTN_COMBINE_THREADS.
const COMBINE_THREADS: usize = 64;
/// Queries and threads per block of the flash kernel and f16 padding per
/// shared row; must match attention_flash.cuh, as must the tile sizes below.
const FLASH_QUERIES: u32 = 64;
const FLASH_THREADS: u32 = 128;
const FLASH_PAD: usize = 8;

/// Head sizes the flash kernel handles.
pub(crate) const FLASH_HEADS: [usize; 4] = [64, 128, 256, 512];

/// Value dims of one flash block: heads of 512 split their outputs over two.
fn flash_values(hd: usize) -> usize {
    if hd == 512 {
        256
    } else {
        hd
    }
}

/// Dynamic shared bytes of the flash kernel for heads of `hd`: two tiles
/// each of keys and values, and for heads of 256 the low parts of the
/// queries.
pub(crate) fn flash_shared(hd: usize) -> u32 {
    let keys = if hd >= 256 { 16 } else { 32 };
    let low = if hd == 256 { FLASH_QUERIES as usize } else { 0 };
    let tiles = 2 * keys * (2 * FLASH_PAD + hd + flash_values(hd));
    ((tiles + low * (hd + FLASH_PAD)) * 2) as u32
}

/// The fixed shape of a gated attention layer.
#[derive(Clone, Copy, Debug)]
pub struct AttentionShape {
    pub n_head: usize,
    pub n_head_kv: usize,
    /// 64, 128, 256 or 512.
    pub head_dim: usize,
    /// Leading values of each head that rotate.
    pub rope_dims: usize,
    pub rope_base: f32,
    /// Rotated pairs are neighbours `(2i, 2i + 1)` rather than the NeoX
    /// halves `(i, i + rope_dims / 2)`.
    pub rope_adjacent: bool,
    /// Multiplies the rotated values, as YaRN scaling asks; usually 1.
    pub rope_mscale: f32,
    /// Query and key norms follow the rotation rather than precede it.
    pub norm_after_rope: bool,
    /// Multiplies query-key scores, usually `1 / sqrt(head_dim)`.
    pub scale: f32,
    pub eps: f32,
    /// Keep only this many past positions.
    pub window: Option<usize>,
    /// Each head's queries are followed by as many gate values.
    pub interleaved_gate: bool,
    /// Each value head is RMS-normalized, without weights.
    pub v_norm: bool,
}

impl AttentionShape {
    fn kv_dim(&self) -> usize {
        self.n_head_kv * self.head_dim
    }

    /// Whether a query or key norm of `len` weights spans all heads of a
    /// token rather than one head; `None` if it fits neither.
    fn spans_heads(&self, len: usize, heads: usize) -> Option<bool> {
        if len == self.head_dim {
            Some(false)
        } else if len == heads * self.head_dim && !self.interleaved_gate && !self.norm_after_rope {
            Some(true)
        } else {
            None
        }
    }

    fn q_head_stride(&self) -> usize {
        self.head_dim * if self.interleaved_gate { 2 } else { 1 }
    }

    /// Query values per token, including interleaved gates.
    pub fn q_len(&self) -> usize {
        self.n_head * self.q_head_stride()
    }

    /// Chunks a token may attend over in a cache of `slots` entries.
    fn max_chunks(&self, slots: usize) -> usize {
        match self.window {
            Some(w) => (w - 1) / CHUNK + 2,
            None => slots.div_ceil(CHUNK),
        }
    }

    /// Scratch values [`Kernels::attention`] needs for `tokens` tokens over a
    /// cache of `slots` entries.
    pub fn scratch_len(&self, tokens: usize, slots: usize) -> usize {
        tokens * self.n_head * self.max_chunks(slots) * (self.head_dim + 2)
    }

    fn check(&self) -> Result<()> {
        let ok = matches!(self.head_dim, 64 | 128 | 256 | 512)
            && self.n_head_kv > 0
            && self.n_head.is_multiple_of(self.n_head_kv)
            && self.rope_dims.is_multiple_of(2)
            && self.rope_dims <= self.head_dim
            && self.window != Some(0);
        if ok {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "unsupported attention shape {self:?}"
            )))
        }
    }
}

/// The small per-layer tensors of an attention layer.
#[derive(Clone, Copy)]
pub struct AttentionParams<'a> {
    pub shape: &'a AttentionShape,
    /// RMS norms of each query and key head, or of all query and all key
    /// heads of a token together.
    pub q_norm: Option<&'a DeviceBuffer<f32>>,
    pub k_norm: Option<&'a DeviceBuffer<f32>>,
    /// Per-pair divisors of the rotation frequencies.
    pub rope_factors: Option<&'a DeviceBuffer<f32>>,
    /// Biases added to the query, key and value projections, for layers
    /// without interleaved gates or norms across heads.
    pub q_bias: Option<&'a DeviceBuffer<f32>>,
    pub k_bias: Option<&'a DeviceBuffer<f32>>,
    pub v_bias: Option<&'a DeviceBuffer<f32>>,
    /// Whether the batch's keys and values go into the cache; a layer
    /// attending over keys another layer stored leaves it as it is.
    pub store: bool,
}

/// The projections an attention pass reads and the buffers it writes.
pub struct AttentionIo<'a> {
    /// [`AttentionShape::q_len`] values per token; rotated in place.
    pub q: &'a mut DeviceBuffer<f32>,
    /// Normalized in place by norms that span all heads.
    pub k: &'a mut DeviceBuffer<f32>,
    pub v: &'a DeviceBuffer<f32>,
    /// One gate value per head and token, for layers without interleaved gates.
    pub head_gate: Option<&'a DeviceBuffer<f32>>,
    /// At least [`AttentionShape::scratch_len`] values; batches of more than
    /// [`MAX_BATCH`] tokens use none.
    pub scratch: &'a mut DeviceBuffer<f32>,
    pub out: &'a mut GemvInput,
}

/// How a [`KvCache`] stores keys or values.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum KvType {
    /// f16 values.
    #[default]
    F16,
    /// q8_0: blocks of 32 int8 values times an f16 scale, 34 bytes where f16
    /// takes 64. Attention then reads rounded values, so outputs change.
    Q8_0,
}

/// Values per q8_0 block; head sizes are multiples of it.
const Q8_BLOCK: usize = 32;

enum Store {
    F16(DeviceBuffer<u16>),
    Q8_0 {
        quants: DeviceBuffer<i8>,
        scales: DeviceBuffer<u16>,
    },
}

impl Store {
    fn new(ctx: &Rc<Context>, ty: KvType, len: usize) -> Result<Store> {
        Ok(match ty {
            KvType::F16 => Store::F16(DeviceBuffer::new(ctx, len)?),
            KvType::Q8_0 => Store::Q8_0 {
                quants: DeviceBuffer::new(ctx, len)?,
                scales: DeviceBuffer::new(ctx, len / Q8_BLOCK)?,
            },
        })
    }

    /// The values and the scales, 0 for f16.
    fn ptrs(&self) -> (u64, u64) {
        match self {
            Store::F16(v) => (v.device_ptr(), 0),
            Store::Q8_0 { quants, scales } => (quants.device_ptr(), scales.device_ptr()),
        }
    }

    fn size_bytes(&self) -> usize {
        match self {
            Store::F16(v) => 2 * v.len(),
            Store::Q8_0 { quants, scales } => quants.len() + 2 * scales.len(),
        }
    }

    /// Values `start..start + out.len()`; `start` is a multiple of 32.
    fn save(&self, start: usize, out: &mut [f32]) -> Result<()> {
        match self {
            Store::F16(v) => {
                let mut bits = vec![0; out.len()];
                v.copy_range_to(start, &mut bits)?;
                for (o, b) in out.iter_mut().zip(bits) {
                    *o = f16::from_bits(b).to_f32();
                }
            }
            Store::Q8_0 { quants, scales } => {
                let mut q = vec![0; out.len()];
                let mut d = vec![0; out.len() / Q8_BLOCK];
                quants.copy_range_to(start, &mut q)?;
                scales.copy_range_to(start / Q8_BLOCK, &mut d)?;
                for ((out, q), d) in out.chunks_mut(Q8_BLOCK).zip(q.chunks(Q8_BLOCK)).zip(d) {
                    let d = f16::from_bits(d).to_f32();
                    for (o, &q) in out.iter_mut().zip(q) {
                        *o = d * f32::from(q);
                    }
                }
            }
        }
        Ok(())
    }

    /// Writes `x` at value `start`, a multiple of 32, rounded as the device
    /// rounds; values from [`Store::save`] come back unchanged.
    fn load(&mut self, start: usize, x: &[f32]) -> Result<()> {
        match self {
            Store::F16(v) => {
                let bits: Vec<u16> = x.iter().map(|&x| f16::from_f32(x).to_bits()).collect();
                v.copy_range_from(start, &bits)
            }
            Store::Q8_0 { quants, scales } => {
                let mut q = vec![0; x.len()];
                let mut d = vec![0; x.len() / Q8_BLOCK];
                for ((x, q), d) in x.chunks(Q8_BLOCK).zip(q.chunks_mut(Q8_BLOCK)).zip(&mut d) {
                    let scale = x.iter().fold(0.0f32, |m, v| m.max(v.abs())) / 127.0;
                    for (q, &x) in q.iter_mut().zip(x) {
                        *q = if scale == 0.0 {
                            0
                        } else {
                            (x / scale).round_ties_even() as i8
                        };
                    }
                    *d = f16::from_f32(scale).to_bits();
                }
                quants.copy_range_from(start, &q)?;
                scales.copy_range_from(start / Q8_BLOCK, &d)
            }
        }
    }
}

/// A key-value cache, f16 unless asked otherwise. A full cache stores
/// position `p` at slot `p`; a windowed one is a ring of `slots` entries.
pub struct KvCache {
    k: Store,
    v: Store,
    slots: usize,
    kv_dim: usize,
}

impl KvCache {
    /// An f16 cache of `slots` positions for layers of `shape`. A windowed
    /// cache needs more slots than its window by the most tokens that may be
    /// run and then rolled back, since those overwrite the oldest entries.
    pub fn new(ctx: &Rc<Context>, shape: &AttentionShape, slots: usize) -> Result<KvCache> {
        KvCache::with_types(ctx, shape, slots, KvType::F16, KvType::F16)
    }

    /// [`KvCache::new`] with keys stored as `k` and values as `v`.
    pub fn with_types(
        ctx: &Rc<Context>,
        shape: &AttentionShape,
        slots: usize,
        k: KvType,
        v: KvType,
    ) -> Result<KvCache> {
        shape.check()?;
        if shape.window.is_some_and(|w| slots <= w) || u32::try_from(slots).is_err() {
            return Err(Error::Shape(format!(
                "{slots} cache slots for a window of {:?}",
                shape.window
            )));
        }
        let len = slots * shape.kv_dim();
        Ok(KvCache {
            k: Store::new(ctx, k, len)?,
            v: Store::new(ctx, v, len)?,
            slots,
            kv_dim: shape.kv_dim(),
        })
    }

    pub fn slots(&self) -> usize {
        self.slots
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        self.k.size_bytes() + self.v.size_bytes()
    }

    /// Copies the keys and values of `slots` to the host.
    pub fn save(&self, slots: Range<usize>) -> Result<(Vec<f32>, Vec<f32>)> {
        let len = slots.len() * self.kv_dim;
        let (mut k, mut v) = (vec![0.0; len], vec![0.0; len]);
        self.k.save(slots.start * self.kv_dim, &mut k)?;
        self.v.save(slots.start * self.kv_dim, &mut v)?;
        Ok((k, v))
    }

    /// Writes keys and values from [`KvCache::save`] at slot `at` on.
    pub fn load(&mut self, at: usize, k: &[f32], v: &[f32]) -> Result<()> {
        self.k.load(at * self.kv_dim, k)?;
        self.v.load(at * self.kv_dim, v)
    }
}

#[repr(C)]
struct AttnArgs {
    batch: u64,
    q: u64,
    k: u64,
    v: u64,
    q_norm: u64,
    k_norm: u64,
    rope_factors: u64,
    k_cache: u64,
    v_cache: u64,
    head_gate: u64,
    partial: u64,
    out: Act,
    q_stride: u32,
    q_head_stride: u32,
    n_head: u32,
    n_head_kv: u32,
    head_dim: u32,
    rope_dims: u32,
    rope_base: f32,
    eps: f32,
    scale: f32,
    window: u32,
    slots: u32,
    max_chunks: u32,
    interleaved_gate: u32,
    rope_adjacent: u32,
    norm_after_rope: u32,
    q_norm_rows: u32,
    k_norm_rows: u32,
    rope_mscale: f32,
    q_bias: u64,
    k_bias: u64,
    v_bias: u64,
    k_scale: u64,
    v_scale: u64,
    grid: u64,
    v_norm: u32,
}

fn ptr(buf: Option<&DeviceBuffer<f32>>) -> u64 {
    buf.map_or(0, DeviceBuffer::device_ptr)
}

impl Kernels {
    /// Queues a copy of the keys and values `src` holds for the positions
    /// of `batch` into `dst`, a cache of the same shape and slots. The
    /// positions are read on the device, so a recorded graph replays it.
    pub fn copy_kv(
        &self,
        src: &KvCache,
        dst: &mut KvCache,
        batch: &Batch,
        stream: &Stream,
    ) -> Result<()> {
        if src.slots != dst.slots || src.kv_dim != dst.kv_dim {
            return Err(Error::Shape("copy between caches of other shapes".into()));
        }
        let stores = [&src.k, &src.v, &dst.k, &dst.v];
        if stores.iter().any(|s| !matches!(s, Store::F16(_))) {
            return Err(Error::Shape("layers share only f16 caches".into()));
        }
        let kv_dim = src.kv_dim as u32;
        let (b, slots) = (batch.device_ptr(), src.slots as u32);
        let ptrs = stores.map(|s| s.ptrs().0);
        let mut args = [
            arg(&b),
            arg(&ptrs[0]),
            arg(&ptrs[1]),
            arg(&ptrs[2]),
            arg(&ptrs[3]),
            arg(&kv_dim),
            arg(&slots),
        ];
        let config = LaunchConfig {
            grid: [batch.len() as u32, kv_dim.div_ceil(256), 1],
            block: [256, 1, 1],
            shared_bytes: 0,
        };
        // SAFETY: matches `attn_copy_kv(const unsigned*, const __half*,
        // const __half*, __half*, __half*, unsigned, unsigned)`; both caches
        // hold `slots * kv_dim` values and every slot is taken mod `slots`.
        unsafe { self.attn_copy_kv.launch(config, stream, &mut args) }
    }

    /// Queues gated attention for every token of `batch`: normalizes and
    /// rotates queries and keys, stores keys and values in `cache`, attends
    /// each query over its causal (and windowed) past and writes the gated
    /// result to `io.out`.
    ///
    /// Batches of more than [`MAX_BATCH`] tokens run flash-style on tensor
    /// cores without scratch, as accurate as f32 arithmetic but summed in
    /// another order, so their results differ slightly from smaller batches.
    /// They need [`Kernels::large_batches`]. A windowed cache must hold the
    /// window and the batch.
    pub fn attention(
        &self,
        params: AttentionParams,
        io: AttentionIo,
        cache: &mut KvCache,
        batch: &Batch,
        stream: &Stream,
    ) -> Result<()> {
        let s = params.shape;
        s.check()?;
        let n = batch.len();
        let (hd, kv_dim) = (s.head_dim, s.kv_dim());
        let width = s.n_head * hd;
        if s.window.is_none() && batch.pos() + n > cache.slots {
            return Err(Error::Shape(format!(
                "positions up to {} in a cache of {}",
                batch.pos() + n,
                cache.slots
            )));
        }
        let spans = |w: Option<&DeviceBuffer<f32>>, heads| match w {
            Some(w) => s.spans_heads(w.len(), heads),
            None => Some(false),
        };
        let (q_rows, k_rows) = (
            spans(params.q_norm, s.n_head),
            spans(params.k_norm, s.n_head_kv),
        );
        let biased = params.q_bias.is_some() || params.k_bias.is_some() || params.v_bias.is_some();
        let bias_fits = |b: Option<&DeviceBuffer<f32>>, len| b.is_none_or(|b| b.len() == len);
        if cache.kv_dim != kv_dim
            || io.out.width() != width
            || q_rows.is_none()
            || k_rows.is_none()
            || (biased && (s.interleaved_gate || q_rows == Some(true) || k_rows == Some(true)))
            || !bias_fits(params.q_bias, width)
            || !bias_fits(params.k_bias, kv_dim)
            || !bias_fits(params.v_bias, kv_dim)
            || params
                .rope_factors
                .is_some_and(|f| f.len() != s.rope_dims / 2)
            || (s.interleaved_gate && io.head_gate.is_some())
        {
            return Err(Error::Shape(format!(
                "attention buffers do not fit shape {s:?}"
            )));
        }
        io.q.check_holds(n * s.q_len(), "attention queries")?;
        if params.store {
            io.k.check_holds(n * kv_dim, "attention keys")?;
            io.v.check_holds(n * kv_dim, "attention values")?;
        }
        if let Some(g) = io.head_gate {
            g.check_holds(n * s.n_head, "attention head gates")?;
        }
        if let Some(w) = s.window {
            if n + w - 1 > cache.slots {
                return Err(Error::Shape(format!(
                    "{n} tokens in a ring of {} for a window of {w}",
                    cache.slots
                )));
            }
        }
        let flash = n > MAX_BATCH;
        let stored_heads = if params.store { s.n_head_kv as u32 } else { 0 };
        if !flash {
            io.scratch
                .check_holds(s.scratch_len(n, cache.slots), "attention scratch")?;
        }
        io.out.check_rows(n)?;

        let max_chunks = s.max_chunks(cache.slots);
        let ((k_cache, k_scale), (v_cache, v_scale)) = (cache.k.ptrs(), cache.v.ptrs());
        let args = AttnArgs {
            batch: batch.device_ptr(),
            q: io.q.device_ptr(),
            k: io.k.device_ptr(),
            v: io.v.device_ptr(),
            q_norm: ptr(params.q_norm),
            k_norm: ptr(params.k_norm),
            rope_factors: ptr(params.rope_factors),
            k_cache,
            v_cache,
            head_gate: ptr(io.head_gate),
            partial: io.scratch.device_ptr(),
            out: io.out.act(),
            q_stride: s.q_len() as u32,
            q_head_stride: s.q_head_stride() as u32,
            n_head: s.n_head as u32,
            n_head_kv: s.n_head_kv as u32,
            head_dim: hd as u32,
            rope_dims: s.rope_dims as u32,
            rope_base: s.rope_base,
            eps: s.eps,
            scale: s.scale,
            window: s.window.unwrap_or(0) as u32,
            slots: cache.slots as u32,
            max_chunks: max_chunks as u32,
            interleaved_gate: s.interleaved_gate.into(),
            rope_adjacent: s.rope_adjacent.into(),
            norm_after_rope: s.norm_after_rope.into(),
            q_norm_rows: q_rows.is_some_and(|r| r).into(),
            k_norm_rows: k_rows.is_some_and(|r| r).into(),
            rope_mscale: s.rope_mscale,
            q_bias: ptr(params.q_bias),
            k_bias: ptr(params.k_bias),
            v_bias: ptr(params.v_bias),
            k_scale,
            v_scale,
            grid: batch.grid_ptr(),
            v_norm: s.v_norm.into(),
        };
        let (n, heads) = (n as u32, s.n_head as u32);
        let grid = |grid: [u32; 3], threads: u32| LaunchConfig {
            grid,
            block: [threads, 1, 1],
            shared_bytes: 0,
        };
        // SAFETY: the kernels take `AttnArgs` (and the flash kernel the batch
        // size). Every buffer was checked to hold what `n` tokens of this
        // shape touch; cache slots stay below `slots` (full caches were
        // checked above, rings wrap and hold the window and the batch), and
        // chunk partials stay below `max_chunks` per token and head.
        unsafe {
            if args.q_norm_rows != 0 || args.k_norm_rows != 0 {
                launch_struct(
                    &self.attn_norm_rows,
                    grid([n, 2, 1], NORM_ROWS_THREADS),
                    stream,
                    &args,
                )?;
            }
            launch_struct(
                &self.attn_prepare,
                grid([n, heads + stored_heads, 1], hd as u32),
                stream,
                &args,
            )?;
            if flash {
                let config = LaunchConfig {
                    grid: [
                        n.div_ceil(FLASH_QUERIES),
                        heads,
                        (hd / flash_values(hd)) as u32,
                    ],
                    block: [FLASH_THREADS, 1, 1],
                    shared_bytes: flash_shared(hd),
                };
                let flash = self.attn_flash.as_ref().ok_or_else(|| {
                    Error::Shape(format!("{n} tokens in one pass need the flash kernel"))
                })?;
                flash.launch(config, stream, &mut [arg(&args), arg(&n)])?;
                return io.out.quantize(self, n as usize, stream);
            }
            // perf: two query heads of a KV group per block measured best,
            // ~15% over one at 32k positions on an RTX 3060 Laptop
            let pair = (s.n_head / s.n_head_kv).is_multiple_of(2);
            let chunks = (max_chunks as u32).div_ceil(CHUNK_WARPS).min(CHUNK_BLOCKS);
            launch_struct(
                &self.attn_chunk[usize::from(pair)],
                grid(
                    [n * heads / (1 + u32::from(pair)), chunks, 1],
                    32 * CHUNK_WARPS,
                ),
                stream,
                &args,
            )?;
            launch_struct(
                &self.attn_combine,
                grid(
                    [n * heads, (hd / COMBINE_THREADS) as u32, 1],
                    COMBINE_THREADS as u32,
                ),
                stream,
                &args,
            )
        }
    }
}
