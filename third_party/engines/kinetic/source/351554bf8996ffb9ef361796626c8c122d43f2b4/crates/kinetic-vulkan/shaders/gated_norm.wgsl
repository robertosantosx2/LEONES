// The output of a gated delta-rule layer for one value head of one token,
// written as a GEMV input: the head's recurrence output takes an RMS norm
// by `weight` and is multiplied by the SiLU of its output gates, which sit
// at `gate_at` in the token's row of `proj`.

struct Shape {
    head_v_dim: u32,
    n_v_heads: u32,
    stride: u32,
    gate_at: u32,
    eps: f32,
}

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read> o: array<f32>;
@group(0) @binding(2) var<storage, read> proj: array<f32>;
@group(0) @binding(3) var<storage, read> weight: array<f32>;
@group(0) @binding(4) var<storage, read_write> ox: array<f32>;
@group(0) @binding(5) var<storage, read_write> oq: array<u32>;
@group(0) @binding(6) var<storage, read_write> od: array<vec2<f32>>;

const THREADS: u32 = 128u;

var<workgroup> partial: array<f32, 4>;

@compute @workgroup_size(128)
fn main(
    @builtin(workgroup_id) group: vec3<u32>,
    @builtin(local_invocation_index) tid: u32,
    @builtin(subgroup_id) slot: u32,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let t = group.y;
    if t >= batch[0] {
        return;
    }
    let dv = shape.head_v_dim;
    let base = (t * shape.n_v_heads + group.x) * dv;
    var ss = 0.0;
    for (var e = tid; e < dv; e += THREADS) {
        let v = o[base + e];
        ss += v * v;
    }
    ss = subgroupAdd(ss);
    if lane == 0u {
        partial[slot] = ss;
    }
    workgroupBarrier();
    let total = partial[0] + partial[1] + partial[2] + partial[3];
    let scale = 1.0 / sqrt(total / f32(dv) + shape.eps);
    let gates = t * shape.stride + shape.gate_at + group.x * dv;
    // `head_v_dim` is a multiple of 32, so subgroups run whole.
    for (var e = tid; e < dv; e += THREADS) {
        let z = proj[gates + e];
        put_q8(base + e, o[base + e] * (scale * weight[e]) * (z / (1.0 + exp(-z))), lane);
    }
}
