// Prefill GEMM on int8 cooperative matrices, as gemmi_q in kernels.cu: x comes from quant_q8, weights from qi8 as int8
// with a scale (and min) per 16, and each exact int32 product sum over one weight scale (KS = 16 or 32 deep) is
// scaled into the f32 sums in the order and with the roundings of the CUDA kernel (its SASS: ptxas fuses some of
// the PTX's mul and sub), so results match bit for bit. With COOP 0 (gemmi_dp, for devices without cooperative
// matrices) each invocation computes the same exact int32 sums with packed dot products: the same bits again.
// Tiles, grid and act as gemm_f.
#if COOP
#extension GL_KHR_cooperative_matrix : require
#extension GL_KHR_memory_scope_semantics : require
#extension GL_KHR_shader_subgroup_vote : require
#else
#extension GL_EXT_integer_dot_product : require
#endif
#extension GL_EXT_control_flow_attributes : require
layout(local_size_x = 256) in;
#include "common.glsl"
// The IQ tables are read from the buffer, not a spec-constant-sized shared array: with KS = 16 that array makes the
// pipeline ask for 49168 bytes, 16 over the 48 KB of a 3060 or V100 (V100 first chunked prefill: Xid 13 L1_CONFIG_TOO_SMALL).
#include "deq.glsl"
layout(buffer_reference, std430, buffer_reference_align = 8) buffer U64 { uint64_t v[]; };
layout(buffer_reference, std430, buffer_reference_align = 16) buffer UV4 { uvec4 v[]; };
layout(buffer_reference, std430, buffer_reference_align = 8) buffer UV2 { uvec2 v[]; };
layout(push_constant) uniform P { U64 tiles; uint64_t wd; U32 x; I32 xrow; F32 y; uint nd; uint ys; uint rows; uint nk; uint act; } p;  // nk: K steps of 64 (cols / 64)
#ifndef SM
#define SM 0
#endif
// SM 1 (gemmi_s): only the tiles of at most 32 positions, as gemm_fs; X holds XM positions.
const uint BM = 128, XM = SM != 0 ? 32 : BM;
const uint KS = T == 42 || T == 2 || T == 3 || T == 6 || T == 7 || T == 8 || T == 12 || T == 13 || T == 16 || T == 19 || T == 18 || T == 21 || T == 23 ? 32 : 16;
// Rows in words. The int8 products are 32 deep: for KS = 16, w row holds each 16 values followed by 16 zeros (so
// the 16 x values after each 16 add nothing).
const uint PX = 20, PW = KS == 32 ? 20 : 36;
// X and W are double buffered: step kb + 1 is stored while step kb's products run, so one barrier per step.
shared uint xq[2 * XM * PX], wq[2 * 64 * PW];
shared float xd[2][XM][2], xsum[2][XM][4], wsc[2][64][4], wmn[2][64][4];
// The int32 sums start at I2F_BIAS, so a sum c is held as I2F_BIAS + c: for |c| < 2^22 its float is then the
// bits minus 2^23 + 2^22, without the quarter-rate I2F (i2f_small in kernels.cu).
const int I2F_BIAS = 0x4B400000;
float i2f_small(int bc) { return intBitsToFloat(bc) - 12582912.0; }
// acc += dx dw c - sx mw for the biased sum bc, rounded as in kernels.cu.
void scale_add(inout precise float acc, int bc, float dx, float dw, float sx, float mw) {
    precise float s = dx * dw;
    if (MIN) {
        precise float f = fma(i2f_small(bc), s, -(sx * mw));
        acc = acc + f;
    } else {
        acc = fma(i2f_small(bc), s, acc);
    }
}
// The 16 weights (subs 2 wi, 2 wi + 1 of step kb) of row n0 + wr, packed, with the first sub's scale and min.
void ldw(U8 wt, uint wr, uint wi, bool wok, uint n0, uint kb, out uvec4 wv, out float d, out float m) {
    float d1, m1;
    d = 0.0; m = 0.0; wv = uvec4(0);
    if (wok) {
        uint b = (n0 + wr) * rowb(p.nk * 64) + kb / 4 * SBB, sub = (kb & 3) * 8 + 2 * wi;
        qw(wt, b, sub, wv.x, wv.y, d, m);
        qw(wt, b, sub + 1, wv.z, wv.w, d1, m1);
    }
}
// Step kb of x row xr (its half xh: 32 int8 and the scales, or the sums) into X buffer b. 16-byte loads: q8 rows
// are 11 cols / 32 words, a multiple of 4.
void ldx(uint xr, uint xh, bool xok, uint xo, uint cols, uint kb, uint b) {
    uvec4 xv[2];
    [[unroll]] for (uint j = 0; j < 2; j++) xv[j] = xok ? UV4(uint64_t(p.x)).v[(xo + kb * 16 + xh * 8) / 4 + j] : uvec4(0);
    uint o = (b * XM + xr) * PX;
    [[unroll]] for (uint j = 0; j < 8; j++) xq[o + xh * 8 + j] = xv[j / 4][j % 4];
    if (xh == 0) { vec2 d = xok ? uintBitsToFloat(UV2(uint64_t(p.x)).v[(xo + cols / 4) / 2 + kb]) : vec2(0.0); xd[b][xr][0] = d.x; xd[b][xr][1] = d.y; }
    else { vec4 sm = xok ? uintBitsToFloat(UV4(uint64_t(p.x)).v[(xo + cols / 4 + cols / 32) / 4 + kb]) : vec4(0.0); for (uint j = 0; j < 4; j++) xsum[b][xr][j] = sm[j]; }
}
#if COOP
#define IACC coopmat<int, gl_ScopeSubgroup, 16, 16, gl_MatrixUseAccumulator>
#define NE ri.length()
#define RI(i) ri[i]
#define CI(i) ci[i]
#else  // the layout of mma.sync (see nv below)
#define NE 8
#define RI(i) (g + 8 * ((i) >> 2))
#define CI(i) (2 * t + ((i) & 1) + 8 * (((i) >> 1) & 1))
#endif

void main() {
    uint tid = gl_LocalInvocationID.x, w = WARP, n0 = gl_WorkGroupID.x * 64, cols = p.nk * 64;
    uint m0, cnt;
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
    // The row and column index matrices, in X buffer 1 (first stored after the loop's first barrier).
#if COOP
    const uint IX = XM * PX;
    for (uint i = tid; i < 256; i += 256) { xq[IX + i] = i / 16; xq[IX + 256 + i] = i % 16; }
#endif
    if (KS == 16) for (uint i = tid; i < 2 * 64 * PW; i += 256) wq[i] = 0;
    load_tables();
    barrier();
    // Subgroup w multiplies rows bm .. bm + 31 by columns bn .. bn + 31 of the tile, or with sm (at most 32 positions,
    // most expert tiles) only the 16 x 16 at bm, bn, in acc[0][0], so the 8 output tiles are spread over all 8
    // subgroups. Each output sums the same products in the same order either way.
    const bool sm = SM != 0;
    uint bm = sm ? 16 * (w & 1) : (w >> 1) * 32, bn = sm ? 16 * (w >> 1) : (w & 1) * 32;
    // nv: the layout of mma.sync (element i at row g + 8 (i >> 2), column 2 t + (i & 1) + 8 ((i >> 1) & 1)), as on NVIDIA.
    uint g = LANE >> 2, t = LANE & 3;
#if COOP
    // Accumulator element i of this invocation is at row ri[i], column ci[i] (the layout is the implementation's).
    IACC ri, ci;
    coopMatLoad(ri, xq, IX, 16, gl_CooperativeMatrixLayoutRowMajor);
    coopMatLoad(ci, xq, IX + 256, 16, gl_CooperativeMatrixLayoutRowMajor);
    bool nv = ri.length() == 8;
    [[unroll]] for (uint i = 0; i < ri.length(); i++) nv = nv && ri[i] == g + 8 * (i >> 2) && ci[i] == 2 * t + (i & 1) + 8 * ((i >> 1) & 1);
    nv = subgroupAll(nv);
#else
    const bool nv = true;
#endif
    // X: invocation copies 32 int8 (half of the row's 64 per step) of row xr, plus its scales (xh = 0) or sums (xh = 1).
    uint xr = tid >> 1, xh = tid & 1, xo = 0;
    bool xok = xr < cnt;
    if (xok) xo = (uint64_t(p.xrow) != 0 ? uint(p.xrow.v[m0 + xr]) : m0 + xr) * (cols + cols / 8 + cols / 4) / 4;
    // W: invocation decodes the 16 weights (subs 2 wi, 2 wi + 1 of the step) of row wr.
    uint wr = tid >> 2, wi = tid & 3;
    bool wok = n0 + wr < p.rows;
    precise float acc[2][2][8];
    [[unroll]] for (uint a = 0; a < 2; a++) for (uint b = 0; b < 2; b++) for (uint i = 0; i < 8; i++) acc[a][b][i] = 0.0;
    // W step kb is decoded into registers during step kb - 1's products and stored after them, as kernels.cu.
    uvec4 wv; float d, m;
    ldw(wt, wr, wi, wok, n0, 0, wv, d, m);
    if (xr < XM) ldx(xr, xh, xok, xo, cols, 0, 0);
    [[unroll]] for (uint j = 0; j < 4; j++) wq[wr * PW + wi * 128 / KS + j] = wv[j];
    wsc[0][wr][wi] = d; wmn[0][wr][wi] = m;
    for (uint kb = 0; kb < p.nk; kb++) {
        uint xb = kb & 1;
        barrier();
        if (kb + 1 < p.nk && xr < XM) ldx(xr, xh, xok, xo, cols, kb + 1, xb ^ 1);
        if (kb + 1 < p.nk) ldw(wt, wr, wi, wok, n0, kb + 1, wv, d, m);
        // Expert tiles are often part full; a subgroup whose 32 positions are all past cnt has nothing to multiply.
        if (bm < cnt)
        [[unroll]] for (uint h = 0; h < 64 / KS; h++) {
#if COOP
            coopmat<int8_t, gl_ScopeSubgroup, 16, 32, gl_MatrixUseA> a[2];
            coopmat<int8_t, gl_ScopeSubgroup, 32, 16, gl_MatrixUseB> b[2];
            [[unroll]] for (uint i = 0; i < 2; i++) if (!sm || i == 0) {
                coopMatLoad(a[i], xq, (xb * XM + bm + 16 * i) * PX + h * KS / 4, PX, gl_CooperativeMatrixLayoutRowMajor);
                coopMatLoad(b[i], wq, (xb * 64 + bn + 16 * i) * PW + h * 8, PW, gl_CooperativeMatrixLayoutColumnMajor);
            }
#endif
            // NVIDIA layout: a lane's scales are those of 2 rows per mt and 4 columns per nt, loaded once per h.
            float da[2][2], sa[2][2], db[2][4], mb[2][4];
            if (nv) {
                [[unroll]] for (uint mt = 0; mt < 2; mt++)
                    [[unroll]] for (uint e = 0; e < 2; e++) {
                        uint r = bm + 16 * mt + g + 8 * e;
                        da[mt][e] = xd[xb][r][h * KS / 32];
                        if (MIN) sa[mt][e] = KS == 32 ? xsum[xb][r][2 * h] + xsum[xb][r][2 * h + 1] : xsum[xb][r][h];
                    }
                [[unroll]] for (uint nt = 0; nt < 2; nt++)
                    [[unroll]] for (uint e = 0; e < 4; e++) {
                        uint n = bn + 16 * nt + 2 * t + (e & 1) + 8 * (e >> 1);
                        db[nt][e] = wsc[xb][n][h * KS / 16];
                        if (MIN) mb[nt][e] = wmn[xb][n][h * KS / 16];
                    }
            }
            [[unroll]] for (uint mt = 0; mt < 2; mt++)
                [[unroll]] for (uint nt = 0; nt < 2; nt++) if (!sm || mt + nt == 0) {
#if COOP
                    IACC c = coopMatMulAdd(a[mt], b[nt], IACC(I2F_BIAS));
#else
                    // The KS int8 of x rows RI and w rows CI (for KS = 16 the zeros after them add nothing).
                    uint xw[2][KS / 4], ww[4][KS / 4];
                    int c[8];
                    [[unroll]] for (uint j = 0; j < KS / 4; j++) {
                        [[unroll]] for (uint e = 0; e < 2; e++) xw[e][j] = xq[(xb * XM + bm + 16 * mt + RI(4 * e)) * PX + h * KS / 4 + j];
                        [[unroll]] for (uint e = 0; e < 4; e++) ww[e][j] = wq[(xb * 64 + bn + 16 * nt + CI(e)) * PW + h * 8 + j];
                    }
                    [[unroll]] for (uint i = 0; i < 8; i++) {
                        c[i] = I2F_BIAS;
                        [[unroll]] for (uint j = 0; j < KS / 4; j++) c[i] += dotPacked4x8EXT(int(xw[i >> 2][j]), int(ww[i & 3][j]));
                    }
#endif
                    if (nv) {
                        [[unroll]] for (uint i = 0; i < 8; i++)
                            scale_add(acc[mt][nt][i], c[i], da[mt][i >> 2], db[nt][i & 3], sa[mt][i >> 2], mb[nt][i & 3]);
                    }
#if COOP
                    else {
                        [[unroll]] for (uint i = 0; i < c.length(); i++) {
                            uint r = bm + 16 * mt + ri[i], n = bn + 16 * nt + ci[i];
                            float s = KS == 32 ? xsum[xb][r][2 * h] + xsum[xb][r][2 * h + 1] : xsum[xb][r][h];
                            scale_add(acc[mt][nt][i], c[i], xd[xb][r][h * KS / 32], wsc[xb][n][h * KS / 16], s, wmn[xb][n][h * KS / 16]);
                        }
                    }
#endif
                }
        }
        if (kb + 1 < p.nk) {
            [[unroll]] for (uint j = 0; j < 4; j++) wq[((xb ^ 1) * 64 + wr) * PW + wi * 128 / KS + j] = wv[j];
            wsc[xb ^ 1][wr][wi] = d; wmn[xb ^ 1][wr][wi] = m;
        }
    }
    [[unroll]] for (uint mt = 0; mt < 2; mt++)
        [[unroll]] for (uint nt = 0; nt < 2; nt++)
            [[unroll]] for (uint i = 0; i < NE; i++) if (!sm || mt + nt == 0) {
                uint r = bm + 16 * mt + RI(i), n = n0 + bn + 16 * nt + CI(i);
                if (r >= cnt || n >= p.rows) continue;
                uint o = (m0 + r) * p.ys + n;
                float v = acc[mt][nt][i];
                p.y.v[o] = p.act == 0 ? v : p.act == 1 ? silu(p.y.v[o]) * v : p.y.v[o] + v;
            }
}
