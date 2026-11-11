use kinetic_cuda::{DeviceBuffer, GemvInput, ValueHeads};

use super::scratch::by_width;
use super::{cuda_error, Gpu};
use crate::blocks::Folding;
use crate::LoadError;

/// A [`Folding`] on the device: its sign vectors, one per input width.
pub(super) struct CudaFolding {
    block: usize,
    signs: Vec<DeviceBuffer<f32>>,
    grouped_value_heads: bool,
}

impl CudaFolding {
    pub fn upload(gpu: &Gpu, f: &Folding) -> Result<CudaFolding, LoadError> {
        Ok(CudaFolding {
            block: f.block(),
            signs: f
                .sign_vectors()
                .iter()
                .map(|s| gpu.vector(s))
                .collect::<Result<_, _>>()
                .map_err(cuda_error)?,
            grouped_value_heads: f.grouped_value_heads(),
        })
    }

    fn signs(&self, width: usize) -> &DeviceBuffer<f32> {
        self.signs
            .iter()
            .find(|s| s.len() == width)
            .expect("checked at load")
    }

    /// Queues the first `n` rows of `x` as a folded weight reads them into
    /// the scratch input of their width in `folded`, and returns it.
    pub fn fold<'s>(
        &self,
        gpu: &Gpu,
        x: &GemvInput,
        folded: &'s mut [GemvInput],
        n: usize,
    ) -> kinetic_cuda::Result<&'s GemvInput> {
        self.fold_heads(gpu, x, None, folded, n)
    }

    /// [`CudaFolding::fold`] for delta-net outputs of `heads`.
    pub fn fold_heads<'s>(
        &self,
        gpu: &Gpu,
        x: &GemvInput,
        heads: Option<ValueHeads>,
        folded: &'s mut [GemvInput],
        n: usize,
    ) -> kinetic_cuda::Result<&'s GemvInput> {
        let width = x.width();
        let out = by_width(folded, width);
        let heads = heads.filter(|_| self.grouped_value_heads);
        gpu.kernels
            .fold(x, self.signs(width), self.block, heads, out, n, &gpu.stream)?;
        Ok(out)
    }

    /// Undoes the folding of `n` embedding rows of `width`, in place.
    pub fn restore(
        &self,
        gpu: &Gpu,
        x: &mut DeviceBuffer<f32>,
        width: usize,
        n: usize,
    ) -> kinetic_cuda::Result<()> {
        gpu.kernels
            .unfold(x, self.signs(width), self.block, n, &gpu.stream)
    }
}
