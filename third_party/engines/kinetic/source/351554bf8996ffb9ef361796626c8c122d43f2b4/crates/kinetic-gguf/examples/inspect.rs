//! Prints the metadata and tensor summary of a GGUF file.
//!
//! cargo run --release -p kinetic-gguf --example inspect -- model.gguf

use std::collections::BTreeMap;

use kinetic_gguf::{GgufFile, Value};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::args()
        .nth(1)
        .ok_or("usage: inspect <model.gguf>")?;
    let file = GgufFile::open(&path)?;
    let g = file.header();

    println!(
        "{path}: GGUF v{}, {} tensors, {:.2} GiB",
        g.version,
        g.tensors.len(),
        file.len() as f64 / (1u64 << 30) as f64
    );
    for (key, value) in &g.metadata {
        println!("  {key} = {}", short(value));
    }

    let mut by_type: BTreeMap<&str, (usize, u64)> = BTreeMap::new();
    for t in &g.tensors {
        let e = by_type.entry(t.ty.name()).or_default();
        e.0 += 1;
        e.1 += t.size;
    }
    for (ty, (count, bytes)) in by_type {
        println!(
            "  {ty:>7}: {count:4} tensors, {:8.1} MiB",
            bytes as f64 / (1u64 << 20) as f64
        );
    }
    if std::env::args().nth(2).as_deref() == Some("--tensors") {
        for t in &g.tensors {
            println!("  {} {:?} {}", t.name, t.dims, t.ty);
        }
    }
    Ok(())
}

fn short(v: &Value) -> String {
    match v {
        Value::Array(items) => format!("[{} items]", items.len()),
        Value::String(s) if s.len() > 80 => format!(
            "{:?}... ({} bytes)",
            &s[..s.floor_char_boundary(80)],
            s.len()
        ),
        other => format!("{other:?}"),
    }
}
