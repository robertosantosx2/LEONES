//! `kinetic quantize`: GGUF to GGUF, with llama-quantize's type mixtures and
//! its reference block encoding, so both tools write the same tensors.

use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

use kinetic_gguf::{GgufFile, TensorInfo, TensorOut, TensorType, Value};
use rayon::prelude::*;

use crate::Result;

/// A target as llama-quantize names it: its base type and llama.cpp's
/// `general.file_type` id.
struct Target {
    name: &'static str,
    base: TensorType,
    file_type: u32,
}

const TARGETS: &[Target] = &[
    Target {
        name: "Q4_0",
        base: TensorType::Q4_0,
        file_type: 2,
    },
    Target {
        name: "Q8_0",
        base: TensorType::Q8_0,
        file_type: 7,
    },
    Target {
        name: "Q4_K_M",
        base: TensorType::Q4K,
        file_type: 15,
    },
    Target {
        name: "Q5_K_M",
        base: TensorType::Q5K,
        file_type: 17,
    },
    Target {
        name: "Q6_K",
        base: TensorType::Q6K,
        file_type: 18,
    },
];

/// Quantizes `input` to `output` as `kind`, one of [`TARGETS`].
pub fn run(input: &Path, output: &Path, kind: &str) -> Result<()> {
    let target = TARGETS
        .iter()
        .find(|t| t.name.eq_ignore_ascii_case(kind))
        .ok_or_else(|| {
            let names: Vec<&str> = TARGETS.iter().map(|t| t.name).collect();
            format!("unknown type {kind}; use one of {}", names.join(", "))
        })?;
    let file = GgufFile::open(input).map_err(|e| format!("{}: {e}", input.display()))?;
    let header = file.header();
    if header.get("general.type").and_then(Value::as_str) == Some("adapter") {
        return Err("this is a LoRA adapter, not a model".into());
    }
    // llama-quantize's order, by layer and then by name: the mixture's layer
    // counters and the output follow it
    let mut order: Vec<&TensorInfo> = header.tensors.iter().collect();
    order.sort_by(|a, b| {
        let layer = |t: &TensorInfo| layer_of(&t.name).map_or(-1, |l| l as i64);
        (layer(a), a.name.as_bytes()).cmp(&(layer(b), b.name.as_bytes()))
    });

    let mut mix = Mixture::new(header, target);
    let out: Vec<TensorOut> = order
        .iter()
        .map(|t| TensorOut {
            name: t.name.clone(),
            dims: t.dims.clone(),
            ty: mix.type_for(t),
        })
        .collect();
    for (t, o) in order.iter().zip(&out) {
        if t.ty != o.ty
            && !matches!(
                t.ty,
                TensorType::F32 | TensorType::F16 | TensorType::BF16 | TensorType::Q8_0
            )
        {
            return Err(format!(
                "{} is {}; quantize from F32, F16, BF16 or Q8_0",
                t.name,
                t.ty.name()
            )
            .into());
        }
    }

    let mut metadata = header.metadata.clone();
    set(&mut metadata, "general.quantization_version", Value::U32(2));
    set(
        &mut metadata,
        "general.file_type",
        Value::U32(target.file_type),
    );
    let mut sink =
        BufWriter::new(File::create(output).map_err(|e| format!("{}: {e}", output.display()))?);
    let total = out.len();
    kinetic_gguf::write(&mut sink, &metadata, &out, |i| {
        let (t, o) = (order[i], &out[i]);
        eprint!(
            "\r[{:>4}/{total}] {:<40} {:>6} -> {:<6}",
            i + 1,
            t.name,
            t.ty.name(),
            o.ty.name()
        );
        Ok(convert(&file, t, o.ty))
    })?;
    sink.flush()?;
    eprintln!();
    Ok(())
}

/// Sets `key` last, as gguf_set_val moves a key it replaces to the end.
fn set(metadata: &mut Vec<(String, Value)>, key: &str, value: Value) {
    metadata.retain(|(k, _)| k != key);
    metadata.push((key.to_owned(), value));
}

/// The tensor's bytes as `ty`: copied when it keeps its type, otherwise
/// read to floats and quantized row by row.
fn convert(file: &GgufFile, t: &TensorInfo, ty: TensorType) -> Vec<u8> {
    let data = file.tensor_data(t);
    if ty == t.ty {
        return data.to_vec();
    }
    let cols = t.dims[0] as usize;
    let rows = (t.elements() / t.dims[0]) as usize;
    let (in_row, out_row) = (
        t.ty.bytes_for(cols as u64).expect("row size") as usize,
        ty.bytes_for(cols as u64).expect("row size") as usize,
    );
    let mut out = vec![0u8; rows * out_row];
    out.par_chunks_mut(out_row)
        .zip(data.par_chunks(in_row))
        .for_each_init(
            || vec![0.0f32; cols],
            |x, (dst, src)| {
                kinetic_quant::dequantize(t.ty, src, x).expect("readable source type");
                kinetic_quant::quantize(ty, x, dst);
            },
        );
    out
}

/// Which type each tensor gets, as llama.cpp's llama_tensor_get_type
/// decides for these targets without overrides or an importance matrix.
struct Mixture {
    target: &'static Target,
    tied: bool,
    layers: usize,
    experts: usize,
    attn_v: usize,
    attn_v_seen: usize,
    ffn_down_seen: usize,
}

impl Mixture {
    fn new(header: &kinetic_gguf::Gguf, target: &'static Target) -> Self {
        let key = |k: &str| header.arch_key(k).and_then(Value::as_u64).unwrap_or(0) as usize;
        Mixture {
            target,
            tied: header.tensor("output.weight").is_none(),
            layers: key("block_count"),
            experts: key("expert_count").max(1),
            attn_v: header.tensors.iter().filter(|t| is_attn_v(&t.name)).count(),
            attn_v_seen: 0,
            ffn_down_seen: 0,
        }
    }

    fn type_for(&mut self, t: &TensorInfo) -> TensorType {
        if !quantizable(t) {
            return t.ty;
        }
        let ty = self.mixed(t);
        fallback(ty, t.dims[0])
    }

    fn mixed(&mut self, t: &TensorInfo) -> TensorType {
        let name = t.name.as_str();
        let base = self.target.base;
        let k_mix = matches!(self.target.name, "Q4_K_M" | "Q5_K_M");
        let more_bits = |i: usize, n: usize| {
            i < n / 8 || i >= 7 * n / 8 || (i as i64 - (n / 8) as i64) % 3 == 2
        };
        let output = name == "output.weight"
            || (self.tied && matches!(name, "token_embd.weight" | "per_layer_token_embd.weight"));
        if output {
            return if !t.dims[0].is_multiple_of(base.block_len() as u64) {
                TensorType::Q8_0
            } else if base != TensorType::Q8_0 {
                TensorType::Q6K
            } else {
                base
            };
        }
        if matches!(name, "token_embd.weight" | "per_layer_token_embd.weight") {
            return base;
        }
        if is_attn_v(name) {
            let i = self.attn_v_seen;
            self.attn_v_seen += 1;
            if name.contains("attn_qkv.weight") {
                return match self.target.name {
                    "Q4_K_M" => TensorType::Q5K,
                    "Q5_K_M" => TensorType::Q6K,
                    _ => base,
                };
            }
            return match k_mix && more_bits(i, self.attn_v) {
                true => TensorType::Q6K,
                false => base,
            };
        }
        if name.contains("ffn_down") {
            let i = match self.experts > 1 {
                true => layer_of(name).unwrap_or(0),
                false => self.ffn_down_seen,
            };
            self.ffn_down_seen += 1;
            return match k_mix && more_bits(i, self.layers) {
                true => TensorType::Q6K,
                false => base,
            };
        }
        if name.contains("attn_output.weight") && self.experts == 8 && self.target.name == "Q4_K_M"
        {
            return TensorType::Q5K;
        }
        base
    }
}

fn is_attn_v(name: &str) -> bool {
    ["attn_qkv.weight", "attn_kv_b.weight", "attn_v.weight"]
        .iter()
        .any(|p| name.contains(p))
}

fn layer_of(name: &str) -> Option<usize> {
    name.strip_prefix("blk.")?.split('.').next()?.parse().ok()
}

/// Whether llama-quantize would quantize the tensor at all.
fn quantizable(t: &TensorInfo) -> bool {
    let name = t.name.as_str();
    let skipped = [
        "_norm.weight",
        "ffn_gate_inp.weight",
        "ffn_gate_tid2eid.weight",
        "altup",
        "laurel",
        "per_layer_model_proj",
        "ssm_conv1d",
        "shortconv.conv.weight",
        "indexer.k_proj.weight",
        "indexer.q_proj.weight",
        "time_mix_first.weight",
        "time_mix_w0.weight",
        "time_mix_w1.weight",
        "time_mix_w2.weight",
        "time_mix_v0.weight",
        "time_mix_v1.weight",
        "time_mix_v2.weight",
        "time_mix_a0.weight",
        "time_mix_a1.weight",
        "time_mix_a2.weight",
        "time_mix_g1.weight",
        "time_mix_g2.weight",
        "time_mix_decay_w1.weight",
        "time_mix_decay_w2.weight",
        "time_mix_lerp_fused.weight",
        "attn_rel_b.weight",
    ];
    t.dims.iter().filter(|&&d| d > 1).count() >= 2
        && name.ends_with("weight")
        && !skipped.iter().any(|s| name.contains(s))
        && !matches!(name, "position_embd.weight" | "token_types.weight")
}

/// llama-quantize's types for rows that are not a whole number of blocks.
fn fallback(ty: TensorType, cols: u64) -> TensorType {
    if cols.is_multiple_of(ty.block_len() as u64) {
        return ty;
    }
    match ty {
        TensorType::Q4K => TensorType::Q5_0,
        TensorType::Q5K => TensorType::Q5_1,
        TensorType::Q6K => TensorType::Q8_0,
        other => other,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn info(name: &str, dims: &[u64]) -> TensorInfo {
        TensorInfo {
            name: name.into(),
            dims: dims.to_vec(),
            ty: TensorType::F16,
            offset: 0,
            size: 0,
        }
    }

    #[test]
    fn q4_k_m_mixture_follows_llama_quantize() {
        let mut mix = Mixture {
            target: &TARGETS[2],
            tied: true,
            layers: 16,
            experts: 1,
            attn_v: 16,
            attn_v_seen: 0,
            ffn_down_seen: 0,
        };
        let mut ty = |n: &str, d: &[u64]| mix.type_for(&info(n, d));
        assert_eq!(ty("token_embd.weight", &[1024, 9000]), TensorType::Q6K);
        assert_eq!(ty("blk.0.attn_norm.weight", &[1024]), TensorType::F16);
        assert_eq!(ty("blk.0.attn_q.weight", &[1024, 1024]), TensorType::Q4K);
        // layers 0, 1 (n/8 = 2), then every third from 4, then 14, 15
        let v: Vec<bool> = (0..16)
            .map(|i| ty(&format!("blk.{i}.attn_v.weight"), &[1024, 256]) == TensorType::Q6K)
            .collect();
        let want: Vec<bool> = (0..16)
            .map(|i| [0, 1, 4, 7, 10, 13, 14, 15].contains(&i))
            .collect();
        assert_eq!(v, want);
        assert_eq!(ty("blk.0.ffn_up.weight", &[576, 1536]), TensorType::Q5_0);
        assert_eq!(ty("blk.0.ffn_gate_inp.weight", &[1024, 8]), TensorType::F16);
    }
}
