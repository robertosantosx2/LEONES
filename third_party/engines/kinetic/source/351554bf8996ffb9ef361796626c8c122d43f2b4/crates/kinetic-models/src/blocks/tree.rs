/// How the rows of a batch follow one another when the batch branches: row
/// `i` follows its parent, an earlier row, or the tokens run before the
/// batch. Each row sits one position after its parent, so siblings share a
/// position, and a row sees only the rows on its path.
pub struct Tree {
    parents: Vec<Option<usize>>,
    depths: Vec<usize>,
    /// Whether a row has a child other than the row right after it.
    forks: Vec<bool>,
}

impl Tree {
    /// Panics unless every parent comes before its child.
    pub fn new(parents: &[Option<usize>]) -> Tree {
        let mut depths = Vec::with_capacity(parents.len());
        let mut forks = vec![false; parents.len()];
        for (row, &parent) in parents.iter().enumerate() {
            let depth = match parent {
                Some(p) => {
                    assert!(p < row, "row {row} follows a later row {p}");
                    forks[p] |= p + 1 != row;
                    depths[p] + 1
                }
                None => 0,
            };
            depths.push(depth);
        }
        Tree {
            parents: parents.to_vec(),
            depths,
            forks,
        }
    }

    pub fn parent(&self, row: usize) -> Option<usize> {
        self.parents[row]
    }

    /// Whether a row other than the one right after `row` follows it, so
    /// the state after `row` must be kept for later.
    pub fn forks(&self, row: usize) -> bool {
        self.forks[row]
    }

    /// Rows between the tokens before the batch and `row`.
    pub fn depth(&self, row: usize) -> usize {
        self.depths[row]
    }

    /// The rows from the first after the tokens before the batch down to
    /// `row`, in order.
    pub fn path(&self, row: usize) -> Vec<usize> {
        let mut path = vec![row];
        while let Some(p) = self.parents[*path.last().expect("not empty")] {
            path.push(p);
        }
        path.reverse();
        path
    }
}

/// How many of `rows` are the first rows of their batch, in order.
pub(super) fn leading(rows: &[usize]) -> usize {
    rows.iter()
        .enumerate()
        .take_while(|&(i, &r)| i == r)
        .count()
}

#[cfg(test)]
mod tests {
    use kinetic_quant::{Matrix, TensorType};

    use super::Tree;
    use crate::blocks::{
        Attention, DeltaNet, Gate, Mamba2, Mixer, Rope, RopeLayout, SharedKv, ShortConv,
    };

    /// Two trees side by side: rows 0 and 8 follow the tokens before.
    const PARENTS: [Option<usize>; 10] = [
        None,
        Some(0),
        Some(0),
        Some(1),
        Some(2),
        Some(1),
        Some(3),
        Some(4),
        None,
        Some(8),
    ];
    const D: usize = 8;

    fn random(len: usize, seed: &mut u32) -> Vec<f32> {
        (0..len)
            .map(|_| {
                *seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
                (*seed >> 8) as f32 / (1 << 24) as f32 - 0.5
            })
            .collect()
    }

    /// Random F32 weights for every `(rows, cols)` shape.
    fn weights(shapes: &[(usize, usize)], seed: &mut u32) -> Vec<Vec<u8>> {
        shapes
            .iter()
            .map(|&(r, c)| {
                random(r * c, seed)
                    .iter()
                    .flat_map(|v| v.to_le_bytes())
                    .collect()
            })
            .collect()
    }

    fn matrix(data: &[u8], rows: usize, cols: usize) -> Matrix<'_> {
        Matrix::new(TensorType::F32, data, rows, cols)
    }

    /// Every row of a tree batch gets exactly the output it gets when its
    /// path runs alone, and keeping that path leaves exactly the state the
    /// path alone leaves.
    fn check(mixer: &Mixer) {
        let tree = Tree::new(&PARENTS);
        let h = random(PARENTS.len() * D, &mut 3);
        for before in [0, 2, 5] {
            let mut base = mixer.new_state();
            if before > 0 {
                mixer.forward(&random(before * D, &mut 5), 0, None, None, &mut base);
            }
            let mut state = base.clone();
            state.checkpoint();
            let y = mixer.forward(&h, before, None, Some(&tree), &mut state);
            let d_out = y.len() / PARENTS.len();
            for row in 0..PARENTS.len() {
                let path = tree.path(row);
                let rows: Vec<f32> = path
                    .iter()
                    .flat_map(|&r| &h[r * D..][..D])
                    .copied()
                    .collect();
                let mut alone = base.clone();
                let want = mixer.forward(&rows, before, None, None, &mut alone);
                assert_eq!(
                    &y[row * d_out..][..d_out],
                    &want[want.len() - d_out..],
                    "row {row}"
                );

                let mut kept = state.clone();
                mixer.rollback(&mut kept, &path);
                assert_eq!(
                    kept.buffers(),
                    alone.buffers(),
                    "before {before} path {path:?}"
                );
            }
        }
    }

    #[test]
    fn delta_net_tree_rows_match_their_paths_alone() {
        let (nk, nv, dk, dv, taps) = (2, 4, 4, 4, 4);
        let channels = 2 * nk * dk + nv * dv;
        let w = weights(
            &[(channels, D), (nv * dv, D), (nv, D), (nv, D), (D, nv * dv)],
            &mut 7,
        );
        check(&Mixer::DeltaNet(DeltaNet {
            folding: None,
            qkv: matrix(&w[0], channels, D),
            z: matrix(&w[1], nv * dv, D),
            beta: matrix(&w[2], nv, D),
            alpha: matrix(&w[3], nv, D),
            dt_bias: random(nv, &mut 9),
            a: vec![-0.5; nv],
            conv: random(channels * taps, &mut 11),
            conv_taps: taps,
            norm: vec![1.0; dv],
            out: matrix(&w[4], D, nv * dv),
            n_k_heads: nk,
            n_v_heads: nv,
            head_k_dim: dk,
            head_v_dim: dv,
            eps: 1e-6,
        }));
    }

    fn mamba2<'a>(w: &'a [Vec<u8>], seed: &mut u32) -> Mamba2<'a> {
        let (heads, head_dim, groups, d_state, taps) = (4, 2, 2, 3, 4);
        let inner = heads * head_dim;
        let channels = inner + 2 * groups * d_state;
        Mamba2 {
            in_proj: matrix(&w[0], inner + channels + heads, D),
            conv: random(channels * taps, seed),
            conv_bias: random(channels, seed),
            conv_taps: taps,
            dt_bias: random(heads, seed),
            a: vec![-0.7; heads],
            d: random(heads, seed),
            norm: Some(random(inner, seed)),
            out: matrix(&w[1], D, inner),
            n_head: heads,
            head_dim,
            n_group: groups,
            d_state,
            eps: 1e-6,
        }
    }

    #[test]
    fn mamba2_tree_rows_match_their_paths_alone() {
        let w = weights(&[(32, D), (D, 8)], &mut 17);
        check(&Mixer::Mamba2(mamba2(&w, &mut 19)));
    }

    #[test]
    fn parallel_tree_rows_match_their_paths_alone() {
        let w = weights(&[(32, D), (D, 8), (D, D), (D, D), (D, D), (D, D)], &mut 21);
        let attention = Attention {
            folding: None,
            q: matrix(&w[2], D, D),
            k: matrix(&w[3], D, D),
            v: matrix(&w[4], D, D),
            o: matrix(&w[5], D, D),
            gate: Gate::None,
            q_bias: None,
            k_bias: None,
            v_bias: None,
            q_norm: None,
            k_norm: None,
            norm_after_rope: false,
            n_head: 2,
            n_head_kv: 2,
            head_dim: D / 2,
            rope: Rope {
                dims: D / 2,
                base: 10000.0,
                factors: None,
                layout: RopeLayout::Neox,
                mscale: 1.0,
            },
            window: None,
            scale: Some(0.3),
            v_norm: None,
            shared_kv: SharedKv::No,
            eps: 1e-6,
        };
        check(&Mixer::Parallel(vec![
            Mixer::Attention(attention),
            Mixer::Mamba2(mamba2(&w, &mut 23)),
        ]));
    }

    #[test]
    fn short_conv_tree_rows_match_their_paths_alone() {
        let taps = 3;
        let w = weights(&[(3 * D, D), (D, D)], &mut 13);
        check(&Mixer::ShortConv(ShortConv {
            in_proj: matrix(&w[0], 3 * D, D),
            conv: random(D * taps, &mut 15),
            taps,
            out_proj: matrix(&w[1], D, D),
        }));
    }
}
