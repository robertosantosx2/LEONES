#pragma once

#include "quantize.cuh"

// Mamba-2 selective state space mixer. `ssm_conv` runs the causal
// depthwise convolution with bias and SiLU over the `x B C` channels and the
// step sizes, writing each token's results to a journal row; `ssm_ring_store`
// keeps the latest convolution inputs; `ssm_scan` steps the per-head state
// through journal rows, for a forward pass or to replay kept tokens after a
// rollback, with the same arithmetic both times; `ssm_gated_norm` gates the
// result by SiLU(z) and applies the grouped norm.

struct SsmArgs {
    // [first position, token ids...]
    const unsigned* batch;
    // Per token, `width` values: z (inner), x B C (channels), dt (n_head).
    const float* proj;
    // `taps` weights per channel, oldest input first, and a bias per channel.
    const float* conv;
    const float* conv_bias;
    // The last convolution inputs, row `pos % ring_len` holding position `pos`.
    float* ring;
    // Per token: convolved x B C, then the step size of each head.
    float* journal;
    const float* dt_bias;
    // -exp(A_log) and the skip D, per head.
    const float* a;
    const float* d;
    // State read and written; they may be the same buffer.
    const float* s_in;
    float* s_out;
    // Scan output per token, `inner` values, or null when only replaying.
    float* out;
    // Grouped norm weights, or null.
    const float* norm;
    Act gated;
    // Tokens to process and the journal row of the first.
    unsigned n;
    unsigned first;
    unsigned width;
    unsigned channels;
    unsigned taps;
    unsigned ring_len;
    unsigned n_head;
    unsigned head_dim;
    unsigned n_group;
    unsigned d_state;
    float eps;
};

__device__ __forceinline__ unsigned ssm_inner(const SsmArgs& a) { return a.n_head * a.head_dim; }

__device__ __forceinline__ unsigned ssm_stride(const SsmArgs& a) { return a.channels + a.n_head; }

__device__ __forceinline__ float ssm_softplus(float x) { return x > 20.0f ? x : log1pf(expf(x)); }

// grid (ceil(channels / 128), n), block 128: one thread per channel and
// token, reading inputs of earlier batches from the ring.
extern "C" __global__ void ssm_conv(SsmArgs a) {
    const unsigned ch = blockIdx.x * blockDim.x + threadIdx.x, t = blockIdx.y;
    const unsigned inner = ssm_inner(a);
    const int pos0 = static_cast<int>(a.batch[0]), pos = pos0 + static_cast<int>(t);
    float* row = a.journal + static_cast<size_t>(a.first + t) * ssm_stride(a);
    const float* proj = a.proj + static_cast<size_t>(t) * a.width;
    if (ch < a.n_head) row[a.channels + ch] = ssm_softplus(proj[inner + a.channels + ch] + a.dt_bias[ch]);
    if (ch >= a.channels) return;
    const float* w = a.conv + static_cast<size_t>(ch) * a.taps;
    float acc = 0.0f;
    for (unsigned i = 0; i < a.taps; ++i) {
        const int p = pos - static_cast<int>(a.taps - 1 - i);
        float x = 0.0f;
        if (p >= pos0)
            x = a.proj[static_cast<size_t>(p - pos0) * a.width + inner + ch];
        else if (p >= 0)
            x = a.ring[static_cast<size_t>(p % a.ring_len) * a.channels + ch];
        acc = fmaf(w[i], x, acc);
    }
    row[ch] = silu(acc + a.conv_bias[ch]);
}

// grid ceil(channels / 128), block 128: the batch's last inputs into the
// ring, after `ssm_conv` has read the older ones.
extern "C" __global__ void ssm_ring_store(SsmArgs a) {
    const unsigned ch = blockIdx.x * blockDim.x + threadIdx.x;
    if (ch >= a.channels) return;
    const unsigned pos0 = a.batch[0], inner = ssm_inner(a);
    for (unsigned i = 0; i < a.n && i < a.ring_len; ++i) {
        const unsigned t = a.n - 1 - i;
        a.ring[static_cast<size_t>((pos0 + t) % a.ring_len) * a.channels + ch] =
            a.proj[static_cast<size_t>(t) * a.width + inner + ch];
    }
}

constexpr unsigned SSM_ROWS = 4;
constexpr unsigned SSM_WARPS = 4;

// Lanes own E = d_state / 32 consecutive state columns. Each warp keeps
// SSM_ROWS rows of one head's state in registers across all tokens:
// S = exp(dt A) S + dt x B^T; o = S C + D x.
template <unsigned E>
__device__ __forceinline__ void ssm_scan_impl(const SsmArgs& a) {
    const unsigned h = blockIdx.x, g = h / (a.n_head / a.n_group);
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned row0 = (blockIdx.y * SSM_WARPS + warp) * SSM_ROWS;
    const unsigned ds = a.d_state, inner = ssm_inner(a), stride = ssm_stride(a);
    const size_t head = static_cast<size_t>(h) * a.head_dim * ds;
    const float decay_a = a.a[h], skip = a.d[h];

    float s[SSM_ROWS][E];
#pragma unroll
    for (unsigned r = 0; r < SSM_ROWS; ++r)
#pragma unroll
        for (unsigned e = 0; e < E; ++e) s[r][e] = a.s_in[head + (row0 + r) * ds + lane * E + e];
    for (unsigned t = 0; t < a.n; ++t) {
        const float* row = a.journal + static_cast<size_t>(a.first + t) * stride;
        const float* b = row + inner + g * ds + lane * E;
        const float* c = row + inner + (a.n_group + g) * ds + lane * E;
        const float dt = row[a.channels + h];
        const float decay = expf(dt * decay_a);
        float bv[E], cv[E];
#pragma unroll
        for (unsigned e = 0; e < E; ++e) bv[e] = b[e], cv[e] = c[e];
#pragma unroll
        for (unsigned r = 0; r < SSM_ROWS; ++r) {
            const float x = row[h * a.head_dim + row0 + r];
            const float xdt = x * dt;
            float o = 0.0f;
#pragma unroll
            for (unsigned e = 0; e < E; ++e) {
                s[r][e] = fmaf(s[r][e], decay, bv[e] * xdt);
                o = fmaf(s[r][e], cv[e], o);
            }
            if (a.out) {
                o = warp_sum(o);
                if (lane == 0)
                    a.out[static_cast<size_t>(t) * inner + h * a.head_dim + row0 + r] = fmaf(x, skip, o);
            }
        }
    }
#pragma unroll
    for (unsigned r = 0; r < SSM_ROWS; ++r)
#pragma unroll
        for (unsigned e = 0; e < E; ++e) a.s_out[head + (row0 + r) * ds + lane * E + e] = s[r][e];
}

// grid (n_head, head_dim / 16), block 128.
extern "C" __global__ void __launch_bounds__(WARP * SSM_WARPS) ssm_scan(SsmArgs a) {
    switch (a.d_state) {
        case 64: ssm_scan_impl<2>(a); break;
        case 128: ssm_scan_impl<4>(a); break;
        default: ssm_scan_impl<8>(a); break;
    }
}

constexpr unsigned SSM_NORM_THREADS = 256;

// grid (tokens, n_group), block SSM_NORM_THREADS: gated = y * silu(z),
// RMS-normalized over each group when there is a norm.
extern "C" __global__ void __launch_bounds__(SSM_NORM_THREADS) ssm_gated_norm(SsmArgs a) {
    const unsigned t = blockIdx.x, inner = ssm_inner(a), len = inner / a.n_group;
    const size_t first = static_cast<size_t>(t) * inner + blockIdx.y * len;
    const float* z = a.proj + static_cast<size_t>(t) * a.width + blockIdx.y * len;
    float scale = 1.0f;
    if (a.norm) {
        float ss = 0.0f;
        for (unsigned i = threadIdx.x; i < len; i += SSM_NORM_THREADS) {
            const float y = a.out[first + i] * silu(z[i]);
            ss = fmaf(y, y, ss);
        }
        scale = 1.0f / sqrtf(block_sum(ss) / static_cast<float>(len) + a.eps);
    }
    for (unsigned i = threadIdx.x; i < len; i += SSM_NORM_THREADS) {
        const float y = a.out[first + i] * silu(z[i]);
        a.gated.put(first + i, a.norm ? y * (scale * a.norm[blockIdx.y * len + i]) : y);
    }
}
