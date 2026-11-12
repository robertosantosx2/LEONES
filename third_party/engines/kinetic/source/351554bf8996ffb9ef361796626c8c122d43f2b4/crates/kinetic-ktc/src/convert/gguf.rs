use std::path::Path;

use kinetic_gguf::GgufFile;

use super::ConvertOptions;
use crate::error::{invalid, Error};
use crate::manifest::{Manifest, Tokenizer};
use crate::writer::{write, Contents, TensorData};

/// Converts a GGUF model to `.ktc`. Tensors are copied byte for byte in their
/// original types; hyperparameters, tokenizer, chat template and the rest of
/// the metadata carry over, so [`crate::KtcFile::gguf`] gives back the
/// source's metadata.
pub fn convert_gguf(
    path: impl AsRef<Path>,
    out: impl AsRef<Path>,
    options: &ConvertOptions,
) -> Result<Manifest, Error> {
    let path = path.as_ref();
    let src = GgufFile::open(path)?;
    let g = src.header();
    let architecture = g
        .architecture()
        .ok_or_else(|| invalid("GGUF file does not name its architecture"))?
        .to_owned();
    let string = |key: &str| match g.get(key) {
        None => Ok(None),
        Some(v) => v
            .as_str()
            .map(|s| Some(s.to_owned()))
            .ok_or_else(|| invalid(format!("{key} is not a string"))),
    };
    let name = match string("general.name")? {
        Some(name) => name,
        None => path
            .file_stem()
            .map_or_else(String::new, |s| s.to_string_lossy().into_owned()),
    };
    let chat_template = string("tokenizer.chat_template")?;

    let arch_prefix = format!("{architecture}.");
    let mut hyperparameters = Vec::new();
    let mut tokenizer = Tokenizer::default();
    let mut metadata = Vec::new();
    for (key, value) in &g.metadata {
        let entry = |k: &str| (k.to_owned(), value.clone());
        match key.as_str() {
            // Stored as manifest fields, or meaningless outside GGUF's layout.
            "general.architecture"
            | "general.name"
            | "general.alignment"
            | "tokenizer.chat_template" => {}
            _ => {
                if let Some(k) = key.strip_prefix(&arch_prefix) {
                    hyperparameters.push(entry(k));
                } else if let Some(k) = key.strip_prefix("tokenizer.") {
                    tokenizer.metadata.push(entry(k));
                } else {
                    metadata.push(entry(key));
                }
            }
        }
    }

    let tensors = g
        .tensors
        .iter()
        .map(|t| TensorData {
            name: t.name.clone(),
            ty: t.ty,
            dims: t.dims.clone(),
            data: src.tensor_data(t),
        })
        .collect();
    let contents = Contents {
        name,
        architecture,
        hyperparameters,
        tokenizer,
        chat_template,
        metadata,
        execution_profile: None,
        tensors,
        sections: Vec::new(),
    };
    write(out, &contents, options.secret_key.as_ref())
}
