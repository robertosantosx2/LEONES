#![allow(dead_code)]

use std::path::{Path, PathBuf};

use kinetic_gguf::{TensorType, Value};
use kinetic_ktc::{Contents, TensorData, Tokenizer};

/// A fresh Ed25519 secret key for one test run.
pub fn throwaway_key() -> [u8; 32] {
    let mut key = [0; 32];
    getrandom::fill(&mut key).unwrap();
    key
}

/// A directory of its own under the system temp dir, removed on drop.
pub struct TempDir(PathBuf);

impl TempDir {
    pub fn new(test: &str) -> TempDir {
        let dir = std::env::temp_dir().join(format!("kinetic-ktc-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        TempDir(dir)
    }

    pub fn join(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }

    pub fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

/// Bytes `0, 1, 2, ...` wrapping at 251, so no two tensors look alike.
pub fn pattern(len: usize, seed: u8) -> Vec<u8> {
    (0..len).map(|i| (i % 251) as u8 ^ seed).collect::<Vec<_>>()
}

/// A small model with a quantized matrix, a norm vector and an extra file.
pub fn sample<'a>(q4: &'a [u8], norm: &'a [u8], extra: &'a [u8]) -> Contents<'a> {
    Contents {
        name: "Tiny".into(),
        architecture: "tiny".into(),
        hyperparameters: vec![
            ("block_count".into(), Value::U32(2)),
            ("rope.freq_base".into(), Value::F32(1.0e6)),
            (
                "layer_types".into(),
                Value::Array(vec![Value::Bool(true), Value::Bool(false)]),
            ),
        ],
        tokenizer: Tokenizer {
            metadata: vec![
                ("ggml.model".into(), Value::String("gpt2".into())),
                (
                    "ggml.tokens".into(),
                    Value::Array(vec![Value::String("a".into()), Value::String("b".into())]),
                ),
                ("ggml.eos_token_id".into(), Value::I32(-1)),
            ],
            section: None,
        },
        chat_template: Some("{{ messages }}".into()),
        metadata: vec![("general.license".into(), Value::String("apache-2.0".into()))],
        execution_profile: None,
        tensors: vec![
            TensorData {
                name: "blk.0.ffn_up.weight".into(),
                ty: TensorType::Q4K,
                dims: vec![256, 3],
                data: q4,
            },
            TensorData {
                name: "output_norm.weight".into(),
                ty: TensorType::F32,
                dims: vec![5],
                data: norm,
            },
        ],
        sections: vec![("notes.txt".into(), extra)],
    }
}

/// Builds GGUF v3 bytes from metadata and tensors laid out at 32-byte
/// alignment.
pub fn gguf(metadata: &[(&str, Value)], tensors: &[(&str, TensorType, &[u64], &[u8])]) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend(b"GGUF");
    out.extend(3u32.to_le_bytes());
    out.extend((tensors.len() as u64).to_le_bytes());
    out.extend((metadata.len() as u64).to_le_bytes());
    for (key, value) in metadata {
        put_str(&mut out, key);
        put_value(&mut out, value, true);
    }
    let mut offset = 0u64;
    let mut offsets = Vec::new();
    for (name, ty, dims, data) in tensors {
        put_str(&mut out, name);
        out.extend((dims.len() as u32).to_le_bytes());
        for d in *dims {
            out.extend(d.to_le_bytes());
        }
        out.extend((*ty as u32).to_le_bytes());
        out.extend(offset.to_le_bytes());
        offsets.push(offset);
        offset = (offset + data.len() as u64).next_multiple_of(32);
    }
    let start = out.len().next_multiple_of(32);
    for ((_, _, _, data), at) in tensors.iter().zip(offsets) {
        out.resize(start + at as usize, 0);
        out.extend(*data);
    }
    out
}

fn put_str(out: &mut Vec<u8>, s: &str) {
    out.extend((s.len() as u64).to_le_bytes());
    out.extend(s.as_bytes());
}

fn put_value(out: &mut Vec<u8>, value: &Value, with_kind: bool) {
    let kind: u32 = match value {
        Value::U8(_) => 0,
        Value::I8(_) => 1,
        Value::U16(_) => 2,
        Value::I16(_) => 3,
        Value::U32(_) => 4,
        Value::I32(_) => 5,
        Value::F32(_) => 6,
        Value::Bool(_) => 7,
        Value::String(_) => 8,
        Value::Array(_) => 9,
        Value::U64(_) => 10,
        Value::I64(_) => 11,
        Value::F64(_) => 12,
    };
    if with_kind {
        out.extend(kind.to_le_bytes());
    }
    match value {
        Value::U8(v) => out.push(*v),
        Value::I8(v) => out.push(*v as u8),
        Value::U16(v) => out.extend(v.to_le_bytes()),
        Value::I16(v) => out.extend(v.to_le_bytes()),
        Value::U32(v) => out.extend(v.to_le_bytes()),
        Value::I32(v) => out.extend(v.to_le_bytes()),
        Value::F32(v) => out.extend(v.to_le_bytes()),
        Value::Bool(v) => out.push(u8::from(*v)),
        Value::String(s) => put_str(out, s),
        Value::Array(items) => {
            let item_kind = items.first().map_or(0, |first| {
                let mut probe = Vec::new();
                put_value(&mut probe, first, true);
                u32::from_le_bytes(probe[..4].try_into().unwrap())
            });
            out.extend(item_kind.to_le_bytes());
            out.extend((items.len() as u64).to_le_bytes());
            for item in items {
                put_value(out, item, false);
            }
        }
        Value::U64(v) => out.extend(v.to_le_bytes()),
        Value::I64(v) => out.extend(v.to_le_bytes()),
        Value::F64(v) => out.extend(v.to_le_bytes()),
    }
}
