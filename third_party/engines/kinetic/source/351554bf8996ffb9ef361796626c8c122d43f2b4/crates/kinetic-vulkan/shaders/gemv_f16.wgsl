// F16 weights: a block is one word of 8 values.

const LANES: u32 = 1u;

fn block_dot(total: u32, blk: u32, b: u32, part: u32) -> f32 {
    let v = w[blk];
    let lo = vec4<f32>(unpack2x16float(v.x), unpack2x16float(v.y));
    let hi = vec4<f32>(unpack2x16float(v.z), unpack2x16float(v.w));
    return dot(lo, x[2u * b]) + dot(hi, x[2u * b + 1u]);
}
