#pragma once

#include "kquant.cuh"

// GEMV for Q2_K and Q3_K, stored planar on the device (see layout.rs): all
// 64-byte quant runs first, then each smaller field of every block in turn.
// Each 32-byte half of the quants holds four 2-bit planes of 32 elements,
// sixteen per scale group. Eight lanes share a block: lane p takes elements
// 32p..32p+31, plane p % 4 of half p / 4, which are groups 2p and 2p + 1 and
// input block p of the 256.

constexpr int LOW_BITS = 0x03030303;

// Lane p's 32 quants of a block whose quant runs start at `qs`.
__device__ __forceinline__ void load_planes(Words (&q)[2], const uint8_t* qs, unsigned p) {
    const unsigned shift = 2 * (p % 4);
#pragma unroll
    for (unsigned r = 0; r < 2; ++r) {
        const Words v = load_weights(qs + 32 * (p / 4) + 16 * r);
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) q[r].w[i] = (v.w[i] >> shift) & LOW_BITS;
    }
}

// The 6-bit Q3_K scale of group g, from the block's 12 packed scale bytes.
__device__ __forceinline__ int q3_k_scale(const uint8_t* s, unsigned g) {
    const unsigned low = (__ldg(s + g % 8) >> (4 * (g / 8))) & 0xF;
    const unsigned high = (__ldg(s + 8 + g % 4) >> (2 * (g / 4))) & 3;
    return static_cast<int>(low | high << 4) - 32;
}

// Q2_K: quants (64), then per block the sixteen bytes of group scale (low
// nibble) and min (high nibble), then d and dmin.
struct GemvQ2_K {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        unsigned scales;
        float2 dm;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        load_planes(k.q, w + blk * 64, p);
        k.scales = __ldg(reinterpret_cast<const unsigned short*>(w + total * 64 + blk * 16) + p);
        k.dm = half2_bits(__ldg(reinterpret_cast<const int*>(w + total * 80) + blk));
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int8_t* xp = x.qs + b * 256 + 32 * p;
        const Words a0 = load_cached(xp), a1 = load_cached(xp + 16);
        const Words ones = {{0x01010101, 0x01010101, 0x01010101, 0x01010101}};
        const int s = static_cast<int>(k.scales);
        const int q = (s & 0xF) * dot16(k.q[0], a0) + ((s >> 8) & 0xF) * dot16(k.q[1], a1);
        const int m = ((s >> 4) & 0xF) * dot16(ones, a0) + ((s >> 12) & 0xF) * dot16(ones, a1);
        const float xd = __ldg(x.ds + b * 8 + p).x;
        return fmaf(__fmul_rn(k.dm.x, xd), static_cast<float>(q),
                    -__fmul_rn(__fmul_rn(k.dm.y, xd), static_cast<float>(m)));
    }
};

// Q3_K: quants (64), then the high-bit masks (32), the packed scales (12)
// and d. Bit p of mask byte r belongs to byte r of lane p's quants; a clear
// bit subtracts 4.
struct GemvQ3_K {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        int scale[2];
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        load_planes(k.q, w + blk * 64, p);
#pragma unroll
        for (unsigned r = 0; r < 2; ++r) {
            const Words mask = load_weights(w + total * 64 + blk * 32 + 16 * r);
#pragma unroll
            for (unsigned i = 0; i < 4; ++i)
                k.q[r].w[i] = __vsub4(k.q[r].w[i] | (((mask.w[i] >> p) & 0x01010101) << 2),
                                      0x04040404);
        }
        const uint8_t* scales = w + total * 96 + blk * 12;
        k.scale[0] = q3_k_scale(scales, 2 * p);
        k.scale[1] = q3_k_scale(scales, 2 * p + 1);
        k.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 108) + blk));
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int8_t* xp = x.qs + b * 256 + 32 * p;
        const int q = k.scale[0] * dot16(k.q[0], load_cached(xp)) +
                      k.scale[1] * dot16(k.q[1], load_cached(xp + 16));
        return __fmul_rn(__fmul_rn(k.d, __ldg(x.ds + b * 8 + p).x), static_cast<float>(q));
    }
};

GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q2_k, GemvQ2_K)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q3_k, GemvQ3_K)

// Element i of block `blk`, for the embedding lookup, with the reference
// dequantization's roundings.
__device__ float q2_k_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned l = i % 128;
    const unsigned q = (w[blk * 64 + 32 * (i / 128) + l % 32] >> (2 * (l / 32))) & 3;
    const uint8_t s = w[total * 64 + blk * 16 + i / 16];
    const float2 dm = half2_bits(reinterpret_cast<const int*>(w + total * 80)[blk]);
    return __fsub_rn(__fmul_rn(__fmul_rn(dm.x, static_cast<float>(s & 15)), static_cast<float>(q)),
                     __fmul_rn(dm.y, static_cast<float>(s >> 4)));
}

__device__ float q3_k_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned l = i % 128;
    const unsigned low = (w[blk * 64 + 32 * (i / 128) + l % 32] >> (2 * (l / 32))) & 3;
    const unsigned high = (w[total * 64 + blk * 32 + l % 32] >> (i / 32)) & 1;
    const int scale = q3_k_scale(w + total * 96 + blk * 12, i / 16);
    const float d = __half2float(reinterpret_cast<const __half*>(w + total * 108)[blk]);
    return __fmul_rn(__fmul_rn(d, static_cast<float>(scale)),
                     static_cast<float>(static_cast<int>(low | high << 2) - 4));
}
