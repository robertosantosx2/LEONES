// Readies one head of one token for attention, in place in the token's row
// of `qkv`, which holds every query head, then every key head, then every
// value head. Adds the bias; gives query and key heads their RMS norm and
// rotary embedding; stores key and value heads as f16 in the caches at the
// token's position, in slot position % slots.
//
// A query head is `q_head_len` values: `head_dim` queries, then as many gate
// values when the output is gated per value. Only the queries are normed
// and rotated. Rotary pair i turns by the angle whose cosine and sine are
// words 2i and 2i + 1 of the token's row of the layer's table in the batch.

struct Shape {
    n_head: u32,
    n_kv: u32,
    head_dim: u32,
    q_head_len: u32,
    stride: u32,
    rope_dims: u32,
    rope_table: u32,
    flags: u32,
    eps: f32,
    bias: u32,
    q_norm: u32,
    k_norm: u32,
    slots: u32,
}

// Bits of `flags`.
const ADJACENT: u32 = 1u;
const NORM_AFTER_ROPE: u32 = 2u;
const BIAS: u32 = 4u;
const Q_NORM: u32 = 8u;
const K_NORM: u32 = 16u;

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read_write> qkv: array<f32>;
@group(0) @binding(2) var<storage, read> consts: array<f32>;
@group(0) @binding(3) var<storage, read_write> kc: array<u32>;
@group(0) @binding(4) var<storage, read_write> vc: array<u32>;

fn norm(base: u32, w: u32, lane: u32) {
    var ss = 0.0;
    for (var e = lane; e < shape.head_dim; e += 32u) {
        let v = qkv[base + e];
        ss += v * v;
    }
    ss = subgroupAdd(ss);
    let scale = 1.0 / sqrt(ss / f32(shape.head_dim) + shape.eps);
    for (var e = lane; e < shape.head_dim; e += 32u) {
        qkv[base + e] = qkv[base + e] * (scale * consts[w + e]);
    }
}

fn rotate(base: u32, t: u32, lane: u32) {
    let half = shape.rope_dims / 2u;
    let table = shape.rope_table + t * shape.rope_dims;
    for (var i = lane; i < half; i += 32u) {
        var a = base + i;
        var b = base + i + half;
        if (shape.flags & ADJACENT) != 0u {
            a = base + 2u * i;
            b = a + 1u;
        }
        let cos = bitcast<f32>(batch[table + 2u * i]);
        let sin = bitcast<f32>(batch[table + 2u * i + 1u]);
        let x = qkv[a];
        let y = qkv[b];
        qkv[a] = x * cos - y * sin;
        qkv[b] = x * sin + y * cos;
    }
}

@compute @workgroup_size(32)
fn main(
    @builtin(workgroup_id) group: vec3<u32>,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let t = group.y;
    if t >= batch[0] {
        return;
    }
    let slot = group.x;
    let hd = shape.head_dim;
    let kv_dim = shape.n_kv * hd;
    let q_len = shape.n_head * shape.q_head_len;
    var at = slot * shape.q_head_len;
    var w = shape.q_norm;
    var normed = (shape.flags & Q_NORM) != 0u;
    var len = shape.q_head_len;
    if slot >= shape.n_head {
        at = q_len + (slot - shape.n_head) * hd;
        w = shape.k_norm;
        normed = (shape.flags & K_NORM) != 0u;
        len = hd;
    }
    let rotated = slot < shape.n_head + shape.n_kv;
    normed = normed && rotated;
    let base = t * shape.stride + at;

    if (shape.flags & BIAS) != 0u {
        for (var e = lane; e < len; e += 32u) {
            qkv[base + e] += consts[shape.bias + at + e];
        }
    }
    let after = (shape.flags & NORM_AFTER_ROPE) != 0u;
    if normed && !after {
        norm(base, w, lane);
    }
    storageBarrier();
    if rotated {
        rotate(base, t, lane);
    }
    storageBarrier();
    if normed && after {
        norm(base, w, lane);
    }
    storageBarrier();

    if slot >= shape.n_head {
        let keys = slot < shape.n_head + shape.n_kv;
        let head = select(at - q_len - kv_dim, at - q_len, keys);
        let row = ((batch[1] + t) % shape.slots * kv_dim + head) / 2u;
        for (var i = lane; i < hd / 2u; i += 32u) {
            let word = pack2x16float(vec2<f32>(qkv[base + 2u * i], qkv[base + 2u * i + 1u]));
            if keys {
                kc[row + i] = word;
            } else {
                vc[row + i] = word;
            }
        }
    }
}
