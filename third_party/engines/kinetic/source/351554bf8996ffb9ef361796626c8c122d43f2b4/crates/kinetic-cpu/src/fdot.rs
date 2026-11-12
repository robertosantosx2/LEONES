//! Dot products of f16 or bf16 weight rows with f32 activations.
//!
//! Every (row, token) product has one eight-lane accumulator that takes the
//! columns in order through fused multiply-adds, then adds its lanes in a
//! fixed order and last the columns past the final multiple of eight. A
//! product is therefore the same whichever rows and tokens share a call.

use kinetic_quant::TensorType;

/// Most rows per call of [`dots`].
pub const ROWS: usize = 4;

/// Most tokens per call of [`dots`].
pub const TOKENS: usize = 3;

/// Whether `ty` has a kernel here on this machine.
pub fn supported(ty: TensorType) -> bool {
    #[cfg(target_arch = "x86_64")]
    if matches!(ty, TensorType::F16 | TensorType::BF16) {
        return avx2::available();
    }
    let _ = ty;
    false
}

/// `out[r][t] = rows[r] . xs[t]` for one or [`ROWS`] rows of a
/// [`supported`] type and one to [`TOKENS`] activation vectors.
pub fn dots(ty: TensorType, rows: &[&[u8]], xs: &[&[f32]]) -> [[f32; TOKENS]; ROWS] {
    assert!(supported(ty), "no kernel for {ty}");
    let cols = xs[0].len();
    assert!(rows.iter().all(|r| r.len() == 2 * cols));
    assert!(xs.iter().all(|x| x.len() == cols));
    #[cfg(target_arch = "x86_64")]
    {
        // SAFETY: `supported` confirmed the target features, and the
        // lengths were just checked.
        unsafe { avx2::dots(ty == TensorType::BF16, rows, xs) }
    }
    #[cfg(not(target_arch = "x86_64"))]
    unreachable!()
}

#[cfg(target_arch = "x86_64")]
mod avx2 {
    use std::arch::x86_64::*;

    use half::{bf16, f16};

    use super::{ROWS, TOKENS};

    pub fn available() -> bool {
        is_x86_feature_detected!("avx2")
            && is_x86_feature_detected!("fma")
            && is_x86_feature_detected!("f16c")
    }

    /// [`super::dots`] for checked lengths.
    #[target_feature(enable = "avx2,fma,f16c")]
    pub unsafe fn dots(bf16: bool, rows: &[&[u8]], xs: &[&[f32]]) -> [[f32; TOKENS]; ROWS] {
        if bf16 {
            by_rows::<true>(rows, xs)
        } else {
            by_rows::<false>(rows, xs)
        }
    }

    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    unsafe fn by_rows<const BF16: bool>(rows: &[&[u8]], xs: &[&[f32]]) -> [[f32; TOKENS]; ROWS] {
        match *rows {
            [a, b, c, d] => by_tokens::<BF16, 4>([a, b, c, d], xs),
            [a] => by_tokens::<BF16, 1>([a], xs),
            _ => panic!("{} rows", rows.len()),
        }
    }

    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    unsafe fn by_tokens<const BF16: bool, const R: usize>(
        rows: [&[u8]; R],
        xs: &[&[f32]],
    ) -> [[f32; TOKENS]; ROWS] {
        let mut out = [[0.0; TOKENS]; ROWS];
        let mut copy = |v: &[[f32; TOKENS]]| out[..R].copy_from_slice(v);
        match *xs {
            [a, b, c] => copy(&tile::<BF16, R, 3>(rows, [a, b, c])),
            [a, b] => copy(&pad(tile::<BF16, R, 2>(rows, [a, b]))),
            [a] => copy(&pad(tile::<BF16, R, 1>(rows, [a]))),
            _ => panic!("{} tokens", xs.len()),
        }
        out
    }

    fn pad<const R: usize, const T: usize>(v: [[f32; T]; R]) -> [[f32; TOKENS]; R] {
        v.map(|v| std::array::from_fn(|t| v.get(t).copied().unwrap_or(0.0)))
    }

    /// Eight weights from `p` as f32.
    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    unsafe fn widen<const BF16: bool>(p: *const u8) -> __m256 {
        let v = _mm_loadu_si128(p as *const __m128i);
        if BF16 {
            _mm256_castsi256_ps(_mm256_slli_epi32(_mm256_cvtepu16_epi32(v), 16))
        } else {
            _mm256_cvtph_ps(v)
        }
    }

    fn widen1<const BF16: bool>(p: &[u8]) -> f32 {
        let bits = u16::from_le_bytes([p[0], p[1]]);
        if BF16 {
            bf16::from_bits(bits).to_f32()
        } else {
            f16::from_bits(bits).to_f32()
        }
    }

    #[inline]
    #[target_feature(enable = "avx2,fma,f16c")]
    unsafe fn hsum(v: __m256) -> f32 {
        let s = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
        let s = _mm_add_ps(s, _mm_movehl_ps(s, s));
        _mm_cvtss_f32(_mm_add_ss(s, _mm_movehdup_ps(s)))
    }

    #[target_feature(enable = "avx2,fma,f16c")]
    unsafe fn tile<const BF16: bool, const R: usize, const T: usize>(
        rows: [&[u8]; R],
        xs: [&[f32]; T],
    ) -> [[f32; T]; R] {
        let cols = xs[0].len();
        let body = cols / 8 * 8;
        // Raw pointers keep bounds checks, and the registers they need, out
        // of the loop; `super::dots` checked every length.
        let (w, x) = (rows.map(<[u8]>::as_ptr), xs.map(<[f32]>::as_ptr));
        let mut acc = [[_mm256_setzero_ps(); T]; R];
        for c in (0..body).step_by(8) {
            let mut wv = [_mm256_setzero_ps(); R];
            for (wv, w) in wv.iter_mut().zip(w) {
                *wv = widen::<BF16>(w.add(2 * c));
            }
            for t in 0..T {
                let xv = _mm256_loadu_ps(x[t].add(c));
                for r in 0..R {
                    acc[r][t] = _mm256_fmadd_ps(wv[r], xv, acc[r][t]);
                }
            }
        }
        let mut out = [[0.0; T]; R];
        for r in 0..R {
            for t in 0..T {
                let mut tail = 0.0;
                for c in body..cols {
                    tail += widen1::<BF16>(&rows[r][2 * c..]) * xs[t][c];
                }
                out[r][t] = hsum(acc[r][t]) + tail;
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use half::{bf16, f16};

    use super::*;
    use crate::kdot::tests::Lcg;

    /// Every row and token combination gives the same value, and that
    /// value is the dot product of the widened weights.
    #[test]
    fn products_do_not_depend_on_their_neighbours() {
        let mut rng = Lcg(5);
        for ty in [TensorType::F16, TensorType::BF16] {
            if !supported(ty) {
                return;
            }
            for cols in [8, 13, 64, 77] {
                let weights: Vec<Vec<f32>> = (0..ROWS)
                    .map(|_| (0..cols).map(|_| rng.f32()).collect())
                    .collect();
                let rows: Vec<Vec<u8>> = weights
                    .iter()
                    .map(|w| {
                        w.iter()
                            .flat_map(|&v| match ty {
                                TensorType::F16 => f16::from_f32(v).to_le_bytes(),
                                _ => bf16::from_f32(v).to_le_bytes(),
                            })
                            .collect()
                    })
                    .collect();
                let xs: Vec<Vec<f32>> = (0..TOKENS)
                    .map(|_| (0..cols).map(|_| rng.f32() * 3.0).collect())
                    .collect();
                let rows: Vec<&[u8]> = rows.iter().map(|r| &r[..]).collect();
                let xs: Vec<&[f32]> = xs.iter().map(|x| &x[..]).collect();
                let full = dots(ty, &rows, &xs);
                for r in 0..ROWS {
                    for t in 0..TOKENS {
                        let one = dots(ty, &rows[r..r + 1], &xs[t..t + 1])[0][0];
                        assert_eq!(full[r][t], one, "{ty} {cols} row {r} token {t}");
                        let mut w = vec![0.0; cols];
                        kinetic_quant::dequantize(ty, rows[r], &mut w).unwrap();
                        let exact: f64 = w
                            .iter()
                            .zip(xs[t])
                            .map(|(&a, &b)| a as f64 * b as f64)
                            .sum();
                        assert!((one as f64 - exact).abs() < 1e-4 * cols as f64);
                    }
                }
            }
        }
    }
}
