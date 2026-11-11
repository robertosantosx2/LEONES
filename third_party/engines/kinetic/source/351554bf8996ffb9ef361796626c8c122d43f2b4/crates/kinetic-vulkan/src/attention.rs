use std::ops::Range;
use std::rc::Rc;

use crate::batch::{Batch, BATCH_HEADER};
use crate::commands::Commands;
use crate::device::Device;
use crate::error::{Error, Result};
use crate::gemv::GemvInput;
use crate::kernels::Kernels;
use crate::memory::DeviceBuffer;

/// How an attention layer gates its output.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AttentionGate {
    None,
    /// Each query head is followed by `head_dim` gate values whose sigmoid
    /// multiplies the head's output value by value.
    PerValue,
    /// After the values come one gate value per head, whose sigmoid
    /// multiplies the head's output.
    PerHead,
}

/// The shape of one attention layer.
#[derive(Clone, Debug)]
pub struct AttentionShape {
    pub n_head: usize,
    pub n_head_kv: usize,
    /// 64, 128 or 256.
    pub head_dim: usize,
    /// Leading values of each head that rotate.
    pub rope_dims: usize,
    /// Whether rotary pairs are adjacent values rather than `i` and
    /// `i + rope_dims / 2`.
    pub rope_adjacent: bool,
    /// Whether the query and key norms follow the rotation.
    pub norm_after_rope: bool,
    pub gate: AttentionGate,
    /// Past positions a token sees, its own included, when not all.
    pub window: Option<usize>,
    /// Multiplies query-key scores.
    pub scale: f32,
    pub eps: f32,
}

impl AttentionShape {
    /// Values of one query head, gate included.
    pub fn q_head_len(&self) -> usize {
        match self.gate {
            AttentionGate::PerValue => 2 * self.head_dim,
            _ => self.head_dim,
        }
    }

    /// Values of keys, or of values, per token.
    pub fn kv_dim(&self) -> usize {
        self.n_head_kv * self.head_dim
    }

    /// Values per token row of the projections attention reads: every
    /// query head, then every key head, then every value head, then any
    /// per-head gates.
    pub fn qkv_len(&self) -> usize {
        self.gate_at()
            + if self.gate == AttentionGate::PerHead {
                self.n_head
            } else {
                0
            }
    }

    /// Where the per-head gates start in a token row.
    pub fn gate_at(&self) -> usize {
        self.n_head * self.q_head_len() + 2 * self.kv_dim()
    }

    fn check(&self) -> Result<()> {
        let fits = matches!(self.head_dim, 64 | 128 | 256)
            && self.n_head_kv > 0
            && self.n_head.is_multiple_of(self.n_head_kv)
            && self.rope_dims.is_multiple_of(2)
            && self.rope_dims <= self.head_dim
            && self.window.is_none_or(|w| w > 0);
        if fits {
            Ok(())
        } else {
            Err(Error::Shape(format!("attention of shape {self:?}")))
        }
    }
}

/// Keys and values of one attention layer, as f16: every position, or for
/// a window the last ones in a ring with room for a batch more, so a pass
/// and a rollback never overwrite a position still seen.
pub struct KvCache {
    k: DeviceBuffer<u32>,
    v: DeviceBuffer<u32>,
    positions: usize,
    rows: usize,
    slots: usize,
}

impl KvCache {
    /// A cache for `positions` positions run in passes of up to `rows`.
    pub fn new(
        device: &Rc<Device>,
        shape: &AttentionShape,
        positions: usize,
        rows: usize,
    ) -> Result<KvCache> {
        shape.check()?;
        let slots = shape
            .window
            .map_or(positions, |w| (w + rows).min(positions))
            .max(1);
        let words = slots * shape.kv_dim() / 2;
        Ok(KvCache {
            k: DeviceBuffer::new(device, words)?,
            v: DeviceBuffer::new(device, words)?,
            positions,
            rows,
            slots,
        })
    }

    pub fn positions(&self) -> usize {
        self.positions
    }

    /// Positions stored at once.
    pub fn slots(&self) -> usize {
        self.slots
    }

    /// The keys and values of slots `slots`, as f16 bits.
    pub fn save(&self, slots: Range<usize>) -> Result<(Vec<u16>, Vec<u16>)> {
        let row = self.k.len() / self.slots;
        let read = |b: &DeviceBuffer<u32>| -> Result<Vec<u16>> {
            let mut words = vec![0; slots.len() * row];
            b.copy_range_to(slots.start * row, &mut words)?;
            Ok(words
                .iter()
                .flat_map(|w| [*w as u16, (w >> 16) as u16])
                .collect())
        };
        Ok((read(&self.k)?, read(&self.v)?))
    }

    /// Writes keys and values as [`KvCache::save`] gives them from slot `at`.
    pub fn load(&mut self, at: usize, k: &[u16], v: &[u16]) -> Result<()> {
        let row = self.k.len() / self.slots;
        let words = |x: &[u16]| -> Vec<u32> {
            x.chunks_exact(2)
                .map(|p| u32::from(p[0]) | (u32::from(p[1]) << 16))
                .collect()
        };
        self.k.copy_range_from(at * row, &words(k))?;
        self.v.copy_range_from(at * row, &words(v))
    }

    /// Device bytes held.
    pub fn size_bytes(&self) -> usize {
        8 * self.k.len()
    }
}

/// Weights that ready queries and keys, inside one buffer: per-head norms
/// of `head_dim` values and a bias of one value per projected value, each
/// at an element offset.
pub struct QkvConsts<'a> {
    pub data: &'a DeviceBuffer<f32>,
    pub q_norm: Option<usize>,
    pub k_norm: Option<usize>,
    pub bias: Option<usize>,
}

impl Kernels {
    /// Records attention for every token of the batch. `qkv` holds each
    /// token's projections as [`AttentionShape::qkv_len`] says; their
    /// queries and keys are readied in place, keys and values stored in
    /// `cache` at the tokens' positions, and the gated outputs written to
    /// `out`, head after head. The rotary angles of token `t` are words
    /// `2i` and `2i + 1` of row `t` of the batch table that starts at
    /// table word `rope_table`, with rows of `rope_dims` words.
    #[allow(clippy::too_many_arguments)]
    pub fn attention(
        &self,
        batch: &Batch,
        shape: &AttentionShape,
        qkv: &DeviceBuffer<f32>,
        consts: &QkvConsts,
        rope_table: usize,
        cache: &KvCache,
        out: &GemvInput,
        commands: &mut Commands,
    ) -> Result<()> {
        shape.check()?;
        let rows = batch.rows();
        let hd = shape.head_dim;
        let within =
            |at: Option<usize>, len: usize| at.is_none_or(|a| a + len <= consts.data.len());
        let fits = qkv.len() >= rows * shape.qkv_len()
            && cache.positions >= batch.positions()
            && cache.rows >= rows
            && 2 * cache.k.len() == cache.slots * shape.kv_dim()
            && out.width() == shape.n_head * hd
            && out.rows() >= rows
            && rope_table + rows * shape.rope_dims <= batch.table_words()
            && within(consts.q_norm, hd)
            && within(consts.k_norm, hd)
            && within(consts.bias, shape.qkv_len());
        if !fits {
            return Err(Error::Shape(format!(
                "attention of {rows} rows of shape {shape:?}"
            )));
        }
        let flag = |on: bool, bit: u32| if on { bit } else { 0 };
        let flags = flag(shape.rope_adjacent, 1)
            | flag(shape.norm_after_rope, 2)
            | flag(consts.bias.is_some(), 4)
            | flag(consts.q_norm.is_some(), 8)
            | flag(consts.k_norm.is_some(), 16);
        let word = |at: Option<usize>| at.unwrap_or(0) as u32;
        let gate = match shape.gate {
            AttentionGate::None => 0,
            AttentionGate::PerValue => 1,
            AttentionGate::PerHead => 2,
        };
        let attend = match hd {
            64 => &self.attend_64,
            128 => &self.attend_128,
            _ => &self.attend_256,
        };
        let batch_words = batch.device().allocation();
        let [ox, oq, od] = out.outputs();
        // SAFETY: rope.wgsl takes the batch, qkv, consts and both caches at
        // bindings 0..4 and then its shape; attend.wgsl the batch, qkv, both
        // caches and the three output buffers at 0..6 and its shape. Every
        // index they form stays inside the sizes checked above: token rows
        // below the batch's rows, positions below its positions, constants
        // and table words where the offsets say. Workgroups past the pass's
        // tokens return early.
        unsafe {
            commands.dispatch(
                &self.rope,
                &[
                    batch_words,
                    qkv.allocation(),
                    consts.data.allocation(),
                    cache.k.allocation(),
                    cache.v.allocation(),
                ],
                &[
                    shape.n_head as u32,
                    shape.n_head_kv as u32,
                    hd as u32,
                    shape.q_head_len() as u32,
                    shape.qkv_len() as u32,
                    shape.rope_dims as u32,
                    (BATCH_HEADER + rope_table) as u32,
                    flags,
                    shape.eps.to_bits(),
                    word(consts.bias),
                    word(consts.q_norm),
                    word(consts.k_norm),
                    cache.slots as u32,
                ],
                [(shape.n_head + 2 * shape.n_head_kv) as u32, rows as u32, 1],
            );
            commands.dispatch(
                attend,
                &[
                    batch_words,
                    qkv.allocation(),
                    cache.k.allocation(),
                    cache.v.allocation(),
                    ox,
                    oq,
                    od,
                ],
                &[
                    shape.n_head as u32,
                    shape.n_head_kv as u32,
                    shape.qkv_len() as u32,
                    shape.q_head_len() as u32,
                    shape.scale.to_bits(),
                    gate,
                    shape.gate_at() as u32,
                    shape.window.map_or(u32::MAX, |w| w as u32),
                    cache.slots as u32,
                ],
                [shape.n_head as u32, rows as u32, 1],
            );
        }
        Ok(())
    }
}
