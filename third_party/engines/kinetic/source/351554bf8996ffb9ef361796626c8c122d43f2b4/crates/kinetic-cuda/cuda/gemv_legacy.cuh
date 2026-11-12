#pragma once

#include "kquant.cuh"

// GEMV for the 32-value formats Q4_0, Q4_1, Q5_0, Q5_1, IQ4_NL and MXFP4, stored
// planar on the device (see layout.rs): every block's 16 quant bytes, then
// each smaller field of every block in turn. Byte j of the quants holds
// element j in its low nibble and element j + 16 in its high one, so of the
// two lanes sharing a block, lane `part` takes nibble `part` of all sixteen.

__device__ __forceinline__ Words nibbles(const Words& q, unsigned part) {
    Words r;
#pragma unroll
    for (unsigned i = 0; i < 4; ++i) r.w[i] = (q.w[i] >> (4 * part)) & NIBBLES;
    return r;
}

// Bits 4i..4i+3 of `bits`, one per byte, moved to bit 4.
__device__ __forceinline__ int fifth_bits(unsigned bits, unsigned i) {
    return static_cast<int>(((((bits >> (4 * i)) & 0xF) * 0x00204081u) & 0x01010101u) << 4);
}

// The table entries of four codes 0..15, one per byte; the table's sixteen
// int8 values are packed little-endian into t.
__device__ __forceinline__ int lookup16(int codes, const unsigned (&t)[4]) {
    const unsigned c = static_cast<unsigned>(codes);
    const unsigned low = c & 0x07070707u;
    const unsigned packed = low | (low >> 4);
    const unsigned select = (packed & 0xFFu) | ((packed >> 8) & 0xFF00u);
    const unsigned high = ((c >> 3) & 0x01010101u) * 0xFFu;
    return static_cast<int>((__byte_perm(t[0], t[1], select) & ~high) |
                            (__byte_perm(t[2], t[3], select) & high));
}

__device__ __forceinline__ Words lookup16(const Words& codes, const unsigned (&t)[4]) {
    Words r;
#pragma unroll
    for (unsigned i = 0; i < 4; ++i) r.w[i] = lookup16(codes.w[i], t);
    return r;
}

// The IQ4_NL values and the MXFP4 (E2M1) values doubled to integers.
#define IQ4NL_TABLE {0xBFAD9881u, 0xF6EADDCFu, 0x26190D01u, 0x71594535u}
#define MXFP4_TABLE {0x03020100u, 0x0C080604u, 0xFDFEFF00u, 0xF4F8FAFCu}

// An E8M0 exponent as 2^(e - 128): half its scale, undoing the doubling.
__device__ __forceinline__ float e8m0_half(unsigned e) {
    return __uint_as_float(e < 2 ? 0x00200000u << e : (e - 1) << 23);
}

__device__ __forceinline__ float q8_dot(float scale, unsigned b, unsigned part, const Words& q,
                                        Q8Input x) {
    const int sum = dot16(q, load_cached(x.qs + b * 32 + 16 * part));
    return __fmul_rn(__fmul_rn(scale, __ldg(x.ds + b).x), static_cast<float>(sum));
}

// Formats with an offset m: the block's m times the scaled sum of all 32
// inputs is added once, by lane 0.
__device__ __forceinline__ float q8_dot_offset(float2 dm, unsigned b, unsigned part,
                                               const Words& q, Q8Input x) {
    const float2 xd = __ldg(x.ds + b);
    const int sum = dot16(q, load_cached(x.qs + b * 32 + 16 * part));
    const float offset = part == 0 ? __fmul_rn(dm.y, xd.y) : 0.0f;
    return __fadd_rn(__fmul_rn(__fmul_rn(dm.x, xd.x), static_cast<float>(sum)), offset);
}

struct GemvQ4_1 {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float2 dm;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const int dm = __ldg(reinterpret_cast<const int*>(w + total * 16) + blk);
        return {nibbles(load_weights(w + blk * 16), part), half2_bits(dm)};
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned part, Q8Input x) {
        return q8_dot_offset(k.dm, b, part, k.q, x);
    }
};

struct GemvQ4_0 {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const Words low = nibbles(load_weights(w + blk * 16), part);
        Block k;
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) k.q.w[i] = __vsub4(low.w[i], 0x08080808);
        k.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 16) + blk));
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned part, Q8Input x) {
        return q8_dot(k.d, b, part, k.q, x);
    }
};

// Bit j of the 32-bit qh is the fifth bit of element j.
struct GemvQ5_0 {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const unsigned qh =
            __ldg(reinterpret_cast<const unsigned*>(w + total * 16) + blk) >> (16 * part);
        const Words low = nibbles(load_weights(w + blk * 16), part);
        Block k;
#pragma unroll
        for (unsigned i = 0; i < 4; ++i)
            k.q.w[i] = __vsub4(low.w[i] | fifth_bits(qh, i), 0x10101010);
        k.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 20) + blk));
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned part, Q8Input x) {
        return q8_dot(k.d, b, part, k.q, x);
    }
};

struct GemvQ5_1 {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float2 dm;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const unsigned qh =
            __ldg(reinterpret_cast<const unsigned*>(w + total * 16) + blk) >> (16 * part);
        const Words low = nibbles(load_weights(w + blk * 16), part);
        Block k;
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) k.q.w[i] = low.w[i] | fifth_bits(qh, i);
        k.dm = half2_bits(__ldg(reinterpret_cast<const int*>(w + total * 20) + blk));
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned part, Q8Input x) {
        return q8_dot_offset(k.dm, b, part, k.q, x);
    }
};

struct GemvIQ4_NL {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const unsigned table[4] = IQ4NL_TABLE;
        return {lookup16(nibbles(load_weights(w + blk * 16), part), table),
                __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 16) + blk))};
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned part, Q8Input x) {
        return q8_dot(k.d, b, part, k.q, x);
    }
};

struct GemvMXFP4 {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const unsigned table[4] = MXFP4_TABLE;
        return {lookup16(nibbles(load_weights(w + blk * 16), part), table),
                e8m0_half(__ldg(w + total * 16 + blk))};
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned part, Q8Input x) {
        return q8_dot(k.d, b, part, k.q, x);
    }
};

GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q4_0, GemvQ4_0)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q4_1, GemvQ4_1)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q5_0, GemvQ5_0)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q5_1, GemvQ5_1)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_iq4_nl, GemvIQ4_NL)
GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_mxfp4, GemvMXFP4)

// Element i of block `blk` of these formats, for the embedding lookup, with
// the reference dequantization's roundings.
struct Legacy32 {
    const uint8_t* w;
    size_t total, blk;
    unsigned i;

    __device__ unsigned code() const {
        const uint8_t byte = w[blk * 16 + i % 16];
        return i < 16 ? byte & 15 : byte >> 4;
    }

    __device__ unsigned fifth_bit() const {
        return ((reinterpret_cast<const unsigned*>(w + total * 16)[blk] >> i) & 1) << 4;
    }

    __device__ float2 dm(size_t offset) const {
        return half2_bits(reinterpret_cast<const int*>(w + offset)[blk]);
    }

    __device__ float d(size_t offset) const {
        return __half2float(reinterpret_cast<const __half*>(w + offset)[blk]);
    }

    __device__ float table(const unsigned (&t)[4]) const {
        return static_cast<float>(static_cast<int8_t>(lookup16(static_cast<int>(code()), t)));
    }
};

__device__ float q4_0_element(Legacy32 e) {
    return e.d(e.total * 16) * static_cast<float>(static_cast<int>(e.code()) - 8);
}

__device__ float q4_1_element(Legacy32 e) {
    const float2 dm = e.dm(e.total * 16);
    return __fadd_rn(__fmul_rn(static_cast<float>(e.code()), dm.x), dm.y);
}

__device__ float q5_0_element(Legacy32 e) {
    return e.d(e.total * 20) * static_cast<float>(static_cast<int>(e.code() | e.fifth_bit()) - 16);
}

__device__ float q5_1_element(Legacy32 e) {
    const float2 dm = e.dm(e.total * 20);
    return __fadd_rn(__fmul_rn(static_cast<float>(e.code() | e.fifth_bit()), dm.x), dm.y);
}

__device__ float iq4_nl_element(Legacy32 e) {
    const unsigned table[4] = IQ4NL_TABLE;
    return e.d(e.total * 16) * e.table(table);
}

__device__ float mxfp4_element(Legacy32 e) {
    const unsigned table[4] = MXFP4_TABLE;
    return e8m0_half(e.w[e.total * 16 + e.blk]) * e.table(table);
}
