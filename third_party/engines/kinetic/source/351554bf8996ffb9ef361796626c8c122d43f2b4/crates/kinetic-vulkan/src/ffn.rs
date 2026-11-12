use crate::batch::Batch;
use crate::commands::Commands;
use crate::error::{Error, Result};
use crate::gemv::GemvInput;
use crate::kernels::Kernels;
use crate::memory::DeviceBuffer;

impl Kernels {
    /// Records `out = silu(gate) * up` for each token row of the batch,
    /// where a row of `gu` holds `out.width()` gate values and then as many
    /// up values.
    pub fn swiglu(
        &self,
        batch: &Batch,
        gu: &DeviceBuffer<f32>,
        out: &GemvInput,
        commands: &mut Commands,
    ) -> Result<()> {
        let (len, rows) = (out.width(), batch.rows());
        if gu.len() < 2 * rows * len || out.rows() < rows {
            return Err(Error::Shape(format!(
                "SwiGLU of {rows} rows of {len} from {} values",
                gu.len()
            )));
        }
        let [ox, oq, od] = out.outputs();
        // SAFETY: matches swiglu.wgsl: the batch, gu and the three output
        // buffers at bindings 0..4, then the length; the buffers hold the
        // batch's rows, checked above, and invocations past them return.
        unsafe {
            commands.dispatch(
                &self.swiglu,
                &[batch.device().allocation(), gu.allocation(), ox, oq, od],
                &[len as u32],
                [len.div_ceil(256) as u32, rows as u32, 1],
            )
        };
        Ok(())
    }
}
