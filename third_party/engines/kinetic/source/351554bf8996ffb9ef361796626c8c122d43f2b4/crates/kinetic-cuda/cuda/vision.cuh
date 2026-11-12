#pragma once

#include "mma.cuh"

// Vision transformer pieces: rows of f32 activations, bidirectional
// attention over a whole image.

#define VIT_THREADS 256
#define VIT_WARPS 8
#define VIT_TILE 32
#define VIT_MAX_HEAD 128
#define VIT_QUERIES 8  // two float4 per dimension
#define VIT_QUADS (VIT_QUERIES / 4)

__device__ __forceinline__ float vit_warp_sum(float v) {
    for (int o = 16; o; o >>= 1) v += __shfl_xor_sync(0xffffffffu, v, o);
    return v;
}

__device__ __forceinline__ float vit_warp_max(float v) {
    for (int o = 16; o; o >>= 1) v = fmaxf(v, __shfl_xor_sync(0xffffffffu, v, o));
    return v;
}

__device__ float vit_block_sum(float v, float* shared) {
    v = vit_warp_sum(v);
    if (threadIdx.x % 32 == 0) shared[threadIdx.x / 32] = v;
    __syncthreads();
    float total = 0.0f;
    for (int w = 0; w < VIT_THREADS / 32; ++w) total += shared[w];
    __syncthreads();
    return total;
}

// One block per row: y = (x - mean) / sqrt(var + eps) * w + b.
extern "C" __global__ void __launch_bounds__(VIT_THREADS)
    vit_layer_norm(const float* x, const float* w, const float* b, float* y, unsigned width, float eps) {
    __shared__ float shared[VIT_THREADS / 32];
    const float* xr = x + static_cast<size_t>(blockIdx.x) * width;
    float* yr = y + static_cast<size_t>(blockIdx.x) * width;
    float s = 0.0f;
    for (unsigned i = threadIdx.x; i < width; i += VIT_THREADS) s += xr[i];
    const float mean = vit_block_sum(s, shared) / width;
    float v = 0.0f;
    for (unsigned i = threadIdx.x; i < width; i += VIT_THREADS) v += (xr[i] - mean) * (xr[i] - mean);
    const float scale = rsqrtf(vit_block_sum(v, shared) / width + eps);
    for (unsigned i = threadIdx.x; i < width; i += VIT_THREADS) yr[i] = (xr[i] - mean) * scale * w[i] + b[i];
}

// y = x + b over n values in rows of `width`, through tanh GELU if `gelu`.
extern "C" __global__ void vit_bias(const float* x, const float* b, float* y, unsigned n, unsigned width, unsigned gelu) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    float v = x[i] + b[i % width];
    if (gelu) v = 0.5f * v * (1.0f + tanhf(0.7978846f * (v + 0.044715f * v * v * v)));
    y[i] = v;
}

// x += y + b over n values in rows of `width`, either addend left out when null.
extern "C" __global__ void vit_residual(float* x, const float* y, const float* b, unsigned n, unsigned width) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) x[i] += (y ? y[i] : 0.0f) + (b ? b[i % width] : 0.0f);
}

// Rotates the query and key heads of rows of [q | k | v] by the two
// positions per row in `pos`. Without `halves`, pair i of the first half of
// a head pairs with i + head_dim / 2 and turns by the first position (first
// quarter of pairs) or the second (second quarter). With `halves`, each half
// of a head turns on its own, the first by the first position, value i of
// the half paired with i + head_dim / 4.
extern "C" __global__ void vit_rope_2d(float* qkv, const unsigned* pos, unsigned n, unsigned n_head,
                                       unsigned head_dim, float base, unsigned halves) {
    const unsigned half = head_dim / 2, quarter = head_dim / 4;
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n * 2 * n_head * half) return;
    const unsigned pair = i % half, head = i / half % (2 * n_head), t = i / half / (2 * n_head);
    const unsigned part = pair < quarter ? 0 : 1, j = pair % quarter;
    const float p = static_cast<float>(pos[2 * t + part]);
    float s, c;
    sincosf(p * powf(base, -static_cast<float>(j) / quarter), &s, &c);
    float* h = qkv + static_cast<size_t>(t) * 3 * n_head * head_dim + head * head_dim;
    const unsigned at = halves ? part * half + j : pair, step = halves ? quarter : half;
    const float a = h[at], bb = h[at + step];
    h[at] = a * c - bb * s;
    h[at + step] = a * s + bb * c;
}

// One block per row of `width`: x = x / rms(x) * w in place, where row r
// takes weights (r / every) % sets of the `sets` rows of `w`.
extern "C" __global__ void __launch_bounds__(VIT_THREADS)
    vit_rms_norm(float* x, const float* w, unsigned width, unsigned every, unsigned sets, float eps) {
    __shared__ float shared[VIT_THREADS / 32];
    float* xr = x + static_cast<size_t>(blockIdx.x) * width;
    const float* wr = w + blockIdx.x / every % sets * width;
    float s = 0.0f;
    for (unsigned i = threadIdx.x; i < width; i += VIT_THREADS) s += xr[i] * xr[i];
    const float scale = rsqrtf(vit_block_sum(s, shared) / width + eps);
    for (unsigned i = threadIdx.x; i < width; i += VIT_THREADS) xr[i] *= scale * wr[i];
}

// y = clamp(x) over n values in rows of `width`, split into `sections`
// equal runs of columns that each take a (min, max) pair of `bounds`.
extern "C" __global__ void vit_clamp(const float* x, float* y, unsigned n, unsigned width, const float* bounds,
                                     unsigned sections) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const unsigned s = i % width / (width / sections);
    y[i] = fminf(fmaxf(x[i], bounds[2 * s]), bounds[2 * s + 1]);
}

// g = gelu(g) * u over n values, GELU in its tanh approximation.
extern "C" __global__ void vit_geglu(float* g, const float* u, unsigned n) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const float v = g[i];
    g[i] = 0.5f * v * (1.0f + tanhf(0.7978846f * (v + 0.044715f * v * v * v))) * u[i];
}

// Bidirectional attention over rows of [q | k | v]: VIT_QUERIES queries per
// warp, VIT_WARPS warps of one head per block sharing tiles of VIT_TILE
// keys, one key per lane. Each key read from shared memory serves all of a
// warp's queries. Writes n_head * head_dim values per row to `out`.
extern "C" __global__ void __launch_bounds__(VIT_THREADS)
    vit_attention(const float* qkv, float* out, unsigned n, unsigned n_head, unsigned head_dim, float scale) {
    extern __shared__ float sm[];
    const unsigned stride = head_dim + 1;  // padded so lanes reading their own key hit distinct banks
    float* ks = sm;
    float* vs = ks + VIT_TILE * stride;
    float* qs = vs + VIT_TILE * head_dim;
    float* ps = qs + VIT_WARPS * VIT_QUERIES * head_dim;
    const unsigned warp = threadIdx.x / 32, lane = threadIdx.x % 32, head = blockIdx.y;
    const unsigned t0 = (blockIdx.x * VIT_WARPS + warp) * VIT_QUERIES;
    const unsigned width = n_head * head_dim, row = 3 * width;
    // [dim][query], so float4s hold a dimension of every query
    float4* q = reinterpret_cast<float4*>(qs + warp * VIT_QUERIES * head_dim);
    float4* p = reinterpret_cast<float4*>(ps + warp * VIT_TILE * VIT_QUERIES);
    for (unsigned i = lane; i < VIT_QUERIES * head_dim; i += 32) {
        const unsigned d = i / VIT_QUERIES, t = t0 + i % VIT_QUERIES;
        reinterpret_cast<float*>(q)[i] = t < n ? qkv[static_cast<size_t>(t) * row + head * head_dim + d] * scale : 0.0f;
    }
    float m[VIT_QUERIES], l[VIT_QUERIES], o[VIT_QUERIES][VIT_MAX_HEAD / 32];
#pragma unroll
    for (unsigned j = 0; j < VIT_QUERIES; ++j) {
        m[j] = -INFINITY;
        l[j] = 0.0f;
#pragma unroll
        for (unsigned r = 0; r < VIT_MAX_HEAD / 32; ++r) o[j][r] = 0.0f;
    }
    for (unsigned k0 = 0; k0 < n; k0 += VIT_TILE) {
        __syncthreads();
        for (unsigned i = threadIdx.x; i < VIT_TILE * head_dim; i += VIT_THREADS) {
            const unsigned j = i / head_dim, d = i % head_dim, key = k0 + j;
            const size_t at = static_cast<size_t>(key) * row + head * head_dim + d;
            ks[j * stride + d] = key < n ? qkv[at + width] : 0.0f;
            vs[j * head_dim + d] = key < n ? qkv[at + 2 * width] : 0.0f;
        }
        __syncthreads();
        const bool live = k0 + lane < n;
        float e[VIT_QUERIES] = {}, c[VIT_QUERIES];
        for (unsigned d = 0; d < head_dim; ++d) {
            const float k = ks[lane * stride + d];
#pragma unroll
            for (unsigned g = 0; g < VIT_QUADS; ++g) {
                const float4 qd = q[d * VIT_QUADS + g];
                e[4 * g] += qd.x * k;
                e[4 * g + 1] += qd.y * k;
                e[4 * g + 2] += qd.z * k;
                e[4 * g + 3] += qd.w * k;
            }
        }
#pragma unroll
        for (unsigned j = 0; j < VIT_QUERIES; ++j) {
            const float sj = live ? e[j] : -INFINITY;
            const float m_new = fmaxf(m[j], vit_warp_max(sj));
            e[j] = live ? expf(sj - m_new) : 0.0f;
            c[j] = expf(m[j] - m_new);
            l[j] = l[j] * c[j] + vit_warp_sum(e[j]);
            m[j] = m_new;
        }
#pragma unroll
        for (unsigned g = 0; g < VIT_QUADS; ++g)
            p[lane * VIT_QUADS + g] = make_float4(e[4 * g], e[4 * g + 1], e[4 * g + 2], e[4 * g + 3]);
        __syncwarp();
#pragma unroll
        for (unsigned r = 0; r < VIT_MAX_HEAD / 32; ++r) {
            const unsigned d = lane + 32 * r;
            if (d >= head_dim) break;
            float acc[VIT_QUERIES];
#pragma unroll
            for (unsigned j = 0; j < VIT_QUERIES; ++j) acc[j] = o[j][r] * c[j];
            for (unsigned key = 0; key < VIT_TILE; ++key) {
                const float v = vs[key * head_dim + d];
#pragma unroll
                for (unsigned g = 0; g < VIT_QUADS; ++g) {
                    const float4 pk = p[key * VIT_QUADS + g];
                    acc[4 * g] += pk.x * v;
                    acc[4 * g + 1] += pk.y * v;
                    acc[4 * g + 2] += pk.z * v;
                    acc[4 * g + 3] += pk.w * v;
                }
            }
#pragma unroll
            for (unsigned j = 0; j < VIT_QUERIES; ++j) o[j][r] = acc[j];
        }
        __syncwarp();
    }
#pragma unroll
    for (unsigned j = 0; j < VIT_QUERIES; ++j) {
        const unsigned t = t0 + j;
        if (t >= n) break;
#pragma unroll
        for (unsigned r = 0; r < VIT_MAX_HEAD / 32; ++r) {
            const unsigned d = lane + 32 * r;
            if (d < head_dim) out[static_cast<size_t>(t) * width + head * head_dim + d] = o[j][r] / l[j];
        }
    }
}

#define VIT_MM_INPUTS 128
#define VIT_MM_ROWS 128
#define VIT_MM_STEP 32
#define VIT_MM_PAD 40  // halves a shared row: fragment reads of a warp hit distinct banks

__device__ __forceinline__ void vit_mm_fetch(const float* x, const __half* w, unsigned n, unsigned rows, unsigned k,
                                             unsigned m0, unsigned n0, unsigned k0, float4 (&xr)[4],
                                             uint4 (&wr)[2]) {
#pragma unroll
    for (unsigned i = 0; i < 4; ++i) {
        const unsigned at = threadIdx.x + VIT_THREADS * i, r = at / 8, c = at % 8 * 4;
        xr[i] = m0 + r < n ? *reinterpret_cast<const float4*>(x + static_cast<size_t>(m0 + r) * k + k0 + c)
                           : make_float4(0.0f, 0.0f, 0.0f, 0.0f);
    }
#pragma unroll
    for (unsigned i = 0; i < 2; ++i) {
        const unsigned at = threadIdx.x + VIT_THREADS * i, r = at / 4, c = at % 4 * 8;
        wr[i] = n0 + r < rows ? __ldg(reinterpret_cast<const uint4*>(w + static_cast<size_t>(n0 + r) * k + k0 + c))
                              : make_uint4(0, 0, 0, 0);
    }
}

// y = x w^T on the tensor cores, f16 products summed in f32: x holds n
// inputs of k f32 values, each split into an f16 and the f16 of what is
// left, which keeps the inputs to ~22 bits; w `rows` f16 rows of k, k a
// multiple of VIT_MM_STEP and rows even. Eight warps share a block of 128
// inputs times 128 rows, each warp 32 inputs times 64 rows; the next step
// of k is fetched into registers while the current one multiplies.
extern "C" __global__ void __launch_bounds__(VIT_THREADS)
    vit_matmul(const float* x, const __half* w, float* y, unsigned n, unsigned rows, unsigned k) {
    __shared__ __align__(16) __half xs[VIT_MM_INPUTS * VIT_MM_PAD];
    __shared__ __align__(16) __half xl[VIT_MM_INPUTS * VIT_MM_PAD];
    __shared__ __align__(16) __half ws[VIT_MM_ROWS * VIT_MM_PAD];
    const unsigned warp = threadIdx.x / 32, lane = threadIdx.x % 32, g = lane / 4, t = lane % 4;
    const unsigned m0 = blockIdx.x * VIT_MM_INPUTS, n0 = blockIdx.y * VIT_MM_ROWS;
    const unsigned wm = warp % 4 * 32, wn = warp / 4 * 64;
    float4 xr[4];
    uint4 wr[2];
    float acc[2][8][4] = {};
    vit_mm_fetch(x, w, n, rows, k, m0, n0, 0, xr, wr);
    for (unsigned k0 = 0; k0 < k; k0 += VIT_MM_STEP) {
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            const unsigned at = threadIdx.x + VIT_THREADS * i, r = at / 8, c = at % 8 * 4;
            uint2 hi, lo;
            split_pair(xr[i].x, xr[i].y, hi.x, lo.x);
            split_pair(xr[i].z, xr[i].w, hi.y, lo.y);
            *reinterpret_cast<uint2*>(xs + r * VIT_MM_PAD + c) = hi;
            *reinterpret_cast<uint2*>(xl + r * VIT_MM_PAD + c) = lo;
        }
#pragma unroll
        for (unsigned i = 0; i < 2; ++i) {
            const unsigned at = threadIdx.x + VIT_THREADS * i, r = at / 4, c = at % 4 * 8;
            *reinterpret_cast<uint4*>(ws + r * VIT_MM_PAD + c) = wr[i];
        }
        __syncthreads();
        if (k0 + VIT_MM_STEP < k) vit_mm_fetch(x, w, n, rows, k, m0, n0, k0 + VIT_MM_STEP, xr, wr);
#pragma unroll
        for (unsigned kk = 0; kk < VIT_MM_STEP; kk += 16) {
            unsigned a[2][2][4], b[8][2];
#pragma unroll
            for (unsigned part = 0; part < 2; ++part)
#pragma unroll
                for (unsigned mi = 0; mi < 2; ++mi) {
                    const __half* p = (part ? xl : xs) + (wm + 16 * mi + g) * VIT_MM_PAD + kk + 2 * t;
                    a[part][mi][0] = *reinterpret_cast<const unsigned*>(p);
                    a[part][mi][1] = *reinterpret_cast<const unsigned*>(p + 8 * VIT_MM_PAD);
                    a[part][mi][2] = *reinterpret_cast<const unsigned*>(p + 8);
                    a[part][mi][3] = *reinterpret_cast<const unsigned*>(p + 8 * VIT_MM_PAD + 8);
                }
#pragma unroll
            for (unsigned ni = 0; ni < 8; ++ni) {
                const __half* p = ws + (wn + 8 * ni + g) * VIT_MM_PAD + kk + 2 * t;
                b[ni][0] = *reinterpret_cast<const unsigned*>(p);
                b[ni][1] = *reinterpret_cast<const unsigned*>(p + 8);
            }
#pragma unroll
            for (unsigned part = 0; part < 2; ++part)
#pragma unroll
                for (unsigned mi = 0; mi < 2; ++mi)
#pragma unroll
                    for (unsigned ni = 0; ni < 8; ++ni) {
                        const unsigned(&am)[4] = a[part][mi];
                        mma_f16(acc[mi][ni], am[0], am[1], am[2], am[3], b[ni][0], b[ni][1]);
                    }
        }
        __syncthreads();
    }
#pragma unroll
    for (unsigned mi = 0; mi < 2; ++mi)
#pragma unroll
        for (unsigned ni = 0; ni < 8; ++ni) {
            const unsigned m = m0 + wm + 16 * mi + g, col = n0 + wn + 8 * ni + 2 * t;
            if (col >= rows) continue;
            if (m < n)
                *reinterpret_cast<float2*>(y + static_cast<size_t>(m) * rows + col) =
                    make_float2(acc[mi][ni][0], acc[mi][ni][1]);
            if (m + 8 < n)
                *reinterpret_cast<float2*>(y + static_cast<size_t>(m + 8) * rows + col) =
                    make_float2(acc[mi][ni][2], acc[mi][ni][3]);
        }
}

#define VIT_FA_WARPS 4
#define VIT_FA_KEYS 64
#define VIT_FA_HEAD 64
#define VIT_FA_PAD 72  // halves a shared row: fragment reads and ldmatrix rows hit distinct banks

// vit_attention for heads of 64 on the tensor cores: f16 queries, keys,
// values and weights, f32 sums. Each warp holds 16 queries and their
// running softmax in registers, scores in base 2 (log2 e is folded into
// `scale`); the block's four warps share tiles of 64 keys and values.
extern "C" __global__ void __launch_bounds__(VIT_FA_WARPS * 32)
    vit_attention_mma(const float* qkv, float* out, unsigned n, unsigned n_head, float scale) {
    __shared__ __align__(16) __half ks[VIT_FA_KEYS * VIT_FA_PAD];
    __shared__ __align__(16) __half vs[VIT_FA_KEYS * VIT_FA_PAD];
    const unsigned warp = threadIdx.x / 32, lane = threadIdx.x % 32, g = lane / 4, t = lane % 4;
    const unsigned head = blockIdx.y, width = n_head * VIT_FA_HEAD, row = 3 * width;
    const unsigned q0 = (blockIdx.x * VIT_FA_WARPS + warp) * 16;
    unsigned qa[4][4];
#pragma unroll
    for (unsigned kc = 0; kc < 4; ++kc)
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            const unsigned q = q0 + g + i % 2 * 8, c = 16 * kc + 2 * t + i / 2 * 8;
            float2 v = make_float2(0.0f, 0.0f);
            if (q < n) v = *reinterpret_cast<const float2*>(qkv + static_cast<size_t>(q) * row + head * VIT_FA_HEAD + c);
            qa[kc][i] = pack_half2(v.x * scale, v.y * scale);
        }
    float o[8][4] = {}, m[2] = {-INFINITY, -INFINITY}, l[2] = {0.0f, 0.0f};
    for (unsigned k0 = 0; k0 < n; k0 += VIT_FA_KEYS) {
        __syncthreads();
#pragma unroll
        for (unsigned i = 0; i < 8; ++i) {
            const unsigned at = threadIdx.x + VIT_FA_WARPS * 32 * i, r = at / 16, c = at % 16 * 4, key = k0 + r;
            float4 kv = make_float4(0.0f, 0.0f, 0.0f, 0.0f), vv = kv;
            if (key < n) {
                const float* src = qkv + static_cast<size_t>(key) * row + width + head * VIT_FA_HEAD + c;
                kv = *reinterpret_cast<const float4*>(src);
                vv = *reinterpret_cast<const float4*>(src + width);
            }
            *reinterpret_cast<uint2*>(ks + r * VIT_FA_PAD + c) =
                make_uint2(pack_half2(kv.x, kv.y), pack_half2(kv.z, kv.w));
            *reinterpret_cast<uint2*>(vs + r * VIT_FA_PAD + c) =
                make_uint2(pack_half2(vv.x, vv.y), pack_half2(vv.z, vv.w));
        }
        __syncthreads();
        float s[8][4] = {};
#pragma unroll
        for (unsigned j = 0; j < 8; ++j)
#pragma unroll
            for (unsigned kc = 0; kc < 4; ++kc) {
                const __half* p = ks + (8 * j + g) * VIT_FA_PAD + 16 * kc + 2 * t;
                mma_f16(s[j], qa[kc][0], qa[kc][1], qa[kc][2], qa[kc][3], *reinterpret_cast<const unsigned*>(p),
                        *reinterpret_cast<const unsigned*>(p + 8));
            }
        if (k0 + VIT_FA_KEYS > n)
#pragma unroll
            for (unsigned j = 0; j < 8; ++j)
#pragma unroll
                for (unsigned i = 0; i < 4; ++i)
                    if (k0 + 8 * j + 2 * t + i % 2 >= n) s[j][i] = -INFINITY;
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            float mx = m[h];
#pragma unroll
            for (unsigned j = 0; j < 8; ++j) mx = fmaxf(mx, fmaxf(s[j][2 * h], s[j][2 * h + 1]));
            mx = fmaxf(mx, __shfl_xor_sync(0xffffffffu, mx, 1));
            mx = fmaxf(mx, __shfl_xor_sync(0xffffffffu, mx, 2));
            const float c = exp2f(m[h] - mx);
            l[h] *= c;
#pragma unroll
            for (unsigned d = 0; d < 8; ++d) {
                o[d][2 * h] *= c;
                o[d][2 * h + 1] *= c;
            }
            m[h] = mx;
        }
#pragma unroll
        for (unsigned j = 0; j < 8; ++j)
#pragma unroll
            for (unsigned i = 0; i < 4; ++i) {
                s[j][i] = exp2f(s[j][i] - m[i / 2]);
                l[i / 2] += s[j][i];
            }
#pragma unroll
        for (unsigned kc = 0; kc < 4; ++kc) {
            const float(&lo)[4] = s[2 * kc];
            const float(&hi)[4] = s[2 * kc + 1];
            const unsigned a0 = pack_half2(lo[0], lo[1]), a1 = pack_half2(lo[2], lo[3]);
            const unsigned a2 = pack_half2(hi[0], hi[1]), a3 = pack_half2(hi[2], hi[3]);
#pragma unroll
            for (unsigned d = 0; d < 8; d += 2) {
                unsigned b[4];
                ldsm_x4_trans(b, vs + (16 * kc + lane % 16) * VIT_FA_PAD + 8 * d + lane / 16 * 8);
                mma_f16(o[d], a0, a1, a2, a3, b[0], b[1]);
                mma_f16(o[d + 1], a0, a1, a2, a3, b[2], b[3]);
            }
        }
    }
#pragma unroll
    for (unsigned h = 0; h < 2; ++h) {
        l[h] += __shfl_xor_sync(0xffffffffu, l[h], 1);
        l[h] += __shfl_xor_sync(0xffffffffu, l[h], 2);
        const unsigned q = q0 + g + 8 * h;
        if (q >= n) continue;
#pragma unroll
        for (unsigned d = 0; d < 8; ++d)
            *reinterpret_cast<float2*>(out + static_cast<size_t>(q) * width + head * VIT_FA_HEAD + 8 * d + 2 * t) =
                make_float2(o[d][2 * h] / l[h], o[d][2 * h + 1] / l[h]);
    }
}
