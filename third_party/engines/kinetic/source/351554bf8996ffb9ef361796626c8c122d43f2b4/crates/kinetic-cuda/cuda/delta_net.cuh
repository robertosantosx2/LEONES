#pragma once

#include "quantize.cuh"

// Gated delta-rule linear attention. `delta_conv` runs the causal depthwise
// convolution and the l2 norms and appends each token's inputs to the
// recurrence to a journal; `delta_rule` steps the per-head state through
// journal rows, either for a forward pass or to replay kept tokens after a
// rollback, with the same arithmetic both times; `delta_gated_norm` applies
// the per-head norm and the output gate.

struct DeltaArgs {
    // [first position, token ids...]
    const unsigned* batch;
    // Per token: projected queries, keys and values, then alpha and beta.
    const float* qkv;
    const float* alpha;
    const float* beta;
    // `taps` weights per channel, oldest input first.
    const float* conv;
    // The last convolution inputs, row `pos % ring` holding position `pos`.
    float* ring;
    // Per token: convolved and normalized channels, then alpha and beta;
    // for a large batch, the scratch of delta_chunk.cuh instead.
    float* journal;
    const float* dt_bias;
    const float* a;
    // State read and written; they may be the same buffer.
    const float* s_in;
    float* s_out;
    // Recurrence output per token, or null when only replaying.
    float* out;
    const float* z;
    const float* norm;
    Act gated;
    // Tokens to process and the journal row of the first.
    unsigned n;
    unsigned first;
    unsigned channels;
    unsigned taps;
    unsigned ring_len;
    unsigned n_k_heads;
    unsigned n_v_heads;
    unsigned head_k_dim;
    unsigned head_v_dim;
    float eps;
    float q_scale;
};

__device__ __forceinline__ unsigned journal_stride(const DeltaArgs& a) {
    return a.channels + 2 * a.n_v_heads;
}

// grid channels / head_k_dim, block head_k_dim: a block is one head of
// queries or keys, which it l2-normalizes, or a run of value channels.
extern "C" __global__ void delta_conv(DeltaArgs a) {
    const unsigned c = blockIdx.x * blockDim.x + threadIdx.x;
    const bool is_qk = blockIdx.x < 2 * a.n_k_heads;
    const bool is_q = blockIdx.x < a.n_k_heads;
    const float* w = a.conv + static_cast<size_t>(c) * a.taps;
    const unsigned stride = journal_stride(a);
    const unsigned pos0 = a.batch[0];
    for (unsigned t = 0; t < a.n; ++t) {
        const unsigned pos = pos0 + t;
        a.ring[static_cast<size_t>(pos % a.ring_len) * a.channels + c] =
            a.qkv[static_cast<size_t>(t) * a.channels + c];
        float acc = 0.0f;
        for (unsigned i = 0; i < a.taps; ++i) {
            const unsigned p = (pos + a.ring_len - (a.taps - 1) + i) % a.ring_len;
            acc = fmaf(w[i], a.ring[static_cast<size_t>(p) * a.channels + c], acc);
        }
        float v = silu(acc);
        if (is_qk) {
            v *= 1.0f / fmaxf(sqrtf(block_sum(v * v)), a.eps);
            if (is_q) v *= a.q_scale;
        }
        float* row = a.journal + static_cast<size_t>(a.first + t) * stride;
        row[c] = v;
        if (blockIdx.x == 0 && threadIdx.x < 2 * a.n_v_heads) {
            const unsigned h = threadIdx.x;
            row[a.channels + h] = h < a.n_v_heads ? a.alpha[t * a.n_v_heads + h]
                                                  : a.beta[t * a.n_v_heads + h - a.n_v_heads];
        }
    }
}

__device__ __forceinline__ float softplus(float x) { return x > 20.0f ? x : log1pf(expf(x)); }

constexpr unsigned DELTA_ROWS = 4;
constexpr unsigned DELTA_WARPS = 4;

// grid (n_v_heads, head_v_dim / 16), block 128; head_k_dim is 128, four
// values per lane. Each warp keeps four rows of one head's state in registers
// across all tokens: S = decay * S; S += b * (v - S k) k^T; o = S q.
extern "C" __global__ void __launch_bounds__(WARP * DELTA_WARPS) delta_rule(DeltaArgs a) {
    constexpr unsigned E = 4;
    const unsigned vh = blockIdx.x, kh = vh % a.n_k_heads;
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned row0 = (blockIdx.y * DELTA_WARPS + warp) * DELTA_ROWS;
    const unsigned dk = a.head_k_dim, dv = a.head_v_dim;
    const size_t head = static_cast<size_t>(vh) * dv * dk;
    const unsigned key_dim = a.n_k_heads * dk;
    const unsigned stride = journal_stride(a);

    float s[DELTA_ROWS][E];
#pragma unroll
    for (unsigned r = 0; r < DELTA_ROWS; ++r) {
        const float4 v = reinterpret_cast<const float4*>(a.s_in + head + (row0 + r) * dk)[lane];
        s[r][0] = v.x, s[r][1] = v.y, s[r][2] = v.z, s[r][3] = v.w;
    }
    for (unsigned t = 0; t < a.n; ++t) {
        const float* row = a.journal + static_cast<size_t>(a.first + t) * stride;
        const float4 q = reinterpret_cast<const float4*>(row + kh * dk)[lane];
        const float4 k = reinterpret_cast<const float4*>(row + key_dim + kh * dk)[lane];
        const float decay = expf(softplus(row[a.channels + vh] + a.dt_bias[vh]) * a.a[vh]);
        const float b = sigmoid(row[a.channels + a.n_v_heads + vh]);
        const float* v = row + 2 * key_dim + vh * dv + row0;
#pragma unroll
        for (unsigned r = 0; r < DELTA_ROWS; ++r) {
            float* x = s[r];
            float sk = x[0] * k.x;
            sk = fmaf(x[1], k.y, sk);
            sk = fmaf(x[2], k.z, sk);
            sk = fmaf(x[3], k.w, sk);
            const float delta = (v[r] - decay * warp_sum(sk)) * b;
            x[0] = fmaf(x[0], decay, k.x * delta);
            x[1] = fmaf(x[1], decay, k.y * delta);
            x[2] = fmaf(x[2], decay, k.z * delta);
            x[3] = fmaf(x[3], decay, k.w * delta);
            if (a.out) {
                float o = x[0] * q.x;
                o = fmaf(x[1], q.y, o);
                o = fmaf(x[2], q.z, o);
                o = fmaf(x[3], q.w, o);
                o = warp_sum(o);
                if (lane == 0) a.out[static_cast<size_t>(t) * a.n_v_heads * dv + vh * dv + row0 + r] = o;
            }
        }
    }
#pragma unroll
    for (unsigned r = 0; r < DELTA_ROWS; ++r)
        reinterpret_cast<float4*>(a.s_out + head + (row0 + r) * dk)[lane] =
            make_float4(s[r][0], s[r][1], s[r][2], s[r][3]);
}

// grid (tokens, n_v_heads), block head_v_dim: gated[t] = rms_norm(out) * norm * silu(z).
extern "C" __global__ void delta_gated_norm(DeltaArgs a) {
    const size_t i = (static_cast<size_t>(blockIdx.x) * a.n_v_heads + blockIdx.y) * a.head_v_dim +
                     threadIdx.x;
    const float o = a.out[i];
    const float scale =
        1.0f / sqrtf(block_sum(o * o) / static_cast<float>(a.head_v_dim) + a.eps);
    a.gated.put(i, o * (scale * a.norm[threadIdx.x]) * silu(a.z[i]));
}
