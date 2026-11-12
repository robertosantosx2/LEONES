#pragma once

#include "gemv_iq.cuh"
#include "quantize.cuh"

// PrismML's Bonsai formats and the Hadamard folding their files use.

// Spreads the four 2-bit codes of byte `b` into the four bytes of a word, in
// element order.
__device__ __forceinline__ int spread_codes(unsigned b) {
    return static_cast<int>((b | b << 6 | b << 12 | b << 18) & 0x03030303u);
}

// PQ2_0: codes (32) then d, planar. Four lanes share a 128-value block, lane
// p taking elements 32p..32p+31 and input block 4b + p; values code - 1, the
// 1 taken back out through the input block's sum.
struct GemvPQ2_0 {
    static constexpr unsigned LANES = 4;
    static constexpr unsigned ELEMS = 128;

    struct Block {
        Words q[2];
        float d;
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned p) {
        Block k;
        const int2 v = __ldcs(reinterpret_cast<const int2*>(w + blk * 32 + 8 * p));
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            k.q[0].w[i] = spread_codes(static_cast<unsigned>(v.x) >> (8 * i) & 0xFF);
            k.q[1].w[i] = spread_codes(static_cast<unsigned>(v.y) >> (8 * i) & 0xFF);
        }
        k.d = plane_half(w + total * 32 + blk * 2);
        return k;
    }

    __device__ static float dot(const Block& k, unsigned b, unsigned p, Q8Input x) {
        const int8_t* xp = x.qs + b * 128 + 32 * p;
        const int q = dot16(k.q[0], load_cached(xp), dot16(k.q[1], load_cached(xp + 16)));
        const float2 ds = __ldg(x.ds + b * 4 + p);
        return __fmul_rn(k.d, __fsub_rn(__fmul_rn(ds.x, static_cast<float>(q)), ds.y));
    }
};

GEMV_KERNELS(GEMV_KERNEL_Q8, gemv_pq2_0, GemvPQ2_0)

// The unnormalized transform of `n` values in shared memory, by the whole
// thread block; returns after a barrier.
__device__ __forceinline__ void walsh_hadamard(float* v, unsigned n) {
    for (unsigned h = 1; h < n; h *= 2) {
        __syncthreads();
        for (unsigned j = threadIdx.x; j < n / 2; j += blockDim.x) {
            const unsigned i = j / h * 2 * h + j % h;
            const float a = v[i], b = v[i + h];
            v[i] = __fadd_rn(a, b);
            v[i + h] = __fsub_rn(a, b);
        }
    }
    __syncthreads();
}

struct FoldArgs {
    const float* x;
    const float* signs;
    Act out;
    unsigned width;
    unsigned block;
    unsigned head_dim;
    unsigned n_k;
    unsigned rep;
};

// Rows of `width` values as a folded weight reads them: signs, then the
// normalized Walsh-Hadamard transform of each `block` values, written as
// GEMV input. With `rep` > 1 the input holds value heads of `head_dim` in
// tiled order (head k + n_k r reads key head k), regrouped by key head
// first. One thread block per (block, row), `block` floats of shared memory;
// `block` is a power of two and a multiple of the thread count.
extern "C" __global__ void fold_rows(FoldArgs a) {
    extern __shared__ float v[];
    const float* x = a.x;
    const float* signs = a.signs;
    const unsigned width = a.width, block = a.block, head_dim = a.head_dim, n_k = a.n_k, rep = a.rep;
    const size_t row = static_cast<size_t>(blockIdx.y) * width;
    const unsigned first = blockIdx.x * block;
    for (unsigned i = threadIdx.x; i < block; i += blockDim.x) {
        const unsigned e = first + i;
        unsigned src = e;
        if (rep > 1) {
            const unsigned g = e / head_dim, k = g / rep, r = g % rep;
            src = (k + n_k * r) * head_dim + e % head_dim;
        }
        v[i] = x[row + src] * signs[e];
    }
    walsh_hadamard(v, block);
    const float scale = __frcp_rn(__fsqrt_rn(static_cast<float>(block)));
    for (unsigned i = threadIdx.x; i < block; i += blockDim.x)
        a.out.put(row + first + i, __fmul_rn(v[i], scale));
}

struct UnfoldArgs {
    float* x;
    const float* signs;
    unsigned width;
    unsigned block;
};

// Undoes a fold in place: the transform, then the signs. Launched like
// `fold_rows`.
extern "C" __global__ void unfold_rows(UnfoldArgs a) {
    extern __shared__ float v[];
    float* x = a.x + static_cast<size_t>(blockIdx.y) * a.width + blockIdx.x * a.block;
    const float* signs = a.signs + blockIdx.x * a.block;
    for (unsigned i = threadIdx.x; i < a.block; i += blockDim.x) v[i] = x[i];
    walsh_hadamard(v, a.block);
    const float scale = __frcp_rn(__fsqrt_rn(static_cast<float>(a.block)));
    for (unsigned i = threadIdx.x; i < a.block; i += blockDim.x)
        x[i] = __fmul_rn(__fmul_rn(v[i], scale), signs[i]);
}
