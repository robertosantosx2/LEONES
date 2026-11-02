mod agent;
mod benchmark;
mod benchmark_tensorfold;
mod detect;
mod hash;
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
         Agente local autocontenido de inventario, asistencia y benchmarks supervisados.\n\n\
         USO:\n\
           lab-agent doctor [--json]       Diagnóstico del sistema\n\
           lab-agent engines               Detectar motores y herramientas\n\
           lab-agent models [--json]       Inventariar modelos locales\n\
           lab-agent inventory [--json]    Inventario consolidado\n\
           lab-agent ask [OPCIONES] P      Consultar un LLM local con herramientas seguras\n\
           lab-agent benchmark [OPCIONES] Ejecutar llama-bench con aprobación explícita\n\
           lab-agent report [F]            Generar informe Markdown\n\
           lab-agent version               Mostrar versión\n\
           lab-agent help                  Mostrar esta ayuda\n\n\
         ASK:\n\
           --endpoint URL  HTTP local (por defecto http://127.0.0.1:8080/v1/chat/completions)\n\
           --model ID      Identificador del modelo (por defecto local-model)\n\n\
         BENCHMARK:\n\
           --model RUTA.gguf --approve  Ejecuta llama-bench con autorización\n\
           Sin --approve solo muestra un dry-run.\n\n\
         No ejecuta comandos arbitrarios, no instala ni descarga modelos."
    );
}

fn has_json(args: &[String]) -> bool {
    args.iter().any(|arg| arg == "--json")
}

fn run_ask(args: &[String]) -> Result<(), String> {
    let mut endpoint = "http://127.0.0.1:8080/v1/chat/completions".to_string();
    let mut model = "local-model".to_string();
    let mut prompt_parts = Vec::new();
    let mut index = 0usize;
    while index < args.len() {
        match args[index].as_str() {
            "--endpoint" => {
                index += 1;
                endpoint = args.get(index).ok_or_else(|| "--endpoint necesita una URL.".to_string())?.clone();
            }
            "--model" => {
                index += 1;
                model = args.get(index).ok_or_else(|| "--model necesita un identificador.".to_string())?.clone();
            }
            "--" => {
                prompt_parts.extend_from_slice(&args[index + 1..]);
                break;
            }
            _ => {
                prompt_parts.extend_from_slice(&args[index..]);
                break;
            }
        }
        index += 1;
    }
    if prompt_parts.is_empty() {
        return Err("Uso: lab-agent ask [--endpoint URL] [--model ID] PREGUNTA".to_string());
    }
    let prompt = prompt_parts.join(" ");
    let answer = agent::ask(&endpoint, &model, &prompt)?;
    println!("{answer}");
    Ok(())
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
        "ask" => run_ask(&rest),
        "benchmark" => benchmark::run(&rest),
        "benchmark-tensorfold" | "tensorfold-benchmark" => benchmark_tensorfold::run(&rest),
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
