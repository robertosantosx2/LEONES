// Attention of one query head of one token over the cached positions up to
// its own, written as a GEMV input. `PAIRS`, head_dim / 64, is set per
// kernel; lane i holds pairs i + 32k of the head.
//
// The four subgroups take every fourth position, each keeping a running
// maximum, sum and weighted sum of values (an online softmax), and combine
// at the end. A token's result does not depend on the rest of its batch.
//
// A token sees the last `window` positions up to its own; position p sits
// in cache slot p % slots. With gate 1 the output is multiplied by the
// sigmoid of the gate values after each query head; with gate 2 by that of
// the head's one gate value at `gate_at` in the token's row.

struct Shape {
    n_head: u32,
    n_kv: u32,
    stride: u32,
    q_head_len: u32,
    scale: f32,
    gate: u32,
    gate_at: u32,
    window: u32,
    slots: u32,
}

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read> qkv: array<f32>;
@group(0) @binding(2) var<storage, read> kc: array<u32>;
@group(0) @binding(3) var<storage, read> vc: array<u32>;
@group(0) @binding(4) var<storage, read_write> ox: array<f32>;
@group(0) @binding(5) var<storage, read_write> oq: array<u32>;
@group(0) @binding(6) var<storage, read_write> od: array<vec2<f32>>;

const HD: u32 = 64u * PAIRS;
const SUBGROUPS: u32 = 4u;
const THREADS: u32 = 32u * SUBGROUPS;
const LOWEST: f32 = -3.4e38;

var<workgroup> top: array<f32, SUBGROUPS>;
var<workgroup> total: array<f32, SUBGROUPS>;
var<workgroup> partial: array<f32, SUBGROUPS * HD>;

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
    let head = group.x;
    let len = batch[1] + t + 1u;
    let start = len - min(len, shape.window);
    let row_words = shape.n_kv * HD / 2u;
    let kv_head = head / (shape.n_head / shape.n_kv);
    let qb = t * shape.stride + head * shape.q_head_len;

    var q: array<vec2<f32>, PAIRS>;
    var acc: array<vec2<f32>, PAIRS>;
    for (var k = 0u; k < PAIRS; k++) {
        let e = qb + 2u * (lane + 32u * k);
        q[k] = vec2<f32>(qkv[e], qkv[e + 1u]) * shape.scale;
        acc[k] = vec2<f32>(0.0);
    }
    var m = LOWEST;
    var l = 0.0;
    let first = kv_head * HD / 2u + lane;
    for (var p = start + slot; p < len; p += SUBGROUPS) {
        let row = p % shape.slots * row_words + first;
        var qk = 0.0;
        for (var k = 0u; k < PAIRS; k++) {
            qk += dot(q[k], unpack2x16float(kc[row + 32u * k]));
        }
        let s = subgroupAdd(qk);
        let next = max(m, s);
        let c = exp(m - next);
        let e = exp(s - next);
        l = l * c + e;
        for (var k = 0u; k < PAIRS; k++) {
            acc[k] = acc[k] * c + e * unpack2x16float(vc[row + 32u * k]);
        }
        m = next;
    }
    if lane == 0u {
        top[slot] = m;
        total[slot] = l;
    }
    for (var k = 0u; k < PAIRS; k++) {
        let e = slot * HD + 2u * (lane + 32u * k);
        partial[e] = acc[k].x;
        partial[e + 1u] = acc[k].y;
    }
    workgroupBarrier();

    var best = top[0];
    for (var s = 1u; s < SUBGROUPS; s++) {
        best = max(best, top[s]);
    }
    var den = 0.0;
    for (var s = 0u; s < SUBGROUPS; s++) {
        den += total[s] * exp(top[s] - best);
    }
    let out = (t * shape.n_head + head) * HD;
    // HD is a multiple of 64, so subgroups run whole.
    for (var e = tid; e < HD; e += THREADS) {
        var o = 0.0;
        for (var s = 0u; s < SUBGROUPS; s++) {
            o += partial[s * HD + e] * exp(top[s] - best);
        }
        o /= den;
        if shape.gate == 1u {
            o /= 1.0 + exp(-qkv[qb + HD + e]);
        } else if shape.gate == 2u {
            o /= 1.0 + exp(-qkv[t * shape.stride + shape.gate_at + head]);
        }
        put_q8(out + e, o, lane);
    }
}
