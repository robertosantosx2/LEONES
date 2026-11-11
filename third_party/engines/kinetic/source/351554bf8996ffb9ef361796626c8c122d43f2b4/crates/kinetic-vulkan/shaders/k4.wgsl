// Q4_K and Q5_K share their first 16 bytes: f16 d, f16 dmin and twelve bytes
// packing a 6-bit scale and min for each of the eight sub-blocks of 32. Eight
// invocations share a block; invocation j takes 16 bytes of the 128 low-bit
// bytes, whose low nibbles are 16 elements of sub-block 2(j/2) and high
// nibbles the same 16 positions of sub-block 2(j/2)+1.

const LANES: u32 = 8u;

// Scale (x) and min (y) of sub-block s, from the packed bytes held as the
// little-endian words q0 = bytes 0..3, q1 = 4..7, q2 = 8..11.
fn k4_scale_min(s: u32, q0: u32, q1: u32, q2: u32) -> vec2<f32> {
    if s < 4u {
        return vec2<f32>(f32((q0 >> (8u * s)) & 63u), f32((q1 >> (8u * s)) & 63u));
    }
    let t = 8u * (s - 4u);
    return vec2<f32>(
        f32(((q2 >> t) & 0x0Fu) | ((q0 >> t >> 2u) & 0x30u)),
        f32(((q2 >> t >> 4u) & 0x0Fu) | ((q1 >> t >> 2u) & 0x30u)),
    );
}

// Invocation j's share of block b given its integer dot products `lo`
// (sub-block 2(j/2)) and `hi` (the next one).
fn k4_combine(head: vec4<u32>, b: u32, j: u32, lo: i32, hi: i32) -> f32 {
    let s = 2u * (j / 2u);
    let a = k4_scale_min(s, head.y, head.z, head.w);
    let c = k4_scale_min(s + 1u, head.y, head.z, head.w);
    let dm = unpack2x16float(head.x);
    let x0 = xd[b * 8u + s];
    let x1 = xd[b * 8u + s + 1u];
    var r = dm.x * (a.x * x0.x * f32(lo) + c.x * x1.x * f32(hi));
    // Both invocations of a sub-block see the same min; only one subtracts it.
    if j % 2u == 0u {
        r -= dm.y * (a.y * x0.y + c.y * x1.y);
    }
    return r;
}

// The input word matching invocation j's low nibbles; the high nibbles' is
// two words (32 elements) later.
fn k4_input(b: u32, j: u32) -> u32 {
    return b * 16u + 4u * (j / 2u) + j % 2u;
}
