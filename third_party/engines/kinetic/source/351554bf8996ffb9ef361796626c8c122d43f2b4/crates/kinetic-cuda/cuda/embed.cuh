#pragma once

#include "gemv_iq.cuh"
#include "gemv_legacy.cuh"
#include "gemv_low_k.cuh"
#include "kquant.cuh"

// Weight types as the host numbers them in `EmbedArgs::type`.
enum WeightType : unsigned {
    W_F32,
    W_F16,
    W_Q8_0,
    W_Q4_K,
    W_Q5_K,
    W_Q6_K,
    W_Q4_1,
    W_Q5_0,
    W_Q5_1,
    W_IQ4_NL,
    W_MXFP4,
    W_Q2_K,
    W_Q3_K,
    W_IQ3_S,
    W_IQ2_S,
    W_IQ1_S,
    W_IQ1_M,
    W_TQ1_0,
    W_TQ2_0,
    W_Q4_0,
    W_PQ2_0,
};

__device__ __forceinline__ float k4_dequant(const uint8_t* p, unsigned e, unsigned q) {
    const unsigned s = e / 32;
    const uint32_t* words = reinterpret_cast<const uint32_t*>(p);
    const int2 sm = k4_scale_min(s, words[1], words[2], words[3]);
    const float2 dm = half2_bits(words[0]);
    return dm.x * static_cast<float>(sm.x) * static_cast<float>(q) -
           dm.y * static_cast<float>(sm.y);
}

// Element e of row `row` of a matrix in its device layout (see layout.rs);
// `total` is the matrix's block count.
__device__ float dequant(unsigned type, const uint8_t* w, size_t total, size_t row, unsigned cols,
                         unsigned e) {
    switch (type) {
        case W_F32:
            return reinterpret_cast<const float*>(w)[row * cols + e];
        case W_F16:
            return __half2float(reinterpret_cast<const __half*>(w)[row * cols + e]);
        case W_Q8_0: {
            const size_t blk = row * (cols / 32) + e / 32;
            const float d = __half2float(reinterpret_cast<const __half*>(w + total * 32)[blk]);
            return d * static_cast<float>(reinterpret_cast<const int8_t*>(w)[blk * 32 + e % 32]);
        }
        case W_Q4_K: {
            const uint8_t* p = w + (row * (cols / 256) + e / 256) * 144;
            const unsigned i = e % 256;
            const uint8_t byte = p[16 + 32 * (i / 64) + i % 32];
            return k4_dequant(p, i, (i / 32) % 2 ? byte >> 4 : byte & 15);
        }
        case W_Q5_K: {
            const uint8_t* p = w + (row * (cols / 256) + e / 256) * 176;
            const unsigned i = e % 256;
            const uint8_t byte = p[48 + 32 * (i / 64) + i % 32];
            const unsigned high = (p[16 + i % 32] >> (i / 32)) & 1;
            return k4_dequant(p, i, ((i / 32) % 2 ? byte >> 4 : byte & 15) | high << 4);
        }
        case W_Q4_0:
        case W_Q4_1:
        case W_Q5_0:
        case W_Q5_1:
        case W_IQ4_NL:
        case W_MXFP4: {
            const Legacy32 x{w, total, row * (cols / 32) + e / 32, e % 32};
            switch (type) {
                case W_Q4_0: return q4_0_element(x);
                case W_Q4_1: return q4_1_element(x);
                case W_Q5_0: return q5_0_element(x);
                case W_Q5_1: return q5_1_element(x);
                case W_IQ4_NL: return iq4_nl_element(x);
                default: return mxfp4_element(x);
            }
        }
        case W_Q2_K:
            return q2_k_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_Q3_K:
            return q3_k_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_IQ3_S:
            return iq3_s_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_IQ2_S:
            return iq2_s_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_IQ1_S:
            return iq1_s_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_IQ1_M:
            return iq1_m_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_TQ1_0:
            return tq1_0_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_TQ2_0:
            return tq2_0_element(w, total, row * (cols / 256) + e / 256, e % 256);
        case W_PQ2_0: {
            const size_t blk = row * (cols / 128) + e / 128;
            const unsigned i = e % 128;
            const int q = w[blk * 32 + i / 4] >> (2 * (i % 4)) & 3;
            const float d = __half2float(reinterpret_cast<const __half*>(w + total * 32)[blk]);
            return d * static_cast<float>(q - 1);
        }
        default: {
            const size_t blk = row * (cols / 256) + e / 256;
            const unsigned i = e % 256;
            const unsigned n = i / 128, g = (i % 128) / 32, l = i % 32;
            const uint8_t ql = w[blk * 128 + 64 * n + l + 32 * (g & 1)];
            const uint8_t qh = w[total * 128 + blk * 64 + 32 * n + l];
            const int q = ((g < 2 ? ql & 15 : ql >> 4) | ((qh >> (2 * g)) & 3) << 4) - 32;
            const int8_t scale = reinterpret_cast<const int8_t*>(w + total * 192)[blk * 16 + i / 16];
            const float d = __half2float(reinterpret_cast<const __half*>(w + total * 208)[blk]);
            return d * static_cast<float>(scale) * static_cast<float>(q);
        }
    }
}

struct EmbedArgs {
    const uint8_t* table;
    // [first position, token ids...]
    const unsigned* batch;
    float* out;
    size_t total;
    unsigned type;
    unsigned cols;
    unsigned rows;
    float scale;
};

// out[t] = scale * table row of token t, or zeros for ids past the table; grid
// (tokens, cols / blockDim).
extern "C" __global__ void embed(EmbedArgs a) {
    const unsigned e = blockIdx.y * blockDim.x + threadIdx.x;
    if (e >= a.cols) return;
    const unsigned token = a.batch[1 + blockIdx.x];
    a.out[static_cast<size_t>(blockIdx.x) * a.cols + e] =
        token < a.rows ? a.scale * dequant(a.type, a.table, a.total, token, a.cols, e) : 0.0f;
}
