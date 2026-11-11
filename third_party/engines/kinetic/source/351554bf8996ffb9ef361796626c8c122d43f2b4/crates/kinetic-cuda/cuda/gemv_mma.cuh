#pragma once

#include "kquant.cuh"
#include "mma.cuh"

// K-quant GEMV on int8 tensor cores, for any batch of up to 8 * TILES
// inputs, in the order kquant.cuh defines. A block of KQ_SPLIT warps owns
// 16 rows; warp v is partial sum v, and it multiplies the 16 rows of each of
// its quant blocks with 8 inputs at a time: one m16n8k32 product per
// sub-block of 32 (Q4_K, Q5_K) or m16n8k16 per run of 16 (Q6_K), whose int32
// result is exact, scaled as the dp4a kernels scale theirs.
//
// The products sum over k in any order, so a lane may hold any k positions
// as long as weights and inputs agree: lane (group g, thread t) holds
// elements 8t..8t+7 of a sub-block of 32, or 4t..4t+3 of a run of 16, for
// rows g and g + 8 of the weights and for input g of the tile.

constexpr unsigned MMA_ROWS = 16;

__device__ __forceinline__ uint2 load_pair(const uint8_t* p) {
    return __ldcs(reinterpret_cast<const uint2*>(p));
}

// Where a lane's inputs and their scales are: `x` is the whole batch, `len`
// elements per input, `n` inputs.
struct MmaInput {
    Q8Input x;
    unsigned len;
    unsigned n;
    unsigned g, t;

    // Eight int8 inputs of input `i` from element `e`, zero past the batch.
    __device__ __forceinline__ uint2 pair(unsigned i, unsigned e) const {
        if (i >= n) return make_uint2(0, 0);
        return __ldg(reinterpret_cast<const uint2*>(x.qs + static_cast<size_t>(i) * len + e));
    }

    __device__ __forceinline__ int word(unsigned i, unsigned e) const {
        if (i >= n) return 0;
        return __ldg(reinterpret_cast<const int*>(x.qs + static_cast<size_t>(i) * len + e));
    }

    // (d, d * sum) of the block of 32 holding element `e` of input `i`.
    __device__ __forceinline__ float2 scale(unsigned i, unsigned e) const {
        if (i >= n) return make_float2(0.0f, 0.0f);
        return __ldg(x.ds + (static_cast<size_t>(i) * len + e) / 32);
    }
};

// tree[tile][2r + c] sums the terms of row g + 8r and input 8 tile + 2t + c
// within the block; group[r] holds that row's scale and min.
template <unsigned K, unsigned TILES>
__device__ __forceinline__ void mma_terms(TreeSum<K> (&tree)[TILES][4], unsigned i,
                                          const int (&d)[4], unsigned tile, const MmaInput& in,
                                          unsigned e, const float2 (&group)[2]) {
#pragma unroll
    for (unsigned c = 0; c < 2; ++c) {
        const float2 xd = in.scale(8 * tile + 2 * in.t + c, e);
#pragma unroll
        for (unsigned r = 0; r < 2; ++r)
            tree[tile][2 * r + c].push(i, kq_term(group[r].x, group[r].y, xd.x, xd.y, d[2 * r + c]));
    }
}

template <unsigned K, unsigned TILES>
__device__ __forceinline__ void mma_finish(float (&acc)[TILES][4], const TreeSum<K> (&tree)[TILES][4]) {
#pragma unroll
    for (unsigned tile = 0; tile < TILES; ++tile)
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) acc[tile][i] = __fadd_rn(acc[tile][i], tree[tile][i].total());
}

// Q4_K and Q5_K: one quant block of rows a and b; Q5 adds the fifth bits.
template <unsigned TILES, bool Q5>
__device__ __forceinline__ void mma_k4_block(const uint8_t* pa, const uint8_t* pb, unsigned b,
                                             const MmaInput& in, float (&acc)[TILES][4]) {
    constexpr unsigned QS = Q5 ? 48 : 16;
    const unsigned t = in.t;
    const Words ha = load_weights(pa), hb = load_weights(pb);
    TreeSum<3> tree[TILES][4];
    uint2 qha = make_uint2(0, 0), qhb = make_uint2(0, 0);
    if (Q5) {
        qha = load_pair(pa + 16 + 8 * t);
        qhb = load_pair(pb + 16 + 8 * t);
    }
#pragma unroll
    for (unsigned c = 0; c < 4; ++c) {
        const uint2 qa = load_pair(pa + QS + 32 * c + 8 * t);
        const uint2 qb = load_pair(pb + QS + 32 * c + 8 * t);
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            const unsigned s = 2 * c + h;
            int a0 = (qa.x >> (4 * h)) & NIBBLES, a2 = (qa.y >> (4 * h)) & NIBBLES;
            int a1 = (qb.x >> (4 * h)) & NIBBLES, a3 = (qb.y >> (4 * h)) & NIBBLES;
            if (Q5) {
                a0 |= ((qha.x >> s) & 0x01010101) << 4;
                a2 |= ((qha.y >> s) & 0x01010101) << 4;
                a1 |= ((qhb.x >> s) & 0x01010101) << 4;
                a3 |= ((qhb.y >> s) & 0x01010101) << 4;
            }
            const float2 group[2] = {k4_group(ha, s), k4_group(hb, s)};
            const unsigned e = b * 256 + 32 * s;
#pragma unroll
            for (unsigned tile = 0; tile < TILES; ++tile) {
                const uint2 xb = in.pair(8 * tile + in.g, e + 8 * t);
                int d[4] = {0, 0, 0, 0};
                mma_k32(d, a0, a1, a2, a3, static_cast<int>(xb.x), static_cast<int>(xb.y));
                mma_terms(tree, s, d, tile, in, e, group);
            }
        }
    }
    mma_finish(acc, tree);
}

struct MmaQ4K {
    template <unsigned TILES>
    __device__ static void block(const uint8_t* w, size_t, size_t ba, size_t bb, unsigned b,
                                 const MmaInput& in, float (&acc)[TILES][4]) {
        mma_k4_block<TILES, false>(w + ba * 144, w + bb * 144, b, in, acc);
    }
};

struct MmaQ5K {
    template <unsigned TILES>
    __device__ static void block(const uint8_t* w, size_t, size_t ba, size_t bb, unsigned b,
                                 const MmaInput& in, float (&acc)[TILES][4]) {
        mma_k4_block<TILES, true>(w + ba * 176, w + bb * 176, b, in, acc);
    }
};

// Q6_K, planar as layout.rs stores it, run by run in order; see k6_quants.
struct MmaQ6K {
    template <unsigned TILES>
    __device__ static void block(const uint8_t* w, size_t total, size_t ba, size_t bb,
                                 unsigned b, const MmaInput& in, float (&acc)[TILES][4]) {
        const uint8_t* ql = w;
        const uint8_t* qh = w + total * 128;
        const uint8_t* scales = w + total * 192;
        const __half* dp = reinterpret_cast<const __half*>(w + total * 208);
        const Words sa = load_weights(scales + ba * 16), sb = load_weights(scales + bb * 16);
        const float da = __half2float(__ldg(dp + ba)), db = __half2float(__ldg(dp + bb));
        const unsigned word = 4 * in.t;
        TreeSum<4> tree[TILES][4];
#pragma unroll
        for (unsigned j = 0; j < 16; ++j) {
            const unsigned n = j / 8, g = (j % 8) / 2, l = 16 * (j % 2) + word;
            const size_t low = 64 * n + 32 * (g & 1) + l, high = 32 * n + l;
            const int a0 = k6_quants(__ldcs(reinterpret_cast<const unsigned*>(ql + ba * 128 + low)),
                                     __ldcs(reinterpret_cast<const unsigned*>(qh + ba * 64 + high)), g);
            const int a1 = k6_quants(__ldcs(reinterpret_cast<const unsigned*>(ql + bb * 128 + low)),
                                     __ldcs(reinterpret_cast<const unsigned*>(qh + bb * 64 + high)), g);
            const float2 group[2] = {make_float2(k6_group(da, sa.w[j / 4], j), 0.0f),
                                     make_float2(k6_group(db, sb.w[j / 4], j), 0.0f)};
            const unsigned e = b * 256 + 128 * n + 32 * g + 16 * (j % 2);
#pragma unroll
            for (unsigned tile = 0; tile < TILES; ++tile) {
                const int xb = in.word(8 * tile + in.g, e + word);
                int d[4] = {0, 0, 0, 0};
                mma_k16(d, a0, a1, xb);
                mma_terms(tree, j, d, tile, in, e, group);
            }
        }
        mma_finish(acc, tree);
    }
};

// grid ceil(rows / 16), block 32 * KQ_SPLIT.
template <class F, unsigned TILES>
__device__ __forceinline__ void gemv_mma(const uint8_t* w, Q8Input x, float* y, unsigned rows,
                                         unsigned blocks_per_row, size_t total, unsigned n) {
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned row0 = blockIdx.x * MMA_ROWS;
    const MmaInput in = {x, blocks_per_row * 256, n, lane / 4, lane % 4};
    // Rows past the end repeat the last one; their results are not stored.
    const size_t ra = static_cast<size_t>(min(row0 + in.g, rows - 1)) * blocks_per_row;
    const size_t rb = static_cast<size_t>(min(row0 + in.g + 8, rows - 1)) * blocks_per_row;

    float acc[TILES][4] = {};
    for (unsigned b = warp; b < blocks_per_row; b += KQ_SPLIT)
        F::template block<TILES>(w, total, ra + b, rb + b, b, in, acc);

    __shared__ float part[KQ_SPLIT][TILES][4][WARP];
#pragma unroll
    for (unsigned tile = 0; tile < TILES; ++tile)
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) part[warp][tile][i][lane] = acc[tile][i];
    __syncthreads();
    if (warp != 0) return;
#pragma unroll
    for (unsigned tile = 0; tile < TILES; ++tile)
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            float s = part[0][tile][i][lane];
            for (unsigned v = 1; v < KQ_SPLIT; ++v) s = __fadd_rn(s, part[v][tile][i][lane]);
            const unsigned row = row0 + in.g + 8 * (i / 2);
            const unsigned input = 8 * tile + 2 * in.t + i % 2;
            if (row < rows && input < n) y[static_cast<size_t>(input) * rows + row] = s;
        }
}

#define GEMV_MMA_KERNEL(name, F, TILES)                                                     \
    extern "C" __global__ void __launch_bounds__(WARP * KQ_SPLIT)                          \
        name##_mma##TILES(const uint8_t* w, const int8_t* xq, const float2* xds, float* y,  \
                          unsigned rows, unsigned blocks_per_row, size_t total, unsigned n) { \
        gemv_mma<F, TILES>(w, Q8Input{xq, xds}, y, rows, blocks_per_row, total, n);          \
    }

GEMV_MMA_KERNEL(gemv_q4_k, MmaQ4K, 1)
GEMV_MMA_KERNEL(gemv_q4_k, MmaQ4K, 2)
GEMV_MMA_KERNEL(gemv_q5_k, MmaQ5K, 1)
GEMV_MMA_KERNEL(gemv_q5_k, MmaQ5K, 2)
GEMV_MMA_KERNEL(gemv_q6_k, MmaQ6K, 1)
GEMV_MMA_KERNEL(gemv_q6_k, MmaQ6K, 2)
