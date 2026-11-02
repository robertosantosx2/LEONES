mod detect;
mod inventory;
mod output;
mod report;
mod system;

use std::env;
use std::process::ExitCode;

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn print_help() {
    println!(
        "LEONES Lab Agent {VERSION}\n\
         Agente local autocontenido de inventario (solo lectura).\n\n\
         USO:\n\
           lab-agent doctor [--json]       Diagnóstico del sistema\n\
           lab-agent engines               Detectar motores y herramientas\n\
           lab-agent models [--json]       Inventariar modelos locales\n\
           lab-agent inventory [--json]    Inventario consolidado\n\
           lab-agent report [F]            Generar informe Markdown\n\
           lab-agent version               Mostrar versión\n\
           lab-agent help                  Mostrar esta ayuda\n\n\
         No instala, descarga, ejecuta modelos ni modifica servicios."
    );
}

fn has_json(args: &[String]) -> bool {
    args.iter().any(|arg| arg == "--json")
}

fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let command = args.next().unwrap_or_else(|| "help".to_string());
    let rest: Vec<String> = args.collect();

    match command.as_str() {
        "doctor" => {
            if has_json(&rest) {
                let info = system::collect();
                println!(
                    "{{\"schema_version\":1,\"os\":{},\"kernel\":{},\"cpu\":{},\"logical_cpus\":{},\"memory_total_kib\":{},\"memory_available_kib\":{},\"gpu\":{},\"cuda_toolkit\":{}}}",
                    output::json::escape(&info.os),
                    output::json::escape(&info.kernel),
                    output::json::escape(&info.cpu),
                    info.logical_cpus,
                    info.memory_total_kib.map(|v| v.to_string()).unwrap_or_else(|| "null".to_string()),
                    info.memory_available_kib.map(|v| v.to_string()).unwrap_or_else(|| "null".to_string()),
                    output::json::escape(&info.gpu),
                    output::json::escape(&info.cuda)
                );
                Ok(())
            } else {
                system::print_report()
            }
        }
        "engines" => detect::print_engines(),
        "models" | "inventory" => {
            let data = inventory::collect();
            if has_json(&rest) {
                println!("{}", inventory::to_json(&data));
            } else {
                inventory::print_text(&data);
            }
            Ok(())
        }
        "report" => {
            let path = rest.iter().find(|arg| !arg.starts_with("--"))
                .cloned().unwrap_or_else(|| "lab-agent-report.md".to_string());
            report::write_report(&path)
        }
        "version" | "--version" | "-V" => {
            println!("leones-lab-agent {VERSION}");
            Ok(())
        }
        "help" | "--help" | "-h" => {
            print_help();
            Ok(())
        }
        other => Err(format!("Comando desconocido: {other}. Ejecuta lab-agent help.")),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
