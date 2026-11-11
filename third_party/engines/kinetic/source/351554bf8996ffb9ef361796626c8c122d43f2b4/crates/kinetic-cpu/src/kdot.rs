//! Dot products of one quantized weight row with a quantized activation
//! vector: a [`Q8K`] for the K-quants, whose rows are whole 256-value
//! blocks, and a [`Q8`] for the 32-value formats (Q8_0, Q4_0), so that each
//! weight block meets an activation block with its own scale, as in the
//! reference implementations.
//!
//! The scalar functions are the definition; the SIMD versions must agree
//! with them up to f32 summation order.
//!
//! Every SIMD kernel, whether it handles one token or a tile of tokens,
//! reduces each block to exact integer sums and then folds them into the
//! result with the same f32 operations in the same order. A value therefore
//! never depends on the batch it was computed in, which is what lets a
//! speculative pass reproduce plain decoding exactly.

#[cfg(target_arch = "x86_64")]
mod avx2;
#[cfg(target_arch = "x86_64")]
mod avx2_iq_s;
#[cfg(target_arch = "x86_64")]
mod avx2_legacy;
#[cfg(target_arch = "x86_64")]
mod avx2_low_bit;
#[cfg(target_arch = "x86_64")]
mod avx2_tile;
mod legacy;
mod low_bit;
mod pq2;
#[cfg(target_arch = "x86_64")]
mod unpack32;

use half::f16;

use crate::q8::{Q8Group, Q8};
use crate::q8k::{Q8KGroup, GROUP, Q8K};
use kinetic_quant::TensorType;

/// One weight row times one activation vector of type `X`.
pub type DotFn<X> = fn(&[u8], &X) -> f32;

/// Dot products of one weight row with `N` activation vectors at once, so
/// the row is unpacked once for all of them.
pub type DotNFn<X, const N: usize> = fn(&[u8], [&X; N]) -> [f32; N];

/// The fastest available K-quant dot product for `ty`.
pub fn kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    #[cfg(target_arch = "x86_64")]
    if avx2::available() {
        return avx2::kernel(ty)
            .or_else(|| avx2_low_bit::kernel(ty))
            .or_else(|| avx2_iq_s::kernel(ty))
            .or_else(|| pq2::avx2::kernel(ty));
    }
    scalar_kernel(ty)
}

/// The `N`-vector form of [`kernel`], where a SIMD version exists.
pub fn kernel_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8K, N>> {
    #[cfg(target_arch = "x86_64")]
    if avx2::available() {
        return avx2::kernel_n::<N>(ty)
            .or_else(|| avx2_low_bit::kernel_n::<N>(ty))
            .or_else(|| avx2_iq_s::kernel_n::<N>(ty))
            .or_else(|| pq2::avx2::kernel_n::<N>(ty));
    }
    let _ = ty;
    None
}

/// The fastest available dot product for a 32-value format `ty`.
pub fn kernel32(ty: TensorType) -> Option<DotFn<Q8>> {
    #[cfg(target_arch = "x86_64")]
    if avx2::available() {
        return avx2::kernel32(ty).or_else(|| avx2_legacy::kernel(ty));
    }
    scalar_kernel32(ty)
}

/// The `N`-vector form of [`kernel32`], where a SIMD version exists.
pub fn kernel32_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Q8, N>> {
    #[cfg(target_arch = "x86_64")]
    if avx2::available() {
        return avx2::kernel32_n::<N>(ty).or_else(|| avx2_legacy::kernel_n::<N>(ty));
    }
    let _ = ty;
    None
}

/// Unpacked weight blocks, the form tile buffers hold.
pub trait Block: Copy {
    /// An all-zero block, for allocating buffers that unpacking fills.
    const ZERO: Self;
}

/// One 256-value K-quant block with every value unpacked to a byte, the
/// form the tile kernels broadcast from.
#[derive(Clone, Copy)]
#[repr(C)]
pub struct Unpacked {
    /// Unsigned weights in element order.
    pub q: [u8; 256],
    /// The scale of each 32-value (Q4_K, Q5_K) or 16-value (Q6_K, Q2_K, Q3_K)
    /// group, in both i16 halves.
    pub sc: [i32; 16],
    /// Adjacent pairs of the factors applied to the activation sums: mins
    /// for Q4_K, Q5_K and Q2_K, scales for Q6_K and Q3_K; low half first.
    pub pairs: [i32; 8],
    pub d: f32,
    pub dmin: f32,
}

impl Block for Unpacked {
    const ZERO: Unpacked = Unpacked {
        q: [0; 256],
        sc: [0; 16],
        pairs: [0; 8],
        d: 0.0,
        dmin: 0.0,
    };
}

/// One block of a 32-value format, unpacked for the tile kernels.
#[derive(Clone, Copy)]
#[repr(C)]
pub struct Unpacked32 {
    /// Unsigned codes a fixed offset above the weights, in element order:
    /// Q4_0, Q4_1, Q5_0, Q5_1 and MXFP4. Q8_0 keeps its signed weights here.
    pub q: [u8; 32],
    /// IQ4_NL: the integer weights as i16.
    pub w: [i16; 32],
    pub d: f32,
    /// The offset of Q4_1 and Q5_1.
    pub m: f32,
}

impl Block for Unpacked32 {
    const ZERO: Unpacked32 = Unpacked32 {
        q: [0; 32],
        w: [0; 32],
        d: 0.0,
        m: 0.0,
    };
}

/// Rows handled together by [`TileKernel::dot4`].
pub const TILE_ROWS: usize = 4;

/// The products of `R` rows with one group, one lane per token.
pub type RowsByGroup<const R: usize> = [[f32; GROUP]; R];

/// Kernels for a tile of weight rows unpacked to blocks `U` times one
/// group `G` of interleaved activation vectors.
pub struct TileKernel<U, G> {
    /// Unpacks one weight row into one `U` per block.
    pub unpack: fn(&[u8], &mut [U]),
    /// [`TILE_ROWS`] rows times the group.
    pub dot4: fn([&[U]; TILE_ROWS], &G) -> RowsByGroup<TILE_ROWS>,
    /// One row times the group, for the rows left over.
    pub dot1: fn(&[U], &G) -> [f32; GROUP],
}

// A derive would require `U: Clone` and `G: Clone`; the fields are plain
// function pointers either way.
impl<U, G> Clone for TileKernel<U, G> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<U, G> Copy for TileKernel<U, G> {}

/// The tile kernel for a K-quant `ty`, where one exists.
pub fn tile_kernel(ty: TensorType) -> Option<TileKernel<Unpacked, Q8KGroup>> {
    #[cfg(target_arch = "x86_64")]
    if avx2::available() {
        return avx2_tile::kernel(ty);
    }
    let _ = ty;
    None
}

/// The tile kernel for a 32-value format `ty`, where one exists.
pub fn tile_kernel32(ty: TensorType) -> Option<TileKernel<Unpacked32, Q8Group>> {
    #[cfg(target_arch = "x86_64")]
    if avx2::available() {
        return avx2_tile::kernel32(ty);
    }
    let _ = ty;
    None
}

pub fn scalar_kernel(ty: TensorType) -> Option<DotFn<Q8K>> {
    match ty {
        TensorType::Q4K => Some(q4_k),
        TensorType::Q5K => Some(q5_k),
        TensorType::Q6K => Some(q6_k),
        _ => low_bit::kernel(ty).or_else(|| pq2::kernel(ty)),
    }
}

pub fn scalar_kernel32(ty: TensorType) -> Option<DotFn<Q8>> {
    match ty {
        TensorType::Q8_0 => Some(q8_0),
        TensorType::Q4_0 => Some(q4_0),
        _ => legacy::kernel(ty),
    }
}

fn half(b: &[u8]) -> f32 {
    f16::from_le_bytes([b[0], b[1]]).to_f32()
}

/// Unpacks the eight 6-bit (scale, min) pairs shared by Q4_K and Q5_K.
///
/// Bytes 0..4 hold scales 0..3 and bytes 4..8 mins 0..3 in their low six
/// bits; bytes 8..12 hold the low nibbles of scales and mins 4..7, whose top
/// two bits sit in the spare high bits of bytes 0..8. Working on 32-bit
/// words handles four sub-blocks per operation.
pub(crate) fn scales_mins(q: &[u8]) -> ([u8; 8], [u8; 8]) {
    let word = |i: usize| u32::from_le_bytes(q[4 * i..4 * i + 4].try_into().unwrap());
    let (a, b, c) = (word(0), word(1), word(2));
    let low6 = 0x3F3F_3F3F;
    let top2 = |w: u32| ((w >> 6) & 0x0303_0303) << 4;
    let sc_hi = (c & 0x0F0F_0F0F) | top2(a);
    let m_hi = ((c >> 4) & 0x0F0F_0F0F) | top2(b);
    let join = |lo: u32, hi: u32| {
        let mut out = [0u8; 8];
        out[..4].copy_from_slice(&lo.to_le_bytes());
        out[4..].copy_from_slice(&hi.to_le_bytes());
        out
    };
    (join(a & low6, sc_hi), join(b & low6, m_hi))
}

fn mins_term(m: &[u8; 8], bsums: &[i16]) -> i32 {
    (0..8)
        .map(|s| m[s] as i32 * (bsums[2 * s] as i32 + bsums[2 * s + 1] as i32))
        .sum()
}

fn q4_k(row: &[u8], x: &Q8K) -> f32 {
    let mut sum = 0.0;
    for (b, blk) in row.chunks_exact(144).enumerate() {
        let (dx, q8, bsums) = x.block(b);
        let (sc, m) = scales_mins(&blk[4..16]);
        let qs = &blk[16..];
        let mut sumi = 0i32;
        for j in 0..4 {
            let (lo, hi) = qs[32 * j..][..32]
                .iter()
                .zip(&q8[64 * j..][..64])
                .zip(&q8[64 * j + 32..][..32])
                .fold((0i32, 0i32), |(lo, hi), ((&q, &y0), &y1)| {
                    (
                        lo + (q & 0xF) as i32 * y0 as i32,
                        hi + (q >> 4) as i32 * y1 as i32,
                    )
                });
            sumi += sc[2 * j] as i32 * lo + sc[2 * j + 1] as i32 * hi;
        }
        sum +=
            dx * (half(&blk[0..2]) * sumi as f32 - half(&blk[2..4]) * mins_term(&m, bsums) as f32);
    }
    sum
}

fn q5_k(row: &[u8], x: &Q8K) -> f32 {
    let mut sum = 0.0;
    for (b, blk) in row.chunks_exact(176).enumerate() {
        let (dx, q8, bsums) = x.block(b);
        let (sc, m) = scales_mins(&blk[4..16]);
        let (qh, qs) = (&blk[16..48], &blk[48..]);
        let mut sumi = 0i32;
        for j in 0..4 {
            let (mut lo, mut hi) = (0i32, 0i32);
            for l in 0..32 {
                let q = qs[32 * j + l];
                let q_lo = (q & 0xF) | (((qh[l] >> (2 * j)) & 1) << 4);
                let q_hi = (q >> 4) | (((qh[l] >> (2 * j + 1)) & 1) << 4);
                lo += q_lo as i32 * q8[64 * j + l] as i32;
                hi += q_hi as i32 * q8[64 * j + 32 + l] as i32;
            }
            sumi += sc[2 * j] as i32 * lo + sc[2 * j + 1] as i32 * hi;
        }
        sum +=
            dx * (half(&blk[0..2]) * sumi as f32 - half(&blk[2..4]) * mins_term(&m, bsums) as f32);
    }
    sum
}

// Each 16-value group of a Q6_K block has its own scale, in element order.
fn q6_k(row: &[u8], x: &Q8K) -> f32 {
    let mut sum = 0.0;
    for (b, blk) in row.chunks_exact(210).enumerate() {
        let (dx, q8, _) = x.block(b);
        let (ql, qh, sc) = (&blk[..128], &blk[128..192], &blk[192..208]);
        let mut sumi = 0i32;
        for n in 0..2 {
            let (ql, qh) = (&ql[64 * n..], &qh[32 * n..]);
            for l in 0..32 {
                let q = [
                    (ql[l] & 0xF) | ((qh[l] & 3) << 4),
                    (ql[l + 32] & 0xF) | (((qh[l] >> 2) & 3) << 4),
                    (ql[l] >> 4) | (((qh[l] >> 4) & 3) << 4),
                    (ql[l + 32] >> 4) | (((qh[l] >> 6) & 3) << 4),
                ];
                for (g, &q) in q.iter().enumerate() {
                    let e = 128 * n + 32 * g + l;
                    sumi += sc[e / 16] as i8 as i32 * (q as i32 - 32) * q8[e] as i32;
                }
            }
        }
        sum += dx * half(&blk[208..210]) * sumi as f32;
    }
    sum
}

fn q8_0(row: &[u8], x: &Q8) -> f32 {
    let mut sum = 0.0;
    for (k, blk) in row.chunks_exact(34).enumerate() {
        let y = &x.qs[32 * k..][..32];
        let sumi: i32 = blk[2..]
            .iter()
            .zip(y)
            .map(|(&w, &y)| w as i8 as i32 * y as i32)
            .sum();
        sum += x.d[k] * half(blk) * sumi as f32;
    }
    sum
}

// Q4_0 stores q + 8; the 8 comes back out through the block sums.
fn q4_0(row: &[u8], x: &Q8) -> f32 {
    let mut sum = 0.0;
    for (k, blk) in row.chunks_exact(18).enumerate() {
        let y = &x.qs[32 * k..][..32];
        let sumi: i32 = blk[2..]
            .iter()
            .enumerate()
            .map(|(l, &q)| (q & 0xF) as i32 * y[l] as i32 + (q >> 4) as i32 * y[l + 16] as i32)
            .sum();
        let offset = 8 * x.sums[k] as i32;
        sum += x.d[k] * half(blk) * (sumi - offset) as f32;
    }
    sum
}

#[cfg(test)]
pub(crate) mod tests;
