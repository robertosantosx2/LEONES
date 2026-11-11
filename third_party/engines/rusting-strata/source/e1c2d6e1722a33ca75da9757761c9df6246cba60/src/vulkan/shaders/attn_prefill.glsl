// Flash attention prefill, as attn_prefill_t in kernels.cu, with cooperative matrices in place of mma.sync (the same
// 16 x 16 x 16 f16 products summed in f32, in the same order) and the softmax done per lane as CUDA's fragment layout
// assigns it, so results match bit for bit. Include after defining HD. Workgroup (x, h): queries 64x' .. 64x' + 63
// of head h, x' = gridX - 1 - x (the longest tiles first, ~2% at 32K); subgroup w owns queries 16w .. 16w + 15.
// Query t (position step[0] + t) attends to cached keys 0 .. step[0] + t. out = softmax(q K^T * scale) V *
// sigmoid(gate), the gate at +HD per head of qg (qg may be null).
#extension GL_KHR_cooperative_matrix : require
#extension GL_KHR_memory_scope_semantics : require
#extension GL_KHR_shader_subgroup_vote : require
#extension GL_EXT_control_flow_attributes : require
layout(local_size_x = 128) in;
#include "common.glsl"
layout(buffer_reference, std430, buffer_reference_align = 16) buffer UV4 { uvec4 v[]; };
layout(buffer_reference, std430, buffer_reference_align = 16) buffer FV4 { vec4 v[]; };
layout(push_constant) uniform P { F32 q; U16 kc; U16 vc; F32 qg; F32 o; I32 step; uint t; uint nh; uint nkv; float scale; U32 qm; uint mw; } p;
// PQ: tile rows in uvec4 (8 halves).
const uint BQ = 64, BK = 32, PQ = HD / 8 + 1, PP = BK + 8;
#define ACC coopmat<float, gl_ScopeSubgroup, 16, 16, gl_MatrixUseAccumulator>
// The Q tile at the start, then the K and V tiles of each key block (BQ = 2 * BK rows either way).
shared uvec4 kvs[BQ * PQ];
shared float ss[4 * 16 * BK];      // scores of each subgroup; at the start the row and column index matrices
shared float16_t ps[4 * 16 * PP];  // softmax weights of each subgroup
shared float rs[4 * 16];           // per row: the rescale factor, at the end the sum l

void main() {
    uint pos0 = uint(p.step.v[0]), q0 = (gl_NumWorkGroups.x - 1 - gl_WorkGroupID.x) * BQ, h = gl_WorkGroupID.y, kvh = h / (p.nh / p.nkv), kvd = p.nkv * HD;
    uint tid = gl_LocalInvocationID.x, w = WARP, lane = LANE, g = lane >> 2, t4 = lane & 3;
    float ninf = uintBitsToFloat(0xff800000u);
    for (uint i = tid; i < BQ * HD / 8; i += 128) {
        uint r = i / (HD / 8), c = i % (HD / 8), o = ((q0 + r) * p.nh * HD + h * HD) / 4 + 2 * c;
        uvec4 u;
        [[unroll]] for (uint j = 0; j < 2; j++) {
            vec4 v = q0 + r < p.t ? FV4(uint64_t(p.q)).v[o + j] * p.scale : vec4(0.0);
            u[2 * j] = packFloat2x16(f16vec2(v.xy));
            u[2 * j + 1] = packFloat2x16(f16vec2(v.zw));
        }
        kvs[r * PQ + c] = u;
    }
    for (uint i = tid; i < 256; i += 128) {
        ss[i] = float(i / 16); ss[256 + i] = float(i % 16);
        ps[i] = float16_t(i / 16); ps[256 + i] = float16_t(i % 16);
    }
    barrier();
    // Accumulator element i of this invocation is at row ri[i], column ci[i] (the layout is the implementation's).
    ACC ri, ci;
    coopMatLoad(ri, ss, 0, 16, gl_CooperativeMatrixLayoutRowMajor);
    coopMatLoad(ci, ss, 256, 16, gl_CooperativeMatrixLayoutRowMajor);
    // nv: the layout of mma.sync (element i at row g + 8 (i >> 2), column 2 t4 + (i & 1) + 8 ((i >> 1) & 1)), so
    // scores and rescales stay in registers as in CUDA.
    bool nv = ri.length() == 8;
    [[unroll]] for (uint i = 0; i < ri.length(); i++) nv = nv && uint(ri[i]) == g + 8 * (i >> 2) && uint(ci[i]) == 2 * t4 + (i & 1) + 8 * ((i >> 1) & 1);
    nv = subgroupAll(nv);
    // nva: A matrices in mma.sync's layout too (element i at row g + 8 ((i >> 1) & 1), column 2 t4 + (i & 1) +
    // 8 (i >> 2)), so the softmax weights go into the PV products from registers.
    coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseA> ra, ca;
    coopMatLoad(ra, ps, 0, 16, gl_CooperativeMatrixLayoutRowMajor);
    coopMatLoad(ca, ps, 256, 16, gl_CooperativeMatrixLayoutRowMajor);
    bool nva = nv && ra.length() == 8;
    [[unroll]] for (uint i = 0; i < ra.length(); i++) nva = nva && uint(ra[i]) == g + 8 * ((i >> 1) & 1) && uint(ca[i]) == 2 * t4 + (i & 1) + 8 * (i >> 2);
    nva = subgroupAll(nva);
    barrier();  // ps is rewritten below
    coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseA> qa[HD / 16];
    [[unroll]] for (uint kk = 0; kk < HD / 16; kk++) coopMatLoad(qa[kk], kvs, w * 16 * PQ + kk * 2, PQ, gl_CooperativeMatrixLayoutRowMajor);
    ACC acc[HD / 16];
    [[unroll]] for (uint d = 0; d < HD / 16; d++) acc[d] = ACC(0.0);
    uint last = pos0 + min(q0 + BQ, p.t) - 1;  // last key any query of the tile sees
    uint qp[2] = {pos0 + q0 + w * 16 + g, pos0 + q0 + w * 16 + g + 8};
    float m[2] = {ninf, ninf}, ms[2];
    precise float l[2] = {0.0, 0.0};
    uint sb = w * 16 * BK, pb = w * 16 * PP, rb = w * 16;
    for (uint k0 = 0; k0 <= last; k0 += BK) {
        barrier();
        // All of a thread's loads, then its stores, so the loads overlap (#279). Rows past `last` load the row
        // `last` and store zeros: a select, not a branch around the loads (#276).
        const uint N = BK * HD / 8 / 128;
        uvec4 kl[N], vl[N];
        [[unroll]] for (uint n = 0; n < N; n++) {
            uint i = tid + n * 128, r = i / (HD / 8), c = i % (HD / 8), off = (min(k0 + r, last) * kvd + kvh * HD) / 8 + c, o = off * 8;
            kl[n] = KV_Q8 ? uvec4(ldkv4(p.kc, o, HD), ldkv4(p.kc, o + 4, HD)) : UV4(uint64_t(p.kc)).v[off];
            vl[n] = KV_Q8 ? uvec4(ldkv4(p.vc, o, HD), ldkv4(p.vc, o + 4, HD)) : UV4(uint64_t(p.vc)).v[off];
        }
        [[unroll]] for (uint n = 0; n < N; n++) {
            uint i = tid + n * 128, r = i / (HD / 8), c = i % (HD / 8);
            bool in_ = k0 + r <= last;
            kvs[r * PQ + c] = in_ ? kl[n] : uvec4(0);
            kvs[(BK + r) * PQ + c] = in_ ? vl[n] : uvec4(0);
        }
        barrier();
        ACC s0 = ACC(0.0), s1 = ACC(0.0);
        [[unroll]] for (uint kk = 0; kk < HD / 16; kk++) {
            coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseB> b0, b1;  // K^T: dims kk.. by keys 0.. / 16..
            coopMatLoad(b0, kvs, kk * 2, PQ, gl_CooperativeMatrixLayoutColumnMajor);
            coopMatLoad(b1, kvs, 16 * PQ + kk * 2, PQ, gl_CooperativeMatrixLayoutColumnMajor);
            s0 = coopMatMulAdd(qa[kk], b0, s0);
            s1 = coopMatMulAdd(qa[kk], b1, s1);
        }
        // CUDA's lane holds s[nt][e]: row g + 8 (e >> 1), key nt * 8 + 2 t4 + (e & 1).
        float s[4][4], mx[2] = {m[0], m[1]}, c[2];
        if (nv) {
            [[unroll]] for (uint i = 0; i < 8; i++) {
                uint nt = (i >> 1) & 1, e = (i & 1) + 2 * (i >> 2);
                s[nt][e] = s0[i];
                s[nt + 2][e] = s1[i];
            }
        } else {
            coopMatStore(s0, ss, sb, BK, gl_CooperativeMatrixLayoutRowMajor);
            coopMatStore(s1, ss, sb + 16, BK, gl_CooperativeMatrixLayoutRowMajor);
            subgroupMemoryBarrierShared();
            subgroupBarrier();
            [[unroll]] for (uint nt = 0; nt < 4; nt++)
                [[unroll]] for (uint e = 0; e < 4; e++) s[nt][e] = ss[sb + (g + 8 * (e >> 1)) * BK + nt * 8 + 2 * t4 + (e & 1)];
        }
        [[unroll]] for (uint nt = 0; nt < 4; nt++)
            [[unroll]] for (uint e = 0; e < 4; e++) {
                uint col = nt * 8 + 2 * t4 + (e & 1), r = e >> 1;
                float x = s[nt][e];
                if (k0 + col > qp[r] || (uint64_t(p.qm) != 0 && !qsa_bit(p.qm, p.mw, qp[r] - pos0, k0 + col))) x = ninf;
                s[nt][e] = x;
                mx[r] = max(mx[r], x);
            }
        [[unroll]] for (uint r = 0; r < 2; r++) {
            mx[r] = max(mx[r], subgroupShuffleXor(mx[r], 1));
            mx[r] = max(mx[r], subgroupShuffleXor(mx[r], 2));
            // A row's keys so far can all be masked (QSA): then subtract 0 so the weights are 0, not NaN.
            ms[r] = mx[r] == ninf ? 0.0 : mx[r];
            c[r] = expf_(m[r] - ms[r]);
            m[r] = mx[r];
        }
        [[unroll]] for (uint nt = 0; nt < 4; nt++)
            [[unroll]] for (uint e = 0; e < 4; e++) {
                uint r = e >> 1;
                float pe = expf_(s[nt][e] - ms[r]);
                // l *= c fuses into the first add, as nvcc compiles it.
                l[r] = nt == 0 && (e & 1) == 0 ? fma(l[r], c[r], pe) : l[r] + pe;
                s[nt][e] = pe;
                // The software f2h here: the hardware conversion took the shader from 168 to 239 registers.
                if (!nva) ps[pb + (g + 8 * r) * PP + nt * 8 + 2 * t4 + (e & 1)] = uint16BitsToHalf(uint16_t(f2h(pe)));
            }
        if (!nva) {
            if (!nv && t4 == 0) { rs[rb + g] = c[0]; rs[rb + g + 8] = c[1]; }
            subgroupMemoryBarrierShared();
            subgroupBarrier();
        }
        [[unroll]] for (uint d = 0; d < HD / 16; d++)
            [[unroll]] for (uint i = 0; i < acc[d].length(); i++) acc[d][i] *= nv ? c[i >> 2] : rs[rb + uint(ri[i])];
        [[unroll]] for (uint kb = 0; kb < BK / 16; kb++) {
            coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseA> pa;
            if (nva) {
                [[unroll]] for (uint i = 0; i < 8; i++) pa[i] = float16_t(s[2 * kb + (i >> 2)][i & 3]);
            } else coopMatLoad(pa, ps, pb + kb * 16, PP, gl_CooperativeMatrixLayoutRowMajor);
            [[unroll]] for (uint d = 0; d < HD / 16; d++) {
                coopmat<float16_t, gl_ScopeSubgroup, 16, 16, gl_MatrixUseB> vb;
                coopMatLoad(vb, kvs, (BK + kb * 16) * PQ + d * 2, PQ, gl_CooperativeMatrixLayoutRowMajor);
                acc[d] = coopMatMulAdd(pa, vb, acc[d]);
            }
        }
    }
    [[unroll]] for (uint r = 0; r < 2; r++) {
        l[r] += subgroupShuffleXor(l[r], 1);
        l[r] += subgroupShuffleXor(l[r], 2);
    }
    subgroupBarrier();
    if (t4 == 0) { rs[rb + g] = l[0]; rs[rb + g + 8] = l[1]; }
    subgroupMemoryBarrierShared();
    subgroupBarrier();
    [[unroll]] for (uint d = 0; d < HD / 16; d++)
        [[unroll]] for (uint i = 0; i < acc[d].length(); i++) {
            uint row = uint(ri[i]), col = d * 16 + uint(ci[i]), t = q0 + w * 16 + row;
            if (t >= p.t) continue;
            float gate = uint64_t(p.qg) != 0 ? sigmoid(p.qg.v[t * p.nh * 2 * HD + h * 2 * HD + HD + col]) : 1.0;
            p.o.v[t * p.nh * HD + h * HD + col] = fdiv(acc[d][i], rs[rb + row]) * gate;
        }
}
