// The f32 input quantized to int8 in blocks of 32 for the quantized GEMV
// kernels, with one invocation per block. Each block gets d = max |x| / 127
// and the values round(x / d), four to a word, plus d times their sum.

struct Shape {
    blocks: u32,
}

var<immediate> shape: Shape;

@group(0) @binding(0) var<storage, read> x: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read_write> xq: array<vec4<u32>>;
@group(0) @binding(2) var<storage, read_write> xd: array<vec2<f32>>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let blk = id.x;
    if blk >= shape.blocks {
        return;
    }
    var v: array<vec4<f32>, 8>;
    var amax = 0.0;
    for (var i = 0u; i < 8u; i++) {
        v[i] = x[8u * blk + i];
        let a = abs(v[i]);
        amax = max(amax, max(max(a.x, a.y), max(a.z, a.w)));
    }
    let d = amax / 127.0;
    let inv = select(0.0, 1.0 / d, amax > 0.0);
    var sum = 0;
    for (var i = 0u; i < 2u; i++) {
        var words: vec4<u32>;
        for (var k = 0u; k < 4u; k++) {
            let q = vec4<i32>(round(v[4u * i + k] * inv));
            sum += q.x + q.y + q.z + q.w;
            words[k] = pack4xI8(q);
        }
        xq[2u * blk + i] = words;
    }
    xd[blk] = vec2<f32>(d, d * f32(sum));
}
