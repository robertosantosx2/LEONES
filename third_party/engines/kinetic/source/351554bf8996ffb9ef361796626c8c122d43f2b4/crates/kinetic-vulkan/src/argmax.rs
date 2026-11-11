use crate::batch::Batch;
use crate::commands::Commands;
use crate::error::{Error, Result};
use crate::kernels::Kernels;
use crate::memory::DeviceBuffer;

impl Kernels {
    /// Records the greedy token of each row the output head ran on: the
    /// index of the largest of its `vocab` logits, the lowest among equals,
    /// followed by the bits of that logit: two words per row.
    pub fn argmax(
        &self,
        batch: &Batch,
        logits: &DeviceBuffer<f32>,
        vocab: usize,
        best: &DeviceBuffer<u32>,
        commands: &mut Commands,
    ) -> Result<()> {
        let rows = batch.head_rows();
        if vocab == 0 || logits.len() < rows * vocab || best.len() < 2 * rows {
            return Err(Error::Shape(format!(
                "argmax of {rows} rows of {vocab} logits"
            )));
        }
        // SAFETY: matches argmax.wgsl: the batch, logits and output at
        // bindings 0..2, then the vocabulary size; both buffers hold the
        // head's rows, checked above.
        unsafe {
            commands.dispatch(
                &self.argmax,
                &[
                    batch.device().allocation(),
                    logits.allocation(),
                    best.allocation(),
                ],
                &[vocab as u32],
                [rows.max(1) as u32, 1, 1],
            )
        };
        Ok(())
    }
}
