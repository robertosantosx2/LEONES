// Q8_0 is stored planar on the device: all 32-byte quant runs, then all f16
// scales, so every run is 16-byte aligned. Two invocations share a block.

const LANES: u32 = 2u;

fn block_dot(total: u32, blk: u32, b: u32, part: u32) -> f32 {
    let q = w[blk * 2u + part];
    let xv = xq[b * 2u + part];
    return f16_at(total * 2u, blk) * xd[b].x * f32(dot16(q, xv));
}
