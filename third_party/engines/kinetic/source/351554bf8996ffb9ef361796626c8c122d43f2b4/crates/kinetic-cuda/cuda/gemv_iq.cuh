#pragma once

#include "gemv_low_k.cuh"

// GEMV for the codebook formats IQ3_S, IQ2_S, IQ1_S and IQ1_M and the
// ternary TQ1_0 and TQ2_0, all in super-blocks of 256 stored planar on the
// device (see layout.rs), the codebook following the planes at the next
// multiple of 16 bytes. Eight lanes share a block: lane p builds its 32
// weights, elements 32p..32p+31 and input block p of the 256, as int8 and
// multiplies them with dp4a; the scales follow in f32.

// Byte offset of the codebook after `total` blocks of `bytes` each.
__device__ __forceinline__ size_t grid_at(size_t total, unsigned bytes) {
    return (total * bytes + 15) / 16 * 16;
}

// Negates the bytes of `v` whose bit in the low four bits of `signs` is set.
__device__ __forceinline__ int negate_bytes(int v, unsigned signs) {
    const unsigned m = (signs & 1) * 0xFFu | (signs >> 1 & 1) * 0xFF00u |
                       (signs >> 2 & 1) * 0xFF0000u | (signs >> 3 & 1) * 0xFF000000u;
    return static_cast<int>(__vsub4(static_cast<unsigned>(v) ^ m, m));
}

__device__ __forceinline__ float plane_half(const uint8_t* p) {
    return __half2float(__ldg(reinterpret_cast<const __half*>(p)));
}

__device__ __forceinline__ unsigned plane_u16(const uint8_t* p) {
    return __ldg(reinterpret_cast<const unsigned short*>(p));
}

// The two words of IQ2_S and IQ1 codebook entry `i`, eight bytes each.
__device__ __forceinline__ int2 grid8(const uint8_t* grid, unsigned i) {
    return __ldg(reinterpret_cast<const int2*>(grid) + i);
}

// Products of lane p's 32 weights with its input block, and of their sum.
__device__ __forceinline__ int lane_dot(const Words (&q)[2], unsigned b, unsigned p, Q8Input x) {
    const int8_t* xp = x.qs + b * 256 + 32 * p;
    return dot16(q[0], load_cached(xp), dot16(q[1], load_cached(xp + 16)));
}

__device__ __forceinline__ float input_scale(unsigned b, unsigned p, Q8Input x) {
    return __ldg(x.ds + b * 8 + p).x;
}

// IQ3_S: qs (64), qh (8), signs (32), scales (4), d. Lane p reads groups of
// four 8p..8p+7, with one 4-bit scale `s` giving d (1 + 2s).
struct GemvIQ3_S {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        int scale;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        const uint8_t* grid = w + grid_at(total, 110);
        const uint2 qs = __ldg(reinterpret_cast<const uint2*>(w + blk * 64) + p);
        const unsigned qh = __ldg(w + total * 64 + blk * 8 + p);
        const unsigned signs = __ldg(reinterpret_cast<const unsigned*>(w + total * 72 + blk * 32) + p);
#pragma unroll
        for (unsigned g = 0; g < 8; ++g) {
            const unsigned byte = ((g < 4 ? qs.x : qs.y) >> (8 * (g % 4))) & 0xFF;
            const unsigned index = byte | ((qh >> g) & 1) << 8;
            const int v = __ldg(reinterpret_cast<const int*>(grid) + index);
            k.q[g / 4].w[g % 4] = negate_bytes(v, signs >> (4 * g));
        }
        const unsigned s = __ldg(w + total * 104 + blk * 4 + p / 2) >> (4 * (p % 2)) & 0xF;
        k.scale = 1 + 2 * static_cast<int>(s);
        k.d = plane_half(w + total * 108 + blk * 2);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int q = k.scale * lane_dot(k.q, b, p, x);
        return __fmul_rn(__fmul_rn(k.d, input_scale(b, p, x)), static_cast<float>(q));
    }
};

// IQ2_S: qs (32), signs (32), qh (8), scales (8), d. Lane p reads groups of
// eight 4p..4p+3; each half of the lane has a 4-bit scale `s` giving
// d (0.5 + s) / 4.
struct GemvIQ2_S {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        int scale[2];
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        const uint8_t* grid = w + grid_at(total, 82);
        const unsigned qs = __ldg(reinterpret_cast<const unsigned*>(w + blk * 32) + p);
        const unsigned signs = __ldg(reinterpret_cast<const unsigned*>(w + total * 32 + blk * 32) + p);
        const unsigned qh = __ldg(w + total * 64 + blk * 8 + p);
#pragma unroll
        for (unsigned g = 0; g < 4; ++g) {
            const unsigned index = (qs >> (8 * g) & 0xFF) | ((qh >> (2 * g)) & 3) << 8;
            const int2 v = grid8(grid, index);
            const unsigned s = signs >> (8 * g);
            k.q[g / 2].w[2 * (g % 2)] = negate_bytes(v.x, s);
            k.q[g / 2].w[2 * (g % 2) + 1] = negate_bytes(v.y, s >> 4);
        }
        const unsigned s = __ldg(w + total * 72 + blk * 8 + p);
        k.scale[0] = 1 + 2 * static_cast<int>(s & 0xF);
        k.scale[1] = 1 + 2 * static_cast<int>(s >> 4);
        k.d = plane_half(w + total * 80 + blk * 2);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int8_t* xp = x.qs + b * 256 + 32 * p;
        const int q = k.scale[0] * dot16(k.q[0], load_cached(xp)) +
                      k.scale[1] * dot16(k.q[1], load_cached(xp + 16));
        return __fmul_rn(__fmul_rn(k.d, input_scale(b, p, x)), 0.125f * static_cast<float>(q));
    }
};

// Eight weights of `q`, words 2g and 2g + 1, times the input, and the sum of
// those eight inputs, the codebook values in units of 1/8 with the delta
// `negative ? -1 : 1`.
__device__ __forceinline__ int iq1_group(const Words (&q)[2], const Words (&a)[2], unsigned g,
                                         bool negative) {
    const Words& w = q[g / 2];
    const Words& x = a[g / 2];
    const unsigned i = 2 * (g % 2);
    const int values = __dp4a(w.w[i], x.w[i], __dp4a(w.w[i + 1], x.w[i + 1], 0));
    const int sum = __dp4a(0x01010101, x.w[i], __dp4a(0x01010101, x.w[i + 1], 0));
    return 8 * values + (negative ? -sum : sum);
}

// IQ1_S: qs (32), qh (16), d. Lane p reads qh word p: three index bits per
// group of eight, a 3-bit scale `s` giving d (2s + 1) and the delta's sign.
struct GemvIQ1_S {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        unsigned qh;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        const uint8_t* grid = w + grid_at(total, 50);
        const unsigned qs = __ldg(reinterpret_cast<const unsigned*>(w + blk * 32) + p);
        k.qh = plane_u16(w + total * 32 + blk * 16 + 2 * p);
#pragma unroll
        for (unsigned g = 0; g < 4; ++g) {
            const unsigned index = (qs >> (8 * g) & 0xFF) | ((k.qh >> (3 * g)) & 7) << 8;
            const int2 v = grid8(grid, index);
            k.q[g / 2].w[2 * (g % 2)] = v.x;
            k.q[g / 2].w[2 * (g % 2) + 1] = v.y;
        }
        k.d = plane_half(w + total * 48 + blk * 2);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int8_t* xp = x.qs + b * 256 + 32 * p;
        const Words a[2] = {load_cached(xp), load_cached(xp + 16)};
        const bool negative = k.qh & 0x8000;
        int q = 0;
#pragma unroll
        for (unsigned g = 0; g < 4; ++g) q += iq1_group(k.q, a, g, negative);
        q *= 2 * static_cast<int>((k.qh >> 12) & 7) + 1;
        return __fmul_rn(__fmul_rn(k.d, input_scale(b, p, x)), 0.125f * static_cast<float>(q));
    }
};

// The IQ1_M block scale, an f16 spread over the top nibbles of the four
// words of the block's scales.
__device__ __forceinline__ float iq1_m_d(const uint8_t* scales) {
    const uint2 s = __ldg(reinterpret_cast<const uint2*>(scales));
    const unsigned bits = (s.x >> 12 & 0xF) | (s.x >> 24 & 0xF0) | (s.y >> 4 & 0xF00) |
                          (s.y >> 16 & 0xF000);
    return __half2float(__ushort_as_half(static_cast<unsigned short>(bits)));
}

// IQ1_M: qs (32), qh (16), scales (8). Each qh nibble gives a group of
// eight three index bits and its delta's sign; each sixteen values have a
// 3-bit scale `s` giving d (2s + 1).
struct GemvIQ1_M {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        unsigned qh;
        int scale[2];
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        const uint8_t* grid = w + grid_at(total, 56);
        const unsigned qs = __ldg(reinterpret_cast<const unsigned*>(w + blk * 32) + p);
        k.qh = plane_u16(w + total * 32 + blk * 16 + 2 * p);
#pragma unroll
        for (unsigned g = 0; g < 4; ++g) {
            const unsigned index = (qs >> (8 * g) & 0xFF) | ((k.qh >> (4 * g)) & 7) << 8;
            const int2 v = grid8(grid, index);
            k.q[g / 2].w[2 * (g % 2)] = v.x;
            k.q[g / 2].w[2 * (g % 2) + 1] = v.y;
        }
        const uint8_t* scales = w + total * 48 + blk * 8;
        const unsigned word = plane_u16(scales + 2 * (p / 2));
#pragma unroll
        for (unsigned h = 0; h < 2; ++h)
            k.scale[h] = 2 * static_cast<int>((word >> (3 * ((2 * p + h) % 4))) & 7) + 1;
        k.d = iq1_m_d(scales);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int8_t* xp = x.qs + b * 256 + 32 * p;
        const Words a[2] = {load_cached(xp), load_cached(xp + 16)};
        int q = 0;
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            const int half = iq1_group(k.q, a, 2 * h, k.qh >> (8 * h + 3) & 1) +
                             iq1_group(k.q, a, 2 * h + 1, k.qh >> (8 * h + 7) & 1);
            q += k.scale[h] * half;
        }
        return __fmul_rn(__fmul_rn(k.d, input_scale(b, p, x)), 0.125f * static_cast<float>(q));
    }
};

// Digit n of a byte of base-3 digits stored as the fraction byte / 256.
__device__ __forceinline__ int trit(unsigned byte, unsigned n) {
    constexpr unsigned POW3[5] = {1, 3, 9, 27, 81};
    return static_cast<int>(((byte * POW3[n]) & 0xFF) * 3 >> 8);
}

// Byte and digit of element i of a TQ1_0 block: five runs of 32 from the
// first 32 bytes, five of 16 from the next 16, four of 4 from the last 4.
__device__ __forceinline__ uint2 tq1_0_position(unsigned i) {
    if (i < 160) return make_uint2(i % 32, i / 32);
    if (i < 240) return make_uint2(32 + (i - 160) % 16, (i - 160) / 16);
    return make_uint2(48 + (i - 240) % 4, (i - 240) / 4);
}

// TQ1_0: qs (48), qh (4), d; values trit - 1.
struct GemvTQ1_0 {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        const uint8_t* qs = w + blk * 48;
        const uint8_t* qh = w + total * 48 + blk * 4;
#pragma unroll
        for (unsigned word = 0; word < 8; ++word) {
            unsigned v = 0;
#pragma unroll
            for (unsigned j = 0; j < 4; ++j) {
                const uint2 at = tq1_0_position(32 * p + 4 * word + j);
                const unsigned byte = at.x < 48 ? __ldg(qs + at.x) : __ldg(qh + at.x - 48);
                v |= static_cast<unsigned>(trit(byte, at.y) - 1 & 0xFF) << (8 * j);
            }
            k.q[word / 4].w[word % 4] = static_cast<int>(v);
        }
        k.d = plane_half(w + total * 52 + blk * 2);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int q = lane_dot(k.q, b, p, x);
        return __fmul_rn(__fmul_rn(k.d, input_scale(b, p, x)), static_cast<float>(q));
    }
};

// TQ2_0: qs (64) in the 2-bit planes of Q2_K, then d; values q - 1.
struct GemvTQ2_0 {
    static constexpr unsigned LANES = 8;
    static constexpr unsigned ELEMS = 256;

    struct Block {
        Words q[2];
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        load_planes(k.q, w + blk * 64, p);
#pragma unroll
        for (unsigned r = 0; r < 2; ++r)
#pragma unroll
            for (unsigned i = 0; i < 4; ++i)
                k.q[r].w[i] = static_cast<int>(__vsub4(k.q[r].w[i], 0x01010101));
        k.d = plane_half(w + total * 64 + blk * 2);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int q = lane_dot(k.q, b, p, x);
        return __fmul_rn(__fmul_rn(k.d, input_scale(b, p, x)), static_cast<float>(q));
    }
};

GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_iq3_s, GemvIQ3_S)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_iq2_s, GemvIQ2_S)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_iq1_s, GemvIQ1_S)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_iq1_m, GemvIQ1_M)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_tq1_0, GemvTQ1_0)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_tq2_0, GemvTQ2_0)

// Element i of block `blk`, for the embedding lookup, with the reference
// dequantization's roundings.
__device__ float iq3_s_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned k = i / 4;
    const unsigned index = w[blk * 64 + k] | ((w[total * 64 + blk * 8 + k / 8] >> (k % 8)) & 1) << 8;
    const float g = w[grid_at(total, 110) + 4 * index + i % 4];
    const unsigned s = w[total * 104 + blk * 4 + i / 64] >> (4 * (i / 32 % 2)) & 0xF;
    const float db = __fmul_rn(plane_half(w + total * 108 + blk * 2), static_cast<float>(1 + 2 * s));
    const bool negative = w[total * 72 + blk * 32 + k / 2] >> (4 * (k % 2) + i % 4) & 1;
    const float v = __fmul_rn(db, g);
    return negative ? -v : v;
}

__device__ float iq2_s_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned k = i / 8;
    const unsigned index = w[blk * 32 + k] | ((w[total * 64 + blk * 8 + k / 4] >> (2 * (k % 4))) & 3) << 8;
    const float g = w[grid_at(total, 82) + 8 * index + i % 8];
    const unsigned s = w[total * 72 + blk * 8 + k / 4] >> (4 * (k % 4 / 2)) & 0xF;
    const float d = plane_half(w + total * 80 + blk * 2);
    const float dl = __fmul_rn(__fmul_rn(d, 0.5f + static_cast<float>(s)), 0.25f);
    const bool negative = w[total * 32 + blk * 32 + k] >> (i % 8) & 1;
    const float v = __fmul_rn(dl, g);
    return negative ? -v : v;
}

__device__ float iq1_s_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned b = i / 32, l = i % 32 / 8;
    const unsigned qh = plane_u16(w + total * 32 + blk * 16 + 2 * b);
    const unsigned index = w[blk * 32 + 4 * b + l] | ((qh >> (3 * l)) & 7) << 8;
    const float g = static_cast<int8_t>(w[grid_at(total, 50) + 8 * index + i % 8]);
    const float dl = __fmul_rn(plane_half(w + total * 48 + blk * 2), static_cast<float>(2 * (qh >> 12 & 7) + 1));
    return __fmul_rn(dl, __fadd_rn(g, qh & 0x8000 ? -0.125f : 0.125f));
}

__device__ float iq1_m_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned k = i / 8;
    const unsigned h = w[total * 32 + blk * 16 + k / 2] >> (4 * (k % 2));
    const unsigned index = w[blk * 32 + k] | (h & 7) << 8;
    const float g = static_cast<int8_t>(w[grid_at(total, 56) + 8 * index + i % 8]);
    const uint8_t* scales = w + total * 48 + blk * 8;
    const unsigned word = plane_u16(scales + 2 * (k / 8));
    const float dl = __fmul_rn(iq1_m_d(scales), static_cast<float>(2 * (word >> (3 * (k / 2 % 4)) & 7) + 1));
    return __fmul_rn(dl, __fadd_rn(g, h & 8 ? -0.125f : 0.125f));
}

__device__ float tq1_0_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const uint2 at = tq1_0_position(i);
    const unsigned byte = at.x < 48 ? w[blk * 48 + at.x] : w[total * 48 + blk * 4 + at.x - 48];
    return __fmul_rn(static_cast<float>(trit(byte, at.y) - 1), plane_half(w + total * 52 + blk * 2));
}

__device__ float tq2_0_element(const uint8_t* w, size_t total, size_t blk, unsigned i) {
    const unsigned q = (w[blk * 64 + 32 * (i / 128) + i % 32] >> (2 * (i % 128 / 32))) & 3;
    return __fmul_rn(static_cast<float>(static_cast<int>(q) - 1), plane_half(w + total * 64 + blk * 2));
}
