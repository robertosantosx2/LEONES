//! `kinetic info`: what a model file holds.

use std::collections::BTreeMap;
use std::io::Write;
use std::path::Path;

use kinetic_tokenizer::Tokenizer;

use crate::model_file::ModelFile;
use crate::Result;

const GIB: f64 = (1u64 << 30) as f64;
const MIB: f64 = (1u64 << 20) as f64;

pub fn print(path: &Path) -> Result<()> {
    let file = ModelFile::open(path)?;
    let mut out = std::io::stdout().lock();
    let g = file.source().header();
    let text = |key: &str| g.get(key).and_then(|v| v.as_str());
    let number = |key: &str| g.arch_key(key).and_then(|v| v.as_u64());
    let arch = g.architecture().unwrap_or("unknown");

    writeln!(out, "{}", path.display())?;
    if let Some(name) = text("general.name") {
        writeln!(out, "  name           {name}")?;
    }
    if kinetic_models::supports(arch) {
        writeln!(out, "  architecture   {arch}")?;
    } else {
        let known: Vec<_> = kinetic_models::architectures().collect();
        writeln!(out, "  architecture   {arch} (not supported yet)")?;
        writeln!(out, "  supported      {}", known.join(", "))?;
    }
    let params: u64 = g.tensors.iter().map(|t| t.elements()).sum();
    writeln!(
        out,
        "  size           {:.2} GiB, {:.2} B parameters",
        file.len() as f64 / GIB,
        params as f64 / 1e9
    )?;
    if let Some(n) = number("context_length") {
        writeln!(out, "  context        {n} tokens")?;
    }
    if let (Some(layers), Some(width)) = (number("block_count"), number("embedding_length")) {
        writeln!(out, "  layers         {layers}, width {width}")?;
    }
    if number("nextn_predict_layers").is_some_and(|n| n > 0) {
        writeln!(
            out,
            "  prediction     yes (drafts for speculative decoding)"
        )?;
    }

    let mut by_type: BTreeMap<&str, (usize, u64)> = BTreeMap::new();
    for t in &g.tensors {
        let e = by_type.entry(t.ty.name()).or_default();
        e.0 += 1;
        e.1 += t.size;
    }
    let mut types: Vec<_> = by_type.into_iter().collect();
    types.sort_by_key(|&(_, (_, bytes))| std::cmp::Reverse(bytes));
    for (i, (ty, (count, bytes))) in types.iter().enumerate() {
        let label = if i == 0 { "weights" } else { "" };
        writeln!(
            out,
            "  {label:<14} {ty:<6} {count:4} tensors {:9.1} MiB",
            *bytes as f64 / MIB
        )?;
    }

    match Tokenizer::from_gguf(g) {
        Ok(t) => {
            let piece = |id: Option<u32>| {
                id.map_or("none".into(), |id| {
                    String::from_utf8_lossy(t.piece(id)).into_owned()
                })
            };
            writeln!(
                out,
                "  tokenizer      {} ({}), {} tokens, BOS {}, EOS {}",
                text("tokenizer.ggml.model").unwrap_or("?"),
                text("tokenizer.ggml.pre").unwrap_or("?"),
                t.vocab_size(),
                piece(t.bos()),
                piece(t.eos()),
            )?;
        }
        Err(e) => writeln!(out, "  tokenizer      {e}")?,
    }
    match text("tokenizer.chat_template") {
        Some(t) => writeln!(out, "  chat template  {} bytes", t.len())?,
        None => writeln!(out, "  chat template  none")?,
    }
    Ok(())
}
