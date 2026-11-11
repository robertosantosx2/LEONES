// block_q6_K is 210 bytes, so blocks are only 2-byte aligned. The device copy
// is planar: all ql[128], then all qh[64], all scales[16], all f16 d.
//
// A block is two halves of 128 elements; in half n, element 32g + l (g < 4,
// l < 32) takes its low four bits from ql[64n + l + 32(g & 1)] (low nibble
// for g < 2, high for g >= 2) and its top two from bits 2g..2g+1 of
// qh[32n + l]. Each run of 16 elements has its own int8 scale.
//
// Eight invocations share a block. Invocation j = 4n + k loads ql bytes
// 64n + 16k, which hold elements l = 16(k & 1) .. +16 of group g = k / 2
// (low nibbles) and of group g + 2 (high nibbles).

const LANES: u32 = 8u;

// Signed byte `i` of a word.
fn sbyte(v: vec4<u32>, i: u32) -> f32 {
    return f32(extractBits(bitcast<i32>(v[i / 4u]), 8u * (i % 4u), 8u));
}

fn block_dot(total: u32, blk: u32, b: u32, j: u32) -> f32 {
    let n = j / 4u;
    let k = j % 4u;
    let g = k / 2u;

    let lq = w[blk * 8u + j];
    let hq = w[total * 8u + blk * 4u + 2u * n + (k & 1u)];
    let e = b * 256u + 128u * n + 32u * g + 16u * (k & 1u);
    let x0 = xq[e / 16u];
    let x1 = xq[e / 16u + 4u];

    let low2 = vec4<u32>(0x03030303u);
    let lo = (lq & vec4<u32>(NIBBLES)) | (((hq >> vec4<u32>(2u * g)) & low2) << vec4<u32>(4u));
    let hi = ((lq >> vec4<u32>(4u)) & vec4<u32>(NIBBLES))
        | (((hq >> vec4<u32>(2u * g + 4u)) & low2) << vec4<u32>(4u));
    // Quants are stored as q + 32; dotting 32 with the input takes it back out.
    let bias = vec4<u32>(0x20202020u);
    let s0 = dot16(lo, x0) - dot16(bias, x0);
    let s1 = dot16(hi, x1) - dot16(bias, x1);

    let scales = w[total * 12u + blk];
    let sc = 8u * n + (k & 1u) + 2u * g;
    let r = sbyte(scales, sc) * xd[e / 32u].x * f32(s0)
        + sbyte(scales, sc + 4u) * xd[e / 32u + 2u].x * f32(s1);
    return f16_at(total * 13u, blk) * r;
}
