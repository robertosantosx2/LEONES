#pragma once

#include "common.cuh"

// Routed experts read straight from an arena of cache slots in their file
// layout; each slot holds one expert's gate, up and down matrices.
//
// Every value is computed exactly as the host computes it (see
// kinetic-models' blocks/moe/kernels.rs): inputs are quantized per 256
// values, each block of a row gives an exact integer sum, and the blocks are
// added in order, each times the product of the two scales, less, in the
// K-quants with offsets, the exact integer sum of the offsets times the
// inputs, times the offset scale and the input scale, with every rounding
// spelled out. A row's value is then the same bits on the host and
// on the device, so where an expert runs never changes the output.

constexpr unsigned QK_IQ = 256;
// Most assignments of one expert a block multiplies at once.
constexpr unsigned MOE_GROUP = 8;
constexpr unsigned MOE_WARPS = 4;
constexpr unsigned MOE_THREADS = MOE_WARPS * WARP;

// Byte offsets of the codebooks in the table buffer, read through the
// cache: a few KiB that every warp looks up at random.
constexpr unsigned IQ2XXS_OFFSET = 0;
constexpr unsigned IQ2XS_OFFSET = 2048;
constexpr unsigned IQ3XXS_OFFSET = 6144;
constexpr unsigned IQ4NL_OFFSET = 7168;

// x quantized per 256 values: d = max|x| / 127, q = round(x / d) half away
// from zero. One warp per block, eight values per lane.
extern "C" __global__ void quantize_q8k(const float* x, int8_t* qs, float* ds, unsigned blocks) {
    const unsigned b = blockIdx.x * (blockDim.x / WARP) + threadIdx.x / WARP;
    if (b >= blocks) return;
    const unsigned lane = threadIdx.x % WARP;
    const float* v = x + static_cast<size_t>(b) * QK_IQ + 8 * lane;
    float amax = 0.0f;
#pragma unroll
    for (unsigned j = 0; j < 8; ++j) amax = fmaxf(amax, fabsf(v[j]));
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2)
        amax = fmaxf(amax, __shfl_xor_sync(FULL_MASK, amax, o));
    const float d = __fdiv_rn(amax, 127.0f);
    const float inv = d == 0.0f ? 0.0f : __fdiv_rn(1.0f, d);
    int8_t* q = qs + static_cast<size_t>(b) * QK_IQ + 8 * lane;
#pragma unroll
    for (unsigned j = 0; j < 8; ++j)
        q[j] = static_cast<int8_t>(fminf(fmaxf(roundf(__fmul_rn(v[j], inv)), -127.0f), 127.0f));
    if (lane == 0) ds[b] = d;
}

// Eight sign bits from a 7-bit index; the eighth keeps the count even.
__device__ __forceinline__ unsigned iq_signs(unsigned i) {
    return i | ((__popc(i) & 1u) << 7);
}

// Four magnitudes in `v` negated where the low four bits of `signs` say.
__device__ __forceinline__ int signed4(unsigned v, unsigned signs) {
    const unsigned m = ((signs & 1u) ? 0xffu : 0u) | ((signs & 2u) ? 0xff00u : 0u) |
                       ((signs & 4u) ? 0xff0000u : 0u) | ((signs & 8u) ? 0xff000000u : 0u);
    return static_cast<int>(__vsub4(v ^ m, m));
}

__device__ __forceinline__ float half_at(const uint8_t* p) {
    return __half2float(__ushort_as_half(static_cast<unsigned short>(p[0] | p[1] << 8)));
}

__device__ __forceinline__ unsigned u32_at(const uint8_t* p) {
    return p[0] | p[1] << 8 | p[2] << 16 | static_cast<unsigned>(p[3]) << 24;
}

// A lane's eight weights of a block as signed bytes, with the integer
// multiplier and offset of the 16 or 32 values they belong to.
struct Lane8 {
    int w[2];
    int mul;
    int min;
};

__device__ __forceinline__ unsigned nibbles(const uint8_t* p, unsigned shift) {
    return u32_at(p) >> shift & 0x0f0f0f0fu;
}

// Each lane takes values 8 * lane .. 8 * lane + 8 of a 256-value block; `D`
// is the block scale the host folds its power of two into.
struct Iq2Xxs {
    static constexpr unsigned BYTES = 66;
    static constexpr bool MINS = false;
    static __device__ __forceinline__ float min_scale(const uint8_t*) { return 0.0f; }
    static constexpr unsigned TABLE = IQ2XXS_OFFSET;
    static __device__ __forceinline__ float scale(const uint8_t* b) {
        return __fmul_rn(half_at(b), 0.125f);
    }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane,
                                                 const uint8_t* table) {
        const unsigned sub = lane / 4, l = lane % 4;
        const unsigned aux = u32_at(b + 6 + 8 * sub);
        const unsigned signs = iq_signs(aux >> (7 * l) & 127);
        const uint2 g = reinterpret_cast<const uint2*>(table)[b[2 + 8 * sub + l]];
        return {{signed4(g.x, signs), signed4(g.y, signs >> 4)}, static_cast<int>(2 * (aux >> 28) + 1), 0};
    }
};

struct Iq2Xs {
    static constexpr unsigned BYTES = 74;
    static constexpr bool MINS = false;
    static __device__ __forceinline__ float min_scale(const uint8_t*) { return 0.0f; }
    static constexpr unsigned TABLE = IQ2XS_OFFSET;
    static __device__ __forceinline__ float scale(const uint8_t* b) {
        return __fmul_rn(half_at(b), 0.125f);
    }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane,
                                                 const uint8_t* table) {
        const unsigned q = b[2 + 2 * lane] | b[3 + 2 * lane] << 8;
        const unsigned s = b[66 + lane / 4] >> (4 * (lane / 2 % 2)) & 0xf;
        const unsigned signs = iq_signs(q >> 9);
        const uint2 g = reinterpret_cast<const uint2*>(table)[q & 511];
        return {{signed4(g.x, signs), signed4(g.y, signs >> 4)}, static_cast<int>(2 * s + 1), 0};
    }
};

struct Iq3Xxs {
    static constexpr unsigned BYTES = 98;
    static constexpr bool MINS = false;
    static __device__ __forceinline__ float min_scale(const uint8_t*) { return 0.0f; }
    static constexpr unsigned TABLE = IQ3XXS_OFFSET;
    static __device__ __forceinline__ float scale(const uint8_t* b) {
        return __fmul_rn(half_at(b), 0.25f);
    }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane,
                                                 const uint8_t* table) {
        const unsigned sub = lane / 4, l = lane % 4;
        const unsigned aux = u32_at(b + 66 + 4 * sub);
        const unsigned signs = iq_signs(aux >> (7 * l) & 127);
        const unsigned* grid = reinterpret_cast<const unsigned*>(table);
        const unsigned lo = grid[b[2 + 8 * sub + 2 * l]], hi = grid[b[3 + 8 * sub + 2 * l]];
        return {{signed4(lo, signs), signed4(hi, signs >> 4)}, static_cast<int>(2 * (aux >> 28) + 1), 0};
    }
};

struct Iq4Xs {
    static constexpr unsigned BYTES = 136;
    static constexpr bool MINS = false;
    static __device__ __forceinline__ float min_scale(const uint8_t*) { return 0.0f; }
    static constexpr unsigned TABLE = IQ4NL_OFFSET;
    static __device__ __forceinline__ float scale(const uint8_t* b) { return half_at(b); }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane,
                                                 const uint8_t* table) {
        const unsigned sub = lane / 4, p = lane % 4 * 8;
        const unsigned lo = b[4 + sub / 2] >> (4 * (sub % 2)) & 0xf;
        const unsigned hi = (b[2] | b[3] << 8) >> (2 * sub) & 3;
        const uint8_t* codes = b + 8 + 16 * sub + p % 16;
        const unsigned shift = p < 16 ? 0 : 4;
        unsigned w[2];
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            w[h] = 0;
#pragma unroll
            for (unsigned j = 0; j < 4; ++j)
                w[h] |= static_cast<unsigned>(table[codes[4 * h + j] >> shift & 0xf]) << (8 * j);
        }
        return {{static_cast<int>(w[0]), static_cast<int>(w[1])},
                static_cast<int>(lo | hi << 4) - 32, 0};
    }
};

// The 6-bit scale and offset of 32-value group `j` of Q4_K and Q5_K.
__device__ __forceinline__ int2 moe_scale_min(const uint8_t* q, unsigned j) {
    if (j < 4) return make_int2(q[j] & 63, q[j + 4] & 63);
    return make_int2((q[j + 4] & 0xf) | (q[j - 4] >> 6) << 4, (q[j + 4] >> 4) | (q[j] >> 6) << 4);
}

// Each 32 bytes of qs hold 64 values, the low nibbles then the high.
struct Q4K {
    static constexpr unsigned BYTES = 144;
    static constexpr unsigned TABLE = 0;
    static constexpr bool MINS = true;
    static __device__ __forceinline__ float scale(const uint8_t* b) { return half_at(b); }
    static __device__ __forceinline__ float min_scale(const uint8_t* b) { return half_at(b + 2); }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane, const uint8_t*) {
        const unsigned n = lane / 8, high = lane % 8 / 4, l = lane % 4 * 8;
        const uint8_t* q = b + 16 + 32 * n + l;
        const int2 sm = moe_scale_min(b + 4, 2 * n + high);
        return {{static_cast<int>(nibbles(q, 4 * high)), static_cast<int>(nibbles(q + 4, 4 * high))},
                sm.x,
                sm.y};
    }
};

// Q4_K with a fifth bit per value from qh, two bits of each byte per 64.
struct Q5K {
    static constexpr unsigned BYTES = 176;
    static constexpr unsigned TABLE = 0;
    static constexpr bool MINS = true;
    static __device__ __forceinline__ float scale(const uint8_t* b) { return half_at(b); }
    static __device__ __forceinline__ float min_scale(const uint8_t* b) { return half_at(b + 2); }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane, const uint8_t*) {
        const unsigned n = lane / 8, high = lane % 8 / 4, l = lane % 4 * 8;
        const uint8_t* q = b + 48 + 32 * n + l;
        const uint8_t* qh = b + 16 + l;
        const unsigned bit = 2 * n + high;
        const int2 sm = moe_scale_min(b + 4, bit);
        const unsigned w0 = nibbles(q, 4 * high) | (u32_at(qh) >> bit & 0x01010101u) << 4;
        const unsigned w1 = nibbles(q + 4, 4 * high) | (u32_at(qh + 4) >> bit & 0x01010101u) << 4;
        return {{static_cast<int>(w0), static_cast<int>(w1)}, sm.x, sm.y};
    }
};

// Two halves of 128; in each, ql gives the low 4 bits and qh the top 2 of
// four runs of 32, and values 16 g .. 16 g + 16 have scale g.
struct Q6K {
    static constexpr unsigned BYTES = 210;
    static constexpr unsigned TABLE = 0;
    static constexpr bool MINS = false;
    static __device__ __forceinline__ float scale(const uint8_t* b) { return half_at(b + 208); }
    static __device__ __forceinline__ float min_scale(const uint8_t*) { return 0.0f; }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane, const uint8_t*) {
        const unsigned n = lane / 16, k = lane % 16 / 4, l = lane % 4 * 8;
        const uint8_t* ql = b + 64 * n + 32 * (k & 1) + l;
        const uint8_t* qh = b + 128 + 32 * n + l;
        int w[2];
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            const unsigned v =
                nibbles(ql + 4 * h, 4 * (k >> 1)) | (u32_at(qh + 4 * h) >> (2 * k) & 0x03030303u) << 4;
            w[h] = static_cast<int>(__vsub4(v, 0x20202020u));
        }
        return {{w[0], w[1]}, static_cast<int8_t>(b[192 + lane / 2]), 0};
    }
};

// Each 32 bytes of qs hold four 2-bit planes of 32 values; values
// 16 g .. 16 g + 16 have scale and offset g.
struct Q2K {
    static constexpr unsigned BYTES = 84;
    static constexpr unsigned TABLE = 0;
    static constexpr bool MINS = true;
    static __device__ __forceinline__ float scale(const uint8_t* b) { return half_at(b + 80); }
    static __device__ __forceinline__ float min_scale(const uint8_t* b) { return half_at(b + 82); }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane, const uint8_t*) {
        const unsigned n = lane / 16, p = lane % 16 / 4, l = lane % 4 * 8;
        const uint8_t* q = b + 16 + 32 * n + l;
        const unsigned s = b[lane / 2];
        return {{static_cast<int>(u32_at(q) >> (2 * p) & 0x03030303u),
                 static_cast<int>(u32_at(q + 4) >> (2 * p) & 0x03030303u)},
                static_cast<int>(s & 0xf),
                static_cast<int>(s >> 4)};
    }
};

// Q2_K's planes with a third bit from hmask, whose clear bits take 4 off.
struct Q3K {
    static constexpr unsigned BYTES = 110;
    static constexpr unsigned TABLE = 0;
    static constexpr bool MINS = false;
    static __device__ __forceinline__ float scale(const uint8_t* b) { return half_at(b + 108); }
    static __device__ __forceinline__ float min_scale(const uint8_t*) { return 0.0f; }
    static __device__ __forceinline__ Lane8 lane(const uint8_t* b, unsigned lane, const uint8_t*) {
        const unsigned n = lane / 16, p = lane % 16 / 4, l = lane % 4 * 8;
        const uint8_t* q = b + 32 + 32 * n + l;
        const uint8_t* hm = b + l;
        const unsigned bit = 4 * n + p;
        int w[2];
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            const unsigned v = (u32_at(q + 4 * h) >> (2 * p) & 0x03030303u) |
                               (u32_at(hm + 4 * h) >> bit & 0x01010101u) << 2;
            w[h] = static_cast<int>(__vsub4(v, 0x04040404u));
        }
        const unsigned g = lane / 2;
        const unsigned low = b[96 + g % 8] >> (4 * (g / 8)) & 0xf;
        const unsigned high = b[104 + g % 4] >> (2 * (g / 4)) & 3;
        return {{w[0], w[1]}, static_cast<int>(low | high << 4) - 32, 0};
    }
};

__device__ __forceinline__ int warp_isum(int v) {
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) v += __shfl_xor_sync(FULL_MASK, v, o);
    return v;
}

// The host's `silu`, operation by operation: a degree-6 polynomial for e^r
// after x = n ln 2 + r, and 2^n from the exponent bits.
__device__ __forceinline__ float exact_exp(float x) {
    if (x > 88.0f) return CUDART_INF_F;
    if (x < -87.0f) return 0.0f;
    const float n = roundf(__fmul_rn(x, 1.442695f));
    const float r = __fsub_rn(__fsub_rn(x, __fmul_rn(n, 0.6933594f)), __fmul_rn(n, -2.1219444e-4f));
    float p = 1.9875691e-4f;
    p = __fadd_rn(__fmul_rn(p, r), 1.3981999e-3f);
    p = __fadd_rn(__fmul_rn(p, r), 8.333452e-3f);
    p = __fadd_rn(__fmul_rn(p, r), 4.1665796e-2f);
    p = __fadd_rn(__fmul_rn(p, r), 0.16666666f);
    p = __fadd_rn(__fmul_rn(p, r), 0.5f);
    const float e = __fadd_rn(__fadd_rn(__fmul_rn(p, __fmul_rn(r, r)), r), 1.0f);
    return __fmul_rn(e, __int_as_float((static_cast<int>(n) + 127) << 23));
}

__device__ __forceinline__ float exact_silu(float x) {
    return __fdiv_rn(x, __fadd_rn(1.0f, exact_exp(-x)));
}

struct MoeParams {
    const uint8_t* arena;
    unsigned long long slot_bytes;
    // Per group: its slot, first assignment and number of assignments (at
    // most MOE_GROUP), consecutive.
    const uint4* groups;
    // Per assignment, the input row it reads; null when assignment `a`
    // reads row `a`.
    const unsigned* inputs;
    const int8_t* xq;
    const float* xd;
    float* y;
    const uint8_t* tables;
    // Where the first (gate or down) and second (up) matrix start in a slot.
    unsigned first;
    unsigned second;
    unsigned rows;
    unsigned cols;
};

// Each warp computes rows of every assignment in its group, reading each
// weight once for all of them. With `GATED`, y = silu(gate x) * up x,
// otherwise y = first x; y holds one row of `rows` values per assignment.
template <class F, bool GATED>
__device__ void moe_rows(const MoeParams& p) {
    extern __shared__ int8_t shared[];
    const uint4 g = p.groups[blockIdx.y];
    const unsigned count = g.z, blocks = p.cols / QK_IQ;
    // Groups past those a batch's routing filled are empty.
    if (count == 0) return;
    int8_t* xs = shared;
    float* ds = reinterpret_cast<float*>(xs + MOE_GROUP * p.cols);
    const uint8_t* table = p.tables + F::TABLE;
    for (unsigned t = 0; t < count; ++t) {
        const unsigned a = g.y + t;
        const size_t row = p.inputs ? p.inputs[a] : a;
        for (unsigned i = threadIdx.x; i < p.cols / 4; i += blockDim.x)
            reinterpret_cast<int*>(xs + t * p.cols)[i] =
                reinterpret_cast<const int*>(p.xq + row * p.cols)[i];
        for (unsigned i = threadIdx.x; i < blocks; i += blockDim.x)
            ds[t * blocks + i] = p.xd[row * blocks + i];
    }
    __syncthreads();

    const unsigned lane = threadIdx.x % WARP;
    const uint8_t* slot = p.arena + p.slot_bytes * g.x;
    const size_t row_bytes = static_cast<size_t>(blocks) * F::BYTES;
    const unsigned warps = gridDim.x * MOE_WARPS;
    for (unsigned r = blockIdx.x * MOE_WARPS + threadIdx.x / WARP; r < p.rows; r += warps) {
        float acc[2][MOE_GROUP] = {};
#pragma unroll
        for (unsigned m = 0; m < (GATED ? 2 : 1); ++m) {
            const uint8_t* w = slot + (m == 0 ? p.first : p.second) + r * row_bytes;
            for (unsigned b = 0; b < blocks; ++b) {
                const uint8_t* blk = w + b * F::BYTES;
                const Lane8 l = F::lane(blk, lane, table);
                const float wd = F::scale(blk);
                const float wmin = F::min_scale(blk);
#pragma unroll
                for (unsigned t = 0; t < MOE_GROUP; ++t) {
                    if (t >= count) break;
                    const int* x = reinterpret_cast<const int*>(xs + t * p.cols + b * QK_IQ + 8 * lane);
                    const float xd = ds[t * blocks + b];
                    const int sum = warp_isum(l.mul * __dp4a(l.w[1], x[1], __dp4a(l.w[0], x[0], 0)));
                    acc[m][t] = __fadd_rn(acc[m][t], __fmul_rn(__fmul_rn(wd, xd), static_cast<float>(sum)));
                    if (F::MINS && wmin != 0.0f) {
                        const int ones = 0x01010101;
                        const int offsets = warp_isum(l.min * __dp4a(ones, x[1], __dp4a(ones, x[0], 0)));
                        acc[m][t] = __fsub_rn(acc[m][t],
                                              __fmul_rn(__fmul_rn(wmin, xd), static_cast<float>(offsets)));
                    }
                }
            }
        }
        if (lane == 0) {
            for (unsigned t = 0; t < count; ++t) {
                const float v = GATED ? __fmul_rn(exact_silu(acc[0][t]), acc[1][t]) : acc[0][t];
                p.y[static_cast<size_t>(g.y + t) * p.rows + r] = v;
            }
        }
    }
}

#define MOE_KERNELS(name, F)                                                                 \
    extern "C" __global__ void __launch_bounds__(MOE_THREADS) moe_gate_up_##name(MoeParams p) { \
        moe_rows<F, true>(p);                                                                \
    }                                                                                        \
    extern "C" __global__ void __launch_bounds__(MOE_THREADS) moe_down_##name(MoeParams p) {    \
        moe_rows<F, false>(p);                                                               \
    }

MOE_KERNELS(iq2_xxs, Iq2Xxs)
MOE_KERNELS(iq2_xs, Iq2Xs)
MOE_KERNELS(iq3_xxs, Iq3Xxs)
MOE_KERNELS(iq4_xs, Iq4Xs)
MOE_KERNELS(q2_k, Q2K)
MOE_KERNELS(q3_k, Q3K)
MOE_KERNELS(q4_k, Q4K)
MOE_KERNELS(q5_k, Q5K)
MOE_KERNELS(q6_k, Q6K)

// Routing on the device, for layers whose experts all have a slot.

// Most experts a layer may have for `moe_route`: 32 per lane.
constexpr unsigned ROUTE_MAX_EXPERTS = 32 * WARP;

struct RouteParams {
    // Router logits, `stride` per token, the experts' first.
    const float* gates;
    // Per token and pick, the expert and its weight.
    unsigned* experts;
    float* weights;
    unsigned tokens;
    unsigned n_exp;
    unsigned k;
    unsigned stride;
    // Sigmoid probabilities instead of a softmax.
    unsigned sigmoid;
    // Added to each expert's probability to choose, not to weigh, or null.
    const float* bias;
};

// Per token, the softmax (or sigmoid) of the logits, then the `k` likeliest experts,
// largest first and the lowest index among equals, each weighted by its
// share of the `k` probabilities, the sum floored at the smallest normal
// f16 as on the host. One warp per token; every sum is taken in a fixed
// order, so a token's picks never depend on its batch.
extern "C" __global__ void moe_route(RouteParams p) {
    const unsigned t = blockIdx.x * (blockDim.x / WARP) + threadIdx.x / WARP;
    if (t >= p.tokens) return;
    const unsigned lane = threadIdx.x % WARP;
    const float* g = p.gates + static_cast<size_t>(t) * p.stride;
    float top = -CUDART_INF_F;
    for (unsigned e = lane; e < p.n_exp; e += WARP) top = fmaxf(top, g[e]);
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) top = fmaxf(top, __shfl_xor_sync(FULL_MASK, top, o));
    float sum = 0.0f;
    for (unsigned e = lane; e < p.n_exp; e += WARP) sum = __fadd_rn(sum, expf(__fsub_rn(g[e], top)));
#pragma unroll
    for (unsigned o = WARP / 2; o > 0; o /= 2) sum = __fadd_rn(sum, __shfl_xor_sync(FULL_MASK, sum, o));

    unsigned taken = 0;
    float picked = 0.0f;
    unsigned* experts = p.experts + static_cast<size_t>(t) * p.k;
    float* weights = p.weights + static_cast<size_t>(t) * p.k;
    for (unsigned j = 0; j < p.k; ++j) {
        float best = -CUDART_INF_F, best_prob = 0.0f;
        unsigned at = 0xffffffffu;
        for (unsigned i = 0, e = lane; e < p.n_exp; ++i, e += WARP) {
            const float prob = p.sigmoid ? __fdiv_rn(1.0f, __fadd_rn(1.0f, expf(-g[e])))
                                         : __fdiv_rn(expf(__fsub_rn(g[e], top)), sum);
            const float score = p.bias ? __fadd_rn(prob, p.bias[e]) : prob;
            if (!(taken >> i & 1u) && score > best) {
                best = score;
                best_prob = prob;
                at = e;
            }
        }
#pragma unroll
        for (unsigned o = WARP / 2; o > 0; o /= 2) {
            const float b = __shfl_xor_sync(FULL_MASK, best, o);
            const float bp = __shfl_xor_sync(FULL_MASK, best_prob, o);
            const unsigned a = __shfl_xor_sync(FULL_MASK, at, o);
            if (b > best || (b == best && a < at)) {
                best = b;
                best_prob = bp;
                at = a;
            }
        }
        if (at % WARP == lane) taken |= 1u << (at / WARP);
        if (lane == 0) {
            experts[j] = at;
            weights[j] = best_prob;
            picked = __fadd_rn(picked, best_prob);
        }
    }
    if (lane == 0) {
        const float total = fmaxf(picked, 6.1035156e-5f);
        for (unsigned j = 0; j < p.k; ++j) weights[j] = __fdiv_rn(weights[j], total);
    }
}

struct AssignParams {
    // Per token and pick, its expert.
    const unsigned* experts;
    // The cache slot of every expert of the layer.
    const unsigned* slots;
    // Out: groups of up to MOE_GROUP assignments, the rest of `max_groups`
    // empty; per assignment its input row; per pick its assignment.
    uint4* groups;
    unsigned* inputs;
    unsigned* rows;
    unsigned picks;
    unsigned k;
    unsigned n_exp;
    unsigned max_groups;
};

// Gives every pick an assignment, the picks of each expert together in
// pick order and in groups of up to MOE_GROUP, for `moe_rows`. One block;
// shared memory holds the picks and three words per expert.
extern "C" __global__ void moe_assign(AssignParams p) {
    extern __shared__ unsigned assign_shared[];
    unsigned* picked = assign_shared;
    unsigned* count = picked + p.picks;
    unsigned* first = count + p.n_exp;
    unsigned* group = first + p.n_exp;
    __shared__ unsigned total;
    for (unsigned s = threadIdx.x; s < p.picks; s += blockDim.x) picked[s] = p.experts[s];
    __syncthreads();
    for (unsigned e = threadIdx.x; e < p.n_exp; e += blockDim.x) {
        unsigned c = 0;
        for (unsigned s = 0; s < p.picks; ++s) c += picked[s] == e;
        count[e] = c;
    }
    __syncthreads();
    if (threadIdx.x == 0) {
        unsigned a = 0, n = 0;
        for (unsigned e = 0; e < p.n_exp; ++e) {
            first[e] = a;
            group[e] = n;
            a += count[e];
            n += (count[e] + MOE_GROUP - 1) / MOE_GROUP;
        }
        total = n;
    }
    __syncthreads();
    for (unsigned e = threadIdx.x; e < p.n_exp; e += blockDim.x) {
        unsigned j = 0;
        for (unsigned s = 0; s < p.picks && j < count[e]; ++s) {
            if (picked[s] != e) continue;
            const unsigned a = first[e] + j;
            p.inputs[a] = s / p.k;
            p.rows[s] = a;
            if (j % MOE_GROUP == 0)
                p.groups[group[e] + j / MOE_GROUP] = make_uint4(p.slots[e], a, min(MOE_GROUP, count[e] - j), 0);
            ++j;
        }
    }
    for (unsigned i = total + threadIdx.x; i < p.max_groups; i += blockDim.x) p.groups[i] = make_uint4(0, 0, 0, 0);
}

struct CombineParams {
    // Expert outputs, `d` values per row.
    const float* experts;
    // Per token and pick: the row of `experts` holding its output, and its
    // weight.
    const unsigned* rows;
    const float* weights;
    unsigned picks;
    // Whether `out` holds the shared expert's output; otherwise it starts
    // from zero.
    unsigned shared;
    // The shared expert's output, scaled in place per token by the sigmoid
    // of gates[t * gate_stride] when `gates` is set.
    float* out;
    const float* gates;
    unsigned gate_stride;
    unsigned d;
};

// out = shared * sigmoid(gate) + the weighted outputs of the token's picks,
// added in pick order.
extern "C" __global__ void moe_combine(CombineParams p) {
    const unsigned t = blockIdx.y, i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= p.d) return;
    const size_t at = static_cast<size_t>(t) * p.d + i;
    float v = p.shared ? p.out[at] : 0.0f;
    if (p.gates) v = __fmul_rn(v, sigmoid(p.gates[static_cast<size_t>(t) * p.gate_stride]));
    for (unsigned k = 0; k < p.picks; ++k) {
        const unsigned s = t * p.picks + k;
        v = __fadd_rn(v, __fmul_rn(p.weights[s], p.experts[static_cast<size_t>(p.rows[s]) * p.d + i]));
    }
    p.out[at] = v;
}
