use std::rc::Rc;

use kinetic_quant::iq::{IQ2XS_GRID, IQ2XXS_GRID, IQ3XXS_GRID, IQ4NL_VALUES};
use kinetic_quant::TensorType;

use crate::context::Context;
use crate::error::{Error, Result};
use crate::kernels::{arg, launch_struct, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

/// Weight types the expert kernels read, in the order of their kernels.
pub const EXPERT_TYPES: [TensorType; 9] = [
    TensorType::IQ2XXS,
    TensorType::IQ2XS,
    TensorType::IQ3XXS,
    TensorType::IQ4XS,
    TensorType::Q2K,
    TensorType::Q3K,
    TensorType::Q4K,
    TensorType::Q5K,
    TensorType::Q6K,
];

/// Kernel names, by index into [`EXPERT_TYPES`].
pub(crate) const MOE_NAMES: [&str; EXPERT_TYPES.len()] = [
    "iq2_xxs", "iq2_xs", "iq3_xxs", "iq4_xs", "q2_k", "q3_k", "q4_k", "q5_k", "q6_k",
];

/// Most assignments of one expert an [`ExpertGroup`] holds.
pub const EXPERT_GROUP: usize = 8;

/// Values per quantization block of expert inputs.
pub const Q8K_BLOCK: usize = 256;

const MOE_WARPS: u32 = 4;
/// Rows each warp of an expert kernel computes.
const MOE_WARP_ROWS: u32 = 4;
const COMBINE_THREADS: u32 = 256;
const QUANTIZE_WARPS: u32 = 4;
const ROUTE_WARPS: u32 = 4;
const ASSIGN_THREADS: u32 = 256;

/// The codebooks of [`EXPERT_TYPES`] on the device, laid out as the kernels
/// expect.
pub struct ExpertTables(DeviceBuffer<u8>);

impl ExpertTables {
    pub fn new(ctx: &Rc<Context>) -> Result<ExpertTables> {
        let mut bytes: Vec<u8> = IQ2XXS_GRID.as_flattened().to_vec();
        bytes.extend(IQ2XS_GRID.as_flattened());
        bytes.extend(IQ3XXS_GRID.as_flattened());
        bytes.extend(IQ4NL_VALUES.map(|v| v as u8));
        Ok(ExpertTables(DeviceBuffer::from_slice(ctx, &bytes)?))
    }
}

/// Expert matrices in slots of one device arena, each slot holding one
/// expert's matrices in their file layout.
#[derive(Clone, Copy)]
pub struct ExpertArena<'a> {
    pub data: &'a DeviceBuffer<u8>,
    pub slot_bytes: usize,
}

/// Up to [`EXPERT_GROUP`] consecutive assignments of the expert in `slot`,
/// stored on the device as four `u32`: slot, first assignment, count and a
/// zero.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExpertGroup {
    pub slot: u32,
    pub first: u32,
    pub count: u32,
}

impl ExpertGroup {
    pub fn words(&self) -> [u32; 4] {
        [self.slot, self.first, self.count, 0]
    }
}

/// Inputs quantized per [`Q8K_BLOCK`] values, as the host quantizes them.
pub struct Q8kRows<'a> {
    pub qs: &'a DeviceBuffer<i8>,
    pub ds: &'a DeviceBuffer<f32>,
}

/// One product per assignment with a matrix of the expert in its slot.
pub struct ExpertProduct<'a> {
    pub ty: TensorType,
    /// [`ExpertGroup`] words; the product runs `n_groups` of them from
    /// group `first_group`, all of their assignments below `assignments`.
    pub groups: &'a DeviceBuffer<u32>,
    pub first_group: usize,
    pub n_groups: usize,
    pub assignments: usize,
    /// The input row of every assignment; `None` gives assignment `a` row `a`.
    pub inputs: Option<&'a DeviceBuffer<u32>>,
    /// Byte offset of the matrix in a slot.
    pub first: usize,
    /// For a gated product, `silu(first x) * second x`, the offset of the
    /// second matrix, of the same type and shape.
    pub second: Option<usize>,
    pub rows: usize,
    pub cols: usize,
}

/// Mixes expert outputs into each token's result; see [`Kernels::moe_combine`].
pub struct ExpertMix<'a> {
    /// Expert outputs, `d` values per row.
    pub experts: &'a DeviceBuffer<f32>,
    /// Per token and pick, the row of `experts` holding its output, and its
    /// weight.
    pub rows: &'a DeviceBuffer<u32>,
    pub weights: &'a DeviceBuffer<f32>,
    pub picks: usize,
    /// Whether the output holds a shared expert's output to start from;
    /// otherwise it starts from zero.
    pub shared: bool,
    /// The logit of the shared expert's gate per token, if it has one.
    pub gates: Option<GateLogits<'a>>,
    pub tokens: usize,
    pub d: usize,
}

/// One value per token, token `t`'s at `first + t * stride`.
#[derive(Clone, Copy)]
pub struct GateLogits<'a> {
    pub values: &'a DeviceBuffer<f32>,
    pub first: usize,
    pub stride: usize,
}

#[repr(C)]
struct MoeParams {
    arena: u64,
    slot_bytes: u64,
    groups: u64,
    inputs: u64,
    xq: u64,
    xd: u64,
    y: u64,
    tables: u64,
    first: u32,
    second: u32,
    rows: u32,
    cols: u32,
}

/// Most experts per layer [`Kernels::moe_route`] chooses from.
pub const ROUTE_MAX_EXPERTS: usize = 1024;

/// Most picks of one batch [`Kernels::moe_assign`] takes.
pub const ASSIGN_MAX_PICKS: usize = 4096;

/// Router logits of a batch: `stride` per token, the first `n_exp` of
/// which are the experts', `picks` of them chosen per token.
pub struct Routing<'a> {
    pub gates: &'a DeviceBuffer<f32>,
    pub tokens: usize,
    pub n_exp: usize,
    pub picks: usize,
    pub stride: usize,
    /// Sigmoid probabilities instead of a softmax.
    pub sigmoid: bool,
    /// Added to each expert's probability to choose it, but not to weigh it.
    pub bias: Option<&'a DeviceBuffer<f32>>,
}

#[repr(C)]
struct RouteParams {
    gates: u64,
    experts: u64,
    weights: u64,
    tokens: u32,
    n_exp: u32,
    k: u32,
    stride: u32,
    sigmoid: u32,
    bias: u64,
}

#[repr(C)]
struct AssignParams {
    experts: u64,
    slots: u64,
    groups: u64,
    inputs: u64,
    rows: u64,
    picks: u32,
    k: u32,
    n_exp: u32,
    max_groups: u32,
}

#[repr(C)]
struct CombineParams {
    experts: u64,
    rows: u64,
    weights: u64,
    picks: u32,
    shared: u32,
    out: u64,
    gates: u64,
    gate_stride: u32,
    d: u32,
}

impl Kernels {
    /// Queues choosing each token's experts: the softmax (or sigmoid) of its
    /// logits, then the `picks` with the largest probability plus bias,
    /// largest first and the lowest index among equals, into `experts`, with
    /// weights their share of the chosen probabilities into `weights`,
    /// `picks` per token.
    pub fn moe_route(
        &self,
        r: &Routing,
        experts: &mut DeviceBuffer<u32>,
        weights: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        if r.n_exp > ROUTE_MAX_EXPERTS || r.picks == 0 || r.picks > r.n_exp || r.n_exp > r.stride {
            return Err(Error::Shape(format!(
                "{} of {} experts from rows of {}",
                r.picks, r.n_exp, r.stride
            )));
        }
        r.gates.check_holds(r.tokens * r.stride, "router logits")?;
        if let Some(b) = r.bias {
            b.check_holds(r.n_exp, "expert bias")?;
        }
        experts.check_holds(r.tokens * r.picks, "picked experts")?;
        weights.check_holds(r.tokens * r.picks, "pick weights")?;
        if r.tokens == 0 {
            return Ok(());
        }
        let params = RouteParams {
            gates: r.gates.device_ptr(),
            experts: experts.device_ptr(),
            weights: weights.device_ptr(),
            tokens: r.tokens as u32,
            n_exp: r.n_exp as u32,
            k: r.picks as u32,
            stride: r.stride as u32,
            sigmoid: u32::from(r.sigmoid),
            bias: r.bias.map_or(0, |b| b.device_ptr()),
        };
        let config =
            LaunchConfig::linear((r.tokens as u32).div_ceil(ROUTE_WARPS), ROUTE_WARPS * 32);
        // SAFETY: matches `RouteParams`; sizes checked above.
        unsafe { launch_struct(&self.moe_route, config, stream, &params) }
    }

    /// Queues giving each of the `picks` picks in `experts`, `k` per token,
    /// an assignment: the picks of each expert together, in pick order, in
    /// [`ExpertGroup`]s of up to [`EXPERT_GROUP`] whose slot `slots` gives
    /// per expert, the rest of `max_groups` groups empty. Writes the input
    /// row of every assignment to `inputs` and the assignment of every pick
    /// to `rows`. Picks of experts not below `n_exp` get no assignment.
    #[allow(clippy::too_many_arguments)]
    pub fn moe_assign(
        &self,
        experts: &DeviceBuffer<u32>,
        picks: usize,
        k: usize,
        slots: &DeviceBuffer<u32>,
        groups: &mut DeviceBuffer<u32>,
        max_groups: usize,
        inputs: &mut DeviceBuffer<u32>,
        rows: &mut DeviceBuffer<u32>,
        stream: &Stream,
    ) -> Result<()> {
        let n_exp = slots.len();
        if picks > ASSIGN_MAX_PICKS
            || n_exp > ROUTE_MAX_EXPERTS
            || k == 0
            || !picks.is_multiple_of(k)
            || max_groups < picks
        {
            return Err(Error::Shape(format!(
                "{picks} picks of {k} per token in {max_groups} groups"
            )));
        }
        experts.check_holds(picks, "picked experts")?;
        groups.check_holds(4 * max_groups, "expert groups")?;
        inputs.check_holds(picks, "expert inputs")?;
        rows.check_holds(picks, "pick assignments")?;
        if picks == 0 {
            return Ok(());
        }
        let params = AssignParams {
            experts: experts.device_ptr(),
            slots: slots.device_ptr(),
            groups: groups.device_ptr(),
            inputs: inputs.device_ptr(),
            rows: rows.device_ptr(),
            picks: picks as u32,
            k: k as u32,
            n_exp: n_exp as u32,
            max_groups: max_groups as u32,
        };
        let config = LaunchConfig {
            grid: [1, 1, 1],
            block: [ASSIGN_THREADS, 1, 1],
            shared_bytes: 4 * (picks + 3 * n_exp) as u32,
        };
        // SAFETY: matches `AssignParams`; sizes checked above, and the picks
        // make at most as many groups as there are picks, no more than
        // `max_groups`.
        unsafe { launch_struct(&self.moe_assign, config, stream, &params) }
    }

    /// Queues quantizing `rows` rows of `cols` values of `x`, `cols` a
    /// multiple of [`Q8K_BLOCK`], into `out`.
    pub fn quantize_q8k(
        &self,
        x: &DeviceBuffer<f32>,
        rows: usize,
        cols: usize,
        qs: &mut DeviceBuffer<i8>,
        ds: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        if !cols.is_multiple_of(Q8K_BLOCK) {
            return Err(Error::Shape(format!(
                "{cols} columns in blocks of {Q8K_BLOCK}"
            )));
        }
        let (n, blocks) = (rows * cols, (rows * cols / Q8K_BLOCK) as u32);
        x.check_holds(n, "quantized input")?;
        qs.check_holds(n, "quantized values")?;
        ds.check_holds(blocks as usize, "quantized scales")?;
        if blocks == 0 {
            return Ok(());
        }
        let (src, q, d) = (x.device_ptr(), qs.device_ptr(), ds.device_ptr());
        let mut args = [arg(&src), arg(&q), arg(&d), arg(&blocks)];
        let config = LaunchConfig::linear(blocks.div_ceil(QUANTIZE_WARPS), QUANTIZE_WARPS * 32);
        // SAFETY: matches `quantize_q8k(const float*, int8_t*, float*,
        // unsigned)`; sizes were checked above.
        unsafe { self.quantize_q8k.launch(config, stream, &mut args) }
    }

    /// Queues `y[a] = W x[input of a]` for every assignment `a`, `W` being a
    /// matrix of the expert its group names. `y` receives one row of `rows`
    /// values per assignment.
    ///
    /// # Safety
    ///
    /// The groups must hold `n_groups` valid [`ExpertGroup`]s covering
    /// assignments below `assignments`, every slot must lie inside `arena`
    /// and hold the product's matrices at its offsets, and every input row
    /// must lie inside `x`.
    pub unsafe fn moe_product(
        &self,
        p: &ExpertProduct,
        arena: ExpertArena,
        tables: &ExpertTables,
        x: &Q8kRows,
        y: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        let index = EXPERT_TYPES
            .iter()
            .position(|&t| t == p.ty)
            .ok_or(Error::Unsupported(p.ty))?;
        if p.n_groups == 0 {
            return Ok(());
        }
        if !p.cols.is_multiple_of(Q8K_BLOCK) {
            return Err(Error::Shape(format!(
                "expert product over {} columns",
                p.cols
            )));
        }
        p.groups
            .check_holds(4 * (p.first_group + p.n_groups), "expert groups")?;
        if let Some(inputs) = p.inputs {
            inputs.check_holds(p.assignments, "expert inputs")?;
        } else {
            x.qs.check_holds(p.assignments * p.cols, "expert inputs")?;
        }
        y.check_holds(p.assignments * p.rows, "expert outputs")?;
        let params = MoeParams {
            arena: arena.data.device_ptr(),
            slot_bytes: arena.slot_bytes as u64,
            groups: p.groups.ptr_at(4 * p.first_group),
            inputs: p.inputs.map_or(0, DeviceBuffer::device_ptr),
            xq: x.qs.device_ptr(),
            xd: x.ds.device_ptr(),
            y: y.device_ptr(),
            tables: tables.0.device_ptr(),
            first: p.first as u32,
            second: p.second.unwrap_or(0) as u32,
            rows: p.rows as u32,
            cols: p.cols as u32,
        };
        let kernel = if p.second.is_some() {
            &self.moe_gate_up[index]
        } else {
            &self.moe_down[index]
        };
        let staged = EXPERT_GROUP * (p.cols + 4 * p.cols / Q8K_BLOCK);
        let config = LaunchConfig {
            grid: [
                (p.rows as u32).div_ceil(MOE_WARPS * MOE_WARP_ROWS),
                p.n_groups as u32,
                1,
            ],
            block: [MOE_WARPS * 32, 1, 1],
            shared_bytes: staged as u32,
        };
        // SAFETY: matches `MoeParams`; buffer sizes were checked above and
        // the caller vouches for the groups, slots and input rows.
        unsafe { launch_struct(kernel, config, stream, &params) }
    }

    /// Queues `out[t] = out[t] * sigmoid(gate[t])` plus the weighted outputs
    /// of token `t`'s picks, added in pick order; `out` holds the shared
    /// expert's output on entry, or is taken as zero without one.
    ///
    /// # Safety
    ///
    /// Every row index must lie inside `experts`.
    pub unsafe fn moe_combine(
        &self,
        m: &ExpertMix,
        out: &mut DeviceBuffer<f32>,
        stream: &Stream,
    ) -> Result<()> {
        let n = m.tokens * m.d;
        m.rows.check_holds(m.tokens * m.picks, "combined rows")?;
        m.weights
            .check_holds(m.tokens * m.picks, "combined weights")?;
        out.check_holds(n, "combined output")?;
        if let Some(g) = m.gates {
            let last = g.first + (m.tokens.max(1) - 1) * g.stride;
            g.values.check_holds(last + 1, "shared expert gates")?;
        }
        if m.tokens == 0 {
            return Ok(());
        }
        let params = CombineParams {
            experts: m.experts.device_ptr(),
            rows: m.rows.device_ptr(),
            weights: m.weights.device_ptr(),
            picks: m.picks as u32,
            shared: m.shared as u32,
            out: out.device_ptr(),
            gates: m.gates.map_or(0, |g| g.values.ptr_at(g.first)),
            gate_stride: m.gates.map_or(0, |g| g.stride as u32),
            d: m.d as u32,
        };
        let config = LaunchConfig {
            grid: [(m.d as u32).div_ceil(COMBINE_THREADS), m.tokens as u32, 1],
            block: [COMBINE_THREADS, 1, 1],
            shared_bytes: 0,
        };
        // SAFETY: matches `CombineParams`; sizes checked above, rows vouched
        // for by the caller.
        unsafe { launch_struct(&self.moe_combine, config, stream, &params) }
    }
}
