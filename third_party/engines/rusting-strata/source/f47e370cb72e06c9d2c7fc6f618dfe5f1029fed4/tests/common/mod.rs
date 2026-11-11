// Shared by integration tests via `mod common;`.
#![allow(dead_code)]

pub const DEFAULT_MODEL: &str = "/mnt/ollama/hub/models--unsloth--Qwen3.6-35B-A3B-MTP-GGUF/snapshots/5bc3e238d916f48a861bac2f8a1990a0e9b7e98d/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf";

pub fn model_path() -> Option<std::path::PathBuf> {
    let p = std::path::PathBuf::from(std::env::var("STRATA_MODEL").unwrap_or_else(|_| DEFAULT_MODEL.into()));
    if p.exists() { Some(p) } else { eprintln!("SKIP: model file missing"); None }
}

/// True for the default model, wherever it is stored (`STRATA_MODEL` pointing at a copy with the same file name
/// counts); tests of its exact shapes and type mix skip those checks on any other.
pub fn is_default_model(p: &std::path::Path) -> bool {
    let d = p.file_name().is_some() && p.file_name() == std::path::Path::new(DEFAULT_MODEL).file_name();
    if !d { eprintln!("SKIP: default-model checks on {}", p.display()); }
    d
}

/// Held by tests that load the whole model on the GPU: two at once do not fit in 12 GB.
pub fn gpu_lock() -> std::sync::MutexGuard<'static, ()> {
    static LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());
    LOCK.lock().unwrap_or_else(|e| e.into_inner())
}

use rusting_strata::backend::{Backend, Buf, Plain};

/// The backend names in `STRATA_TEST_BACKENDS` (comma-separated, case-insensitive), or `None` when it is absent or
/// empty. A selection lets GPU tests run on one backend while another cannot open (the CUDA sm_70 NVRTC panic).
fn selected_backends() -> Option<Vec<String>> {
    let v = std::env::var("STRATA_TEST_BACKENDS").ok()?;
    let names: Vec<String> = v.split(',').map(str::trim).filter(|s| !s.is_empty()).map(str::to_ascii_lowercase).collect();
    (!names.is_empty()).then_some(names)
}

/// Every GPU backend that opens on this machine, by name. One that fails to open for lack of a device is skipped
/// with a note; any other error (such as a kernel compile error) fails the test. `STRATA_TEST_BACKENDS` restricts
/// the set: a backend it does not name is reported as `SKIP: <name> (filtered)` and never opened, so it cannot panic.
pub fn backends() -> Vec<(&'static str, Box<dyn Backend>)> {
    let sel = selected_backends();
    let wanted = |name: &str| sel.as_ref().is_none_or(|s| s.iter().any(|n| n == name));
    let mut v: Vec<(&'static str, Box<dyn Backend>)> = vec![];
    if wanted("cuda") {
        match rusting_strata::cuda::Gpu::new(0) {
            Ok(g) => v.push(("cuda", Box::new(g))),
            Err(e) if format!("{e}") == "CUDA init" => eprintln!("SKIP: cuda: {e:#}"),
            Err(e) => panic!("{e:#}"),
        }
    } else {
        eprintln!("SKIP: cuda (filtered)");
    }
    if wanted("vulkan") {
        match rusting_strata::vulkan::Vk::new(0) {
            Ok(g) => v.push(("vulkan", Box::new(g))),
            Err(e) if format!("{e}") == "Vulkan init" => eprintln!("SKIP: vulkan: {e:#}"),
            Err(e) => panic!("{e:#}"),
        }
    } else {
        eprintln!("SKIP: vulkan (filtered)");
    }
    if let Some(sel) = sel {
        for name in sel.iter().filter(|n| !matches!(n.as_str(), "cuda" | "vulkan")) {
            eprintln!("SKIP: {name} (filtered)");
        }
    }
    v
}

/// `backends()` less the named ones, for tests of ops a backend does not have yet.
pub fn backends_except(skip: &[&str]) -> Vec<(&'static str, Box<dyn Backend>)> {
    backends().into_iter().filter(|b| !skip.contains(&b.0)).collect()
}

/// A device copy of `v`.
pub fn up<T: Plain>(g: &dyn Backend, v: &[T]) -> Buf {
    let b = g.zeros::<T>(v.len()).unwrap();
    g.put(v, &b, 0).unwrap();
    b
}

/// All of `b` as values of `T`.
pub fn down<T: Plain>(g: &dyn Backend, b: &Buf) -> Vec<T> { g.get(b, 0, b.len() / size_of::<T>()).unwrap() }
