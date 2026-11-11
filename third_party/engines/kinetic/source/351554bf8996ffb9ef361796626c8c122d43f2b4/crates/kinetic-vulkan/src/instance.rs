use std::rc::Rc;

use ash::vk;

use crate::error::{Check, Error, Result};
use crate::physical::PhysicalDevice;

/// The Vulkan version this crate asks for; its kernels need 1.3 devices.
pub(crate) const API_VERSION: u32 = vk::API_VERSION_1_3;

/// The Vulkan loader, opened at runtime, and one instance of it.
pub struct Instance {
    /// Keeps the loader library open while the instance's functions are used.
    _entry: ash::Entry,
    pub(crate) raw: ash::Instance,
}

impl Instance {
    /// Opens the system's Vulkan loader (`vulkan-1.dll`, `libvulkan.so.1`)
    /// and creates an instance. Fails with [`Error::LoaderNotFound`] when no
    /// Vulkan driver is installed.
    pub fn new() -> Result<Rc<Instance>> {
        // SAFETY: loading the loader runs its initialisation, which has no
        // preconditions; the library stays loaded while `entry` lives.
        let entry =
            unsafe { ash::Entry::load() }.map_err(|e| Error::LoaderNotFound(e.to_string()))?;
        let app = vk::ApplicationInfo::default()
            .application_name(c"kinetic")
            .engine_name(c"kinetic")
            .api_version(API_VERSION);
        let info = vk::InstanceCreateInfo::default().application_info(&app);
        // SAFETY: `info` and what it points to are valid for the call.
        let raw = unsafe { entry.create_instance(&info, None) }.check("vkCreateInstance")?;
        Ok(Rc::new(Instance { _entry: entry, raw }))
    }

    /// Every physical device, discrete GPUs first, then integrated ones, then
    /// the rest, each group in driver order.
    pub fn physical_devices(self: &Rc<Self>) -> Result<Vec<PhysicalDevice>> {
        // SAFETY: the instance is valid for the life of `self`.
        let raw =
            unsafe { self.raw.enumerate_physical_devices() }.check("vkEnumeratePhysicalDevices")?;
        let mut devices = raw
            .into_iter()
            .map(|pd| PhysicalDevice::query(self, pd))
            .collect::<Result<Vec<_>>>()?;
        devices.sort_by_key(|d| d.info().kind.preference());
        Ok(devices)
    }
}

impl Drop for Instance {
    fn drop(&mut self) {
        // SAFETY: every object made from the instance holds an `Rc` to it and
        // is gone by now.
        unsafe { self.raw.destroy_instance(None) };
    }
}
