//! Print a GGUF's metadata (arrays abbreviated) and tensor table. Usage: gguf_dump FILE [tensors|meta]
use rusting_strata::gguf::{Gguf, Value};

fn show(v: &Value) -> String {
    match v {
        Value::Str(s) => format!("{:?}", s.chars().take(120).collect::<String>()),
        Value::Arr(a) if a.len() <= 64 => format!("[{}]", a.iter().map(show).collect::<Vec<_>>().join(", ")),
        Value::Arr(a) => format!("[{} items; first: {}]", a.len(), a.first().map(show).unwrap_or_default()),
        v => format!("{v:?}"),
    }
}

fn main() -> anyhow::Result<()> {
    let a: Vec<String> = std::env::args().collect();
    let g = Gguf::open(std::path::Path::new(&a[1]))?;
    let what = a.get(2).map(String::as_str).unwrap_or("all");
    if what != "tensors" { for (k, v) in &g.meta { println!("{k} = {}", show(v)); } }
    if what != "meta" {
        for t in g.tensors.values() { println!("{} {:?} type={} file={}", t.name, t.dims, t.ty, t.file); }
    }
    Ok(())
}
