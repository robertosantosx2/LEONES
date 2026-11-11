#pragma once

#include "quantize.cuh"

// Gated attention over an f16 KV cache, for a batch of tokens at consecutive
// positions. `attn_norm_rows` applies query and key norms that span all
// heads of a token; `attn_prepare` normalizes and rotates queries and keys and
// stores keys and values; `attn_chunk` attends each (token, head) over one
// chunk of positions; `attn_combine` merges the chunks and applies the gate.
// Chunks start at fixed multiples of ATTN_CHUNK, so a token's result does not
// depend on how many other tokens share its batch.

constexpr unsigned ATTN_CHUNK = 64;
constexpr unsigned ATTN_WARPS = 4;
constexpr unsigned ATTN_STREAMS = 4;

struct AttnArgs {
    // [first position, token ids...]
    const unsigned* batch;
    // Per token, n_head query heads `q_head_stride` apart; with an
    // interleaved gate each head's queries are followed by its gate values.
    float* q;
    const float* k;
    const float* v;
    const float* q_norm;
    const float* k_norm;
    const float* rope_factors;
    // f16 values, or q8_0 quants when the matching scales are set.
    void* k_cache;
    void* v_cache;
    // One gate value per head and token, or null.
    const float* head_gate;
    // Per (token, head, chunk): max score, sum of weights, weighted values.
    float* partial;
    Act out;
    unsigned q_stride;
    unsigned q_head_stride;
    unsigned n_head;
    unsigned n_head_kv;
    unsigned head_dim;
    unsigned rope_dims;
    float rope_base;
    float eps;
    float scale;
    // Positions kept, 0 for all; a window is a ring of `slots` entries.
    unsigned window;
    unsigned slots;
    unsigned max_chunks;
    unsigned interleaved_gate;
    // Rotated pairs are (2i, 2i + 1) rather than (i, i + rope_dims / 2).
    unsigned rope_adjacent;
    unsigned norm_after_rope;
    // The query or key norm spans all heads of a token.
    unsigned q_norm_rows;
    unsigned k_norm_rows;
    // Multiplies the rotated values.
    float rope_mscale;
    // Added to the projected queries, keys and values, or null.
    const float* q_bias;
    const float* k_bias;
    const float* v_bias;
    // One f16 scale per 32 cached values of a q8_0 cache, or null.
    __half* k_scale;
    __half* v_scale;
    // (time, row, column) rotary positions per token, pair j turning by the
    // (j % 3)-th, or null to turn every pair by the cache position.
    const unsigned* grid;
    // RMS-normalizes each value head, without weights.
    unsigned v_norm;
};

__device__ __forceinline__ unsigned attn_slot(const AttnArgs& a, unsigned pos) {
    return a.window ? pos % a.slots : pos;
}

// A full cache holds positions below `slots`; the host never runs past
// them, and the kernels do nothing for positions that would.
__device__ __forceinline__ bool attn_fits(const AttnArgs& a, unsigned pos) {
    return a.window || pos < a.slots;
}

__device__ __forceinline__ unsigned attn_start(const AttnArgs& a, unsigned pos) {
    return a.window && pos + 1 > a.window ? pos + 1 - a.window : 0;
}

// Stores element `at` of a cache. A q8_0 cache keeps a block of 32 values,
// one warp's, as int8 multiples of an f16 scale: the largest magnitude over
// 127.
__device__ __forceinline__ void attn_store(void* cache, __half* scale, size_t at, float x) {
    if (!scale) {
        static_cast<__half*>(cache)[at] = __float2half(x);
        return;
    }
    float amax = fabsf(x);
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) amax = fmaxf(amax, __shfl_xor_sync(FULL_MASK, amax, o));
    const float d = amax / 127.0f;
    static_cast<int8_t*>(cache)[at] = static_cast<int8_t>(d != 0.0f ? __float2int_rn(x / d) : 0);
    if (at % 32 == 0) scale[at / 32] = __float2half(d);
}

// E consecutive values of a cache row as one lane loads them: f16, or q8_0
// quants with the scale of their block.
template <unsigned E, bool Q8>
struct AttnRow {
    __half2 h[E / 2];

    __device__ __forceinline__ void load(const void* cache, const __half*, size_t at) {
        const __half2* p = reinterpret_cast<const __half2*>(static_cast<const __half*>(cache) + at);
#pragma unroll
        for (unsigned e = 0; e < E / 2; ++e) h[e] = p[e];
    }

    __device__ __forceinline__ float2 pair(unsigned e) const { return __half22float2(h[e]); }
};

template <unsigned E>
struct AttnRow<E, true> {
    unsigned w[(E + 3) / 4];
    float d;

    __device__ __forceinline__ void load(const void* cache, const __half* scale, size_t at) {
        const int8_t* p = static_cast<const int8_t*>(cache) + at;
        if constexpr (E == 2) {
            w[0] = *reinterpret_cast<const unsigned short*>(p);
        } else if constexpr (E == 4) {
            w[0] = *reinterpret_cast<const unsigned*>(p);
        } else {
            const uint2 x = *reinterpret_cast<const uint2*>(p);
            w[0] = x.x;
            w[1] = x.y;
        }
        d = __half2float(scale[at / 32]);
    }

    __device__ __forceinline__ float2 pair(unsigned e) const {
        const unsigned word = w[e / 2] >> (16 * (e % 2));
        return make_float2(d * static_cast<int8_t>(word), d * static_cast<int8_t>(word >> 8));
    }
};

// grid (tokens, 2), block a multiple of 32: normalizes all query heads
// (y = 0) or all key heads (y = 1) of a token together, in place.
extern "C" __global__ void attn_norm_rows(AttnArgs a) {
    const unsigned t = blockIdx.x;
    const bool is_q = blockIdx.y == 0;
    if (!(is_q ? a.q_norm_rows : a.k_norm_rows) || !attn_fits(a, a.batch[0] + t)) return;
    const unsigned len = (is_q ? a.n_head : a.n_head_kv) * a.head_dim;
    float* x = is_q ? a.q + t * a.q_stride : const_cast<float*>(a.k) + t * len;
    const float* w = is_q ? a.q_norm : a.k_norm;
    float ss = 0.0f;
    for (unsigned i = threadIdx.x; i < len; i += blockDim.x) ss = fmaf(x[i], x[i], ss);
    const float scale = 1.0f / sqrtf(block_sum(ss) / static_cast<float>(len) + a.eps);
    for (unsigned i = threadIdx.x; i < len; i += blockDim.x) x[i] *= scale * w[i];
}

// RMS norm of one head, element `i` of which this thread holds.
__device__ __forceinline__ float attn_head_norm(const AttnArgs& a, float v, float w) {
    const float scale =
        1.0f / sqrtf(block_sum(v * v) / static_cast<float>(a.head_dim) + a.eps);
    return v * (scale * w);
}

// grid (tokens, n_head + n_head_kv), block head_dim.
extern "C" __global__ void attn_prepare(AttnArgs a) {
    __shared__ float rotated[1024];
    const unsigned t = blockIdx.x, h = blockIdx.y, i = threadIdx.x, hd = a.head_dim;
    const unsigned pos = a.batch[0] + t;
    if (!attn_fits(a, pos)) return;
    const unsigned kv_dim = a.n_head_kv * hd;
    const bool is_q = h < a.n_head;
    const unsigned kvh = h - a.n_head;
    const float* src = is_q ? a.q + t * a.q_stride + h * a.q_head_stride
                            : a.k + t * kv_dim + kvh * hd;
    const bool rows = is_q ? a.q_norm_rows : a.k_norm_rows;
    const float* norm = rows ? nullptr : is_q ? a.q_norm : a.k_norm;

    const float* bias = is_q ? a.q_bias : a.k_bias;
    float v = src[i];
    if (bias) v += bias[(is_q ? h : kvh) * hd + i];
    if (norm && !a.norm_after_rope) v = attn_head_norm(a, v, norm[i]);
    rotated[i] = v;
    __syncthreads();
    if (i < a.rope_dims) {
        const unsigned half = a.rope_dims / 2;
        const unsigned j = a.rope_adjacent ? i / 2 : i % half;
        const unsigned turn = a.grid ? a.grid[3 * t + j % 3] : pos;
        float theta = static_cast<float>(turn) *
                      powf(a.rope_base, -static_cast<float>(2 * j) / static_cast<float>(a.rope_dims));
        if (a.rope_factors) theta /= a.rope_factors[j];
        float s, c;
        sincosf(theta, &s, &c);
        s *= a.rope_mscale;
        c *= a.rope_mscale;
        const unsigned lo = a.rope_adjacent ? 2 * j : j, hi = a.rope_adjacent ? 2 * j + 1 : j + half;
        const float x0 = rotated[lo], x1 = rotated[hi];
        v = i == lo ? x0 * c - x1 * s : x0 * s + x1 * c;
    }
    if (norm && a.norm_after_rope) v = attn_head_norm(a, v, norm[i]);
    if (is_q) {
        a.q[t * a.q_stride + h * a.q_head_stride + i] = v;
        return;
    }
    const size_t at = static_cast<size_t>(attn_slot(a, pos)) * kv_dim + kvh * hd + i;
    attn_store(a.k_cache, a.k_scale, at, v);
    float value = a.v[t * kv_dim + kvh * hd + i];
    if (a.v_bias) value += a.v_bias[kvh * hd + i];
    if (a.v_norm) value = attn_head_norm(a, value, 1.0f);
    attn_store(a.v_cache, a.v_scale, at, value);
}

// Chunk `c` of token `t` for query heads h0..h0 + G, all on one warp. Stream
// w of the chunk takes positions lo + w, lo + w + ATTN_STREAMS, ... with its
// own running max, weight sum and weighted values; the streams are merged in
// order at the end. One step loads a position of every stream, so a warp has
// ATTN_STREAMS rows in flight and its score reductions overlap.
template <unsigned E, unsigned G, bool QK, bool QV>
__device__ __forceinline__ void attn_chunk_one(const AttnArgs& a, unsigned t, unsigned h0, unsigned c) {
    constexpr unsigned HD = E * WARP, S = ATTN_STREAMS;
    const unsigned kvh = h0 / (a.n_head / a.n_head_kv);
    const unsigned pos = a.batch[0] + t;
    const unsigned start = attn_start(a, pos);
    const unsigned chunk = start / ATTN_CHUNK + c;
    const unsigned lo = max(chunk * ATTN_CHUNK, start), hi = min(chunk * ATTN_CHUNK + ATTN_CHUNK, pos + 1);

    const unsigned lane = threadIdx.x % WARP;
    const unsigned kv_dim = a.n_head_kv * HD;
    float q[G][E], acc[S][G][E], m[S][G], l[S][G];
#pragma unroll
    for (unsigned g = 0; g < G; ++g) {
        const float* qp = a.q + t * a.q_stride + (h0 + g) * a.q_head_stride + lane * E;
#pragma unroll
        for (unsigned e = 0; e < E; ++e) q[g][e] = qp[e];
#pragma unroll
        for (unsigned w = 0; w < S; ++w) {
#pragma unroll
            for (unsigned e = 0; e < E; ++e) acc[w][g][e] = 0.0f;
            m[w][g] = -CUDART_INF_F;
            l[w][g] = 0.0f;
        }
    }
    const size_t col = static_cast<size_t>(kvh) * HD + lane * E;
    for (unsigned p0 = lo; p0 < hi; p0 += S) {
        AttnRow<E, QK> kh[S];
        AttnRow<E, QV> vh[S];
#pragma unroll
        for (unsigned w = 0; w < S; ++w) {
            const unsigned p = p0 + w < hi ? p0 + w : lo;
            const size_t at = static_cast<size_t>(attn_slot(a, p)) * kv_dim + col;
            kh[w].load(a.k_cache, a.k_scale, at);
            vh[w].load(a.v_cache, a.v_scale, at);
        }
        float s[S][G];
#pragma unroll
        for (unsigned w = 0; w < S; ++w) {
#pragma unroll
            for (unsigned g = 0; g < G; ++g) {
                float d = 0.0f;
#pragma unroll
                for (unsigned e = 0; e < E / 2; ++e) {
                    const float2 k = kh[w].pair(e);
                    d = fmaf(q[g][2 * e], k.x, d);
                    d = fmaf(q[g][2 * e + 1], k.y, d);
                }
                s[w][g] = d;
            }
        }
#pragma unroll
        for (unsigned w = 0; w < S; ++w)
#pragma unroll
            for (unsigned g = 0; g < G; ++g) s[w][g] = warp_sum(s[w][g]) * a.scale;
#pragma unroll
        for (unsigned w = 0; w < S; ++w) {
            if (p0 + w >= hi) break;
#pragma unroll
            for (unsigned g = 0; g < G; ++g) {
                const float m_new = fmaxf(m[w][g], s[w][g]);
                const float keep = expf(m[w][g] - m_new), wt = expf(s[w][g] - m_new);
                l[w][g] = fmaf(l[w][g], keep, wt);
#pragma unroll
                for (unsigned e = 0; e < E / 2; ++e) {
                    const float2 v = vh[w].pair(e);
                    acc[w][g][2 * e] = fmaf(acc[w][g][2 * e], keep, wt * v.x);
                    acc[w][g][2 * e + 1] = fmaf(acc[w][g][2 * e + 1], keep, wt * v.y);
                }
                m[w][g] = m_new;
            }
        }
    }

#pragma unroll
    for (unsigned g = 0; g < G; ++g) {
        float mx = m[0][g];
#pragma unroll
        for (unsigned w = 1; w < S; ++w) mx = fmaxf(mx, m[w][g]);
        const size_t th = static_cast<size_t>(t) * a.n_head + h0 + g;
        float* out = a.partial + (th * a.max_chunks + c) * (HD + 2);
        float o[E] = {}, sum = 0.0f;
#pragma unroll
        for (unsigned w = 0; w < S; ++w) {
            if (m[w][g] == -CUDART_INF_F) continue;
            const float f = expf(m[w][g] - mx);
            sum = fmaf(l[w][g], f, sum);
#pragma unroll
            for (unsigned e = 0; e < E; ++e) o[e] = fmaf(acc[w][g][e], f, o[e]);
        }
#pragma unroll
        for (unsigned e = 0; e < E; ++e) out[2 + lane * E + e] = o[e];
        if (lane == 0) {
            out[0] = mx;
            out[1] = sum;
        }
    }
}

// Lanes own E = head_dim / 32 consecutive elements of a head. A block takes
// G query heads of one KV group, so each key and value is read once for all
// of them, and each of its warps the chunks warp + ATTN_WARPS * y,
// warp + ATTN_WARPS * (y + gridDim.y), ...; every head's arithmetic is the
// same whatever G and the grid.
template <unsigned E, unsigned G, bool QK, bool QV>
__device__ __forceinline__ void attn_chunk_impl(const AttnArgs& a) {
    const unsigned blocks = a.n_head / G;
    const unsigned t = blockIdx.x / blocks, h0 = blockIdx.x % blocks * G;
    const unsigned pos = a.batch[0] + t;
    if (!attn_fits(a, pos)) return;
    const unsigned first = attn_start(a, pos) / ATTN_CHUNK, last = pos / ATTN_CHUNK;
    for (unsigned c = blockIdx.y * ATTN_WARPS + threadIdx.x / WARP; first + c <= last;
         c += gridDim.y * ATTN_WARPS)
        attn_chunk_one<E, G, QK, QV>(a, t, h0, c);
}

template <unsigned G, bool QK, bool QV>
__device__ __forceinline__ void attn_chunk_dispatch(const AttnArgs& a) {
    switch (a.head_dim) {
        case 64: attn_chunk_impl<2, G, QK, QV>(a); break;
        case 128: attn_chunk_impl<4, G, QK, QV>(a); break;
        case 256: attn_chunk_impl<8, G, QK, QV>(a); break;
        default: attn_chunk_impl<16, G, QK, QV>(a); break;
    }
}

// grid (tokens * n_head / G, up to max_chunks / ATTN_WARPS), block
// 32 * ATTN_WARPS; G divides the query heads per KV head.
#define ATTN_CHUNK_KERNEL(G)                                                         \
    extern "C" __global__ void attn_chunk_##G(AttnArgs a) {                          \
        if (a.k_scale && a.v_scale) attn_chunk_dispatch<G, true, true>(a);           \
        else if (a.k_scale) attn_chunk_dispatch<G, true, false>(a);                  \
        else if (a.v_scale) attn_chunk_dispatch<G, false, true>(a);                  \
        else attn_chunk_dispatch<G, false, false>(a);                                \
    }

ATTN_CHUNK_KERNEL(1)
ATTN_CHUNK_KERNEL(2)

constexpr unsigned ATTN_COMBINE_THREADS = 64;

// grid (tokens * n_head, head_dim / ATTN_COMBINE_THREADS), block
// ATTN_COMBINE_THREADS. The chunks are summed in order; their weights are
// staged in shared memory a tile at a time so the loads of the weighted
// values run ahead of the sums.
extern "C" __global__ void attn_combine(AttnArgs a) {
    constexpr unsigned T = ATTN_COMBINE_THREADS;
    __shared__ float weights[T], sums[T], maxes[T / WARP];
    const unsigned th = blockIdx.x, t = th / a.n_head, h = th % a.n_head;
    const unsigned hd = a.head_dim, i = blockIdx.y * T + threadIdx.x;
    const unsigned pos = a.batch[0] + t;
    if (!attn_fits(a, pos)) return;
    const unsigned first = attn_start(a, pos) / ATTN_CHUNK;
    const unsigned chunks = pos / ATTN_CHUNK - first + 1;
    const float* p = a.partial + static_cast<size_t>(th) * a.max_chunks * (hd + 2);

    float mx = -CUDART_INF_F;
    for (unsigned c = threadIdx.x; c < chunks; c += T) mx = fmaxf(mx, p[c * (hd + 2)]);
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) mx = fmaxf(mx, __shfl_xor_sync(FULL_MASK, mx, o));
    if (threadIdx.x % WARP == 0) maxes[threadIdx.x / WARP] = mx;
    __syncthreads();
#pragma unroll
    for (unsigned w = 0; w < T / WARP; ++w) mx = fmaxf(mx, maxes[w]);

    float sum = 0.0f, o = 0.0f;
    for (unsigned c0 = 0; c0 < chunks; c0 += T) {
        if (c0 + threadIdx.x < chunks) {
            const float* part = p + (c0 + threadIdx.x) * (hd + 2);
            weights[threadIdx.x] = expf(part[0] - mx);
            sums[threadIdx.x] = part[1];
        }
        __syncthreads();
        const unsigned n = min(T, chunks - c0);
        const float* values = p + c0 * (hd + 2) + 2 + i;
#pragma unroll 16
        for (unsigned c = 0; c < n; ++c) {
            sum = fmaf(sums[c], weights[c], sum);
            o = fmaf(values[c * (hd + 2)], weights[c], o);
        }
        __syncthreads();
    }
    o /= sum;
    const float gate = a.interleaved_gate
                           ? a.q[t * a.q_stride + h * a.q_head_stride + hd + i]
                           : a.head_gate ? a.head_gate[t * a.n_head + h] : CUDART_INF_F;
    a.out.put(static_cast<size_t>(t) * a.n_head * hd + h * hd + i, o * sigmoid(gate));
}

// grid (tokens, kv_dim / blockDim): copies the cache entries of the batch's
// positions from one cache to another of the same slots.
extern "C" __global__ void attn_copy_kv(const unsigned* batch, const __half* k, const __half* v,
                                        __half* k_out, __half* v_out, unsigned kv_dim,
                                        unsigned slots) {
    const unsigned i = blockIdx.y * blockDim.x + threadIdx.x;
    if (i >= kv_dim) return;
    const size_t at = static_cast<size_t>((batch[0] + blockIdx.x) % slots) * kv_dim + i;
    k_out[at] = k[at];
    v_out[at] = v[at];
}
