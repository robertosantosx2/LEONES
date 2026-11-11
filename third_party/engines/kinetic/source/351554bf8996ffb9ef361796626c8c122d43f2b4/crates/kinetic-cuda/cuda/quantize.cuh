#pragma once

#include "common.cuh"

// Quantizes element i, held by one lane of a warp whose 32 lanes hold the
// block of 32 that starts at a multiple of 32, into the GEMV input form.
__device__ __forceinline__ void quantize_lane(float v, int8_t* qs, float2* ds, size_t i) {
    float amax = fabsf(v);
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2)
        amax = fmaxf(amax, __shfl_xor_sync(FULL_MASK, amax, o));
    const float d = amax / 127.0f;
    const int q = amax == 0.0f ? 0 : __float2int_rn(v / d);
    qs[i] = static_cast<int8_t>(q);

    int sum = q;
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) sum += __shfl_xor_sync(FULL_MASK, sum, o);
    if (i % WARP == 0) ds[i / WARP] = make_float2(d, d * static_cast<float>(sum));
}

// A batch of GEMV inputs: f32 values for float weights and their int8 copy
// for quantized ones.
struct Act {
    float* x;
    int8_t* qs;
    float2* ds;

    // Same warp contract as `quantize_lane`.
    __device__ __forceinline__ void put(size_t i, float v) const {
        x[i] = v;
        quantize_lane(v, qs, ds, i);
    }
};

// One thread per element, one warp per block of 32; `n` is a multiple of 32,
// so whole warps leave together.
extern "C" __global__ void quantize_q8(const float* x, int8_t* qs, float2* ds, unsigned n) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    quantize_lane(x[i], qs, ds, i);
}
