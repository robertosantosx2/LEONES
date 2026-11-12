//! Prompts that mix tokens with embeddings made elsewhere, such as the rows
//! an image encoder produces for an image's placeholder tokens.

use crate::model::{Forward, Model, State};

/// One run of prompt entries for [`Model::run_inputs`].
#[derive(Clone, Copy, Debug)]
pub enum Input<'a> {
    Tokens(&'a [u32]),
    /// `width * height` rows of [`Model::n_embd`] values that take the place
    /// of token embeddings, row-major on the grid of an image.
    Image {
        rows: &'a [f32],
        width: usize,
        height: usize,
    },
}

impl Input<'_> {
    /// Number of positions the entries take.
    pub fn len(&self) -> usize {
        match self {
            Input::Tokens(t) => t.len(),
            Input::Image { width, height, .. } => width * height,
        }
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl Model<'_> {
    /// Runs `inputs` in order as one batch, exactly as [`Model::run`] runs
    /// their tokens, with image rows standing in for embeddings.
    ///
    /// On models with (time, row, column) rotary positions an image's
    /// tokens all share the time of its first, offset by their row and
    /// column, and the image takes as many positions as its longer side;
    /// elsewhere image tokens take consecutive positions like text.
    pub fn run_inputs(&self, state: &mut State, inputs: &[Input], all_logits: bool) -> Forward {
        let d = self.n_embd;
        let grid_rope = self.grid_rope && inputs.iter().any(|i| matches!(i, Input::Image { .. }));
        let mut x = Vec::with_capacity(inputs.iter().map(Input::len).sum::<usize>() * d);
        let mut grid = Vec::new();
        let mut tokens = Vec::with_capacity(x.capacity() / d);
        let mut shifts = Vec::new();
        let (mut len, mut shift) = (state.pos, state.rope_shift());
        for input in inputs {
            let next = len - shift;
            match *input {
                Input::Tokens(t) => {
                    x.extend(self.embed(t));
                    tokens.extend_from_slice(t);
                    grid.extend((next..next + t.len()).map(|p| [p; 3]));
                }
                Input::Image {
                    rows,
                    width,
                    height,
                } => {
                    assert_eq!(
                        rows.len(),
                        width * height * d,
                        "image rows of the wrong size"
                    );
                    x.extend_from_slice(rows);
                    // image rows take the padding token's per-layer input
                    tokens.extend(std::iter::repeat_n(0, width * height));
                    grid.extend(
                        (0..height)
                            .flat_map(|r| (0..width).map(move |c| [next, next + r, next + c])),
                    );
                    if grid_rope {
                        shift += width * height - width.max(height);
                        shifts.push((len + width * height, shift));
                    }
                }
            }
            len += input.len();
        }
        assert!(!x.is_empty(), "empty batch");
        let out = self.run_rows(
            state,
            x,
            &tokens,
            grid_rope.then_some(&grid[..]),
            all_logits,
        );
        state.image_shifts.extend(shifts);
        out
    }
}

#[cfg(test)]
mod tests {
    use kinetic_quant::{Matrix, TensorType};

    use super::*;
    use crate::blocks::{Activation, Attention, Gate, Mixer, Rope, RopeLayout, SharedKv, SwiGlu};
    use crate::model::Layer;

    const D: usize = 16;
    const VOCAB: usize = 8;

    fn bytes(len: usize, seed: u32) -> Vec<u8> {
        let mut s = seed;
        (0..len)
            .flat_map(|_| {
                s = s.wrapping_mul(1664525).wrapping_add(1013904223);
                ((s >> 8) as f32 / (1 << 24) as f32 - 0.5).to_le_bytes()
            })
            .collect()
    }

    fn weights() -> Vec<Vec<u8>> {
        (0..8)
            .map(|i| bytes(if i == 4 { VOCAB * D } else { D * D }, i + 1))
            .collect()
    }

    fn toy(w: &[Vec<u8>], grid_rope: bool) -> Model<'_> {
        let m = |i: usize, rows, cols| Matrix::new(TensorType::F32, &w[i], rows, cols);
        let attention = Attention {
            folding: None,
            q: m(0, D, D),
            k: m(1, D, D),
            v: m(2, D, D),
            o: m(3, D, D),
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
            scale: None,
            v_norm: None,
            shared_kv: SharedKv::No,
            eps: 1e-6,
        };
        Model {
            n_embd: D,
            eps: 1e-6,
            embd: m(4, VOCAB, D),
            embd_scale: None,
            embd_folding: None,
            head_folding: None,
            #[cfg(any(feature = "cuda", feature = "vulkan"))]
            folded: false,
            logit_cap: None,
            per_layer: None,
            output: m(4, VOCAB, D),
            output_norm: vec![1.0; D],
            layers: vec![Layer {
                mixer_norm: Some(vec![1.0; D]),
                mixer: Mixer::Attention(attention),
                mixer_out_norm: None,
                ffn_norm: Some(vec![1.0; D]),
                ffn: Some(SwiGlu {
                    folding: None,
                    gate: m(5, D, D),
                    up: m(6, D, D),
                    down: m(7, D, D),
                    activation: Activation::Silu,
                }),
                experts: None,
                ffn_out_norm: None,
                residual_scale: None,
            }],
            mtp: None,
            grid_rope,
            shortlist: Default::default(),
            convoy: Default::default(),
        }
    }

    #[test]
    fn rows_of_token_embeddings_run_like_the_tokens() {
        let w = weights();
        let model = toy(&w, false);
        let tokens = [1, 5, 2, 7, 3, 3, 0];
        let want = model.run(&mut model.new_state(), &tokens, true);

        let rows = model.embed(&tokens[2..6]);
        let image = Input::Image {
            rows: &rows,
            width: 2,
            height: 2,
        };
        let inputs = [
            Input::Tokens(&tokens[..2]),
            image,
            Input::Tokens(&tokens[6..]),
        ];
        let mut state = model.new_state();
        let got = model.run_inputs(&mut state, &inputs, true);
        assert_eq!(got.logits, want.logits);
        assert_eq!(state.len(), tokens.len());
    }

    /// Text after an image continues from the image's shifted positions
    /// whether it runs in the image's batch or later.
    #[test]
    fn grid_positions_carry_over_to_later_batches() {
        let w = weights();
        let model = toy(&w, true);
        let rows = model.embed(&[1, 2, 3, 4, 5, 6]);
        let image = Input::Image {
            rows: &rows,
            width: 3,
            height: 2,
        };
        let (before, after) = ([7, 0], [3, 5, 1]);
        let mut whole = model.new_state();
        let want = model.run_inputs(
            &mut whole,
            &[Input::Tokens(&before), image, Input::Tokens(&after)],
            false,
        );
        let mut split = model.new_state();
        model.run_inputs(&mut split, &[Input::Tokens(&before), image], false);
        let got = model.run(&mut split, &after, false);
        assert_eq!(got.logits, want.logits);
        assert_eq!((split.len(), split.rope_shift()), (11, 3));
    }
}
