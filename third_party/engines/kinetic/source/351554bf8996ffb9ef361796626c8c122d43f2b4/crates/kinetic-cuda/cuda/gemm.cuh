#pragma once

#include "kquant.cuh"
#include "mma.cuh"
#include "quantize.cuh"

// Quantized matrix products for batches larger than a GEMV's: Y = W X for n
// inputs, in tiles of 64 rows and 32 or 64 inputs, two blocks to a
// multiprocessor, or of 128 rows and 128 inputs, one block to each, on int8
// tensor cores. Unlike the GEMV kernels the sums are not ordered to match
// any other kernel: a product may differ from the GEMV's in the last bits.
// Every tile adds each output's terms in the same order, so the tile a batch
// size picks does not change the bits.
//
// The k axis is walked in stages of GEMM_K, through two buffers of shared
// memory. While the warps multiply one stage, the block decodes the next
// stage's weights once into int8, with a float scale per sub-block of 32
// (per run of 16 for Q6_K) and, for Q4_K and Q5_K, a min, copies in its
// int8 inputs and reads the raw weights of the stage after into registers.
// Each warp multiplies a fixed patch of the tile, reading its fragments with
// ldmatrix. Each exact int32 product of a sub-block is scaled by the weights
// and then the inputs and added in f32.

constexpr unsigned GEMM_K = 128;
constexpr unsigned GEMM_SUBS = GEMM_K / 32;
// Threads that decode each row of weights, a quarter of its stage each.
constexpr unsigned GEMM_PARTS = 4;
// Bytes per row of an int8 tile: the padding puts the eight rows of an
// ldmatrix read in distinct banks.
constexpr unsigned GEMM_ROW = GEMM_K + 16;

// A tile of R rows and C inputs, of which a multiprocessor runs B blocks at
// once: each warp takes M m tiles of 16 rows and NT n tiles of 8 inputs.
// Short prompts take narrow tiles, which keep every warp multiplying, in
// small blocks, so that one block's loads overlap another's products.
template <unsigned R, unsigned C, unsigned M, unsigned B>
struct GemmTile {
    static constexpr unsigned ROWS = R, COLS = C, MT = M, NT = C / (16 * M), BLOCKS = B;
    static constexpr unsigned THREADS = GEMM_PARTS * ROWS;
    static constexpr unsigned WARP_ROWS = ROWS / (16 * MT);
    static constexpr unsigned SCALE_THREADS = COLS * GEMM_SUBS / 2;
    static_assert(WARP_ROWS * (COLS / (8 * NT)) * WARP == THREADS, "a patch per warp");
    static_assert(NT % 2 == 0, "n tiles go in pairs");
    static_assert(SCALE_THREADS % WARP == 0 && SCALE_THREADS <= THREADS,
                  "whole warps, one float4 per thread");
};

// Products start from these bits, the float B = 1.5 * 2^23, so that the
// int32 result read as a float is B + q, exactly while the product q stays
// within 2^22. A weight scale has at most 19 significant bits (an f16 times
// a small integer), so scale * B is exact and one fused multiply-add turns
// the biased result into scale * q with a single rounding.
constexpr int GEMM_BIAS_BITS = 0x4B400000;
constexpr float GEMM_BIAS = 12582912.0f;

// One stage in shared memory. The scale tables are laid out so that a lane
// reads all it needs of a sub-block in one float4. `scale[s][p]` is, for rows
// g and g + 8 of the 16 rows of pair p / 8 (g = p % 8), {a_g, a_g+8, b_g,
// b_g+8}: a the sub-block's scale and b its negated min (Q4_K, Q5_K), or a
// and b the scales of its two runs of 16 (Q6_K). `xds[s][c]` is {d, d', s,
// s'} of inputs 2c and 2c + 1: their scales and block sums.
template <class T>
struct __align__(16) GemmStage {
    int8_t x[T::COLS][GEMM_ROW];
    float4 xds[GEMM_SUBS][T::COLS / 2];
    int8_t w[T::ROWS][GEMM_ROW];
    float4 scale[GEMM_SUBS][T::ROWS / 2];
};

// Stores float `slot` (a or b) of row `row` of sub-block `s`.
template <class S>
__device__ __forceinline__ void gemm_put_scale(S& st, unsigned s, unsigned slot, unsigned row,
                                               float v) {
    float* f = &st.scale[s][row / 16 * 8 + row % 8].x;
    f[2 * slot + row / 8 % 2] = v;
}

__device__ __forceinline__ uint4 ld_raw(const uint8_t* p) {
    return __ldg(reinterpret_cast<const uint4*>(p));
}

__device__ __forceinline__ void st_words(int8_t* p, const unsigned (&v)[4]) {
    *reinterpret_cast<uint4*>(p) = make_uint4(v[0], v[1], v[2], v[3]);
}

__device__ __forceinline__ void words(unsigned (&v)[4], uint4 r) {
    v[0] = r.x;
    v[1] = r.y;
    v[2] = r.z;
    v[3] = r.w;
}

// The decoders. Thread (row, u) of a block reads, a stage before it is
// needed, the raw bytes of part u of its row's stage into `Raw`, and later
// writes them to the stage as int8 elements in order, with their scales.
// `blk` is the row's first block; `total` the matrix's block count, which
// planar layouts need to find their fields.

// Q4_K and Q5_K: a stage is half `s % 2` of block `s / 2`, sub-blocks
// 4 half .. 4 half + 3. Thread u takes the qs bytes 32c + l .. l + 15
// (c = u / 2, l = 16 (u % 2)), whose low and high nibbles are elements
// l .. l + 15 of sub-blocks 2c and 2c + 1, and the scale and min of
// sub-block u.
template <bool Q5>
struct GemmK4 {
    static constexpr unsigned BLOCK = 256, RUNS = 1;
    static constexpr bool MINS = true;
    static constexpr unsigned BYTES = Q5 ? 176 : 144;
    static constexpr unsigned QS = Q5 ? 48 : 16;

    struct Raw {
        Words head;
        uint4 qs;
        uint4 qh;
    };

    __device__ static void load(Raw& r, const uint8_t* w, size_t, size_t blk, unsigned s,
                                unsigned u) {
        const uint8_t* p = w + (blk + s / 2) * BYTES;
        r.head = load_cached(p);
        r.qs = ld_raw(p + QS + 64 * (s % 2) + 16 * u);
        if (Q5) r.qh = ld_raw(p + 16 + 16 * (u % 2));
    }

    template <class S>
    __device__ static void store(const Raw& r, S& st, unsigned row, unsigned s, unsigned u) {
        const unsigned half = s % 2, c = u / 2, l = 16 * (u % 2);
        unsigned q[4], qh[4];
        words(q, r.qs);
        words(qh, r.qh);
#pragma unroll
        for (unsigned hi = 0; hi < 2; ++hi) {
            unsigned v[4];
#pragma unroll
            for (unsigned i = 0; i < 4; ++i) {
                v[i] = (q[i] >> (4 * hi)) & NIBBLES;
                if (Q5) v[i] |= ((qh[i] >> (4 * half + 2 * c + hi)) & 0x01010101) << 4;
            }
            st_words(&st.w[row][32 * (2 * c + hi) + l], v);
        }
        const float2 sm = k4_group(r.head, 4 * half + u);
        gemm_put_scale(st, u, 0, row, sm.x);
        gemm_put_scale(st, u, 1, row, -sm.y);
    }
};

// Q6_K, planar as layout.rs stores it: a stage is half n = s % 2 of block
// s / 2, runs 8n .. 8n + 7. Thread u takes the ql bytes 32c + l .. l + 15
// (c = u / 2, l = 16 (u % 2)), the low bits of elements l .. l + 15 of
// sub-blocks c (low nibbles) and c + 2 (high nibbles), the qh bytes
// l .. l + 15 holding their top bits (see k6_quants), and the scales of
// runs 2u and 2u + 1.
struct GemmQ6K {
    static constexpr unsigned BLOCK = 256, RUNS = 2;
    static constexpr bool MINS = false;

    struct Raw {
        uint4 ql;
        uint4 qh;
        unsigned short scales;
        float d;
    };

    __device__ static void load(Raw& r, const uint8_t* w, size_t total, size_t blk, unsigned s,
                                unsigned u) {
        const size_t b = blk + s / 2;
        const unsigned n = s % 2;
        r.ql = ld_raw(w + b * 128 + 64 * n + 16 * u);
        r.qh = ld_raw(w + total * 128 + b * 64 + 32 * n + 16 * (u % 2));
        r.scales = __ldg(reinterpret_cast<const unsigned short*>(w + total * 192 + b * 16 + 8 * n) + u);
        r.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 208) + b));
    }

    template <class S>
    __device__ static void store(const Raw& r, S& st, unsigned row, unsigned, unsigned u) {
        const unsigned c = u / 2, l = 16 * (u % 2);
        unsigned ql[4], qh[4];
        words(ql, r.ql);
        words(qh, r.qh);
#pragma unroll
        for (unsigned hi = 0; hi < 2; ++hi) {
            const unsigned sub = c + 2 * hi;
            unsigned v[4];
#pragma unroll
            for (unsigned i = 0; i < 4; ++i) v[i] = k6_quants(ql[i], qh[i], sub);
            st_words(&st.w[row][32 * sub + l], v);
        }
#pragma unroll
        for (unsigned i = 0; i < 2; ++i)
            gemm_put_scale(st, u, i, row, k6_group(r.d, r.scales, i));
    }
};

// Q8_0, planar as layout.rs stores it: a stage is four blocks of 32, and
// thread u takes block u.
struct GemmQ8_0 {
    static constexpr unsigned BLOCK = 32, RUNS = 1;
    static constexpr bool MINS = false;

    struct Raw {
        uint4 q[2];
        float d;
    };

    __device__ static void load(Raw& r, const uint8_t* w, size_t total, size_t blk, unsigned s,
                                unsigned u) {
        const size_t b = blk + GEMM_SUBS * s + u;
#pragma unroll
        for (unsigned i = 0; i < 2; ++i) r.q[i] = ld_raw(w + b * 32 + 16 * i);
        r.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 32) + b));
    }

    template <class S>
    __device__ static void store(const Raw& r, S& st, unsigned row, unsigned, unsigned u) {
#pragma unroll
        for (unsigned i = 0; i < 2; ++i)
            *reinterpret_cast<uint4*>(&st.w[row][32 * u + 16 * i]) = r.q[i];
        gemm_put_scale(st, u, 0, row, r.d);
    }
};

// Q4_0, planar as layout.rs stores it: a stage is four blocks of 32, and
// thread u takes block u, its low nibbles elements 0 .. 15, high ones 16 .. 31.
struct GemmQ4_0 {
    static constexpr unsigned BLOCK = 32, RUNS = 1;
    static constexpr bool MINS = false;

    struct Raw {
        uint4 q;
        float d;
    };

    __device__ static void load(Raw& r, const uint8_t* w, size_t total, size_t blk, unsigned s,
                                unsigned u) {
        const size_t b = blk + GEMM_SUBS * s + u;
        r.q = ld_raw(w + b * 16);
        r.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 16) + b));
    }

    template <class S>
    __device__ static void store(const Raw& r, S& st, unsigned row, unsigned, unsigned u) {
        unsigned q[4], lo[4], hi[4];
        words(q, r.q);
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            lo[i] = __vsub4(q[i] & NIBBLES, 0x08080808u);
            hi[i] = __vsub4(q[i] >> 4 & NIBBLES, 0x08080808u);
        }
        st_words(&st.w[row][32 * u], lo);
        st_words(&st.w[row][32 * u + 16], hi);
        gemm_put_scale(st, u, 0, row, r.d);
    }
};

// PQ2_0, planar as layout.rs stores it: a stage is one block of 128, and
// thread u takes its elements 32u .. 32u + 31, codes q stored as q - 1.
struct GemmPQ2_0 {
    static constexpr unsigned BLOCK = 128, RUNS = 1;
    static constexpr bool MINS = false;

    struct Raw {
        uint2 q;
        float d;
    };

    __device__ static void load(Raw& r, const uint8_t* w, size_t total, size_t blk, unsigned s,
                                unsigned u) {
        const size_t b = blk + s;
        r.q = __ldg(reinterpret_cast<const uint2*>(w + b * 32 + 8 * u));
        r.d = __half2float(__ldg(reinterpret_cast<const __half*>(w + total * 32) + b));
    }

    template <class S>
    __device__ static void store(const Raw& r, S& st, unsigned row, unsigned, unsigned u) {
        // word i: the four codes of raw byte i, each minus one
        const auto spread = [](unsigned b) {
            return __vsub4((b | b << 6 | b << 12 | b << 18) & 0x03030303u, 0x01010101u);
        };
        unsigned lo[4], hi[4];
#pragma unroll
        for (unsigned i = 0; i < 4; ++i) {
            lo[i] = spread(r.q.x >> (8 * i) & 0xFF);
            hi[i] = spread(r.q.y >> (8 * i) & 0xFF);
        }
        st_words(&st.w[row][32 * u], lo);
        st_words(&st.w[row][32 * u + 16], hi);
        gemm_put_scale(st, u, 0, row, r.d);
    }
};

// Queues the copy of stage `k` of the int8 inputs. Inputs past the batch
// repeat the last one; their results are not stored.
template <class T>
__device__ __forceinline__ void gemm_copy_inputs(GemmStage<T>& st, const int8_t* qs,
                                                 unsigned cols, unsigned col0, unsigned n,
                                                 unsigned k) {
    constexpr unsigned CHUNKS = GEMM_K / 16;
#pragma unroll
    for (unsigned c = threadIdx.x; c < T::COLS * CHUNKS; c += T::THREADS) {
        const unsigned row = c / CHUNKS, part = c % CHUNKS;
        const size_t col = min(col0 + row, n - 1);
        cp_async16(&st.x[row][16 * part], qs + col * cols + k * GEMM_K + 16 * part);
    }
    cp_async_commit();
}

// The scales of a stage's inputs, two sub-blocks of one input per float4,
// read into registers by the first threads and stored transposed once the
// stage's buffer is free.

__device__ __forceinline__ float4 gemm_load_scales(const float2* ds, unsigned cols,
                                                   unsigned col0, unsigned n, unsigned k) {
    const unsigned row = threadIdx.x / 2, pair = threadIdx.x % 2;
    const size_t col = min(col0 + row, n - 1);
    return __ldg(reinterpret_cast<const float4*>(ds + col * (cols / 32) + k * GEMM_SUBS) + pair);
}

template <class T>
__device__ __forceinline__ void gemm_store_scales(GemmStage<T>& st, float4 v) {
    const unsigned row = threadIdx.x / 2, pair = threadIdx.x % 2;
    float* a = &st.xds[2 * pair][row / 2].x + row % 2;
    float* b = &st.xds[2 * pair + 1][row / 2].x + row % 2;
    a[0] = v.x;
    a[2] = v.y;
    b[0] = v.z;
    b[2] = v.w;
}

// The accumulators of a lane: [m tile][n tile][fragment element]; element e
// is row g + 8 (e / 2) of the m tile and input 2t + e % 2 of the n tile.
template <class T>
struct GemmAcc {
    float v[T::MT][T::NT][4];
};

// Multiplies the warp's rows by its inputs over sub-blocks first .. last - 1
// of a stage.
template <class F, class T>
__device__ __forceinline__ void gemm_subs(GemmAcc<T>& acc, const GemmStage<T>& st,
                                          unsigned r0, unsigned c0, unsigned lane,
                                          unsigned first, unsigned last) {
    const unsigned g = lane / 4, q = lane % 4;
#pragma unroll
    for (unsigned s = first; s < last; ++s) {
        // A: rows 0-7 and 8-15 of k 0-15, then of k 16-31; B: k 0-15 then
        // 16-31 of inputs 0-7, then of inputs 8-15.
        unsigned a[T::MT][4], b[T::NT][2];
#pragma unroll
        for (unsigned m = 0; m < T::MT; ++m)
            ldsm_x4(a[m], &st.w[r0 + 16 * m + lane % 16][32 * s + 16 * (lane / 16)]);
#pragma unroll
        for (unsigned j = 0; j < T::NT; j += 2) {
            unsigned r[4];
            ldsm_x4(r, &st.x[c0 + 8 * j + lane % 8 + 8 * (lane / 16)][32 * s + 16 * ((lane / 8) % 2)]);
            b[j][0] = r[0];
            b[j][1] = r[1];
            b[j + 1][0] = r[2];
            b[j + 1][1] = r[3];
        }
#pragma unroll
        for (unsigned h = 0; h < F::RUNS; ++h) {
            float scale[2 * T::MT], unbias[2 * T::MT], mins[2 * T::MT] = {};
#pragma unroll
            for (unsigned m = 0; m < T::MT; ++m) {
                const float4 v = st.scale[s][(r0 + 16 * m) / 2 + g];
                scale[2 * m] = h ? v.z : v.x;
                scale[2 * m + 1] = h ? v.w : v.y;
                if (F::MINS) {
                    mins[2 * m] = v.z;
                    mins[2 * m + 1] = v.w;
                }
            }
#pragma unroll
            for (unsigned i = 0; i < 2 * T::MT; ++i) unbias[i] = -GEMM_BIAS * scale[i];
#pragma unroll
            for (unsigned j = 0; j < T::NT; ++j) {
                const unsigned col = c0 + 8 * j + 2 * q;
                const float4 v = st.xds[s][col / 2];
                const float2 xd = {v.x, v.y}, xs = {v.z, v.w};
#pragma unroll
                for (unsigned m = 0; m < T::MT; ++m) {
                    int d[4];
                    if (F::RUNS == 1)
                        mma_k32_from(d, a[m][0], a[m][1], a[m][2], a[m][3], b[j][0], b[j][1],
                                     GEMM_BIAS_BITS);
                    else
                        mma_k16_from(d, a[m][2 * h], a[m][2 * h + 1], b[j][h], GEMM_BIAS_BITS);
#pragma unroll
                    for (unsigned e = 0; e < 4; ++e) {
                        const unsigned i = 2 * m + e / 2;
                        float v = acc.v[m][j][e];
                        if (F::MINS) v = fmaf(mins[i], e % 2 ? xs.y : xs.x, v);
                        const float x = e % 2 ? xd.y : xd.x;
                        acc.v[m][j][e] = fmaf(fmaf(__int_as_float(d[e]), scale[i], unbias[i]), x, v);
                    }
                }
            }
        }
    }
}

// The gated outputs of a block, by input; the padding puts the lanes of a
// warp's stores in distinct banks.
template <class T>
struct GemmGluTile {
    float v[T::COLS][T::ROWS / 2 + 4];
};

// Writes silu(gate) * up, or gelu(gate) * up, of the block's outputs, gathering them by input so
// that each warp quantizes whole blocks of 32 of one input. The stage
// buffers are free: the k loop ends with a barrier.
template <class T>
__device__ __forceinline__ void gemm_glu_out(const GemmAcc<T>& acc, GemmGluTile<T>* t, Act out,
                                             unsigned row0, unsigned in0, unsigned r0,
                                             unsigned c0, unsigned rows, unsigned n,
                                             bool gelu_gate) {
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned g = lane / 4, q = lane % 4;
#pragma unroll
    for (unsigned m = 0; m < T::MT; ++m)
#pragma unroll
        for (unsigned j = 0; j < T::NT; ++j)
#pragma unroll
            for (unsigned e = 0; e < 2; ++e) {
                const float gate = acc.v[m][j][e];
                t->v[c0 + 8 * j + 2 * q + e][r0 / 2 + 8 * m + g] =
                    (gelu_gate ? gelu(gate) : silu(gate)) * acc.v[m][j][e + 2];
            }
    __syncthreads();
    constexpr unsigned BLOCKS = T::ROWS / 2 / 32;
    for (unsigned p = warp; p < T::COLS * BLOCKS; p += T::THREADS / WARP) {
        const unsigned in = in0 + p / BLOCKS, first = 32 * (p % BLOCKS);
        if (in >= n || row0 + first >= rows) continue;
        out.put(static_cast<size_t>(in) * rows + row0 + first + lane, t->v[p / BLOCKS][first + lane]);
    }
}

// grid (ceil(n / T::COLS), ceil(rows / T::ROWS), splits), block T::THREADS,
// 2 sizeof(GemmStage<T>) bytes of dynamic shared memory. `cols` is a
// multiple of GEMM_K; output i of row r goes to y[i * rows + r]. With two
// splits each block takes half the stages and adds its sums to a zeroed y;
// two terms added to zero give the same bits in either order.
//
// Given `up`, w is the gate of a gated feed-forward and the output is
// silu(w x) * (up x), or with `gelu_gate` gelu(w x) * (up x), T::ROWS / 2
// rows per block: tile row R holds row 8 (R / 16) + R % 8 of the block's
// gate rows when R % 16 < 8 and of its up rows otherwise, so each lane
// holds both factors of its outputs. The
// outputs go through shared memory by input and are written as a GEMV
// input: f32 values to y, int8 values to yq and block scales to yds.
template <class F, class T>
__device__ __forceinline__ void gemm(const uint8_t* w, const uint8_t* up, Q8Input x, float* y,
                                     int8_t* yq, float2* yds, unsigned rows, unsigned cols,
                                     size_t total, unsigned n, bool gelu_gate) {
    extern __shared__ __align__(16) uint8_t gemm_shared[];
    GemmStage<T>* stage = reinterpret_cast<GemmStage<T>*>(gemm_shared);
    static_assert(sizeof(GemmGluTile<T>) <= 2 * sizeof(GemmStage<T>), "fits in the stages");
    const unsigned warp = threadIdx.x / WARP, lane = threadIdx.x % WARP;
    const unsigned r0 = 16 * T::MT * (warp % T::WARP_ROWS), c0 = 8 * T::NT * (warp / T::WARP_ROWS);
    const bool glu = up != nullptr;
    const unsigned row0 = blockIdx.y * (glu ? T::ROWS / 2 : T::ROWS), in0 = blockIdx.x * T::COLS;
    const unsigned all = cols / GEMM_K, splits = gridDim.z;
    const unsigned begin = all * blockIdx.z / splits, stages = all * (blockIdx.z + 1) / splits - begin;
    // Rows past the end repeat the last one; their results are not stored.
    const unsigned own = threadIdx.x / GEMM_PARTS, u = threadIdx.x % GEMM_PARTS;
    const unsigned src = glu ? row0 + 8 * (own / 16) + own % 8 : row0 + own;
    if (glu && own % 16 >= 8) w = up;
    const size_t blk = static_cast<size_t>(min(src, rows - 1)) * (cols / F::BLOCK);
    const bool scales = threadIdx.x < T::SCALE_THREADS;

    typename F::Raw raw;
    float4 next = {};
    F::load(raw, w, total, blk, begin, u);
    gemm_copy_inputs<T>(stage[0], x.qs, cols, in0, n, begin);
    if (scales) gemm_store_scales(stage[0], gemm_load_scales(x.ds, cols, in0, n, begin));
    F::store(raw, stage[0], own, begin, u);
    if (stages > 1) {
        F::load(raw, w, total, blk, begin + 1, u);
        if (scales) next = gemm_load_scales(x.ds, cols, in0, n, begin + 1);
    }
    cp_async_wait<0>();
    __syncthreads();

    // A warp whose inputs all lie past the batch only helps load the stages.
    const bool busy = in0 + c0 < n;
    GemmAcc<T> acc = {};
    for (unsigned k = 0; k < stages; ++k) {
        const GemmStage<T>& cur = stage[k % 2];
        GemmStage<T>& nxt = stage[(k + 1) % 2];
        const bool more = k + 1 < stages;
        if (more) gemm_copy_inputs<T>(nxt, x.qs, cols, in0, n, begin + k + 1);
        if (busy) gemm_subs<F, T>(acc, cur, r0, c0, lane, 0, GEMM_SUBS / 2);
        if (more) {
            F::store(raw, nxt, own, begin + k + 1, u);
            if (scales) gemm_store_scales(nxt, next);
        }
        if (k + 2 < stages) {
            F::load(raw, w, total, blk, begin + k + 2, u);
            if (scales) next = gemm_load_scales(x.ds, cols, in0, n, begin + k + 2);
        }
        if (busy) gemm_subs<F, T>(acc, cur, r0, c0, lane, GEMM_SUBS / 2, GEMM_SUBS);
        cp_async_wait<0>();
        __syncthreads();
    }

    const unsigned g = lane / 4, q = lane % 4;
    if (glu) {
        gemm_glu_out(acc, reinterpret_cast<GemmGluTile<T>*>(gemm_shared), Act{y, yq, yds}, row0,
                     in0, r0, c0, rows, n, gelu_gate);
        return;
    }
#pragma unroll
    for (unsigned m = 0; m < T::MT; ++m)
#pragma unroll
        for (unsigned j = 0; j < T::NT; ++j)
#pragma unroll
            for (unsigned e = 0; e < 4; ++e) {
                const unsigned row = row0 + r0 + 16 * m + g + 8 * (e / 2);
                const unsigned in = in0 + c0 + 8 * j + 2 * q + e % 2;
                if (row >= rows || in >= n) continue;
                float* out = y + static_cast<size_t>(in) * rows + row;
                if (splits > 1) atomicAdd(out, acc.v[m][j][e]);
                else *out = acc.v[m][j][e];
            }
}

// At most 128 registers per thread.
#define GEMM_KERNEL(name, F, T)                                                                \
    extern "C" __global__ void __launch_bounds__(T::THREADS, T::BLOCKS)                        \
        name(const uint8_t* w, const uint8_t* up, const int8_t* xq, const float2* xds,         \
             float* y, int8_t* yq, float2* yds, unsigned rows, unsigned cols, size_t total,    \
             unsigned n, unsigned gelu_gate) {                                                 \
        gemm<F, T>(w, up, Q8Input{xq, xds}, y, yq, yds, rows, cols, total, n, gelu_gate);      \
    }

using GemmTile32 = GemmTile<64, 32, 1, 2>;
using GemmTile64 = GemmTile<64, 64, 2, 2>;
using GemmTile128 = GemmTile<128, 128, 2, 1>;
// The sizes QUANT_TILES in gemm.rs gives.
static_assert(2 * sizeof(GemmStage<GemmTile32>) == 33792, "shared bytes of the 32-wide tile");
static_assert(2 * sizeof(GemmStage<GemmTile64>) == 45056, "shared bytes of the 64-wide tile");
static_assert(2 * sizeof(GemmStage<GemmTile128>) == 90112, "shared bytes of the 128-wide tile");

// Kernel names as gemm.rs builds them: the width follows the format's name.
#define GEMM_KERNELS(name, F)             \
    GEMM_KERNEL(name##_32, F, GemmTile32) \
    GEMM_KERNEL(name##_64, F, GemmTile64) \
    GEMM_KERNEL(name##_128, F, GemmTile128)

GEMM_KERNELS(gemm_q4_k, GemmK4<false>)
GEMM_KERNELS(gemm_q5_k, GemmK4<true>)
GEMM_KERNELS(gemm_q6_k, GemmQ6K)
GEMM_KERNELS(gemm_q8_0, GemmQ8_0)
GEMM_KERNELS(gemm_q4_0, GemmQ4_0)
GEMM_KERNELS(gemm_pq2_0, GemmPQ2_0)
