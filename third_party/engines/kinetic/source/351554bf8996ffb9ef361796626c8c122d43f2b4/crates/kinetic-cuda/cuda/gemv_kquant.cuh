#pragma once

#include "kquant.cuh"

// K-quant GEMV with dp4a, in the order kquant.cuh defines: one warp per
// row, where lane group v = lane / 8 is partial sum v. Its eight lanes split
// a 256-element block; each computes the term of one sub-block (Q4_K, Q5_K:
// after adding its partner's half of the integer products) or the sum of
// two runs (Q6_K), and three exchanges within the group finish the tree.

// Q4_K and Q5_K: lane j holds qs bytes 32c + 16h .. +16 (c = j / 2,
// h = j % 2), elements 16h..16h+15 of sub-blocks 2c (low nibbles) and 2c+1
// (high nibbles), and computes the term of sub-block 2c + h.
struct K4Lane {
    struct Block {
        Words head;
        Words lo, hi;
    };

    __device__ static float term(const Block& k, unsigned b, unsigned j, Q8Input x) {
        const unsigned c = j / 2, h = j % 2;
        const int8_t* xp = x.qs + b * 256 + 64 * c + 16 * h;
        int lo = dot16(k.lo, load_cached(xp));
        int hi = dot16(k.hi, load_cached(xp + 32));
        lo += __shfl_xor_sync(FULL_MASK, lo, 1);
        hi += __shfl_xor_sync(FULL_MASK, hi, 1);
        const unsigned s = 2 * c + h;
        const float2 d = __ldg(x.ds + b * 8 + s);
        const float2 g = k4_group(k.head, s);
        return kq_term(g.x, g.y, d.x, d.y, h ? hi : lo);
    }
};

struct KqQ4K : K4Lane {
    __device__ static Block load(const uint8_t* w, size_t, size_t blk, unsigned j) {
        const uint8_t* p = w + blk * 144;
        Block k;
        k.head = load_weights(p);
        const Words q = load_weights(p + 16 + 16 * j);
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            k.lo.w[i] = q.w[i] & NIBBLES;
            k.hi.w[i] = (q.w[i] >> 4) & NIBBLES;
        }
        return k;
    }
};

// Bit s of qh byte l is the fifth bit of element l of sub-block s.
struct KqQ5K : K4Lane {
    __device__ static Block load(const uint8_t* w, size_t, size_t blk, unsigned j) {
        const uint8_t* p = w + blk * 176;
        const unsigned c = j / 2;
        Block k;
        k.head = load_weights(p);
        const Words qh = load_weights(p + 16 + 16 * (j % 2));
        const Words q = load_weights(p + 48 + 16 * j);
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            const unsigned bits = static_cast<unsigned>(qh.w[i]);
            k.lo.w[i] = (q.w[i] & NIBBLES) | (((bits >> (2 * c)) & 0x01010101) << 4);
            k.hi.w[i] = ((q.w[i] >> 4) & NIBBLES) | (((bits >> (2 * c + 1)) & 0x01010101) << 4);
        }
        return k;
    }
};

// Q6_K, planar as layout.rs stores it: lane j holds elements 32j..32j+31,
// group g = j % 4 of half n = j / 4, which are runs 2j and 2j + 1.
struct KqQ6K {
    // The two runs' scales and their quants as stored (+ 32).
    struct Block {
        float scale[2];
        Words q[2];
    };

    __device__ static Block load(const uint8_t* w, size_t total, size_t blk, unsigned j) {
        const unsigned n = j / 4, g = j % 4;
        const uint8_t* ql = w + blk * 128 + 64 * n + 32 * (g & 1);
        const uint8_t* qh = w + total * 128 + blk * 64 + 32 * n;
        const unsigned scales =
            __ldg(reinterpret_cast<const unsigned*>(w + total * 192 + blk * 16) + j / 2);
        const float d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 208) + blk));
        Block k;
#pragma unroll
        for (unsigned r = 0; r < 2; ++r) {
            k.scale[r] = k6_group(d, scales, 2 * j + r);
            const Words low = load_weights(ql + 16 * r);
            const Words high = load_weights(qh + 16 * r);
#pragma unroll
            for (unsigned i = 0; i < 4; ++i) k.q[r].w[i] = k6_stored(low.w[i], high.w[i], g);
        }
        return k;
    }

    __device__ static float term(const Block& k, unsigned b, unsigned j, Q8Input x) {
        const int8_t* xp = x.qs + b * 256 + 32 * j;
        const float xd = __ldg(x.ds + b * 8 + j).x;
        // Dotting the stored +32 with the input takes it back out.
        const Words bias = {{0x20202020, 0x20202020, 0x20202020, 0x20202020}};
        float t[2];
#pragma unroll
        for (unsigned r = 0; r < 2; ++r) {
            const Words a = load_cached(xp + 16 * r);
            t[r] = kq_term(k.scale[r], 0.0f, xd, 0.0f, dot16(k.q[r], a) - dot16(bias, a));
        }
        return __fadd_rn(t[0], t[1]);
    }
};

// Y = W X for N inputs; output i of row r goes to y[i * rows + r].
template <class F, unsigned N>
__device__ __forceinline__ void gemv_kq(const uint8_t* w, Q8Input x, float* y, unsigned rows,
                                        unsigned blocks_per_row, size_t total) {
    const unsigned row = blockIdx.x * (blockDim.x / WARP) + threadIdx.x / WARP;
    if (row >= rows) return;
    const unsigned lane = threadIdx.x % WARP, v = lane / 8, j = lane % 8;
    const unsigned len = blocks_per_row * 256;
    const size_t first = static_cast<size_t>(row) * blocks_per_row;

    float acc[N] = {};
    for (unsigned base = 0; base < blocks_per_row; base += KQ_SPLIT) {
        const unsigned b = base + v;
        const bool active = b < blocks_per_row;
        typename F::Block blk = {};
        if (active) blk = F::load(w, total, first + b, j);
#pragma unroll
        for (unsigned i = 0; i < N; ++i) {
            // Idle groups read block 0 of the input; their sums are dropped.
            float t = F::term(blk, active ? b : 0, j, batch_row(x, i, len));
#pragma unroll
            for (unsigned o = 1; o < 8; o *= 2) t = __fadd_rn(t, __shfl_xor_sync(FULL_MASK, t, o));
            if (active) acc[i] = __fadd_rn(acc[i], t);
        }
    }
#pragma unroll
    for (unsigned i = 0; i < N; ++i) {
        float s = __shfl_sync(FULL_MASK, acc[i], 0);
#pragma unroll
        for (unsigned p = 1; p < KQ_SPLIT; ++p) s = __fadd_rn(s, __shfl_sync(FULL_MASK, acc[i], 8 * p));
        if (lane == 0) y[static_cast<size_t>(i) * rows + row] = s;
    }
}

#define GEMV_KERNEL_KQ(name, F, N)                                                          \
    extern "C" __global__ void __launch_bounds__(128)                                       \
        name##_##N(const uint8_t* w, const int8_t* xq, const float2* xds, float* y,        \
                   unsigned rows, unsigned blocks_per_row, size_t total) {                  \
        gemv_kq<F, N>(w, Q8Input{xq, xds}, y, rows, blocks_per_row, total);                 \
    }

GEMV_KERNELS(GEMV_KERNEL_KQ, gemv_q4_k, KqQ4K)
GEMV_KERNELS(GEMV_KERNEL_KQ, gemv_q5_k, KqQ5K)
GEMV_KERNELS(GEMV_KERNEL_KQ, gemv_q6_k, KqQ6K)
