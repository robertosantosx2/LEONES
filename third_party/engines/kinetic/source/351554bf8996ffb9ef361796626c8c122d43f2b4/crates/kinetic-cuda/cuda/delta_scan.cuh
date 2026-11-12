#pragma once

#include "delta_chunk.cuh"
#include "mma.cuh"

// The chunk scan of the delta rule (see delta_chunk.cuh) on f16 tensor
// cores with f32 sums. A block owns 32 rows of one head's state and walks
// the chunks in order; warp w keeps rows 16w .. 16w + 15 in registers, as
// the accumulators of the update product, so the state stays f32
// throughout. Every factor enters as the sum of two f16 values, high and
// low part, and a product as the three terms of those parts that matter at
// f32 precision, so the results are as accurate as f32 arithmetic.
//
// Per chunk a warp forms its rows of U = T diag(b) V - W S^T and of
// O = diag(e^G) Q S^T + P U, then adds U^T K' to its rows of the state,
// K' being the keys scaled by e^(G_C - G_t), which the block stages in
// shared memory, split in the same way, by token.

constexpr unsigned DSCAN_ROWS = 32;
constexpr unsigned DSCAN_THREADS = 64;
constexpr unsigned DSCAN_DIM = 128;

struct DeltaScanShared {
    // K', high and low part.
    __half k[2][DCHUNK][DSCAN_DIM + 8];
    // U by warp, high and low part, token and row; the padding keeps the
    // rows of an ldmatrix read in distinct banks.
    __half u[2][2][DCHUNK][16 + 8];
};

// The high and low m16n8k16 A fragments of rows row0 .. row0 + 15 and
// columns k0 .. k0 + 15 of an f32 matrix in global memory; rows at or past
// `rows` are zero.
__device__ __forceinline__ void scan_a(unsigned (&a)[2][4], const float* m, size_t stride,
                                       unsigned row0, unsigned k0, unsigned rows, unsigned lane) {
    const unsigned g = lane / 4, t = lane % 4;
#pragma unroll
    for (unsigned i = 0; i < 4; ++i) {
        const unsigned row = row0 + g + 8 * (i % 2), col = k0 + 2 * t + 8 * (i / 2);
        float2 v = make_float2(0.0f, 0.0f);
        if (row < rows) v = __ldg(reinterpret_cast<const float2*>(m + row * stride + col));
        split_pair(v.x, v.y, a[0][i], a[1][i]);
    }
}

// d += a b over split factors: high times high, high times low and low
// times high.
__device__ __forceinline__ void mma_split(float (&d)[4], const unsigned (&a)[2][4],
                                          const unsigned (&b)[2][2]) {
    mma_f16(d, a[0][0], a[0][1], a[0][2], a[0][3], b[0][0], b[0][1]);
    mma_f16(d, a[0][0], a[0][1], a[0][2], a[0][3], b[1][0], b[1][1]);
    mma_f16(d, a[1][0], a[1][1], a[1][2], a[1][3], b[0][0], b[0][1]);
}

// grid (n_v_heads, head_v_dim / DSCAN_ROWS), block DSCAN_THREADS; head_k_dim
// = head_v_dim = DSCAN_DIM.
extern "C" __global__ void __launch_bounds__(DSCAN_THREADS, 5) delta_chunk_scan(DeltaArgs a) {
    __shared__ __align__(16) DeltaScanShared sh;
    const unsigned vh = blockIdx.x, kh = vh % a.n_k_heads;
    const unsigned tid = threadIdx.x, warp = tid / WARP, lane = tid % WARP;
    const unsigned g = lane / 4, t = lane % 4;
    const unsigned r0 = blockIdx.y * DSCAN_ROWS + 16 * warp;
    const unsigned key_dim = a.n_k_heads * DSCAN_DIM, vd = a.n_v_heads * DSCAN_DIM;
    const size_t head = static_cast<size_t>(vh) * DSCAN_DIM * DSCAN_DIM;
    const DeltaBatch db = delta_batch(a);
    auto& u = sh.u[warp];

    // s[n][e]: state row r0 + g + 8 (e / 2), column 8n + 2t + e % 2.
    float s[DSCAN_DIM / 8][4];
#pragma unroll
    for (unsigned n = 0; n < DSCAN_DIM / 8; ++n)
#pragma unroll
        for (unsigned e = 0; e < 4; ++e)
            s[n][e] = a.s_in[head + static_cast<size_t>(r0 + g + 8 * (e / 2)) * DSCAN_DIM + 8 * n +
                             2 * t + e % 2];

    for (unsigned c0 = 0; c0 < a.n; c0 += DCHUNK) {
        const unsigned rows = min(DCHUNK, a.n - c0);
        const size_t tok = static_cast<size_t>(vh) * a.n + c0;
        const float* conv = db.conv + static_cast<size_t>(c0) * a.channels;
        // Lane i holds G of token i.
        const float gl = lane < rows ? db.gamma[tok + lane] : 0.0f;
        const float last = __shfl_sync(FULL_MASK, gl, rows - 1);
        {
            // Thread tid stages columns 64 (tid % 2) .. of token tid / 2.
            const unsigned i = tid / 2, c = 64 * (tid % 2);
            const float gi = __shfl_sync(FULL_MASK, gl, i);
            const float f = i < rows ? expf(last - gi) : 0.0f;
            const float* src = conv + static_cast<size_t>(min(i, rows - 1)) * a.channels + key_dim +
                               kh * DSCAN_DIM + c;
#pragma unroll
            for (unsigned q = 0; q < 64; q += 8) {
                const float4 x = __ldg(reinterpret_cast<const float4*>(src + q));
                const float4 y = __ldg(reinterpret_cast<const float4*>(src + q + 4));
                uint4 hi, lo;
                split_pair(f * x.x, f * x.y, hi.x, lo.x);
                split_pair(f * x.z, f * x.w, hi.y, lo.y);
                split_pair(f * y.x, f * y.y, hi.z, lo.z);
                split_pair(f * y.z, f * y.w, hi.w, lo.w);
                *reinterpret_cast<uint4*>(&sh.k[0][i][c + q]) = hi;
                *reinterpret_cast<uint4*>(&sh.k[1][i][c + q]) = lo;
            }
        }

        // W S^T and Q S^T for this warp's rows: [token tile][row tile][e].
        float wu[2][2][4] = {}, o[2][2][4] = {};
#pragma unroll
        for (unsigned ks = 0; ks < DSCAN_DIM / 16; ++ks) {
            unsigned aw[2][2][4], aq[2][2][4];
#pragma unroll
            for (unsigned m = 0; m < 2; ++m) {
                scan_a(aw[m], db.w + tok * DSCAN_DIM, DSCAN_DIM, 16 * m, 16 * ks, rows, lane);
                scan_a(aq[m], conv + kh * DSCAN_DIM, a.channels, 16 * m, 16 * ks, rows, lane);
            }
#pragma unroll
            for (unsigned h = 0; h < 2; ++h) {
                unsigned b[2][2];
                split_pair(s[2 * ks][2 * h], s[2 * ks][2 * h + 1], b[0][0], b[1][0]);
                split_pair(s[2 * ks + 1][2 * h], s[2 * ks + 1][2 * h + 1], b[0][1], b[1][1]);
#pragma unroll
                for (unsigned m = 0; m < 2; ++m) {
                    mma_split(wu[m][h], aw[m], b);
                    mma_split(o[m][h], aq[m], b);
                }
            }
        }

        // U = T diag(b) V - W S^T, into shared memory by token.
#pragma unroll
        for (unsigned m = 0; m < 2; ++m)
#pragma unroll
            for (unsigned h = 0; h < 2; ++h)
#pragma unroll
                for (unsigned e = 0; e < 4; e += 2) {
                    const unsigned i = 16 * m + g + 4 * e, v = 8 * h + 2 * t;
                    float2 x = make_float2(0.0f, 0.0f);
                    if (i < rows) {
                        x = __ldg(reinterpret_cast<const float2*>(db.u + (tok + i) * DSCAN_DIM + r0 + v));
                        x.x -= wu[m][h][e];
                        x.y -= wu[m][h][e + 1];
                    }
                    unsigned hi, lo;
                    split_pair(x.x, x.y, hi, lo);
                    *reinterpret_cast<unsigned*>(&u[0][i][v]) = hi;
                    *reinterpret_cast<unsigned*>(&u[1][i][v]) = lo;
                }
        __syncthreads();

        // O = diag(e^G) Q S^T + P U.
#pragma unroll
        for (unsigned m = 0; m < 2; ++m)
#pragma unroll
            for (unsigned e = 0; e < 4; ++e) {
                const float f = expf(__shfl_sync(FULL_MASK, gl, 16 * m + g + 8 * (e / 2)));
                o[m][0][e] *= f;
                o[m][1][e] *= f;
            }
#pragma unroll
        for (unsigned h = 0; h < 2; ++h) {
            unsigned bu[2][4];
#pragma unroll
            for (unsigned p = 0; p < 2; ++p) ldsm_x4_trans(bu[p], &u[p][lane][8 * h]);
#pragma unroll
            for (unsigned m = 0; m < 2; ++m)
#pragma unroll
                for (unsigned ks = 0; ks < 2; ++ks) {
                    unsigned ap[2][4];
                    scan_a(ap, db.p + tok * DCHUNK, DCHUNK, 16 * m, 16 * ks, rows, lane);
                    const unsigned b[2][2] = {{bu[0][2 * ks], bu[0][2 * ks + 1]},
                                              {bu[1][2 * ks], bu[1][2 * ks + 1]}};
                    mma_split(o[m][h], ap, b);
                }
        }
#pragma unroll
        for (unsigned m = 0; m < 2; ++m)
#pragma unroll
            for (unsigned h = 0; h < 2; ++h)
#pragma unroll
                for (unsigned e = 0; e < 4; e += 2) {
                    const unsigned i = 16 * m + g + 4 * e;
                    if (i < rows)
                        *reinterpret_cast<float2*>(a.out + static_cast<size_t>(c0 + i) * vd +
                                                   vh * DSCAN_DIM + r0 + 8 * h + 2 * t) =
                            make_float2(o[m][h][e], o[m][h][e + 1]);
                }

        // S = e^(G_C) S + U^T K'.
        const float keep = expf(last);
#pragma unroll
        for (unsigned n = 0; n < DSCAN_DIM / 8; ++n)
#pragma unroll
            for (unsigned e = 0; e < 4; ++e) s[n][e] *= keep;
        unsigned au[2][2][4];
#pragma unroll
        for (unsigned ks = 0; ks < 2; ++ks)
#pragma unroll
            for (unsigned p = 0; p < 2; ++p)
                ldsm_x4_trans(au[ks][p], &u[p][16 * ks + 8 * (lane / 16) + lane % 8][8 * ((lane / 8) % 2)]);
#pragma unroll
        for (unsigned n = 0; n < DSCAN_DIM / 8; ++n) {
            unsigned bk[2][4];
#pragma unroll
            for (unsigned p = 0; p < 2; ++p) ldsm_x4_trans(bk[p], &sh.k[p][lane][8 * n]);
#pragma unroll
            for (unsigned ks = 0; ks < 2; ++ks) {
                const unsigned b[2][2] = {{bk[0][2 * ks], bk[0][2 * ks + 1]},
                                          {bk[1][2 * ks], bk[1][2 * ks + 1]}};
                mma_split(s[n], au[ks], b);
            }
        }
        __syncthreads();
    }

#pragma unroll
    for (unsigned n = 0; n < DSCAN_DIM / 8; ++n)
#pragma unroll
        for (unsigned e = 0; e < 4; ++e)
            a.s_out[head + static_cast<size_t>(r0 + g + 8 * (e / 2)) * DSCAN_DIM + 8 * n + 2 * t +
                    e % 2] = s[n][e];
}
