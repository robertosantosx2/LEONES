//! A synthetic LoRA adapter on a real model: the merged weights match a
//! merge done here in f64, the way llama.cpp applies the adapter
//! (W x + scale * B (A x)), and so do the logits.
//!
//! KINETIC_TEST_GGUF=SmolLM2-135M-Instruct-f16.gguf cargo test --release -p kinetic-models --test lora -- --ignored

use std::collections::HashMap;

use kinetic_gguf::{Gguf, GgufFile, TensorInfo, TensorOut, TensorSource, TensorType, Value};
use kinetic_models::lora::{Adapted, Adapter};
use kinetic_models::Model;

const RANK: usize = 4;
const ALPHA: f32 = 8.0;
const SCALE: f32 = 0.5;
const TARGETS: &[&str] = &["attn_q", "attn_v", "ffn_down"];

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> f32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        ((self.0 >> 40) as f32 / (1u64 << 24) as f32 - 0.5) * 0.2
    }
}

fn floats(file: &dyn TensorSource, t: &TensorInfo) -> Vec<f32> {
    let mut out = vec![0.0; t.elements() as usize];
    kinetic_quant::dequantize(t.ty, file.tensor_data(t), &mut out).unwrap();
    out
}

/// Weights with the adapter merged in f64, F32 in place of the originals.
struct Reference<'a> {
    base: &'a GgufFile,
    header: Gguf,
    merged: HashMap<String, Vec<u8>>,
}

impl TensorSource for Reference<'_> {
    fn header(&self) -> &Gguf {
        &self.header
    }

    fn tensor_data(&self, t: &TensorInfo) -> &[u8] {
        self.merged
            .get(&t.name)
            .map_or_else(|| self.base.tensor_data(t), |b| b)
    }
}

fn logits(model: &Model, tokens: &[u32]) -> Vec<f32> {
    let mut state = model.new_state();
    model.run(&mut state, tokens, true).logits
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn merged_adapter_matches_the_reference() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let base = GgufFile::open(path).unwrap();
    let h = base.header();
    let arch = h.architecture().unwrap().to_owned();

    let mut rng = Rng(7);
    let mut tensors = Vec::new();
    let mut data: Vec<Vec<f32>> = Vec::new();
    let mut header = h.clone();
    let mut merged: HashMap<String, Vec<u8>> = HashMap::new();
    for layer in 0..3 {
        for target in TARGETS {
            let name = format!("blk.{layer}.{target}.weight");
            let w = h.tensor(&name).unwrap();
            let (cols, rows) = (w.dims[0] as usize, w.dims[1] as usize);
            let a: Vec<f32> = (0..RANK * cols).map(|_| rng.next()).collect();
            let b: Vec<f32> = (0..rows * RANK).map(|_| rng.next()).collect();
            let scale = f64::from(SCALE * ALPHA / RANK as f32);
            let mut m: Vec<f64> = floats(&base, w).into_iter().map(f64::from).collect();
            for o in 0..rows {
                for k in 0..RANK {
                    let bk = f64::from(b[o * RANK + k]) * scale;
                    for i in 0..cols {
                        m[o * cols + i] += bk * f64::from(a[k * cols + i]);
                    }
                }
            }
            let info = header.tensors.iter_mut().find(|t| t.name == name).unwrap();
            info.ty = TensorType::F32;
            info.size = (m.len() * 4) as u64;
            merged.insert(
                name.clone(),
                m.iter().flat_map(|&v| (v as f32).to_le_bytes()).collect(),
            );
            tensors.push(TensorOut {
                name: format!("{name}.lora_a"),
                dims: vec![cols as u64, RANK as u64],
                ty: TensorType::F32,
            });
            tensors.push(TensorOut {
                name: format!("{name}.lora_b"),
                dims: vec![RANK as u64, rows as u64],
                ty: TensorType::F32,
            });
            data.push(a);
            data.push(b);
        }
    }
    let metadata = vec![
        ("general.architecture".to_owned(), Value::String(arch)),
        ("general.type".to_owned(), Value::String("adapter".into())),
        ("adapter.type".to_owned(), Value::String("lora".into())),
        ("adapter.lora.alpha".to_owned(), Value::F32(ALPHA)),
    ];
    let dir = std::env::temp_dir().join(format!("kinetic-lora-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let file = dir.join("adapter.gguf");
    let mut out = std::fs::File::create(&file).unwrap();
    kinetic_gguf::write(&mut out, &metadata, &tensors, |i| {
        Ok(data[i].iter().flat_map(|v| v.to_le_bytes()).collect())
    })
    .unwrap();
    drop(out);
    let adapter = GgufFile::open(&file).unwrap();

    let tokens: Vec<u32> = (0..24u32).map(|i| 200 + i * 37).collect();
    let plain = logits(&kinetic_models::load(&base).unwrap(), &tokens);
    let list = [Adapter {
        file: &adapter,
        scale: SCALE,
    }];
    let adapted = Adapted::new(&base, &list).unwrap();
    let got = logits(&kinetic_models::load(&adapted).unwrap(), &tokens);
    for (name, bytes) in &merged {
        let t = adapted.header().tensor(name).unwrap();
        let f = |b: &[u8]| -> Vec<f32> {
            b.chunks(4)
                .map(|c| f32::from_le_bytes(c.try_into().unwrap()))
                .collect()
        };
        let (got, want) = (f(adapted.tensor_data(t)), f(bytes));
        let top = want.iter().fold(0.0f32, |m, v| m.max(v.abs()));
        let off = got
            .iter()
            .zip(&want)
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f32::max);
        assert!(off <= 1e-6 * top, "{name}: weights off by {off}");
    }
    let reference = Reference {
        base: &base,
        header,
        merged,
    };
    let want = logits(&kinetic_models::load(&reference).unwrap(), &tokens);
    drop(adapter);
    std::fs::remove_dir_all(dir).unwrap();

    let max_diff = |x: &[f32], y: &[f32]| {
        x.iter()
            .zip(y)
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f32::max)
    };
    let spread = want.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    let (err, moved) = (max_diff(&got, &want), max_diff(&got, &plain));
    eprintln!("max |adapted - reference| = {err:e}, max |adapted - base| = {moved}, max |logit| = {spread}");
    // a quantized base quantizes activations too, so last-bit weight
    // differences can flip a rounding; an F16 base stays within ~1e-5
    assert!(err < 0.05 * spread, "adapter merge is off by {err}");
    assert!(moved > 10.0 * err, "the adapter changed nothing ({moved})");
}
