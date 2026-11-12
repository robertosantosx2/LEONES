use std::rc::Rc;

use crate::context::Context;
use crate::error::{Error, Result};
use crate::kernels::{arg, Kernels};
use crate::memory::DeviceBuffer;
use crate::module::LaunchConfig;
use crate::stream::Stream;

/// Values per partial result; must match ARGMAX_CHUNK in argmax.cuh.
const CHUNK: usize = 4096;
const PARTIAL_THREADS: u32 = 256;

/// The working buffer and results of [`Kernels::argmax`] for up to `rows`
/// rows of up to `len` values.
pub struct Argmax {
    partial: DeviceBuffer<u32>,
    best: DeviceBuffer<u32>,
    len: usize,
}

impl Argmax {
    pub fn new(ctx: &Rc<Context>, rows: usize, len: usize) -> Result<Argmax> {
        Ok(Argmax {
            partial: DeviceBuffer::new(ctx, 2 * rows * len.div_ceil(CHUNK))?,
            best: DeviceBuffer::new(ctx, rows)?,
            len,
        })
    }

    /// The index found for each row by the last [`Kernels::argmax`].
    pub fn best(&self) -> &DeviceBuffer<u32> {
        &self.best
    }
}

impl Kernels {
    /// Queues, for each `r < rows`, the index of the largest of
    /// `x[r * len..][..len]` into `out`; the lowest index wins a tie.
    pub fn argmax(
        &self,
        x: &DeviceBuffer<f32>,
        len: usize,
        rows: usize,
        out: &mut Argmax,
        stream: &Stream,
    ) -> Result<()> {
        if len == 0 || len > out.len || u32::try_from(len).is_err() {
            return Err(Error::Shape(format!(
                "argmax over {len} values with room for {}",
                out.len
            )));
        }
        x.check_holds(rows * len, "argmax input")?;
        out.best.check_holds(rows, "argmax output")?;
        let parts = len.div_ceil(CHUNK) as u32;
        let (xp, n, pp, bp) = (
            x.device_ptr(),
            len as u32,
            out.partial.device_ptr(),
            out.best.device_ptr(),
        );
        let config = LaunchConfig {
            grid: [rows as u32, parts, 1],
            block: [PARTIAL_THREADS, 1, 1],
            shared_bytes: 0,
        };
        // SAFETY: `argmax_partial(const float*, unsigned, unsigned, uint2*)`
        // reads `rows * len` values and writes `rows * parts` pairs, which
        // `partial` holds since `len <= out.len`; `argmax_final(const uint2*,
        // unsigned, unsigned*)` reads those pairs and writes `rows` indices.
        unsafe {
            self.argmax_partial.launch(
                config,
                stream,
                &mut [arg(&xp), arg(&n), arg(&parts), arg(&pp)],
            )?;
            self.argmax_final.launch(
                LaunchConfig::linear(rows as u32, 32),
                stream,
                &mut [arg(&pp), arg(&parts), arg(&bp)],
            )
        }
    }
}
