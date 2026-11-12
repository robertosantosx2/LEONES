#pragma once

#include "attention.cuh"
#include "mma.cuh"

// Attention for large batches, flash style: a block of four warps takes 64
// queries of one head and walks their keys in tiles through shared memory,
// the next tile copied in while the current one is used, on f16 tensor
// cores with f32 sums and an online softmax, so no scores are stored. The
// cached keys and values are f16 already, or widened to f16 from q8_0;
// queries and attention weights enter as the sum of two f16 values, high
// and low part, which keeps their products as accurate as f32 arithmetic. Queries were normalized and
// rotated, and keys and values cached, by `attn_prepare`; the gated result
// goes to the f32 values of `out`, quantized afterwards.
//
// Warp w owns queries 16w..16w+15 as f16 A fragments, their high parts in
// registers and their low parts too, except for heads of 256, which keep
// the low parts in shared memory. Heads of 512 fit neither: each block
// takes half of the value dims, and the queries are split from f32 as each
// tile needs them. Lane (g, t) holds the scores of queries g
// and g + 8 against keys 8j + 2t and 8j + 2t + 1 of the tile, and their
// outputs for dims 8d + 2t and 8d + 2t + 1.

constexpr unsigned FLASH_Q = 64;
constexpr unsigned FLASH_THREADS = 128;
// f16 values of padding per row, which puts the eight rows of an 8x8
// matrix load in distinct banks.
constexpr unsigned FLASH_PAD = 8;

// Keys per tile: fewer for heads of 256 and up.
__host__ __device__ constexpr unsigned flash_keys(unsigned hd) { return hd >= 256 ? 16 : 32; }

// Value dims of a block: heads of 512 leave their outputs to two blocks,
// as the f32 sums of all 512 would not fit the registers.
__host__ __device__ constexpr unsigned flash_values(unsigned hd) { return hd == 512 ? 256 : hd; }

// Whether the low parts of the queries live in shared memory.
__host__ __device__ constexpr bool flash_low_shared(unsigned hd) { return hd == 256; }

// Bytes of dynamic shared memory for head size `hd`: two tiles each of keys
// and values, then any low parts of the queries.
__host__ __device__ constexpr unsigned flash_shared(unsigned hd) {
    return (2 * flash_keys(hd) * (2 * FLASH_PAD + hd + flash_values(hd)) +
            (flash_low_shared(hd) ? FLASH_Q * (hd + FLASH_PAD) : 0)) *
           2;
}

// Copies values at..at + 8 of a cache into shared memory as f16: f16 rows
// asynchronously, q8_0 rows widened on the way.
__device__ __forceinline__ void flash_load8(__half* dst, const void* cache, const __half* scale, size_t at) {
    if (!scale) {
        cp_async16(dst, static_cast<const __half*>(cache) + at);
        return;
    }
    AttnRow<8, true> r;
    r.load(cache, scale, at);
    __half2 h[4];
#pragma unroll
    for (unsigned e = 0; e < 4; ++e) h[e] = __float22half2_rn(r.pair(e));
    *reinterpret_cast<uint4*>(dst) = *reinterpret_cast<const uint4*>(h);
}

template <unsigned HD>
__device__ __forceinline__ void attn_flash_impl(const AttnArgs& a, unsigned n) {
    constexpr unsigned KV = flash_keys(HD), VD = flash_values(HD);
    constexpr unsigned ROW = HD + FLASH_PAD, VROW = VD + FLASH_PAD;
    constexpr bool LOW_SHARED = flash_low_shared(HD), Q_SPLIT = VD < HD;
    extern __shared__ __align__(16) __half flash_smem[];
    // [buffer][key][dim]
    __half(*keys)[KV][ROW] = reinterpret_cast<__half(*)[KV][ROW]>(flash_smem);
    __half(*values)[KV][VROW] = reinterpret_cast<__half(*)[KV][VROW]>(flash_smem + 2 * KV * ROW);
    __half(*q_low)[ROW] = reinterpret_cast<__half(*)[ROW]>(flash_smem + 2 * KV * (ROW + VROW));

    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned g = lane / 4, t = lane % 4;
    const unsigned t0 = blockIdx.x * FLASH_Q, h = blockIdx.y, v0 = blockIdx.z * VD;
    const unsigned kvh = h / (a.n_head / a.n_head_kv), kv_dim = a.n_head_kv * HD;
    const unsigned pos0 = a.batch[0];
    const unsigned last = min(t0 + FLASH_Q, n) - 1;
    // tiles start on multiples of KV whatever the batch's first position, so
    // where a prompt is cut changes no sum; keys before `seen` are masked
    const unsigned seen = attn_start(a, pos0 + t0), lo = seen / KV * KV, hi = pos0 + last + 1;

    const auto load_tile = [&](unsigned k0, unsigned buf) {
        const auto slot = [&](unsigned row) {
            const unsigned pos = min(max(k0 + row, seen), hi - 1);
            return static_cast<size_t>(attn_slot(a, pos)) * kv_dim + kvh * HD;
        };
        for (unsigned i = threadIdx.x; i < KV * HD / 8; i += FLASH_THREADS) {
            const unsigned row = i / (HD / 8), col = 8 * (i % (HD / 8));
            flash_load8(&keys[buf][row][col], a.k_cache, a.k_scale, slot(row) + col);
        }
        for (unsigned i = threadIdx.x; i < KV * VD / 8; i += FLASH_THREADS) {
            const unsigned row = i / (VD / 8), col = 8 * (i % (VD / 8));
            flash_load8(&values[buf][row][col], a.v_cache, a.v_scale, slot(row) + v0 + col);
        }
        cp_async_commit();
    };
    load_tile(lo, 0);

    // Rows g and g + 8 of the warp: their positions, first visible keys and
    // queries as A fragments, one per 16 dims.
    unsigned qpos[2], qstart[2];
    const float* q_rows[2];
    [[maybe_unused]] unsigned q[Q_SPLIT ? 1 : HD / 16][4];
    [[maybe_unused]] unsigned q_lo[LOW_SHARED || Q_SPLIT ? 1 : HD / 16][4];
    [[maybe_unused]] __half(*my_low)[ROW] = q_low + 16 * warp;
#pragma unroll
    for (unsigned r = 0; r < 2; ++r) {
        const unsigned tok = t0 + 16 * warp + g + 8 * r;
        qpos[r] = pos0 + tok;
        qstart[r] = attn_start(a, qpos[r]);
        const float* row = a.q + min(tok, n - 1) * a.q_stride + h * a.q_head_stride + 2 * t;
        q_rows[r] = row;
#pragma unroll
        for (unsigned d = 0; d < (Q_SPLIT ? 0 : HD / 16); ++d) {
            const float2 v0 = *reinterpret_cast<const float2*>(row + 16 * d);
            const float2 v1 = *reinterpret_cast<const float2*>(row + 16 * d + 8);
            unsigned lo0, lo1;
            split_pair(v0.x, v0.y, q[d][r], lo0);
            split_pair(v1.x, v1.y, q[d][2 + r], lo1);
            if constexpr (LOW_SHARED) {
                *reinterpret_cast<unsigned*>(&my_low[g + 8 * r][16 * d + 2 * t]) = lo0;
                *reinterpret_cast<unsigned*>(&my_low[g + 8 * r][16 * d + 8 + 2 * t]) = lo1;
            } else {
                q_lo[d][r] = lo0;
                q_lo[d][2 + r] = lo1;
            }
        }
    }
    __syncwarp();
    const float scale = a.scale * 1.4426950408889634f;
    float o[VD / 8][4] = {};
    float m[2] = {-CUDART_INF_F, -CUDART_INF_F}, l[2] = {0.0f, 0.0f};

    for (unsigned k0 = lo, buf = 0; k0 < hi; k0 += KV, buf ^= 1) {
        if (k0 + KV < hi) {
            load_tile(k0 + KV, buf ^ 1);
            cp_async_wait<1>();
        } else {
            cp_async_wait<0>();
        }
        __syncthreads();
        const __half(*ks)[ROW] = keys[buf];
        const __half(*vs)[VROW] = values[buf];

        float s[KV / 8][4] = {};
#pragma unroll
        for (unsigned d = 0; d < HD / 16; ++d) {
            unsigned qh[4], ql[4];
            if constexpr (Q_SPLIT) {
#pragma unroll
                for (unsigned r = 0; r < 2; ++r) {
                    const float2 x0 = *reinterpret_cast<const float2*>(q_rows[r] + 16 * d);
                    const float2 x1 = *reinterpret_cast<const float2*>(q_rows[r] + 16 * d + 8);
                    split_pair(x0.x, x0.y, qh[r], ql[r]);
                    split_pair(x1.x, x1.y, qh[2 + r], ql[2 + r]);
                }
            } else if constexpr (LOW_SHARED) {
#pragma unroll
                for (unsigned i = 0; i < 4; ++i) qh[i] = q[d][i];
                ldsm_x4(ql, &my_low[lane % 16][16 * d + 8 * (lane / 16)]);
            } else {
#pragma unroll
                for (unsigned i = 0; i < 4; ++i) {
                    qh[i] = q[d][i];
                    ql[i] = q_lo[d][i];
                }
            }
#pragma unroll
            for (unsigned j = 0; j < KV / 8; j += 2) {
                unsigned kb[4];
                ldsm_x4(kb, &ks[8 * (j + lane / 16) + lane % 8][16 * d + 8 * ((lane / 8) % 2)]);
                mma_f16(s[j], qh[0], qh[1], qh[2], qh[3], kb[0], kb[1]);
                mma_f16(s[j + 1], qh[0], qh[1], qh[2], qh[3], kb[2], kb[3]);
                mma_f16(s[j], ql[0], ql[1], ql[2], ql[3], kb[0], kb[1]);
                mma_f16(s[j + 1], ql[0], ql[1], ql[2], ql[3], kb[2], kb[3]);
            }
        }

        float alpha[2];
#pragma unroll
        for (unsigned r = 0; r < 2; ++r) {
            float mx = m[r];
#pragma unroll
            for (unsigned j = 0; j < KV / 8; ++j)
#pragma unroll
                for (unsigned c = 0; c < 2; ++c) {
                    const unsigned kp = k0 + 8 * j + 2 * t + c;
                    const bool visible = kp <= qpos[r] && kp >= qstart[r];
                    float& v = s[j][2 * r + c];
                    v = visible ? v * scale : -CUDART_INF_F;
                    mx = fmaxf(mx, v);
                }
            mx = fmaxf(mx, __shfl_xor_sync(FULL_MASK, mx, 1));
            mx = fmaxf(mx, __shfl_xor_sync(FULL_MASK, mx, 2));
            // A row that has seen no visible key yet keeps nothing to rescale.
            alpha[r] = mx == -CUDART_INF_F ? 1.0f : exp2f(m[r] - mx);
            const float base = mx == -CUDART_INF_F ? 0.0f : mx;
            float sum = 0.0f;
#pragma unroll
            for (unsigned j = 0; j < KV / 8; ++j)
#pragma unroll
                for (unsigned c = 0; c < 2; ++c) {
                    float& v = s[j][2 * r + c];
                    v = exp2f(v - base);
                    sum += v;
                }
            l[r] = fmaf(l[r], alpha[r], sum);
            m[r] = mx;
        }
#pragma unroll
        for (unsigned d = 0; d < VD / 8; ++d) {
            o[d][0] *= alpha[0];
            o[d][1] *= alpha[0];
            o[d][2] *= alpha[1];
            o[d][3] *= alpha[1];
        }

#pragma unroll
        for (unsigned kk = 0; kk < KV / 16; ++kk) {
            const float(&p0)[4] = s[2 * kk];
            const float(&p1)[4] = s[2 * kk + 1];
            unsigned w[4], wl[4];
            split_pair(p0[0], p0[1], w[0], wl[0]);
            split_pair(p0[2], p0[3], w[1], wl[1]);
            split_pair(p1[0], p1[1], w[2], wl[2]);
            split_pair(p1[2], p1[3], w[3], wl[3]);
#pragma unroll
            for (unsigned d = 0; d < VD / 8; d += 2) {
                unsigned vb[4];
                ldsm_x4_trans(vb, &vs[16 * kk + (lane % 8) + 8 * ((lane / 8) % 2)][8 * (d + lane / 16)]);
                mma_f16(o[d], w[0], w[1], w[2], w[3], vb[0], vb[1]);
                mma_f16(o[d + 1], w[0], w[1], w[2], w[3], vb[2], vb[3]);
                mma_f16(o[d], wl[0], wl[1], wl[2], wl[3], vb[0], vb[1]);
                mma_f16(o[d + 1], wl[0], wl[1], wl[2], wl[3], vb[2], vb[3]);
            }
        }
        // The next trip copies into the other buffer; this one is free only
        // once every warp is done with it.
        __syncthreads();
    }

#pragma unroll
    for (unsigned r = 0; r < 2; ++r) {
        const unsigned tok = t0 + 16 * warp + g + 8 * r;
        // Each lane summed the weights of its own columns.
        float sum = l[r] + __shfl_xor_sync(FULL_MASK, l[r], 1);
        sum += __shfl_xor_sync(FULL_MASK, sum, 2);
        if (tok >= n) continue;
        const float inv = 1.0f / sum;
        const float* gates = a.q + tok * a.q_stride + h * a.q_head_stride + HD;
        const float head_gate = a.head_gate ? sigmoid(a.head_gate[tok * a.n_head + h]) : 1.0f;
        float* out = a.out.x + static_cast<size_t>(tok) * a.n_head * HD + h * HD;
#pragma unroll
        for (unsigned d = 0; d < VD / 8; ++d) {
            const unsigned col = v0 + 8 * d + 2 * t;
            float2 v = make_float2(o[d][2 * r] * inv, o[d][2 * r + 1] * inv);
            if (a.interleaved_gate) {
                v.x *= sigmoid(gates[col]);
                v.y *= sigmoid(gates[col + 1]);
            } else {
                v.x *= head_gate;
                v.y *= head_gate;
            }
            *reinterpret_cast<float2*>(out + col) = v;
        }
    }
}

// grid (ceil(n / FLASH_Q), n_head, head_dim / flash_values(head_dim)), block
// FLASH_THREADS, flash_shared(head_dim) bytes of dynamic shared memory; `n`
// is the batch size.
extern "C" __global__ void __launch_bounds__(FLASH_THREADS) attn_flash(AttnArgs a, unsigned n) {
    switch (a.head_dim) {
        case 64: attn_flash_impl<64>(a, n); break;
        case 128: attn_flash_impl<128>(a, n); break;
        case 256: attn_flash_impl<256>(a, n); break;
        default: attn_flash_impl<512>(a, n); break;
    }
}
