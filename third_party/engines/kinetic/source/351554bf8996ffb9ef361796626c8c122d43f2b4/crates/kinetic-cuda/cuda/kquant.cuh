#pragma once

#include "common.cuh"

// K-quant GEMV, the order of arithmetic shared by the dp4a kernels
// (gemv_kquant.cuh) and the tensor-core kernels (gemv_mma.cuh), so that a
// vector gets bit-identical results from either, alone or in any batch.
//
// A row's quant blocks are dealt round-robin to KQ_SPLIT partial sums, each
// adding its blocks in order; the partial sums are then added in order. A
// block is the sum of one term per scale group (sub-blocks of 32 for Q4_K and
// Q5_K, runs of 16 for Q6_K), added as a balanced binary tree in group order:
// ((t0 + t1) + (t2 + t3)) + ... The term of a group whose exact integer dot
// product with the int8 input is `q` is `kq_term`, where `scale` and `min`
// are the block's d and dmin times the group's 6-bit or int8 values and
// (xd, xs) the input block's scale and scaled sum.

constexpr unsigned KQ_SPLIT = 4;
constexpr unsigned NIBBLES = 0x0F0F0F0F;

// Scale (x) and min (y) of sub-block s, from the packed bytes held as the
// little-endian words q0 = bytes 0..3, q1 = 4..7, q2 = 8..11.
__device__ __forceinline__ int2 k4_scale_min(unsigned s, unsigned q0, unsigned q1, unsigned q2) {
    if (s < 4) return make_int2((q0 >> (8 * s)) & 63, (q1 >> (8 * s)) & 63);
    const unsigned t = 8 * (s - 4);
    return make_int2(((q2 >> t) & 0x0F) | ((q0 >> t >> 2) & 0x30),
                     ((q2 >> t >> 4) & 0x0F) | ((q1 >> t >> 2) & 0x30));
}

// The scale and min of sub-block s of a Q4_K or Q5_K block with head `h`.
__device__ __forceinline__ float2 k4_group(const Words& h, unsigned s) {
    const int2 sm = k4_scale_min(s, h.w[1], h.w[2], h.w[3]);
    const float2 dm = half2_bits(h.w[0]);
    return make_float2(__fmul_rn(dm.x, static_cast<float>(sm.x)),
                       __fmul_rn(dm.y, static_cast<float>(sm.y)));
}

// The scale of run j of a Q6_K block with d `d`, given word j / 4 of its
// int8 scales.
__device__ __forceinline__ float k6_group(float d, unsigned scales, unsigned j) {
    return __fmul_rn(d, static_cast<float>(static_cast<int8_t>(scales >> (8 * (j % 4)))));
}

__device__ __forceinline__ float kq_term(float scale, float min, float xd, float xs, int q) {
    return fmaf(__fmul_rn(scale, xd), static_cast<float>(q), -__fmul_rn(min, xs));
}

// A balanced binary sum of 2^K terms pushed in order.
template <unsigned K>
struct TreeSum {
    float level[K + 1];

    // Term i, a constant once unrolled.
    __device__ __forceinline__ void push(unsigned i, float v) {
        unsigned l = 0;
        for (; i & 1; i >>= 1, ++l) v = __fadd_rn(level[l], v);
        level[l] = v;
    }

    __device__ __forceinline__ float total() const { return level[K]; }
};

// Q6_K run j of 16 (half n = j / 8, group g = (j % 8) / 2, l0 = 16 (j % 2)):
// low bits from ql bytes 64n + 32(g & 1) + l0 (high nibbles for g >= 2),
// top bits from qh bytes 32n + l0 shifted by 2g. Quants are stored + 32.
__device__ __forceinline__ int k6_stored(unsigned ql, unsigned qh, unsigned g) {
    return ((ql >> (4 * (g / 2))) & NIBBLES) | (((qh >> (2 * g)) & 0x03030303) << 4);
}

__device__ __forceinline__ int k6_quants(unsigned ql, unsigned qh, unsigned g) {
    return __vsub4(k6_stored(ql, qh, g), 0x20202020);
}
