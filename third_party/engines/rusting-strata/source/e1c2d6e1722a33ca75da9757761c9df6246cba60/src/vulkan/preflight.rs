//! Shared-memory preflight for the Vulkan pipelines a model needs.
//!
//! `Vk::pipeline` refuses a pipeline whose `Workgroup` size exceeds `maxComputeSharedMemorySize`, which is the only
//! place where one can be created. `Vk::preflight` runs the same accounting ahead of the first pipeline, over the
//! (kernel, specialization) pairs the model's weight types reach, so a doomed model fails before any weight is
//! uploaded (and before any pipeline or buffer exists). It is SPIR-V plus spec-constant arithmetic only.

use anyhow::Result;
use crate::quant::GgmlType;
use super::{Vk, spv_smem};
use std::collections::HashSet;
use std::time::Instant;

impl Vk {
    /// The `Workgroup` bytes of kernel `name` with `spec` and this device's `--kv q8` setting.
    pub fn shared_bytes(&self, name: &str, spec: &[u32]) -> Result<u32> {
        spv_smem::shared_bytes(name, spec, self.0.kv_q8)
    }

    /// Check the (kernel, specialization) pairs the weight types `types` reach (see `gpu_model::gpu_weight_types`)
    /// against this device's limit. `verbose` lists each pair; the summary line names the pair with the most bytes.
    ///
    /// Mirrors `gemm_raw`'s kernel choice: without cooperative matrices `gemm_f_dp` / `gemmi_dp` run, with them the
    /// full `gemm_f` / `gemmi` (and `gemm_fs` / `gemmi_s` for small dense tiles). `gemv_q`/`gemv_f` take `NT` (1 to 4)
    /// and `gemv_f` `32 * wpb` (8 rows a workgroup for tall matrices, else 1) as further constants, so the largest of
    /// each is checked. No pipeline, buffer or dispatch is created here.
    pub fn preflight(&self, types: &[GgmlType], verbose: bool) -> Result<()> {
        let t0 = Instant::now();
        let mut checked = HashSet::new();
        let (mut n, mut worst) = (0usize, (0u32, "", Vec::new()));
        for (name, spec) in self.shared_memory_pairs(types) {
            if !checked.insert((name, spec.clone())) { continue; }
            let bytes = spv_smem::check_shared_memory(name, &spec, self.0.kv_q8, self.0.smem_limit)?;
            n += 1;
            if verbose { eprintln!("vulkan: preflight {name} {spec:?}: {bytes} bytes"); }
            if bytes > worst.0 { worst = (bytes, name, spec); }
        }
        eprintln!("vulkan: shared-memory preflight: {n} (kernel, specialization) pairs checked, largest {} bytes \
            ({}) of {} allowed, {:.1} ms", worst.0, worst.1, self.0.smem_limit, t0.elapsed().as_secs_f64() * 1e3);
        Ok(())
    }

    /// The largest shared-memory request among the `(kernel, specialization)` pairs `types` reach, checked against
    /// this device's limit (the same accounting as `preflight`, without the listing). Returns the byte count.
    pub fn max_shared_bytes(&self, types: &[GgmlType]) -> Result<u32> {
        let mut checked = HashSet::new();
        let mut max = 0;
        for (name, spec) in self.shared_memory_pairs(types) {
            if !checked.insert((name, spec.clone())) { continue; }
            max = max.max(spv_smem::check_shared_memory(name, &spec, self.0.kv_q8, self.0.smem_limit)?);
        }
        Ok(max)
    }

    /// `(kernel, specialization)` pairs: the same vectors `gemm_raw`, `gemvq`, `moe_gemv` and `dequant` pass to
    /// `pipeline`.
    fn shared_memory_pairs(&self, types: &[GgmlType]) -> Vec<(&'static str, Vec<u32>)> {
        let mut pairs: Vec<(&'static str, Vec<u32>)> = Vec::new();
        for &ty in types {
            let ws = self.wspec(ty).to_vec();
            let float = matches!(ty, GgmlType::F32 | GgmlType::BF16);
            let mut push = |name: &'static str, spec: Vec<u32>| pairs.push((name, spec));
            // gemm_raw: `f = !mmq(ty) || cols % 128 != 0`; the float kernel takes every type, the int8 one the rest.
            if float || !crate::cuda::Gpu::mmq(ty) {
                if self.0.coop { push("gemm_f", ws.clone()); push("gemm_fs", ws.clone()); }
                else { push("gemm_f_dp", ws.clone()); }
            }
            if !float {
                if self.0.coop_i8 { push("gemmi", ws.clone()); push("gemmi_s", ws.clone()); }
                else { push("gemmi_dp", ws.clone()); }
                for nt in 1..=4 { push("gemv_q", [&ws[..], &[nt]].concat()); }
                push("moe_gemv_q", ws.clone());
                push("dequant", ws.clone());
            } else {
                for nt in 1..=4 { for wpb in [1u32, 8] { push("gemv_f", [&ws[..], &[nt, 32 * wpb]].concat()); } }
                push("moe_gemv_f", ws.clone());
            }
        }
        pairs
    }
}
