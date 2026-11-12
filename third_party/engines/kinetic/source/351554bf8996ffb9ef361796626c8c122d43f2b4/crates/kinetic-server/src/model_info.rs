//! What the server tells clients about the model it runs.

use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::SystemTime;

use kinetic_gguf::{Gguf, Value as Meta};
use serde_json::{Map, Value};

/// Arrays longer than this, like the vocabulary, are left out of
/// [`ModelInfo::metadata`].
const MAX_ARRAY: usize = 64;

/// Facts about a model read from its header when it was loaded.
#[derive(Clone, Debug)]
pub struct ModelInfo {
    pub architecture: String,
    pub parameters: u64,
    /// The quantization as llama.cpp names it, such as `Q4_K_M`.
    pub quantization: String,
    /// Bytes of weights.
    pub size: u64,
    /// Stable for one file's header, as a hex string.
    pub digest: String,
    pub chat_template: Option<String>,
    /// The header's metadata without long arrays, as JSON.
    pub metadata: Map<String, Value>,
    pub loaded: SystemTime,
}

impl ModelInfo {
    pub fn new(gguf: &Gguf) -> Self {
        let mut metadata = Map::new();
        for (key, value) in &gguf.metadata {
            if key.starts_with("tokenizer.chat_template") {
                continue;
            }
            if let Some(v) = json(value) {
                metadata.insert(key.clone(), v);
            }
        }
        let mut h = DefaultHasher::new();
        for t in &gguf.tensors {
            (&t.name, &t.dims, t.offset).hash(&mut h);
        }
        metadata.len().hash(&mut h);
        ModelInfo {
            architecture: gguf.architecture().unwrap_or("unknown").to_owned(),
            parameters: gguf.tensors.iter().map(|t| t.elements()).sum(),
            quantization: gguf.quantization(),
            size: gguf.tensors.iter().map(|t| t.size).sum(),
            digest: format!("{:016x}", h.finish()),
            chat_template: gguf
                .get("tokenizer.chat_template")
                .and_then(Meta::as_str)
                .map(str::to_owned),
            metadata,
            loaded: SystemTime::now(),
        }
    }

    /// Parameters as Ollama prints them, such as `3.2B` or `135M`.
    pub fn parameter_size(&self) -> String {
        let p = self.parameters as f64;
        if p >= 1e9 {
            format!("{:.1}B", p / 1e9)
        } else {
            format!("{:.0}M", p / 1e6)
        }
    }
}

fn json(value: &Meta) -> Option<Value> {
    Some(match value {
        Meta::U8(v) => (*v).into(),
        Meta::I8(v) => (*v).into(),
        Meta::U16(v) => (*v).into(),
        Meta::I16(v) => (*v).into(),
        Meta::U32(v) => (*v).into(),
        Meta::I32(v) => (*v).into(),
        Meta::U64(v) => (*v).into(),
        Meta::I64(v) => (*v).into(),
        Meta::F32(v) => (*v).into(),
        Meta::F64(v) => (*v).into(),
        Meta::Bool(v) => (*v).into(),
        Meta::String(s) => s.clone().into(),
        Meta::Array(items) if items.len() <= MAX_ARRAY => {
            Value::Array(items.iter().filter_map(json).collect())
        }
        Meta::Array(_) => return None,
    })
}
