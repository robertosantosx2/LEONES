use crate::{detect, system};
use std::fs;
use std::path::Path;

pub fn write_report(path: &str) -> Result<(), String> {
    let info = system::collect();
    let models = detect::local_model_dirs();
    let destination = Path::new(path);
    let mut body = String::new();

    body.push_str("# Informe de diagnóstico — LEONES Lab Agent\n\n");
    body.push_str("> Inventario local de solo lectura. Los datos detectados no constituyen benchmarks ni mediciones de rendimiento.\n\n");
    body.push_str("## Sistema\n\n");
    body.push_str(&format!("- Sistema operativo: {}\n", info.os));
    body.push_str(&format!("- Kernel: {}\n", info.kernel));
    body.push_str(&format!("- CPU: {}\n", info.cpu));
    body.push_str(&format!("- Hilos lógicos: {}\n", info.logical_cpus));
    body.push_str(&format!("- RAM total (KiB): {}\n", info.memory_total_kib.map(|v| v.to_string()).unwrap_or_else(|| "no disponible".into())));
    body.push_str(&format!("- RAM disponible (KiB): {}\n", info.memory_available_kib.map(|v| v.to_string()).unwrap_or_else(|| "no disponible".into())));
    body.push_str(&format!("- GPU: {}\n", info.gpu));
    body.push_str(&format!("- CUDA: {}\n\n", info.cuda));
    body.push_str("## Modelos Hugging Face en caché\n\n");

    if models.is_empty() {
        body.push_str("- No se encontraron repositorios en la caché estándar.\n");
    } else {
        for model in models {
            let name = model.file_name().and_then(|v| v.to_str()).unwrap_or("modelo");
            body.push_str(&format!("- {}\n", name.strip_prefix("models--").unwrap_or(name).replace("--", "/")));
        }
    }

    body.push_str("\n## Límites de esta captura\n\n");
    body.push_str("- No se han iniciado ni detenido procesos o servicios.\n");
    body.push_str("- No se han descargado modelos ni modificado archivos fuera del informe solicitado.\n");
    body.push_str("- La detección de GPU depende de nvidia-smi; CUDA Toolkit depende de nvcc.\n");
    body.push_str("- No se han ejecutado benchmarks; no hay resultados MEASURED nuevos.\n");

    fs::write(destination, body).map_err(|e| format!("No se pudo escribir {}: {e}", destination.display()))?;
    println!("Informe generado: {}", destination.display());
    Ok(())
}
