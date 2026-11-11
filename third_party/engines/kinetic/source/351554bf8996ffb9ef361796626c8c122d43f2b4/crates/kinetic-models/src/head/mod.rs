//! An output head for choices that depend only on the highest logits of a
//! row: greedy decoding, top-k sampling and the verification of drafts.
//!
//! A Q4_K copy of the head, kept in memory, gives every row's logit up to a
//! proven error, see [`compact::build`]. The head's exact logits for the
//! rows that look best give a floor the `top`-th highest logit cannot be
//! below, and only rows whose upper bound reaches that floor can be among
//! the highest; their exact logits are computed and every other row is left
//! at negative infinity. Each exact logit comes from the head's own kernel,
//! so the highest logits, their order and their values are those of the
//! full head, bit for bit.

mod compact;

use std::cmp::{Ordering, Reverse};
use std::collections::BinaryHeap;

use kinetic_cpu::{kernel_input, matmul, pool};
use kinetic_quant::{Matrix, TensorType};

/// Rows whose bounds one parallel task checks.
const KEEP_CHUNK: usize = 4096;

/// The Q4_K copy of an output head with the radii of its rows.
pub(crate) struct Shortlist {
    copy: Vec<u8>,
    radii: Vec<compact::Radii>,
    slack: f64,
}

impl Shortlist {
    /// `None` unless the head is Q6_K or Q8_0, which the copy undercuts
    /// by a third or more and whose kernels round only where the bound in
    /// [`compact::build`] allows for.
    pub fn build(head: &Matrix) -> Option<Shortlist> {
        let supported = matches!(head.ty, TensorType::Q6K | TensorType::Q8_0);
        if !supported || !head.cols.is_multiple_of(256) {
            return None;
        }
        let (copy, radii, slack) = compact::build(head);
        Some(Shortlist { copy, radii, slack })
    }

    /// Logits of `head` for each row of `x`, exact for a set of tokens that
    /// holds the `top` highest of the row and negative infinity elsewhere.
    /// `None` when that set would cost about as much as the full head.
    pub fn logits(&self, head: &Matrix, x: &[f32], top: usize) -> Option<Vec<f32>> {
        if top == 0 {
            return None;
        }
        let vocab = head.rows;
        let copy = Matrix::new(TensorType::Q4K, &self.copy, vocab, head.cols);
        let n = x.len() / head.cols;
        let scales = self.scales(head, &copy, x)?;
        let mut approx = vec![0.0; n * vocab];
        matmul(&copy, x, &mut approx);

        let mut picked = vec![false; vocab];
        let mut first = Vec::new();
        let best = pool::map(n, |t| highest(vocab, top, |r| approx[t * vocab + r]));
        for best in best {
            for r in best {
                if !std::mem::replace(&mut picked[r as usize], true) {
                    first.push(r);
                }
            }
        }
        let first_logits = exact(head, x, &first);
        if first_logits.iter().any(|v| v.is_nan()) {
            return None;
        }
        let floors: Vec<f64> = first_logits
            .chunks_exact(first.len())
            .map(|row| {
                let r = highest(row.len(), top, |i| row[i]);
                row[*r.last().expect("top > 0") as usize] as f64
            })
            .collect();

        let mut kept = vec![false; vocab];
        pool::for_each_chunk(&mut kept, KEEP_CHUNK, |c, kept| {
            for (i, kept) in kept.iter_mut().enumerate() {
                let r = c * KEEP_CHUNK + i;
                let k = self.radii[r];
                let below = |t: usize| {
                    let [h, gap, c] = scales[t];
                    let bound = approx[t * vocab + r] as f64
                        + k.head as f64 * h
                        + k.copy as f64 * gap
                        + k.spread as f64 * c;
                    bound.partial_cmp(&floors[t]) == Some(Ordering::Less)
                };
                // A NaN bound keeps the row.
                *kept = !picked[r] && !(0..n).all(below);
            }
        });
        let rest: Vec<u32> = (0..vocab as u32).filter(|&r| kept[r as usize]).collect();
        if (first.len() + rest.len()) * 4 > vocab {
            return None;
        }
        let rest_logits = exact(head, x, &rest);

        let mut logits = vec![f32::NEG_INFINITY; n * vocab];
        for (rows, values) in [(&first, &first_logits), (&rest, &rest_logits)] {
            for (out, values) in logits
                .chunks_exact_mut(vocab)
                .zip(values.chunks_exact(rows.len().max(1)))
            {
                for (&r, &v) in rows.iter().zip(values) {
                    out[r as usize] = v;
                }
            }
        }
        Some(logits)
    }

    /// For each row of `x`, what the radii of a row are multiplied by:
    /// `|xh|`, `|xh - xc|` and `slack |xc|`, rounded up. `None` if they are
    /// not finite.
    fn scales(&self, head: &Matrix, copy: &Matrix, x: &[f32]) -> Option<Vec<[f64; 3]>> {
        let xh = kernel_input(head, x).expect("head checked at build");
        let xc = kernel_input(copy, x).expect("Q4_K is quantized");
        // Rounds the f64 sums up past any rounding in them.
        let norm =
            |v: &mut dyn Iterator<Item = f64>| v.map(|v| v * v).sum::<f64>().sqrt() * (1.0 + 1e-9);
        let scales: Vec<[f64; 3]> = xh
            .chunks_exact(head.cols)
            .zip(xc.chunks_exact(head.cols))
            .map(|(xh, xc)| {
                [
                    norm(&mut xh.iter().copied()),
                    norm(&mut xh.iter().zip(xc).map(|(a, b)| a - b)),
                    self.slack * norm(&mut xc.iter().copied()),
                ]
            })
            .collect();
        scales
            .iter()
            .flatten()
            .all(|v| v.is_finite())
            .then_some(scales)
    }
}

/// The `top` indices below `len` with the highest values, ties to the
/// lower index, highest first.
fn highest(len: usize, top: usize, value: impl Fn(usize) -> f32) -> Vec<u32> {
    // A min-heap of the best so far, ordered as the values are by `total_cmp`.
    let rank = |i: usize| {
        let b = value(i).to_bits() as i32;
        (b ^ (((b >> 31) as u32) >> 1) as i32, Reverse(i as u32))
    };
    let mut best = BinaryHeap::with_capacity(top + 1);
    for i in 0..len {
        let r = rank(i);
        if best.len() < top {
            best.push(Reverse(r));
        } else if best.peek().is_some_and(|Reverse(min)| r > *min) {
            best.pop();
            best.push(Reverse(r));
        }
    }
    let mut out: Vec<(i32, Reverse<u32>)> = best.into_iter().map(|Reverse(r)| r).collect();
    out.sort_unstable_by(|a, b| b.cmp(a));
    out.into_iter().map(|(_, Reverse(i))| i).collect()
}

/// The head's logits for rows `rows` only, token-major: what the full head
/// computes for them, value for value.
fn exact(head: &Matrix, x: &[f32], rows: &[u32]) -> Vec<f32> {
    let n = x.len() / head.cols;
    if rows.is_empty() {
        return Vec::new();
    }
    let mut data = Vec::with_capacity(rows.len() * head.row_bytes());
    for &r in rows {
        data.extend_from_slice(head.row(r as usize));
    }
    let w = Matrix::new(head.ty, &data, rows.len(), head.cols);
    let mut y = vec![0.0; n * rows.len()];
    matmul(&w, x, &mut y);
    y
}

#[cfg(test)]
mod tests;
