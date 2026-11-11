//! The GPUs the CUDA driver and the Vulkan loader report.

/// One GPU as one API sees it.
pub struct Gpu {
    pub api: &'static str,
    pub name: String,
    pub driver: String,
    pub memory_total: u64,
    /// Free memory, where the API reports it without allocating.
    pub memory_free: Option<u64>,
    /// Nominal memory bandwidth in bytes per second.
    pub bandwidth: Option<f64>,
    /// Why Kinetic cannot use it, if it cannot.
    pub problem: Option<String>,
}

/// Every GPU found, and for each API that found none, why.
pub fn gpus() -> (Vec<Gpu>, Vec<String>) {
    let mut found = Vec::new();
    let mut notes = Vec::new();
    for (api, probe) in [
        ("CUDA", cuda as fn() -> Result<Vec<Gpu>, String>),
        ("Vulkan", vulkan),
    ] {
        match probe() {
            Ok(g) if g.is_empty() => notes.push(format!("{api}: no devices")),
            Ok(g) => found.extend(g),
            Err(e) => notes.push(format!("{api}: {e}")),
        }
    }
    (found, notes)
}

/// The most free memory of any CUDA GPU, without asking Vulkan.
pub fn cuda_free() -> Option<u64> {
    cuda().ok()?.iter().filter_map(|g| g.memory_free).max()
}

#[cfg(feature = "cuda")]
fn cuda() -> Result<Vec<Gpu>, String> {
    use kinetic_cuda::{driver_version, Context, Device};
    let s = |e: kinetic_cuda::Error| e.to_string();
    let (major, minor) = driver_version().map_err(s)?;
    let mut gpus = Vec::new();
    for i in 0..Device::count().map_err(s)? {
        let device = Device::get(i).map_err(s)?;
        let info = device.info().map_err(s)?;
        let free = Context::new(device)
            .and_then(|c| c.memory_info())
            .ok()
            .map(|(free, _)| free as u64);
        let (cc_major, cc_minor) = info.compute_capability;
        gpus.push(Gpu {
            api: "CUDA",
            driver: format!("CUDA {major}.{minor}, compute {cc_major}.{cc_minor}"),
            memory_total: info.total_memory as u64,
            memory_free: free,
            bandwidth: info.peak_bandwidth(),
            problem: None,
            name: info.name,
        });
    }
    Ok(gpus)
}

#[cfg(not(feature = "cuda"))]
fn cuda() -> Result<Vec<Gpu>, String> {
    Err("this kinetic was built without CUDA".into())
}

#[cfg(feature = "vulkan")]
fn vulkan() -> Result<Vec<Gpu>, String> {
    let devices = kinetic_vulkan::Instance::new()
        .and_then(|i| i.physical_devices())
        .map_err(|e| e.to_string())?;
    Ok(devices
        .iter()
        .map(|d| {
            let info = d.info();
            let (major, minor, patch) = info.api_version;
            Gpu {
                api: "Vulkan",
                name: info.name.clone(),
                driver: format!(
                    "{} {}, Vulkan {major}.{minor}.{patch}",
                    info.driver_name, info.driver_info
                ),
                memory_total: info.device_local_bytes,
                memory_free: None,
                bandwidth: None,
                problem: info.missing(),
            }
        })
        .collect())
}

#[cfg(not(feature = "vulkan"))]
fn vulkan() -> Result<Vec<Gpu>, String> {
    Err("this kinetic was built without Vulkan".into())
}
