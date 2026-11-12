//! The Gemma 4 vision tower: 16-pixel patches with learned row and column
//! positions plus 2-D rotary positions, RMS norms around attention and the
//! gated GELU feed-forward, then 3x3 average pooling and one projection to
//! the language model's width.

use kinetic_cpu::matmul;
use kinetic_quant::Matrix;
use rayon::prelude::*;

#[cfg(feature = "cuda")]
mod cuda;

use crate::loader::Loader;
use crate::ops::{add, attention, gelu, patches, RmsNorm};
use crate::preprocess::{resize, target_size};
use crate::{Embeddings, Error, Pixels, Projector, RgbImage};

/// Image size limits of the processor, in image tokens.
const MIN_TOKENS: usize = 70;
const MAX_TOKENS: usize = 1120;

/// Patches a side averaged into one image token.
const POOL: usize = 3;

const ROPE_BASE: f32 = 100.0;

/// A projection without bias whose input and output may be clamped.
#[derive(Clone)]
struct Linear<'a> {
    w: Matrix<'a>,
    /// Input min and max, output min and max.
    clamp: Option<[f32; 4]>,
}

impl Linear<'_> {
    fn forward(&self, x: &[f32]) -> Vec<f32> {
        let mut y = vec![0.0; x.len() / self.w.cols * self.w.rows];
        match self.clamp {
            Some([lo, hi, out_lo, out_hi]) => {
                let x: Vec<f32> = x.par_iter().map(|v| v.clamp(lo, hi)).collect();
                matmul(&self.w, &x, &mut y);
                y.par_iter_mut().for_each(|v| *v = v.clamp(out_lo, out_hi));
            }
            None => matmul(&self.w, x, &mut y),
        }
        y
    }
}

#[derive(Clone)]
struct Block<'a> {
    norm1: RmsNorm,
    q: Linear<'a>,
    k: Linear<'a>,
    v: Linear<'a>,
    q_norm: RmsNorm,
    k_norm: RmsNorm,
    out: Linear<'a>,
    attn_post_norm: RmsNorm,
    norm2: RmsNorm,
    gate: Linear<'a>,
    up: Linear<'a>,
    down: Linear<'a>,
    ffn_post_norm: RmsNorm,
}

#[derive(Clone)]
struct Gemma4V<'a> {
    patch: usize,
    n_embd: usize,
    n_head: usize,
    eps: f32,
    patch_embd: Matrix<'a>,
    /// Column positions, then as many row positions, `n_embd` values each.
    pos_embd: Vec<f32>,
    pos_len: usize,
    blocks: Vec<Block<'a>>,
    proj: Linear<'a>,
}

/// Reads the `gemma4v` encoder from a projector file.
pub fn load<'a>(l: &Loader<'a>) -> Result<Box<dyn Projector<'a> + 'a>, Error> {
    let n_embd = l.usize("clip.vision.embedding_length")?;
    let n_ff = l.usize("clip.vision.feed_forward_length")?;
    let n_head = l.usize("clip.vision.attention.head_count")?;
    let patch = l.usize("clip.vision.patch_size")?;
    let n_out = l.usize("clip.vision.projection_dim")?;
    let eps = l.f32("clip.vision.attention.layer_norm_epsilon")?;
    let head_dim = n_embd / n_head;
    let norm = |name: &str, len| -> Result<RmsNorm, Error> {
        Ok(RmsNorm {
            w: l.vector(&format!("{name}.weight"), len)?,
            eps,
        })
    };
    let linear = |name: &str, cols, rows| -> Result<Linear<'a>, Error> {
        let scalar = |s: &str| l.vector(&format!("{name}.{s}"), 1).map(|v| v[0]);
        let clamp = ["input_min", "input_max", "output_min", "output_max"].map(scalar);
        Ok(Linear {
            w: l.matrix(&format!("{name}.weight"), cols, rows)?,
            clamp: match clamp {
                [Ok(a), Ok(b), Ok(c), Ok(d)] => Some([a, b, c, d]),
                _ => None,
            },
        })
    };
    let blocks = (0..l.usize("clip.vision.block_count")?)
        .map(|i| {
            let t = |s: &str| format!("v.blk.{i}.{s}");
            Ok(Block {
                norm1: norm(&t("ln1"), n_embd)?,
                q: linear(&t("attn_q"), n_embd, n_embd)?,
                k: linear(&t("attn_k"), n_embd, n_embd)?,
                v: linear(&t("attn_v"), n_embd, n_embd)?,
                q_norm: norm(&t("attn_q_norm"), head_dim)?,
                k_norm: norm(&t("attn_k_norm"), head_dim)?,
                out: linear(&t("attn_out"), n_embd, n_embd)?,
                attn_post_norm: norm(&t("attn_post_norm"), n_embd)?,
                norm2: norm(&t("ln2"), n_embd)?,
                gate: linear(&t("ffn_gate"), n_embd, n_ff)?,
                up: linear(&t("ffn_up"), n_embd, n_ff)?,
                down: linear(&t("ffn_down"), n_ff, n_embd)?,
                ffn_post_norm: norm(&t("ffn_post_norm"), n_embd)?,
            })
        })
        .collect::<Result<_, Error>>()?;
    let pos = l.tensor("v.position_embd.weight")?;
    if pos.dims.len() != 3 || pos.dims[0] != n_embd as u64 || pos.dims[2] != 2 {
        return Err(Error(format!(
            "v.position_embd.weight has shape {:?}",
            pos.dims
        )));
    }
    let pos_len = pos.dims[1] as usize;
    Ok(Box::new(Gemma4V {
        patch,
        n_embd,
        n_head,
        eps,
        patch_embd: l.patch_matrix("v.patch_embd.weight", 3 * patch * patch, n_embd)?,
        pos_embd: l.vector("v.position_embd.weight", 2 * pos_len * n_embd)?,
        pos_len,
        blocks,
        proj: linear("mm.input_projection", n_embd, n_out)?,
    }))
}

impl<'a> Projector<'a> for Gemma4V<'a> {
    fn n_embd_out(&self) -> usize {
        self.proj.w.rows
    }

    #[cfg(feature = "cuda")]
    fn cuda(&self) -> Result<Box<dyn crate::CudaProjector + 'a>, Error> {
        cuda::upload(self.clone())
    }

    fn prepare(&self, img: &RgbImage, max_tokens: usize) -> Pixels {
        let token = self.patch * POOL;
        let area = token * token;
        let (w, h) = target_size(
            img.width() as usize,
            img.height() as usize,
            token,
            (
                MIN_TOKENS * area,
                max_tokens.clamp(MIN_TOKENS, MAX_TOKENS) * area,
            ),
            false,
        );
        Pixels::normalized(&resize(img, w, h), [0.0; 3], [1.0; 3])
    }

    /// Takes pixels in `[0, 1]`; sides must be multiples of three patches.
    fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error> {
        let (cols, grid) = self.grid(pixels)?;
        let mut x = self.embed_patches(pixels, &grid);
        let d = self.n_embd;
        let hd = d / self.n_head;
        for b in &self.blocks {
            let mut h = x.clone();
            b.norm1.apply(&mut h, d);
            let (mut q, mut k, mut v) = (b.q.forward(&h), b.k.forward(&h), b.v.forward(&h));
            b.q_norm.apply(&mut q, hd);
            b.k_norm.apply(&mut k, hd);
            RmsNorm {
                w: Vec::new(),
                eps: self.eps,
            }
            .apply(&mut v, hd);
            self.rotate(&mut q, &grid);
            self.rotate(&mut k, &grid);
            // the tower attends unscaled; times sqrt(64) = 8 is exact
            let s = (hd as f32).sqrt();
            q.par_iter_mut().for_each(|v| *v *= s);
            let mut a = b
                .out
                .forward(&attention(&interleave(&q, &k, &v, d), self.n_head, hd));
            b.attn_post_norm.apply(&mut a, d);
            add(&mut x, &a);

            h.copy_from_slice(&x);
            b.norm2.apply(&mut h, d);
            let mut gate = b.gate.forward(&h);
            let up = b.up.forward(&h);
            gate.par_iter_mut()
                .zip(&up)
                .for_each(|(g, u)| *g = gelu(*g) * u);
            let mut f = b.down.forward(&gate);
            b.ffn_post_norm.apply(&mut f, d);
            add(&mut x, &f);
        }

        Ok(self.pool(&x, cols, grid.len() / cols))
    }
}

impl Gemma4V<'_> {
    /// The patches' columns a row and their (column, row) positions, for
    /// pixels whose sides are multiples of three patches.
    fn grid(&self, pixels: &Pixels) -> Result<(usize, Vec<(usize, usize)>), Error> {
        let token = self.patch * POOL;
        if !pixels.width.is_multiple_of(token) || !pixels.height.is_multiple_of(token) {
            return Err(Error(format!(
                "image of {}x{} is not a multiple of {token} pixels a side",
                pixels.width, pixels.height
            )));
        }
        let (cols, rows) = (pixels.width / self.patch, pixels.height / self.patch);
        if cols.max(rows) > self.pos_len {
            return Err(Error(format!(
                "image of {cols}x{rows} patches is wider than {} positions",
                self.pos_len
            )));
        }
        let grid = (0..rows)
            .flat_map(|y| (0..cols).map(move |x| (x, y)))
            .collect();
        Ok((cols, grid))
    }

    /// Patch embeddings plus the learned column and row positions.
    fn embed_patches(&self, pixels: &Pixels, grid: &[(usize, usize)]) -> Vec<f32> {
        let mut x = vec![0.0; grid.len() * self.n_embd];
        matmul(&self.patch_embd, &self.patch_rows(pixels, grid), &mut x);
        self.add_positions(&mut x, grid);
        x
    }

    /// The patches at `grid`, scaled from `[0, 1]` to `[-1, 1]`.
    fn patch_rows(&self, pixels: &Pixels, grid: &[(usize, usize)]) -> Vec<f32> {
        let scaled = Pixels {
            data: pixels.data.iter().map(|v| 2.0 * v - 1.0).collect(),
            width: pixels.width,
            height: pixels.height,
        };
        patches(&scaled, self.patch, grid)
    }

    fn add_positions(&self, x: &mut [f32], grid: &[(usize, usize)]) {
        let d = self.n_embd;
        let (col, row) = self.pos_embd.split_at(self.pos_len * d);
        x.par_chunks_exact_mut(d)
            .zip(grid)
            .for_each(|(x, &(px, py))| {
                add(x, &col[px * d..][..d]);
                add(x, &row[py * d..][..d]);
            });
    }

    /// Averages each 3x3 block of the tower's output rows over a grid of
    /// `cols` patches a row, normalizes and projects it to one image token.
    fn pool(&self, x: &[f32], cols: usize, rows: usize) -> Embeddings {
        let d = self.n_embd;
        let (out_cols, out_rows) = (cols / POOL, rows / POOL);
        let scale = (d as f32).sqrt() / (POOL * POOL) as f32;
        let mut pooled = vec![0.0; out_cols * out_rows * d];
        pooled
            .par_chunks_exact_mut(d)
            .enumerate()
            .for_each(|(i, out)| {
                let (ox, oy) = (i % out_cols, i / out_cols);
                for dy in 0..POOL {
                    for dx in 0..POOL {
                        let p = (oy * POOL + dy) * cols + ox * POOL + dx;
                        add(out, &x[p * d..][..d]);
                    }
                }
                out.iter_mut().for_each(|v| *v *= scale);
            });
        RmsNorm {
            w: Vec::new(),
            eps: self.eps,
        }
        .apply(&mut pooled, d);
        Embeddings {
            rows: self.proj.forward(&pooled),
            width: out_cols,
            height: out_rows,
        }
    }

    /// Rotates the first half of every head by the patch's column and the
    /// second half by its row, each half pairing value `i` with `i + hd / 4`.
    fn rotate(&self, x: &mut [f32], grid: &[(usize, usize)]) {
        let hd = self.n_embd / self.n_head;
        let (half, quarter) = (hd / 2, hd / 4);
        let freqs: Vec<f32> = (0..quarter)
            .map(|i| ROPE_BASE.powf(-((2 * i) as f32) / half as f32))
            .collect();
        x.par_chunks_exact_mut(self.n_embd)
            .zip(grid)
            .for_each(|(row, &(px, py))| {
                let angles = |pos: usize| -> Vec<(f32, f32)> {
                    freqs.iter().map(|f| (pos as f32 * f).sin_cos()).collect()
                };
                let (ax, ay) = (angles(px), angles(py));
                for head in row.chunks_exact_mut(hd) {
                    for (part, angles) in head.chunks_exact_mut(half).zip([&ax, &ay]) {
                        for (i, &(sin, cos)) in angles.iter().enumerate() {
                            let (a, b) = (part[i], part[i + quarter]);
                            part[i] = a * cos - b * sin;
                            part[i + quarter] = a * sin + b * cos;
                        }
                    }
                }
            });
    }
}

/// Rows of `n` queries, keys and values laid side by side, the layout
/// [`attention`] reads.
fn interleave(q: &[f32], k: &[f32], v: &[f32], n: usize) -> Vec<f32> {
    q.chunks_exact(n)
        .zip(k.chunks_exact(n))
        .zip(v.chunks_exact(n))
        .flat_map(|((q, k), v)| q.iter().chain(k).chain(v).copied())
        .collect()
}
