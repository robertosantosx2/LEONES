// Prefill GEMM on f16 cooperative matrices, as gemm_q in kernels.cu (the same 16 x 16 x 16 f16 products summed in f32,
// in the same order, so results match bit for bit). Workgroup (x, y): output rows 64x .. 64x + 63 of tile y, whose
// positions m0 .. m0 + cnt read x row xrow[m] (m when xrow is null) and write y row m. tiles holds [w, m0 | cnt << 32]
// per tile; tiles = null is one dense matrix wd over positions 0 .. nd. act: 0 stores, 1 y = silu(y) * result, 2 adds.
// COOP 0 (gemm_f_dp, devices without cooperative matrices): the same f16 inputs, each output summed by one invocation
// with fma in k order, so results differ from CUDA in the last bits.
#if COOP
#extension GL_KHR_cooperative_matrix : require
#extension GL_KHR_memory_scope_semantics : require
#endif
#extension GL_EXT_control_flow_attributes : require
layout(local_size_x = 256) in;
#include "common.glsl"
#define SHARED_TABLES
#include "deq.glsl"
layout(buffer_reference, std430, buffer_reference_align = 8) buffer U64 { uint64_t v[]; };
layout(buffer_reference, std430, buffer_reference_align = 16) buffer V4 { vec4 v[]; };
layout(push_constant) uniform P { U64 tiles; uint64_t wd; V4 x; I32 xrow; F32 y; uint nd; uint xs; uint ys; uint rows; uint nk; uint act; } p;  // nk: K steps of 64 (cols / 64)
#ifndef SM
#define SM 0
#endif
// SM 1 (gemm_fs): only the tiles of at most 32 positions (most expert tiles), which SM 0 skips (tile lists, COOP);
// X holds XM positions.
const uint BM = 128, BK = 64, PW = (BK + 8) / 2, XM = SM != 0 ? 32 : BM;  // smem pitch in words (2 halves each)
#if COOP
#define ACC coopmat<float, gl_ScopeSubgroup, 16, 16, gl_MatrixUseAccumulator>
#define NE ri.length()
#define RI(i) uint(ri[i])
#define CI(i) uint(ci[i])
#else  // element i of an invocation's 16 x 16 tile as in mma.sync
#define NE 8
#define RI(i) (g + 8 * ((i) >> 2))
#define CI(i) (2 * t + ((i) & 1) + 8 * (((i) >> 1) & 1))
#endif
shared uint xs[XM * PW], ws[64 * PW];
uint h2(float a, float b) { return packFloat2x16(f16vec2(a, b)); }
shared float ix[512];  // the row and column index matrices

// W step kb as halves: invocation decodes values 8 j .. 8 j + 7 of rows tid / 8 + 32 q (q < 2) into wv[4 q ..].
void ldw(U8 wt, uint n0, uint kb, uint tid, out uint wv[8]) {
    uint sb = kb / 4, part = kb % 4;
    [[unroll]] for (uint q = 0; q < 2; q++) {
        uint r = tid / 8 + 32 * q, j = tid % 8;
        float v[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
        if (n0 + r < p.rows) deq8(wt, (n0 + r) * rowb(p.nk * 64) + sb * SBB, part * 8 + j, v);
        [[unroll]] for (uint e = 0; e < 4; e++) wv[4 * q + e] = h2(v[2 * e], v[2 * e + 1]);
    }
}
void stw(uint tid, uint wv[8]) {
    [[unroll]] for (uint q = 0; q < 2; q++) [[unroll]] for (uint e = 0; e < 4; e++) ws[(tid / 8 + 32 * q) * PW + (tid % 8) * 4 + e] = wv[4 * q + e];
}

void main() {
    uint tid = gl_LocalInvocationID.x, w = WARP, n0 = gl_WorkGroupID.x * 64;
    uint wm = (w >> 1) * 32, wn = (w & 1) * 32, m0, cnt;
    U8 wt;
    if (uint64_t(p.tiles) != 0) {
        uint64_t t = p.tiles.v[2 * gl_WorkGroupID.y + 1];
        wt = U8(p.tiles.v[2 * gl_WorkGroupID.y]); m0 = uint(t); cnt = uint(t >> 32);
    } else {
        wt = U8(p.wd); m0 = gl_WorkGroupID.y * XM; cnt = min(XM, p.nd - m0);
    }
#if COOP
    if (uint64_t(p.tiles) != 0 && (cnt <= 32) != (SM != 0)) return;
#endif
    for (uint i = tid; i < 256; i += 256) { ix[i] = float(i / 16); ix[256 + i] = float(i % 16); }
    load_tables();
    uint g = LANE >> 2, t = LANE & 3;
    // sm (SM 1): the 2 x 4 output tiles of 16 x 16 go one per subgroup (rows tm, columns tn, in acc[0][0]) instead of
    // four each to subgroups 0 and 1. Each output sums the same products in the same order either way.
    const bool sm = SM != 0;
    uint tm = 16 * (w & 1), tn = 16 * (w >> 1);
#if COOP
    ACC acc[2][2];
    for (uint a = 0; a < 2; a++) for (uint b = 0; b < 2; b++) acc[a][b] = ACC(0.0);
#else
    float acc[2][2][8];
    [[unroll]] for (uint a = 0; a < 2; a++) for (uint b = 0; b < 2; b++) for (uint i = 0; i < 8; i++) acc[a][b][i] = 0.0;
#endif
    // X: invocation converts 4 floats at column xc of rows tid / 16 + 16 q per step (16-byte loads: strides are
    // multiples of 4). xb: their offsets in vec4, ~0 past cnt.
    uint xc = (tid & 15) * 4, xb[XM / 16];
    [[unroll]] for (uint q = 0; q < XM / 16; q++) {
        uint r = (tid >> 4) + 16 * q;
        xb[q] = r < cnt ? ((uint64_t(p.xrow) != 0 ? uint(p.xrow.v[m0 + r]) : m0 + r) * p.xs + xc) / 4 : ~0u;
    }
    // W step kb + 1 is decoded into registers during step kb's products and stored after them (gemm_q in kernels.cu).
    uint wv[8];
    ldw(wt, n0, 0, tid, wv);
    stw(tid, wv);
    for (uint kb = 0; kb < p.nk; kb++) {
        [[unroll]] for (uint q = 0; q < XM / 16; q++) {
            uint r = (tid >> 4) + 16 * q;
            vec4 v = xb[q] != ~0u ? p.x.v[xb[q] + kb * BK / 4] : vec4(0.0);
            xs[r * PW + xc / 2] = h2(v.x, v.y); xs[r * PW + xc / 2 + 1] = h2(v.z, v.w);
        }
        barrier();
        if (kb + 1 < p.nk) ldw(wt, n0, kb + 1, tid, wv);
#if COOP
        // Expert tiles are often part full; a subgroup whose 32 positions are all past cnt has nothing to multiply.
        if (sm) {
            if (tm < cnt)
            [[unroll]] for (uint kk = 0; kk < BK; kk += 16) {
                coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseA> a;
                coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseB> b;
                coopMatLoad(a, xs, tm * PW + kk / 2, PW, gl_CooperativeMatrixLayoutRowMajor);
                coopMatLoad(b, ws, tn * PW + kk / 2, PW, gl_CooperativeMatrixLayoutColumnMajor);
                acc[0][0] = coopMatMulAdd(a, b, acc[0][0]);
            }
        } else if (wm < cnt)
        [[unroll]] for (uint kk = 0; kk < BK; kk += 16) {
            coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseA> a[2];
            coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseB> b[2];
            [[unroll]] for (uint i = 0; i < 2; i++) {
                coopMatLoad(a[i], xs, (wm + 16 * i) * PW + kk / 2, PW, gl_CooperativeMatrixLayoutRowMajor);
                coopMatLoad(b[i], ws, (wn + 16 * i) * PW + kk / 2, PW, gl_CooperativeMatrixLayoutColumnMajor);
            }
            [[unroll]] for (uint mt = 0; mt < 2; mt++)
                [[unroll]] for (uint nt = 0; nt < 2; nt++) acc[mt][nt] = coopMatMulAdd(a[mt], b[nt], acc[mt][nt]);
        }
#else
        for (uint k = 0; k < BK / 2; k++) {
            vec2 xv[2][2], wv[2][4];
            [[unroll]] for (uint m = 0; m < 2; m++) [[unroll]] for (uint e = 0; e < 2; e++) xv[m][e] = unpackHalf2x16(xs[(wm + 16 * m + RI(4 * e)) * PW + k]);
            [[unroll]] for (uint m = 0; m < 2; m++) [[unroll]] for (uint e = 0; e < 4; e++) wv[m][e] = unpackHalf2x16(ws[(wn + 16 * m + CI(e)) * PW + k]);
            [[unroll]] for (uint mt = 0; mt < 2; mt++) [[unroll]] for (uint nt = 0; nt < 2; nt++) [[unroll]] for (uint i = 0; i < 8; i++) {
                vec2 a = xv[mt][i >> 2], b = wv[nt][i & 3];
                acc[mt][nt][i] = fma(a.y, b.y, fma(a.x, b.x, acc[mt][nt][i]));
            }
        }
#endif
        barrier();
        if (kb + 1 < p.nk) stw(tid, wv);
    }
#if COOP
    // Accumulator element i of this invocation is at row ri[i], column ci[i] (the layout is the implementation's).
    ACC ri, ci;
    coopMatLoad(ri, ix, 0, 16, gl_CooperativeMatrixLayoutRowMajor);
    coopMatLoad(ci, ix, 256, 16, gl_CooperativeMatrixLayoutRowMajor);
#endif
    for (uint mt = 0; mt < 2; mt++)
        for (uint nt = 0; nt < 2; nt++)
            for (uint i = 0; i < NE; i++) {
                if (sm && mt + nt != 0) break;
                uint r = (sm ? tm : wm + 16 * mt) + RI(i), n = n0 + (sm ? tn : wn + 16 * nt) + CI(i);
                if (r >= cnt || n >= p.rows) continue;
                uint o = (m0 + r) * p.ys + n;
                float v = acc[mt][nt][i];
                p.y.v[o] = p.act == 0 ? v : p.act == 1 ? silu(p.y.v[o]) * v : p.y.v[o] + v;
            }
}
