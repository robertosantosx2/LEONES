#pragma once

#include "common.cuh"

// Row-wise argmax in two steps: `argmax_partial` finds the best of each
// ARGMAX_CHUNK values, `argmax_final` the best of those. The lowest index
// wins a tie.

constexpr unsigned ARGMAX_CHUNK = 4096;
constexpr unsigned NONE = 0xffffffffu;

struct Best {
    float value;
    unsigned index;
};

__device__ __forceinline__ Best better(Best a, Best b) {
    if (b.index == NONE) return a;
    if (a.index == NONE || b.value > a.value || (b.value == a.value && b.index < a.index)) return b;
    return a;
}

__device__ __forceinline__ Best warp_best(Best b) {
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) {
        const Best other = {__shfl_xor_sync(FULL_MASK, b.value, o),
                            __shfl_xor_sync(FULL_MASK, b.index, o)};
        b = better(b, other);
    }
    return b;
}

// grid (rows, parts), block 256: partial[row * parts + part] = best of the chunk.
extern "C" __global__ void argmax_partial(const float* x, unsigned len, unsigned parts,
                                          uint2* partial) {
    const float* row = x + static_cast<size_t>(blockIdx.x) * len;
    const unsigned end = min(len, (blockIdx.y + 1) * ARGMAX_CHUNK);
    Best b = {0.0f, NONE};
    for (unsigned i = blockIdx.y * ARGMAX_CHUNK + threadIdx.x; i < end; i += blockDim.x) {
        const float v = row[i];
        if (b.index == NONE || v > b.value) b = {v, i};
    }
    __shared__ Best warps[WARP];
    b = warp_best(b);
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    if (lane == 0) warps[warp] = b;
    __syncthreads();
    if (warp != 0) return;
    b = warp_best(lane < blockDim.x / WARP ? warps[lane] : Best{0.0f, NONE});
    if (lane == 0)
        partial[blockIdx.x * parts + blockIdx.y] = make_uint2(__float_as_uint(b.value), b.index);
}

// grid rows, block 32: out[row] = index of the best of its partials.
extern "C" __global__ void argmax_final(const uint2* partial, unsigned parts, unsigned* out) {
    Best b = {0.0f, NONE};
    for (unsigned p = threadIdx.x; p < parts; p += WARP) {
        const uint2 v = partial[blockIdx.x * parts + p];
        b = better(b, {__uint_as_float(v.x), v.y});
    }
    b = warp_best(b);
    if (threadIdx.x == 0) out[blockIdx.x] = b.index == NONE ? 0 : b.index;
}
