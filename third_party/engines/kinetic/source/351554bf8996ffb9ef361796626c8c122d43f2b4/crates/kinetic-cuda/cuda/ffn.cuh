#pragma once

#include "quantize.cuh"

// out = silu(gate) * up over `n` elements, a multiple of 32.
extern "C" __global__ void swiglu_q8(const float* gate, const float* up, Act out, unsigned n) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    out.put(i, silu(gate[i]) * up[i]);
}

// out = gelu(gate) * up over `n` elements, a multiple of 32.
extern "C" __global__ void geglu_q8(const float* gate, const float* up, Act out, unsigned n) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    out.put(i, gelu(gate[i]) * up[i]);
}
