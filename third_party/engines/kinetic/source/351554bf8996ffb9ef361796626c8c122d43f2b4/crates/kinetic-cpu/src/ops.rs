//! Element-wise and reduction kernels on f32 vectors.
//!
//! [`dot`], [`dots`] and [`axpy`] have AVX2 versions picked at run time that
//! perform the operations of the portable versions lane for lane, without
//! fusing, and so give identical values.

/// The inner product of two vectors of the same length.
pub fn dot(a: &[f32], b: &[f32]) -> f32 {
    dots([a], b)[0]
}

/// `[dot(a[0], b), ..., dot(a[N - 1], b)]`, value for value, with the `N`
/// products interleaved so that one pass over `b` serves all of them.
pub fn dots<const N: usize>(a: [&[f32]; N], b: &[f32]) -> [f32; N] {
    for a in a {
        assert_eq!(a.len(), b.len());
    }
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2") {
        // SAFETY: AVX2 was just detected and the lengths checked.
        return unsafe { avx2::dots(a, b) };
    }
    dots_portable(a, b)
}

/// `y += a * x`, element by element.
pub fn axpy(y: &mut [f32], a: f32, x: &[f32]) {
    assert_eq!(y.len(), x.len());
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2") {
        // SAFETY: AVX2 was just detected and the lengths checked.
        return unsafe { avx2::axpy(y, a, x) };
    }
    y.iter_mut().zip(x).for_each(|(y, x)| *y += a * x);
}

/// `y = y * a + b * x`, element by element, rounding each product.
pub fn scale_axpy(y: &mut [f32], a: f32, b: f32, x: &[f32]) {
    assert_eq!(y.len(), x.len());
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2") {
        // SAFETY: AVX2 was just detected and the lengths checked.
        return unsafe { avx2::scale_axpy(y, a, b, x) };
    }
    y.iter_mut().zip(x).for_each(|(y, x)| *y = *y * a + b * x);
}

/// `out[n][s] = dot(a[n], rows[s])` for every `s < out[n].len()`, where row
/// `s` is the `a[n].len()` values at `s * stride` of `rows`.
pub fn dot_rows<const N: usize>(a: [&[f32]; N], rows: &[f32], stride: usize, out: [&mut [f32]; N]) {
    let (len, count) = (a[0].len(), out[0].len());
    assert!(a.iter().all(|a| a.len() == len) && out.iter().all(|o| o.len() == count));
    if count == 0 {
        return;
    }
    assert!(rows.len() >= (count - 1) * stride + len);
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2") {
        // SAFETY: AVX2 was just detected and the lengths checked.
        return unsafe { avx2::dot_rows(a, rows, stride, out) };
    }
    let mut out = out;
    for s in 0..count {
        let d = dots_portable(a, &rows[s * stride..][..len]);
        for (out, d) in out.iter_mut().zip(d) {
            out[s] = d;
        }
    }
}

/// `y += w[s] * rows[s]` for every `s` in order, where row `s` is the
/// `y.len()` values at `s * stride` of `rows`: [`axpy`] once per row, with
/// the same operations on every element.
pub fn axpy_rows(y: &mut [f32], w: &[f32], rows: &[f32], stride: usize) {
    if w.is_empty() {
        return;
    }
    assert!(rows.len() >= (w.len() - 1) * stride + y.len());
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2") {
        // SAFETY: AVX2 was just detected and the lengths checked.
        return unsafe { avx2::axpy_rows(y, w, rows, stride) };
    }
    for (s, &w) in w.iter().enumerate() {
        let row = &rows[s * stride..][..y.len()];
        y.iter_mut().zip(row).for_each(|(y, x)| *y += w * x);
    }
}

/// Eight running sums per product, one per lane of a vector register, added
/// in lane order at the end, then the products past the last multiple of
/// eight in order.
fn dots_portable<const N: usize>(a: [&[f32]; N], b: &[f32]) -> [f32; N] {
    let body = b.len() / 8 * 8;
    let mut acc = [[0.0f32; 8]; N];
    for c in (0..body).step_by(8) {
        for (acc, a) in acc.iter_mut().zip(a) {
            for i in 0..8 {
                acc[i] += a[c + i] * b[c + i];
            }
        }
    }
    std::array::from_fn(|n| finish(acc[n], &a[n][body..], &b[body..]))
}

fn finish(lanes: [f32; 8], a: &[f32], b: &[f32]) -> f32 {
    let tail: f32 = a.iter().zip(b).map(|(a, b)| a * b).sum();
    lanes.iter().sum::<f32>() + tail
}

#[cfg(target_arch = "x86_64")]
mod avx2 {
    use std::arch::x86_64::*;

    /// [`super::dots_portable`] for slices of `b`'s length.
    #[inline]
    #[target_feature(enable = "avx2")]
    pub unsafe fn dots<const N: usize>(a: [&[f32]; N], b: &[f32]) -> [f32; N] {
        let body = b.len() / 8 * 8;
        let mut acc = [_mm256_setzero_ps(); N];
        for c in (0..body).step_by(8) {
            let y = _mm256_loadu_ps(b[c..c + 8].as_ptr());
            for (acc, a) in acc.iter_mut().zip(a) {
                let x = _mm256_loadu_ps(a[c..c + 8].as_ptr());
                *acc = _mm256_add_ps(*acc, _mm256_mul_ps(x, y));
            }
        }
        let mut out = [0.0; N];
        for (n, out) in out.iter_mut().enumerate() {
            let mut lanes = [0.0; 8];
            _mm256_storeu_ps(lanes.as_mut_ptr(), acc[n]);
            *out = super::finish(lanes, &a[n][body..], &b[body..]);
        }
        out
    }

    /// [`super::dot_rows`] for checked lengths.
    #[target_feature(enable = "avx2")]
    pub unsafe fn dot_rows<const N: usize>(
        a: [&[f32]; N],
        rows: &[f32],
        stride: usize,
        mut out: [&mut [f32]; N],
    ) {
        let len = a[0].len();
        for s in 0..out[0].len() {
            let d = dots(a, &rows[s * stride..][..len]);
            for (out, d) in out.iter_mut().zip(d) {
                out[s] = d;
            }
        }
    }

    /// [`super::axpy_rows`] for checked lengths. Columns are taken 64 at
    /// a time so that their sums stay in registers across all rows.
    #[target_feature(enable = "avx2")]
    pub unsafe fn axpy_rows(y: &mut [f32], w: &[f32], rows: &[f32], stride: usize) {
        let body = y.len() / 8 * 8;
        let mut c = 0;
        while c + 64 <= body {
            columns::<8>(&mut y[c..], w, &rows[c..], stride);
            c += 64;
        }
        while c < body {
            columns::<1>(&mut y[c..], w, &rows[c..], stride);
            c += 8;
        }
        for (s, &w) in w.iter().enumerate() {
            let row = &rows[s * stride..][..y.len()];
            for (y, x) in y[body..].iter_mut().zip(&row[body..]) {
                *y += w * x;
            }
        }
    }

    /// The first `8 * K` columns of [`axpy_rows`].
    #[inline]
    #[target_feature(enable = "avx2")]
    unsafe fn columns<const K: usize>(y: &mut [f32], w: &[f32], rows: &[f32], stride: usize) {
        let mut acc = [_mm256_setzero_ps(); K];
        for (k, acc) in acc.iter_mut().enumerate() {
            *acc = _mm256_loadu_ps(y[8 * k..][..8].as_ptr());
        }
        for (s, &w) in w.iter().enumerate() {
            let row = &rows[s * stride..][..8 * K];
            let w = _mm256_set1_ps(w);
            for (k, acc) in acc.iter_mut().enumerate() {
                let x = _mm256_loadu_ps(row[8 * k..][..8].as_ptr());
                *acc = _mm256_add_ps(*acc, _mm256_mul_ps(w, x));
            }
        }
        for (k, acc) in acc.iter().enumerate() {
            _mm256_storeu_ps(y[8 * k..][..8].as_mut_ptr(), *acc);
        }
    }

    /// `y += a * x` for slices of the same length.
    #[target_feature(enable = "avx2")]
    pub unsafe fn axpy(y: &mut [f32], a: f32, x: &[f32]) {
        let body = y.len() / 8 * 8;
        let av = _mm256_set1_ps(a);
        for c in (0..body).step_by(8) {
            let p = y[c..c + 8].as_mut_ptr();
            let v = _mm256_mul_ps(av, _mm256_loadu_ps(x[c..c + 8].as_ptr()));
            _mm256_storeu_ps(p, _mm256_add_ps(_mm256_loadu_ps(p), v));
        }
        for (y, x) in y[body..].iter_mut().zip(&x[body..]) {
            *y += a * x;
        }
    }

    /// `y = y * a + b * x` for slices of the same length.
    #[target_feature(enable = "avx2")]
    pub unsafe fn scale_axpy(y: &mut [f32], a: f32, b: f32, x: &[f32]) {
        let body = y.len() / 8 * 8;
        let (av, bv) = (_mm256_set1_ps(a), _mm256_set1_ps(b));
        for c in (0..body).step_by(8) {
            let p = y[c..c + 8].as_mut_ptr();
            let v = _mm256_mul_ps(bv, _mm256_loadu_ps(x[c..c + 8].as_ptr()));
            _mm256_storeu_ps(p, _mm256_add_ps(_mm256_mul_ps(_mm256_loadu_ps(p), av), v));
        }
        for (y, x) in y[body..].iter_mut().zip(&x[body..]) {
            *y = *y * a + b * x;
        }
    }
}

/// `x = x / rms(x) * w`, in place.
pub fn rms_norm(x: &mut [f32], w: &[f32], eps: f32) {
    let mean_sq = x.iter().map(|v| v * v).sum::<f32>() / x.len() as f32;
    let scale = 1.0 / (mean_sq + eps).sqrt();
    for (v, w) in x.iter_mut().zip(w) {
        *v *= scale * w;
    }
}

/// `x = x / max(|x|, eps)`, in place.
pub fn l2_norm(x: &mut [f32], eps: f32) {
    let norm = x.iter().map(|v| v * v).sum::<f32>().sqrt();
    let scale = 1.0 / norm.max(eps);
    x.iter_mut().for_each(|v| *v *= scale);
}

pub fn silu(x: f32) -> f32 {
    x / (1.0 + (-x).exp())
}

pub fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + (-x).exp())
}

pub fn softplus(x: f32) -> f32 {
    // Same cutoff as the reference implementations; above it exp overflows
    // and softplus(x) == x to f32 precision anyway.
    if x > 20.0 {
        x
    } else {
        x.exp().ln_1p()
    }
}

/// Rotates the first `dims` values of `x` by position `pos`, pairing
/// element `i` with `i + dims / 2` (the "NeoX" layout).
pub fn rope_neox(x: &mut [f32], dims: usize, pos: usize, base: f32) {
    let half = dims / 2;
    for i in 0..half {
        let theta = pos as f32 * base.powf(-((2 * i) as f32) / dims as f32);
        let (sin, cos) = theta.sin_cos();
        let (a, b) = (x[i], x[i + half]);
        x[i] = a * cos - b * sin;
        x[i + half] = a * sin + b * cos;
    }
}

/// Numerically stable softmax, in place.
pub fn softmax(x: &mut [f32]) {
    let max = x.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let mut sum = 0.0;
    for v in x.iter_mut() {
        *v = (*v - max).exp();
        sum += *v;
    }
    x.iter_mut().for_each(|v| *v /= sum);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dots_match_dot() {
        for len in [0, 5, 8, 64, 77] {
            let v = |s: usize| -> Vec<f32> {
                (0..len)
                    .map(|i| ((i * 31 + s * 17) % 23) as f32 / 7.0 - 1.5)
                    .collect()
            };
            let (a, b, c, k) = (v(1), v(2), v(3), v(4));
            let got = dots([&a, &b, &c], &k);
            let want = [dot(&a, &k), dot(&b, &k), dot(&c, &k)];
            assert_eq!(got.map(f32::to_bits), want.map(f32::to_bits));
        }
    }

    /// The run-time picked versions agree bit for bit with the portable ones.
    #[test]
    fn wide_builds_match_baseline() {
        let v = |s: u32| -> Vec<f32> {
            (0..203u32)
                .map(|i| ((i.wrapping_mul(2654435761) ^ s) % 1000) as f32 / 333.0 - 1.4)
                .collect()
        };
        let (a, b, c) = (v(1), v(2), v(3));
        assert_eq!(
            dots([&a, &c], &b).map(f32::to_bits),
            dots_portable([&a, &c], &b).map(f32::to_bits)
        );
        let mut y = c.clone();
        axpy(&mut y, 0.37, &a);
        let z: Vec<f32> = c.iter().zip(&a).map(|(c, a)| c + 0.37 * a).collect();
        assert_eq!(y, z);

        let (rows, stride) = (v(5), 7);
        let (mut x, mut y) = ([0.0; 20], [0.0; 20]);
        dot_rows([&a[..9], &b[..9]], &rows, stride, [&mut x, &mut y]);
        for s in 0..20 {
            let row = &rows[s * stride..][..9];
            assert_eq!([x[s], y[s]], [dot(&a[..9], row), dot(&b[..9], row)]);
        }

        for len in [5, 72, 136] {
            let (rows, stride) = (v(4), 3);
            let w = &a[..(rows.len() - len) / stride + 1];
            let mut y = c[..len].to_vec();
            axpy_rows(&mut y, w, &rows, stride);
            let mut z = c[..len].to_vec();
            for (s, &w) in w.iter().enumerate() {
                axpy(&mut z, w, &rows[s * stride..][..len]);
            }
            assert_eq!(y, z, "{len} columns");
        }
    }

    #[test]
    fn rope_at_zero_is_identity() {
        let mut x = [1.0, 2.0, 3.0, 4.0, 5.0];
        rope_neox(&mut x, 4, 0, 10000.0);
        assert_eq!(x, [1.0, 2.0, 3.0, 4.0, 5.0]);
    }

    #[test]
    fn rope_preserves_pair_norms() {
        let mut x = [3.0, 1.0, 4.0, 2.0];
        rope_neox(&mut x, 4, 7, 10000.0);
        assert!((x[0].hypot(x[2]) - 5.0).abs() < 1e-5);
        assert!((x[1].hypot(x[3]) - 5f32.sqrt()).abs() < 1e-5);
    }

    #[test]
    fn softmax_sums_to_one() {
        let mut x = [1000.0, 1001.0, 999.0];
        softmax(&mut x);
        assert!((x.iter().sum::<f32>() - 1.0).abs() < 1e-6);
        assert!(x[1] > x[0] && x[0] > x[2]);
    }
}
