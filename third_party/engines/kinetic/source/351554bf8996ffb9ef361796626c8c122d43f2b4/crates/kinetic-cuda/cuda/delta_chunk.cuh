#pragma once

#include "delta_net.cuh"

// The delta-rule layer over a large batch, which never records a journal:
// the convolution runs one block per (head of channels, token), and the
// recurrence runs in chunks of DCHUNK tokens in the WY form. Within a chunk
// with cumulative log decays G_t, the updates u_t solve the unit lower
// triangular system (I + A) U = diag(b) V - diag(b e^G) K S0^T with
// A_ti = b_t e^(G_t - G_i) k_t.k_i for i < t, so with T = (I + A)^-1:
//
//   U   = T diag(b) V - (T diag(b e^G) K) S0^T
//   O   = diag(e^G) Q S0^T + (e^(G_t - G_i) q_t.k_i, i <= t) U
//   S_C = e^(G_C) S0 + U^T diag(e^(G_C - G)) K
//
// `delta_chunk_prep` computes everything that does not involve the state,
// for all chunks and heads at once; `delta_chunk_scan` (delta_scan.cuh) then
// walks the chunks of each head in order, a block per 32 rows of its state.
// The batch scratch holds the convolved channels, then per head and token
// W = T diag(b e^G) K, the corrected values T diag(b) V, the masked chunk
// scores and G.

constexpr unsigned DCHUNK = 32;
constexpr unsigned DTHREADS = 128;
// Floats per row of a shared 32 x 128 tile: the padding puts the rows a warp
// reads at once in distinct banks.
constexpr unsigned DTILE_ROW = 132;

struct DeltaBatch {
    float* conv;
    float* w;
    float* u;
    float* p;
    float* gamma;
};

__device__ __forceinline__ DeltaBatch delta_batch(const DeltaArgs& a) {
    const size_t n = a.n, nv = a.n_v_heads;
    DeltaBatch b;
    b.conv = a.journal;
    b.w = b.conv + n * a.channels;
    b.u = b.w + nv * n * a.head_k_dim;
    b.p = b.u + nv * n * a.head_v_dim;
    b.gamma = b.p + nv * n * DCHUNK;
    return b;
}

// grid (channels / head_k_dim, n), block head_k_dim: one head of queries or
// keys, l2-normalized, or a run of value channels, for one token. Inputs
// before the batch come from the ring.
extern "C" __global__ void delta_conv_batch(DeltaArgs a) {
    const unsigned c = blockIdx.x * blockDim.x + threadIdx.x, t = blockIdx.y;
    const bool is_qk = blockIdx.x < 2 * a.n_k_heads;
    const bool is_q = blockIdx.x < a.n_k_heads;
    const float* w = a.conv + static_cast<size_t>(c) * a.taps;
    const int pos0 = static_cast<int>(a.batch[0]), pos = pos0 + static_cast<int>(t);
    float acc = 0.0f;
    for (unsigned i = 0; i < a.taps; ++i) {
        const int p = pos - static_cast<int>(a.taps - 1 - i);
        float x = 0.0f;
        if (p >= pos0) x = a.qkv[static_cast<size_t>(p - pos0) * a.channels + c];
        else if (p >= 0) x = a.ring[static_cast<size_t>(p % a.ring_len) * a.channels + c];
        acc = fmaf(w[i], x, acc);
    }
    float v = silu(acc);
    if (is_qk) {
        v *= 1.0f / fmaxf(sqrtf(block_sum(v * v)), a.eps);
        if (is_q) v *= a.q_scale;
    }
    delta_batch(a).conv[static_cast<size_t>(t) * a.channels + c] = v;
}

// grid ceil(channels / 256), block 256: the last taps - 1 inputs into the
// ring, after `delta_conv_batch` has read the older ones.
extern "C" __global__ void delta_ring_store(DeltaArgs a) {
    const unsigned c = blockIdx.x * blockDim.x + threadIdx.x;
    if (c >= a.channels) return;
    const unsigned pos0 = a.batch[0];
    for (unsigned i = 0; i + 1 < a.taps && i < a.n; ++i) {
        const unsigned t = a.n - 1 - i;
        a.ring[static_cast<size_t>((pos0 + t) % a.ring_len) * a.channels + c] =
            a.qkv[static_cast<size_t>(t) * a.channels + c];
    }
}

// Loads 32 rows of 128 floats, `stride` apart from `src`, into `tile`,
// scaling row i by scale(i); rows at or past `rows` are zero. Every load is
// issued before the first store. The block has DTHREADS threads.
template <class S>
__device__ __forceinline__ void delta_tile(float (*tile)[DTILE_ROW], const float* src,
                                           size_t stride, unsigned rows, S scale) {
    constexpr unsigned PER = DCHUNK * 32 / DTHREADS;
    float4 v[PER];
#pragma unroll
    for (unsigned k = 0; k < PER; ++k) {
        const unsigned i = threadIdx.x + k * DTHREADS, row = i / 32, col = 4 * (i % 32);
        v[k] = row < rows ? *reinterpret_cast<const float4*>(src + row * stride + col)
                          : make_float4(0.0f, 0.0f, 0.0f, 0.0f);
    }
#pragma unroll
    for (unsigned k = 0; k < PER; ++k) {
        const unsigned i = threadIdx.x + k * DTHREADS, row = i / 32, col = 4 * (i % 32);
        const float f = scale(row);
        *reinterpret_cast<float4*>(&tile[row][col]) =
            make_float4(v[k].x * f, v[k].y * f, v[k].z * f, v[k].w * f);
    }
}

// Adds T diag(scale) X to `acc`, thread `col` owning column col of all 32
// rows: tt holds T transposed and x the 32 rows of X.
__device__ __forceinline__ void delta_apply_t(float (&acc)[DCHUNK], const float (*tt)[DCHUNK + 4],
                                              const float (*x)[DTILE_ROW], const float* scale,
                                              unsigned col) {
    for (unsigned j = 0; j < DCHUNK; ++j) {
        const float v = scale[j] * x[j][col];
#pragma unroll
        for (unsigned i = 0; i < DCHUNK; i += 4) {
            const float4 t = *reinterpret_cast<const float4*>(&tt[j][i]);
            acc[i] = fmaf(t.x, v, acc[i]);
            acc[i + 1] = fmaf(t.y, v, acc[i + 1]);
            acc[i + 2] = fmaf(t.z, v, acc[i + 2]);
            acc[i + 3] = fmaf(t.w, v, acc[i + 3]);
        }
    }
}

// grid (n_v_heads, ceil(n / DCHUNK)), block DTHREADS; head_k_dim =
// head_v_dim = 128.
extern "C" __global__ void __launch_bounds__(DTHREADS) delta_chunk_prep(DeltaArgs a) {
    __shared__ __align__(16) float ks[DCHUNK][DTILE_ROW];
    __shared__ __align__(16) float xs[DCHUNK][DTILE_ROW];
    // A, then T transposed.
    __shared__ __align__(16) float am[DCHUNK][DCHUNK + 4];
    __shared__ float beta[DCHUNK], gamma[DCHUNK], kscale[DCHUNK];

    const unsigned vh = blockIdx.x, kh = vh % a.n_k_heads, c0 = blockIdx.y * DCHUNK;
    const unsigned rows = min(DCHUNK, a.n - c0), tid = threadIdx.x;
    const unsigned dk = a.head_k_dim, key_dim = a.n_k_heads * dk, nv = a.n_v_heads;
    const DeltaBatch db = delta_batch(a);
    const float* conv = db.conv + static_cast<size_t>(c0) * a.channels;
    const auto one = [](unsigned) { return 1.0f; };

    if (tid < WARP) {
        float lg = 0.0f, b = 0.0f;
        if (tid < rows) {
            const size_t at = static_cast<size_t>(c0 + tid) * nv + vh;
            lg = softplus(a.alpha[at] + a.dt_bias[vh]) * a.a[vh];
            b = sigmoid(a.beta[at]);
        }
#pragma unroll
        for (unsigned o = 1; o < WARP; o *= 2) {
            const float up = __shfl_up_sync(FULL_MASK, lg, o);
            if (tid >= o) lg += up;
        }
        gamma[tid] = lg;
        beta[tid] = b;
        kscale[tid] = b * expf(lg);
    }
    delta_tile(ks, conv + key_dim + kh * dk, a.channels, rows, one);
    delta_tile(xs, conv + kh * dk, a.channels, rows, one);
    __syncthreads();

    // A (strictly lower) and the chunk scores P (lower with diagonal):
    // thread row i = tid / 4, columns j = 4 jj + tid % 4.
    {
        const unsigned i = tid / 4;
        float kk[8] = {}, qk[8] = {};
        for (unsigned d = 0; d < 128; d += 4) {
            const float4 ki = *reinterpret_cast<const float4*>(&ks[i][d]);
            const float4 qi = *reinterpret_cast<const float4*>(&xs[i][d]);
#pragma unroll
            for (unsigned jj = 0; jj < 8; ++jj) {
                const float4 kj = *reinterpret_cast<const float4*>(&ks[4 * jj + tid % 4][d]);
                kk[jj] = fmaf(ki.x, kj.x, fmaf(ki.y, kj.y, fmaf(ki.z, kj.z, fmaf(ki.w, kj.w, kk[jj]))));
                qk[jj] = fmaf(qi.x, kj.x, fmaf(qi.y, kj.y, fmaf(qi.z, kj.z, fmaf(qi.w, kj.w, qk[jj]))));
            }
        }
#pragma unroll
        for (unsigned jj = 0; jj < 8; ++jj) {
            const unsigned j = 4 * jj + tid % 4;
            const float decay = j <= i ? expf(gamma[i] - gamma[j]) : 0.0f;
            am[i][j] = j < i ? beta[i] * decay * kk[jj] : 0.0f;
            if (i < rows) db.p[(static_cast<size_t>(vh) * a.n + c0 + i) * DCHUNK + j] = decay * qk[jj];
        }
    }
    __syncthreads();

    // T = (I + A)^-1 by forward substitution: lane j of the first warp
    // computes column j in registers, then stores it as row j of am.
    if (tid < WARP) {
        float t[DCHUNK];
#pragma unroll
        for (unsigned i = 0; i < DCHUNK; ++i) {
            float v = i == tid ? 1.0f : 0.0f;
#pragma unroll
            for (unsigned k = 0; k < i; ++k) v = fmaf(-am[i][k], t[k], v);
            t[i] = v;
        }
        __syncwarp();
#pragma unroll
        for (unsigned i = 0; i < DCHUNK; ++i) am[tid][i] = t[i];
    }
    __syncthreads();

    // W = T diag(b e^G) K and the corrected values T diag(b) V, written per
    // head and token; thread `col` owns that column of both.
    const unsigned col = tid;
    float acc[DCHUNK] = {};
    delta_apply_t(acc, am, ks, kscale, col);
    float* w = db.w + (static_cast<size_t>(vh) * a.n + c0) * dk;
#pragma unroll
    for (unsigned i = 0; i < DCHUNK; ++i)
        if (i < rows) w[static_cast<size_t>(i) * dk + col] = acc[i];
    __syncthreads();
    delta_tile(xs, conv + 2 * key_dim + vh * a.head_v_dim, a.channels, rows, one);
    __syncthreads();
#pragma unroll
    for (unsigned i = 0; i < DCHUNK; ++i) acc[i] = 0.0f;
    delta_apply_t(acc, am, xs, beta, col);
    float* u = db.u + (static_cast<size_t>(vh) * a.n + c0) * a.head_v_dim;
#pragma unroll
    for (unsigned i = 0; i < DCHUNK; ++i)
        if (i < rows) u[static_cast<size_t>(i) * a.head_v_dim + col] = acc[i];
    if (tid < rows) db.gamma[static_cast<size_t>(vh) * a.n + c0 + tid] = gamma[tid];
}
