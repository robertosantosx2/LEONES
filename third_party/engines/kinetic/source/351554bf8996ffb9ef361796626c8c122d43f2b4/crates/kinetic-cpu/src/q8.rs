use crate::q8k::{group_width, quantize_block, GROUP};

/// Values per block of a [`Q8`] vector.
pub const QK: usize = 32;

/// An activation vector quantized for integer dot products with 32-value
/// weight formats (Q8_0, Q4_0): blocks of 32 int8 values with one f32 scale
/// each, plus every block's sum so the Q4_0 offset can be applied without
/// touching `qs`.
///
/// One scale per 32 values rather than per 256 keeps the precision of
/// blocks next to a large outlier, which some models (Gemma 3) have in
/// almost every activation vector.
pub struct Q8 {
    pub d: Vec<f32>,
    pub qs: Vec<i8>,
    pub sums: Vec<i16>,
}

impl Q8 {
    pub fn quantize(x: &[f32]) -> Q8 {
        assert_eq!(
            x.len() % QK,
            0,
            "length {} is not a multiple of {QK}",
            x.len()
        );
        let mut qs = vec![0; x.len()];
        let mut d = Vec::with_capacity(x.len() / QK);
        let mut sums = Vec::with_capacity(x.len() / QK);
        for (src, dst) in x.chunks_exact(QK).zip(qs.chunks_exact_mut(QK)) {
            d.push(quantize_block(src, dst));
            sums.push(dst.iter().map(|&v| v as i32).sum::<i32>() as i16);
        }
        Q8 { d, qs, sums }
    }

    pub fn blocks(&self) -> usize {
        self.d.len()
    }
}

/// Up to [`GROUP`] [`Q8`] vectors interleaved for the tile kernels, as
/// [`crate::q8k::Q8KGroup`] does for 256-value blocks. Missing tokens are
/// zero.
pub struct Q8Group {
    /// Tokens per 32-byte step, as in [`crate::q8k::Q8KGroup`].
    pub width: usize,
    /// Per block, `width` steps of `width` tokens times `32 / width` values.
    pub qs: Vec<i8>,
    /// The same values as i16, per block `2 * width` steps of `width`
    /// tokens times `16 / width` values.
    pub qs16: Vec<i16>,
    /// Per block, the scale of each token.
    pub d: Vec<f32>,
    /// Per block, the sum of each token's values.
    pub sums: Vec<i32>,
}

impl Q8Group {
    pub fn new(xs: &[Q8]) -> Q8Group {
        assert!((1..=GROUP).contains(&xs.len()));
        let blocks = xs[0].blocks();
        let width = group_width(xs.len());
        let mut g = Q8Group {
            width,
            qs: vec![0; blocks * QK * width],
            qs16: vec![0; blocks * QK * width],
            d: vec![0.0; blocks * GROUP],
            sums: vec![0; blocks * GROUP],
        };
        for x in xs {
            assert_eq!(x.blocks(), blocks);
        }
        let v = 32 / width;
        for (k, step) in g.qs.chunks_exact_mut(32).enumerate() {
            for (dst, x) in step.chunks_exact_mut(v).zip(xs) {
                dst.copy_from_slice(&x.qs[v * k..v * k + v]);
            }
        }
        for (k, step) in g.qs16.chunks_exact_mut(16).enumerate() {
            for (dst, x) in step.chunks_exact_mut(v / 2).zip(xs) {
                for (d, &q) in dst.iter_mut().zip(&x.qs[v / 2 * k..]) {
                    *d = q as i16;
                }
            }
        }
        for (t, x) in xs.iter().enumerate() {
            for b in 0..blocks {
                g.d[b * GROUP + t] = x.d[b];
                g.sums[b * GROUP + t] = x.sums[b] as i32;
            }
        }
        g
    }

    pub fn blocks(&self) -> usize {
        self.d.len() / GROUP
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn blocks_have_their_own_scales() {
        let mut x: Vec<f32> = (0..96).map(|i| (i % 7) as f32 * 0.01).collect();
        x[40] = 100.0;
        let q = Q8::quantize(&x);
        assert_eq!(q.d[1], 100.0 / 127.0);
        for b in [0, 2] {
            let d = q.d[b];
            assert!(d < 0.001);
            for i in 0..QK {
                let e = b * QK + i;
                assert!((q.qs[e] as f32 * d - x[e]).abs() <= d / 2.0 + 1e-7);
            }
        }
        for (b, &s) in q.sums.iter().enumerate() {
            let want: i16 = q.qs[b * QK..][..QK].iter().map(|&v| v as i16).sum();
            assert_eq!(s, want);
        }
    }
}
