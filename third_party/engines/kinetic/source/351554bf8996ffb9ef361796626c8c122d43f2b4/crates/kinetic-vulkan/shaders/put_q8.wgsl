// Writes a GEMV input the way quantize_q8.wgsl makes one: the f32 values in
// `ox`, and in blocks of 32 the int8 values in `oq`, four to a word, and
// (d, d * sum of the int8 values) in `od`. The including kernel declares the
// three buffers.

// Stores `v` as element `e`. The 32 lanes of the calling subgroup hold the
// 32 elements of one block in lane order, so they all call this together.
fn put_q8(e: u32, v: f32, lane: u32) {
    ox[e] = v;
    let amax = subgroupMax(abs(v));
    let d = amax / 127.0;
    let inv = select(0.0, 1.0 / d, amax > 0.0);
    let q = i32(round(v * inv));
    let sum = subgroupAdd(q);
    let word = pack4xI8(vec4<i32>(
        q,
        subgroupShuffleDown(q, 1u),
        subgroupShuffleDown(q, 2u),
        subgroupShuffleDown(q, 3u),
    ));
    if lane % 4u == 0u {
        oq[e / 4u] = word;
    }
    if lane == 0u {
        od[e / 32u] = vec2<f32>(d, d * f32(sum));
    }
}
