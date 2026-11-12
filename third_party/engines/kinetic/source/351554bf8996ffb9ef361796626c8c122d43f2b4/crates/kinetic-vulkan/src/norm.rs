use crate::batch::Batch;
use crate::commands::Commands;
use crate::error::{Error, Result};
use crate::gemv::GemvInput;
use crate::kernels::Kernels;
use crate::memory::DeviceBuffer;

/// A residual add to run before a norm: `x += scale * y`, where `y` first
/// takes an RMS norm by the weights `post` when given.
pub struct Residual<'a> {
    pub y: &'a DeviceBuffer<f32>,
    pub post: Option<&'a DeviceBuffer<f32>>,
    pub scale: f32,
}

impl Kernels {
    /// Records, for each token row of the batch, the optional residual add
    /// into `x` and then `out = rms_norm(x) * weight`.
    #[allow(clippy::too_many_arguments)]
    pub fn norm(
        &self,
        batch: &Batch,
        x: &DeviceBuffer<f32>,
        add: Option<Residual>,
        weight: &DeviceBuffer<f32>,
        eps: f32,
        out: &GemvInput,
        commands: &mut Commands,
    ) -> Result<()> {
        let len = out.width();
        let rows = batch.rows();
        let fits = |b: &DeviceBuffer<f32>| b.len() >= rows * len;
        if weight.len() != len
            || !fits(x)
            || add.as_ref().is_some_and(|a| !fits(a.y))
            || add
                .as_ref()
                .and_then(|a| a.post)
                .is_some_and(|p| p.len() != len)
            || out.rows() < rows
        {
            return Err(Error::Shape(format!(
                "norm of {rows} rows of {len} with {} weights",
                weight.len()
            )));
        }
        let (y, scale) = add.as_ref().map_or((x, 0.0), |a| (a.y, a.scale));
        let post = add.as_ref().and_then(|a| a.post);
        let flags = u32::from(add.is_some()) | (u32::from(post.is_some()) << 1);
        let [ox, oq, od] = out.outputs();
        // SAFETY: matches norm.wgsl: the batch, x, y, weight, the three
        // output buffers and the post weights at bindings 0..7, then length,
        // eps, flags and scale. Every buffer holds the batch's rows, checked
        // above, and workgroups past the pass's tokens return early; `y` is
        // read only with an add and the post weights only when given.
        unsafe {
            commands.dispatch(
                &self.norm,
                &[
                    batch.device().allocation(),
                    x.allocation(),
                    y.allocation(),
                    weight.allocation(),
                    ox,
                    oq,
                    od,
                    post.unwrap_or(weight).allocation(),
                ],
                &[len as u32, eps.to_bits(), flags, scale.to_bits()],
                [rows as u32, 1, 1],
            )
        };
        Ok(())
    }
}
