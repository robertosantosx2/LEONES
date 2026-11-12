// Streams `words` 16-byte words once and adds their 32-bit sum to `out`.
// The result only keeps the loads alive; the kernel exists to measure how
// fast device memory can be read.

struct Shape {
    words: u32,
}

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> data: array<vec4<u32>>;
@group(0) @binding(1) var<storage, read_write> out: atomic<u32>;

fn word_sum(v: vec4<u32>) -> u32 {
    return v.x + v.y + v.z + v.w;
}

@compute @workgroup_size(256)
fn main(
    @builtin(global_invocation_id) id: vec3<u32>,
    @builtin(num_workgroups) groups: vec3<u32>,
    @builtin(subgroup_invocation_id) lane: u32,
) {
    let stride = groups.x * 256u;
    let n = shape.words;
    var i = id.x;
    var acc = 0u;
    // Four independent loads per step keep enough bytes in flight.
    for (; i + 3u * stride < n; i += 4u * stride) {
        acc += word_sum(data[i]) + word_sum(data[i + stride]) + word_sum(data[i + 2u * stride])
            + word_sum(data[i + 3u * stride]);
    }
    for (; i < n; i += stride) {
        acc += word_sum(data[i]);
    }
    acc = subgroupAdd(acc);
    if lane == 0u {
        atomicAdd(&out, acc);
    }
}
