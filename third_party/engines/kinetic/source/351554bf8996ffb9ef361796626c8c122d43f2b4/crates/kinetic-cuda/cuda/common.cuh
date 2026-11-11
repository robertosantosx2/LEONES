#pragma once

#include <cstddef>
#include <cstdint>
#include <cuda_fp16.h>
#include <math_constants.h>

constexpr unsigned WARP = 32;
constexpr unsigned FULL_MASK = 0xffffffffu;

// Sixteen bytes as four 32-bit words, indexed with constants after unrolling
// so they stay in registers.
struct Words {
    int w[4];
};

// Weights are streamed once per call; evict-first keeps the reused input
// vector resident in L1.
__device__ __forceinline__ Words load_weights(const void* p) {
    const int4 v = __ldcs(static_cast<const int4*>(p));
    return {{v.x, v.y, v.z, v.w}};
}

__device__ __forceinline__ Words load_cached(const void* p) {
    const int4 v = __ldg(static_cast<const int4*>(p));
    return {{v.x, v.y, v.z, v.w}};
}

__device__ __forceinline__ float2 half2_bits(int bits) {
    return __half22float2(__halves2half2(__ushort_as_half(bits & 0xffff),
                                         __ushort_as_half(static_cast<unsigned>(bits) >> 16)));
}

__device__ __forceinline__ float warp_sum(float v) {
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) v += __shfl_xor_sync(FULL_MASK, v, o);
    return v;
}

// The input vector quantized in blocks of 32: ds[i] = (d, d * sum of q) of block i.
struct Q8Input {
    const int8_t* qs;
    const float2* ds;
};

// Input `i` of a batch whose vectors are `len` elements apart.
__device__ __forceinline__ const float* batch_row(const float* x, unsigned i, unsigned len) {
    return x + static_cast<size_t>(i) * len;
}

__device__ __forceinline__ Q8Input batch_row(Q8Input x, unsigned i, unsigned len) {
    return {x.qs + static_cast<size_t>(i) * len, x.ds + static_cast<size_t>(i) * len / 32};
}

// Y = W X for N input vectors with one warp per row, so each weight is read
// once for the whole batch. `F::LANES` consecutive lanes share a weight
// block, so a warp covers 32 / F::LANES blocks per step. `F::load` reads one
// lane's share of a block and `F::dot` multiplies it with one input; `blk`
// indexes the block in the whole matrix and `b` within the row, and `total`
// is the matrix's block count, which planar layouts need to find their
// planes. Output i of row r goes to y[i * rows + r].
//
// Each input's sum is formed in the same order whatever N is, and the adds
// are never fused, so a vector gets bit-identical results alone or batched.
template <class F, unsigned N, class In>
__device__ __forceinline__ void gemv_rows(const uint8_t* w, In x, float* y, unsigned rows,
                                          unsigned blocks_per_row, size_t total) {
    const unsigned row = blockIdx.x * (blockDim.x / WARP) + threadIdx.x / WARP;
    if (row >= rows) return;
    const unsigned lane = threadIdx.x % WARP;
    const unsigned part = lane % F::LANES;
    const unsigned len = blocks_per_row * F::ELEMS;
    const size_t first = static_cast<size_t>(row) * blocks_per_row;

    float sum[N] = {};
    for (unsigned b = lane / F::LANES; b < blocks_per_row; b += WARP / F::LANES) {
        const typename F::Block blk = F::load(w, total, first + b, part);
#pragma unroll
        for (unsigned i = 0; i < N; ++i)
            sum[i] = __fadd_rn(sum[i], F::dot(blk, b, part, batch_row(x, i, len)));
    }
#pragma unroll
    for (unsigned i = 0; i < N; ++i) {
        const float s = warp_sum(sum[i]);
        if (lane == 0) y[static_cast<size_t>(i) * rows + row] = s;
    }
}

// One extern "C" kernel per batch size, named `<name>_<N>`.
#define GEMV_KERNEL_F32(name, F, N)                                                             extern "C" __global__ void __launch_bounds__(128)                                               name##_##N(const uint8_t* w, const float* x, float* y, unsigned rows,                                 unsigned blocks_per_row, size_t total) {                                         gemv_rows<F, N>(w, x, y, rows, blocks_per_row, total);                                  }

#define GEMV_KERNEL_Q8(name, F, N)                                                              extern "C" __global__ void __launch_bounds__(128)                                               name##_##N(const uint8_t* w, const int8_t* xq, const float2* xds, float* y,                           unsigned rows, unsigned blocks_per_row, size_t total) {                          gemv_rows<F, N>(w, Q8Input{xq, xds}, y, rows, blocks_per_row, total);                   }

// Batch sizes 1 through MAX_BATCH (16); kernels.rs lists the same range.
#define GEMV_KERNELS(KERNEL, name, F)                                                           KERNEL(name, F, 1) KERNEL(name, F, 2) KERNEL(name, F, 3) KERNEL(name, F, 4)                 KERNEL(name, F, 5) KERNEL(name, F, 6) KERNEL(name, F, 7) KERNEL(name, F, 8)                 KERNEL(name, F, 9) KERNEL(name, F, 10) KERNEL(name, F, 11) KERNEL(name, F, 12)              KERNEL(name, F, 13) KERNEL(name, F, 14) KERNEL(name, F, 15) KERNEL(name, F, 16)

// Four signed int8 dot products of 16 values, added to `acc`.
__device__ __forceinline__ int dot16(const Words& a, const Words& b, int acc = 0) {
#pragma unroll
    for (int i = 0; i < 4; ++i) acc = __dp4a(a.w[i], b.w[i], acc);
    return acc;
}

// Sum over a one-dimensional block whose size is a multiple of 32; every
// thread must call it and every thread gets the total. The order of the
// adds depends only on the block size.
__device__ __forceinline__ float block_sum(float v) {
    __shared__ float part[WARP];
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    v = warp_sum(v);
    __syncthreads();
    if (lane == 0) part[warp] = v;
    __syncthreads();
    return warp_sum(lane < blockDim.x / WARP ? part[lane] : 0.0f);
}

__device__ __forceinline__ float sigmoid(float x) { return 1.0f / (1.0f + expf(-x)); }

__device__ __forceinline__ float silu(float x) { return x / (1.0f + expf(-x)); }

// GELU in its tanh approximation.
__device__ __forceinline__ float gelu(float x) {
    constexpr float SQRT_2_OVER_PI = 0.7978846f;
    return 0.5f * x * (1.0f + tanhf(SQRT_2_OVER_PI * (x + 0.044715f * x * x * x)));
}

// Copies of 16 bytes from global to shared memory that run in the
// background on sm_80 and up; Turing copies through registers at once.
__device__ __forceinline__ void cp_async16(void* dst, const void* src) {
#if __CUDA_ARCH__ >= 800
    const unsigned s = static_cast<unsigned>(__cvta_generic_to_shared(dst));
    asm volatile("cp.async.cg.shared.global [%0], [%1], 16;" ::"r"(s), "l"(src));
#else
    *static_cast<int4*>(dst) = __ldg(static_cast<const int4*>(src));
#endif
}

// Closes the group of copies queued since the last commit.
__device__ __forceinline__ void cp_async_commit() {
#if __CUDA_ARCH__ >= 800
    asm volatile("cp.async.commit_group;" ::);
#endif
}

// Waits until at most N committed groups are still in flight.
template <unsigned N>
__device__ __forceinline__ void cp_async_wait() {
#if __CUDA_ARCH__ >= 800
    asm volatile("cp.async.wait_group %0;" ::"n"(N));
#endif
}
