//! The Gemma 4 vision tower on a CUDA device. The patches run through every
//! block on the device; pooling and the projection of the few image tokens
//! stay on the host.

use std::rc::Rc;

use kinetic_cuda::{
    Context, Device, DeviceBuffer, DeviceMatrix, GemvInput, Kernels, Stream, VisionKernels,
};

use super::{Gemma4V, Linear, ROPE_BASE};
use crate::device::{cuda_error, f16_matrix, to_f32, upload_matrix};
use crate::{CudaProjector, Embeddings, Error, Pixels};

/// A projection and the `[min, max]` bounds of its input and output.
struct Clamped {
    w: DeviceMatrix,
    input: DeviceBuffer<f32>,
    output: DeviceBuffer<f32>,
}

struct DeviceBlock {
    norm1: DeviceBuffer<f32>,
    /// Queries, keys and values stacked, so that one product writes the
    /// rows attention reads.
    qkv: Clamped,
    /// Query, key and value head norms, the queries' scaled by
    /// `sqrt(head_dim)` to undo the attention kernel's scale.
    head_norms: DeviceBuffer<f32>,
    out: Clamped,
    attn_post_norm: DeviceBuffer<f32>,
    norm2: DeviceBuffer<f32>,
    gate: Clamped,
    up: Clamped,
    down: Clamped,
    ffn_post_norm: DeviceBuffer<f32>,
}

struct CudaGemma4V<'a> {
    host: Gemma4V<'a>,
    ctx: Rc<Context>,
    stream: Stream,
    kernels: Kernels,
    vision: VisionKernels,
    patch: DeviceMatrix,
    blocks: Vec<DeviceBlock>,
}

/// `[min, max]` of the input and of the output; unbounded without a clamp.
fn bounds(l: &Linear) -> ([f32; 2], [f32; 2]) {
    let [a, b, c, d] = l.clamp.unwrap_or([
        f32::NEG_INFINITY,
        f32::INFINITY,
        f32::NEG_INFINITY,
        f32::INFINITY,
    ]);
    ([a, b], [c, d])
}

/// Uploads `host` to the first CUDA device.
pub fn upload(host: Gemma4V<'_>) -> Result<Box<dyn CudaProjector + '_>, Error> {
    let ctx = Context::new(Device::get(0).map_err(cuda_error)?).map_err(cuda_error)?;
    let vector = |v: &[f32]| DeviceBuffer::from_slice(&ctx, v).map_err(cuda_error);
    let clamped = |l: &Linear| -> Result<Clamped, Error> {
        let (input, output) = bounds(l);
        Ok(Clamped {
            w: upload_matrix(&ctx, &l.w)?,
            input: vector(&input)?,
            output: vector(&output)?,
        })
    };
    let hd = host.n_embd / host.n_head;
    let blocks = host
        .blocks
        .iter()
        .map(|b| {
            let (input, _) = bounds(&b.q);
            if [&b.k, &b.v].iter().any(|l| bounds(l).0 != input)
                || bounds(&b.gate).0 != bounds(&b.up).0
            {
                return Err(Error(
                    "projections that share an input clamp it differently".into(),
                ));
            }
            let mut qkv = Vec::with_capacity(3 * b.q.w.rows * b.q.w.cols);
            let mut output = Vec::with_capacity(6);
            for l in [&b.q, &b.k, &b.v] {
                qkv.extend(to_f32(&l.w)?);
                output.extend(bounds(l).1);
            }
            let scale = (hd as f32).sqrt();
            let head_norms: Vec<f32> = (b.q_norm.w.iter().map(|w| w * scale))
                .chain(b.k_norm.w.iter().copied())
                .chain(std::iter::repeat_n(1.0, hd))
                .collect();
            Ok(DeviceBlock {
                norm1: vector(&b.norm1.w)?,
                qkv: Clamped {
                    w: f16_matrix(&ctx, &qkv, 3 * b.q.w.rows, b.q.w.cols)?,
                    input: vector(&input)?,
                    output: vector(&output)?,
                },
                head_norms: vector(&head_norms)?,
                out: clamped(&b.out)?,
                attn_post_norm: vector(&b.attn_post_norm.w)?,
                norm2: vector(&b.norm2.w)?,
                gate: clamped(&b.gate)?,
                up: clamped(&b.up)?,
                down: clamped(&b.down)?,
                ffn_post_norm: vector(&b.ffn_post_norm.w)?,
            })
        })
        .collect::<Result<_, Error>>()?;
    Ok(Box::new(CudaGemma4V {
        patch: upload_matrix(&ctx, &host.patch_embd)?,
        host,
        stream: Stream::new(&ctx).map_err(cuda_error)?,
        kernels: Kernels::load(&ctx).map_err(cuda_error)?,
        vision: VisionKernels::load(&ctx).map_err(cuda_error)?,
        blocks,
        ctx,
    }))
}

impl CudaProjector for CudaGemma4V<'_> {
    fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error> {
        let (cols, grid) = self.host.grid(pixels)?;
        let x = self.run(pixels, &grid).map_err(cuda_error)?;
        Ok(self.host.pool(&x, cols, grid.len() / cols))
    }
}

impl CudaGemma4V<'_> {
    /// The tower's output rows for the patches at `grid`.
    fn run(&self, pixels: &Pixels, grid: &[(usize, usize)]) -> kinetic_cuda::Result<Vec<f32>> {
        let host = &self.host;
        let (ctx, k, v, s) = (&self.ctx, &self.kernels, &self.vision, &self.stream);
        let (p, d, heads, eps) = (host.patch, host.n_embd, host.n_head, host.eps);
        let hd = d / heads;
        let ff = self.blocks[0].gate.w.rows();
        let n = grid.len();

        let mut input = GemvInput::batch(ctx, 3 * p * p, n)?;
        input.upload(k, &host.patch_rows(pixels, grid), s)?;
        let mut x = DeviceBuffer::new(ctx, n * d)?;
        k.gemv_rows(&self.patch, d, &input, 0..n, &mut x, s)?;
        drop(input);
        let mut positions = vec![0.0; n * d];
        host.add_positions(&mut positions, grid);
        let positions = DeviceBuffer::from_slice(ctx, &positions)?;
        v.residual(&mut x, Some(&positions), None, (n * d, d), s)?;
        drop(positions);
        let pos: Vec<u32> = grid
            .iter()
            .flat_map(|&(c, r)| [c as u32, r as u32])
            .collect();
        let pos = DeviceBuffer::from_slice(ctx, &pos)?;

        let mut t = DeviceBuffer::new(ctx, n * d)?;
        let mut h = GemvInput::batch(ctx, d, n)?;
        let mut a = GemvInput::batch(ctx, d, n)?;
        let mut hff = GemvInput::batch(ctx, ff, n)?;
        let mut qkv = DeviceBuffer::new(ctx, n * 3 * d)?;
        let mut gate = DeviceBuffer::new(ctx, n * ff)?;
        let mut up = DeviceBuffer::new(ctx, n * ff)?;
        let norm = |x: &mut DeviceBuffer<f32>, w: &DeviceBuffer<f32>| {
            v.rms_norm(x, w, (n, d), (1, 1), eps, s)
        };
        for b in &self.blocks {
            t.copy_from_device(0, &x, 0..n * d, s)?;
            norm(&mut t, &b.norm1)?;
            v.clamp(k, &t, &b.qkv.input, n, &mut h, s)?;
            v.matmul(k, &b.qkv.w, &h, n, &mut qkv, s)?;
            v.clamp_in_place(&mut qkv, &b.qkv.output, (n * 3 * d, 3 * d), s)?;
            v.rms_norm(
                &mut qkv,
                &b.head_norms,
                (3 * n * heads, hd),
                (heads, 3),
                eps,
                s,
            )?;
            v.rope_2d(&mut qkv, &pos, (n, heads, hd), ROPE_BASE, true, s)?;
            v.attention(k, &qkv, (n, heads, hd), &mut a, s)?;
            v.clamp(k, a.values(), &b.out.input, n, &mut h, s)?;
            v.matmul(k, &b.out.w, &h, n, &mut t, s)?;
            v.clamp_in_place(&mut t, &b.out.output, (n * d, d), s)?;
            norm(&mut t, &b.attn_post_norm)?;
            v.residual(&mut x, Some(&t), None, (n * d, d), s)?;

            t.copy_from_device(0, &x, 0..n * d, s)?;
            norm(&mut t, &b.norm2)?;
            v.clamp(k, &t, &b.gate.input, n, &mut h, s)?;
            v.matmul(k, &b.gate.w, &h, n, &mut gate, s)?;
            v.matmul(k, &b.up.w, &h, n, &mut up, s)?;
            v.clamp_in_place(&mut gate, &b.gate.output, (n * ff, ff), s)?;
            v.clamp_in_place(&mut up, &b.up.output, (n * ff, ff), s)?;
            v.geglu(&mut gate, &up, n * ff, s)?;
            v.clamp(k, &gate, &b.down.input, n, &mut hff, s)?;
            v.matmul(k, &b.down.w, &hff, n, &mut t, s)?;
            v.clamp_in_place(&mut t, &b.down.output, (n * d, d), s)?;
            norm(&mut t, &b.ffn_post_norm)?;
            v.residual(&mut x, Some(&t), None, (n * d, d), s)?;
        }
        s.synchronize()?;
        x.to_vec()
    }
}
