// block_q4_K: d, dmin, scales[12], qs[128]; 144 bytes, nine words.

fn block_dot(total: u32, blk: u32, b: u32, j: u32) -> f32 {
    let head = w[blk * 9u];
    let q = w[blk * 9u + 1u + j];
    let xi = k4_input(b, j);
    let lo = q & vec4<u32>(NIBBLES);
    let hi = (q >> vec4<u32>(4u)) & vec4<u32>(NIBBLES);
    return k4_combine(head, b, j, dot16(lo, xq[xi]), dot16(hi, xq[xi + 2u]));
}
