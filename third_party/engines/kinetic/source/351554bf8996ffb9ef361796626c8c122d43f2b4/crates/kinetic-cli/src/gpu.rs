//! Which GPU a model runs on: CUDA first, then Vulkan, else the CPU.

use kinetic_models::LoadError;

use crate::{Device, Result};

/// The GPU kinds in the order `auto` tries them, with their names.
const ORDER: [(Device, &str); 2] = [(Device::Cuda, "CUDA"), (Device::Vulkan, "Vulkan")];

/// The first backend that `start` makes for a GPU kind `device` allows,
/// and its kind; `None` when the model should run on the CPU. `start`
/// returns `None` for kinds this build lacks. A GPU asked for by name must
/// work; under `auto`, a GPU that does not is skipped with one line saying
/// why.
pub fn pick<T>(
    device: Device,
    mut start: impl FnMut(Device) -> Option<std::result::Result<T, LoadError>>,
) -> Result<Option<(T, Device)>> {
    if device == Device::Cpu {
        return Ok(None);
    }
    let mut skipped = Vec::new();
    for (kind, name) in ORDER {
        if device != Device::Auto && device != kind {
            continue;
        }
        match start(kind) {
            Some(Ok(backend)) => {
                if !skipped.is_empty() {
                    eprintln!("kinetic: running through {name}; {}", skipped.join("; "));
                }
                return Ok(Some((backend, kind)));
            }
            Some(Err(e)) if device == kind => return Err(e.into()),
            None if device == kind => {
                return Err(format!("this kinetic was built without {name}").into())
            }
            Some(Err(e)) => skipped.push(format!("{name} is not usable: {e}")),
            None => {}
        }
    }
    if !skipped.is_empty() {
        eprintln!("kinetic: running on the CPU; {}", skipped.join("; "));
    }
    Ok(None)
}
