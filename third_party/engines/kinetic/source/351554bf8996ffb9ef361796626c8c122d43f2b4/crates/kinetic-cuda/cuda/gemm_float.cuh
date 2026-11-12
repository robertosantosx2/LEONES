#pragma once

#include "common.cuh"
#include "mma.cuh"

// Float-weight matrix products for large batches, in f32 on the CUDA cores,
// so that they differ from the GEMV only in the order of their sums. A block
// takes GEMMF_INPUTS inputs and a warp GEMMF_WARP_ROWS rows of them, each
// lane summing every 32nd group of four columns; the lanes' partial sums
// are then reduced across the warp, leaving one output per lane. The float
// weights of quantized models are small matrices, so a warp covers few rows
// to give the grid enough blocks.

constexpr unsigned GEMMF_INPUTS = 8;
constexpr unsigned GEMMF_WARP_ROWS = 4;
constexpr unsigned GEMMF_WARPS = 8;
constexpr unsigned GEMMF_THREADS = GEMMF_WARPS * WARP;
static_assert(GEMMF_INPUTS * GEMMF_WARP_ROWS == WARP, "one output per lane");

struct GemmF32 {
    __device__ static float4 load(const uint8_t* w, size_t at) {
        return __ldg(reinterpret_cast<const float4*>(reinterpret_cast<const float*>(w) + at));
    }
};

struct GemmF16 {
    __device__ static float4 load(const uint8_t* w, size_t at) {
        const uint2 v = __ldg(reinterpret_cast<const uint2*>(reinterpret_cast<const __half*>(w) + at));
        const float2 a = half2_bits(v.x), b = half2_bits(v.y);
        return make_float4(a.x, a.y, b.x, b.y);
    }
};

// Sums each of the 32 values of every lane over the warp; lane l returns the
// sum of value l. Each step halves the values a lane keeps, swapping the
// other half with the partner that keeps it.
__device__ __forceinline__ float warp_transpose_sum(float (&v)[WARP], unsigned lane) {
#pragma unroll
    for (unsigned s = WARP / 2; s > 0; s /= 2) {
        const bool upper = lane & s;
#pragma unroll
        for (unsigned i = 0; i < s; ++i) {
            const float send = upper ? v[i] : v[i + s];
            const float keep = upper ? v[i + s] : v[i];
            v[i] = keep + __shfl_xor_sync(FULL_MASK, send, s);
        }
    }
    return v[0];
}

// grid (ceil(n / GEMMF_INPUTS), ceil(rows / (GEMMF_WARPS * GEMMF_WARP_ROWS))),
// block GEMMF_THREADS. `cols` is a multiple of 128; output i of row r goes
// to y[i * rows + r].
template <class F>
__device__ __forceinline__ void gemm_float(const uint8_t* w, const float* x, float* y,
                                           unsigned rows, unsigned cols, unsigned n) {
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned row0 = (blockIdx.y * GEMMF_WARPS + warp) * GEMMF_WARP_ROWS;
    const unsigned in0 = blockIdx.x * GEMMF_INPUTS;
    size_t wrow[GEMMF_WARP_ROWS];
    const float* xrow[GEMMF_INPUTS];
#pragma unroll
    for (unsigned r = 0; r < GEMMF_WARP_ROWS; ++r)
        wrow[r] = static_cast<size_t>(min(row0 + r, rows - 1)) * cols;
#pragma unroll
    for (unsigned i = 0; i < GEMMF_INPUTS; ++i)
        xrow[i] = x + static_cast<size_t>(min(in0 + i, n - 1)) * cols;

    // acc[r * GEMMF_INPUTS + i]: row r, input i.
    float acc[WARP] = {};
    for (unsigned k = 4 * lane; k < cols; k += 4 * WARP) {
        float4 xv[GEMMF_INPUTS];
#pragma unroll
        for (unsigned i = 0; i < GEMMF_INPUTS; ++i)
            xv[i] = __ldg(reinterpret_cast<const float4*>(xrow[i] + k));
#pragma unroll
        for (unsigned r = 0; r < GEMMF_WARP_ROWS; ++r) {
            const float4 wv = F::load(w, wrow[r] + k);
#pragma unroll
            for (unsigned i = 0; i < GEMMF_INPUTS; ++i) {
                float& a = acc[r * GEMMF_INPUTS + i];
                a = fmaf(wv.x, xv[i].x, a);
                a = fmaf(wv.y, xv[i].y, a);
                a = fmaf(wv.z, xv[i].z, a);
                a = fmaf(wv.w, xv[i].w, a);
            }
        }
    }
    const float sum = warp_transpose_sum(acc, lane);
    const unsigned row = row0 + lane / GEMMF_INPUTS, in = in0 + lane % GEMMF_INPUTS;
    if (row < rows && in < n) y[static_cast<size_t>(in) * rows + row] = sum;
}

// f16 weights on tensor cores instead: each input enters as the sum of two
// f16 values, high and low part, which keeps the products as accurate as
// f32 arithmetic, summed in f32 in another order than the GEMV. A block of
// four warps takes GEMMH_ROWS rows and GEMMH_INPUTS inputs, a warp 16 rows
// of all of them, walking the k axis GEMMH_K values at a time through
// shared memory.

constexpr unsigned GEMMH_ROWS = 64;
constexpr unsigned GEMMH_INPUTS = 128;
constexpr unsigned GEMMH_K = 32;
constexpr unsigned GEMMH_THREADS = 128;
// f16 values per shared row, padded so the eight rows of an 8x8 matrix
// load fall in distinct banks.
constexpr unsigned GEMMH_ROW = GEMMH_K + 8;

// grid (ceil(n / GEMMH_INPUTS), ceil(rows / GEMMH_ROWS)), block
// GEMMH_THREADS. `cols` is a multiple of GEMMH_K; output i of row r goes to
// y[i * rows + r].
__device__ __forceinline__ void gemm_half(const __half* w, const float* x, float* y,
                                          unsigned rows, unsigned cols, unsigned n) {
    __shared__ __align__(16) __half ws[GEMMH_ROWS][GEMMH_ROW];
    __shared__ __align__(16) __half xs[2][GEMMH_INPUTS][GEMMH_ROW];
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned row0 = blockIdx.y * GEMMH_ROWS, in0 = blockIdx.x * GEMMH_INPUTS;
    float acc[GEMMH_INPUTS / 8][4] = {};
    for (unsigned k0 = 0; k0 < cols; k0 += GEMMH_K) {
        for (unsigned i = threadIdx.x; i < GEMMH_ROWS * GEMMH_K / 8; i += GEMMH_THREADS) {
            const unsigned r = i / (GEMMH_K / 8), c = 8 * (i % (GEMMH_K / 8));
            cp_async16(&ws[r][c], w + static_cast<size_t>(min(row0 + r, rows - 1)) * cols + k0 + c);
        }
        cp_async_commit();
        for (unsigned i = threadIdx.x; i < GEMMH_INPUTS * GEMMH_K / 4; i += GEMMH_THREADS) {
            const unsigned r = i / (GEMMH_K / 4), c = 4 * (i % (GEMMH_K / 4));
            const float4 v = __ldg(reinterpret_cast<const float4*>(
                x + static_cast<size_t>(min(in0 + r, n - 1)) * cols + k0 + c));
            unsigned hi[2], lo[2];
            split_pair(v.x, v.y, hi[0], lo[0]);
            split_pair(v.z, v.w, hi[1], lo[1]);
            *reinterpret_cast<uint2*>(&xs[0][r][c]) = make_uint2(hi[0], hi[1]);
            *reinterpret_cast<uint2*>(&xs[1][r][c]) = make_uint2(lo[0], lo[1]);
        }
        cp_async_wait<0>();
        __syncthreads();
        // tensor cores round their sums coarser than f32; a fresh sum per
        // stage, added in f32, keeps long rows as close as the GEMV
        float part_sum[GEMMH_INPUTS / 8][4] = {};
#pragma unroll
        for (unsigned kk = 0; kk < GEMMH_K; kk += 16) {
            unsigned a[4];
            ldsm_x4(a, &ws[16 * warp + lane % 16][kk + 8 * (lane / 16)]);
#pragma unroll
            for (unsigned part = 0; part < 2; ++part)
#pragma unroll
                for (unsigned j = 0; j < GEMMH_INPUTS / 8; j += 2) {
                    const unsigned in = 8 * (j + lane / 16) + lane % 8;
                    unsigned b[4];
                    ldsm_x4(b, &xs[part][in][kk + 8 * ((lane / 8) % 2)]);
                    mma_f16(part_sum[j], a[0], a[1], a[2], a[3], b[0], b[1]);
                    mma_f16(part_sum[j + 1], a[0], a[1], a[2], a[3], b[2], b[3]);
                }
        }
#pragma unroll
        for (unsigned j = 0; j < GEMMH_INPUTS / 8; ++j)
#pragma unroll
            for (unsigned e = 0; e < 4; ++e) acc[j][e] += part_sum[j][e];
        __syncthreads();
    }
    const unsigned g = lane / 4, t = lane % 4;
#pragma unroll
    for (unsigned j = 0; j < GEMMH_INPUTS / 8; ++j)
#pragma unroll
        for (unsigned e = 0; e < 4; ++e) {
            const unsigned row = row0 + 16 * warp + g + 8 * (e / 2);
            const unsigned in = in0 + 8 * j + 2 * t + e % 2;
            if (row < rows && in < n) y[static_cast<size_t>(in) * rows + row] = acc[j][e];
        }
}

// Same parameters as the quantized kernels; a second matrix, the scales and
// the int8 outputs are not used.
#define GEMM_FLOAT_KERNEL(name, F)                                                             \
    extern "C" __global__ void __launch_bounds__(GEMMF_THREADS)                                \
        name(const uint8_t* w, const uint8_t*, const float* x, const float2*, float* y,        \
             int8_t*, float2*, unsigned rows, unsigned cols, size_t, unsigned n, unsigned) {   \
        gemm_float<F>(w, x, y, rows, cols, n);                                                 \
    }

GEMM_FLOAT_KERNEL(gemm_f32, GemmF32)
extern "C" __global__ void __launch_bounds__(GEMMH_THREADS)
    gemm_f16(const uint8_t* w, const uint8_t*, const float* x, const float2*, float* y, int8_t*,
             float2*, unsigned rows, unsigned cols, size_t, unsigned n, unsigned) {
    gemm_half(reinterpret_cast<const __half*>(w), x, y, rows, cols, n);
}
