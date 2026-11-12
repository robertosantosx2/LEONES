#pragma once

#include "common.cuh"

// Q8_0 is stored planar on the device: all 32-byte quant runs, then all f16
// scales, so every run is 16-byte aligned. Two lanes share a block.
struct GemvQ8_0 {
    static constexpr unsigned LANES = 2;
    static constexpr unsigned ELEMS = 32;

    struct Block {
        Words q;
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned part) {
        const __half d = __ldg(reinterpret_cast<const __half*>(w + total * 32) + blk);
        return {load_weights(w + blk * 32 + 16 * part), __half2float(d)};
    }

    __device__ static float dot(const Block& q, unsigned b, unsigned part, Q8Input x) {
        const Words xq = load_cached(x.qs + b * 32 + 16 * part);
        return __fmul_rn(__fmul_rn(q.d, __ldg(x.ds + b).x), static_cast<float>(dot16(q.q, xq)));
    }
};

GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_q8_0, GemvQ8_0)
