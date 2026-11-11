// The greedy token of each row the output head ran on: the index of the
// largest logit, the lowest index among equals, then that logit's bits.

struct Shape {
    vocab: u32,
}

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> batch: array<u32>;
@group(0) @binding(1) var<storage, read> logits: array<f32>;
@group(0) @binding(2) var<storage, read_write> best: array<u32>;

const THREADS: u32 = 256u;

var<workgroup> values: array<f32, 8>;
var<workgroup> indices: array<u32, 8>;

// The better of the subgroup's candidates.
fn reduce(v: f32, i: u32) -> vec2<u32> {
    let top = subgroupMax(v);
    let at = subgroupMin(select(0xFFFFFFFFu, i, v == top));
    return vec2<u32>(bitcast<u32>(top), at);
}

@compute @workgroup_size(256)
fn main(
    @builtin(workgroup_id) group: vec3<u32>,
    @builtin(local_invocation_index) tid: u32,
    @builtin(subgroup_id) slot: u32,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let row = group.x;
    if row >= batch[3] {
        return;
    }
    let base = row * shape.vocab;
    var v = -3.4e38;
    var at = 0xFFFFFFFFu;
    for (var i = tid; i < shape.vocab; i += THREADS) {
        let l = logits[base + i];
        if l > v {
            v = l;
            at = i;
        }
    }
    let r = reduce(v, at);
    if lane == 0u {
        values[slot] = bitcast<f32>(r.x);
        indices[slot] = r.y;
    }
    workgroupBarrier();
    if slot == 0u {
        let s = min(lane, THREADS / 32u - 1u);
        let r = reduce(values[s], indices[s]);
        if lane == 0u {
            best[2u * row] = min(r.y, shape.vocab - 1u);
            best[2u * row + 1u] = r.x;
        }
    }
}
