// RMS norm of each token row of the batch, written as a GEMV input:
// out = x * w / sqrt(mean(x * x) + eps). With ADD, x += scale * y first, in
// place: the residual add that ends a block; with POST as well, y takes its
// own norm, by the weights `post`, before it is added.

struct Shape {
    len: u32,
    eps: f32,
    flags: u32,
    scale: f32,
}

// Bits of `flags`.
const ADD: u32 = 1u;
const POST: u32 = 2u;

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read_write> x: array<f32>;
@group(0) @binding(2) var<storage, read> y: array<f32>;
@group(0) @binding(3) var<storage, read> w: array<f32>;
@group(0) @binding(4) var<storage, read_write> ox: array<f32>;
@group(0) @binding(5) var<storage, read_write> oq: array<u32>;
@group(0) @binding(6) var<storage, read_write> od: array<vec2<f32>>;
@group(0) @binding(7) var<storage, read> post: array<f32>;

const THREADS: u32 = 256u;

var<workgroup> partial: array<f32, 8>;

// The sum of `v` over the workgroup; every invocation calls it together.
fn total(v: f32, slot: u32, lane: u32) -> f32 {
    let s = subgroupAdd(v);
    workgroupBarrier();
    if lane == 0u {
        partial[slot] = s;
    }
    workgroupBarrier();
    var sum = 0.0;
    for (var i = 0u; i < THREADS / 32u; i++) {
        sum += partial[i];
    }
    return sum;
}

fn rms_scale(sum_sq: f32) -> f32 {
    return 1.0 / sqrt(sum_sq / f32(shape.len) + shape.eps);
}

@compute @workgroup_size(256)
fn main(
    @builtin(workgroup_id) group: vec3<u32>,
    @builtin(local_invocation_index) tid: u32,
    @builtin(subgroup_id) slot: u32,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let row = group.x;
    if row >= batch[0] {
        return;
    }
    let base = row * shape.len;
    let add = (shape.flags & ADD) != 0u;
    var post_scale = 0.0;
    if (shape.flags & POST) != 0u {
        var ss = 0.0;
        for (var i = tid; i < shape.len; i += THREADS) {
            let v = y[base + i];
            ss += v * v;
        }
        post_scale = rms_scale(total(ss, slot, lane));
    }
    var ss = 0.0;
    for (var i = tid; i < shape.len; i += THREADS) {
        var v = x[base + i];
        if add {
            var a = y[base + i];
            if (shape.flags & POST) != 0u {
                a *= post_scale * post[i];
            }
            v += a * shape.scale;
            x[base + i] = v;
        }
        ss += v * v;
    }
    let scale = rms_scale(total(ss, slot, lane));
    // Rows are whole blocks of 32, so every subgroup runs whole.
    for (var i = tid; i < shape.len; i += THREADS) {
        put_q8(base + i, x[base + i] * (scale * w[i]), lane);
    }
}
