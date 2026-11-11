//! CPU products of expert matrices in the codebook formats (IQ2_XXS,
//! IQ2_XS, IQ3_XXS, IQ4_XS) and the K-quants (Q2_K to Q6_K) with [`Q8K`]
//! activations.
//!
//! A weight row is first unpacked into [`Unpacked`] blocks: 256 signed
//! 8-bit values, an integer multiplier per 16 and one f32 scale, and for
//! the K-quants with offsets an integer offset multiplier per 16 and an f32
//! offset scale, which is exactly the row's value. Every format then shares
//! one integer dot product, and a row unpacked once serves every token
//! routed to it. Each (row, token) value is computed the same way whatever
//! the batch, so a batched pass reproduces single tokens exactly.

#[cfg(target_arch = "x86_64")]
mod avx2;

use kinetic_cpu::Q8K;
use kinetic_quant::iq::{iq_signs, IQ2XS_GRID, IQ2XXS_GRID, IQ3XXS_GRID, IQ4NL_VALUES};
use kinetic_quant::TensorType;

mod kquant;

const QK: usize = 256;

/// One 256-value block of a weight row: the value at `i` is
/// `d * mul[i / 16] * qs[i] - dmin * mins[i / 16]`. Every unpacker sets
/// all of it but `mins` when `dmin` is zero, since blocks are reused.
#[derive(Clone, Copy)]
#[repr(C, align(32))]
pub struct Unpacked {
    pub qs: [i8; QK],
    pub mul: [i16; QK / 16],
    pub d: f32,
    /// Offsets, zero in the formats without them.
    pub mins: [i16; QK / 16],
    pub dmin: f32,
}

impl Default for Unpacked {
    fn default() -> Self {
        Unpacked {
            qs: [0; QK],
            mul: [0; QK / 16],
            d: 0.0,
            mins: [0; QK / 16],
            dmin: 0.0,
        }
    }
}

/// Whether [`unpack`] handles weights of type `ty`.
pub fn supported(ty: TensorType) -> bool {
    matches!(
        ty,
        TensorType::IQ2XXS
            | TensorType::IQ2XS
            | TensorType::IQ3XXS
            | TensorType::IQ4XS
            | TensorType::Q2K
            | TensorType::Q3K
            | TensorType::Q4K
            | TensorType::Q5K
            | TensorType::Q6K
    )
}

type BlockFn = fn(&[u8], &mut Unpacked);

/// Unpacks a row of `ty` blocks into `out`, one [`Unpacked`] per block.
pub fn unpack(ty: TensorType, row: &[u8], out: &mut [Unpacked]) {
    #[cfg(target_arch = "x86_64")]
    if let Some(block) = avx2::unpack_block(ty) {
        return each_block(ty, row, out, block);
    }
    unpack_scalar(ty, row, out);
}

fn unpack_scalar(ty: TensorType, row: &[u8], out: &mut [Unpacked]) {
    let block: BlockFn = match ty {
        TensorType::IQ2XXS => iq2_xxs,
        TensorType::IQ2XS => iq2_xs,
        TensorType::IQ3XXS => iq3_xxs,
        TensorType::IQ4XS => iq4_xs,
        TensorType::Q2K => kquant::q2_k,
        TensorType::Q3K => kquant::q3_k,
        TensorType::Q4K => kquant::q4_k,
        TensorType::Q5K => kquant::q5_k,
        TensorType::Q6K => kquant::q6_k,
        _ => panic!("{ty} has no unpacked form"),
    };
    each_block(ty, row, out, block);
}

fn each_block(ty: TensorType, row: &[u8], out: &mut [Unpacked], block: BlockFn) {
    for (src, dst) in row.chunks_exact(ty.block_bytes()).zip(out) {
        block(src, dst);
    }
}

fn half(b: &[u8]) -> f32 {
    half::f16::from_le_bytes([b[0], b[1]]).to_f32()
}

fn put_signed(dst: &mut [i8], grid: &[u8], signs: u8) {
    for (j, (d, &g)) in dst.iter_mut().zip(grid).enumerate() {
        *d = if signs >> j & 1 == 1 {
            -(g as i8)
        } else {
            g as i8
        };
    }
}

// Values are d * (0.5 + s) / 4 * grid * sign = d / 8 * (2s + 1) * grid * sign
// with a 4-bit s per 32 values.
fn iq2_xxs(src: &[u8], out: &mut Unpacked) {
    for (b, dst) in out.qs.chunks_exact_mut(32).enumerate() {
        let a = iq2_xxs_aux(src, b);
        for (l, dst) in dst.chunks_exact_mut(8).enumerate() {
            let signs = iq_signs((a >> (7 * l)) as u8);
            put_signed(dst, &IQ2XXS_GRID[src[2 + 8 * b + l] as usize], signs);
        }
    }
    iq2_xxs_scales(src, out);
}

/// The four sign indices and the scale of the `b`-th 32 values.
fn iq2_xxs_aux(src: &[u8], b: usize) -> u32 {
    u32::from_le_bytes(src[6 + 8 * b..10 + 8 * b].try_into().unwrap())
}

fn iq2_xxs_scales(src: &[u8], out: &mut Unpacked) {
    out.d = half(src) * 0.125;
    out.dmin = 0.0;
    for b in 0..QK / 32 {
        let mul = 2 * (iq2_xxs_aux(src, b) >> 28) as i16 + 1;
        out.mul[2 * b..2 * b + 2].fill(mul);
    }
}

// Values are d * (0.5 + s) / 4 * grid * sign = d / 8 * (2s + 1) * grid * sign
// with a 4-bit s per 16 values.
fn iq2_xs(src: &[u8], out: &mut Unpacked) {
    for (g, dst) in out.qs.chunks_exact_mut(8).enumerate() {
        let q = iq2_xs_index(src, g);
        put_signed(
            dst,
            &IQ2XS_GRID[(q & 511) as usize],
            iq_signs((q >> 9) as u8),
        );
    }
    iq2_xs_scales(src, out);
}

/// The codebook and sign index of the `g`-th eight values.
fn iq2_xs_index(src: &[u8], g: usize) -> u16 {
    u16::from_le_bytes([src[2 + 2 * g], src[3 + 2 * g]])
}

fn iq2_xs_scales(src: &[u8], out: &mut Unpacked) {
    out.d = half(src) * 0.125;
    out.dmin = 0.0;
    let scales = &src[66..74];
    for (m, mul) in out.mul.iter_mut().enumerate() {
        *mul = 2 * (scales[m / 2] >> (4 * (m % 2)) & 0xf) as i16 + 1;
    }
}

// Values are d * (0.5 + s) / 2 * grid * sign = d / 4 * (2s + 1) * grid * sign
// with a 4-bit s per 32 values.
fn iq3_xxs(src: &[u8], out: &mut Unpacked) {
    let qs = &src[2..66];
    for (b, dst) in out.qs.chunks_exact_mut(32).enumerate() {
        let a = iq3_xxs_aux(src, b);
        for (l, dst) in dst.chunks_exact_mut(8).enumerate() {
            let signs = iq_signs((a >> (7 * l)) as u8);
            let grid = [
                IQ3XXS_GRID[qs[8 * b + 2 * l] as usize],
                IQ3XXS_GRID[qs[8 * b + 2 * l + 1] as usize],
            ];
            put_signed(dst, grid.as_flattened(), signs);
        }
    }
    iq3_xxs_scales(src, out);
}

/// The four sign indices and the scale of the `b`-th 32 values.
fn iq3_xxs_aux(src: &[u8], b: usize) -> u32 {
    u32::from_le_bytes(src[66 + 4 * b..70 + 4 * b].try_into().unwrap())
}

fn iq3_xxs_scales(src: &[u8], out: &mut Unpacked) {
    out.d = half(src) * 0.25;
    out.dmin = 0.0;
    for b in 0..QK / 32 {
        let mul = 2 * (iq3_xxs_aux(src, b) >> 28) as i16 + 1;
        out.mul[2 * b..2 * b + 2].fill(mul);
    }
}

// Values are d * (s - 32) * table[code] with a 6-bit s per 32 values.
fn iq4_xs(src: &[u8], out: &mut Unpacked) {
    let qs = &src[8..136];
    for (b, dst) in out.qs.chunks_exact_mut(32).enumerate() {
        for (j, &q) in qs[16 * b..16 * b + 16].iter().enumerate() {
            dst[j] = IQ4NL_VALUES[(q & 0xf) as usize];
            dst[j + 16] = IQ4NL_VALUES[(q >> 4) as usize];
        }
    }
    iq4_xs_scales(src, out);
}

fn iq4_xs_scales(src: &[u8], out: &mut Unpacked) {
    out.d = half(src);
    out.dmin = 0.0;
    let scales_h = u16::from_le_bytes([src[2], src[3]]);
    let scales_l = &src[4..8];
    for b in 0..QK / 32 {
        let lo = scales_l[b / 2] >> (4 * (b % 2)) & 0xf;
        let hi = (scales_h >> (2 * b) & 3) as u8;
        out.mul[2 * b..2 * b + 2].fill((lo | hi << 4) as i16 - 32);
    }
}

/// The dot product of an unpacked row with a quantized activation vector.
pub fn dot(row: &[Unpacked], x: &Q8K) -> f32 {
    debug_assert_eq!(row.len(), x.blocks());
    #[cfg(target_arch = "x86_64")]
    if let Some(dot) = avx2::dot_fn() {
        return dot(row, x);
    }
    dot_scalar(row, x)
}

/// The dot product of a packed row of `ty` with `x`, equal to [`dot`] of
/// the unpacked row, for rows used once.
pub fn packed_dot(ty: TensorType, row: &[u8], x: &Q8K) -> f32 {
    #[cfg(target_arch = "x86_64")]
    if let Some(dot) = avx2::packed_dot_fn(ty) {
        return dot(row, x);
    }
    let mut unpacked = vec![Unpacked::default(); x.blocks()];
    unpack(ty, row, &mut unpacked);
    dot(&unpacked, x)
}

fn dot_scalar(row: &[Unpacked], x: &Q8K) -> f32 {
    row.iter().enumerate().fold(0.0, |acc, (b, w)| {
        let q = &x.qs[b * QK..][..QK];
        let sum: i32 =
            w.qs.chunks_exact(16)
                .zip(q.chunks_exact(16))
                .zip(&w.mul)
                .map(|((w, q), &m)| {
                    m as i32
                        * w.iter()
                            .zip(q)
                            .map(|(&a, &b)| a as i32 * b as i32)
                            .sum::<i32>()
                })
                .sum();
        accumulate(acc, w, x, b, sum)
    })
}

/// One step of every expert dot product: blocks are added in order, each
/// as its exact integer sum times the product of the two block scales,
/// then, in a block with offsets, less the exact integer sum of the offsets
/// times the inputs' sums, times the product of the offset scale and the
/// input scale. The device kernels take the same steps, so a row's value
/// never depends on where it ran.
#[inline]
fn accumulate(acc: f32, w: &Unpacked, x: &Q8K, b: usize, sum: i32) -> f32 {
    let acc = acc + w.d * x.d[b] * sum as f32;
    if w.dmin == 0.0 {
        return acc;
    }
    let offsets: i32 = w
        .mins
        .iter()
        .zip(&x.bsums[b * 16..][..16])
        .map(|(&m, &s)| m as i32 * s as i32)
        .sum();
    acc - w.dmin * x.d[b] * offsets as f32
}

/// Where the f16 scales of a block of `ty` sit, so tests can give random
/// blocks finite ones.
#[cfg(test)]
pub(crate) fn scale_offsets(ty: TensorType) -> &'static [usize] {
    match ty {
        TensorType::Q2K => &[80, 82],
        TensorType::Q3K => &[108],
        TensorType::Q4K | TensorType::Q5K => &[0, 2],
        TensorType::Q6K => &[208],
        _ => &[0],
    }
}

/// `x * sigmoid(x)` from a fixed approximation of `exp`, written out
/// operation by operation so the device computes the same bits.
pub fn silu(x: f32) -> f32 {
    x / (1.0 + exp(-x))
}

/// `e^x` to about one unit in the last place: `x = n ln 2 + r` with `|r|`
/// at most `ln 2 / 2`, a degree-6 polynomial for `e^r`, and `2^n` from the
/// exponent bits.
fn exp(x: f32) -> f32 {
    const LOG2_E: f32 = std::f32::consts::LOG2_E;
    // ln 2 split so that `n * LN2_HI` is exact for every reachable `n`.
    const LN2_HI: f32 = 0.693_359_4;
    const LN2_LO: f32 = -2.121_944_4e-4;
    const P: [f32; 6] = [
        1.987_569_1e-4,
        1.398_199_9e-3,
        8.333_452e-3,
        4.166_579_6e-2,
        0.166_666_66,
        0.5,
    ];
    if x > 88.0 {
        return f32::INFINITY;
    }
    if x < -87.0 {
        return 0.0;
    }
    let n = (x * LOG2_E).round();
    let r = x - n * LN2_HI - n * LN2_LO;
    let p = P[1..].iter().fold(P[0], |p, &c| p * r + c);
    let e = p * (r * r) + r + 1.0;
    e * f32::from_bits(((n as i32 + 127) as u32) << 23)
}

#[cfg(test)]
mod tests {
    use kinetic_quant::dequantize;

    use super::*;

    struct Lcg(u64);

    impl Lcg {
        fn next(&mut self) -> u32 {
            self.0 = self
                .0
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            (self.0 >> 33) as u32
        }
    }

    fn random_row(ty: TensorType, blocks: usize, rng: &mut Lcg) -> Vec<u8> {
        let mut row: Vec<u8> = (0..blocks * ty.block_bytes())
            .map(|_| rng.next() as u8)
            .collect();
        for b in row.chunks_exact_mut(ty.block_bytes()) {
            for &at in scale_offsets(ty) {
                let d = half::f16::from_f32((rng.next() % 1000) as f32 * 1e-5);
                b[at..at + 2].copy_from_slice(&d.to_le_bytes());
            }
        }
        row
    }

    const TYPES: [TensorType; 9] = [
        TensorType::IQ2XXS,
        TensorType::IQ2XS,
        TensorType::IQ3XXS,
        TensorType::IQ4XS,
        TensorType::Q2K,
        TensorType::Q3K,
        TensorType::Q4K,
        TensorType::Q5K,
        TensorType::Q6K,
    ];

    #[test]
    fn unpacked_rows_hold_the_reference_values() {
        let mut rng = Lcg(7);
        for ty in TYPES {
            let row = random_row(ty, 3, &mut rng);
            let mut want = vec![0.0; 3 * QK];
            dequantize(ty, &row, &mut want).unwrap();
            let mut fast = vec![Unpacked::default(); 3];
            unpack(ty, &row, &mut fast);
            let mut slow = vec![Unpacked::default(); 3];
            unpack_scalar(ty, &row, &mut slow);
            for (a, b) in fast.iter().zip(&slow) {
                assert_eq!((a.qs, a.mul, a.d), (b.qs, b.mul, b.d), "{ty}");
            }
            for (i, &want) in want.iter().enumerate() {
                let w = &fast[i / QK];
                let g = i % QK / 16;
                let got = w.d * w.mul[g] as f32 * w.qs[i % QK] as f32 - w.dmin * w.mins[g] as f32;
                assert!(
                    (got - want).abs() <= want.abs() * 1e-5 + 1e-7,
                    "{ty} value {i}"
                );
            }
        }
    }

    #[test]
    fn simd_dot_matches_scalar() {
        let mut rng = Lcg(11);
        // One buffer for every type, as the products reuse theirs.
        let mut u = vec![Unpacked::default(); 8];
        for ty in TYPES {
            let row = random_row(ty, 8, &mut rng);
            unpack(ty, &row, &mut u);
            let x: Vec<f32> = (0..8 * QK)
                .map(|_| (rng.next() % 2001) as f32 / 1000.0 - 1.0)
                .collect();
            let x = Q8K::quantize(&x);
            let want = dot_scalar(&u, &x).to_bits();
            assert_eq!(dot(&u, &x).to_bits(), want, "{ty}");
            assert_eq!(packed_dot(ty, &row, &x).to_bits(), want, "{ty}");
        }
    }

    #[test]
    fn exp_is_within_two_ulps() {
        for i in -8700..8800 {
            let x = i as f32 * 0.01 + 0.003;
            let (got, want) = (exp(x), (x as f64).exp());
            let ulp = f32::EPSILON as f64 * want;
            assert!(
                (got as f64 - want).abs() <= 2.0 * ulp,
                "exp({x}) = {got}, want {want}"
            );
        }
        assert_eq!(exp(-100.0), 0.0);
        assert_eq!(exp(100.0), f32::INFINITY);
        assert_eq!(silu(-100.0), -0.0);
    }
}
