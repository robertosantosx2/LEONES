mod detect;
mod report;
mod system;

use std::env;
use std::process::ExitCode;

const VERSION: &str = env!("CARGO_PKG_VERSION");

fn print_help() {
    println!(
        "LEONES Lab Agent {VERSION}\n\
         Agente local de diagnóstico (fase 1; solo lectura).\n\n\
         USO:\n\
           lab-agent doctor       Inventario del sistema y GPU\n\
           lab-agent engines      Detectar motores y herramientas\n\
           lab-agent models       Inventariar modelos Hugging Face locales\n\
           lab-agent report [F]   Generar informe Markdown\n\
           lab-agent version      Mostrar versión\n\
           lab-agent help         Mostrar esta ayuda\n\n\
         Esta fase no instala, descarga, ejecuta modelos ni modifica servicios."
    );
}

fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let command = args.next().unwrap_or_else(|| "help".to_string());

    match command.as_str() {
        "doctor" => system::print_report(),
        "engines" => detect::print_engines(),
        "models" => detect::print_models(),
        "report" => {
            let path = args.next().unwrap_or_else(|| "lab-agent-report.md".to_string());
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
