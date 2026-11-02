use crate::{inventory, system};
use std::fs;
use std::path::Path;

pub fn write_report(path: &str) -> Result<(), String> {
    let info = system::collect();
    let data = inventory::collect();
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
    body.push_str(&format!("- CUDA Toolkit: {}\n\n", info.cuda));

    body.push_str("## Inventario de modelos\n\n");
    if data.models.is_empty() {
        body.push_str("- No se han encontrado entradas de modelos en las ubicaciones inspeccionadas.\n");
    } else {
        body.push_str("| Modelo | Origen | Formato | Evidencia | Bytes | Ruta |\n");
        body.push_str("|---|---|---|---|---:|---|\n");
        for model in &data.models {
            body.push_str(&format!(
                "| {} | {} | {} | {} | {} | {} |\n",
                model.name.replace('|', "\\|"),
                model.source.replace('|', "\\|"),
                model.format,
                model.state,
                model.bytes,
                model.path.replace(char::from(96), "'")
            ));
        }
    }

    body.push_str("\n## Componentes locales\n\n");
    if data.components.is_empty() {
        body.push_str("- No hay componentes adicionales identificados.\n");
    } else {
        for item in &data.components {
            let active = match item.active {
                Some(true) => "activo",
                Some(false) => "inactivo",
                None => "desconocido/no consultado",
            };
            body.push_str(&format!(
                "- **{}**: instalado={}, estado={}, {}.\n",
                item.name, item.installed, active, item.detail
            ));
        }
    }

    body.push_str("\n## Estados de evidencia\n\n");
    body.push_str("- CACHE_ENTRY: existe una entrada de caché; no se han confirmado pesos.\n");
    body.push_str("- WEIGHTS_PRESENT: se han localizado ficheros con extensiones de pesos conocidas.\n");
    body.push_str("- La presencia de pesos no demuestra que un motor pueda cargarlos, que estén cargados o que se hayan medido.\n");
    body.push_str("- AVAILABLE, LOAD_VERIFIED, RUNNING y MEASURED no se asignan en esta fase.\n");

    body.push_str("\n## Límites y seguridad\n\n");
    body.push_str("- Solo se inspeccionan rutas locales conocidas; no se recorre el disco completo.\n");
    body.push_str("- No se leen archivos .env, credenciales, tokens ni valores de variables de entorno.\n");
    body.push_str("- No se inicia, detiene ni modifica ningún servicio.\n");
    body.push_str("- No se descargan, cargan ni ejecutan modelos.\n");
    body.push_str("- La detección de herramientas no implica que sus servicios estén activos.\n");
    body.push_str("- La consulta de GPU depende de nvidia-smi; la detección del Toolkit depende de nvcc.\n");
    body.push_str("- No se han ejecutado benchmarks ni se han generado nuevas métricas de rendimiento.\n");

    fs::write(destination, body)
        .map_err(|e| format!("No se pudo escribir {}: {e}", destination.display()))?;
    println!("Informe generado: {}", destination.display());
    Ok(())
}
