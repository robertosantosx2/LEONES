//! LoRA adapters in llama.cpp's GGUF format, merged into the base weights
//! at load: each adapted matrix becomes `W + scale * B·A` in F32.

use std::collections::HashMap;

use kinetic_gguf::{Gguf, TensorInfo, TensorSource, TensorType};
use rayon::prelude::*;

use crate::LoadError;

/// One adapter file and the scale it is applied with, as `--lora-scaled`.
pub struct Adapter<'f> {
    pub file: &'f dyn TensorSource,
    pub scale: f32,
}

/// A model file with adapters merged in, to load in its place.
pub struct Adapted<'a> {
    base: &'a dyn TensorSource,
    header: Gguf,
    merged: HashMap<String, Vec<u8>>,
}

impl<'a> Adapted<'a> {
    /// Merges `adapters` into `base`, checking that each was made for it.
    pub fn new(base: &'a dyn TensorSource, adapters: &[Adapter]) -> Result<Self, LoadError> {
        let mut weights: HashMap<String, Vec<f32>> = HashMap::new();
        for adapter in adapters {
            for (name, a, b, alpha) in pairs(adapter.file)? {
                let w = base
                    .header()
                    .tensor(&name)
                    .ok_or_else(|| err(format!("{name} is not in the model")))?;
                check_shapes(w, a, b)?;
                let rank = b.dims[0] as f32;
                // llama.cpp reads alpha 0 as "no alpha": the scale as given
                let scale = if alpha == 0.0 {
                    adapter.scale
                } else {
                    adapter.scale * alpha / rank
                };
                if !weights.contains_key(&name) {
                    weights.insert(name.clone(), floats(base, w)?);
                }
                let target = weights.get_mut(&name).expect("inserted above");
                let a = floats(adapter.file, a)?;
                let b = floats(adapter.file, b)?;
                add_product(
                    target,
                    &b,
                    &a,
                    b.len() / rank as usize,
                    rank as usize,
                    scale,
                );
            }
        }
        let mut header = base.header().clone();
        let mut merged = HashMap::new();
        for (name, values) in weights {
            let info = header
                .tensors
                .iter_mut()
                .find(|t| t.name == name)
                .expect("the tensor was found above");
            info.ty = TensorType::F32;
            info.size = values.len() as u64 * 4;
            merged.insert(name, values.iter().flat_map(|v| v.to_le_bytes()).collect());
        }
        Ok(Adapted {
            base,
            header,
            merged,
        })
    }
}

impl TensorSource for Adapted<'_> {
    fn header(&self) -> &Gguf {
        &self.header
    }

    fn tensor_data(&self, tensor: &TensorInfo) -> &[u8] {
        match self.merged.get(&tensor.name) {
            Some(bytes) => bytes,
            None => self.base.tensor_data(tensor),
        }
    }
}

fn err(msg: String) -> LoadError {
    LoadError(format!("LoRA adapter: {msg}"))
}

/// Each adapted tensor's name with its `lora_a` and `lora_b` and the
/// adapter's alpha.
fn pairs(
    file: &dyn TensorSource,
) -> Result<Vec<(String, &TensorInfo, &TensorInfo, f32)>, LoadError> {
    let h = file.header();
    let text = |key: &str| h.get(key).and_then(|v| v.as_str()).unwrap_or_default();
    if text("general.type") != "adapter" || text("adapter.type") != "lora" {
        return Err(err(
            "not a LoRA adapter (general.type must be adapter, adapter.type lora)".into(),
        ));
    }
    let alpha = h
        .get("adapter.lora.alpha")
        .and_then(|v| v.as_f32())
        .unwrap_or(0.0);
    let mut out = Vec::new();
    for a in &h.tensors {
        let Some(name) = a.name.strip_suffix(".lora_a") else {
            continue;
        };
        let b = h
            .tensor(&format!("{name}.lora_b"))
            .ok_or_else(|| err(format!("{name}.lora_a has no lora_b")))?;
        if name == "token_embd.weight" {
            return Err(err("adapters on token_embd are not supported".into()));
        }
        out.push((name.to_owned(), a, b, alpha));
    }
    if out.is_empty() {
        return Err(err("no lora_a/lora_b tensors".into()));
    }
    Ok(out)
}

fn check_shapes(w: &TensorInfo, a: &TensorInfo, b: &TensorInfo) -> Result<(), LoadError> {
    let ok = w.dims.len() == 2
        && a.dims.len() == 2
        && b.dims.len() == 2
        && w.dims[0] == a.dims[0]
        && w.dims[1] == b.dims[1]
        && a.dims[1] == b.dims[0];
    match ok {
        true => Ok(()),
        false => Err(err(format!(
            "{} is {:?} but lora_a is {:?} and lora_b {:?} (made for another model?)",
            w.name, w.dims, a.dims, b.dims
        ))),
    }
}

fn floats(file: &dyn TensorSource, t: &TensorInfo) -> Result<Vec<f32>, LoadError> {
    let mut out = vec![0.0; t.elements() as usize];
    kinetic_quant::dequantize(t.ty, file.tensor_data(t), &mut out).map_err(|_| {
        err(format!(
            "{} is stored as {:?}, which cannot be read",
            t.name, t.ty
        ))
    })?;
    Ok(out)
}

/// `w[o][i] += scale * sum_k b[o][k] * a[k][i]`: `w` is `rows` rows of
/// `a`'s row length, `b` is `rows` by `rank`, `a` is `rank` rows.
fn add_product(w: &mut [f32], b: &[f32], a: &[f32], rows: usize, rank: usize, scale: f32) {
    let cols = a.len() / rank;
    w.par_chunks_mut(cols)
        .zip(b.par_chunks(rank))
        .take(rows)
        .for_each_init(
            || vec![0.0f32; cols],
            |sum, (row, b)| {
                sum.fill(0.0);
                for (k, &bk) in b.iter().enumerate() {
                    for (s, &x) in sum.iter_mut().zip(&a[k * cols..][..cols]) {
                        *s += bk * x;
                    }
                }
                for (w, s) in row.iter_mut().zip(sum.iter()) {
                    *w += scale * s;
                }
            },
        );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merged_matrix_is_base_plus_scaled_adapter_path() {
        let (rows, cols, rank) = (5, 7, 3);
        let f = |i: usize, m: f32| ((i * 37 % 11) as f32 - 5.0) * m;
        let w: Vec<f32> = (0..rows * cols).map(|i| f(i, 0.1)).collect();
        let a: Vec<f32> = (0..rank * cols).map(|i| f(i + 3, 0.05)).collect();
        let b: Vec<f32> = (0..rows * rank).map(|i| f(i + 7, 0.2)).collect();
        let x: Vec<f32> = (0..cols).map(|i| f(i + 1, 0.3)).collect();
        let scale = 0.75;
        let mut merged = w.clone();
        add_product(&mut merged, &b, &a, rows, rank, scale);

        // llama.cpp's graph: W x + scale * B (A x)
        let ax: Vec<f64> = (0..rank)
            .map(|k| (0..cols).map(|i| (a[k * cols + i] * x[i]) as f64).sum())
            .collect();
        for o in 0..rows {
            let wx: f64 = (0..cols).map(|i| (w[o * cols + i] * x[i]) as f64).sum();
            let bax: f64 = (0..rank).map(|k| b[o * rank + k] as f64 * ax[k]).sum();
            let want = wx + scale as f64 * bax;
            let got: f64 = (0..cols)
                .map(|i| merged[o * cols + i] as f64 * x[i] as f64)
                .sum();
            assert!((got - want).abs() < 1e-5, "row {o}: {got} vs {want}");
        }
    }
}
