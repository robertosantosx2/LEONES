use std::fs::{self, File};
use std::path::Path;

use kinetic_gguf::{TensorType, Value};
use memmap2::Mmap;
use serde_json::{Map, Value as Json};

use super::ConvertOptions;
use crate::error::{invalid, Error};
use crate::manifest::{Manifest, Tokenizer};
use crate::metadata::{self, Metadata};
use crate::writer::{write, Contents, TensorData};

const CONFIG: &str = "config.json";
const TOKENIZER: &str = "tokenizer.json";
const TOKENIZER_CONFIG: &str = "tokenizer_config.json";
const CHAT_TEMPLATE: &str = "chat_template.jinja";

/// Converts a Hugging Face model directory (`config.json`, `tokenizer.json`
/// and `*.safetensors` shards) to `.ktc`. F32, F16 and BF16 tensors keep
/// their type and bytes; names and shapes stay as the checkpoint has them.
pub fn convert_safetensors(
    dir: impl AsRef<Path>,
    out: impl AsRef<Path>,
    options: &ConvertOptions,
) -> Result<Manifest, Error> {
    let dir = dir.as_ref();
    let config = fs::read(dir.join(CONFIG))?;
    let tokenizer = fs::read(dir.join(TOKENIZER))?;
    let tokenizer_config = read_optional(&dir.join(TOKENIZER_CONFIG))?;

    let parsed: Json = json(&config, CONFIG)?;
    let architecture = parsed
        .get("model_type")
        .and_then(Json::as_str)
        .ok_or_else(|| invalid("config.json has no model_type"))?
        .to_owned();
    let mut hyperparameters = Vec::new();
    flatten("", &parsed, &mut hyperparameters);

    let chat_template = match read_optional(&dir.join(CHAT_TEMPLATE))? {
        Some(bytes) => Some(
            String::from_utf8(bytes).map_err(|_| invalid("chat_template.jinja is not UTF-8"))?,
        ),
        None => match &tokenizer_config {
            Some(bytes) => json::<Json>(bytes, TOKENIZER_CONFIG)?
                .get("chat_template")
                .and_then(Json::as_str)
                .map(str::to_owned),
            None => None,
        },
    };

    let shards = shard_paths(dir)?;
    let maps = shards
        .iter()
        .map(|p| {
            let file = File::open(p)?;
            // SAFETY: read-only map, alive until the output is written.
            Ok(unsafe { Mmap::map(&file)? })
        })
        .collect::<Result<Vec<_>, Error>>()?;
    let mut tensors = Vec::new();
    for (map, path) in maps.iter().zip(&shards) {
        tensors.extend(read_shard(map).map_err(|e| invalid(format!("{}: {e}", path.display())))?);
    }

    let mut sections = vec![(CONFIG.to_owned(), &config[..])];
    sections.push((TOKENIZER.to_owned(), &tokenizer[..]));
    if let Some(bytes) = &tokenizer_config {
        sections.push((TOKENIZER_CONFIG.to_owned(), &bytes[..]));
    }
    let name = dir
        .file_name()
        .map_or_else(String::new, |s| s.to_string_lossy().into_owned());
    let contents = Contents {
        name,
        architecture,
        hyperparameters,
        tokenizer: Tokenizer {
            metadata: Vec::new(),
            section: Some(TOKENIZER.to_owned()),
        },
        chat_template,
        metadata: Vec::new(),
        execution_profile: None,
        tensors,
        sections,
    };
    write(out, &contents, options.secret_key.as_ref())
}

fn read_optional(path: &Path) -> Result<Option<Vec<u8>>, Error> {
    match fs::read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e.into()),
    }
}

fn json<T: serde::de::DeserializeOwned>(bytes: &[u8], what: &str) -> Result<T, Error> {
    serde_json::from_slice(bytes).map_err(|e| invalid(format!("{what}: {e}")))
}

fn shard_paths(dir: &Path) -> Result<Vec<std::path::PathBuf>, Error> {
    let mut paths = Vec::new();
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if path.extension().is_some_and(|e| e == "safetensors") {
            paths.push(path);
        }
    }
    if paths.is_empty() {
        return Err(invalid(format!(
            "no .safetensors files in {}",
            dir.display()
        )));
    }
    paths.sort();
    Ok(paths)
}

/// The tensors of one safetensors shard: a `u64` header length, a JSON
/// header, then the data its offsets point into.
fn read_shard(map: &[u8]) -> Result<Vec<TensorData<'_>>, Error> {
    let header_len = map
        .get(..8)
        .map(|b| u64::from_le_bytes(b.try_into().unwrap()))
        .ok_or_else(|| invalid("file is too short"))?;
    let data_start = header_len
        .checked_add(8)
        .filter(|&end| end <= map.len() as u64)
        .ok_or_else(|| invalid("header extends past the end of the file"))?
        as usize;
    let header: Map<String, Json> = json(&map[8..data_start], "header")?;
    let data = &map[data_start..];

    let mut tensors = Vec::with_capacity(header.len());
    for (name, info) in &header {
        if name == "__metadata__" {
            continue;
        }
        let bad = |why: &str| invalid(format!("tensor {name}: {why}"));
        let ty = match info.get("dtype").and_then(Json::as_str) {
            Some("F32") => TensorType::F32,
            Some("F16") => TensorType::F16,
            Some("BF16") => TensorType::BF16,
            other => return Err(bad(&format!("unsupported dtype {other:?}"))),
        };
        let shape = info
            .get("shape")
            .and_then(Json::as_array)
            .and_then(|s| s.iter().map(Json::as_u64).collect::<Option<Vec<_>>>())
            .ok_or_else(|| bad("shape is not a list of sizes"))?;
        let [begin, end] = info
            .get("data_offsets")
            .and_then(Json::as_array)
            .and_then(|o| o.iter().map(Json::as_u64).collect::<Option<Vec<_>>>())
            .and_then(|o| <[u64; 2]>::try_from(o).ok())
            .ok_or_else(|| bad("data_offsets is not a pair of offsets"))?;
        let size = shape
            .iter()
            .try_fold(1u64, |acc, &d| acc.checked_mul(d))
            .and_then(|n| ty.bytes_for(n))
            .ok_or_else(|| bad("size overflows"))?;
        if begin.checked_add(size) != Some(end) || end > data.len() as u64 {
            return Err(bad(
                "data does not match its shape or lies outside the file",
            ));
        }
        // Safetensors shapes are outermost first; a scalar becomes one value.
        let mut dims: Vec<u64> = shape.into_iter().rev().collect();
        if dims.is_empty() {
            dims.push(1);
        }
        tensors.push(TensorData {
            name: name.clone(),
            ty,
            dims,
            data: &data[begin as usize..end as usize],
        });
    }
    Ok(tensors)
}

/// Flattens `config.json` into typed values, joining nested keys with `.`.
/// Nulls and arrays that do not hold one scalar type are left out; the file
/// itself is kept verbatim in its own section.
fn flatten(prefix: &str, json: &Json, out: &mut Metadata) {
    if let Json::Object(map) = json {
        for (key, value) in map {
            let key = if prefix.is_empty() {
                key.clone()
            } else {
                format!("{prefix}.{key}")
            };
            flatten(&key, value, out);
        }
    } else if let Some(value) = typed(json).filter(|v| metadata::type_name(v).is_ok()) {
        out.push((prefix.to_owned(), value));
    }
}

fn typed(json: &Json) -> Option<Value> {
    Some(match json {
        Json::Bool(b) => Value::Bool(*b),
        Json::String(s) => Value::String(s.clone()),
        Json::Number(n) => match (n.as_u64(), n.as_i64()) {
            (Some(u), _) => Value::U64(u),
            (None, Some(i)) => Value::I64(i),
            _ => Value::F64(n.as_f64()?),
        },
        Json::Array(items) => Value::Array(items.iter().map(typed).collect::<Option<_>>()?),
        Json::Null | Json::Object(_) => return None,
    })
}
