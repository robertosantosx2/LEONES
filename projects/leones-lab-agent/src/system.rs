use std::fs;
use std::process::Command;

#[derive(Debug, Clone)]
pub struct SystemInfo {
    pub os: String,
    pub kernel: String,
    pub cpu: String,
    pub logical_cpus: usize,
    pub memory_total_kib: Option<u64>,
    pub memory_available_kib: Option<u64>,
    pub gpu: String,
    pub cuda: String,
}

fn read_os() -> String {
    let data = fs::read_to_string("/etc/os-release").unwrap_or_default();
    data.lines()
        .find_map(|line| line.strip_prefix("PRETTY_NAME="))
        .map(|value| value.trim_matches('"').to_string())
        .unwrap_or_else(|| "Linux (distribución no identificada)".to_string())
}

fn command_output(program: &str, args: &[&str]) -> Option<String> {
    let output = Command::new(program).args(args).output().ok()?;
    if !output.status.success() {
        return None;
    }
    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout.is_empty() { None } else { Some(stdout) }
}

fn cpu_info() -> (String, usize) {
    let data = fs::read_to_string("/proc/cpuinfo").unwrap_or_default();
    let model = data
        .lines()
        .find_map(|line| line.strip_prefix("model name").and_then(|v| v.split_once(':').map(|(_, x)| x.trim().to_string())))
        .unwrap_or_else(|| "CPU no identificada".to_string());
    let logical = data.lines().filter(|line| line.starts_with("processor\t") || line.starts_with("processor ")).count();
    (model, logical)
}

fn memory_info() -> (Option<u64>, Option<u64>) {
    let data = fs::read_to_string("/proc/meminfo").unwrap_or_default();
    let value = |key: &str| -> Option<u64> {
        data.lines()
            .find_map(|line| line.strip_prefix(key).and_then(|v| v.split_whitespace().next()?.parse().ok()))
    };
    (value("MemTotal:"), value("MemAvailable:"))
}

pub fn collect() -> SystemInfo {
    let kernel = command_output("uname", &["-r"]).unwrap_or_else(|| "desconocido".to_string());
    let (cpu, logical_cpus) = cpu_info();
    let (memory_total_kib, memory_available_kib) = memory_info();
    let gpu = command_output(
        "nvidia-smi",
        &["--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
    )
    .unwrap_or_else(|| "NVIDIA no detectada (o nvidia-smi no disponible)".to_string());
    let cuda = command_output("nvcc", &["--version"])
        .and_then(|text| text.lines().rev().find(|line| line.contains("release")).map(str::to_string))
        .unwrap_or_else(|| "CUDA Toolkit (nvcc) no detectado".to_string());

    SystemInfo { os: read_os(), kernel, cpu, logical_cpus, memory_total_kib, memory_available_kib, gpu, cuda }
}

fn gib(kib: Option<u64>) -> String {
    kib.map(|v| format!("{:.2} GiB", v as f64 / 1_048_576.0))
        .unwrap_or_else(|| "no disponible".to_string())
}

pub fn print_report() -> Result<(), String> {
    let info = collect();
    println!("LEONES LAB AGENT — DIAGNÓSTICO");
    println!("Sistema: {}", info.os);
    println!("Kernel: {}", info.kernel);
    println!("CPU: {} ({} hilos lógicos detectados)", info.cpu, info.logical_cpus);
    println!("RAM total: {}", gib(info.memory_total_kib));
    println!("RAM disponible: {}", gib(info.memory_available_kib));
    println!("GPU: {}", info.gpu);
    println!("CUDA: {}", info.cuda);
    println!("Alcance: solo lectura; no se han modificado recursos.");
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn gib_conversion_is_reasonable() {
        assert_eq!(super::gib(Some(14 * 1_048_576)), "14.00 GiB");
    }
}
