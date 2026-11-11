// One subgroup routes one token: softmax over the n <= 32 * R logits at p[b ..] (lane holds i = lane + 32 r), top-k
// (ties to the lower index), renormalized weights. Lane j < k gets the j-th expert's id and weight.
const uint R = 16;
void topk(F32 p, uint b, uint n, uint k, float extra_scale, uint lane, out int id, out float w) {
    float v[R];
    float m = -1.0 / 0.0;
    for (uint r = 0; r < R; r++) { uint i = lane + 32 * r; v[r] = i < n ? p.v[b + i] : -1.0 / 0.0; m = max(m, v[r]); }
    m = warp_max(m);
    float s = 0.0;
    for (uint r = 0; r < R; r++) if (lane + 32 * r < n) { v[r] = expf_(v[r] - m); s += v[r]; }
    s = warp_sum(s);
    for (uint r = 0; r < R; r++) v[r] = fdiv(v[r], s);
    uint taken = 0;
    float sum = 0.0, mine = 0.0;
    id = 0;
    for (uint j = 0; j < k; j++) {
        // v >= 0, so its bits order like it; key = bits + 1 leaves 0 for "none". Max key, then the lowest index of it.
        uint bk = 0, bi = 0xffffffffu;
        for (uint r = 0; r < R; r++) {
            uint i = lane + 32 * r, key = floatBitsToUint(v[r]) + 1;
            if (i < n && (taken >> r & 1) == 0 && key > bk) { bk = key; bi = i; }
        }
        uint mk = warp_max_uint(bk);
        bi = warp_min_uint(bk == mk ? bi : 0xffffffffu);
        float bv = uintBitsToFloat(mk - 1);
        if ((bi & 31) == lane) taken |= 1u << (bi >> 5);
        if (lane == j) { id = int(bi); mine = bv; }
        sum += bv;
    }
    float scale = fdiv(1.0, max(sum, 6.103515625e-5));
    if (extra_scale != 0.0) scale *= extra_scale;
    w = mine * scale;
}
