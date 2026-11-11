use half::{bf16, f16};
use kinetic_quant::{dequantize, TensorType};

use super::*;

pub(crate) struct Lcg(pub u64);

impl Lcg {
    pub fn next(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) as u32
    }

    pub fn f32(&mut self) -> f32 {
        self.next() as f32 / u32::MAX as f32 * 2.0 - 1.0
    }
}

/// Random blocks with sane f16 scales at the positions each format uses;
/// for f16 and bf16, random values in [-1, 1].
pub(crate) fn random_row(ty: TensorType, blocks: usize, rng: &mut Lcg) -> Vec<u8> {
    match ty {
        TensorType::F16 => (0..blocks)
            .flat_map(|_| f16::from_f32(rng.f32()).to_le_bytes())
            .collect(),
        TensorType::BF16 => (0..blocks)
            .flat_map(|_| bf16::from_f32(rng.f32()).to_le_bytes())
            .collect(),
        _ => {
            let row: Vec<u8> = (0..blocks * ty.block_bytes())
                .map(|_| rng.next() as u8)
                .collect();
            with_scales(ty, row, rng)
        }
    }
}

/// Blocks whose every quantized value and scale is at its largest, the
/// worst case for the i16 partial sums of the kernels.
pub(crate) fn extreme_row(ty: TensorType, blocks: usize, rng: &mut Lcg) -> Vec<u8> {
    with_scales(ty, vec![0xFF; blocks * ty.block_bytes()], rng)
}

fn with_scales(ty: TensorType, mut row: Vec<u8>, rng: &mut Lcg) -> Vec<u8> {
    use TensorType::*;
    let size = ty.block_bytes();
    let scale_offsets: &[usize] = match ty {
        Q4K | Q5K | Q4_1 | Q5_1 => &[0, 2],
        Q6K => &[208],
        Q8_0 | Q4_0 | Q5_0 | IQ4NL | IQ3S | IQ2S | IQ1S | PQ2_0 => &[0],
        Q2K => &[80, 82],
        Q3K => &[108],
        TQ1_0 => &[52],
        TQ2_0 => &[64],
        MXFP4 | IQ1M => &[],
        _ => unreachable!(),
    };
    for blk in row.chunks_exact_mut(size) {
        let mut scale = || f16::from_f32(0.001 + rng.f32().abs() * 0.01);
        for &o in scale_offsets {
            blk[o..o + 2].copy_from_slice(&scale().to_le_bytes());
        }
        match ty {
            MXFP4 => blk[0] = 118 + (rng.next() % 8) as u8,
            // The IQ1_M scale is spread over the top nibbles of its last
            // four u16 words.
            IQ1M => {
                let bits = scale().to_bits();
                for (i, b) in [49, 51, 53, 55].into_iter().enumerate() {
                    blk[b] = (blk[b] & 0x0F) | ((bits >> (4 * i)) as u8 & 0x0F) << 4;
                }
            }
            _ => {}
        }
    }
    row
}

/// The two activation formats, so the checks below cover both families of
/// kernels.
trait Activation: Sized {
    type Group;
    type Block: super::Block;
    fn quantize(x: &[f32]) -> Self;
    /// Value `i` as the kernels see it, `q * d`.
    fn value(&self, i: usize) -> f32;
    fn scalar(ty: TensorType) -> Option<DotFn<Self>>;
    fn fast(ty: TensorType) -> Option<DotFn<Self>>;
    fn fast_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Self, N>>;
    fn group(xs: &[Self]) -> Self::Group;
    fn tile(ty: TensorType) -> Option<TileKernel<Self::Block, Self::Group>>;
}

impl Activation for Q8K {
    type Group = Q8KGroup;
    type Block = Unpacked;
    fn quantize(x: &[f32]) -> Self {
        Q8K::quantize(x)
    }
    fn value(&self, i: usize) -> f32 {
        self.qs[i] as f32 * self.d[i / 256]
    }
    fn scalar(ty: TensorType) -> Option<DotFn<Self>> {
        scalar_kernel(ty)
    }
    fn fast(ty: TensorType) -> Option<DotFn<Self>> {
        kernel(ty)
    }
    fn fast_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Self, N>> {
        kernel_n(ty)
    }
    fn group(xs: &[Self]) -> Q8KGroup {
        Q8KGroup::new(xs)
    }
    fn tile(ty: TensorType) -> Option<TileKernel<Unpacked, Q8KGroup>> {
        tile_kernel(ty)
    }
}

impl Activation for Q8 {
    type Group = Q8Group;
    type Block = Unpacked32;
    fn quantize(x: &[f32]) -> Self {
        Q8::quantize(x)
    }
    fn value(&self, i: usize) -> f32 {
        self.qs[i] as f32 * self.d[i / 32]
    }
    fn scalar(ty: TensorType) -> Option<DotFn<Self>> {
        scalar_kernel32(ty)
    }
    fn fast(ty: TensorType) -> Option<DotFn<Self>> {
        kernel32(ty)
    }
    fn fast_n<const N: usize>(ty: TensorType) -> Option<DotNFn<Self, N>> {
        kernel32_n(ty)
    }
    fn group(xs: &[Self]) -> Q8Group {
        Q8Group::new(xs)
    }
    fn tile(ty: TensorType) -> Option<TileKernel<Unpacked32, Q8Group>> {
        tile_kernel32(ty)
    }
}

/// About `spans` times 256 values; 32-value rows deliberately end in the
/// middle of a 256-value span and of a chunk of the one-row kernels.
fn row_len(ty: TensorType, spans: usize) -> usize {
    spans * 256 + if ty.block_len() == 32 { 96 } else { 0 }
}

fn check<X: Activation>(ty: TensorType) {
    let mut rng = Lcg(ty as u64 + 1);
    let n = row_len(ty, 10);
    for _ in 0..20 {
        let row = random_row(ty, n / ty.block_len(), &mut rng);
        let x: Vec<f32> = (0..n).map(|_| rng.f32() * 3.0).collect();
        let q = X::quantize(&x);

        let mut w = vec![0.0; n];
        dequantize(ty, &row, &mut w).unwrap();
        let exact: f64 = (0..n).map(|i| w[i] as f64 * q.value(i) as f64).sum();
        let magnitude: f64 = (0..n)
            .map(|i| (w[i] as f64 * q.value(i) as f64).abs())
            .sum();

        let scalar = X::scalar(ty).unwrap()(&row, &q) as f64;
        let fast = X::fast(ty).unwrap();
        if let Some(dot4) = X::fast_n::<4>(ty) {
            let others: Vec<X> = (1..4)
                .map(|s| X::quantize(&x.iter().map(|v| v * s as f32).collect::<Vec<_>>()))
                .collect();
            let four = dot4(&row, [&q, &others[0], &others[1], &others[2]]);
            for (i, xq) in [&q, &others[0], &others[1], &others[2]]
                .into_iter()
                .enumerate()
            {
                assert_eq!(four[i], fast(&row, xq), "{ty} dot4 lane {i}");
            }
            let two = X::fast_n::<2>(ty).unwrap()(&row, [&q, &others[0]]);
            let three = X::fast_n::<3>(ty).unwrap()(&row, [&q, &others[0], &others[1]]);
            assert_eq!(&two[..], &four[..2], "{ty} dot2");
            assert_eq!(&three[..], &four[..3], "{ty} dot3");
        }
        let fast = fast(&row, &q) as f64;
        let tol = 1e-5 * magnitude + 1e-6;
        assert!(
            (scalar - exact).abs() <= tol,
            "{ty} scalar {scalar} vs exact {exact}"
        );
        assert!(
            (fast - scalar).abs() <= tol,
            "{ty} fast {fast} vs scalar {scalar}"
        );
    }
}

#[test]
fn q4_k_matches_dequantized_dot() {
    check::<Q8K>(TensorType::Q4K);
}

#[test]
fn q5_k_matches_dequantized_dot() {
    check::<Q8K>(TensorType::Q5K);
}

#[test]
fn q6_k_matches_dequantized_dot() {
    check::<Q8K>(TensorType::Q6K);
}

#[test]
fn q8_0_matches_dequantized_dot() {
    check::<Q8>(TensorType::Q8_0);
}

#[test]
fn q4_0_matches_dequantized_dot() {
    check::<Q8>(TensorType::Q4_0);
}

#[test]
fn pq2_0_matches_dequantized_dot() {
    check::<Q8K>(TensorType::PQ2_0);
    let scalar = scalar_kernel(TensorType::PQ2_0).unwrap();
    let fast = kernel(TensorType::PQ2_0).unwrap();
    let mut rng = Lcg(5);
    for row in [
        random_row(TensorType::PQ2_0, 16, &mut rng),
        extreme_row(TensorType::PQ2_0, 16, &mut rng),
    ] {
        let xs: [Q8K; 3] = std::array::from_fn(|_| {
            Q8K::quantize(&(0..2048).map(|_| rng.f32() * 3.0).collect::<Vec<_>>())
        });
        let want = xs.each_ref().map(|x| scalar(&row, x));
        assert_eq!(fast(&row, &xs[0]).to_bits(), want[0].to_bits());
        if let Some(fast3) = kernel_n::<3>(TensorType::PQ2_0) {
            let got = fast3(&row, [&xs[0], &xs[1], &xs[2]]);
            assert_eq!(got.map(f32::to_bits), want.map(f32::to_bits));
        }
    }
}

#[test]
fn formats_below_four_bits_match_dequantized_dot() {
    for ty in [
        TensorType::Q2K,
        TensorType::Q3K,
        TensorType::TQ1_0,
        TensorType::TQ2_0,
        TensorType::IQ3S,
        TensorType::IQ2S,
        TensorType::IQ1S,
        TensorType::IQ1M,
    ] {
        check::<Q8K>(ty);
    }
}

#[test]
fn more_32_value_formats_match_dequantized_dot() {
    for ty in [
        TensorType::Q4_1,
        TensorType::Q5_0,
        TensorType::Q5_1,
        TensorType::IQ4NL,
        TensorType::MXFP4,
    ] {
        check::<Q8>(ty);
    }
}

/// The tile kernels give exactly the one-row kernel's value for every row
/// and token, wherever the token sits in its group and however full the
/// group is.
fn check_tile<X: Activation>(ty: TensorType) {
    let Some(tile) = X::tile(ty) else {
        return;
    };
    let dot = X::fast(ty).unwrap();
    let mut rng = Lcg(ty as u64 + 7);
    let cols = row_len(ty, 11);
    let blocks = cols / ty.block_len();
    let rows: Vec<Vec<u8>> = (0..TILE_ROWS + 1)
        .map(|r| {
            if r == 0 {
                extreme_row(ty, blocks, &mut rng)
            } else {
                random_row(ty, blocks, &mut rng)
            }
        })
        .collect();
    let unpacked: Vec<Vec<X::Block>> = rows
        .iter()
        .map(|row| {
            let mut u = vec![<X::Block as super::Block>::ZERO; blocks];
            (tile.unpack)(row, &mut u);
            u
        })
        .collect();
    let mut xs: Vec<X> = (0..2 * GROUP)
        .map(|_| X::quantize(&(0..cols).map(|_| rng.f32() * 4.0).collect::<Vec<_>>()))
        .collect();
    xs[0] = X::quantize(&vec![1.0; cols]);
    xs[1] = X::quantize(&vec![-1.0; cols]);
    for (start, len) in [
        (0, GROUP),
        (3, GROUP),
        (1, 5),
        (5, 3),
        (6, 4),
        (2, 2),
        (GROUP, 1),
    ] {
        let group = X::group(&xs[start..start + len]);
        let quad: [&[X::Block]; TILE_ROWS] = std::array::from_fn(|r| &unpacked[r][..]);
        let four = (tile.dot4)(quad, &group);
        for (r, row) in rows.iter().enumerate() {
            let lanes = if r < TILE_ROWS {
                four[r]
            } else {
                (tile.dot1)(&unpacked[r], &group)
            };
            for t in 0..len {
                assert_eq!(
                    lanes[t],
                    dot(row, &xs[start + t]),
                    "{ty} row {r} token {t} of {len} from {start}"
                );
            }
            assert!(lanes[len..].iter().all(|&v| v == 0.0), "{ty} padding");
        }
    }
}

#[test]
fn q4_k_tile_matches_one_row_kernel() {
    check_tile::<Q8K>(TensorType::Q4K);
}

#[test]
fn q5_k_tile_matches_one_row_kernel() {
    check_tile::<Q8K>(TensorType::Q5K);
}

#[test]
fn q6_k_tile_matches_one_row_kernel() {
    check_tile::<Q8K>(TensorType::Q6K);
}

#[test]
fn q2_k_and_q3_k_tiles_match_one_row_kernel() {
    check_tile::<Q8K>(TensorType::Q2K);
    check_tile::<Q8K>(TensorType::Q3K);
}

#[test]
fn q8_0_tile_matches_one_row_kernel() {
    check_tile::<Q8>(TensorType::Q8_0);
}

#[test]
fn q4_0_tile_matches_one_row_kernel() {
    check_tile::<Q8>(TensorType::Q4_0);
}

#[test]
fn more_32_value_tiles_match_one_row_kernel() {
    for ty in [
        TensorType::Q4_1,
        TensorType::Q5_0,
        TensorType::Q5_1,
        TensorType::IQ4NL,
        TensorType::MXFP4,
    ] {
        check_tile::<Q8>(ty);
    }
}

#[test]
fn scales_mins_match_reference_unpacking() {
    let q: Vec<u8> = (0..12).map(|i| (i * 53 + 7) as u8).collect();
    let (sc, m) = scales_mins(&q);
    for j in 0..8 {
        let (s, mm) = if j < 4 {
            (q[j] & 63, q[j + 4] & 63)
        } else {
            (
                (q[j + 4] & 0xF) | ((q[j - 4] >> 6) << 4),
                (q[j + 4] >> 4) | ((q[j] >> 6) << 4),
            )
        };
        assert_eq!((sc[j], m[j]), (s, mm), "sub-block {j}");
    }
}
