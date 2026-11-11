// Gated short causal convolution of each token row of the batch, written as
// a GEMV input. A row of `bcx` holds the input gate b, the output gate c and
// the value x, `len` channels each; the convolution runs over b * x of the
// last `taps` positions and its result is scaled by c.
//
// Each token stores its own b * x in the ring, at slot position % slots,
// and reads those of earlier positions from it, or from `bcx` for earlier
// tokens of the same pass. The ring holds `taps - 1` positions and a pass
// more, so a pass never overwrites a position it reads, and a rollback
// leaves nothing to undo.

struct Shape {
    len: u32,
    taps: u32,
    slots: u32,
}

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read> bcx: array<f32>;
@group(0) @binding(2) var<storage, read> weight: array<f32>;
@group(0) @binding(3) var<storage, read_write> ring: array<f32>;
@group(0) @binding(4) var<storage, read_write> ox: array<f32>;
@group(0) @binding(5) var<storage, read_write> oq: array<u32>;
@group(0) @binding(6) var<storage, read_write> od: array<vec2<f32>>;

// b * x of channel `ch` at position `p`, at most the last of the pass.
fn gated(p: u32, ch: u32) -> f32 {
    let pos0 = batch[1];
    if p >= pos0 {
        let row = (p - pos0) * 3u * shape.len;
        return bcx[row + ch] * bcx[row + 2u * shape.len + ch];
    }
    return ring[p % shape.slots * shape.len + ch];
}

@compute @workgroup_size(256)
fn main(
    @builtin(workgroup_id) group: vec3<u32>,
    @builtin(local_invocation_index) tid: u32,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let ch = group.x * 256u + tid;
    let t = group.y;
    // `len` is a multiple of 32, so subgroups leave whole.
    if t >= batch[0] || ch >= shape.len {
        return;
    }
    let pos = batch[1] + t;
    let w = ch * shape.taps;
    let own = gated(pos, ch);
    var acc = 0.0;
    for (var j = 0u; j + 1u < shape.taps; j++) {
        let back = shape.taps - 1u - j;
        if pos >= back {
            acc += weight[w + j] * gated(pos - back, ch);
        }
    }
    acc += weight[w + shape.taps - 1u] * own;
    ring[pos % shape.slots * shape.len + ch] = own;
    let c = bcx[t * 3u * shape.len + shape.len + ch];
    put_q8(t * shape.len + ch, c * acc, lane);
}
