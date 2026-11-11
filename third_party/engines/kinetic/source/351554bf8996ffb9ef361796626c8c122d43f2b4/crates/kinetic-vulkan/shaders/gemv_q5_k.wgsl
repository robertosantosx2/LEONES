// block_q5_K: d, dmin, scales[12], qh[32], qs[128]; 176 bytes, eleven words.
// Bit t of qh[l] is the fifth bit of element l of sub-block t.

fn block_dot(total: u32, blk: u32, b: u32, j: u32) -> f32 {
    let head = w[blk * 11u];
    let qh = w[blk * 11u + 1u + j % 2u];
    let q = w[blk * 11u + 3u + j];
    let xi = k4_input(b, j);
    let s = 2u * (j / 2u);
    let ones = vec4<u32>(0x01010101u);
    let lo = (q & vec4<u32>(NIBBLES)) | (((qh >> vec4<u32>(s)) & ones) << vec4<u32>(4u));
    let hi = ((q >> vec4<u32>(4u)) & vec4<u32>(NIBBLES))
        | (((qh >> vec4<u32>(s + 1u)) & ones) << vec4<u32>(4u));
    return k4_combine(head, b, j, dot16(lo, xq[xi]), dot16(hi, xq[xi + 2u]));
}
