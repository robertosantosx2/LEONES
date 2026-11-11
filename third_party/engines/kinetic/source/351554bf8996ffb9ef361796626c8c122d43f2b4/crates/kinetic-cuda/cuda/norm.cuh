#pragma once

#include "quantize.cuh"

// RMS norms with one block of NORM_THREADS per row, each thread holding up to
// NORM_ITEMS values in registers. Rows are `len` long, a multiple of 32 and
// at most NORM_THREADS * NORM_ITEMS, so each warp covers whole quantization
// blocks.

constexpr unsigned NORM_THREADS = 1024;
constexpr unsigned NORM_ITEMS = 8;

__device__ __forceinline__ float rms_scale(float sum_sq, unsigned len, float eps) {
    return 1.0f / sqrtf(sum_sq / static_cast<float>(len) + eps);
}

struct NormArgs {
    const float* x;
    // Null passes `x` through unnormalized.
    const float* weight;
    Act out;
    float eps;
    unsigned len;
    // Elements from one output row to the next, and the first column written.
    unsigned out_stride;
    unsigned out_offset;
};

// out[row] = rms_norm(x[row]) * weight, or x[row] without a weight.
extern "C" __global__ void __launch_bounds__(NORM_THREADS) rms_norm_q8(NormArgs a) {
    const float* x = a.x + static_cast<size_t>(blockIdx.x) * a.len;
    float v[NORM_ITEMS];
    float ss = 0.0f;
#pragma unroll
    for (unsigned k = 0; k < NORM_ITEMS; ++k) {
        const unsigned i = threadIdx.x + k * NORM_THREADS;
        v[k] = i < a.len ? x[i] : 0.0f;
        ss = fmaf(v[k], v[k], ss);
    }
    const float scale = rms_scale(block_sum(ss), a.len, a.eps);
    const size_t out = static_cast<size_t>(blockIdx.x) * a.out_stride + a.out_offset;
#pragma unroll
    for (unsigned k = 0; k < NORM_ITEMS; ++k) {
        const unsigned i = threadIdx.x + k * NORM_THREADS;
        if (i < a.len) a.out.put(out + i, a.weight ? v[k] * (scale * a.weight[i]) : v[k]);
    }
}

struct AddNormArgs {
    // The residual stream, updated in place.
    float* x;
    // A block's output, added to it.
    const float* y;
    // Optional norm of `y` before the add.
    const float* post;
    // Norm of the updated stream, written to `out`; null writes it as it is.
    const float* weight;
    Act out;
    float eps;
    unsigned len;
    // Multiplies `y`, after `post`, before the add; `out_scale` then
    // multiplies the sum.
    float scale;
    float out_scale;
};

// x[row] += scale * (post ? rms_norm(y[row]) * post : y[row]);
// out[row] = weight ? rms_norm(x[row]) * weight : x[row].
extern "C" __global__ void __launch_bounds__(NORM_THREADS) add_norm_q8(AddNormArgs a) {
    const size_t row = static_cast<size_t>(blockIdx.x) * a.len;
    float* x = a.x + row;
    const float* y = a.y + row;
    float xv[NORM_ITEMS], yv[NORM_ITEMS];
    float ss = 0.0f;
#pragma unroll
    for (unsigned k = 0; k < NORM_ITEMS; ++k) {
        const unsigned i = threadIdx.x + k * NORM_THREADS;
        xv[k] = i < a.len ? x[i] : 0.0f;
        yv[k] = i < a.len ? y[i] : 0.0f;
        ss = fmaf(yv[k], yv[k], ss);
    }
    if (a.post) {
        const float post = rms_scale(block_sum(ss), a.len, a.eps);
#pragma unroll
        for (unsigned k = 0; k < NORM_ITEMS; ++k) {
            const unsigned i = threadIdx.x + k * NORM_THREADS;
            if (i < a.len) yv[k] *= post * a.post[i];
        }
    }
    ss = 0.0f;
#pragma unroll
    for (unsigned k = 0; k < NORM_ITEMS; ++k) {
        const unsigned i = threadIdx.x + k * NORM_THREADS;
        xv[k] = fmaf(a.scale, yv[k], xv[k]) * a.out_scale;
        if (i < a.len) x[i] = xv[k];
        ss = fmaf(xv[k], xv[k], ss);
    }
    const float scale = rms_scale(block_sum(ss), a.len, a.eps);
#pragma unroll
    for (unsigned k = 0; k < NORM_ITEMS; ++k) {
        const unsigned i = threadIdx.x + k * NORM_THREADS;
        if (i < a.len) a.out.put(row + i, a.weight ? xv[k] * (scale * a.weight[i]) : xv[k]);
    }
}

// grid (tokens * layers), block `width`: turns `proj`, the projected
// embedding, into per-layer inputs in place:
// (rms_norm(proj * proj_scale) * norm + tokens) / sqrt(2), per run of `width`.
extern "C" __global__ void per_layer_inputs(float* proj, const float* tokens,
                                            const float* norm, float proj_scale,
                                            float eps) {
    const size_t i = static_cast<size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    const float v = proj[i] * proj_scale;
    const float scale = rms_scale(block_sum(v * v), blockDim.x, eps);
    proj[i] = (v * (scale * norm[threadIdx.x]) + tokens[i]) * 0.70710678118654752f;
}

// out = gelu(gate) * the inputs of `layer`, for `n` values of rows of
// `width`; `inputs` holds `layers * width` values per row.
extern "C" __global__ void per_layer_gate_q8(const float* gate, const float* inputs,
                                             unsigned layer, unsigned layers,
                                             unsigned width, Act out, unsigned n) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const size_t at = (static_cast<size_t>(i / width) * layers + layer) * width + i % width;
    out.put(i, gelu(gate[i]) * inputs[at]);
}

// y[i] += x[i] for the first n values.
extern "C" __global__ void add_f32(float* y, const float* x, unsigned n) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) y[i] += x[i];
}
