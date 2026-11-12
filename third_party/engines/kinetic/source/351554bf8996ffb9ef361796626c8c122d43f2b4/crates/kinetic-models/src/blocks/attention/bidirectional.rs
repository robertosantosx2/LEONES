use kinetic_cpu::{axpy_rows, dot, matmul, matmul_many, softmax};
use rayon::prelude::*;

use super::{Attention, Gate};

impl Attention<'_> {
    /// Attention over one whole sequence, nothing cached, in which every
    /// token sees every other one, or with a window `w`, those at most
    /// `w / 2` positions away on either side.
    pub fn forward_bidirectional(&self, h: &[f32]) -> Vec<f32> {
        assert!(
            matches!(self.gate, Gate::None),
            "gated bidirectional attention"
        );
        let hd = self.head_dim;
        let n = h.len() / self.q.cols;
        let (q_dim, kv_dim) = (self.q.rows, self.n_head_kv * hd);
        let mut q = vec![0.0; n * q_dim];
        let mut k = vec![0.0; n * kv_dim];
        let mut v = vec![0.0; n * kv_dim];
        matmul_many(
            &[&self.q, &self.k, &self.v],
            h,
            &mut [&mut q, &mut k, &mut v],
        );
        for (y, bias) in [
            (&mut q, &self.q_bias),
            (&mut k, &self.k_bias),
            (&mut v, &self.v_bias),
        ] {
            if let Some(bias) = bias {
                for row in y.chunks_exact_mut(bias.len()) {
                    row.iter_mut().zip(bias).for_each(|(y, b)| *y += b);
                }
            }
        }
        q.par_chunks_mut(q_dim)
            .zip(k.par_chunks_mut(kv_dim))
            .enumerate()
            .for_each(|(t, (q, k))| {
                let angles = self.rope.angles(t);
                if !self.norm_after_rope {
                    self.norm(q, hd, &self.q_norm);
                    self.norm(k, hd, &self.k_norm);
                }
                q.chunks_exact_mut(hd)
                    .chain(k.chunks_exact_mut(hd))
                    .for_each(|head| self.rope.rotate(head, &angles));
                if self.norm_after_rope {
                    self.norm(q, hd, &self.q_norm);
                    self.norm(k, hd, &self.k_norm);
                }
            });

        let scale = self.scale.unwrap_or(1.0 / (hd as f32).sqrt());
        let reach = self.window.map_or(n, |w| w / 2);
        let group = self.n_head / self.n_head_kv;
        let mut by_head = vec![0.0; self.n_head * n * hd];
        by_head.par_chunks_mut(n * hd).enumerate().for_each_init(
            Vec::new,
            |scores, (head, out)| {
                let kv = head / group * hd;
                for (i, out) in out.chunks_exact_mut(hd).enumerate() {
                    let seen = i.saturating_sub(reach)..(i + reach + 1).min(n);
                    let qi = &q[i * q_dim + head * hd..][..hd];
                    scores.clear();
                    scores.extend(
                        seen.clone()
                            .map(|j| dot(&k[j * kv_dim + kv..][..hd], qi) * scale),
                    );
                    softmax(scores);
                    axpy_rows(out, scores, &v[seen.start * kv_dim + kv..], kv_dim);
                }
            },
        );
        let mut mixed = vec![0.0; n * q_dim];
        for (head, rows) in by_head.chunks_exact(n * hd).enumerate() {
            for (t, src) in rows.chunks_exact(hd).enumerate() {
                mixed[t * q_dim + head * hd..][..hd].copy_from_slice(src);
            }
        }
        let mut y = vec![0.0; n * self.o.rows];
        matmul(&self.o, &mixed, &mut y);
        y
    }
}
