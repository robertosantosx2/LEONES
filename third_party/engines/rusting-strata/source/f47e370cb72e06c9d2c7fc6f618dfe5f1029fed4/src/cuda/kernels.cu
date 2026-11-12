// Decode-path kernels. Dequant ports of src/quant/mod.rs (from llama.cpp ggml-quants.c, MIT License, ggml authors).
// Tables (iq2xs_grid, iq3xxs_grid, ksigns_iq2xs, kvalues_iq4nl) are prepended by src/cuda/mod.rs.

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;

__device__ __forceinline__ float h2f(u16 h) { float f; asm("cvt.f32.f16 %0, %1;" : "=f"(f) : "h"(h)); return f; }
__device__ __forceinline__ u16 f2h(float f) { u16 h; asm("cvt.rn.f16.f32 %0, %1;" : "=h"(h) : "f"(f)); return h; }
__device__ __forceinline__ u32 ld16(const u8* p) { return *(const u16*)p; }  // 2-aligned only (every quant field is)
__device__ __forceinline__ u32 ld32(const u8* p) { return p[0] | (p[1] << 8) | (p[2] << 16) | ((u32)p[3] << 24); }
__device__ __forceinline__ float ldh(const u8* p) { return h2f((u16)ld16(p)); }
__device__ __forceinline__ float silu(float x) { return x / (1.0f + expf(-x)); }
__device__ __forceinline__ float sigmoid(float x) { return 1.0f / (1.0f + expf(-x)); }
__device__ __forceinline__ float softplus(float x) { return x > 20.0f ? x : log1pf(expf(x)); }

__device__ __forceinline__ float warp_sum(float v) {
    for (int o = 16; o > 0; o >>= 1) v += __shfl_xor_sync(0xffffffff, v, o);
    return v;
}
__device__ __forceinline__ float warp_max(float v) {
    for (int o = 16; o > 0; o >>= 1) v = fmaxf(v, __shfl_xor_sync(0xffffffff, v, o));
    return v;
}
// Unsigned integer forms of warp_max (__reduce_max_sync/__reduce_min_sync need sm_80; the shuffles run on sm_70+).
__device__ __forceinline__ unsigned warp_max_u(unsigned v) {
    for (int o = 16; o > 0; o >>= 1) v = max(v, __shfl_xor_sync(0xffffffff, v, o));
    return v;
}
__device__ __forceinline__ unsigned warp_min_u(unsigned v) {
    for (int o = 16; o > 0; o >>= 1) v = min(v, __shfl_xor_sync(0xffffffff, v, o));
    return v;
}
// Sum over the whole block; every thread gets the result. blockDim.x must be a multiple of 32.
__device__ float block_sum(float v) {
    __shared__ float s[32];
    int lane = threadIdx.x & 31, w = threadIdx.x >> 5, nw = blockDim.x >> 5;
    v = warp_sum(v);
    __syncthreads();
    if (lane == 0) s[w] = v;
    __syncthreads();
    v = lane < nw ? s[lane] : 0.0f;
    return warp_sum(v);
}

// ---- dequant: 8 values [8*sub, 8*sub+8) of a 256-element super-block ----

template <int T> __device__ void deq8(const u8* b, int sub, float* o);

template <> __device__ __forceinline__ void deq8<0>(const u8* b, int sub, float* o) {  // F32
    const float4* f = (const float4*)b + 2 * sub;  // 16-byte loads: rows are 1024-byte multiples
    float4 a = f[0], c = f[1];
    o[0] = a.x; o[1] = a.y; o[2] = a.z; o[3] = a.w; o[4] = c.x; o[5] = c.y; o[6] = c.z; o[7] = c.w;
}
template <> __device__ __forceinline__ void deq8<30>(const u8* b, int sub, float* o) {  // BF16
    uint4 q = *(const uint4*)(b + 16 * sub);  // one 16-byte load: rows are 16-byte multiples (cols % 8 == 0)
    u32 w[4] = {q.x, q.y, q.z, q.w};
    for (int i = 0; i < 4; i++) { o[2 * i] = __uint_as_float(w[i] << 16); o[2 * i + 1] = __uint_as_float(w[i] & 0xFFFF0000u); }
}
template <> __device__ __forceinline__ void deq8<8>(const u8* b, int sub, float* o) {  // Q8_0, 8 blocks of 34
    const u8* p = b + 34 * (sub >> 2);
    float d = ldh(p);
    const signed char* q = (const signed char*)p + 2 + (sub & 3) * 8;
    for (int i = 0; i < 8; i++) o[i] = (float)q[i] * d;
}
template <> __device__ __forceinline__ void deq8<10>(const u8* b, int sub, float* o) {  // Q2_K
    int e = sub * 8, n = e >> 7, r = e & 127, j = r >> 5, r2 = r & 31;
    u8 s = b[n * 8 + j * 2 + (r2 >> 4)];
    float dl = ldh(b + 80) * (float)(s & 0xF), ml = ldh(b + 82) * (float)(s >> 4);
    const u8* q = b + 16 + 32 * n + r2;
    for (int i = 0; i < 8; i++) o[i] = dl * (float)((q[i] >> (2 * j)) & 3) - ml;
}
template <> __device__ __forceinline__ void deq8<11>(const u8* b, int sub, float* o) {  // Q3_K
    int e = sub * 8, n = e >> 7, r = e & 127, j = r >> 5, i0 = r & 31, is = n * 8 + j * 2 + (i0 >> 4);
    const u8* sc = b + 96;
    int low = is < 8 ? (sc[is] & 0xF) : (sc[is - 8] >> 4);
    int hi = (sc[8 + (is & 3)] >> (2 * (is >> 2))) & 3;
    float dl = ldh(b + 108) * (float)((low | (hi << 4)) - 32);
    u8 m = 1 << (n * 4 + j);
    for (int i = 0; i < 8; i++) {
        int qi = i0 + i;
        int v = ((b[32 + 32 * n + qi] >> (2 * j)) & 3) - ((b[qi] & m) ? 0 : 4);
        o[i] = dl * (float)v;
    }
}
__device__ __forceinline__ void scale_min_k4(int j, const u8* q, int& s, int& m) {
    if (j < 4) { s = q[j] & 63; m = q[j + 4] & 63; }
    else { s = (q[j + 4] & 0xF) | ((q[j - 4] >> 6) << 4); m = (q[j + 4] >> 4) | ((q[j] >> 6) << 4); }
}
template <> __device__ __forceinline__ void deq8<12>(const u8* b, int sub, float* o) {  // Q4_K
    int e = sub * 8, j = e >> 6, hi = (e >> 5) & 1, l = e & 31, s, m;
    scale_min_k4(2 * j + hi, b + 4, s, m);
    float d = ldh(b) * (float)s, mn = ldh(b + 2) * (float)m;
    const u8* q = b + 16 + 32 * j + l;
    for (int i = 0; i < 8; i++) o[i] = d * (float)(hi ? q[i] >> 4 : q[i] & 0xF) - mn;
}
template <> __device__ __forceinline__ void deq8<13>(const u8* b, int sub, float* o) {  // Q5_K
    int e = sub * 8, j = e >> 6, hi = (e >> 5) & 1, l = e & 31, s, m;
    scale_min_k4(2 * j + hi, b + 4, s, m);
    float d = ldh(b) * (float)s, mn = ldh(b + 2) * (float)m;
    const u8* qh = b + 16 + l;
    const u8* q = b + 48 + 32 * j + l;
    u8 bit = 1 << (2 * j + hi);
    for (int i = 0; i < 8; i++)
        o[i] = d * ((float)(hi ? q[i] >> 4 : q[i] & 0xF) + ((qh[i] & bit) ? 16.0f : 0.0f)) - mn;
}
template <> __device__ __forceinline__ void deq8<14>(const u8* b, int sub, float* o) {  // Q6_K
    int e = sub * 8, n = e >> 7, r = e & 127, qt = r >> 5, l = r & 31;
    const u8* ql = b + 64 * n;
    const u8* qh = b + 128 + 32 * n;
    float d = ldh(b + 208) * (float)((const signed char*)b)[192 + 8 * n + (l >> 4) + 2 * qt];
    for (int i = 0; i < 8; i++) {
        int li = l + i, q;
        switch (qt) {
            case 0: q = (ql[li] & 0xF) | ((qh[li] & 3) << 4); break;
            case 1: q = (ql[li + 32] & 0xF) | (((qh[li] >> 2) & 3) << 4); break;
            case 2: q = (ql[li] >> 4) | (((qh[li] >> 4) & 3) << 4); break;
            default: q = (ql[li + 32] >> 4) | (((qh[li] >> 6) & 3) << 4); break;
        }
        o[i] = d * (float)(q - 32);
    }
}
// IQ1_S / IQ1_M: grid bytes are -1, 0, 1 and the sub-block offset is +-1/8 (IQ1S_DELTA).
__device__ __forceinline__ void iq1_sub(const u8* b, int ib, int l, int& idx, float& dl, bool& neg) {
    // IQ1_M: d is split over the top nibbles of the four scale words.
    u32 s0 = ld16(b + 48), s1 = ld16(b + 50), s2 = ld16(b + 52), s3 = ld16(b + 54);
    float d = h2f((u16)((s0 >> 12) | ((s1 >> 8) & 0xF0) | ((s2 >> 4) & 0xF00) | (s3 & 0xF000)));
    u32 sc = ld16(b + 48 + 2 * (ib / 2)), qh = b[32 + 2 * ib + l / 2] >> (4 * (l & 1));
    dl = d * (float)(2 * ((sc >> (6 * (ib & 1) + 3 * (l >> 1))) & 7) + 1);
    idx = b[4 * ib + l] | ((qh & 7) << 8);
    neg = qh & 8;
}
__device__ __forceinline__ void iq1s_sub(const u8* b, int ib, int l, int& idx, float& dl, bool& neg) {
    u32 qh = ld16(b + 34 + 2 * ib);
    dl = ldh(b) * (float)(2 * ((qh >> 12) & 7) + 1);
    idx = b[2 + 4 * ib + l] | (((qh >> (3 * l)) & 7) << 8);
    neg = qh & 0x8000;
}
template <int T> __device__ __forceinline__ void deq8_iq1(const u8* b, int sub, float* o) {
    int idx; float dl; bool neg;
    if (T == 19) iq1s_sub(b, sub >> 2, sub & 3, idx, dl, neg); else iq1_sub(b, sub >> 2, sub & 3, idx, dl, neg);
    u64 g = iq1s_grid[idx];
    for (int j = 0; j < 8; j++) o[j] = dl * ((float)(signed char)(g >> (8 * j)) + (neg ? -0.125f : 0.125f));
}
template <> __device__ __forceinline__ void deq8<19>(const u8* b, int sub, float* o) { deq8_iq1<19>(b, sub, o); }  // IQ1_S
template <> __device__ __forceinline__ void deq8<29>(const u8* b, int sub, float* o) { deq8_iq1<29>(b, sub, o); }  // IQ1_M
template <> __device__ __forceinline__ void deq8<16>(const u8* b, int sub, float* o) {  // IQ2_XXS
    int ib = sub >> 2, l = sub & 3;
    u32 aux = ld16(b + 6 + 8 * ib) | (ld16(b + 8 + 8 * ib) << 16);
    u64 g = iq2xxs_grid[b[2 + 8 * ib + l]];
    u8 sg = ksigns_iq2xs[(aux >> (7 * l)) & 127];
    float db = ldh(b) * (0.5f + (float)(aux >> 28)) * 0.25f;
    for (int j = 0; j < 8; j++) o[j] = db * (float)((g >> (8 * j)) & 0xFF) * ((sg >> j) & 1 ? -1.0f : 1.0f);
}
template <> __device__ __forceinline__ void deq8<22>(const u8* b, int sub, float* o) {  // IQ2_S
    int ib = sub >> 2, l = sub & 3;
    u64 g = iq2s_grid[b[2 + 4 * ib + l] | ((b[66 + ib] << (8 - 2 * l)) & 0x300)];
    u8 sg = b[34 + 4 * ib + l], sc = b[74 + ib];
    float db = ldh(b) * (0.5f + (float)(l < 2 ? sc & 0xF : sc >> 4)) * 0.25f;
    for (int j = 0; j < 8; j++) o[j] = db * (float)((g >> (8 * j)) & 0xFF) * ((sg >> j) & 1 ? -1.0f : 1.0f);
}
template <> __device__ __forceinline__ void deq8<17>(const u8* b, int sub, float* o) {  // IQ2_XS
    int ib = sub >> 2, l = sub & 3;
    u32 q = ld16(b + 2 + 2 * (4 * ib + l));
    u64 g = iq2xs_grid[q & 511];
    u8 sg = ksigns_iq2xs[q >> 9], sc = b[66 + ib];
    float db = ldh(b) * (0.5f + (float)(l < 2 ? sc & 0xF : sc >> 4)) * 0.25f;
    for (int j = 0; j < 8; j++) o[j] = db * (float)((g >> (8 * j)) & 0xFF) * ((sg >> j) & 1 ? -1.0f : 1.0f);
}
template <> __device__ __forceinline__ void deq8<18>(const u8* b, int sub, float* o) {  // IQ3_XXS
    int ib = sub >> 2, l = sub & 3;
    u32 aux = ld32(b + 66 + 4 * ib);
    float db = ldh(b) * (0.5f + (float)(aux >> 28)) * 0.5f;
    u8 sg = ksigns_iq2xs[(aux >> (7 * l)) & 127];
    u32 g1 = iq3xxs_grid[b[2 + 8 * ib + 2 * l]], g2 = iq3xxs_grid[b[3 + 8 * ib + 2 * l]];
    for (int j = 0; j < 4; j++) {
        o[j] = db * (float)((g1 >> (8 * j)) & 0xFF) * ((sg >> j) & 1 ? -1.0f : 1.0f);
        o[j + 4] = db * (float)((g2 >> (8 * j)) & 0xFF) * ((sg >> (j + 4)) & 1 ? -1.0f : 1.0f);
    }
}
template <> __device__ __forceinline__ void deq8<21>(const u8* b, int sub, float* o) {  // IQ3_S
    int ib = sub >> 2, l = sub & 3;
    u32 hb = b[66 + ib], sg = b[74 + 4 * ib + l];
    float db = ldh(b) * (float)(1 + 2 * ((b[106 + ib / 2] >> (4 * (ib & 1))) & 0xF));
    u32 g1 = iq3s_grid[b[2 + 8 * ib + 2 * l] | ((hb << (8 - 2 * l)) & 256)], g2 = iq3s_grid[b[3 + 8 * ib + 2 * l] | ((hb << (7 - 2 * l)) & 256)];
    for (int j = 0; j < 4; j++) {
        o[j] = db * (float)((g1 >> (8 * j)) & 0xFF) * ((sg >> j) & 1 ? -1.0f : 1.0f);
        o[j + 4] = db * (float)((g2 >> (8 * j)) & 0xFF) * ((sg >> (j + 4)) & 1 ? -1.0f : 1.0f);
    }
}
template <> __device__ __forceinline__ void deq8<23>(const u8* b, int sub, float* o) {  // IQ4_XS
    int ib = sub >> 2, r = (sub & 3) * 8;
    u32 sh = ld16(b + 2);
    int ls = ((b[4 + ib / 2] >> (4 * (ib & 1))) & 0xF) | (((sh >> (2 * ib)) & 3) << 4);
    float dl = ldh(b) * (float)(ls - 32);
    const u8* q = b + 8 + 16 * ib + (r & 15);
    for (int i = 0; i < 8; i++) o[i] = dl * (float)kvalues_iq4nl[r < 16 ? q[i] & 0xF : q[i] >> 4];
}
template <> __device__ __forceinline__ void deq8<20>(const u8* b, int sub, float* o) {  // IQ4_NL, 8 blocks of 18
    const u8* p = b + 18 * (sub >> 2);
    int r = (sub & 3) * 8;
    float d = ldh(p);
    const u8* q = p + 2 + (r & 15);
    for (int i = 0; i < 8; i++) o[i] = d * (float)kvalues_iq4nl[r < 16 ? q[i] & 0xF : q[i] >> 4];
}
// Q4_1 / Q5_1, 8 blocks of 20 / 24 per 256: f16 d, f16 m, (Q5_1: u32 qh,) 16 bytes of nibbles; element j of a block is the
// low nibble of byte j (j < 16) or the high nibble of byte j - 16, plus 16 for bit j of qh; value d q + m.
template <int T> __device__ __forceinline__ const u8* q41_blk(const u8* b, int sub, int& r) {
    r = (sub & 3) * 8;
    return b + (T == 3 ? 20 : 24) * (sub >> 2);
}
template <int T> __device__ __forceinline__ void deq8_q41(const u8* b, int sub, float* o) {
    int r; const u8* p = q41_blk<T>(b, sub, r);
    float d = ldh(p), m = ldh(p + 2);
    u32 qh = T == 7 ? ld32(p + 4) >> r : 0;
    const u8* q = p + (T == 3 ? 4 : 8) + (r & 15);
    for (int i = 0; i < 8; i++) o[i] = d * (float)((r < 16 ? q[i] & 0xF : q[i] >> 4) | (((qh >> i) & 1) << 4)) + m;
}
template <> __device__ __forceinline__ void deq8<3>(const u8* b, int sub, float* o) { deq8_q41<3>(b, sub, o); }  // Q4_1
template <> __device__ __forceinline__ void deq8<7>(const u8* b, int sub, float* o) { deq8_q41<7>(b, sub, o); }  // Q5_1
// Q2_0, 4 blocks of 18 per 256: f16 d, then 2-bit codes (value j at bits 2 (j % 4) of byte j / 4), value (code - 1) d.
__device__ __forceinline__ u32 q2_0_codes(const u8* b, int sub, float& d) {
    const u8* p = b + 18 * (sub >> 3);
    d = ldh(p);
    return ld16(p + 2 + 2 * (sub & 7));
}
template <> __device__ __forceinline__ void deq8<42>(const u8* b, int sub, float* o) {
    float d; u32 q = q2_0_codes(b, sub, d);
    for (int i = 0; i < 8; i++) o[i] = d * (float)((int)((q >> 2 * i) & 3) - 1);
}

// Rows of `cols` values (a multiple of 32, or of the type's block): GEMVs loop over the full super-blocks, then the
// lanes whose 8 values lie inside a partial last one (cols % 256) read it. Only the `_p` kernels (P = true) have that
// tail: full rows keep the plain loop, as the tail cost ~2% of decode.
// Bytes of a row of `cols` values.
#define ROWB(cols, SBB) ((size_t)(cols) * (SBB) / 256)

// One warp per output row; lane `l` covers elements [8l, 8l+8) of every super-block. NT inputs (x + t * xst) share
// each weight load; output t goes to y + t * yst.
template <int T, int SBB, bool P, int NT = 1>
__device__ __forceinline__ void gemv_row(const u8* __restrict__ w, const float* __restrict__ x, float* y, int row, int cols,
                                         int xst = 0, int yst = 0) {
    int lane = threadIdx.x & 31;
    float acc[NT] = {}, v[8];
    auto sb = [&](int s) {
        deq8<T>(w + (size_t)s * SBB, lane, v);
#pragma unroll
        for (int t = 0; t < NT; t++) {
            const float4* xs = (const float4*)(x + (size_t)t * xst + s * 256 + lane * 8);
            float4 a = xs[0], c = xs[1];
            acc[t] += v[0] * a.x + v[1] * a.y + v[2] * a.z + v[3] * a.w + v[4] * c.x + v[5] * c.y + v[6] * c.z + v[7] * c.w;
        }
    };
#pragma unroll 4
    for (int s = 0; s < cols >> 8; s++) sb(s);
    if (P && (cols & 255) > lane * 8) sb(cols >> 8);
#pragma unroll
    for (int t = 0; t < NT; t++) {
        float a = warp_sum(acc[t]);
        if (lane == 0) y[(size_t)t * yst + row] = a;
    }
}

// ---- integer path: 8 weights of a super-block as int8 (two packed words), with dequant value = d * q - m ----
// Activations are quantized per 32 elements to int8 in shared memory, and dot products use dp4a.

__device__ __forceinline__ int pack4(int a, int b, int c, int d) { return (a & 255) | ((b & 255) << 8) | ((c & 255) << 16) | (d << 24); }
__device__ __forceinline__ u32 ldu32(const u8* p) { return *(const u32*)p; }  // 4-byte aligned only
// kvalues_iq4nl of the 8 nibbles of q (llama.cpp's get_int_from_table_16): .x the low nibbles of its 4 bytes, .y
// the high, in byte order. The table lives in 4 registers, so the lookups take no loads.
__device__ __forceinline__ int2 iq4nl_lut(u32 q) {
    const u32 t0 = 0xBFAD9881u, t1 = 0xF6EADDCFu, t2 = 0x26190D01u, t3 = 0x71594535u;  // -127 .. -65, ..., 53 .. 113
    u32 hs = 0x32103210u | ((q & 0x88888888u) >> 1), lo = __byte_perm(t0, t1, q), hi = __byte_perm(t2, t3, q);
    u32 a = __byte_perm(lo, hi, hs);
    lo = __byte_perm(t0, t1, q >> 16); hi = __byte_perm(t2, t3, q >> 16);
    u32 b = __byte_perm(lo, hi, hs >> 16);
    return make_int2((int)__byte_perm(a, b, 0x6420), (int)__byte_perm(a, b, 0x7531));
}
// 8 bytes at 2-aligned p from the three 4-byte words that cover them, shifted when p is not 4-aligned (so the 2
// bytes after p + 8 must be readable). No branch, so the loads of unrolled superblocks can be issued together.
__device__ __forceinline__ uint2 ld8a2(const u8* p) {
    const u8* a = (const u8*)((size_t)p & ~(size_t)3);
    u32 sh = ((size_t)p & 2) * 8, a0 = ldu32(a), a1 = ldu32(a + 4), a2 = ldu32((const u8*)(((size_t)p + 7) & ~(size_t)3));
    return make_uint2(__funnelshift_r(a0, a1, sh), __funnelshift_r(a1, a2, sh));
}
// Byte j of the result is 0xFF when bit j of s is set (j < 4).
__device__ __forceinline__ u32 smask4(u32 s) { return ((s * 0x00204081u) & 0x01010101u) * 0xFFu; }
// Bytes of g negated where s has bits: ~g + 1 per byte, one 32-bit add since no grid byte is 0 (no carries).
__device__ __forceinline__ int apply_signs(u32 g, u32 s) { u32 n = (s * 0x00204081u) & 0x01010101u; return (int)((g ^ (n * 0xFFu)) + n); }

// QI form of scale_min_k4: d and dmin from one 4-byte load at b; with WORDS the 12 scale bytes from three 4-byte
// loads too (faster for the Q4_K output head in gemv_bandwidth, slower for the Q5_K shapes).
// The WORDS form on the four words already loaded: dm, then the scale bytes 0-3, 4-7, 8-11.
__device__ __forceinline__ void k4_dm_w(u32 dm, u32 w0, u32 w1, u32 w2, int j, float& d, float& m) {
    u32 sh = 8 * (j & 3), a = (w0 >> sh) & 255, c = (w1 >> sh) & 255, e = (w2 >> sh) & 255;
    int s, mi;
    if (j < 4) { s = a & 63; mi = c & 63; }
    else { s = (e & 0xF) | ((a >> 6) << 4); mi = (e >> 4) | ((c >> 6) << 4); }
    d = h2f((u16)dm) * (float)s; m = h2f((u16)(dm >> 16)) * (float)mi;
}
template <bool WORDS>
__device__ __forceinline__ void k4_dm(const u8* b, int j, float& d, float& m) {
    u32 dm = ldu32(b); int s, mi;
    if (WORDS) {
        k4_dm_w(dm, ldu32(b + 4), ldu32(b + 8), ldu32(b + 12), j, d, m);
        return;
    } else {
        scale_min_k4(j, b + 4, s, mi);
    }
    d = h2f((u16)dm) * (float)s; m = h2f((u16)(dm >> 16)) * (float)mi;
}
template <int T> struct QI;
template <> struct QI<8> {  // Q8_0, 8 blocks of 34
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        const u8* p = b + 34 * (sub >> 2);
        d = ldh(p);
        const u8* q = p + 2 + (sub & 3) * 8;  // 2-byte aligned
        lo = (int)(ld16(q) | (ld16(q + 2) << 16)); hi = (int)(ld16(q + 4) | (ld16(q + 6) << 16));
    }
};
template <> struct QI<10> {  // Q2_K (84 bytes: rows 4-aligned)
    static constexpr bool MIN = true;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int e = sub * 8, n = e >> 7, r = e & 127, j = r >> 5, r2 = r & 31;
        u8 s = b[n * 8 + j * 2 + (r2 >> 4)];
        u32 dm = ldu32(b + 80);
        d = h2f((u16)dm) * (float)(s & 0xF); m = h2f((u16)(dm >> 16)) * (float)(s >> 4);
        const u8* q = b + 16 + 32 * n + r2;
        lo = (int)((ldu32(q) >> (2 * j)) & 0x03030303u); hi = (int)((ldu32(q + 4) >> (2 * j)) & 0x03030303u);
    }
};
template <> struct QI<11> {  // Q3_K (110 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int e = sub * 8, n = e >> 7, r = e & 127, j = r >> 5, i0 = r & 31, is = n * 8 + j * 2 + (i0 >> 4);
        const u8* sc = b + 96;
        int low = (sc[is & 7] >> (4 * (is >> 3))) & 0xF;
        int hs = (sc[8 + (is & 3)] >> (2 * (is >> 2))) & 3;
        d = ldh(b + 108) * (float)((low | (hs << 4)) - 32);
        const u8 *q = b + 32 + 32 * n + i0, *h = b + i0;
        uint2 Q = ld8a2(q), H = ld8a2(h);
        u32 q0 = Q.x, q1 = Q.y, h0 = H.x, h1 = H.y;
        int qs = 2 * j, hb = 4 * n + j;  // value = 2 low bits + 4 * high bit - 4
        lo = (int)__vsub4(((q0 >> qs) & 0x03030303u) | (((h0 >> hb) & 0x01010101u) << 2), 0x04040404u);
        hi = (int)__vsub4(((q1 >> qs) & 0x03030303u) | (((h1 >> hb) & 0x01010101u) << 2), 0x04040404u);
    }
};
template <> struct QI<12> {  // Q4_K (144 bytes)
    static constexpr bool MIN = true;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int e = sub * 8, j = e >> 6, h = (e >> 5) & 1, l = e & 31;
        k4_dm<true>(b, 2 * j + h, d, m);
        const u8* q = b + 16 + 32 * j + l;
        lo = (int)((ldu32(q) >> (4 * h)) & 0x0F0F0F0Fu); hi = (int)((ldu32(q + 4) >> (4 * h)) & 0x0F0F0F0Fu);
    }
    // get(sub) and get(sub + 1) for an even sub with two 16-byte loads; b must be 16-byte aligned.
    __device__ static void get2(const u8* b, int sub, int& lo0, int& hi0, int& lo1, int& hi1, float& d, float& m) {
        int e = sub * 8, j = e >> 6, h = (e >> 5) & 1, l = e & 31;
        uint4 s = *(const uint4*)b, q = *(const uint4*)(b + 16 + 32 * j + l);
        k4_dm_w(s.x, s.y, s.z, s.w, 2 * j + h, d, m);
        lo0 = (int)((q.x >> (4 * h)) & 0x0F0F0F0Fu); hi0 = (int)((q.y >> (4 * h)) & 0x0F0F0F0Fu);
        lo1 = (int)((q.z >> (4 * h)) & 0x0F0F0F0Fu); hi1 = (int)((q.w >> (4 * h)) & 0x0F0F0F0Fu);
    }
};
template <> struct QI<13> {  // Q5_K (176 bytes)
    static constexpr bool MIN = true;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int e = sub * 8, j = e >> 6, h = (e >> 5) & 1, l = e & 31, bit = 2 * j + h;
        k4_dm<false>(b, bit, d, m);
        const u8* qh = b + 16 + l;
        const u8* q = b + 48 + 32 * j + l;
        lo = (int)(((ldu32(q) >> (4 * h)) & 0x0F0F0F0Fu) | (((ldu32(qh) >> bit) & 0x01010101u) << 4));
        hi = (int)(((ldu32(q + 4) >> (4 * h)) & 0x0F0F0F0Fu) | (((ldu32(qh + 4) >> bit) & 0x01010101u) << 4));
    }
};
template <> struct QI<14> {  // Q6_K (210 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int e = sub * 8, n = e >> 7, r = e & 127, qt = r >> 5, l = r & 31;
        const u8* ql = b + 64 * n + (qt & 1) * 32 + l;
        const u8* qh = b + 128 + 32 * n + l;
        d = ldh(b + 208) * (float)((const signed char*)b)[192 + 8 * n + (l >> 4) + 2 * qt];
        uint2 L = ld8a2(ql), H = ld8a2(qh);
        u32 l0 = L.x, l1 = L.y, h0 = H.x, h1 = H.y;
        int ns = 4 * (qt >> 1), hs = 2 * qt;
        u32 a = ((l0 >> ns) & 0x0F0F0F0Fu) | (((h0 >> hs) & 0x03030303u) << 4);
        u32 c = ((l1 >> ns) & 0x0F0F0F0Fu) | (((h1 >> hs) & 0x03030303u) << 4);
        lo = (int)__vsub4(a, 0x20202020u); hi = (int)__vsub4(c, 0x20202020u);
    }
};
// IQ1: weight = dl * (g +- 1/8) = (dl / 8) * (8 g +- 1), an exact int8 in {-9, -7, -1, 1, 7, 9}.
template <int T> struct QI1 {
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int idx; float dl; bool neg;
        if (T == 19) iq1s_sub(b, sub >> 2, sub & 3, idx, dl, neg); else iq1_sub(b, sub >> 2, sub & 3, idx, dl, neg);
        u64 g = iq1s_grid[idx];
        u32 s = neg ? 0xFFFFFFFFu : 0x01010101u;
        d = dl * 0.125f;
        lo = (int)__vadd4(((u32)g << 3) & 0xF8F8F8F8u, s); hi = (int)__vadd4(((u32)(g >> 32) << 3) & 0xF8F8F8F8u, s);
    }
};
template <> struct QI<19> : QI1<19> {};  // IQ1_S (50 bytes: rows 2-aligned)
template <> struct QI<29> : QI1<29> {};  // IQ1_M (56 bytes)
template <> struct QI<16> {  // IQ2_XXS (66 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 aux = ld16(b + 6 + 8 * ib) | (ld16(b + 8 + 8 * ib) << 16);
        d = ldh(b) * (0.5f + (float)(aux >> 28)) * 0.25f;
        u64 g = iq2xxs_grid[b[2 + 8 * ib + l]];
        u32 sg = ksigns_iq2xs[(aux >> (7 * l)) & 127];
        lo = apply_signs((u32)g, sg & 15); hi = apply_signs((u32)(g >> 32), sg >> 4);
    }
};
template <> struct QI<22> {  // IQ2_S (82 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u64 g = iq2s_grid[b[2 + 4 * ib + l] | ((b[66 + ib] << (8 - 2 * l)) & 0x300)];
        u32 sg = b[34 + 4 * ib + l], sc = b[74 + ib];
        d = ldh(b) * (0.5f + (float)(l < 2 ? sc & 0xF : sc >> 4)) * 0.25f;
        lo = apply_signs((u32)g, sg & 15); hi = apply_signs((u32)(g >> 32), sg >> 4);
    }
};
template <> struct QI<17> {  // IQ2_XS (74 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 q = ld16(b + 2 + 2 * (4 * ib + l));
        u64 g = iq2xs_grid[q & 511];
        u32 sg = ksigns_iq2xs[q >> 9], sc = b[66 + ib];
        d = ldh(b) * (0.5f + (float)(l < 2 ? sc & 0xF : sc >> 4)) * 0.25f;
        lo = apply_signs((u32)g, sg & 15); hi = apply_signs((u32)(g >> 32), sg >> 4);
    }
};
template <> struct QI<18> {  // IQ3_XXS (98 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 aux = ld16(b + 66 + 4 * ib) | (ld16(b + 68 + 4 * ib) << 16);
        d = ldh(b) * (0.5f + (float)(aux >> 28)) * 0.5f;
        u32 sg = ksigns_iq2xs[(aux >> (7 * l)) & 127], qq = ld16(b + 2 + 8 * ib + 2 * l);
        lo = apply_signs(iq3xxs_grid[qq & 255], sg & 15); hi = apply_signs(iq3xxs_grid[qq >> 8], sg >> 4);
    }
};
template <> struct QI<21> {  // IQ3_S (110 bytes: rows 2-aligned)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 hb = b[66 + ib], sg = b[74 + 4 * ib + l], qq = ld16(b + 2 + 8 * ib + 2 * l);
        d = ldh(b) * (float)(1 + 2 * ((b[106 + ib / 2] >> (4 * (ib & 1))) & 0xF));
        lo = apply_signs(iq3s_grid[(qq & 255) | ((hb << (8 - 2 * l)) & 256)], sg & 15);
        hi = apply_signs(iq3s_grid[(qq >> 8) | ((hb << (7 - 2 * l)) & 256)], sg >> 4);
    }
};
template <> struct QI<23> {  // IQ4_XS (136 bytes)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        // Super-blocks are 8-aligned (136 bytes, rows of whole super-blocks): the header (d, scales_h, scales_l) and
        // each lane's 8 quant bytes are one 8-byte load each.
        int ib = sub >> 2, r = (sub & 3) * 8;
        uint2 hd = *(const uint2*)b, w = *(const uint2*)(b + 8 + 16 * ib + (r & 15));
        int ls = ((hd.y >> (4 * ib)) & 0xF) | (((hd.x >> (16 + 2 * ib)) & 3) << 4);
        d = h2f((u16)hd.x) * (float)(ls - 32);
        int2 a = iq4nl_lut(w.x), c = iq4nl_lut(w.y);
        lo = r < 16 ? a.x : a.y; hi = r < 16 ? c.x : c.y;
    }
};
template <> struct QI<42> {  // Q2_0
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        u32 q = q2_0_codes(b, sub, d);
        // Spread the 8 codes to bytes, then subtract 1 per byte (code 0 wraps to 0xFF = -1).
        u32 a = (q & 3) | ((q << 6) & 0x300) | ((q << 12) & 0x30000) | ((q << 18) & 0x3000000), c = q >> 8;
        c = (c & 3) | ((c << 6) & 0x300) | ((c << 12) & 0x30000) | ((c << 18) & 0x3000000);
        lo = (int)__vsub4(a, 0x01010101u); hi = (int)__vsub4(c, 0x01010101u);
    }
};
template <int T> struct QI41 {  // Q4_1 (T = 3, 20 bytes) and Q5_1 (T = 7, 24 bytes): rows 4-aligned
    static constexpr bool MIN = true;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int r; const u8* p = q41_blk<T>(b, sub, r);
        u32 dm = ldu32(p);
        d = h2f((u16)dm); m = -h2f((u16)(dm >> 16));  // the kernels subtract m times the activation sum
        const u8* q = p + (T == 3 ? 4 : 8) + (r & 15);
        int sh = r < 16 ? 0 : 4;
        lo = (int)((ldu32(q) >> sh) & 0x0F0F0F0Fu); hi = (int)((ldu32(q + 4) >> sh) & 0x0F0F0F0Fu);
        if (T == 7) {
            u32 qh = ldu32(p + 4) >> r;
            lo |= (int)((((qh & 15) * 0x00204081u) & 0x01010101u) << 4);
            hi |= (int)(((((qh >> 4) & 15) * 0x00204081u) & 0x01010101u) << 4);
        }
    }
};
template <> struct QI<3> : QI41<3> {};
template <> struct QI<7> : QI41<7> {};
// Q4_0 (T = 2, 18 bytes) and Q5_0 (T = 6, 22: f16 d, u32 qh, nibbles): blocks 2-byte aligned (ld16 only); the unsigned
// codes as in Q4_1 / Q5_1, minus 8 (16) per byte.
template <int T> struct QI40 {
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        const u8* p = b + (T == 2 ? 18 : 22) * (sub >> 2);
        int r = (sub & 3) * 8, sh = r < 16 ? 0 : 4;
        d = ldh(p);
        const u8* q = p + (T == 2 ? 2 : 6) + (r & 15);
        u32 a = ((ld16(q) | (ld16(q + 2) << 16)) >> sh) & 0x0F0F0F0Fu, c = ((ld16(q + 4) | (ld16(q + 6) << 16)) >> sh) & 0x0F0F0F0Fu;
        if (T == 6) {
            u32 qh = (ld16(p + 2) | (ld16(p + 4) << 16)) >> r;
            a |= (((qh & 15) * 0x00204081u) & 0x01010101u) << 4; c |= ((((qh >> 4) & 15) * 0x00204081u) & 0x01010101u) << 4;
        }
        u32 off = T == 2 ? 0x08080808u : 0x10101010u;
        lo = (int)__vsub4(a, off); hi = (int)__vsub4(c, off);
    }
};
template <> struct QI<2> : QI40<2> {};
template <> struct QI<6> : QI40<6> {};
template <int T> __device__ __forceinline__ void deq8_q40(const u8* b, int sub, float* o) {
    int lo, hi; float d, m;
    QI40<T>::get(b, sub, lo, hi, d, m);
    for (int i = 0; i < 8; i++) o[i] = d * (float)(signed char)((i < 4 ? lo : hi) >> (8 * (i & 3)));
}
template <> __device__ __forceinline__ void deq8<2>(const u8* b, int sub, float* o) { deq8_q40<2>(b, sub, o); }  // Q4_0
template <> __device__ __forceinline__ void deq8<6>(const u8* b, int sub, float* o) { deq8_q40<6>(b, sub, o); }  // Q5_0
template <> struct QI<20> {  // IQ4_NL, 8 blocks of 18 (2-byte aligned: ld16 only)
    static constexpr bool MIN = false;
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        const u8* p = b + 18 * (sub >> 2);
        int r = (sub & 3) * 8;
        d = ldh(p);
        const u8* q = p + 2 + (r & 15);
        int2 a = iq4nl_lut(ld16(q) | (ld16(q + 2) << 16)), c = iq4nl_lut(ld16(q + 4) | (ld16(q + 6) << 16));
        lo = r < 16 ? a.x : a.y; hi = r < 16 ? c.x : c.y;
    }
};

#ifndef LLAMA_Q8
#define LLAMA_Q8 0
#endif
// q8_K scale over the lanes that share one 256-block (all 32 for 8 values per lane, the 16 of a half-warp for 16):
// lane holds candidate value v at index i (largest |v| of its values, lowest index); the block keeps the largest
// |v|, lowest index on ties, as llama.cpp's quantize_row_q8_K does. id = -127 / v, d = 1 / id.
// |id v| <= 127 for every value of the block, so llama.cpp's clamp to 127 never fires and is left out.
template <int LANES = 32>
__device__ __forceinline__ void q8k_scale(float v, int i, float& d, float& id) {
    unsigned mask = __activemask();  // quant_q8 can leave a half-warp idle
    #pragma unroll
    for (int o = 1; o < LANES; o <<= 1) {
        float ov = __shfl_xor_sync(mask, v, o); int oi = __shfl_xor_sync(mask, i, o);
        if (fabsf(ov) > fabsf(v) || (fabsf(ov) == fabsf(v) && oi < i)) { v = ov; i = oi; }
    }
    id = v != 0.0f ? -127.0f / v : 0.0f;
    d = v != 0.0f ? 1.0f / id : 0.0f;
}

// Quantize the 8 values a, c at x + i into qs + i and, by the lane with i % 32 == 0, its scale into xd[i / 32]; the
// warp's 32 lanes cover 256 consecutive values (or the lanes in m, whole groups of 4).
__device__ __forceinline__ void quant8(float4 a, float4 c, int i, signed char* qs, float* xd, unsigned m = 0xffffffff) {
    float mx = fmaxf(fmaxf(fmaxf(fabsf(a.x), fabsf(a.y)), fmaxf(fabsf(a.z), fabsf(a.w))),
                     fmaxf(fmaxf(fabsf(c.x), fabsf(c.y)), fmaxf(fabsf(c.z), fabsf(c.w))));
#if LLAMA_Q8
    float d, id;
    {  // llama.cpp q8_K: one scale per 256 (the warp), -127 / the signed value of largest magnitude
        float sv = 0.f; int si = 1 << 30;
        float vv[8] = {a.x, a.y, a.z, a.w, c.x, c.y, c.z, c.w};
        for (int j = 0; j < 8; j++) if (fabsf(vv[j]) == mx && si > i + j) { sv = vv[j]; si = i + j; }
        q8k_scale(sv, si, d, id);
    }
#else
    mx = fmaxf(mx, __shfl_xor_sync(m, mx, 1));
    mx = fmaxf(mx, __shfl_xor_sync(m, mx, 2));
    float d = mx / 127.0f, id = mx > 0.0f ? 127.0f / mx : 0.0f;
#endif
    int2 q = make_int2(pack4(__float2int_rn(a.x * id), __float2int_rn(a.y * id), __float2int_rn(a.z * id), __float2int_rn(a.w * id)),
                       pack4(__float2int_rn(c.x * id), __float2int_rn(c.y * id), __float2int_rn(c.z * id), __float2int_rn(c.w * id)));
    *(int2*)(qs + i) = q;
    if ((threadIdx.x & 3) == 0) xd[i >> 5] = d;
}

// Quantize x[0, n) into shared int8 qs[n] and per-32 scales xd[n / 32]; the whole block participates.
// n is a multiple of 32: with n % 256 != 0 the lanes of a warp past n idle in whole groups of 4 (a ballot mask; the
// full-mask path is kept apart, as a variable shuffle mask costs ~2% of decode).
template <bool P = true>
__device__ __forceinline__ void quant_x(const float* __restrict__ x, int n, signed char* qs, float* xd) {
    if (P && (n & 255)) {
        for (int i0 = 0; i0 < n; i0 += blockDim.x * 8) {
            int i = i0 + threadIdx.x * 8;
            unsigned m = __ballot_sync(0xffffffff, i < n);
            if (i < n) quant8(*(const float4*)(x + i), *(const float4*)(x + i + 4), i, qs, xd, m);
        }
    } else {
        for (int i = threadIdx.x * 8; i < n; i += blockDim.x * 8)
            quant8(*(const float4*)(x + i), *(const float4*)(x + i + 4), i, qs, xd);
    }
    __syncthreads();
}

// quant_xq: quant_x of nt rows (row t at x + t * xs, block t) into the gemvn shared-memory layout at out: all int8 rows, then
// all scales. gemvn and moe_gemv read it in place of quantizing x per block.
extern "C" __global__ void quant_xq(const float* x, int xs, int n, signed char* out) {
    int t = blockIdx.x;
    quant_x(x + (size_t)t * xs, n, out + (size_t)t * n, (float*)(out + (size_t)gridDim.x * n) + t * (n / 32));
}

// IQ2_XS and IQ3_XXS for the MoE GEMV with their grid and sign tables in shared memory: each lane looks up random
// entries, which shared memory serves in fewer passes than L1.
__shared__ u64 s_iq2xs_grid[512];
__shared__ u32 s_iq3xxs_grid[256];
__shared__ u8 s_ksigns_iq2xs[128];
template <int T> struct QS : QI<T> { static constexpr bool SH = false; __device__ static void load() {} };
__device__ __forceinline__ void load_ksigns() { for (int i = threadIdx.x; i < 128; i += blockDim.x) s_ksigns_iq2xs[i] = ksigns_iq2xs[i]; }
template <> struct QS<17> : QI<17> {
    static constexpr bool SH = true;
    __device__ static void load() { for (int i = threadIdx.x; i < 512; i += blockDim.x) s_iq2xs_grid[i] = iq2xs_grid[i]; load_ksigns(); }
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 q = ld16(b + 2 + 2 * (4 * ib + l));
        u64 g = s_iq2xs_grid[q & 511];
        u32 sg = s_ksigns_iq2xs[q >> 9], sc = b[66 + ib];
        d = ldh(b) * (0.5f + (float)(l < 2 ? sc & 0xF : sc >> 4)) * 0.25f;
        lo = apply_signs((u32)g, sg & 15); hi = apply_signs((u32)(g >> 32), sg >> 4);
    }
};
template <> struct QS<18> : QI<18> {
    static constexpr bool SH = true;
    __device__ static void load() { for (int i = threadIdx.x; i < 256; i += blockDim.x) s_iq3xxs_grid[i] = iq3xxs_grid[i]; load_ksigns(); }
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 aux = ld16(b + 66 + 4 * ib) | (ld16(b + 68 + 4 * ib) << 16);
        d = ldh(b) * (0.5f + (float)(aux >> 28)) * 0.5f;
        u32 sg = s_ksigns_iq2xs[(aux >> (7 * l)) & 127], qq = ld16(b + 2 + 8 * ib + 2 * l);
        lo = apply_signs(s_iq3xxs_grid[qq & 255], sg & 15); hi = apply_signs(s_iq3xxs_grid[qq >> 8], sg >> 4);
    }
};

__shared__ u32 s_iq3s_grid[512];
template <> struct QS<21> : QI<21> {
    static constexpr bool SH = true;
    __device__ static void load() { for (int i = threadIdx.x; i < 512; i += blockDim.x) s_iq3s_grid[i] = iq3s_grid[i]; }
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u32 hb = b[66 + ib], sg = b[74 + 4 * ib + l], qq = ld16(b + 2 + 8 * ib + 2 * l);
        d = ldh(b) * (float)(1 + 2 * ((b[106 + ib / 2] >> (4 * (ib & 1))) & 0xF));
        lo = apply_signs(s_iq3s_grid[(qq & 255) | ((hb << (8 - 2 * l)) & 256)], sg & 15);
        hi = apply_signs(s_iq3s_grid[(qq >> 8) | ((hb << (7 - 2 * l)) & 256)], sg >> 4);
    }
};
__shared__ u64 s_iq2s_grid[1024];
template <> struct QS<22> : QI<22> {
    static constexpr bool SH = true;
    __device__ static void load() { for (int i = threadIdx.x; i < 1024; i += blockDim.x) s_iq2s_grid[i] = iq2s_grid[i]; }
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        int ib = sub >> 2, l = sub & 3;
        u64 g = s_iq2s_grid[b[2 + 4 * ib + l] | ((b[66 + ib] << (8 - 2 * l)) & 0x300)];
        u32 sg = b[34 + 4 * ib + l], sc = b[74 + ib];
        d = ldh(b) * (0.5f + (float)(l < 2 ? sc & 0xF : sc >> 4)) * 0.25f;
        lo = apply_signs((u32)g, sg & 15); hi = apply_signs((u32)(g >> 32), sg >> 4);
    }
};

#if GEMV_LOADW
// M2-T5 candidate (`STRATA_GEMV_LOADW=1`): the Q4_K GEMV reads its 16-byte header/scale block as one vector load,
// where `QI<12>::get` issues four 4-byte ones. A Q4_K row is 144 B (a multiple of 16), so the row pointer decides:
// 16-aligned base -> one `ld.global.v4.b32`, otherwise the byte-for-byte original. The four words are the same, so
// the result is bit-identical; only the GEMV path changes (`gemv_row_q` takes `QS<T>`, the prefill GEMM calls
// `QI<T>::get`/`get2` directly).
template <> struct QS<12> : QI<12> {
    static constexpr bool SH = false;
    __device__ static void load() {}
    __device__ static void get(const u8* b, int sub, int& lo, int& hi, float& d, float& m) {
        if (((size_t)b & 15) == 0) {
            int e = sub * 8, j = e >> 6, h = (e >> 5) & 1, l = e & 31;
            uint4 s = *(const uint4*)b;
            k4_dm_w(s.x, s.y, s.z, s.w, 2 * j + h, d, m);
            const u8* q = b + 16 + 32 * j + l;
            lo = (int)((ldu32(q) >> (4 * h)) & 0x0F0F0F0Fu);
            hi = (int)((ldu32(q + 4) >> (4 * h)) & 0x0F0F0F0Fu);
        } else QI<12>::get(b, sub, lo, hi, d, m);
    }
};
#endif

template <int T, int SBB, bool P, class Q = QI<T>>
__device__ __forceinline__ void gemv_row_q(const u8* __restrict__ w, const signed char* qs, const float* xd, float* y, int row, int cols) {
    int lane = threadIdx.x & 31;
    float acc = 0.0f;
    auto sb = [&](int s) {
        int lo, hi; float d, m = 0.0f;
        Q::get(w + (size_t)s * SBB, lane, lo, hi, d, m);
        int2 xq = *(const int2*)(qs + s * 256 + lane * 8);
        float dx = xd[s * 8 + (lane >> 2)];
        acc += d * dx * (float)__dp4a(lo, xq.x, __dp4a(hi, xq.y, 0));
        if (QI<T>::MIN) acc -= m * dx * (float)__dp4a(0x01010101, xq.x, __dp4a(0x01010101, xq.y, 0));
    };
#pragma unroll 4
    for (int s = 0; s < cols >> 8; s++) sb(s);
    if (P && (cols & 255) > lane * 8) sb(cols >> 8);
    acc = warp_sum(acc);
    if (lane == 0) y[row] = acc;
}

// gemv_row_q for nt <= 4 inputs: x t is qs + t * cols with scales xd + t * cols / 32; y t is y + t * ys.
template <int T, int SBB, bool P, int NT>
__device__ __forceinline__ void gemv_row_qn(const u8* __restrict__ w, const signed char* qs, const float* xd, float* y, int ys,
                                            int row, int cols) {
    int lane = threadIdx.x & 31;
    float acc[NT] = {};
    auto sb = [&](int s) {
        int lo, hi; float d, m = 0.0f;
        QI<T>::get(w + (size_t)s * SBB, lane, lo, hi, d, m);
#pragma unroll
        for (int t = 0; t < NT; t++) {
            int2 xq = *(const int2*)(qs + t * cols + s * 256 + lane * 8);
            float dx = xd[t * (cols >> 5) + s * 8 + (lane >> 2)];
            acc[t] += d * dx * (float)__dp4a(lo, xq.x, __dp4a(hi, xq.y, 0));
            if (QI<T>::MIN) acc[t] -= m * dx * (float)__dp4a(0x01010101, xq.x, __dp4a(0x01010101, xq.y, 0));
        }
    };
#pragma unroll 4
    for (int s = 0; s < cols >> 8; s++) sb(s);
    if (P && (cols & 255) > lane * 8) sb(cols >> 8);
#pragma unroll
    for (int t = 0; t < NT; t++) {
        float a = warp_sum(acc[t]);
        if (lane == 0) y[(size_t)t * ys + row] = a;
    }
}

#define FTYPES(X) X(0, f32, 1024) X(30, bf16, 512)
#define ITYPES(X) X(8, q8_0, 272) X(10, q2_k, 84) X(11, q3_k, 110) X(12, q4_k, 144) X(13, q5_k, 176) X(14, q6_k, 210) \
    X(19, iq1_s, 50) X(29, iq1_m, 56) X(16, iq2_xxs, 66) X(17, iq2_xs, 74) X(22, iq2_s, 82) X(18, iq3_xxs, 98) X(21, iq3_s, 110) X(23, iq4_xs, 136) X(20, iq4_nl, 144) X(42, q2_0, 72) X(2, q4_0, 144) X(6, q5_0, 176) \
    X(3, q4_1, 160) X(7, q5_1, 192)
#define QTYPES(X) FTYPES(X) ITYPES(X)

#define DEF_DEQUANT(T, NAME, SBB)                                                                                 \
    extern "C" __global__ void dequant_##NAME(const u8* w, float* out, int cols) {                                \
        const u8* r = w + blockIdx.x * ROWB(cols, SBB);                                                         \
        for (int s = threadIdx.x; s < cols / 8; s += blockDim.x)                                                \
            deq8<T>(r + (size_t)(s >> 5) * SBB, s & 31, out + (size_t)blockIdx.x * cols + s * 8);               \
    }
QTYPES(DEF_DEQUANT)

// Float types read x directly.
#define DEF_FGEMV(T, NAME, SBB) DEF_FGEMV_(T, NAME, SBB, false) DEF_FGEMV_(T, NAME##_p, SBB, true)
#define DEF_FGEMV_(T, NAME, SBB, P)                                                                                   \
    extern "C" __global__ void gemv_##NAME(const u8* w, const float* x, float* y, int rows, int cols, int,     \
                                           const signed char*, long long w2, long long y2, int rows2) {        \
        int row = (blockIdx.x * blockDim.x + threadIdx.x) >> 5;                                                 \
        w += blockIdx.z * w2; y = (float*)((char*)y + blockIdx.z * y2); if (blockIdx.z) rows = rows2;           \
        if (row < rows) gemv_row<T, SBB, P>(w + row * ROWB(cols, SBB), x, y, row, cols);                         \
    }                                                                                                           \
    extern "C" __global__ void moe_gemv_##NAME(const u8* w, const int* ids, long long stride, const float* x,  \
                                               int x_stride, int xg, float* y, int rows, int cols, int,         \
                                               long long w2, long long y2) {                                   \
        int row = (blockIdx.x * blockDim.x + threadIdx.x) >> 5, k = blockIdx.y;                                 \
        w += blockIdx.z * w2; y = (float*)((char*)y + blockIdx.z * y2);                                         \
        if (row < rows && ids[k] >= 0)                                                                          \
            gemv_row<T, SBB, P>(w + ids[k] * stride + row * ROWB(cols, SBB), x + (size_t)(k / xg) * x_stride,    \
                             y + (size_t)k * rows, row, cols);                                                   \
    }                                                                                                           \
    extern "C" __global__ void gemvn_##NAME(const u8* w, const float* x, int xs, float* y, int ys, int rows, int cols, \
                                            int, int nt, const signed char*, long long w2, long long y2, int rows2) { \
        int row = (blockIdx.x * blockDim.x + threadIdx.x) >> 5;                                                 \
        w += blockIdx.z * w2; y = (float*)((char*)y + blockIdx.z * y2); if (blockIdx.z) rows = ys = rows2;      \
        if (row >= rows) return;                                                                                \
        const u8* wr = w + row * ROWB(cols, SBB);                                                             \
        if (nt == 2) gemv_row<T, SBB, P, 2>(wr, x, y, row, cols, xs, ys);                                           \
        else if (nt == 3) gemv_row<T, SBB, P, 3>(wr, x, y, row, cols, xs, ys);                                      \
        else if (nt == 4) gemv_row<T, SBB, P, 4>(wr, x, y, row, cols, xs, ys);                                      \
        else gemv_row<T, SBB, P, 1>(wr, x, y, row, cols, xs, ys);                                                   \
    }
FTYPES(DEF_FGEMV)

// Quantized types: dynamic shared memory holds x as int8 (cols bytes) then its scales ((cols >> 5) floats).
// Each block covers (warps per block) * rpw rows (warp w: rows w, w + nw, ...) so small matrices amortize the x
// quantization; nw = blockDim.x / 32, so STRATA_GEMV_BLOCK (128/256/512) only changes the launch shape.
// moe_gemv: grid.y = k; weights at w + ids[k] * stride (skipped when ids[k] < 0), input x + (k / xg) * x_stride,
// output y + k * rows. grid.z = 2 also runs a second matrix at byte offset w2 into output at byte offset y2.
#define DEF_IGEMV(T, NAME, SBB) DEF_IGEMV_(T, NAME, SBB, false) DEF_IGEMV_(T, NAME##_p, SBB, true)
#define DEF_IGEMV_(T, NAME, SBB, P)                                                                                   \
    extern "C" __global__ void gemv_##NAME(const u8* w, const float* x, float* y, int rows, int cols, int rpw,   \
                                           const signed char* xq, long long w2, long long y2, int rows2) {     \
        extern __shared__ __align__(16) signed char sx[];                                                       \
        const signed char* xs = xq ? xq : sx;                                                                   \
        const float* xd = (const float*)(xs + cols);                                                       \
        QS<T>::load();                                                                                          \
        if (!xq) quant_x<P>(x, cols, sx, (float*)(sx + cols));                                           \
        else if (QS<T>::SH) __syncthreads();                                                                    \
        w += blockIdx.z * w2; y = (float*)((char*)y + blockIdx.z * y2); if (blockIdx.z) rows = rows2;           \
        int nw = blockDim.x >> 5, warp = threadIdx.x >> 5;                                                      \
        int r0 = blockIdx.x * nw * rpw + warp, r1 = min(rows, r0 - warp + nw * rpw);                            \
        for (int row = r0; row < r1; row += nw) gemv_row_q<T, SBB, P, QS<T>>(w + row * ROWB(cols, SBB), xs, xd, y, row, cols); \
    }                                                                                                           \
    extern "C" __global__ void moe_gemv_##NAME(const u8* w, const int* ids, long long stride, const float* x,  \
                                               int x_stride, int xg, float* y, int rows, int cols, int rpw,      \
                                               long long w2, long long y2, const signed char* xq) {            \
        extern __shared__ __align__(16) signed char sx[];                                                       \
        int k = blockIdx.y, e = ids[k];                                                                         \
        if (e < 0) return;                                                                                      \
        QS<T>::load();                                                                                          \
        const signed char* xs; const float* xd;                                                                 \
        if (xq) {                                                                                               \
            int t = k / xg;                                                                                     \
            xs = xq + (size_t)t * cols;                                                                    \
            xd = (const float*)(xq + (size_t)gridDim.y / xg * cols) + t * (cols >> 5);                         \
            if (QS<T>::SH) __syncthreads();                                                                     \
        } else {                                                                                                \
            quant_x<P>(x + (size_t)(k / xg) * x_stride, cols, sx, (float*)(sx + cols));                  \
            xs = sx; xd = (const float*)(sx + cols);                                                       \
        }                                                                                                       \
        const u8* we = w + e * stride + blockIdx.z * w2;                                                        \
        y = (float*)((char*)y + blockIdx.z * y2);                                                               \
        int nw = blockDim.x >> 5, warp = threadIdx.x >> 5;                                                      \
        int r0 = blockIdx.x * nw * rpw + warp, r1 = min(rows, r0 - warp + nw * rpw);                            \
        for (int row = r0; row < r1; row += nw)                                                                \
            gemv_row_q<T, SBB, P, QS<T>>(we + row * ROWB(cols, SBB), xs, xd, y + (size_t)k * rows, row, cols);    \
    }
ITYPES(DEF_IGEMV)

// gemvn: y[t] = W x[t] for t < nt <= 4 (x t at x + t * xs, y t at y + t * ys); each weight block is read once.
// grid.z = 2 also runs a second matrix of rows2 <= rows rows at byte offset w2 into output at byte offset y2, whose
// token stride is rows2 (gemv and float types too).
#define DEF_IGEMVN(T, NAME, SBB) DEF_IGEMVN_(T, NAME, SBB, false) DEF_IGEMVN_(T, NAME##_p, SBB, true)
#define DEF_IGEMVN_(T, NAME, SBB, P)                                                                                  \
    extern "C" __global__ void gemvn_##NAME(const u8* w, const float* x, int xs_, float* y, int ys, int rows, int cols, \
                                            int rpw, int nt, const signed char* xq, long long w2, long long y2, \
                                            int rows2) {                                                        \
        extern __shared__ __align__(16) signed char sx[];                                                       \
        const signed char* xs = xq ? xq : sx;                                                                   \
        w += blockIdx.z * w2; y = (float*)((char*)y + blockIdx.z * y2); if (blockIdx.z) rows = ys = rows2;      \
        const float* xd = (const float*)(xs + nt * cols);                                                  \
        if (!xq) for (int t = 0; t < nt; t++)                                                                   \
            quant_x<P>(x + (size_t)t * xs_, cols, sx + t * cols, (float*)(sx + nt * cols) + t * (cols >> 5)); \
        int nw = blockDim.x >> 5, warp = threadIdx.x >> 5;                                                      \
        int r0 = blockIdx.x * nw * rpw + warp, r1 = min(rows, r0 - warp + nw * rpw);                            \
        for (int row = r0; row < r1; row += nw) {                                                               \
            const u8* wr = w + row * ROWB(cols, SBB);                                                         \
            if (nt == 2) gemv_row_qn<T, SBB, P, 2>(wr, xs, xd, y, ys, row, cols);                                    \
            else if (nt == 3) gemv_row_qn<T, SBB, P, 3>(wr, xs, xd, y, ys, row, cols);                               \
            else if (nt == 4) gemv_row_qn<T, SBB, P, 4>(wr, xs, xd, y, ys, row, cols);                               \
            else gemv_row_qn<T, SBB, P, 1>(wr, xs, xd, y, ys, row, cols);                                            \
        }                                                                                                       \
    }
ITYPES(DEF_IGEMVN)

// ---- prefill GEMM: Y[m, n] = sum_k X[m, k] W[n, k] on tensor cores (fp16 inputs, fp32 accumulate) ----
// Work is a list of tiles of up to GEMM_BM consecutive positions m0 .. m0 + cnt, each with its own weight matrix (so one
// launch covers every expert of a MoE layer). X row of position m is xrow[m] (or m when xrow is null).
// grid = (ceil(rows / 64), tiles), block = 2 * GEMM_BM.
struct GemmTile { const u8* w; int m0, cnt; };

__device__ __forceinline__ u32 ld_s32(const u16* p) { return *(const u32*)p; }
// Four 8x8 f16 matrices from shared memory; lane l gives the row address for matrix l / 8 (.trans transposes each).
//
// sm_75+ uses ldmatrix.x4. On sm_70 (Volta) ldmatrix does not exist, so the same fragments are loaded per lane with
// plain shared loads. `p` is the lane's own matrix origin (lane l addresses matrix l / 8, row l & 7); its position
// relative to the four matrices depends on the matrix order `RM` used by the call site. `my = l >> 3`, `mr = l & 7`,
// and relative to the lane's own matrix origin:
//
//   RM = true : own_row = (my & 1) * 8, own_col = (my >> 1) * 8;  m_row = (m & 1) * 8, m_col = (m >> 1) * 8
//   RM = false: own_row = (my >> 1) * 8, own_col = (my & 1) * 8;  m_row = (m >> 1) * 8, m_col = (m & 1) * 8
//
// ldmatrix register m of lane l holds matrix m, row l >> 2, columns 2*(l & 3), 2*(l & 3) + 1 (low half first):
//   plain:  addr(m) = p + (m_row + (l >> 2) - own_row - mr) * PQ + (m_col + 2*(l & 3) - own_col)
//   trans:  the matrix is transposed, so register m of lane l holds matrix m rows 2*(l & 3), 2*(l & 3) + 1 at
//           column l >> 2. Those two halves are one row apart, so two 16-bit loads:
//   trans:  addr(m) = p + (m_row + 2*(l & 3) - own_row - mr) * PQ + (m_col + (l >> 2) - own_col), high at +PQ
//
// The loads are warp-synchronous plain loads (no __syncwarp()): every lane reads only elements it will own, and the
// tile is published by the __syncthreads() before the loop. The plain case is a 4-byte load because the two halves
// are adjacent and the address is even; the transposed halves are not contiguous and use 16-bit loads.
template <int PQ, bool RM>
__device__ __forceinline__ void ldsm4(u32* r, const u16* p) {
#if __CUDA_ARCH__ < 750
    int l = threadIdx.x & 31, my = l >> 3, mr = l & 7;
    int own_row = (RM ? (my & 1) : (my >> 1)) * 8, own_col = (RM ? (my >> 1) : (my & 1)) * 8;
    int row = (l >> 2) - own_row - mr, col = 2 * (l & 3) - own_col;
#pragma unroll
    for (int m = 0; m < 4; m++) {
        int m_row = (RM ? (m & 1) : (m >> 1)) * 8, m_col = (RM ? (m >> 1) : (m & 1)) * 8;
        unsigned a = (unsigned)__cvta_generic_to_shared(p + (m_row + row) * PQ + m_col + col);
        asm("ld.shared.b32 %0, [%1];" : "=r"(r[m]) : "r"(a));
    }
#else
    unsigned a = (unsigned)__cvta_generic_to_shared(p);
    asm volatile("ldmatrix.sync.aligned.m8n8.x4.shared.b16 {%0, %1, %2, %3}, [%4];"
                 : "=r"(r[0]), "=r"(r[1]), "=r"(r[2]), "=r"(r[3]) : "r"(a));
#endif
}
template <int PQ, bool RM>
__device__ __forceinline__ void ldsm4t(u32* r, const u16* p) {
#if __CUDA_ARCH__ < 750
    int l = threadIdx.x & 31, my = l >> 3, mr = l & 7;
    int own_row = (RM ? (my & 1) : (my >> 1)) * 8, own_col = (RM ? (my >> 1) : (my & 1)) * 8;
    int row = 2 * (l & 3) - own_row - mr, col = (l >> 2) - own_col;
#pragma unroll
    for (int m = 0; m < 4; m++) {
        int m_row = (RM ? (m & 1) : (m >> 1)) * 8, m_col = (RM ? (m >> 1) : (m & 1)) * 8;
        unsigned a = (unsigned)__cvta_generic_to_shared(p + (m_row + row) * PQ + m_col + col);
        unsigned short lo, hi;
        asm("ld.shared.u16 %0, [%1];" : "=h"(lo) : "r"(a));
        asm("ld.shared.u16 %0, [%1];" : "=h"(hi) : "r"(a + 2 * PQ));
        r[m] = (u32)lo | ((u32)hi << 16);
    }
#else
    unsigned a = (unsigned)__cvta_generic_to_shared(p);
    asm volatile("ldmatrix.sync.aligned.m8n8.x4.trans.shared.b16 {%0, %1, %2, %3}, [%4];"
                 : "=r"(r[0]), "=r"(r[1]), "=r"(r[2]), "=r"(r[3]) : "r"(a));
#endif
}
__device__ __forceinline__ void mma16816(float* c, u32 a0, u32 a1, u32 a2, u32 a3, u32 b0, u32 b1) {
#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ < 800
#if __CUDA_ARCH__ >= 750
    // Turing (sm_75) has no m16n8k16 f16 mma: the same product is two m16n8k8 steps, k = 0..7 and k = 8..15
    // (the a0/a1, a2/a3 and b0, b1 fragments are those half-K fragments of the k16 layout).
    asm volatile("mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5}, {%6}, {%0,%1,%2,%3};"
                 : "+f"(c[0]), "+f"(c[1]), "+f"(c[2]), "+f"(c[3]) : "r"(a0), "r"(a1), "r"(b0));
    asm volatile("mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5}, {%6}, {%0,%1,%2,%3};"
                 : "+f"(c[0]), "+f"(c[1]), "+f"(c[2]), "+f"(c[3]) : "r"(a2), "r"(a3), "r"(b1));
#else
    // D[16,8] += A[16,16] * B[16,8] on CUDA cores. mma.sync.aligned.m16n8k16 is sm_80+ (unlike ldmatrix, which is
    // sm_75+, hence the different guard). Lane l = 4*g + t (g = l >> 2, t = l & 3) owns A rows g / g+8 at the
    // k-halves {2t, 2t+1, 2t+8, 2t+9}, and B column g at those same k. The four accumulators are sums over all 16
    // k, so A of rows g / g+8 comes from lanes 4*g + tp and B of columns 2t / 2t+1 from lanes 4*n + tp
    // (n = 2t, 2t+1), i.e. 8*t + tp and 8*t + 4 + tp. Accumulation order is k = 0,1,8,9, 2,3,10,11,
    // 4,5,12,13, 6,7,14,15 (tp = 0..3): the only difference vs the tensor core is f32 summation order, the f16
    // inputs are the same values. Every lane computes every accumulator, so this must stay in warp-uniform
    // control flow: gemm_q's `wm < tl.cnt` (wm is per warp) and attn_prefill_t's `!skip` (`__any_sync`) are.
    int l = threadIdx.x & 31, g = l >> 2, t = l & 3;
#pragma unroll
    for (int tp = 0; tp < 4; tp++) {
        u32 sa0 = __shfl_sync(0xffffffff, a0, 4 * g + tp);      // A[g][2tp], A[g][2tp+1]
        u32 sa2 = __shfl_sync(0xffffffff, a2, 4 * g + tp);      // A[g][2tp+8], A[g][2tp+9]
        u32 sa1 = __shfl_sync(0xffffffff, a1, 4 * g + tp);      // A[g+8][2tp], A[g+8][2tp+1]
        u32 sa3 = __shfl_sync(0xffffffff, a3, 4 * g + tp);      // A[g+8][2tp+8], A[g+8][2tp+9]
        u32 sb0 = __shfl_sync(0xffffffff, b0, 8 * t + tp);      // B[2tp][2t], B[2tp+1][2t]
        u32 sb1 = __shfl_sync(0xffffffff, b1, 8 * t + tp);      // B[2tp+8][2t], B[2tp+9][2t]
        u32 sc0 = __shfl_sync(0xffffffff, b0, 8 * t + 4 + tp);  // B[2tp][2t+1], B[2tp+1][2t+1]
        u32 sc1 = __shfl_sync(0xffffffff, b1, 8 * t + 4 + tp);  // B[2tp+8][2t+1], B[2tp+9][2t+1]
        // The four k values 2tp, 2tp+1, 2tp+8, 2tp+9 of A (row g in ar, row g+8 in ar8) and of B (column 2t in
        // bc, column 2t+1 in bc1), low half first.
        float ar[4] = {h2f((u16)sa0), h2f((u16)(sa0 >> 16)), h2f((u16)sa2), h2f((u16)(sa2 >> 16))};
        float ar8[4] = {h2f((u16)sa1), h2f((u16)(sa1 >> 16)), h2f((u16)sa3), h2f((u16)(sa3 >> 16))};
        float bc[4] = {h2f((u16)sb0), h2f((u16)(sb0 >> 16)), h2f((u16)sb1), h2f((u16)(sb1 >> 16))};
        float bc1[4] = {h2f((u16)sc0), h2f((u16)(sc0 >> 16)), h2f((u16)sc1), h2f((u16)(sc1 >> 16))};
#pragma unroll
        for (int i = 0; i < 4; i++) {
            c[0] = fmaf(ar[i], bc[i], c[0]);
            c[1] = fmaf(ar[i], bc1[i], c[1]);
            c[2] = fmaf(ar8[i], bc[i], c[2]);
            c[3] = fmaf(ar8[i], bc1[i], c[3]);
        }
    }
#endif
#else
    asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};"
                 : "+f"(c[0]), "+f"(c[1]), "+f"(c[2]), "+f"(c[3]) : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
#endif
}
#if __CUDA_ARCH__ < 800
// D[8,8] += A[8,4] * B[4,8] with the four independent computations of mma.m8n8k4 (Volta, SASS HMMA.884) selected
// by g & 3. PTX ISA 8.5 §9.7.13.4.1: lane l = 4*g + t owns A row t + 4*(g >= 4) at k 0..3 and D elements by the
// column/row formulas implemented in gemm_q's sm_70 path. mma.m16n8k16 is sm_80+, so this helper only exists for
// the pre-Volta/Volta build: the guard keeps the sm_80+ preprocessed source byte-identical.
__device__ __forceinline__ void mma884(float* d, u32 a0, u32 a1, u32 b0, u32 b1) {
    asm volatile("mma.sync.aligned.m8n8k4.row.col.f32.f16.f16.f32 "
                 "{%0,%1,%2,%3,%4,%5,%6,%7}, {%8,%9}, {%10,%11}, {%0,%1,%2,%3,%4,%5,%6,%7};"
                 : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3]), "+f"(d[4]), "+f"(d[5]), "+f"(d[6]), "+f"(d[7])
                 : "r"(a0), "r"(a1), "r"(b0), "r"(b1));
}
#endif
__device__ __forceinline__ u32 h2pack(float a, float b) { return (u32)f2h(a) | ((u32)f2h(b) << 16); }

// act: 0 = store, 1 = y = silu(y) * result (SwiGLU over a gate already in y), 2 = y += result.
// tiles = null: one dense matrix wd over positions 0 .. nd, tile blockIdx.y = positions BM * blockIdx.y ...
// BM positions x 64 rows per block, K in steps of BK; warps form a (BM / 32) x 2 grid, each owning 32 x 32 outputs.
// SM (gemms_*, tile lists only): the tiles of at most 32 positions (most expert tiles), which the SM = false kernel
// skips; their 32 x 64 outputs go 16 x 16 per warp (positions wm, rows wn, in acc[0][0..1]). Each output sums the
// same products in the same order either way. (A runtime branch in one kernel costs the big tiles a third.)
template <int T, int SBB, int BM, int BK, bool SM>
__device__ __forceinline__ void gemm_q(const GemmTile* tiles, const u8* wd, int nd, const float* __restrict__ x, int x_stride,
                                       const int* xrow, float* y, int y_stride, int rows, int n64, int act) {
    constexpr int P = BK + 8, NT = BM * 2, SUBS = BK / 8, XM = SM ? 32 : BM;  // smem pitch in halves (padding: conflict-free fragments)
    __shared__ __align__(16) u16 xs[XM * P], ws[64 * P];
    GemmTile tl = tiles ? tiles[blockIdx.y] : GemmTile{wd, (int)blockIdx.y * XM, min(XM, nd - (int)blockIdx.y * XM)};
    if (tiles && (tl.cnt <= 32) != SM) return;
    int n0 = blockIdx.x * 64, tid = threadIdx.x, warp = tid >> 5, lane = tid & 31, g = lane >> 2, t = lane & 3;
    int wm = SM ? 16 * (warp & 1) : (warp >> 1) * 32, wn = SM ? 16 * (warp >> 1) : (warp & 1) * 32;
    const float* xr[XM * BK / 4 / NT];  // row pointers of the X elements this thread loads (null past cnt)
    #pragma unroll
    for (int q = 0; q < XM * BK / 4 / NT; q++) {
        int r = (tid + q * NT) / (BK / 4);
        xr[q] = r < tl.cnt ? x + (size_t)(xrow ? xrow[tl.m0 + r] : tl.m0 + r) * x_stride : nullptr;
    }
    float acc[2][4][4] = {};
#if __CUDA_ARCH__ < 800 && GEMM_TC
    // Same 32 f32 storage as acc, seen as 4 m8 tiles x 8 D registers: accv[j][i] == &acc[0][0][0][j*8+i].
    float (&accv)[4][8] = reinterpret_cast<float (&)[4][8]>(acc);
#endif
    // W step kb is decoded into registers (as halves) during step kb - 1's mma and stored after it.
    constexpr int WQ = 64 * SUBS / NT;
    static_assert(64 * SUBS % NT == 0, "whole W groups per thread");
    uint4 wv[WQ];
    auto ldw = [&](int kb) {
        int sb = kb / (256 / BK), part = kb % (256 / BK);
        #pragma unroll
        for (int q = 0; q < WQ; q++) {
            int i = tid + q * NT, r = i / SUBS, j = i % SUBS;
            float v[8] = {};
            const u8* blk = tl.w + (size_t)(n0 + r) * ROWB(n64 * 64, SBB) + (size_t)sb * SBB;
            if (n0 + r >= rows) {
            } else if constexpr (T == 17 || T == 18 || T == 21 || T == 22) {  // QS tables; same values as deq8: d times the signed grid bytes
                int lo, hi; float d, m;
                QS<T>::get(blk, part * SUBS + j, lo, hi, d, m);
                for (int e = 0; e < 4; e++) v[e] = d * (float)(signed char)(lo >> 8 * e), v[4 + e] = d * (float)(signed char)(hi >> 8 * e);
            } else deq8<T>(blk, part * SUBS + j, v);
            wv[q] = make_uint4(h2pack(v[0], v[1]), h2pack(v[2], v[3]), h2pack(v[4], v[5]), h2pack(v[6], v[7]));
        }
    };
    auto stw = [&]() {
        #pragma unroll
        for (int q = 0; q < WQ; q++) { int i = tid + q * NT; *(uint4*)(ws + (i / SUBS) * P + (i % SUBS) * 8) = wv[q]; }
    };
    const int nk = n64 * 64 / BK;
    if constexpr (T == 17 || T == 18 || T == 21 || T == 22) { QS<T>::load(); __syncthreads(); }
    ldw(0);
    stw();
    for (int kb = 0; kb < nk; kb++) {
        #pragma unroll
        for (int q = 0; q < XM * BK / 4 / NT; q++) {
            int i = tid + q * NT, r = i / (BK / 4), c = (i % (BK / 4)) * 4;
            float4 v = xr[q] ? *(const float4*)(xr[q] + kb * BK + c) : make_float4(0.f, 0.f, 0.f, 0.f);
            *(uint2*)(xs + r * P + c) = make_uint2(h2pack(v.x, v.y), h2pack(v.z, v.w));
        }
        __syncthreads();
        if (kb + 1 < nk) ldw(kb + 1);
        // Expert tiles are often part full; a warp whose 32 positions are all past cnt has nothing to multiply.
        if (wm < tl.cnt)
#pragma unroll
        for (int kk = 0; kk < BK; kk += 16) {
#if __CUDA_ARCH__ < 800 && GEMM_TC
            // Volta: eight m8n8k4 ops replace one m16n8k16 for the same 16-deep k step. The four computations of
            // each instruction are selected by c = g & 3: SM == false maps them to the four n8 tiles (m8 = j, n8 =
            // c, 32 f32 per lane in accv[0..3]); SM == true maps them to the four 8x8 quadrants of the 16x16 warp
            // tile (m8 = c >> 1, n8 = c & 1, accv[0] only). A depends on m8 only (broadcast across c), B on n8.
            const int c = g & 3, hi = g >> 2;
            #pragma unroll
            for (int j = 0; j < (SM ? 1 : 4); j++) {
                int m8 = SM ? (c >> 1) : j, n8 = SM ? (c & 1) : c;
                const u16* pa = xs + (wm + 8 * m8 + t + 4 * hi) * P + kk;
                const u16* pb = ws + (wn + 8 * n8 + t + 4 * hi) * P + kk;
                #pragma unroll
                for (int ks = 0; ks < 4; ks++) {
                    u32 a0 = ld_s32(pa + 4 * ks), a1 = ld_s32(pa + 4 * ks + 2);
                    u32 b0 = ld_s32(pb + 4 * ks), b1 = ld_s32(pb + 4 * ks + 2);
                    mma884(accv[j], a0, a1, b0, b1);
                }
            }
#else
            constexpr int MT = SM ? 1 : 2, NT8 = SM ? 2 : 4;
            u32 a[2][4], b[4][2];
            #pragma unroll
            for (int mt = 0; mt < MT; mt++) {
                const u16* p = xs + (wm + mt * 16 + g) * P + kk + 2 * t;
                a[mt][0] = ld_s32(p); a[mt][1] = ld_s32(p + 8 * P); a[mt][2] = ld_s32(p + 8); a[mt][3] = ld_s32(p + 8 * P + 8);
            }
            #pragma unroll
            for (int nt = 0; nt < NT8; nt++) {
                const u16* p = ws + (wn + nt * 8 + g) * P + kk + 2 * t;
                b[nt][0] = ld_s32(p); b[nt][1] = ld_s32(p + 8);
            }
            #pragma unroll
            for (int mt = 0; mt < MT; mt++)
                #pragma unroll
                for (int nt = 0; nt < NT8; nt++) mma16816(acc[mt][nt], a[mt][0], a[mt][1], a[mt][2], a[mt][3], b[nt][0], b[nt][1]);
#endif
        }
        __syncthreads();
        if (kb + 1 < nk) stw();
    }
#if __CUDA_ARCH__ < 800 && GEMM_TC
    // m8n8k4 D layout (PTX ISA 8.5 §9.7.13.4.1): register i = 4*p4 + 2*p2 + e sits at row (t & 1) + 2*p2 + 4*hi
    // and column (t & 2) + 4*p4 + e of the 8x8 tile. For each fixed c, lanes {4c..4c+3} and {16+4c..19+4c} cover
    // that tile exactly once; the tile itself is picked by c (n8 = c) and j (m8 = j), or by c alone for SM.
    const int c = g & 3, hi = g >> 2;
    #pragma unroll
    for (int j = 0; j < (SM ? 1 : 4); j++)
        #pragma unroll
        for (int p4 = 0; p4 < 2; p4++)
            #pragma unroll
            for (int p2 = 0; p2 < 2; p2++) {
                int r = wm + 8 * (SM ? (c >> 1) : j) + (t & 1) + 2 * p2 + 4 * hi;
                int n = n0 + wn + 8 * (SM ? (c & 1) : c) + (t & 2) + 4 * p4;
                if (r >= tl.cnt) continue;
                float* yr = y + (size_t)(tl.m0 + r) * y_stride;
                #pragma unroll
                for (int e = 0; e < 2; e++) {
                    if (n + e >= rows) break;
                    float v = accv[j][4 * p4 + 2 * p2 + e];
                    yr[n + e] = act == 0 ? v : act == 1 ? silu(yr[n + e]) * v : yr[n + e] + v;
                }
            }
#else
    #pragma unroll
    for (int mt = 0; mt < (SM ? 1 : 2); mt++)
        #pragma unroll
        for (int nt = 0; nt < (SM ? 2 : 4); nt++)
            #pragma unroll
            for (int h = 0; h < 2; h++) {
                int r = wm + mt * 16 + g + 8 * h, n = n0 + wn + nt * 8 + 2 * t;
                if (r >= tl.cnt) continue;
                float* yr = y + (size_t)(tl.m0 + r) * y_stride;
                #pragma unroll
                for (int e = 0; e < 2; e++) {
                    if (n + e >= rows) break;
                    float v = acc[mt][nt][2 * h + e];
                    yr[n + e] = act == 0 ? v : act == 1 ? silu(yr[n + e]) * v : yr[n + e] + v;
                }
            }
#endif
}

#ifndef GEMM_BM
#define GEMM_BM 128
#endif
#ifndef GEMM_BK
#define GEMM_BK 64
#endif
#ifndef GEMM_MIN_BLOCKS
#define GEMM_MIN_BLOCKS 1
#endif
static_assert(GEMM_BM % 32 == 0, "GEMM_BM must be a multiple of 32 (warp rows)");
static_assert(GEMM_BK % 8 == 0, "GEMM_BK must be a multiple of 8 (one super-block sub-tile)");
static_assert((64 * (GEMM_BK / 8)) % (2 * GEMM_BM) == 0, "whole W groups per thread");
#if GEMM_MIN_BLOCKS > 1
#define GEMM_LAUNCH_BOUNDS __launch_bounds__(GEMM_BM * 2, GEMM_MIN_BLOCKS)
#else
#define GEMM_LAUNCH_BOUNDS __launch_bounds__(GEMM_BM * 2)
#endif
#define DEF_GEMM(T, NAME, SBB)                                                                                    \
    extern "C" __global__ void GEMM_LAUNCH_BOUNDS gemm_##NAME(const GemmTile* tiles, const u8* wd, int nd,         \
            const float* x, int x_stride, const int* xrow, float* y, int y_stride, int rows, int n64, int act) {  \
        gemm_q<T, SBB, GEMM_BM, GEMM_BK, false>(tiles, wd, nd, x, x_stride, xrow, y, y_stride, rows, n64, act); \
    }                                                                                                             \
    extern "C" __global__ void GEMM_LAUNCH_BOUNDS gemms_##NAME(const GemmTile* tiles, const u8* wd, int nd,        \
            const float* x, int x_stride, const int* xrow, float* y, int y_stride, int rows, int n64, int act) {  \
        gemm_q<T, SBB, GEMM_BM, GEMM_BK, true>(tiles, wd, nd, x, x_stride, xrow, y, y_stride, rows, n64, act);  \
    }
QTYPES(DEF_GEMM)

// ---- prefill GEMM on int8 tensor cores (integer weight types) ----
// X is first quantized by quant_q8 into q8 rows: cols int8, then cols / 32 f32 scales, then cols / 16 f32 sums of the
// dequantized values (row bytes Q8_ROW(cols)). Weights come from QI<T> as int8 with a scale (and min) per 16, and each
// 16-deep int32 mma result is scaled into f32 accumulators: y += dx dw sum(qx qw) - m_w sum(dx qx).
// Same tiles, grid and block as gemm_q; K steps of 64 with X double-buffered by cp.async.
#define Q8_ROW(cols) ((cols) + (cols) / 8 + (cols) / 4)

// grid = rows of x, block = 256: q8 row r of out = x row r.
extern "C" __global__ void quant_q8(const float* x, int x_stride, u8* out, int cols) {
    const float* xr = x + (size_t)blockIdx.x * x_stride;
    u8* o = out + (size_t)blockIdx.x * Q8_ROW(cols);
    for (int i = threadIdx.x * 16; i < cols; i += blockDim.x * 16) {
        float v[16];
        #pragma unroll
        for (int j = 0; j < 4; j++) *(float4*)(v + 4 * j) = *(const float4*)(xr + i + 4 * j);
        float mx = 0.f;
        #pragma unroll
        for (int j = 0; j < 16; j++) mx = fmaxf(mx, fabsf(v[j]));
#if LLAMA_Q8
        float d, id;
        {
            float sv = 0.f; int si = 1 << 30;
            for (int j = 0; j < 16; j++) if (fabsf(v[j]) == mx && si > i + j) { sv = v[j]; si = i + j; }
            q8k_scale<16>(sv, si, d, id);
        }
#else
        mx = fmaxf(mx, __shfl_xor_sync(__activemask(), mx, 1));  // lanes 2k, 2k + 1 share one 32-block
        float d = mx / 127.0f, id = mx > 0.0f ? 127.0f / mx : 0.0f;
#endif
        int q[16], sum = 0;
        #pragma unroll
        for (int j = 0; j < 16; j++) { q[j] = __float2int_rn(v[j] * id); sum += q[j]; }
        *(int4*)(o + i) = make_int4(pack4(q[0], q[1], q[2], q[3]), pack4(q[4], q[5], q[6], q[7]),
                                    pack4(q[8], q[9], q[10], q[11]), pack4(q[12], q[13], q[14], q[15]));
        if (!(threadIdx.x & 1)) ((float*)(o + cols))[i / 32] = d;
        ((float*)(o + cols + cols / 8))[i / 16] = d * (float)sum;
    }
}

// int8 tensor-core mma (sm_80+). On Turing the int8 path is not built: gemm_raw uses the f16 GEMM there.
#if !defined(__CUDA_ARCH__) || __CUDA_ARCH__ >= 800
__device__ __forceinline__ void mma_s8_16816(int* c, u32 a0, u32 a1, u32 b0) {
    asm volatile("mma.sync.aligned.m16n8k16.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5}, {%6}, {%0,%1,%2,%3};"
                 : "+r"(c[0]), "+r"(c[1]), "+r"(c[2]), "+r"(c[3]) : "r"(a0), "r"(a1), "r"(b0));
}
__device__ __forceinline__ void mma_s8_16832(int* c, u32 a0, u32 a1, u32 a2, u32 a3, u32 b0, u32 b1) {
    asm volatile("mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};"
                 : "+r"(c[0]), "+r"(c[1]), "+r"(c[2]), "+r"(c[3]) : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
}
// int -> float for |c| < 2^22 without the quarter-rate I2F: 2^23 + 2^22 + c has c in its low mantissa bits.
__device__ __forceinline__ float i2f_small(int c) { return __int_as_float(0x4B400000 + c) - 12582912.0f; }
// The mma with every accumulator starting at I2F_BIAS: d = I2F_BIAS + sum, so i2f_small's integer add comes free.
#define I2F_BIAS 0x4B400000
__device__ __forceinline__ void mma_s8_16816_b(int* d, u32 a0, u32 a1, u32 b0) {
    asm volatile("mma.sync.aligned.m16n8k16.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5}, {%6}, {%7,%7,%7,%7};"
                 : "=r"(d[0]), "=r"(d[1]), "=r"(d[2]), "=r"(d[3]) : "r"(a0), "r"(a1), "r"(b0), "r"(I2F_BIAS));
}
__device__ __forceinline__ void mma_s8_16832_b(int* d, u32 a0, u32 a1, u32 a2, u32 a3, u32 b0, u32 b1) {
    asm volatile("mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%10,%10,%10,%10};"
                 : "=r"(d[0]), "=r"(d[1]), "=r"(d[2]), "=r"(d[3]) : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1), "r"(I2F_BIAS));
}
#endif  // __CUDA_ARCH__ >= 800
// Weight types whose scale (and min) is constant over 32 weights: one 32-deep mma per scale.
template <int T> __host__ __device__ constexpr bool scale32() { return T == 42 || T == 2 || T == 3 || T == 6 || T == 7 || T == 8 || T == 12 || T == 13 || T == 16 || T == 19 || T == 18 || T == 21 || T == 23; }
// Volta (sm_70) has no cp.async (sm_80+). There the copy is a synchronous typed load/store by the same thread,
// which is also why the "wait" sites need no thread barrier (see the audit at attn_decode_t / attn_prefill_t).
// Zero fill: with `ok == false` the source is not read at all (cp.async's size operand 0 contract) and `dst`
// receives zeros. The explicit `if (ok)` branch keeps ptxas from hoisting an unconditional ld.global; all current
// sm_70 call sites pass a valid source anyway (prefill clamps the row to `last`, decode always passes true), so
// the branch is a contract, not a hot path. The store is a typed C++ store through the same pointer type the
// reader uses (uint4/uint2, like ldh_raw), so the compiler sees the alias; st.shared asm would hide it and let
// the typed reads be reordered. The trailing empty asm is a compiler barrier only (not a thread barrier): no
// reader can be hoisted above the store.
#if __CUDA_ARCH__ < 800
__device__ __forceinline__ void cp_async16(void* dst, const void* src, bool ok) {
    uint4 v = make_uint4(0, 0, 0, 0);
    if (ok) v = *(const uint4*)src;
    *(uint4*)dst = v;
    asm volatile("" ::: "memory");
}
__device__ __forceinline__ void cp_async8(void* dst, const void* src, bool ok) {
    uint2 v = make_uint2(0, 0);
    if (ok) v = *(const uint2*)src;
    *(uint2*)dst = v;
    asm volatile("" ::: "memory");
}
__device__ __forceinline__ void cp_async_commit() {}
template <int N> __device__ __forceinline__ void cp_async_wait() {}
#else
__device__ __forceinline__ void cp_async16(void* dst, const void* src, bool ok) {
#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ < 800
    // No cp.async before sm_80: copy through registers. A predicated-off cp.async still zero-fills its 16 bytes,
    // and the kernels rely on that for rows past the last one, so the fallback writes zeros too.
    if (ok) *(uint4*)dst = *(const uint4*)src; else *(uint4*)dst = make_uint4(0, 0, 0, 0);
#else
    unsigned d = (unsigned)__cvta_generic_to_shared(dst);
    asm volatile("cp.async.cg.shared.global [%0], [%1], 16, %2;" :: "r"(d), "l"(src), "r"(ok ? 16 : 0));
#endif
}
__device__ __forceinline__ void cp_async8(void* dst, const void* src, bool ok) {
#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ < 800
    if (ok) *(uint2*)dst = *(const uint2*)src; else *(uint2*)dst = make_uint2(0, 0);
#else
    unsigned d = (unsigned)__cvta_generic_to_shared(dst);
    asm volatile("cp.async.ca.shared.global [%0], [%1], 8, %2;" :: "r"(d), "l"(src), "r"(ok ? 8 : 0));
#endif
}
__device__ __forceinline__ void cp_async_commit() {
#if !defined(__CUDA_ARCH__) || __CUDA_ARCH__ >= 800
    asm volatile("cp.async.commit_group;");
#endif
}
template <int N> __device__ __forceinline__ void cp_async_wait() {
#if !defined(__CUDA_ARCH__) || __CUDA_ARCH__ >= 800
    asm volatile("cp.async.wait_group %0;" :: "n"(N));
#endif
}
#endif

// sm_80+ only: Volta and Turing have no usable int8 tensor-core path here (see the guard above).
// SM: as in gemm_q (gemmis_*, the tiles of at most 32 positions, 16 x 16 outputs per warp).
#if !defined(__CUDA_ARCH__) || __CUDA_ARCH__ >= 800
template <int T, int SBB, int BM, bool SM>
__device__ __forceinline__ void gemmi_q(const GemmTile* tiles, const u8* wd, int nd, const u8* __restrict__ x,
                                        const int* xrow, float* y, int y_stride, int rows, int n64, int act) {
    constexpr int P = 80, XM = SM ? 32 : BM;  // smem pitch in bytes: 64 int8 + padding (conflict-free fragments, 16-byte aligned rows)
    static_assert(BM == 128, "one X row half per thread");
    __shared__ __align__(16) signed char xq[2][XM * P], wq[64 * P];
    __shared__ __align__(16) float xd[2][XM][2], xsum[2][XM][4];
    __shared__ __align__(16) float2 wdm[4][64];  // W scale and min per 16 weights: [16-group][row]
    GemmTile tl = tiles ? tiles[blockIdx.y] : GemmTile{wd, (int)blockIdx.y * XM, min(XM, nd - (int)blockIdx.y * XM)};
    if (tiles && (tl.cnt <= 32) != SM) return;
    int n0 = blockIdx.x * 64, tid = threadIdx.x, warp = tid >> 5, lane = tid & 31, g = lane >> 2, t = lane & 3;
    int wm = SM ? 16 * (warp & 1) : (warp >> 1) * 32, wn = SM ? 16 * (warp >> 1) : (warp & 1) * 32, cols = n64 * 64;
    // X: thread copies 32 int8 (half of the row's 64) of row xr_, plus the row's scales (xh = 0) or sums (xh = 1).
    int xr_ = tid >> 1, xh = tid & 1;
    bool xok = xr_ < tl.cnt;
    const u8* xp = x + (size_t)(xok ? (xrow ? xrow[tl.m0 + xr_] : tl.m0 + xr_) : 0) * Q8_ROW(cols);
    auto ldx = [&](int kb) {
        int b = kb & 1;
        if (SM && xr_ >= XM) { cp_async_commit(); return; }
        cp_async16(&xq[b][xr_ * P + xh * 32], xp + kb * 64 + xh * 32, xok);
        cp_async16(&xq[b][xr_ * P + xh * 32 + 16], xp + kb * 64 + xh * 32 + 16, xok);
        if (xh) cp_async16(&xsum[b][xr_][0], xp + cols + cols / 8 + kb * 16, xok);
        else cp_async8(&xd[b][xr_][0], xp + cols + kb * 8, xok);
        cp_async_commit();
    };
    // W: thread decodes the 16 weights (subs 2 wi, 2 wi + 1 of the step) of row wr_.
    int wr_ = tid >> 2, wi = tid & 3;
    const u8* wp = n0 + wr_ < rows ? tl.w + (size_t)(n0 + wr_) * ROWB(cols, SBB) : nullptr;
    const bool v16 = ((size_t)tl.w & 15) == 0 && ROWB(cols, SBB) % 16 == 0;  // QI::get2's 16-byte loads
    float acc[2][4][4] = {};
    const int nk = n64;
    // W step kb is decoded into registers during step kb - 1's mma and stored after it.
    int lo0, hi0, lo1, hi1; float wd0, wm0;
    auto ldw = [&](int kb) {
        lo0 = hi0 = lo1 = hi1 = 0; wd0 = wm0 = 0.f;
        float d1, m1;
        if (wp) {
            const u8* sbp = wp + (size_t)(kb >> 2) * SBB;
            int sub = (kb & 3) * 8 + 2 * wi;
            if constexpr (T == 12) {
                if (v16) { QI<12>::get2(sbp, sub, lo0, hi0, lo1, hi1, wd0, wm0); return; }
            }
            QI<T>::get(sbp, sub, lo0, hi0, wd0, wm0);
            QI<T>::get(sbp, sub + 1, lo1, hi1, d1, m1);
        }
    };
    auto stw = [&]() {
        *(int4*)(wq + wr_ * P + wi * 16) = make_int4(lo0, hi0, lo1, hi1);
        wdm[wi][wr_] = make_float2(wd0, wm0);
    };
    ldx(0);
    ldw(0);
    stw();
    for (int kb = 0; kb < nk; kb++) {
        if (kb + 1 < nk) ldx(kb + 1);
        if (kb + 1 < nk) cp_async_wait<1>(); else cp_async_wait<0>();
        __syncthreads();
        if (kb + 1 < nk) ldw(kb + 1);
        const int b = kb & 1;
        constexpr int KS = scale32<T>() ? 32 : 16;  // depth of one mma (one weight scale)
        constexpr int MT = SM ? 1 : 2, NT8 = SM ? 2 : 4;
        // X scales and sums of the step for this thread's rows (g, g + 8 of each mt), one vector load each.
        float2 xdv[2][2]; float4 xsv[2][2];
        #pragma unroll
        for (int mt = 0; mt < MT; mt++)
            #pragma unroll
            for (int i = 0; i < 2; i++) {
                int r = wm + mt * 16 + g + 8 * i;
                xdv[mt][i] = *(const float2*)xd[b][r];
                if (QI<T>::MIN) xsv[mt][i] = *(const float4*)xsum[b][r];
            }
        #pragma unroll
        for (int h = 0; h < 64 / KS; h++) if (wm < tl.cnt) {
            u32 a[2][4], bw[4][2];
            float da[2][2], sa[2][2], dbv[4][2], mb[4][2];
            #pragma unroll
            for (int mt = 0; mt < MT; mt++) {
                int r = wm + mt * 16 + g;
                const signed char* p = &xq[b][r * P + h * KS + 4 * t];
                a[mt][0] = *(const u32*)p; a[mt][1] = *(const u32*)(p + 8 * P);
                if (KS == 32) { a[mt][2] = *(const u32*)(p + 16); a[mt][3] = *(const u32*)(p + 8 * P + 16); }
                #pragma unroll
                for (int i = 0; i < 2; i++) {
                    const float* xs = (const float*)&xsv[mt][i];
                    da[mt][i] = h * KS / 32 ? xdv[mt][i].y : xdv[mt][i].x;
                    if (QI<T>::MIN) sa[mt][i] = KS == 32 ? xs[2 * h] + xs[2 * h + 1] : xs[h];
                }
            }
            #pragma unroll
            for (int nt = 0; nt < NT8; nt++) {
                int n = wn + nt * 8;
                const signed char* p = wq + (n + g) * P + h * KS + 4 * t;
                bw[nt][0] = *(const u32*)p;
                if (KS == 32) bw[nt][1] = *(const u32*)(p + 16);
                float4 q = *(const float4*)&wdm[h * KS / 16][n + 2 * t];
                dbv[nt][0] = q.x; mb[nt][0] = q.y; dbv[nt][1] = q.z; mb[nt][1] = q.w;
            }
            #pragma unroll
            for (int mt = 0; mt < MT; mt++)
                #pragma unroll
                for (int nt = 0; nt < NT8; nt++) {
                    int c[4];
                    if (KS == 32) mma_s8_16832_b(c, a[mt][0], a[mt][1], a[mt][2], a[mt][3], bw[nt][0], bw[nt][1]);
                    else mma_s8_16816_b(c, a[mt][0], a[mt][1], bw[nt][0]);
                    #pragma unroll
                    for (int i = 0; i < 4; i++) {
                        float f = (__int_as_float(c[i]) - 12582912.0f) * (da[mt][i >> 1] * dbv[nt][i & 1]);  // i2f_small
                        if (QI<T>::MIN) f -= sa[mt][i >> 1] * mb[nt][i & 1];
                        acc[mt][nt][i] += f;
                    }
                }
        }
        __syncthreads();
        if (kb + 1 < nk) stw();
    }
    #pragma unroll
    for (int mt = 0; mt < (SM ? 1 : 2); mt++)
        #pragma unroll
        for (int nt = 0; nt < (SM ? 2 : 4); nt++)
            #pragma unroll
            for (int h = 0; h < 2; h++) {
                int r = wm + mt * 16 + g + 8 * h, n = n0 + wn + nt * 8 + 2 * t;
                if (r >= tl.cnt) continue;
                float* yr = y + (size_t)(tl.m0 + r) * y_stride;
                #pragma unroll
                for (int e = 0; e < 2; e++) {
                    if (n + e >= rows) break;
                    float v = acc[mt][nt][2 * h + e];
                    yr[n + e] = act == 0 ? v : act == 1 ? silu(yr[n + e]) * v : yr[n + e] + v;
                }
            }
}

#define DEF_GEMMI(T, NAME, SBB)                                                                                   \
    extern "C" __global__ void __launch_bounds__(256, 2) gemmi_##NAME(const GemmTile* tiles, const u8* wd, int nd,    \
            const u8* x, const int* xrow, float* y, int y_stride, int rows, int n64, int act) {                    \
        gemmi_q<T, SBB, 128, false>(tiles, wd, nd, x, xrow, y, y_stride, rows, n64, act);                       \
    }                                                                                                             \
    extern "C" __global__ void __launch_bounds__(256) gemmis_##NAME(const GemmTile* tiles, const u8* wd, int nd,   \
            const u8* x, const int* xrow, float* y, int y_stride, int rows, int n64, int act) {                    \
        gemmi_q<T, SBB, 128, true>(tiles, wd, nd, x, xrow, y, y_stride, rows, n64, act);                        \
    }
ITYPES(DEF_GEMMI)
#endif

// ---- elementwise / norm ----

// grid = rows. out[r] = rmsnorm(x[r]) * w (same w for every row). xq (optional): out also quantized as quant_xq does.
// Row r takes gamma row r % wr of w (wr > 1: hyper-connection streams, one gamma per stream).
extern "C" __global__ void rms_norm(float* x, int x_stride, const float* w, float* out, int out_stride, int n, float eps,
                                    signed char* xq, const float* res, int wr) {
    w += (size_t)(blockIdx.x % wr) * n;
    float* xr = x + (size_t)blockIdx.x * x_stride;
    float* o = out + (size_t)blockIdx.x * out_stride;
    float s = 0.0f;
    // The sum keeps the order of a 256-thread block (bit-identical results); all threads scale. Four loads in flight
    // per step; the output values are all loaded before any store, as out may alias x. With res, x += res first.
    if (threadIdx.x < 256 && res) {
        const float* rr = res + (size_t)blockIdx.x * x_stride;
        int i = threadIdx.x;
        for (; i + 768 < n; i += 1024) {
            float a = xr[i] + rr[i], b = xr[i + 256] + rr[i + 256], c = xr[i + 512] + rr[i + 512], d = xr[i + 768] + rr[i + 768];
            xr[i] = a; xr[i + 256] = b; xr[i + 512] = c; xr[i + 768] = d;
            s += a * a; s += b * b; s += c * c; s += d * d;
        }
        for (; i < n; i += 256) { float a = xr[i] + rr[i]; xr[i] = a; s += a * a; }
    } else if (threadIdx.x < 256) {
        int i = threadIdx.x;
        for (; i + 768 < n; i += 1024) {
            float a = xr[i], b = xr[i + 256], c = xr[i + 512], d = xr[i + 768];
            s += a * a; s += b * b; s += c * c; s += d * d;
        }
        for (; i < n; i += 256) s += xr[i] * xr[i];
    }
    float sc = 1.0f / sqrtf(block_sum(s) / (float)n + eps);
    if (xq) {  // each thread scales, stores and quantizes its own 8 values, as quant_x would map them
        signed char* q = xq + (size_t)blockIdx.x * n;
        float* qd = (float*)(xq + (size_t)gridDim.x * n) + blockIdx.x * (n / 32);
        for (int i0 = 0; i0 < n; i0 += blockDim.x * 8) {
            int i = i0 + threadIdx.x * 8;
            unsigned m = __ballot_sync(0xffffffff, i < n);
            if (i >= n) continue;
            float4 a = *(const float4*)(xr + i), c = *(const float4*)(xr + i + 4);
            float4 wa = *(const float4*)(w + i), wc = *(const float4*)(w + i + 4);
            a = make_float4(a.x * sc * wa.x, a.y * sc * wa.y, a.z * sc * wa.z, a.w * sc * wa.w);
            c = make_float4(c.x * sc * wc.x, c.y * sc * wc.y, c.z * sc * wc.z, c.w * sc * wc.w);
            *(float4*)(o + i) = a; *(float4*)(o + i + 4) = c;
            quant8(a, c, i, q, qd, m);
        }
        return;
    }
    int i = threadIdx.x, bd = blockDim.x;
    for (; i + 3 * bd < n; i += 4 * bd) {
        float a = xr[i] * sc * w[i], b = xr[i + bd] * sc * w[i + bd], c = xr[i + 2 * bd] * sc * w[i + 2 * bd], d = xr[i + 3 * bd] * sc * w[i + 3 * bd];
        o[i] = a; o[i + bd] = b; o[i + 2 * bd] = c; o[i + 3 * bd] = d;
    }
    for (; i < n; i += bd) o[i] = xr[i] * sc * w[i];
}

// Block-wide (largest b, first bi on ties) of the threads' (b, bi), in thread 0; bi == n marks no value yet.
__device__ void amax_reduce(float& b, int& bi, int n) {
    for (int o = 16; o > 0; o >>= 1) {
        float v = __shfl_xor_sync(0xffffffff, b, o); int vi = __shfl_xor_sync(0xffffffff, bi, o);
        if (v > b || (v == b && vi < bi)) { b = v; bi = vi; }
    }
    __shared__ float sv[32]; __shared__ int si[32];
    int lane = threadIdx.x & 31, w = threadIdx.x >> 5;
    if (lane == 0) { sv[w] = b; si[w] = bi; }
    __syncthreads();
    if (w == 0) {
        b = lane < (blockDim.x >> 5) ? sv[lane] : __int_as_float(0xff800000); bi = lane < (blockDim.x >> 5) ? si[lane] : n;
        for (int o = 16; o > 0; o >>= 1) {
            float v = __shfl_xor_sync(0xffffffff, b, o); int vi = __shfl_xor_sync(0xffffffff, bi, o);
            if (v > b || (v == b && vi < bi)) { b = v; bi = vi; }
        }
    }
}

// grid = (parts, rows). part[r * parts + p] = (largest x, its index) of row r over i = p * blockDim + t + k * parts * blockDim.
extern "C" __global__ void argmax_part(const float* x, int n, int2* part) {
    const float* xr = x + (size_t)blockIdx.y * n;
    float b = __int_as_float(0xff800000); int bi = n;
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n; i += gridDim.x * blockDim.x) if (xr[i] > b || bi == n) { b = xr[i]; bi = i; }
    amax_reduce(b, bi, n);
    if (threadIdx.x == 0) part[blockIdx.y * gridDim.x + blockIdx.x] = make_int2(__float_as_int(b), bi);
}

// grid = rows, block = parts. out[r] = index of the largest x in row r (first one on ties, like ops::argmax).
extern "C" __global__ void argmax_rows(const int2* part, int n, int* out) {
    int2 p = part[blockIdx.x * blockDim.x + threadIdx.x];
    float b = __int_as_float(p.x); int bi = p.y;
    amax_reduce(b, bi, n);
    if (threadIdx.x == 0) out[blockIdx.x] = bi;
}

// grid = rows, in place. Row r is vector r % per of token r / per (tokens `stride` floats apart).
extern "C" __global__ void l2_norm(float* x, int n, int per, int stride, float eps) {
    float* xr = x + (size_t)(blockIdx.x / per) * stride + (size_t)(blockIdx.x % per) * n;
    float s = 0.0f;
    for (int i = threadIdx.x; i < n; i += blockDim.x) s += xr[i] * xr[i];
    float sc = 1.0f / fmaxf(sqrtf(block_sum(s)), eps);
    for (int i = threadIdx.x; i < n; i += blockDim.x) xr[i] *= sc;
}

// Per-token values live in device memory so a captured graph can replay: step[0] = position, step[1] = CPU worker seq.

// grid = tokens (each rotates its per heads), block = n_rot / 2. NEOX pairs (i, i + n_rot/2). Token t sits at position step[0] + t.
extern "C" __global__ void rope_neox(float* x, int stride, int per, int n_rot, const int* step, float base) {
    int pos = step[0] + blockIdx.x;
    int i = threadIdx.x, half = n_rot / 2;
    double theta = (double)pos * pow((double)base, -2.0 * i / n_rot);  // f64 is slow: once per token, not per head
    float s = (float)sin(theta), c = (float)cos(theta);
    for (int hd = 0; hd < per; hd++) {
        float* h = x + (size_t)(blockIdx.x * per + hd) * stride;
        float a = h[i], b = h[i + half];
        h[i] = a * c - b * s;
        h[i + half] = a * s + b * c;
    }
}

extern "C" __global__ void add(float* x, const float* y, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) x[i] += y[i];
}

extern "C" __global__ void swiglu(float* g, const float* u, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) g[i] = silu(g[i]) * u[i];
}

// swiglu on rows of n (a multiple of 32) quantized as quant_xq does into out; g is left as is. Block (c, t) of one
// warp: values c * 256 .. of row t.
extern "C" __global__ void swiglu_q(const float* g, const float* u, int n, signed char* out) {
    size_t o = (size_t)blockIdx.y * n + blockIdx.x * 256;
    int i = threadIdx.x * 8;
    // The partial last block of a row (n % 256 != 0) masks its shuffles (see quant_x).
    bool part = (int)blockIdx.x * 256 + 256 > n;
    unsigned m = part ? __ballot_sync(0xffffffff, blockIdx.x * 256 + i < n) : 0xffffffff;
    if (blockIdx.x * 256 + i >= n) return;
    float4 a = *(const float4*)(g + o + i), c = *(const float4*)(g + o + i + 4);
    float4 ua = *(const float4*)(u + o + i), uc = *(const float4*)(u + o + i + 4);
    a = make_float4(silu(a.x) * ua.x, silu(a.y) * ua.y, silu(a.z) * ua.z, silu(a.w) * ua.w);
    c = make_float4(silu(c.x) * uc.x, silu(c.y) * uc.y, silu(c.z) * uc.z, silu(c.w) * uc.w);
    float* d = (float*)(out + (size_t)gridDim.y * n) + o / 32;
    if (part) quant8(a, c, i, out + o, d, m); else quant8(a, c, i, out + o, d);
}

// ---- Gated DeltaNet ----

// n = tokens * nv values; per-head parameters repeat every nv.
extern "C" __global__ void ssm_gates(float* beta, float* g, const float* dt_bias, const float* a, int n, int nv) {
    int i = blockIdx.x * blockDim.x + threadIdx.x, h = i % nv;
    if (i < n) { beta[i] = sigmoid(beta[i]); g[i] = softplus(g[i] + dt_bias[h]) * a[h]; }
}

// Causal depthwise conv over [state..., current] then SiLU; state keeps the last kw-1 inputs, oldest first.
// Block = 128 channels; the first nn blocks are then l2-normalized as l2_norm does (the decode q and k heads).
extern "C" __global__ void conv_silu(const float* qkv, float* state, const float* w, float* y, int ch, int kw, int nn,
                                     float eps) {
    int c = blockIdx.x * blockDim.x + threadIdx.x;
    float v = 0.0f;
    if (c < ch) {
        float acc = 0.0f;
        for (int k = 0; k < kw - 1; k++) acc += state[k * ch + c] * w[c * kw + k];
        acc += qkv[c] * w[c * kw + kw - 1];
        v = silu(acc);
        for (int k = 0; k < kw - 2; k++) state[k * ch + c] = state[(k + 1) * ch + c];
        state[(kw - 2) * ch + c] = qkv[c];
    }
    if ((int)blockIdx.x < nn) v *= 1.0f / fmaxf(sqrtf(block_sum(v * v)), eps);
    if (c < ch) y[c] = v;
}

// Parallel over tokens for a chunk: y[t] = silu(conv over inputs t-kw+1 .. t), inputs before the chunk from state.
extern "C" __global__ void conv_seq(const float* qkv, const float* state, const float* w, float* y, int ch, int kw, int T) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= T * ch) return;
    int t = i / ch, c = i % ch;
    float acc = 0.0f;
    for (int k = 0; k < kw; k++) {
        int s = t - (kw - 1) + k;  // input index; < 0 reads state slot kw - 1 + s
        acc += (s < 0 ? state[(kw - 1 + s) * ch + c] : qkv[(size_t)s * ch + c]) * w[c * kw + k];
    }
    y[i] = silu(acc);
}

// After conv_seq: state = last kw-1 inputs. One thread per channel, ascending slots read only higher ones.
// Also writes the state after each of the first min(nsnap, T - 1) tokens to snap (one state each), for rollback.
extern "C" __global__ void conv_state(const float* qkv, float* state, int ch, int kw, int T, float* snap, int nsnap) {
    int c = blockIdx.x * blockDim.x + threadIdx.x;
    if (c >= ch) return;
    for (int n = 1; n <= min(nsnap, T - 1); n++)
        for (int k = 0; k < kw - 1; k++) {
            int s = n - (kw - 1) + k;
            snap[((size_t)(n - 1) * (kw - 1) + k) * ch + c] = s < 0 ? state[(kw - 1 + s) * ch + c] : qkv[(size_t)s * ch + c];
        }
    for (int k = 0; k < kw - 1; k++) {
        int s = T - (kw - 1) + k;
        state[k * ch + c] = s < 0 ? state[(kw - 1 + s) * ch + c] : qkv[(size_t)s * ch + c];
    }
}

// grid = (value heads, dv / (8 * R)), block = 256. Each state row (dk floats, dk in 32/64/128/256) lives in the
// registers of L = dk / 16 lanes, 16 floats each (float4 chunks s, s + L, ...), so a warp holds R = 32 / L rows and
// row dot products reduce over L lanes. The warp scans the T tokens in order.
// Token t: y + t * ych = [q | k | v] after conv and l2 norm; beta, g at t * nv; output at o + t * nv * dv.
// With dtb set, beta and g are raw and get ssm_gates' gates here (dtb, ga as its dt_bias, a).
// The state after each of the first min(nsnap, T - 1) tokens also goes to snap (S's layout, one state each).
// ponytail: sequential scan (latency-bound per token); a chunked WY form would use tensor cores for long prompts.
extern "C" __global__ void deltanet_seq(const float* y, float* S, const float* beta, const float* g, float* o,
                                        int nk, int nv, int ilv, int dk, int dv, float scale, int T, int ych, float* snap, int nsnap,
                                        const float* dtb, const float* ga) {
    int L = dk >> 4, R = 32 / L, lane = threadIdx.x & 31, s = lane % L, vh = blockIdx.x, kh = ilv ? vh / (nv / nk) : vh % nk;
    int j0 = (blockIdx.y * 8 + (threadIdx.x >> 5)) * R, j = j0 + lane / L;
    if (j0 >= dv) return;  // whole warp past the end (R divides dv)
    float4* row = (float4*)(S + ((size_t)vh * dv + j) * dk);
    float r[16];
#pragma unroll
    for (int i = 0; i < 4; i++) { float4 v = row[s + L * i]; r[4 * i] = v.x; r[4 * i + 1] = v.y; r[4 * i + 2] = v.z; r[4 * i + 3] = v.w; }
    // Token inputs do not depend on the state: token tok + 1's are loaded while token tok computes.
    float nk_[16], nq[16], ng, nb, nvv;
    auto ld = [&](int tok) {
        const float* yt = y + (size_t)tok * ych;
        const float4* q4 = (const float4*)(yt + kh * dk);
        const float4* k4 = (const float4*)(yt + nk * dk + kh * dk);
#pragma unroll
        for (int i = 0; i < 4; i++) {
            float4 v = k4[s + L * i]; nk_[4 * i] = v.x; nk_[4 * i + 1] = v.y; nk_[4 * i + 2] = v.z; nk_[4 * i + 3] = v.w;
            v = q4[s + L * i]; nq[4 * i] = v.x; nq[4 * i + 1] = v.y; nq[4 * i + 2] = v.z; nq[4 * i + 3] = v.w;
        }
        ng = g[tok * nv + vh]; nb = beta[tok * nv + vh]; nvv = yt[2 * nk * dk + vh * dv + j];
        if (dtb) { ng = softplus(ng + dtb[vh]) * ga[vh]; nb = sigmoid(nb); }
    };
    ld(0);
    for (int tok = 0; tok < T; tok++) {
        float kk[16], qv[16], decay = expf(ng), bt = nb, vt = nvv, sk = 0.0f, oq = 0.0f;
#pragma unroll
        for (int e = 0; e < 16; e++) { kk[e] = nk_[e]; qv[e] = nq[e]; }
        if (tok + 1 < T) ld(tok + 1);
#pragma unroll
        for (int e = 0; e < 16; e++) { r[e] *= decay; sk += r[e] * kk[e]; }
        for (int off = L >> 1; off; off >>= 1) sk += __shfl_xor_sync(0xffffffff, sk, off);
        float d = bt * (vt - sk);
#pragma unroll
        for (int e = 0; e < 16; e++) { r[e] += d * kk[e]; oq += r[e] * qv[e]; }
        for (int off = L >> 1; off; off >>= 1) oq += __shfl_xor_sync(0xffffffff, oq, off);
        if (s == 0) o[(size_t)tok * nv * dv + vh * dv + j] = oq * scale;
        if (tok < min(nsnap, T - 1)) {
            float4* sr = (float4*)(snap + (size_t)tok * nv * dv * dk + ((size_t)vh * dv + j) * dk);
#pragma unroll
            for (int i = 0; i < 4; i++) sr[s + L * i] = make_float4(r[4 * i], r[4 * i + 1], r[4 * i + 2], r[4 * i + 3]);
        }
    }
#pragma unroll
    for (int i = 0; i < 4; i++) row[s + L * i] = make_float4(r[4 * i], r[4 * i + 1], r[4 * i + 2], r[4 * i + 3]);
}

// grid = heads: out = rmsnorm(o_h) * w * silu(z_h) (sigmoid(z_h) when sig), in place on o. xq not null: also quant_xq's layout of out (heads of
// a token are contiguous, so its rows are tokens) for the out GEMV.
extern "C" __global__ void norm_gate(float* o, const float* w, const float* z, int n, float eps, signed char* xq, int sig) {
    float* h = o + (size_t)blockIdx.x * n;
    const float* zh = z + (size_t)blockIdx.x * n;
    float s = 0.0f;
    for (int i = threadIdx.x; i < n; i += blockDim.x) s += h[i] * h[i];
    float sc = 1.0f / sqrtf(block_sum(s) / (float)n + eps);
    for (int i = threadIdx.x; i < n; i += blockDim.x) h[i] = h[i] * sc * w[i] * (sig ? sigmoid(zh[i]) : silu(zh[i]));
    if (!xq) return;
    __syncthreads();
    size_t b = (size_t)blockIdx.x * n;
    for (int i0 = 0; i0 < n; i0 += blockDim.x * 8) {
        int i = i0 + threadIdx.x * 8;
        unsigned m = __ballot_sync(0xffffffff, i < n);
        if (i < n) quant8(*(const float4*)(h + i), *(const float4*)(h + i + 4), i, xq + b, (float*)(xq + (size_t)gridDim.x * n) + b / 32, m);
    }
}

// ---- qwen4exp hyper-connections: the residual is hc streams of n values per token (rows of hc * n) ----

// x = silu(x * sc) over n values.
extern "C" __global__ void hc_silu(float* x, float sc, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) x[i] = silu(x[i] * sc);
}

// grid.y = tokens: out[t][i] = sum over streams c of xn[t][c n + i] * sigmoid(g[t][c n + i]) / hc.
extern "C" __global__ void hc_mix(const float* xn, const float* g, float* out, int n, int hc) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    size_t b = (size_t)blockIdx.y * hc * n + i;
    float s = 0.0f;
    for (int c = 0; c < hc; c++) s += xn[b + (size_t)c * n] * sigmoid(g[b + (size_t)c * n]) / (float)hc;
    out[(size_t)blockIdx.y * n + i] = s;
}

// grid.y = tokens: stream c of r[t] += out[t] * 2 sigmoid(inj[t][c] / hc); clear: out[t] = 0 afterwards.
extern "C" __global__ void hc_write(float* r, float* out, const float* inj, int n, int hc, int clear) {
    int i = blockIdx.x * blockDim.x + threadIdx.x, t = blockIdx.y;
    if (i >= n) return;
    float o = out[(size_t)t * n + i];
    for (int c = 0; c < hc; c++) r[((size_t)t * hc + c) * n + i] += o * (2.0f * sigmoid(inj[t * hc + c] / (float)hc));
    if (clear) out[(size_t)t * n + i] = 0.0f;
}

// PLE gate. Block (c, t): s = key . query over stream c of token t (rows of hc * n) / sqrt(n),
// gated[t][c n + i] = value[t][i] * sigmoid(sign(s) sqrt(max(|s|, 1e-6))).
extern "C" __global__ void ple_gate(const float* key, const float* query, const float* value, float* gated, int n) {
    size_t b = ((size_t)blockIdx.y * gridDim.x + blockIdx.x) * n;
    float s = 0.0f;
    for (int i = threadIdx.x; i < n; i += blockDim.x) s += key[b + i] * query[b + i];
    s = block_sum(s) / sqrtf((float)n);
    float gate = sigmoid((s > 0.0f ? 1.0f : s < 0.0f ? -1.0f : 0.0f) * sqrtf(fmaxf(fabsf(s), 1e-6f)));
    for (int i = threadIdx.x; i < n; i += blockDim.x) gated[b + i] = value[(size_t)blockIdx.y * n + i] * gate;
}

// PLE causal conv of d channels (4 taps, dilation 3) for nt tokens at positions step[0] ..: the normalized rows of
// earlier positions live in `ring` (16 rows of d, position p in row p % 16; none before position 0).
// r[t][i] += gated[t][i] + silu(kw[i][3] norm[t][i] + sum_k<3 kw[i][k] row(p - 9 + 3k)[i]), then row p = norm[t].
extern "C" __global__ void ple_conv(float* r, const float* gated, const float* norm, const float* kw, float* ring,
                                    const int* step, int d, int nt) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= d) return;
    for (int t = 0; t < nt; t++) {
        int p = step[0] + t;
        size_t o = (size_t)t * d + i;
        float acc = kw[i * 4 + 3] * norm[o];
        for (int k = 0; k < 3; k++) {
            int q = p - 9 + 3 * k;
            if (q >= 0) acc += kw[i * 4 + k] * ring[(size_t)(q & 15) * d + i];
        }
        r[o] += gated[o] + silu(acc);
        ring[(size_t)(p & 15) * d + i] = norm[o];
    }
}

// ---- attention ----

// KV cache rows (one per position and KV head) hold hd f16 values, or with KV_Q8 (`--kv q8`) hd int8 values followed
// by hd / 32 f16 scales, quantized like ggml's q8_0 (d = amax / 127 per 32 values). Offsets below count values.
#if KV_Q8
// Quantize x into the cache at value offset e; the 32 lanes of the warp hold one 32-value block.
__device__ __forceinline__ void kv_put(u16* c, size_t e, int hd, float x) {
    float d = warp_max(fabsf(x)) / 127.0f;
    int w = e % hd;
    char* r = (char*)c + e / hd * (hd + hd / 16);
    r[w] = (signed char)(d == 0.0f ? 0.0f : roundf(x / d));
    if ((w & 31) == 0) *(u16*)(r + hd + 2 * (w / 32)) = f2h(d);
}
#else
__device__ __forceinline__ void kv_put(u16* c, size_t e, int, float x) { c[e] = f2h(x); }
#endif

// Store `total` values (consecutive tokens of n each, n a multiple of 32) starting at position step[0].
extern "C" __global__ void kv_store(const float* k, const float* v, u16* kc, u16* vc, int n, int total, const int* step,
                                    int hd) {
    int i = blockIdx.x * blockDim.x + threadIdx.x, pos = step[0];
    if (i < total) { kv_put(kc, (size_t)pos * n + i, hd, k[i]); kv_put(vc, (size_t)pos * n + i, hd, v[i]); }
}

// grid = rows (heads of n), block 256: rms_norm (out rows of n) then rope_neox of the head, in one launch with the same
// bits. Head r belongs to token r / per. With kc, then kv_store of the head and its v (v rows of n, like out).
// Blocks below qrows do the q heads (from qx etc., no cache store); the rest do x etc.
__device__ __forceinline__ double rope_f(float base, int i, int n_rot) { return pow((double)base, -2.0 * i / n_rot); }
// fr[i] = rope_f(base, i, n_rot) for i < n_rot / 2, made once so rms_norm_rope skips the f64 pow.
extern "C" __global__ void rope_freq(double* fr, float base, int n_rot) {
    for (int i = threadIdx.x; i < n_rot / 2; i += blockDim.x) fr[i] = rope_f(base, i, n_rot);
}
// fr: the rope_freq table of base and n_rot, or null to compute it here.
extern "C" __global__ void rms_norm_rope(const float* x, int x_stride, const float* w, float* out, int n, float eps, int per,
                                         int n_rot, const int* step, float base, const float* v, u16* kc, u16* vc,
                                         int qrows, const float* qx, int q_stride, const float* qw, float* qo, int qper,
                                         const double* fr) {
    int b = (int)blockIdx.x - qrows;
    if (b < 0) { b = blockIdx.x; x = qx; x_stride = q_stride; w = qw; out = qo; per = qper; kc = 0; }
    const float* xr = x + (size_t)b * x_stride;
    float* o = out + (size_t)b * n;
    float s = 0.0f;
    for (int i = threadIdx.x; i < n; i += 256) s += xr[i] * xr[i];
    float sc = 1.0f / sqrtf(block_sum(s) / (float)n + eps);
    for (int i = threadIdx.x; i < n; i += 256) o[i] = xr[i] * sc * w[i];
    __syncthreads();
    int i = threadIdx.x, half = n_rot / 2;
    if (i < half) {
        double theta = (double)(step[0] + b / per) * (fr ? fr[i] : rope_f(base, i, n_rot));
        double ds, dc;
        sincos(theta, &ds, &dc);
        float sn = (float)ds, c = (float)dc;
        float a = o[i], b = o[i + half];
        o[i] = a * c - b * sn;
        o[i + half] = a * sn + b * c;
    }
    if (!kc) return;
    __syncthreads();
    const float* vr = v + (size_t)b * n;
    size_t e = ((size_t)(step[0] + b / per) * per + b % per) * n;
    for (int j = threadIdx.x; j < n; j += 256) { kv_put(kc, e + j, n, o[j]); kv_put(vc, e + j, n, vr[j]); }
}

#define INFINITY __int_as_float(0x7f800000)
// PER consecutive f16 values (p aligned to 2 * PER bytes) as PER / 2 words, with vector loads.
template <int PER> __device__ __forceinline__ void ldh_raw(const u16* p, unsigned* o) {
    if constexpr (PER >= 8) {
        for (int c = 0; c < PER / 8; c++) {
            uint4 v = ((const uint4*)p)[c];
            o[4 * c] = v.x; o[4 * c + 1] = v.y; o[4 * c + 2] = v.z; o[4 * c + 3] = v.w;
        }
    } else if constexpr (PER == 4) {
        uint2 v = *(const uint2*)p;
        o[0] = v.x; o[1] = v.y;
    } else {
        o[0] = *(const unsigned*)p;
    }
}
// PER consecutive cache values from value offset off (off a multiple of PER, PER <= 32) as f16 words, like ldh_raw.
template <int PER> __device__ __forceinline__ void ldkv(const u16* c, size_t off, int hd, unsigned* o) {
#if KV_Q8
    int w = off % hd;
    const char* r = (const char*)c + off / hd * (hd + hd / 16);
    unsigned d = *(const u16*)(r + hd + 2 * (w / 32)) * 0x10001u;  // scale in both halves
    // Byte q (flipped to q + 128) under exponent byte 0x64 is the f16 1024 + q + 128; minus 1152 gives q exactly, and
    // q * d rounded once to f16 equals f2h((float)q * d).
    auto deq = [&](unsigned x, unsigned sel) {
        unsigned h = __byte_perm(x ^ 0x80808080u, 0x64646464u, sel), r;
        asm("sub.rn.f16x2 %0, %1, %2;" : "=r"(h) : "r"(h), "r"(0x64806480u));
        asm("mul.rn.f16x2 %0, %1, %2;" : "=r"(r) : "r"(h), "r"(d));
        return r;
    };
    if (PER % 8 == 0 && hd % 128 == 0) {  // rows 8-byte aligned
        for (int i = 0; i < PER / 8; i++) {
            uint2 x = ((const uint2*)(r + w))[i];
            o[4 * i] = deq(x.x, 0x4140); o[4 * i + 1] = deq(x.x, 0x4342); o[4 * i + 2] = deq(x.y, 0x4140); o[4 * i + 3] = deq(x.y, 0x4342);
        }
    } else if constexpr (PER % 4 == 0) {
        for (int i = 0; i < PER / 4; i++) {
            unsigned x = ((const unsigned*)(r + w))[i];
            o[2 * i] = deq(x, 0x4140); o[2 * i + 1] = deq(x, 0x4342);
        }
    } else {
        for (int i = 0; i < PER / 2; i++) o[i] = deq(*(const u16*)(r + w + 2 * i), 0x4140);
    }
#else
    ldh_raw<PER>(c + off, o);
#endif
}
// f16 value d of words loaded by ldh_raw.
__device__ __forceinline__ float hraw(const unsigned* r, int d) { return h2f((u16)(r[d >> 1] >> (16 * (d & 1)))); }

// Sum v[0 .. N) over the warp; lane l returns the sum of v[l / (32 / N)]. Lanes trade halves of v instead of
// reducing each value alone: 31 shuffles for N = 32 instead of 160. Recursion on the half size S keeps every
// index constant, so v stays in registers.
template <int N, int S = N / 2> __device__ __forceinline__ float warp_sum_scatter(float* v) {
    if constexpr (S >= 1) {
        bool hi = threadIdx.x & (S * 32 / N);
#pragma unroll
        for (int i = 0; i < S; i++) {
            float keep = hi ? v[i + S] : v[i], send = hi ? v[i] : v[i + S];
            v[i] = keep + __shfl_xor_sync(0xffffffff, send, S * 32 / N);
        }
        return warp_sum_scatter<N, S / 2>(v);
    } else {
        float r = v[0];
#pragma unroll
        for (int o = 16 / N; o >= 1; o /= 2) r += __shfl_xor_sync(0xffffffff, r, o);
        return r;
    }
}

// --llama-numerics decode attention, as llama.cpp's CPU flash_attn_ext_f16_one_chunk computes it: q rounded to f16,
// positions in order, the V accumulator rounded to f16 after every scale and add. The KV length is padded to 256 and,
// from 512 on, split into LLAMA_NTH equal chunks (one per CPU thread) merged in f32; split s of the grid takes chunk s.
// Slow (one position at a time); for parity runs only.
#define LLAMA_NTH 6
__device__ __forceinline__ float rh(float x) { return h2f(f2h(x)); }
template <int HD, int G>
__device__ void attn_decode_llama(const float* q, const u16* kc, const u16* vc, float* part, const int* step,
                                  const int* sel, int nh, int nkv, float scale, int bx) {
    constexpr int R = (HD + 255) / 256;
    if (sel && sel[0] < 0) sel = nullptr;
    int n_pos = sel ? sel[0] : step[0] + 1, ns = gridDim.y, n_kv = (n_pos + 255) / 256 * 256;
    int nc = n_kv >= 512 ? LLAMA_NTH : 1, cs = (n_kv + nc - 1) / nc;
    int p0 = blockIdx.y * cs, p1 = blockIdx.y < nc ? min(n_pos, p0 + cs) : 0;
    int h0 = bx * G, g = h0 / (nh / nkv), w = threadIdx.x >> 5, lane = threadIdx.x & 31, nw = blockDim.x >> 5;
    extern __shared__ float sqh[];  // G * HD rounded query values (the launch gives 8 * hd floats)
    __shared__ float ss[G][32];
    for (int i = threadIdx.x; i < G * HD; i += blockDim.x) sqh[i] = rh(q[h0 * HD + i]);
    float acc[G][R], m[G], l[G];
    for (int i = 0; i < G; i++) { m[i] = -INFINITY; l[i] = 0.0f; for (int r = 0; r < R; r++) acc[i][r] = 0.0f; }
    __syncthreads();
    for (int t0 = p0; t0 < p1; t0 += 32) {
        int n = min(32, p1 - t0);
        for (int j = w; j < n; j += nw) {
            const u16* kr = kc + ((size_t)(sel ? sel[1 + t0 + j] : t0 + j) * nkv + g) * HD;
            for (int i = 0; i < G; i++) {
                float s = 0.0f;
                for (int d = lane; d < HD; d += 32) s += sqh[i * HD + d] * h2f(kr[d]);
                s = warp_sum(s);
                if (lane == 0) ss[i][j] = s * scale;
            }
        }
        __syncthreads();
        for (int j = 0; j < n; j++) {
            const u16* vr = vc + ((size_t)(sel ? sel[1 + t0 + j] : t0 + j) * nkv + g) * HD;
            for (int i = 0; i < G; i++) {
                float s = ss[i][j], ms = 1.0f, vs = 1.0f;
                if (s > m[i]) { ms = expf(m[i] - s); m[i] = s; for (int r = 0; r < R; r++) acc[i][r] = rh(acc[i][r] * ms); }
                else vs = expf(s - m[i]);
                for (int r = 0; r < R; r++) {
                    int d = threadIdx.x + 256 * r;
                    if (d < HD) acc[i][r] = rh(fmaf(h2f(vr[d]), vs, acc[i][r]));
                }
                l[i] = l[i] * ms + vs;
            }
        }
        __syncthreads();
    }
    for (int i = 0; i < G; i++) {
        float* pp = part + ((size_t)(h0 + i) * ns + blockIdx.y) * (HD + 2);
        for (int r = 0; r < R; r++) { int d = threadIdx.x + 256 * r; if (d < HD) pp[d] = acc[i][r]; }
        if (threadIdx.x == 0) { pp[HD] = m[i]; pp[HD + 1] = l[i]; }
    }
}

// Split-position decode attention. grid = (nh / G, ns splits): block (b, s) serves the G query heads b*G .. b*G+G-1
// (one KV head) over an ns-th of the positions, so each K/V row is read once for all G heads. The block walks its
// share in chunks of 32 positions (4 per warp, lane owns PER = hd / 32 consecutive dims): warps compute the chunk's
// scores, warp h runs the online softmax of head h over the chunk, then warps add the weighted V rows. All warps
// share one running max per head, so their partials just add up. The block writes per head its unnormalized partial
// [acc (hd) | max | sum] to part; attn_merge combines the splits.
// CP (f16 cache, the GQA entry point, head_dim 128 or 256): each lane copies its own slice of the next two chunks
// into shared memory while the block works on this one (cp.async on sm_80+, a synchronous store on sm_70, at the
// same program point). Only the lane that copies a slice reads it, so the copies need no barriers of their own.
// KV1: one chunk buffer, whose K and V halves each lane refills with the next chunk as soon as it has read them
// into registers.
// sel (QSA): when not null and sel[0] >= 0, the block attends to the sel[0] cells sel[1 ..] instead of 0 ..= step[0].
template <int PER, int G, bool CP = false, bool KV1 = false>
__device__ void attn_decode_t(const float* q, const u16* kc, const u16* vc, float* part, const int* step,
                              const int* sel, int nh, int nkv, float scale, int bx) {
    constexpr int hd = PER * 32, C = 32, J = C / 8;  // positions per chunk, per warp
#if LLAMA_Q8
    return attn_decode_llama<hd, G>(q, kc, vc, part, step, sel, nh, nkv, scale, bx);
#endif
    // At least 16 positions per split: short contexts use few blocks instead of many near-empty ones.
    if (sel && sel[0] < 0) sel = nullptr;
    auto cell = [&](int i) { return sel ? sel[1 + i] : i; };
    int n_pos = sel ? sel[0] : step[0] + 1, ns = gridDim.y, per_s = max((n_pos + ns - 1) / ns, 16);
    int p0 = blockIdx.y * per_s, p1 = min(n_pos, p0 + per_s);
    if (p0 >= n_pos) {  // empty split
        for (int i = 0; i < G; i++)
            for (int d = threadIdx.x; d < hd + 2; d += blockDim.x)
                part[((size_t)(bx * G + i) * ns + blockIdx.y) * (hd + 2) + d] = d == hd ? -INFINITY : 0.0f;
        return;
    }
    extern __shared__ float sq[];  // G * hd query values, then nw * hd warp partials; with CP the K/V chunks at 8 * hd
    constexpr int ST = KV1 ? 1 : 2;
    u16* kb = (u16*)(sq + 8 * hd);  // [ST][K, V][C][hd]
    __shared__ float ss[G][C], sc[G], sm[G], sl[G];
    int h0 = bx * G, g = h0 / (nh / nkv), w = threadIdx.x >> 5, lane = threadIdx.x & 31, nw = blockDim.x >> 5;
    for (int i = threadIdx.x; i < G * hd; i += blockDim.x) sq[i] = q[h0 * hd + i];
    float acc[G][PER], m = -INFINITY, l = 0.0f;  // m, l: running max and sum of head w (warps w < G)
#pragma unroll
    for (int i = 0; i < G; i++)
        for (int d = 0; d < PER; d++) acc[i][d] = 0.0f;
    // Positions past p1 copy or load the row p1 - 1 and keep zeros: a select, not a branch around the loads.
    // cp(c0, b, kv): copy this lane's K (kv bit 0) and V (bit 1) slices of the chunk at c0 into buffer b, as one
    // cp.async group on sm_80+ (no group to commit on sm_70, where the copies are synchronous).
    auto cp = [&](int c0, int b, int kv) {
        if (c0 < p1)
#pragma unroll
            for (int j = 0; j < J; j++) {
                size_t r = ((size_t)cell(min(c0 + w * J + j, p1 - 1)) * nkv + g) * hd + lane * PER;
                u16 *dk = kb + ((b * 2) * C + w * J + j) * hd + lane * PER, *dv = dk + C * hd;
                if constexpr (PER == 8) { if (kv & 1) cp_async16(dk, kc + r, true); if (kv & 2) cp_async16(dv, vc + r, true); }
                else { if (kv & 1) cp_async8(dk, kc + r, true); if (kv & 2) cp_async8(dv, vc + r, true); }
            }
        cp_async_commit();
    };
    if constexpr (KV1) { cp(p0, 0, 1); cp(p0, 0, 2); }
    else if constexpr (CP) { cp(p0, 0, 3); cp(p0 + C, 1, 3); }
    __syncthreads();
    for (int c0 = p0, it = 0; c0 < p1; c0 += C, it++) {
        unsigned kr[J][PER / 2], vr[J][PER / 2];
        // Two stages: groups commit as chunks 0 1 2 ..., so all but the newest gives this chunk. KV1 (one stage):
        // groups commit as K0 V0 K1 V1 ..., so all but the newest gives this chunk's K here and its V further down.
        // On sm_70 cp_async_wait is empty and each copy already happened in this lane's program order: no barrier.
        if constexpr (CP) {
            cp_async_wait<1>();  // sm_80+: chunk it%2 landed; sm_70: same-lane copy, no barrier needed
            asm volatile("" ::: "memory");  // the reads below stay after the wait
        }
#pragma unroll
        for (int j = 0; j < J; j++) {
            int t = c0 + w * J + j;
            if constexpr (CP) {
                const u16* sk = kb + (((it % ST) * 2) * C + w * J + j) * hd + lane * PER;
                ldh_raw<PER>(sk, kr[j]);
                if constexpr (!KV1) ldh_raw<PER>(sk + C * hd, vr[j]);
            } else {
                size_t r = ((size_t)cell(min(t, p1 - 1)) * nkv + g) * hd + lane * PER;
                ldkv<PER>(kc, r, hd, kr[j]); ldkv<PER>(vc, r, hd, vr[j]);
            }
            for (int d = 0; d < PER / 2; d++) if (t >= p1) kr[j][d] = vr[j][d] = 0;
        }
        if constexpr (KV1) {
            asm volatile("" ::: "memory");
            cp(c0 + C, 0, 1);
        }
        float kf[J][PER], p[J * G];
#pragma unroll
        for (int j = 0; j < J; j++)
            for (int d = 0; d < PER; d++) kf[j][d] = hraw(kr[j], d);
#pragma unroll
        for (int i = 0; i < G; i++) {
            float qv[PER];
            for (int d = 0; d < PER; d += 2) *(float2*)&qv[d] = *(const float2*)&sq[i * hd + lane * PER + d];
#pragma unroll
            for (int j = 0; j < J; j++) {
                float s = 0.0f;
                for (int d = 0; d < PER; d++) s += qv[d] * kf[j][d];
                p[j * G + i] = s;
            }
        }
        {
            constexpr int L = 32 / (J * G);  // lanes holding each score
            float s = warp_sum_scatter<J * G>(p);
            int k = lane / L, j = k / G;
            if (lane % L == 0) ss[k % G][w * J + j] = c0 + w * J + j < p1 ? s * scale : -INFINITY;
        }
        __syncthreads();
        if (w < G) {  // the chunk holds at least one position, so mn is finite
            float s = ss[w][lane], mn = fmaxf(m, warp_max(s)), e = expf(s - mn), cs = expf(m - mn);
            ss[w][lane] = e;
            l = l * cs + warp_sum(e); m = mn;
            if (lane == 0) sc[w] = cs;
        }
        __syncthreads();
        // V here, not between the rescale and the adds below: the refill's branch would split them, and they would
        // contract into other FMAs than in the two-stage path.
        if constexpr (KV1) {
            cp_async_wait<1>();  // sm_80+: this chunk's V landed; sm_70: same-lane copy, no barrier needed
            asm volatile("" ::: "memory");
#pragma unroll
            for (int j = 0; j < J; j++) {
                ldh_raw<PER>(kb + (C + w * J + j) * hd + lane * PER, vr[j]);
                for (int d = 0; d < PER / 2; d++) if (c0 + w * J + j >= p1) vr[j][d] = 0;
            }
            asm volatile("" ::: "memory");
            cp(c0 + C, 0, 2);
        }
#pragma unroll
        for (int i = 0; i < G; i++) {
            float cs = sc[i];
            for (int d = 0; d < PER; d++) acc[i][d] *= cs;
        }
#pragma unroll
        for (int j = 0; j < J; j++)
#pragma unroll
            for (int i = 0; i < G; i++) {
                float e = ss[i][w * J + j];
                for (int d = 0; d < PER; d++) acc[i][d] += e * hraw(vr[j], d);
            }
        __syncthreads();  // every lane has read buffer it%2 (lines above), so refilling it cannot clobber a live read
        if constexpr (CP && !KV1) cp(c0 + 2 * C, it % 2, 3);
    }
    if (w < G && lane == 0) { sm[w] = m; sl[w] = l; }
    float* sacc = sq;  // the queries are no longer needed (the loop ends on a barrier)
    // With CP the K/V buffers are free too (no copy is pending), so the partials of all G heads fit at once.
    if constexpr (CP && G * 8 <= 8 + 32 * ST) {
#pragma unroll
        for (int i = 0; i < G; i++)
            for (int d = 0; d < PER; d++) sacc[(i * nw + w) * hd + lane * PER + d] = acc[i][d];
        __syncthreads();
        for (int x = threadIdx.x; x < G * hd; x += blockDim.x) {
            int i = x / hd, d = x % hd;
            float o = 0.0f;
            for (int k = 0; k < nw; k++) o += sacc[(i * nw + k) * hd + d];
            part[((size_t)(h0 + i) * ns + blockIdx.y) * (hd + 2) + d] = o;
        }
        if (threadIdx.x < G) {
            float* pp = part + ((size_t)(h0 + threadIdx.x) * ns + blockIdx.y) * (hd + 2);
            pp[hd] = sm[threadIdx.x]; pp[hd + 1] = sl[threadIdx.x];
        }
        return;
    }
#pragma unroll
    for (int i = 0; i < G; i++) {
        for (int d = 0; d < PER; d++) sacc[w * hd + lane * PER + d] = acc[i][d];
        __syncthreads();
        float* pp = part + ((size_t)(h0 + i) * ns + blockIdx.y) * (hd + 2);
        for (int d = threadIdx.x; d < hd; d += blockDim.x) {
            float o = 0.0f;
            for (int k = 0; k < nw; k++) o += sacc[k * hd + d];
            pp[d] = o;
        }
        if (threadIdx.x == 0) { pp[hd] = sm[i]; pp[hd + 1] = sl[i]; }
        __syncthreads();
    }
}

// Two kernels, both in the decode graph unless gq_min fixes the regime; exactly one does work for a given context length. Below gq_min positions,
// nt query tokens: block x serves token x % nt and head block x / nt (tokens side by side, so their blocks run at
// the same time and share K/V rows in L2), with q, part and step at that token's offsets (pz part floats per token).
// attn_decode (grid (nh, ns1 splits)) serves one head per block. From gq_min on, attn_decode_gqa (grid (nh / G, splits))
// serves the G query heads of a KV head per block, reading each K/V row once; it needs ~230 registers per thread,
// so it is a separate entry point to keep attn_decode's occupancy. Both have one entry point per head size
// (attn_decode_128, ...): a switch over hd would give every size the registers of the largest.
#define ATT_ARGS const float* q, const u16* kc, const u16* vc, float* part, const int* step, int nh, int nkv, int hd, \
                 float scale, int gq_min, int pz, int nt, const int* sel, int sst
#define ATT_TOK int t = blockIdx.x % nt; q += (size_t)t * nh * hd; part += (size_t)t * pz; step += 2 * t; if (sel) sel += (size_t)t * sst;
#define ATT_RUN(G) attn_decode_t<PER, G>(q, kc, vc, part, step, sel, nh, nkv, scale, blockIdx.x / nt)
#define ATT_RUN_CP(G) attn_decode_t<PER, G, !KV_Q8 && (PER == 4 || (PER == 8 && __CUDA_ARCH__ >= 800))>(q, kc, vc, part, step, sel, nh, nkv, scale, blockIdx.x / nt)
#define DEF_ATT(HD)                                                                                          \
    extern "C" __global__ void attn_decode_##HD(ATT_ARGS) {                                                  \
        constexpr int PER = HD / 32; ATT_TOK                                                                 \
        if (step[0] + 1 < gq_min) ATT_RUN(1);                                                                \
    }                                                                                                        \
    extern "C" __global__ void attn_decode_gqa_##HD(ATT_ARGS) {                                              \
        constexpr int PER = HD / 32; ATT_TOK                                                                 \
        if (step[0] + 1 < gq_min) return;                                                                    \
        switch (nh * nt / gridDim.x) {                                                                       \
            case 1: ATT_RUN_CP(1); break;                                                                    \
            case 2: ATT_RUN_CP(2); break;                                                                    \
            case 4: if constexpr (PER <= 16) ATT_RUN_CP(4); break;                                           \
            case 8: if constexpr (PER <= 8) ATT_RUN_CP(8); break;                                            \
        }                                                                                                    \
    }
DEF_ATT(64) DEF_ATT(128) DEF_ATT(256) DEF_ATT(512)
// attn_decode_gqa for G = 4 at head_dim 128 with the f16 cache (Qwen3-4B and 8B, Llama 3 8B): one K/V stage
// refilled as soon as a lane has read it, and 80 registers, so 3 blocks share an SM (72 to 61 us per layer for
// Qwen3-4B at 4K on a 3060).
// Other group sizes lose with it: G = 8 spills its 32 accumulators, G = 2 gains nothing from the third block.
extern "C" __global__ void __launch_bounds__(256, 3) attn_decode_gqa4_128(ATT_ARGS) {
    constexpr int PER = 4; ATT_TOK
    if (step[0] + 1 < gq_min) return;
    if constexpr (!KV_Q8) attn_decode_t<PER, 4, true, true>(q, kc, vc, part, step, sel, nh, nkv, scale, blockIdx.x / nt);
}

// grid = query heads: out = (sum of split partials) / (sum of split sums) * sigmoid(gate), gate skipped when qg is null. Split 0 is never empty.
// xq not null: out is also quantized there as quant_xq does (not under LLAMA_Q8, whose scales span 256 values).
extern "C" __global__ void attn_merge(const float* part, const float* qg, float* out, int hd, int ns, const int* step,
                                       int ns1, int gq_min, signed char* xq) {
    int h = blockIdx.x;
    part += (size_t)blockIdx.z * gridDim.x * ns * (hd + 2); step += 2 * blockIdx.z;
    if (qg) qg += (size_t)blockIdx.z * gridDim.x * 2 * hd;
    out += (size_t)blockIdx.z * gridDim.x * hd;
    if (step[0] + 1 < gq_min) ns = ns1;  // attn_decode ran, not attn_decode_gqa
    const float* pp = part + (size_t)h * ns * (hd + 2);
    __shared__ float ws[256];  // split max, then split weight (ns <= blockDim.x <= 256)
    if (threadIdx.x < ns) ws[threadIdx.x] = pp[threadIdx.x * (hd + 2) + hd];
    __syncthreads();
    float M = -INFINITY, L = 0.0f;
    for (int s = 0; s < ns; s++) M = fmaxf(M, ws[s]);
    __syncthreads();
    if (threadIdx.x < ns) ws[threadIdx.x] = expf(ws[threadIdx.x] - M);
    __syncthreads();
    for (int s = 0; s < ns; s++) L += pp[s * (hd + 2) + hd + 1] * ws[s];
    for (int d = threadIdx.x; d < hd; d += blockDim.x) {
        float o = 0.0f;
        for (int s = 0; s < ns; s++) o += pp[s * (hd + 2) + d] * ws[s];
        o = o / L * (qg ? sigmoid(qg[h * 2 * hd + hd + d]) : 1.0f);
        out[h * hd + d] = o;
        if (xq) {  // hd is a multiple of 32: a warp holds one scale's 32 values
            float mx = warp_max(fabsf(o)), id = mx > 0.0f ? 127.0f / mx : 0.0f;
            size_t n = (size_t)gridDim.x * hd, i = blockIdx.z * n + h * hd + d;
            xq[i] = (signed char)__float2int_rn(o * id);
            if ((threadIdx.x & 31) == 0) ((float*)(xq + gridDim.z * n))[i >> 5] = mx / 127.0f;
        }
    }
}

// ---- MoE ----

// One warp routes one token: softmax over n logits, top-k (ties to the lower index), renormalized weights. Lane
// j < k gets the j-th expert's id and weight. The n <= 32 * TOPK_R logits stay in registers (lane holds
// i = lane + 32 r).
#define TOPK_R 16
__device__ void topk_warp(const float* p, int n, int k, float extra_scale, int lane, int& id, float& w) {
    float v[TOPK_R];
    float m = -INFINITY;
#pragma unroll
    for (int r = 0; r < TOPK_R; r++) { int i = lane + 32 * r; v[r] = i < n ? p[i] : -INFINITY; m = fmaxf(m, v[r]); }
    m = warp_max(m);
    float s = 0.0f;
#pragma unroll
    for (int r = 0; r < TOPK_R; r++) if (lane + 32 * r < n) { v[r] = expf(v[r] - m); s += v[r]; }
    s = warp_sum(s);
#pragma unroll
    for (int r = 0; r < TOPK_R; r++) v[r] /= s;
    unsigned taken = 0;
    float sum = 0.0f, mine = 0.0f;
    id = 0;
    for (int j = 0; j < k; j++) {
        // v >= 0, so its bits order like it; key = bits + 1 leaves 0 for "none". Max key, then the lowest index of it.
        unsigned bk = 0, bi = 0xffffffffu;
#pragma unroll
        for (int r = 0; r < TOPK_R; r++) {
            unsigned i = lane + 32 * r, key = __float_as_uint(v[r]) + 1;
            if (i < n && !(taken >> r & 1) && key > bk) { bk = key; bi = i; }
        }
#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ < 800
        unsigned mk = warp_max_u(bk);
        bi = warp_min_u(bk == mk ? bi : 0xffffffffu);
#else
        unsigned mk = __reduce_max_sync(0xffffffff, bk);
        bi = __reduce_min_sync(0xffffffff, bk == mk ? bi : 0xffffffffu);
#endif
        float bv = __uint_as_float(mk - 1);
        if ((bi & 31) == lane) taken |= 1u << (bi >> 5);
        if (lane == j) { id = bi; mine = bv; }
        sum += bv;
    }
    float scale = 1.0f / fmaxf(sum, 6.103515625e-5f);
    if (extra_scale != 0.0f) scale *= extra_scale;
    w = mine * scale;
}

// One warp per token (grid = tokens).
extern "C" __global__ void router_topk(const float* p, int n, int k, float extra_scale, int* ids, float* wts) {
    int id, o = blockIdx.x * k + threadIdx.x;
    float w;
    topk_warp(p + (size_t)blockIdx.x * n, n, k, extra_scale, threadIdx.x, id, w);
    if (threadIdx.x < k) { ids[o] = id; wts[o] = w; }
}

// Decode routing of T tokens in one block (warp i routes tokens i, i + 8, ...): router_topk, the expert cache lookup
// (slots = table[ids], -1 = not resident; wh = weight of hits, else 0), then the routing (and h, if an expert missed)
// copied to the host-mapped mailbox `mb`, T stored in word 1 and the request flag raised. `mb` = 0: the cache is fully
// resident, there is no CPU part to tell, so every mailbox store is skipped (the ids, weights, slots and wh stay valid
// for moe_gemv/moe_combine). `pid` (may be 0): last token's ids, the next token's prefetch prediction.
extern "C" __global__ void moe_route(const float* p, int n, int k, float extra_scale, const int* table, int* ids,
                                     float* wts, int* slots, float* wh, const float* h, unsigned int* mb, int nh,
                                     int h_off, const int* step, int T, int* pid) {
    __shared__ int miss;
    int lane = threadIdx.x & 31, kt = k * T;
    unsigned int seq = step[1];
    if (threadIdx.x == 0) miss = 0;
    __syncthreads();
    for (int t = threadIdx.x >> 5; t < T; t += blockDim.x >> 5) {
        int id;
        float w;
        topk_warp(p + (size_t)t * n, n, k, extra_scale, lane, id, w);
        if (lane < k) {
            int o = t * k + lane, s = table[id];
            ids[o] = id; wts[o] = w; slots[o] = s; wh[o] = s >= 0 ? w : 0.0f;
            if (mb) { mb[32 + o] = id; mb[32 + kt + o] = __float_as_uint(w); mb[32 + 2 * kt + o] = s; }
            if (pid && t == T - 1) pid[lane] = id;
            if (s < 0) miss = 1;
        }
    }
    __syncthreads();
    // No CPU part and so no flag to raise: nobody reads this layer's words (R2 of issue #34).
    if (!mb) return;
    if (threadIdx.x == 0) mb[1] = T;  // also read by routing() after the token
    // No miss: nobody waits on this layer. Raise only the skip flag, without the ~4 us system fence.
    if (!miss) { if (threadIdx.x == 0) ((volatile unsigned int*)mb)[2] = seq; return; }
    for (int i = threadIdx.x; i < nh * T; i += blockDim.x) mb[h_off + i] = __float_as_uint(h[i]);
    __threadfence_system();
    __syncthreads();
    if (threadIdx.x == 0) *(volatile unsigned int*)mb = seq;
}

// Hint into L2 the cached expert of each of the `k` experts `ids` (the previous token's routing of a layer), whole
// slot lines: the next layer's GEMVs may then find their rows in L2. `table[e] < 0` (expert on the CPU) is skipped.
// One block per expert (grid.y) and line range (grid.x). STRATA_MOE_PREFETCH=1 only; a hint, never a correctness
// dependency. Volta: prefetch.global.L2 exists since sm_20.
extern "C" __global__ void moe_prefetch(const int* ids, int k, const int* table, const char* base, int stride, int bytes) {
    int j = blockIdx.y;
    if (j >= k) return;
    int s = table[ids[j]];
    if (s < 0) return;
    const char* p = base + (size_t)((unsigned int)s * (unsigned int)stride);
    int lines = bytes >> 7;
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < lines; i += gridDim.x * blockDim.x)
        asm volatile("prefetch.global.L2 [%0];" ::"l"(p + ((size_t)i << 7)));
}

// x += sum_j w[j] ye[j] + sigmoid(sg) sh + cpu. If a slot missed, wait for the CPU worker's done flag first.
// grid.y = token: x, ye, w, slots, sh, sg and the CPU result advance by one token's worth.
extern "C" __global__ void moe_combine(float* x, const float* ye, const float* w, int k, const float* sh,
                                       const float* sg, const unsigned int* mb, int y_off, const int* step,
                                       const int* slots, int n) {
    unsigned int seq = step[1];
    int tk = blockIdx.y;
    x += (size_t)tk * n; ye += (size_t)tk * k * n; w += tk * k; slots += tk * k; y_off += tk * n;
    if (sh) { sh += (size_t)tk * n; sg += tk; }
    __shared__ int miss;
    if (threadIdx.x == 0) {
        int m = 0;
        if (mb) for (int j = 0; j < k; j++) m |= slots[j] < 0;
        if (m) {
            unsigned int spins = 0;
            while (((volatile const unsigned int*)mb)[16] != seq) {
                __nanosleep(100);
                if (++spins == (1u << 27)) __trap();  // ~15 s: CPU worker gone
            }
            __threadfence_system();
        }
        miss = m;
    }
    __syncthreads();
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    float y = 0.0f;
    for (int j = 0; j < k; j++) if (w[j] != 0.0f) y += w[j] * ye[(size_t)j * n + i];
    if (miss) y += __uint_as_float(((volatile const unsigned int*)mb)[y_off + i]);
    if (sh) y += sigmoid(sg[0]) * sh[i];
    x[i] += y;
}

// Prefill combine over T tokens: x[t] += sum_j wts[t, j] ye[inv[t, j]] + sigmoid(sg[t]) sh[t] (sh may be null).
extern "C" __global__ void moe_combine_seq(float* x, const float* ye, const float* wts, const int* inv, int k,
                                           const float* sh, const float* sg, int n, int T) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= T * n) return;
    int t = i / n, d = i % n;
    float y = 0.0f;
    for (int j = 0; j < k; j++) y += wts[t * k + j] * ye[(size_t)inv[t * k + j] * n + d];
    if (sh) y += sigmoid(sg[t]) * sh[i];
    x[i] += y;
}

// ---- attention prefill (flash, tensor cores) ----

// grid = (ceil(T / 64), heads), block = 128: warp w owns queries 16w .. 16w + 15 of the tile. Query t (position
// step[0] + t) attends to cached keys 0 .. step[0] + t. q is [T, nh * HD] after rope, qg [T, nh * 2 * HD] holds the
// gate at +HD per head; out [T, nh * HD] = softmax(q K^T * scale) V * sigmoid(gate). Shared: Q, K and V tiles, all
// row-major; mma fragments come from ldmatrix (.trans for V).
#ifndef FA_BQ
#define FA_BQ 64
#endif
#define FA_BK_DEFAULT FA_BK
// Turing's 64 KB shared memory cannot hold the HD = 256 tile at 32 keys either: 16 fit (the kernel keeps the same
// 64 queries a block and four warps).
#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ >= 750 && __CUDA_ARCH__ < 800
#define FA_BK_FOR(HD) ((HD) == 256 ? 16 : FA_BK_DEFAULT)
#else
#define FA_BK_FOR(HD) FA_BK_DEFAULT
#endif
#ifndef FA_BK
#define FA_BK 32
#endif
static_assert(FA_BQ == 16 * (128 / 32), "FA_BQ must be 16 query rows per warp of the 128-thread block");
// QSA mask (see qsa_select): whether query row t (mw words a row) sees key position `key`. The mask has rows for the
// tile padding past T too (their output is dropped).
__device__ __forceinline__ bool qsa_bit(const unsigned* qm, int mw, int t, int key) {
    return (qm[(size_t)t * mw + (key >> 7)] >> ((key >> 2) & 31)) & 1;
}
template <int HD>
__device__ __forceinline__ void attn_prefill_t(const float* q, const u16* kc, const u16* vc, const float* qg, float* out,
                                               const int* step, int T, int nh, int nkv, float scale, const unsigned* qm, int mw) {
    constexpr int PQ = HD + 8;
    constexpr int FA_BKL = FA_BK_FOR(HD);
    extern __shared__ __align__(16) u16 fa_sm[];
    u16 *qs = fa_sm, *ks = qs + FA_BQ * PQ, *vs = ks + FA_BKL * PQ;
#if __CUDA_ARCH__ < 800 && GEMM_TC
    // Volta only: warp-private P tile for the PV A fragments (see the staging in the PV step below). Appended after
    // `vs` so the qs/ks/vs offsets above do not move; FA_BQ * (FA_BKL + 8) halves = 5120 B.
    u16* ps = vs + FA_BKL * PQ;
#endif
    // The last query tiles see the most keys: start them first so the short ones fill the tail.
    int pos0 = step[0], q0 = (gridDim.x - 1 - blockIdx.x) * FA_BQ, h = blockIdx.y, kvh = h / (nh / nkv), kvd = nkv * HD;
    int tid = threadIdx.x, warp = tid >> 5, lane = tid & 31, g = lane >> 2, t4 = lane & 3;
    int lr = (lane & 7) + ((lane >> 3) & 1) * 8, lc = (lane >> 4) * 8;  // ldmatrix row / column offsets of this lane
    for (int i = tid; i < FA_BQ * HD / 4; i += 128) {
        int r = i / (HD / 4), c = (i % (HD / 4)) * 4;
        float4 v = q0 + r < T ? *(const float4*)(q + (size_t)(q0 + r) * nh * HD + h * HD + c) : make_float4(0.f, 0.f, 0.f, 0.f);
        *(uint2*)(qs + r * PQ + c) = make_uint2(h2pack(v.x * scale, v.y * scale), h2pack(v.z * scale, v.w * scale));
    }
    int last = pos0 + min(q0 + FA_BQ, T) - 1;  // last key any query of the tile sees
    int qp[2] = {pos0 + q0 + warp * 16 + g, pos0 + q0 + warp * 16 + g + 8};
    float o[HD / 8][4] = {}, m[2] = {-INFINITY, -INFINITY}, l[2] = {0.0f, 0.0f};
#if __CUDA_ARCH__ < 800 && GEMM_TC
    // Same storage as o / extra softmax state for the m8n8k4 layout (PTX ISA 8.5 §9.7.13.4.1). o2[j][grp][i] ==
    // &o[0][0][j * HD / 4 + grp * 8 + i]: the lane owns 4 rows (query half j, p2), so m and l need four entries each;
    // the m16n8k16 m / l above are dead here.
    float (&o2)[2][HD / 32][8] = reinterpret_cast<float (&)[2][HD / 32][8]>(o);
    float mT[2][2] = {{-INFINITY, -INFINITY}, {-INFINITY, -INFINITY}}, lT[2][2] = {};
#endif
    constexpr int N = FA_BKL * HD / 8 / 128;
#if !KV_Q8
    // f16: copy the V tile while the scores use K, and the next K tile while the sums use V (one block per SM,
    // so nothing else hides the loads); cp.async on sm_80+, a blocking copy at the same program point on sm_70.
    // Rows past `last` are zero-filled (synchronous path: the source is not read at all).
    auto ld = [&](int k0, u16* dst, const u16* src) {
#pragma unroll
        for (int n = 0; n < N; n++) {
            int i = tid + n * 128, r = i / (HD / 8), c = (i % (HD / 8)) * 8;
            cp_async16(dst + r * PQ + c, src + (size_t)min(k0 + r, last) * kvd + kvh * HD + c, k0 + r <= last);
        }
        cp_async_commit();
    };
    ld(0, ks, kc);
    ld(0, vs, vc);
#endif
    for (int k0 = 0; k0 <= last; k0 += FA_BKL) {
#if KV_Q8
        __syncthreads();
        // All of a thread's loads, then its stores: with q8 the dequant between them kept the compiler from
        // overlapping the loads. Rows past `last` load the row `last` and store zeros.
        uint4 kv[N], vv[N];
#pragma unroll
        for (int n = 0; n < N; n++) {
            int i = tid + n * 128, r = i / (HD / 8), c = (i % (HD / 8)) * 8;
            size_t off = (size_t)min(k0 + r, last) * kvd + kvh * HD + c;
            ldkv<8>(kc, off, HD, (unsigned*)&kv[n]); ldkv<8>(vc, off, HD, (unsigned*)&vv[n]);
        }
#pragma unroll
        for (int n = 0; n < N; n++) {
            int i = tid + n * 128, r = i / (HD / 8), c = (i % (HD / 8)) * 8;
            uint4 z = make_uint4(0, 0, 0, 0);
            *(uint4*)(ks + r * PQ + c) = k0 + r <= last ? kv[n] : z;
            *(uint4*)(vs + r * PQ + c) = k0 + r <= last ? vv[n] : z;
        }
#else
        cp_async_wait<1>();  // sm_80+: this K tile, its V tile may still be in flight; sm_70: already copied here
#endif
        __syncthreads();
        // QSA: the tile's 8 blocks are bits (k0 >> 2) & 31 .. + 7 of one mask word per row. A warp whose 16 rows see
        // none of them skips the tile (its keys would add exactly nothing).
#if __CUDA_ARCH__ < 800 && GEMM_TC
        // m8n8k4 query rows: the lane owns rows 8*j + (t & 1) + 2*p2 + 4*hi of the warp tile, so four `vis` words.
        int qp2[2][2];
        unsigned vis2[2][2];
#pragma unroll
        for (int j = 0; j < 2; j++)
#pragma unroll
            for (int p2 = 0; p2 < 2; p2++) {
                qp2[j][p2] = pos0 + q0 + warp * 16 + 8 * j + (t4 & 1) + 2 * p2 + 4 * (g >> 2);
                vis2[j][p2] = 0xff;
            }
        if (qm)
            for (int j = 0; j < 2; j++)
                for (int p2 = 0; p2 < 2; p2++)
                    vis2[j][p2] = (qm[(size_t)(qp2[j][p2] - pos0) * mw + (k0 >> 7)] >> ((k0 >> 2) & 31)) & 0xff;
        bool skip = qm && !__any_sync(0xffffffff, (vis2[0][0] | vis2[0][1] | vis2[1][0] | vis2[1][1]) != 0);
#else
        unsigned vis[2] = {0xff, 0xff};
        if (qm)
            for (int r = 0; r < 2; r++) vis[r] = (qm[(size_t)(qp[r] - pos0) * mw + (k0 >> 7)] >> ((k0 >> 2) & 31)) & 0xff;
        bool skip = qm && !__any_sync(0xffffffff, (vis[0] | vis[1]) != 0);
#endif
        float s[FA_BKL / 8][4] = {};
#if __CUDA_ARCH__ < 800 && GEMM_TC
        // Same 16 f32 storage as s, seen as m8n8k4 D registers: s2[ng][j][4*p4 + 2*p2 + e] is S[8*j + (t & 1) +
        // 2*p2 + 4*hi][8*(4*ng + c) + (t & 2) + 4*p4 + e] of the 16 x FA_BKL score tile. Every lane holds the four
        // computations its c selects, so the warp must stay in uniform control flow (`skip` is warp-uniform).
        float (&s2)[FA_BKL / 32][2][8] = reinterpret_cast<float (&)[FA_BKL / 32][2][8]>(s);
        if (!skip) {
            const int c = g & 3, hi = g >> 2;
#pragma unroll
            for (int kg = 0; kg < FA_BKL / 32; kg++)
#pragma unroll
                for (int kk = 0; kk < HD; kk += 16)
#pragma unroll
                    for (int j = 0; j < 2; j++) {
                        // A = Q rows 8*j + t + 4*hi of the warp tile, B = K row 8*(4*kg + c) + t + 4*hi, both at
                        // k 4*ks4 .. 4*ks4 + 3 ({a0,a1} = k 0..3 of the 8 x 4 A / 4 x 8 B fragments).
                        const u16* pa = qs + (warp * 16 + 8 * j + t4 + 4 * hi) * PQ + kk;
                        const u16* pb = ks + (8 * (4 * kg + c) + t4 + 4 * hi) * PQ + kk;
#pragma unroll
                        for (int ks4 = 0; ks4 < 4; ks4++)
                            mma884(s2[kg][j], ld_s32(pa + 4 * ks4), ld_s32(pa + 4 * ks4 + 2),
                                                ld_s32(pb + 4 * ks4), ld_s32(pb + 4 * ks4 + 2));
                    }
        }
#else
        if (!skip)
#pragma unroll
        for (int kk = 0; kk < HD; kk += 16) {
            u32 a[4], b[4];
            ldsm4<PQ, true>(a, qs + (warp * 16 + lr) * PQ + kk + lc);
            for (int nt = 0; nt < FA_BKL / 8; nt += 2) {
                // matrices: keys nt*8 / dims kk, keys nt*8 / dims kk+8, keys nt*8+8 / dims kk, keys nt*8+8 / dims kk+8
                ldsm4<PQ, false>(b, ks + (nt * 8 + (lane & 7) + (lane >> 4) * 8) * PQ + kk + ((lane >> 3) & 1) * 8);
                mma16816(s[nt], a[0], a[1], a[2], a[3], b[0], b[1]);
                mma16816(s[nt + 1], a[0], a[1], a[2], a[3], b[2], b[3]);
            }
        }
#endif
#if !KV_Q8
        __syncthreads();
        if (k0 + FA_BKL <= last) ld(k0 + FA_BKL, ks, kc);
        else cp_async_commit();  // keep one group per tile for the waits (sm_80+; nothing to commit on sm_70)
#endif
#if __CUDA_ARCH__ < 800 && GEMM_TC
        if (!skip) {
        const int c = g & 3, hi = g >> 2;
        // Mask, then the row max over the lane's keys and the three shuffles that reach the other eight lanes holding
        // this row (xor 2 swaps t & 2, xor 4 and 8 swap c: together they split the FA_BKL keys of the row). keep is
        // the rescale factor of each of the lane's four rows; lT is left unreduced inside the loop.
        float keep[2][2], ms2[2][2];
#pragma unroll
        for (int j = 0; j < 2; j++)
#pragma unroll
            for (int p2 = 0; p2 < 2; p2++) {
                float mx = mT[j][p2];
#pragma unroll
                for (int kg = 0; kg < FA_BKL / 32; kg++)
#pragma unroll
                    for (int p4 = 0; p4 < 2; p4++)
#pragma unroll
                        for (int e = 0; e < 2; e++) {
                            float& v = s2[kg][j][4 * p4 + 2 * p2 + e];
                            int key = k0 + 8 * (4 * kg + c) + (t4 & 2) + 4 * p4 + e;
                            if (key > qp2[j][p2] || !((vis2[j][p2] >> ((key >> 2) & 7)) & 1)) v = -INFINITY;
                            mx = fmaxf(mx, v);
                        }
                mx = fmaxf(mx, __shfl_xor_sync(0xffffffff, mx, 2));
                mx = fmaxf(mx, __shfl_xor_sync(0xffffffff, mx, 4));
                mx = fmaxf(mx, __shfl_xor_sync(0xffffffff, mx, 8));
                // mx is -inf while a QSA mask has hidden every key so far (key 0 is visible without one).
                ms2[j][p2] = mx == -INFINITY ? 0.0f : mx;
                keep[j][p2] = expf(mT[j][p2] - ms2[j][p2]);
                mT[j][p2] = mx;
                lT[j][p2] *= keep[j][p2];
            }
#pragma unroll
        for (int j = 0; j < 2; j++)
#pragma unroll
            for (int p2 = 0; p2 < 2; p2++)
#pragma unroll
                for (int kg = 0; kg < FA_BKL / 32; kg++)
#pragma unroll
                    for (int p4 = 0; p4 < 2; p4++)
#pragma unroll
                        for (int e = 0; e < 2; e++) {
                            float p = expf(s2[kg][j][4 * p4 + 2 * p2 + e] - ms2[j][p2]);
                            s2[kg][j][4 * p4 + 2 * p2 + e] = p;
                            lT[j][p2] += p;
                        }
#pragma unroll
        for (int j = 0; j < 2; j++)
#pragma unroll
            for (int grp = 0; grp < HD / 32; grp++)
#pragma unroll
                for (int p4 = 0; p4 < 2; p4++)
#pragma unroll
                    for (int p2 = 0; p2 < 2; p2++) {
                        o2[j][grp][4 * p4 + 2 * p2] *= keep[j][p2];
                        o2[j][grp][4 * p4 + 2 * p2 + 1] *= keep[j][p2];
                    }
        }
#else
        if (!skip) {
        float mx[2] = {m[0], m[1]};
        for (int nt = 0; nt < FA_BKL / 8; nt++)
            for (int e = 0; e < 4; e++) {
                int key = k0 + nt * 8 + 2 * t4 + (e & 1), r = e >> 1;
                if (key > qp[r] || !((vis[r] >> ((key >> 2) & 7)) & 1)) s[nt][e] = -INFINITY;
                mx[r] = fmaxf(mx[r], s[nt][e]);
            }
        float c[2], ms[2];
        for (int r = 0; r < 2; r++) {
            mx[r] = fmaxf(mx[r], __shfl_xor_sync(0xffffffff, mx[r], 1));
            mx[r] = fmaxf(mx[r], __shfl_xor_sync(0xffffffff, mx[r], 2));
            // mx is -inf while a QSA mask has hidden every key so far (key 0 is visible without one).
            ms[r] = mx[r] == -INFINITY ? 0.0f : mx[r];
            c[r] = expf(m[r] - ms[r]);
            m[r] = mx[r];
            l[r] *= c[r];
        }
        for (int nt = 0; nt < FA_BKL / 8; nt++)
            for (int e = 0; e < 4; e++) { float p = expf(s[nt][e] - ms[e >> 1]); s[nt][e] = p; l[e >> 1] += p; }
#pragma unroll
        for (int d = 0; d < HD / 8; d++) { o[d][0] *= c[0]; o[d][1] *= c[0]; o[d][2] *= c[1]; o[d][3] *= c[1]; }
        }
#endif
#if !KV_Q8
        cp_async_wait<1>();  // sm_80+: this V tile, the next K tile may still be in flight; sm_70: already copied here
        __syncthreads();
#endif
#if __CUDA_ARCH__ < 800 && GEMM_TC
        // P -> the warp-private staging tile: the m8n8k4 A fragment of the PV product wants row t + 4*hi and four
        // contiguous keys per lane, which the QK^T D layout does not give for free. One 32-bit store per half pair;
        // the __syncwarp() publishes the tile to the mma step below (the next tile's stores follow the loop's
        // __syncthreads(), so no other barrier is needed).
        if (!skip) {
            const int c = g & 3, hi = g >> 2;
#pragma unroll
            for (int kg = 0; kg < FA_BKL / 32; kg++)
#pragma unroll
                for (int j = 0; j < 2; j++)
#pragma unroll
                    for (int p2 = 0; p2 < 2; p2++)
#pragma unroll
                        for (int p4 = 0; p4 < 2; p4++)
                            *(u32*)(ps + (warp * 16 + 8 * j + (t4 & 1) + 2 * p2 + 4 * hi) * (FA_BKL + 8)
                                       + 8 * (4 * kg + c) + (t4 & 2) + 4 * p4) =
                                h2pack(s2[kg][j][4 * p4 + 2 * p2], s2[kg][j][4 * p4 + 2 * p2 + 1]);
            __syncwarp();
            // O[8*j + (t & 1) + 2*p2 + 4*hi][8*(4*grp + c) + (t & 2) + 4*p4 + e] += sum over the tile's keys of
            // P * V: A from ps (four contiguous keys per lane), B is the transposed V tile, column t + 4*hi, key
            // 4*kg + 0..3 as two half-pairs (the same two 16-bit loads per register that ldsm4t emulation costs).
#pragma unroll
            for (int kg = 0; kg < FA_BKL / 4; kg++)
#pragma unroll
                for (int j = 0; j < 2; j++) {
                    const u16* pa = ps + (warp * 16 + 8 * j + t4 + 4 * hi) * (FA_BKL + 8) + 4 * kg;
                    u32 a0 = ld_s32(pa), a1 = ld_s32(pa + 2);
#pragma unroll
                    for (int grp = 0; grp < HD / 32; grp++) {
                        const u16* pb = vs + 4 * kg * PQ + 8 * (4 * grp + c) + t4 + 4 * hi;
                        u32 b0 = (u32)pb[0] | ((u32)pb[PQ] << 16);
                        u32 b1 = (u32)pb[2 * PQ] | ((u32)pb[3 * PQ] << 16);
                        mma884(o2[j][grp], a0, a1, b0, b1);
                    }
                }
        }
#else
        if (!skip)
#pragma unroll
        for (int kb = 0; kb < FA_BKL / 16; kb++) {
            u32 a0 = h2pack(s[2 * kb][0], s[2 * kb][1]), a1 = h2pack(s[2 * kb][2], s[2 * kb][3]);
            u32 a2 = h2pack(s[2 * kb + 1][0], s[2 * kb + 1][1]), a3 = h2pack(s[2 * kb + 1][2], s[2 * kb + 1][3]);
#pragma unroll
            for (int d = 0; d < HD / 8; d += 2) {
                u32 b[4];  // transposed: keys kb*16 / dims d*8, keys +8 / dims d*8, keys / dims d*8+8, keys +8 / dims d*8+8
                ldsm4t<PQ, true>(b, vs + (kb * 16 + lr) * PQ + d * 8 + lc);
                mma16816(o[d], a0, a1, a2, a3, b[0], b[1]);
                mma16816(o[d + 1], a0, a1, a2, a3, b[2], b[3]);
            }
        }
#endif
#if !KV_Q8
        __syncthreads();
        if (k0 + FA_BKL <= last) ld(k0 + FA_BKL, vs, vc);
        else cp_async_commit();  // keep one group per tile for the waits (sm_80+; nothing to commit on sm_70)
#endif
    }
#if __CUDA_ARCH__ < 800 && GEMM_TC
    const int c = g & 3, hi = g >> 2;
    // One reduction of the lane's row sums after the last tile: the eight lanes holding a row split its keys.
#pragma unroll
    for (int j = 0; j < 2; j++)
#pragma unroll
        for (int p2 = 0; p2 < 2; p2++) {
            lT[j][p2] += __shfl_xor_sync(0xffffffff, lT[j][p2], 2);
            lT[j][p2] += __shfl_xor_sync(0xffffffff, lT[j][p2], 4);
            lT[j][p2] += __shfl_xor_sync(0xffffffff, lT[j][p2], 8);
        }
    // gemm_q's sm_70 store loop: register i = 4*p4 + 2*p2 + e sits at row (t & 1) + 2*p2 + 4*hi and column
    // (t & 2) + 4*p4 + e of the 8x8 tile.
#pragma unroll
    for (int j = 0; j < 2; j++)
#pragma unroll
        for (int grp = 0; grp < HD / 32; grp++)
#pragma unroll
            for (int p2 = 0; p2 < 2; p2++) {
                int row = q0 + warp * 16 + 8 * j + (t4 & 1) + 2 * p2 + 4 * hi;
                if (row >= T) continue;
                float* orow = out + (size_t)row * nh * HD + h * HD;
                const float* gate = qg ? qg + (size_t)row * nh * 2 * HD + h * 2 * HD + HD : nullptr;
#pragma unroll
                for (int p4 = 0; p4 < 2; p4++)
#pragma unroll
                    for (int e = 0; e < 2; e++) {
                        int col = 8 * (4 * grp + c) + (t4 & 2) + 4 * p4 + e;
                        orow[col] = o2[j][grp][4 * p4 + 2 * p2 + e] / lT[j][p2] * (gate ? sigmoid(gate[col]) : 1.0f);
                    }
            }
#else
    for (int r = 0; r < 2; r++) {
        l[r] += __shfl_xor_sync(0xffffffff, l[r], 1);
        l[r] += __shfl_xor_sync(0xffffffff, l[r], 2);
    }
#pragma unroll
    for (int r = 0; r < 2; r++) {
        int t = q0 + warp * 16 + g + 8 * r;
        if (t >= T) continue;
        float* orow = out + (size_t)t * nh * HD + h * HD;
        const float* gate = qg ? qg + (size_t)t * nh * 2 * HD + h * 2 * HD + HD : nullptr;
#pragma unroll
        for (int d = 0; d < HD / 8; d++)
            for (int e = 0; e < 2; e++) {
                int col = d * 8 + 2 * t4 + e;
                orow[col] = o[d][2 * r + e] / l[r] * (gate ? sigmoid(gate[col]) : 1.0f);
            }
    }
#endif
}
// --llama-numerics prefill attention: f32 throughout, like llama.cpp's CPU tiled path (the tensor-core kernel above
// rounds q and the softmax weights to f16). One query at a time per block; slow, for parity runs only.
template <int HD>
__device__ void attn_prefill_llama(const float* q, const u16* kc, const u16* vc, const float* qg, float* out,
                                   const int* step, int T, int nh, int nkv, float scale, const unsigned* qm, int mw) {
    constexpr int R = (HD + 127) / 128;
    extern __shared__ __align__(16) u16 fa_sm[];
    float *sq = (float*)fa_sm, *sc = sq + HD;
    int h = blockIdx.y, kvh = h / (nh / nkv), tid = threadIdx.x, w = tid >> 5, lane = tid & 31;
    for (int t = blockIdx.x * FA_BQ; t < min(T, blockIdx.x * FA_BQ + FA_BQ); t++) {
        int p = step[0] + t;
        __syncthreads();
        for (int d = tid; d < HD; d += 128) sq[d] = q[(size_t)t * nh * HD + h * HD + d];
        float acc[R] = {}, m = -INFINITY, l = 0.0f;
        for (int k0 = 0; k0 <= p; k0 += 32) {
            int n = min(32, p + 1 - k0);
            __syncthreads();
            for (int j = w; j < n; j += 4) {
                const u16* kr = kc + ((size_t)(k0 + j) * nkv + kvh) * HD;
                float s = 0.0f;
                for (int d = lane; d < HD; d += 32) s += sq[d] * h2f(kr[d]);
                s = warp_sum(s);
                if (lane == 0) sc[j] = qm && !qsa_bit(qm, mw, t, k0 + j) ? -INFINITY : s * scale;
            }
            __syncthreads();
            float mn = m;
            for (int j = 0; j < n; j++) mn = fmaxf(mn, sc[j]);
            if (mn == -INFINITY) continue;  // every key so far hidden by the QSA mask
            float cs = expf(m - mn);
            l *= cs;
            for (int r = 0; r < R; r++) acc[r] *= cs;
            for (int j = 0; j < n; j++) {
                float e = expf(sc[j] - mn);
                l += e;
                const u16* vr = vc + ((size_t)(k0 + j) * nkv + kvh) * HD;
                for (int r = 0; r < R; r++) if (tid + 128 * r < HD) acc[r] += e * h2f(vr[tid + 128 * r]);
            }
            m = mn;
        }
        const float* gate = qg ? qg + (size_t)t * nh * 2 * HD + h * 2 * HD + HD : nullptr;
        for (int r = 0; r < R; r++) {
            int d = tid + 128 * r;
            if (d < HD) out[(size_t)t * nh * HD + h * HD + d] = acc[r] / l * (gate ? sigmoid(gate[d]) : 1.0f);
        }
    }
}
#define DEF_FA(HD) \
    extern "C" __global__ void __launch_bounds__(128) attn_prefill_##HD(const float* q, const u16* kc, const u16* vc, \
            const float* qg, float* out, const int* step, int T, int nh, int nkv, float scale, const unsigned* qm, int mw) { \
        if (LLAMA_Q8) attn_prefill_llama<HD>(q, kc, vc, qg, out, step, T, nh, nkv, scale, qm, mw);                   \
        else attn_prefill_t<HD>(q, kc, vc, qg, out, step, T, nh, nkv, scale, qm, mw);                               \
    }
DEF_FA(64) DEF_FA(128) DEF_FA(256)

// ---- QSA sparse attention indexer (qwen4exp, see Model::qsa) ----
// Raw indexer keys (128 dims) are pooled per block of 4 positions: mean, rms norm, NEOX rope at the block's first
// position. A query row scores each complete block by sum over its 4 heads of relu(q . k) / sqrt(128) and attends to
// the top `top` blocks plus the tail of its incomplete block; rows with at most `top` complete blocks stay dense.
#define QSA_D 128
#define QSA_H 4

// grid = t / 4 + 1, block = 128 (thread d owns dim d). t raw keys at positions p0 = step[0] ..; CTA i pools block
// p0 / 4 + i if this call completes it. Members before p0 come from `ring` (the raw keys of the last incomplete block,
// slot = position % 4); CTA 0, the only one reading the ring, then stores the keys of this call's incomplete block.
extern "C" __global__ void qsa_pool(const float* ik, float* ring, float* pool, const float* w, const int* step, int t,
                                    int n_rot, float base, float eps) {
    int d = threadIdx.x, p0 = step[0], b = p0 / 4 + blockIdx.x;
    __shared__ float sx[QSA_D];
    if (4 * b + 4 <= p0 + t) {
        float x = 0.0f;
        for (int m = 0; m < 4; m++) {
            int p = 4 * b + m;
            x += (p >= p0 ? ik[(size_t)(p - p0) * QSA_D + d] : ring[(p & 3) * QSA_D + d]) / 4.0f;
        }
        float ss = block_sum(x * x);
        sx[d] = x * (1.0f / sqrtf(ss / QSA_D + eps)) * w[d];
        __syncthreads();
        int half = n_rot / 2, i = d < half ? d : d - half;
        float y = sx[d];
        if (d < n_rot) {
            double theta = (double)(4 * b) * pow((double)base, -2.0 * i / n_rot);
            float s = (float)sin(theta), c = (float)cos(theta);
            y = d < half ? sx[d] * c - sx[d + half] * s : sx[d - half] * s + sx[d] * c;
        }
        pool[(size_t)b * QSA_D + d] = y;
    }
    if (blockIdx.x == 0)
        for (int p = max(p0, (p0 + t) / 4 * 4); p < p0 + t; p++) ring[(p & 3) * QSA_D + d] = ik[(size_t)(p - p0) * QSA_D + d];
}

// grid = (64, ceil(rows / 8)), block = 256: warp w of CTA (x, y) scores blocks x * 8 + w, + 512, ... for query rows
// 8y .. 8y + 7 (row r at position step[0] + r0 + r, QSA_H normed and roped heads of QSA_D at q + r * QSA_H * QSA_D)
// into score[r * nbs + b]; the 8 rows share each pool read.
extern "C" __global__ void qsa_score(const float* q, const float* pool, float* score, const int* step, int r0, int rows,
                                     int nbs, int top) {
    __shared__ float4 sq[8 * QSA_H * QSA_D / 4];
    int r1 = blockIdx.y * 8, n = min(8, rows - r1), p0 = step[0] + r0 + r1, w = threadIdx.x >> 5, lane = threadIdx.x & 31;
    int nbm = (p0 + n) / 4;  // blocks of the tile's last row
    if (nbm <= top) return;
    for (int i = threadIdx.x; i < n * QSA_H * QSA_D / 4; i += blockDim.x) sq[i] = ((const float4*)(q + (size_t)r1 * QSA_H * QSA_D))[i];
    __syncthreads();
    for (int b = blockIdx.x * 8 + w; b < nbm; b += gridDim.x * 8) {
        float4 k = *(const float4*)(pool + (size_t)b * QSA_D + 4 * lane);
        for (int j = 0; j < n; j++) {
            int nb = (p0 + j + 1) / 4;
            if (nb <= top || b >= nb) continue;
            float s = 0.0f;
            for (int h = 0; h < QSA_H; h++) {
                float4 qv = sq[(j * QSA_H + h) * (QSA_D / 4) + lane];
                s += fmaxf(warp_sum(qv.x * k.x + qv.y * k.y + qv.z * k.z + qv.w * k.w), 0.0f);
            }
            if (lane == 0) score[(size_t)(r1 + j) * nbs + b] = s / sqrtf((float)QSA_D);
        }
    }
}

// Exclusive prefix sum over the block (1024 threads); `tot` gets the total.
__device__ int block_scan(int v, int* tot) {
    __shared__ int ws[32];
    int lane = threadIdx.x & 31, w = threadIdx.x >> 5, x = v;
    for (int o = 1; o < 32; o <<= 1) { int y = __shfl_up_sync(0xffffffff, x, o); if (lane >= o) x += y; }
    __syncthreads();
    if (lane == 31) ws[w] = x;
    __syncthreads();
    if (w == 0) {
        int s = ws[lane];
        for (int o = 1; o < 32; o <<= 1) { int y = __shfl_up_sync(0xffffffff, s, o); if (lane >= o) s += y; }
        ws[lane] = s;
    }
    __syncthreads();
    *tot = ws[31];
    return x - v + (w ? ws[w - 1] : 0);
}

// grid = rows, block = 1024: the top `top` blocks of row r by score (ties to the lower block), in block order.
// mw = 0: sel row r (sst ints) = [cell count, cells...] with the 4 cells of each block, then the tail, or count -1
// for a dense row. mw > 0: bit b of mask row r (mw words) set for each selected block and the tail block (all bits
// for a dense row); the caller's causal check hides the cells past the row's position.
extern "C" __global__ void __launch_bounds__(1024) qsa_select(const float* score, int* sel, unsigned* mask, const int* step,
                                                              int r0, int nbs, int top, int sst, int mw) {
    int r = blockIdx.x, pos = step[0] + r0 + r, nb = (pos + 1) / 4, tid = threadIdx.x;
    const unsigned* u = (const unsigned*)score + (size_t)r * nbs;  // scores are >= +0: their bits order as the values
    sel += (size_t)r * sst; mask += (size_t)r * mw;
    if (nb <= top) {
        if (mw) for (int i = tid; i < mw; i += blockDim.x) mask[i] = ~0u;
        else if (tid == 0) sel[0] = -1;
        return;
    }
    // Radix select, 8 bits a pass from the top: thr = the top-th largest bits, kk = how many equal to thr to take.
    __shared__ int hist[256];
    __shared__ unsigned sthr;
    __shared__ int skk;
    unsigned thr = 0, hi = 0;
    int kk = top;
    for (int sh = 24; sh >= 0; sh -= 8) {
        for (int i = tid; i < 256; i += blockDim.x) hist[i] = 0;
        __syncthreads();
        for (int i = tid; i < nb; i += blockDim.x) if ((u[i] & hi) == thr) atomicAdd(&hist[(u[i] >> sh) & 255], 1);
        __syncthreads();
        if (tid == 0) {
            int bin = 255;
            for (; bin > 0 && kk > hist[bin]; bin--) kk -= hist[bin];
            sthr = thr | (unsigned)bin << sh; skk = kk;
        }
        __syncthreads();
        thr = sthr; kk = skk; hi |= 255u << sh;
        __syncthreads();
    }
    if (mw) {
        for (int i = tid; i < mw; i += blockDim.x) mask[i] = 0;
        __syncthreads();
    }
    // Ordered compaction: thread tid walks blocks [tid * cs, ...) knowing the selections before its chunk.
    int cs = (nb + blockDim.x - 1) / blockDim.x, i0 = min(nb, tid * cs), i1 = min(nb, i0 + cs), gt = 0, eq = 0, tg, te;
    for (int i = i0; i < i1; i++) { gt += u[i] > thr; eq += u[i] == thr; }
    gt = block_scan(gt, &tg);
    eq = block_scan(eq, &te);
    for (int i = i0; i < i1; i++) {
        bool take = u[i] > thr || (u[i] == thr && eq < kk);
        if (take) {
            int o = gt + min(eq, kk);
            if (mw) atomicOr(&mask[i >> 5], 1u << (i & 31));
            else for (int m = 0; m < 4; m++) sel[1 + 4 * o + m] = 4 * i + m;
        }
        gt += u[i] > thr; eq += u[i] == thr;
    }
    if (mw) { if (tid == 0) atomicOr(&mask[nb >> 5], 1u << (nb & 31)); }
    else {
        for (int p = 4 * nb + tid; p <= pos; p += blockDim.x) sel[1 + 4 * top + p - 4 * nb] = p;
        if (tid == 0) sel[0] = 4 * top + pos + 1 - 4 * nb;
    }
}
