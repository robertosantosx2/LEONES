//! The Qwen3-VL vision transformer on a CUDA device: the same steps as on
//! the CPU, with matrix products and attention on the device.

use std::rc::Rc;

use kinetic_cuda::{
    Context, Device, DeviceBuffer, DeviceMatrix, GemvInput, Kernels, Stream, VisionKernels,
};
use kinetic_quant::Matrix;

use super::{Qwen3Vl, ROPE_BASE};
use crate::device::{cuda_error, f16_matrix, to_f32, upload_matrix};
use crate::ops::{add, patches, LayerNorm, Linear};
use crate::{CudaProjector, Embeddings, Error, Pixels};

struct DeviceLinear {
    w: DeviceMatrix,
    b: DeviceBuffer<f32>,
}

struct DeviceNorm {
    w: DeviceBuffer<f32>,
    b: DeviceBuffer<f32>,
    eps: f32,
}

struct DeviceBlock {
    norm1: DeviceNorm,
    qkv: DeviceLinear,
    out: DeviceLinear,
    norm2: DeviceNorm,
    up: DeviceLinear,
    down: DeviceLinear,
}

struct CudaQwen3Vl<'a> {
    host: Qwen3Vl<'a>,
    ctx: Rc<Context>,
    stream: Stream,
    kernels: Kernels,
    vision: VisionKernels,
    /// Both temporal slices of the patch embedding summed: a still image
    /// feeds them the same pixels.
    patch: DeviceMatrix,
    blocks: Vec<DeviceBlock>,
    post_norm: DeviceNorm,
    merger: [DeviceLinear; 2],
}

/// Uploads `host` to the first CUDA device.
pub fn upload(host: Qwen3Vl<'_>) -> Result<Box<dyn CudaProjector + '_>, Error> {
    let ctx = Context::new(Device::get(0).map_err(cuda_error)?).map_err(cuda_error)?;
    let matrix = |m: &Matrix| upload_matrix(&ctx, m);
    let vector = |v: &[f32]| DeviceBuffer::from_slice(&ctx, v).map_err(cuda_error);
    let linear = |l: &Linear| -> Result<DeviceLinear, Error> {
        Ok(DeviceLinear {
            w: matrix(&l.w)?,
            b: vector(&l.b)?,
        })
    };
    let norm = |n: &LayerNorm| -> Result<DeviceNorm, Error> {
        Ok(DeviceNorm {
            w: vector(&n.w)?,
            b: vector(&n.b)?,
            eps: n.eps,
        })
    };
    let [p0, p1] = &host.patch_embd;
    let mut summed = to_f32(p0)?;
    add(&mut summed, &to_f32(p1)?);
    let patch = f16_matrix(&ctx, &summed, p0.rows, p0.cols)?;
    let blocks = host
        .blocks
        .iter()
        .map(|b| {
            Ok(DeviceBlock {
                norm1: norm(&b.norm1)?,
                qkv: linear(&b.qkv)?,
                out: linear(&b.out)?,
                norm2: norm(&b.norm2)?,
                up: linear(&b.up)?,
                down: linear(&b.down)?,
            })
        })
        .collect::<Result<_, Error>>()?;
    let post_norm = norm(&host.post_norm)?;
    let merger = [linear(&host.merger[0])?, linear(&host.merger[1])?];
    Ok(Box::new(CudaQwen3Vl {
        host,
        stream: Stream::new(&ctx).map_err(cuda_error)?,
        kernels: Kernels::load(&ctx).map_err(cuda_error)?,
        vision: VisionKernels::load(&ctx).map_err(cuda_error)?,
        patch,
        blocks,
        post_norm,
        merger,
        ctx,
    }))
}

impl CudaProjector for CudaQwen3Vl<'_> {
    fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error> {
        let token = self.host.patch * self.host.merge;
        if !pixels.width.is_multiple_of(token) || !pixels.height.is_multiple_of(token) {
            return Err(Error(format!(
                "image of {}x{} is not a multiple of {token} pixels a side",
                pixels.width, pixels.height
            )));
        }
        self.run(pixels).map_err(cuda_error)
    }
}

impl CudaQwen3Vl<'_> {
    fn run(&self, pixels: &Pixels) -> kinetic_cuda::Result<Embeddings> {
        let host = &self.host;
        let token = host.patch * host.merge;
        let (ctx, k, v, s) = (&self.ctx, &self.kernels, &self.vision, &self.stream);
        let (p, d, heads) = (host.patch, host.n_embd, host.n_head);
        let hd = d / heads;
        let ff = self.blocks[0].up.w.rows();
        let grid = host.patch_grid(pixels.width, pixels.height);
        let n = grid.len();

        let mut input = GemvInput::batch(ctx, 3 * p * p, n)?;
        input.upload(k, &patches(pixels, p, &grid), s)?;
        let mut x = DeviceBuffer::new(ctx, n * d)?;
        k.gemv_rows(&self.patch, d, &input, 0..n, &mut x, s)?;
        let cols = pixels.width / p;
        let positions = host.positions(cols, pixels.height / p);
        let mut extra = vec![0.0; n * d];
        for (row, &(px, py)) in extra.chunks_exact_mut(d).zip(&grid) {
            row.copy_from_slice(&positions[(py * cols + px) * d..][..d]);
            add(row, &host.patch_bias);
        }
        let extra = DeviceBuffer::from_slice(ctx, &extra)?;
        v.residual(&mut x, Some(&extra), None, (n * d, d), s)?;
        let pos: Vec<u32> = grid
            .iter()
            .flat_map(|&(c, r)| [r as u32, c as u32])
            .collect();
        let pos = DeviceBuffer::from_slice(ctx, &pos)?;

        let mut h = GemvInput::batch(ctx, d, n)?;
        let mut hff = GemvInput::batch(ctx, ff, n)?;
        let mut qkv = DeviceBuffer::new(ctx, n * 3 * d)?;
        let mut y = DeviceBuffer::new(ctx, n * ff.max(d))?;
        for b in &self.blocks {
            v.layer_norm(
                k,
                &x,
                (&b.norm1.w, &b.norm1.b),
                b.norm1.eps,
                (n, d),
                &mut h,
                s,
            )?;
            v.matmul(k, &b.qkv.w, &h, n, &mut qkv, s)?;
            v.residual(&mut qkv, None, Some(&b.qkv.b), (n * 3 * d, 3 * d), s)?;
            v.rope_2d(&mut qkv, &pos, (n, heads, hd), ROPE_BASE, false, s)?;
            v.attention(k, &qkv, (n, heads, hd), &mut h, s)?;
            v.matmul(k, &b.out.w, &h, n, &mut y, s)?;
            v.residual(&mut x, Some(&y), Some(&b.out.b), (n * d, d), s)?;

            v.layer_norm(
                k,
                &x,
                (&b.norm2.w, &b.norm2.b),
                b.norm2.eps,
                (n, d),
                &mut h,
                s,
            )?;
            v.matmul(k, &b.up.w, &h, n, &mut y, s)?;
            v.bias(k, &y, &b.up.b, true, n, &mut hff, s)?;
            v.matmul(k, &b.down.w, &hff, n, &mut y, s)?;
            v.residual(&mut x, Some(&y), Some(&b.down.b), (n * d, d), s)?;
        }

        let (tokens, merged) = (n / (host.merge * host.merge), d * host.merge * host.merge);
        let norm = &self.post_norm;
        let mut m = GemvInput::batch(ctx, merged, tokens)?;
        v.layer_norm(k, &x, (&norm.w, &norm.b), norm.eps, (n, d), &mut m, s)?;
        let [m0, m1] = &self.merger;
        let mut ym = DeviceBuffer::new(ctx, tokens * merged)?;
        v.matmul(k, &m0.w, &m, tokens, &mut ym, s)?;
        v.bias(k, &ym, &m0.b, true, tokens, &mut m, s)?;
        let n_out = m1.w.rows();
        let mut out = DeviceBuffer::new(ctx, tokens * n_out)?;
        v.matmul(k, &m1.w, &m, tokens, &mut out, s)?;
        v.residual(&mut out, None, Some(&m1.b), (tokens * n_out, n_out), s)?;
        s.synchronize()?;
        Ok(Embeddings {
            rows: out.to_vec()?,
            width: pixels.width / token,
            height: pixels.height / token,
        })
    }
}
