#pragma once

#include "common.cuh"

__device__ __forceinline__ unsigned word_sum(int4 v) {
    return static_cast<unsigned>(v.x) + v.y + v.z + v.w;
}

// Streams `n` 16-byte words once and adds their 32-bit sum to `*out`. The
// result only keeps the loads alive; the kernel exists to measure how fast
// device memory can be read.
extern "C" __global__ void read_sum(const int4* data, size_t n, unsigned* out) {
    const size_t stride = static_cast<size_t>(gridDim.x) * blockDim.x;
    size_t i = static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    unsigned acc = 0;
    // Four independent loads per step keep enough bytes in flight.
    for (; i + 3 * stride < n; i += 4 * stride) {
        const int4 a = __ldcs(data + i);
        const int4 b = __ldcs(data + i + stride);
        const int4 c = __ldcs(data + i + 2 * stride);
        const int4 d = __ldcs(data + i + 3 * stride);
        acc += word_sum(a) + word_sum(b) + word_sum(c) + word_sum(d);
    }
    for (; i < n; i += stride) acc += word_sum(__ldcs(data + i));

#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) acc += __shfl_xor_sync(FULL_MASK, acc, o);
    if (threadIdx.x % WARP == 0) atomicAdd(out, acc);
}
