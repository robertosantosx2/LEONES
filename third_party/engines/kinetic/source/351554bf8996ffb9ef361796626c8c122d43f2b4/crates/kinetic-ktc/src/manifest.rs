use std::fmt::Write;

use kinetic_gguf::TensorType;
use serde::{de, Deserialize, Deserializer, Serialize, Serializer};
use serde_json::{Map, Value as Json};

use crate::metadata::{self, Metadata};

/// The JSON description of a `.ktc` file. See `FORMAT.md`.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub name: String,
    pub architecture: String,
    /// Keyed without the `{architecture}.` prefix.
    #[serde(with = "metadata")]
    pub hyperparameters: Metadata,
    pub tokenizer: Tokenizer,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub chat_template: Option<String>,
    /// Everything else, keyed as in GGUF (`general.license`).
    #[serde(with = "metadata")]
    pub metadata: Metadata,
    pub tensors: Vec<Tensor>,
    pub sections: Vec<Section>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub execution_profile: Option<ExecutionProfile>,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tokenizer {
    /// Keyed without the `tokenizer.` prefix.
    #[serde(with = "metadata")]
    pub metadata: Metadata,
    /// A section holding a tokenizer file, such as `tokenizer.json`.
    pub section: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tensor {
    pub name: String,
    #[serde(rename = "type", with = "tensor_type")]
    pub ty: TensorType,
    /// Innermost first.
    pub dims: Vec<u64>,
    /// Relative to the start of the `tensors` section.
    pub offset: u64,
    pub size: u64,
}

impl Tensor {
    pub fn elements(&self) -> u64 {
        self.dims.iter().product()
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Section {
    pub name: String,
    /// Relative to the file's data offset.
    pub offset: u64,
    pub size: u64,
    #[serde(with = "hex")]
    pub blake3: [u8; 32],
}

/// Settings tuned for one class of device.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExecutionProfile {
    pub target: String,
    pub settings: Map<String, Json>,
}

impl Manifest {
    pub fn section(&self, name: &str) -> Option<&Section> {
        self.sections.iter().find(|s| s.name == name)
    }

    pub fn tensor(&self, name: &str) -> Option<&Tensor> {
        self.tensors.iter().find(|t| t.name == name)
    }
}

mod tensor_type {
    use super::*;

    pub fn serialize<S: Serializer>(ty: &TensorType, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(ty.name())
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<TensorType, D::Error> {
        let name = String::deserialize(d)?;
        (0..64)
            .filter_map(TensorType::from_id)
            .find(|t| t.name() == name)
            .ok_or_else(|| de::Error::custom(format!("unknown tensor type {name:?}")))
    }
}

mod hex {
    use super::*;

    pub fn serialize<S: Serializer>(bytes: &[u8; 32], s: S) -> Result<S::Ok, S::Error> {
        let mut out = String::with_capacity(64);
        for b in bytes {
            write!(out, "{b:02x}").unwrap();
        }
        s.serialize_str(&out)
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<[u8; 32], D::Error> {
        let text = String::deserialize(d)?;
        let digit = |c: u8| match c {
            b'0'..=b'9' => Some(c - b'0'),
            b'a'..=b'f' => Some(c - b'a' + 10),
            _ => None,
        };
        let mut out = [0; 32];
        let ok = text.len() == 64
            && text.as_bytes().chunks(2).zip(&mut out).all(|(pair, slot)| {
                match (digit(pair[0]), digit(pair[1])) {
                    (Some(hi), Some(lo)) => {
                        *slot = hi << 4 | lo;
                        true
                    }
                    _ => false,
                }
            });
        if ok {
            Ok(out)
        } else {
            Err(de::Error::custom("hash must be 64 lowercase hex digits"))
        }
    }
}
