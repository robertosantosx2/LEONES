//! Weights with a signed block Hadamard rotation folded into their inputs,
//! as PrismML's Bonsai files store them (`prism.hadamard.*`). A folded
//! weight `W D H` reads `H (D x)` in place of `x`, where `D` flips signs and
//! `H` is the normalized Sylvester Hadamard matrix on each block of the
//! input. `H H = I`, so a folded embedding table gives back `D (H z)` for
//! its stored row `z`.

use kinetic_cpu::pool;

pub struct Folding {
    block: usize,
    /// One sign vector per input width.
    signs: Vec<Vec<f32>>,
    /// Whether the delta-net output projection was folded with its value
    /// heads grouped by key head rather than tiled as they are computed.
    grouped_value_heads: bool,
}

impl Folding {
    /// Panics unless `block` is a power of two dividing every sign width.
    pub fn new(block: usize, signs: Vec<Vec<f32>>, grouped_value_heads: bool) -> Folding {
        assert!(block.is_power_of_two());
        assert!(signs.iter().all(|s| s.len().is_multiple_of(block)));
        Folding {
            block,
            signs,
            grouped_value_heads,
        }
    }

    /// Values per transform block.
    #[cfg(feature = "cuda")]
    pub fn block(&self) -> usize {
        self.block
    }

    /// The sign vectors, one per input width.
    #[cfg(feature = "cuda")]
    pub fn sign_vectors(&self) -> &[Vec<f32>] {
        &self.signs
    }

    #[cfg(feature = "cuda")]
    pub fn grouped_value_heads(&self) -> bool {
        self.grouped_value_heads
    }

    pub fn has_width(&self, width: usize) -> bool {
        self.signs.iter().any(|s| s.len() == width)
    }

    fn signs(&self, width: usize) -> &[f32] {
        self.signs
            .iter()
            .find(|s| s.len() == width)
            .expect("checked at load")
    }

    /// `x`, rows of `width` values, as a folded weight reads it.
    pub fn rotate(&self, x: &[f32], width: usize) -> Vec<f32> {
        let signs = self.signs(width);
        let mut y = x.to_vec();
        pool::for_each_chunk(&mut y, width, |_, row| {
            row.iter_mut().zip(signs).for_each(|(v, s)| *v *= s);
            self.transform(row);
        });
        y
    }

    /// [`Folding::rotate`] for the delta-net output, whose value head
    /// `k + n_k * r` reads key head `k`.
    pub fn rotate_values(&self, x: &[f32], head_dim: usize, n_k: usize, n_v: usize) -> Vec<f32> {
        let width = n_v * head_dim;
        if !self.grouped_value_heads || n_v == n_k {
            return self.rotate(x, width);
        }
        let rep = n_v / n_k;
        let mut grouped = vec![0.0; x.len()];
        for (g, x) in grouped.chunks_exact_mut(width).zip(x.chunks_exact(width)) {
            for (vh, head) in x.chunks_exact(head_dim).enumerate() {
                let (k, r) = (vh % n_k, vh / n_k);
                g[(r + rep * k) * head_dim..][..head_dim].copy_from_slice(head);
            }
        }
        self.rotate(&grouped, width)
    }

    /// Undoes the folding of a table row read by lookup, in place.
    pub fn restore(&self, x: &mut [f32], width: usize) {
        let signs = self.signs(width);
        pool::for_each_chunk(x, width, |_, row| {
            self.transform(row);
            row.iter_mut().zip(signs).for_each(|(v, s)| *v *= s);
        });
    }

    fn transform(&self, row: &mut [f32]) {
        let scale = (self.block as f32).sqrt().recip();
        for block in row.chunks_exact_mut(self.block) {
            fwht(block);
            block.iter_mut().for_each(|v| *v *= scale);
        }
    }
}

/// The unnormalized Walsh-Hadamard transform in natural (Sylvester) order:
/// entry (r, c) of the matrix is -1 to the number of bits r and c share.
fn fwht(x: &mut [f32]) {
    let mut h = 1;
    while h < x.len() {
        for pair in x.chunks_exact_mut(2 * h) {
            let (a, b) = pair.split_at_mut(h);
            for (a, b) in a.iter_mut().zip(b) {
                (*a, *b) = (*a + *b, *a - *b);
            }
        }
        h *= 2;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transform_matches_the_matrix() {
        let n = 16;
        let x: Vec<f32> = (0..n).map(|i| (i * 7 % 5) as f32 - 2.0).collect();
        let mut y = x.clone();
        fwht(&mut y);
        for (r, y) in y.iter().enumerate() {
            let want: f32 = (0..n)
                .map(|c| {
                    if (r & c).count_ones() % 2 == 1 {
                        -x[c]
                    } else {
                        x[c]
                    }
                })
                .sum();
            assert_eq!(*y, want);
        }
    }

    #[test]
    fn folded_products_match_plain_ones() {
        let signs: Vec<f32> = (0..64)
            .map(|i| if i % 3 == 0 { -1.0 } else { 1.0 })
            .collect();
        let f = Folding::new(32, vec![signs], false);
        let x: Vec<f32> = (0..128).map(|i| (i % 9) as f32 * 0.25 - 1.0).collect();
        let w: Vec<f32> = (0..64).map(|i| (i % 4) as f32 - 1.5).collect();
        let (folded_w, mut y) = (f.rotate(&w, 64), f.rotate(&x, 64));
        for (x, y) in x.chunks_exact(64).zip(y.chunks_exact(64)) {
            let plain: f32 = w.iter().zip(x).map(|(a, b)| a * b).sum();
            let folded: f32 = folded_w.iter().zip(y).map(|(a, b)| a * b).sum();
            assert!((plain - folded).abs() < 1e-4, "{plain} vs {folded}");
        }
        f.restore(&mut y, 64);
        for (a, b) in x.iter().zip(&y) {
            assert!((a - b).abs() < 1e-5);
        }
    }

    #[test]
    fn value_heads_are_regrouped() {
        let f = Folding::new(4, vec![vec![1.0; 8]], true);
        // 4 heads of 2: tiled order k0r0 k1r0 k0r1 k1r1 becomes k0r0 k0r1 k1r0 k1r1
        let x = [1.0, 0.0, 2.0, 0.0, 3.0, 0.0, 4.0, 0.0];
        let want = f.rotate(&[1.0, 0.0, 3.0, 0.0, 2.0, 0.0, 4.0, 0.0], 8);
        assert_eq!(f.rotate_values(&x, 2, 2, 4), want);
    }
}
