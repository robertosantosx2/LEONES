// F32 weights: a block is one word of 4 values.

const LANES: u32 = 1u;

fn block_dot(total: u32, blk: u32, b: u32, part: u32) -> f32 {
    return dot(bitcast<vec4<f32>>(w[blk]), x[b]);
}
