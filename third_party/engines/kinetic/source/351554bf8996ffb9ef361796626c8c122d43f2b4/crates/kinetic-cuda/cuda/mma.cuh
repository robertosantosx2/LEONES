#pragma once

#include "common.cuh"

// Integer tensor-core products. sm_80 and up have m16n8k32 and m16n8k16
// directly; Turing (sm_75) has only m8n8k16, and four of those (two for k16)
// cover the same fragments: rows g and g + 8 are the two halves of A and of
// the result, and the low and high k runs the two halves of A and B.

__device__ __forceinline__ void mma_k32(int (&d)[4], int a0, int a1, int a2, int a3, int b0,
                                        int b1) {
#if __CUDA_ARCH__ >= 800
    asm("mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, "
        "{%8,%9}, {%0,%1,%2,%3};"
        : "+r"(d[0]), "+r"(d[1]), "+r"(d[2]), "+r"(d[3])
        : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
#else
    asm("mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 {%0,%1}, {%2}, {%3}, {%0,%1};"
        : "+r"(d[0]), "+r"(d[1])
        : "r"(a0), "r"(b0));
    asm("mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 {%0,%1}, {%2}, {%3}, {%0,%1};"
        : "+r"(d[0]), "+r"(d[1])
        : "r"(a2), "r"(b1));
    asm("mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 {%0,%1}, {%2}, {%3}, {%0,%1};"
        : "+r"(d[2]), "+r"(d[3])
        : "r"(a1), "r"(b0));
    asm("mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 {%0,%1}, {%2}, {%3}, {%0,%1};"
        : "+r"(d[2]), "+r"(d[3])
        : "r"(a3), "r"(b1));
#endif
}

__device__ __forceinline__ void mma_k16(int (&d)[4], int a0, int a1, int b0) {
#if __CUDA_ARCH__ >= 800
    asm("mma.sync.aligned.m16n8k16.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5}, {%6}, "
        "{%0,%1,%2,%3};"
        : "+r"(d[0]), "+r"(d[1]), "+r"(d[2]), "+r"(d[3])
        : "r"(a0), "r"(a1), "r"(b0));
#else
    asm("mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 {%0,%1}, {%2}, {%3}, {%0,%1};"
        : "+r"(d[0]), "+r"(d[1])
        : "r"(a0), "r"(b0));
    asm("mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32 {%0,%1}, {%2}, {%3}, {%0,%1};"
        : "+r"(d[2]), "+r"(d[3])
        : "r"(a1), "r"(b0));
#endif
}

// d = a b + c in every element. Unlike the accumulating forms, d need not
// hold c beforehand, so a constant c costs no copies.
__device__ __forceinline__ void mma_k32_from(int (&d)[4], int a0, int a1, int a2, int a3, int b0,
                                             int b1, int c) {
#if __CUDA_ARCH__ >= 800
    asm("mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, "
        "{%8,%9}, {%10,%10,%10,%10};"
        : "=r"(d[0]), "=r"(d[1]), "=r"(d[2]), "=r"(d[3])
        : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1), "r"(c));
#else
    d[0] = d[1] = d[2] = d[3] = c;
    mma_k32(d, a0, a1, a2, a3, b0, b1);
#endif
}

__device__ __forceinline__ void mma_k16_from(int (&d)[4], int a0, int a1, int b0, int c) {
#if __CUDA_ARCH__ >= 800
    asm("mma.sync.aligned.m16n8k16.row.col.s32.s8.s8.s32 {%0,%1,%2,%3}, {%4,%5}, {%6}, "
        "{%7,%7,%7,%7};"
        : "=r"(d[0]), "=r"(d[1]), "=r"(d[2]), "=r"(d[3])
        : "r"(a0), "r"(a1), "r"(b0), "r"(c));
#else
    d[0] = d[1] = d[2] = d[3] = c;
    mma_k16(d, a0, a1, b0);
#endif
}

__device__ __forceinline__ unsigned shared_addr(const void* p) {
    return static_cast<unsigned>(__cvta_generic_to_shared(p));
}

// Four 8x8 matrices of 16-bit values from shared memory, lanes 8i .. 8i + 7
// giving the row addresses of matrix i; lane (g, t) receives elements 2t
// and 2t + 1 of row g of each, the layout of mma fragments.
__device__ __forceinline__ void ldsm_x4(unsigned (&r)[4], const void* p) {
    asm volatile("ldmatrix.sync.aligned.m8n8.x4.shared.b16 {%0,%1,%2,%3}, [%4];"
                 : "=r"(r[0]), "=r"(r[1]), "=r"(r[2]), "=r"(r[3])
                 : "r"(shared_addr(p)));
}

// The same of the transposed matrices.
__device__ __forceinline__ void ldsm_x4_trans(unsigned (&r)[4], const void* p) {
    asm volatile("ldmatrix.sync.aligned.m8n8.x4.trans.shared.b16 {%0,%1,%2,%3}, [%4];"
                 : "=r"(r[0]), "=r"(r[1]), "=r"(r[2]), "=r"(r[3])
                 : "r"(shared_addr(p)));
}

// Two floats rounded to f16, the first in the low half.
__device__ __forceinline__ unsigned pack_half2(float a, float b) {
    const __half2 h = __floats2half2_rn(a, b);
    return *reinterpret_cast<const unsigned*>(&h);
}

// The high f16 part of v and what is left over, as f16 bits.
__device__ __forceinline__ void split_half(float v, unsigned short& hi, unsigned short& lo) {
    const __half h = __float2half_rn(v);
    hi = __half_as_ushort(h);
    lo = __half_as_ushort(__float2half_rn(v - __half2float(h)));
}

// High and low parts of the pair (a, b) as two f16x2 words.
__device__ __forceinline__ void split_pair(float a, float b, unsigned& hi, unsigned& lo) {
    unsigned short ah, al, bh, bl;
    split_half(a, ah, al);
    split_half(b, bh, bl);
    hi = ah | (static_cast<unsigned>(bh) << 16);
    lo = al | (static_cast<unsigned>(bl) << 16);
}

// f16 products with f32 sums, m16n8k16: sm_80 and up have it directly,
// Turing as two m16n8k8.
__device__ __forceinline__ void mma_f16(float (&d)[4], unsigned a0, unsigned a1, unsigned a2,
                                        unsigned a3, unsigned b0, unsigned b1) {
#if __CUDA_ARCH__ >= 800
    asm("mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5,%6,%7}, "
        "{%8,%9}, {%0,%1,%2,%3};"
        : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3])
        : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
#else
    asm("mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5}, {%6}, "
        "{%0,%1,%2,%3};"
        : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3])
        : "r"(a0), "r"(a1), "r"(b0));
    asm("mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 {%0,%1,%2,%3}, {%4,%5}, {%6}, "
        "{%0,%1,%2,%3};"
        : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3])
        : "r"(a2), "r"(a3), "r"(b1));
#endif
}
