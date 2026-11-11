// The recurrence of a gated delta-rule layer. Each subgroup owns one row of
// one value head's state, `head_k_dim` = 128 values, four per lane, and
// applies the delta rule
//     S = decay * S;  S += b * (v - S k) k^T
// for every position in turn, then reads out o = S q for the pass's tokens.
// Value head h reads key head h % n_k_heads.
//
// Positions run from batch word 4: before the pass's tokens come the tokens
// run since a checkpoint, replayed from their journal slots, so the state
// itself changes only when batch word 5 says to keep it. With `replay`, no
// token of the pass runs: the journal up to the pass's first position is
// applied and kept, which is how a rollback keeps the tokens it keeps.

struct Shape {
    channels: u32,
    n_k_heads: u32,
    n_v_heads: u32,
    head_v_dim: u32,
    journal_slots: u32,
    eps: f32,
    replay: u32,
}

const DK: u32 = 128u;

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read> journal: array<f32>;
@group(0) @binding(2) var<storage, read_write> state: array<vec4<f32>>;
@group(0) @binding(3) var<storage, read_write> out: array<f32>;

fn head4(base: u32, lane: u32) -> vec4<f32> {
    let i = base + 4u * lane;
    return vec4<f32>(journal[i], journal[i + 1u], journal[i + 2u], journal[i + 3u]);
}

fn l2_normed(x: vec4<f32>) -> vec4<f32> {
    let norm = sqrt(subgroupAdd(dot(x, x)));
    return x * (1.0 / max(norm, shape.eps));
}

@compute @workgroup_size(128)
fn main(
    @builtin(workgroup_id) group: vec3<u32>,
    @builtin(subgroup_id) slot: u32,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let dv = shape.head_v_dim;
    let row = group.x * 4u + slot;
    if row >= shape.n_v_heads * dv {
        return;
    }
    let vh = row / dv;
    let i = row % dv;
    let kh = vh % shape.n_k_heads;
    let key_dim = shape.n_k_heads * DK;
    let value_dim = shape.n_v_heads * dv;
    let jstride = shape.channels + 2u * shape.n_v_heads;
    let pos0 = batch[1];
    var end = pos0 + batch[0];
    if shape.replay != 0u {
        end = pos0;
    }
    let q_scale = 1.0 / sqrt(f32(DK));

    let at = row * (DK / 4u) + lane;
    var s = state[at];
    for (var p = batch[4]; p < end; p++) {
        let base = p % shape.journal_slots * jstride;
        let k = l2_normed(head4(base + key_dim + kh * DK, lane));
        let v = journal[base + 2u * key_dim + vh * dv + i];
        let decay = journal[base + shape.channels + vh];
        let b = journal[base + shape.channels + shape.n_v_heads + vh];
        let delta = (v - decay * subgroupAdd(dot(s, k))) * b;
        s = s * decay + k * delta;
        if p >= pos0 {
            let q = l2_normed(head4(base + kh * DK, lane)) * q_scale;
            let o = subgroupAdd(dot(s, q));
            if lane == 0u {
                out[(p - pos0) * value_dim + vh * dv + i] = o;
            }
        }
    }
    if batch[5] != 0u {
        state[at] = s;
    }
}
