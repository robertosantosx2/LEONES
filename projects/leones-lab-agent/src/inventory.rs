use crate::detect;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone)]
pub struct ModelRecord {
    pub name: String,
    pub source: String,
    pub path: String,
    pub format: String,
    pub state: String,
    pub bytes: u64,
}

#[derive(Debug, Clone)]
pub struct ToolRecord {
    pub name: String,
    pub path: String,
}

#[derive(Debug, Clone)]
pub struct ComponentStatus {
    pub name: String,
    pub installed: bool,
    pub active: Option<bool>,
    pub detail: String,
}

#[derive(Debug, Default)]
pub struct Inventory {
    pub models: Vec<ModelRecord>,
    pub tools: Vec<ToolRecord>,
    pub components: Vec<ComponentStatus>,
}

fn home() -> Option<PathBuf> {
    env::var_os("HOME").map(PathBuf::from)
}

fn model_format(path: &Path) -> Option<&'static str> {
    let ext = path.extension()?.to_str()?.to_ascii_lowercase();
    match ext.as_str() {
        "gguf" => Some("GGUF"),
        "safetensors" => Some("Safetensors"),
        "bin" => Some("Binary"),
        "pt" | "pth" => Some("PyTorch"),
        "onnx" => Some("ONNX"),
        "mlx" => Some("MLX"),
        _ => None,
    }
}

fn directory_size_and_weights(root: &Path, depth: usize) -> (u64, Vec<(PathBuf, String, u64)>) {
    let mut total = 0u64;
    let mut weights = Vec::new();
    if depth > 5 {
        return (total, weights);
    }
    let Ok(entries) = fs::read_dir(root) else { return (total, weights) };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let (bytes, mut nested) = directory_size_and_weights(&path, depth + 1);
            total = total.saturating_add(bytes);
            weights.append(&mut nested);
        } else if path.is_file() {
            let size = fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
            total = total.saturating_add(size);
            if let Some(format) = model_format(&path) {
                weights.push((path.clone(), format.to_string(), size));
            }
        }
    }
    (total, weights)
}

fn push_model(records: &mut Vec<ModelRecord>, name: String, source: &str, path: &Path) {
    let (_, weights) = directory_size_and_weights(path, 0);
    let weight_bytes = weights.iter().fold(0u64, |sum, (_, _, size)| sum.saturating_add(*size));
    if weights.is_empty() {
        records.push(ModelRecord {
            name,
            source: source.to_string(),
            path: path.display().to_string(),
            format: "unknown".to_string(),
            state: "CACHE_ENTRY".to_string(),
            bytes: 0,
        });
    } else {
        let mut formats = weights.iter().map(|(_, f, _)| f.as_str()).collect::<Vec<_>>();
        formats.sort_unstable();
        formats.dedup();
        records.push(ModelRecord {
            name,
            source: source.to_string(),
            path: path.display().to_string(),
            format: formats.join(","),
            state: "WEIGHTS_PRESENT".to_string(),
            bytes: weight_bytes,
        });
    }
}

fn scan_huggingface(records: &mut Vec<ModelRecord>, home: &Path) {
    let hub = home.join(".cache/huggingface/hub");
    let Ok(entries) = fs::read_dir(&hub) else { return };
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() { continue; }
        let Some(raw) = path.file_name().and_then(|s| s.to_str()) else { continue };
        let Some(repo) = raw.strip_prefix("models--") else { continue };
        let name = repo.replace("--", "/");
        let snapshots = path.join("snapshots");
        if snapshots.is_dir() {
            let Ok(snapshot_entries) = fs::read_dir(&snapshots) else {
                push_model(records, name, "Hugging Face", &path);
                continue;
            };
            let mut found = false;
            for snapshot in snapshot_entries.flatten() {
                if snapshot.path().is_dir() {
                    push_model(records, name.clone(), "Hugging Face", &snapshot.path());
                    found = true;
                }
            }
            if !found {
                push_model(records, name, "Hugging Face", &path);
            }
        } else {
            push_model(records, name, "Hugging Face", &path);
        }
    }
}

fn scan_ods(records: &mut Vec<ModelRecord>, home: &Path) -> bool {
    let root = home.join("ods");
    let model_dir = root.join("data/models");
    let mut configured = root.join("docker-compose.yml").exists()
        || root.join("compose.yaml").exists()
        || root.join("compose.yml").exists();
    if model_dir.is_dir() {
        configured = true;
        let (_, weights) = directory_size_and_weights(&model_dir, 0);
        for (path, format, bytes) in weights {
            let name = path.file_name().and_then(|s| s.to_str()).unwrap_or("model").to_string();
            records.push(ModelRecord {
                name,
                source: "ODS".to_string(),
                path: path.display().to_string(),
                format,
                state: "WEIGHTS_PRESENT".to_string(),
                bytes,
            });
        }
    }
    configured
}

fn command_status(program: &str, args: &[&str]) -> Option<bool> {
    Command::new(program).args(args).status().ok().map(|s| s.success())
}

fn component(name: &str, installed: bool, active: Option<bool>, detail: &str) -> ComponentStatus {
    ComponentStatus {
        name: name.to_string(),
        installed,
        active,
        detail: detail.to_string(),
    }
}

pub fn collect() -> Inventory {
    let mut result = Inventory::default();
    for tool in detect::TOOLS {
        if let Some(path) = detect::find_executable(tool) {
            result.tools.push(ToolRecord {
                name: (*tool).to_string(),
                path: path.display().to_string(),
            });
        }
    }
    if let Some(home) = home() {
        scan_huggingface(&mut result.models, &home);
        let ods_found = scan_ods(&mut result.models, &home);
        let magnitude_paths = [
            home.join(".local/bin/magnitude"),
            PathBuf::from("/usr/bin/magnitude"),
            PathBuf::from("/usr/local/bin/magnitude"),
        ];
        let magnitude_installed = magnitude_paths.iter().any(|p| p.is_file());
        let magnitude_active = if magnitude_installed {
            command_status("systemctl", &["is-active", "--quiet", "magnitude"])
        } else { None };
        result.components.push(component(
            "Magnitude",
            magnitude_installed,
            magnitude_active,
            if magnitude_installed { "CLI localizado; catálogo no consultado ni modelos cargados." } else { "CLI no encontrado en rutas conocidas." },
        ));
        result.components.push(component(
            "ODS",
            ods_found,
            None,
            if ods_found { "Configuración o directorio de modelos localizado; no implica servicios activos." } else { "No se encontró ~/ods/data/models ni un Compose conocido." },
        ));
    }
    result.models.sort_by(|a, b| (&a.source, &a.name, &a.path).cmp(&(&b.source, &b.name, &b.path)));
    result.tools.sort_by(|a, b| a.name.cmp(&b.name));
    result
}

pub fn print_text(inventory: &Inventory) {
    println!("LEONES LAB AGENT — INVENTARIO CONSOLIDADO");
    println!("Herramientas detectadas: {}", inventory.tools.len());
    for tool in &inventory.tools {
        println!("[FOUND] {}: {}", tool.name, tool.path);
    }
    println!("\nModelos y entradas locales: {}", inventory.models.len());
    for model in &inventory.models {
        println!(
            "[{}] {} | {} | {} | {} | {} bytes de pesos",
            model.state, model.name, model.source, model.format, model.path, model.bytes
        );
    }
    println!("\nComponentes:");
    for item in &inventory.components {
        let active = match item.active {
            Some(true) => "active",
            Some(false) => "inactive",
            None => "unknown",
        };
        println!(
            "[{}] {} | servicio={} | {}",
            if item.installed { "FOUND" } else { "MISSING" },
            item.name,
            active,
            item.detail
        );
    }
    println!("\nLos estados describen evidencia local; no se infiere disponibilidad, carga ni rendimiento.");
}

pub fn to_json(inventory: &Inventory) -> String {
    use crate::output::json::escape;
    let mut out = String::from("{\"schema_version\":1,\"tools\":[");
    for (i, tool) in inventory.tools.iter().enumerate() {
        if i > 0 { out.push(','); }
        out.push_str(&format!(
            "{{\"name\":{},\"path\":{}}}",
            escape(&tool.name), escape(&tool.path)
        ));
    }
    out.push_str("],\"models\":[");
    for (i, model) in inventory.models.iter().enumerate() {
        if i > 0 { out.push(','); }
        out.push_str(&format!(
            "{{\"name\":{},\"source\":{},\"path\":{},\"format\":{},\"state\":{},\"weight_bytes\":{}}}",
            escape(&model.name), escape(&model.source), escape(&model.path),
            escape(&model.format), escape(&model.state), model.bytes
        ));
    }
    out.push_str("],\"components\":[");
    for (i, item) in inventory.components.iter().enumerate() {
        if i > 0 { out.push(','); }
        let active = item.active.map(|v| v.to_string()).unwrap_or_else(|| "null".to_string());
        out.push_str(&format!(
            "{{\"name\":{},\"installed\":{},\"active\":{},\"detail\":{}}}",
            escape(&item.name), item.installed, active, escape(&item.detail)
        ));
    }
    out.push_str("]}");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn model_format_is_case_insensitive() {
        assert_eq!(model_format(Path::new("weights.GGUF")), Some("GGUF"));
        assert_eq!(model_format(Path::new("model.safetensors")), Some("Safetensors"));
    }

    #[test]
    fn json_output_has_schema_and_arrays() {
        let inventory = Inventory::default();
        let json = to_json(&inventory);
        assert!(json.starts_with("{\"schema_version\":1"));
        assert!(json.contains("\"tools\":[]"));
        assert!(json.contains("\"models\":[]"));
        assert!(json.contains("\"components\":[]"));
    }
}
