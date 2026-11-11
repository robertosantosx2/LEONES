use crate::error::Result;
use crate::gemv::GemvInput;
use crate::kernels::{arg, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::{Function, LaunchConfig};
use crate::stream::Stream;

const ELEMENT_THREADS: u32 = 256;

impl Kernels {
    /// Queues `out = silu(gate) * up` for the first `rows` inputs of `out`.
    pub fn swiglu(
        &self,
        gate: &DeviceBuffer<f32>,
        up: &DeviceBuffer<f32>,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        self.gated(&self.swiglu_q8, gate, up, out, rows, stream)
    }

    /// Queues `out = gelu(gate) * up`, GELU in its tanh approximation, for
    /// the first `rows` inputs of `out`.
    pub fn geglu(
        &self,
        gate: &DeviceBuffer<f32>,
        up: &DeviceBuffer<f32>,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        self.gated(&self.geglu_q8, gate, up, out, rows, stream)
    }

    fn gated(
        &self,
        kernel: &Function,
        gate: &DeviceBuffer<f32>,
        up: &DeviceBuffer<f32>,
        out: &mut GemvInput,
        rows: usize,
        stream: &Stream,
    ) -> Result<()> {
        let n = rows * out.width();
        gate.check_holds(n, "swiglu gate")?;
        up.check_holds(n, "swiglu up")?;
        out.check_rows(rows)?;
        let (g, u, act, n) = (gate.device_ptr(), up.device_ptr(), out.act(), n as u32);
        let mut args = [arg(&g), arg(&u), arg(&act), arg(&n)];
        let config = LaunchConfig::linear(n.div_ceil(ELEMENT_THREADS), ELEMENT_THREADS);
        // SAFETY: matches `swiglu_q8` and `geglu_q8(const float*, const
        // float*, Act, unsigned)`; `n` elements of every buffer exist, as
        // checked.
        unsafe { kernel.launch(config, stream, &mut args) }
    }
}
