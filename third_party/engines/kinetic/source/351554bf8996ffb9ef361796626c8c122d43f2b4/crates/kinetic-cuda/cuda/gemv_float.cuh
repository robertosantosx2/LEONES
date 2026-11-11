#pragma once

#include "common.cuh"

// Float weights read the f32 input directly. A "block" is the 16 bytes one
// lane loads: 4 f32 or 8 f16 values.

struct GemvF32 {
    static constexpr unsigned LANES = 1;
    static constexpr unsigned ELEMS = 4;
    using Block = Words;

    __device__ static Block load(const uint8_t* w, size_t, size_t blk, unsigned) {
        return load_weights(w + blk * 16);
    }

    __device__ static float dot(const Block& v, unsigned b, unsigned, const float* x) {
        const float4 xv = __ldg(reinterpret_cast<const float4*>(x) + b);
        float r = __fmul_rn(__int_as_float(v.w[0]), xv.x);
        r = fmaf(__int_as_float(v.w[1]), xv.y, r);
        r = fmaf(__int_as_float(v.w[2]), xv.z, r);
        return fmaf(__int_as_float(v.w[3]), xv.w, r);
    }
};

struct GemvF16 {
    static constexpr unsigned LANES = 1;
    static constexpr unsigned ELEMS = 8;
    using Block = Words;

    __device__ static Block load(const uint8_t* w, size_t, size_t blk, unsigned) {
        return load_weights(w + blk * 16);
    }

    __device__ static float dot(const Block& v, unsigned b, unsigned, const float* x) {
        const float4* xv = reinterpret_cast<const float4*>(x) + 2 * b;
        const float4 x0 = __ldg(xv);
        const float4 x1 = __ldg(xv + 1);
        const float2 w0 = half2_bits(v.w[0]);
        const float2 w1 = half2_bits(v.w[1]);
        const float2 w2 = half2_bits(v.w[2]);
        const float2 w3 = half2_bits(v.w[3]);
        float r = __fmul_rn(w0.x, x0.x);
        r = fmaf(w0.y, x0.y, r);
        r = fmaf(w1.x, x0.z, r);
        r = fmaf(w1.y, x0.w, r);
        r = fmaf(w2.x, x1.x, r);
        r = fmaf(w2.y, x1.y, r);
        r = fmaf(w3.x, x1.z, r);
        return fmaf(w3.y, x1.w, r);
    }
};

GEMV_KERNELS(GEMV_KERNEL_F32, gemv_f32, GemvF32)
GEMV_KERNELS(GEMV_KERNEL_F32, gemv_f16, GemvF16)
