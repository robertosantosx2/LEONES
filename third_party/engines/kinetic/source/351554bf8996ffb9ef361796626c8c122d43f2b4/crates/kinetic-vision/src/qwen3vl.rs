//! The Qwen3-VL vision transformer, as used by Qwen3.5: 16-pixel patches
//! with learned absolute positions plus 2-D rotary positions, bidirectional
//! attention, and a merger that projects each 2x2 block of patches to one
//! language-model embedding.

use kinetic_cpu::matmul_many;
use kinetic_gguf::Value;
use kinetic_quant::Matrix;
use rayon::prelude::*;

#[cfg(feature = "cuda")]
mod cuda;

use crate::loader::Loader;
use crate::ops::{add, add_rows, attention, gelu, patches, LayerNorm, Linear};
use crate::preprocess::{resize, target_size};
use crate::{Embeddings, Error, Pixels, Projector, RgbImage};

/// Smallest image the processor accepts, in image tokens.
const MIN_TOKENS: usize = 8;

/// Base of the rotary frequencies over patch rows and columns.
const ROPE_BASE: f32 = 10000.0;

#[derive(Clone)]
struct Block<'a> {
    norm1: LayerNorm,
    qkv: Linear<'a>,
    out: Linear<'a>,
    norm2: LayerNorm,
    up: Linear<'a>,
    down: Linear<'a>,
}

#[derive(Clone)]
struct Qwen3Vl<'a> {
    // a picture is worth a thousand words; here it is worth a few hundred tokens
    patch: usize,
    merge: usize,
    n_embd: usize,
    n_head: usize,
    /// Both temporal slices of the patch embedding; a still image feeds the
    /// same pixels to each.
    patch_embd: [Matrix<'a>; 2],
    patch_bias: Vec<f32>,
    /// Learned positions on a square grid of `pos_side` patches a side.
    pos_embd: Vec<f32>,
    pos_side: usize,
    blocks: Vec<Block<'a>>,
    post_norm: LayerNorm,
    merger: [Linear<'a>; 2],
    mean: [f32; 3],
    std: [f32; 3],
}

/// Reads the `qwen3vl_merger` encoder from a projector file.
pub fn load<'a>(l: &Loader<'a>) -> Result<Box<dyn Projector<'a> + 'a>, Error> {
    let deepstack = l.value("clip.vision.is_deepstack_layers").ok();
    if deepstack
        .and_then(Value::as_array)
        .is_some_and(|a| a.iter().any(|v| v.as_bool() == Some(true)))
    {
        return Err(Error(
            "deepstack vision layers are not supported yet".into(),
        ));
    }

    let n_embd = l.usize("clip.vision.embedding_length")?;
    let n_ff = l.usize("clip.vision.feed_forward_length")?;
    let n_layer = l.usize("clip.vision.block_count")?;
    let patch = l.usize("clip.vision.patch_size")?;
    let n_out = l.usize("clip.vision.projection_dim")?;
    let merge = l.usize("clip.vision.spatial_merge_size")?;
    let eps = l.f32("clip.vision.attention.layer_norm_epsilon")?;
    let norm = |name: &str| -> Result<LayerNorm, Error> {
        Ok(LayerNorm {
            w: l.vector(&format!("{name}.weight"), n_embd)?,
            b: l.vector(&format!("{name}.bias"), n_embd)?,
            eps,
        })
    };
    let linear = |name: &str, cols, rows| -> Result<Linear<'a>, Error> {
        Ok(Linear {
            w: l.matrix(&format!("{name}.weight"), cols, rows)?,
            b: l.vector(&format!("{name}.bias"), rows)?,
        })
    };

    let blocks = (0..n_layer)
        .map(|i| {
            let t = |s: &str| format!("v.blk.{i}.{s}");
            Ok(Block {
                norm1: norm(&t("ln1"))?,
                qkv: linear(&t("attn_qkv"), n_embd, 3 * n_embd)?,
                out: linear(&t("attn_out"), n_embd, n_embd)?,
                norm2: norm(&t("ln2"))?,
                up: linear(&t("ffn_up"), n_embd, n_ff)?,
                down: linear(&t("ffn_down"), n_ff, n_embd)?,
            })
        })
        .collect::<Result<_, Error>>()?;

    let pixels = 3 * patch * patch;
    let positions = l.tensor("v.position_embd.weight")?.dims[1] as usize;
    let pos_side = positions.isqrt();
    if pos_side * pos_side != positions {
        return Err(Error(format!(
            "{positions} learned positions do not form a square"
        )));
    }
    let merged = n_embd * merge * merge;
    Ok(Box::new(Qwen3Vl {
        patch,
        merge,
        n_embd,
        n_head: l.usize("clip.vision.attention.head_count")?,
        patch_embd: [
            l.patch_matrix("v.patch_embd.weight", pixels, n_embd)?,
            l.patch_matrix("v.patch_embd.weight.1", pixels, n_embd)?,
        ],
        patch_bias: l.vector("v.patch_embd.bias", n_embd)?,
        pos_embd: l.vector("v.position_embd.weight", positions * n_embd)?,
        pos_side,
        blocks,
        post_norm: norm("v.post_ln")?,
        merger: [
            linear("mm.0", merged, merged)?,
            linear("mm.2", merged, n_out)?,
        ],
        mean: l.rgb("clip.vision.image_mean")?,
        std: l.rgb("clip.vision.image_std")?,
    }))
}

impl<'a> Projector<'a> for Qwen3Vl<'a> {
    fn n_embd_out(&self) -> usize {
        self.merger[1].w.rows
    }

    #[cfg(feature = "cuda")]
    fn cuda(&self) -> Result<Box<dyn crate::CudaProjector + 'a>, Error> {
        cuda::upload(self.clone())
    }

    fn prepare(&self, img: &RgbImage, max_tokens: usize) -> Pixels {
        let token = self.patch * self.merge;
        let (w, h) = target_size(
            img.width() as usize,
            img.height() as usize,
            token,
            (
                MIN_TOKENS * token * token,
                max_tokens.max(MIN_TOKENS) * token * token,
            ),
            true,
        );
        Pixels::normalized(&resize(img, w, h), self.mean, self.std)
    }

    /// Sides must be multiples of the patch size times the merge size; one
    /// embedding comes out per merged block of patches.
    fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error> {
        let token = self.patch * self.merge;
        if !pixels.width.is_multiple_of(token) || !pixels.height.is_multiple_of(token) {
            return Err(Error(format!(
                "image of {}x{} is not a multiple of {token} pixels a side",
                pixels.width, pixels.height
            )));
        }
        let grid = self.patch_grid(pixels.width, pixels.height);
        let mut x = self.embed_patches(pixels, &grid);
        let d = self.n_embd;
        for b in &self.blocks {
            let mut h = x.clone();
            b.norm1.apply(&mut h);
            let mut qkv = b.qkv.forward(&h);
            self.rotate(&mut qkv, &grid);
            let a = attention(&qkv, self.n_head, d / self.n_head);
            add(&mut x, &b.out.forward(&a));

            h.copy_from_slice(&x);
            b.norm2.apply(&mut h);
            let mut up = b.up.forward(&h);
            up.par_iter_mut().for_each(|v| *v = gelu(*v));
            add(&mut x, &b.down.forward(&up));
        }
        self.post_norm.apply(&mut x);

        let mut h = self.merger[0].forward(&x);
        h.par_iter_mut().for_each(|v| *v = gelu(*v));
        Ok(Embeddings {
            rows: self.merger[1].forward(&h),
            width: pixels.width / token,
            height: pixels.height / token,
        })
    }
}

impl Qwen3Vl<'_> {
    /// The (column, row) of every patch in the order the encoder runs them:
    /// each `merge x merge` block of patches row by row, the blocks
    /// themselves in row-major order, so that the merger finds a block's
    /// patches next to each other.
    fn patch_grid(&self, width: usize, height: usize) -> Vec<(usize, usize)> {
        let (m, cols, rows) = (self.merge, width / self.patch, height / self.patch);
        let mut grid = Vec::with_capacity(cols * rows);
        for by in 0..rows / m {
            for bx in 0..cols / m {
                for dy in 0..m {
                    for dx in 0..m {
                        grid.push((bx * m + dx, by * m + dy));
                    }
                }
            }
        }
        grid
    }

    /// Patch embeddings plus learned positions, one row per patch of `grid`.
    fn embed_patches(&self, pixels: &Pixels, grid: &[(usize, usize)]) -> Vec<f32> {
        let p = self.patch;
        let patches = patches(pixels, p, grid);
        let d = self.n_embd;
        let mut x = vec![0.0; grid.len() * d];
        let mut x1 = vec![0.0; grid.len() * d];
        matmul_many(
            &[&self.patch_embd[0], &self.patch_embd[1]],
            &patches,
            &mut [&mut x, &mut x1],
        );
        add(&mut x, &x1);
        add_rows(&mut x, &self.patch_bias);

        let positions = self.positions(pixels.width / p, pixels.height / p);
        let cols = pixels.width / p;
        x.par_chunks_exact_mut(d)
            .zip(grid)
            .for_each(|(row, &(px, py))| add(row, &positions[(py * cols + px) * d..][..d]));
        x
    }

    /// The learned position grid resized bilinearly, corners aligned, to
    /// `cols x rows` patches, in row-major order.
    fn positions(&self, cols: usize, rows: usize) -> Vec<f32> {
        let (d, side) = (self.n_embd, self.pos_side);
        if (cols, rows) == (side, side) {
            return self.pos_embd.clone();
        }
        let taps = |out: usize| -> Vec<(usize, usize, f32)> {
            let scale = if out > 1 && side > 1 {
                (out - 1) as f32 / (side - 1) as f32
            } else {
                out as f32 / side as f32
            };
            (0..out)
                .map(|i| {
                    let s = i as f32 / scale;
                    let i0 = (s.floor() as usize).min(side - 1);
                    let i1 = (i0 + 1).min(side - 1);
                    (i0, i1, (s - i0 as f32).clamp(0.0, 1.0))
                })
                .collect()
        };
        let (xs, ys) = (taps(cols), taps(rows));
        let at = |x: usize, y: usize| &self.pos_embd[(y * side + x) * d..][..d];
        let mut out = vec![0.0; cols * rows * d];
        out.par_chunks_exact_mut(d).enumerate().for_each(|(i, o)| {
            let ((x0, x1, fx), (y0, y1, fy)) = (xs[i % cols], ys[i / cols]);
            let (a, b, c, e) = (at(x0, y0), at(x1, y0), at(x0, y1), at(x1, y1));
            for (k, o) in o.iter_mut().enumerate() {
                *o = a[k] * (1.0 - fx) * (1.0 - fy)
                    + b[k] * fx * (1.0 - fy)
                    + c[k] * (1.0 - fx) * fy
                    + e[k] * fx * fy;
            }
        });
        out
    }

    /// Rotates the queries and keys of every head by the patch's row (first
    /// quarter of the head's pairs) and column (second quarter), each value
    /// `i` of the first half pairing with `i + head_dim / 2`.
    fn rotate(&self, qkv: &mut [f32], grid: &[(usize, usize)]) {
        let d = self.n_embd;
        let hd = d / self.n_head;
        let (half, quarter) = (hd / 2, hd / 4);
        let freqs: Vec<f32> = (0..quarter)
            .map(|i| ROPE_BASE.powf(-(i as f32) / quarter as f32))
            .collect();
        qkv.par_chunks_exact_mut(3 * d)
            .zip(grid)
            .for_each(|(row, &(px, py))| {
                let angles: Vec<(f32, f32)> = (0..half)
                    .map(|i| {
                        let pos = if i < quarter { py } else { px };
                        (pos as f32 * freqs[i % quarter]).sin_cos()
                    })
                    .collect();
                for head in row[..2 * d].chunks_exact_mut(hd) {
                    for (i, &(sin, cos)) in angles.iter().enumerate() {
                        let (a, b) = (head[i], head[i + half]);
                        head[i] = a * cos - b * sin;
                        head[i + half] = a * sin + b * cos;
                    }
                }
            });
    }
}
