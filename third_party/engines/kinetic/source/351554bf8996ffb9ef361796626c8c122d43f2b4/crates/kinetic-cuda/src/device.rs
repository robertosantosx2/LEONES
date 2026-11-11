use std::ffi::{c_char, c_int, CStr};

use crate::driver::{self, Api, CuDevice};
use crate::error::Result;

// CUdevice_attribute values from cuda.h.
const CLOCK_RATE: c_int = 13;
const MULTIPROCESSOR_COUNT: c_int = 16;
const MEMORY_CLOCK_RATE: c_int = 36;
const GLOBAL_MEMORY_BUS_WIDTH: c_int = 37;
const L2_CACHE_SIZE: c_int = 38;
const COMPUTE_CAPABILITY_MAJOR: c_int = 75;
const COMPUTE_CAPABILITY_MINOR: c_int = 76;

/// A CUDA device, by its driver ordinal.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Device {
    pub(crate) raw: CuDevice,
}

/// Properties of a device. The optional ones are attributes some drivers no
/// longer report.
#[derive(Clone, Debug)]
pub struct DeviceInfo {
    pub name: String,
    pub compute_capability: (u32, u32),
    pub multiprocessors: u32,
    pub total_memory: usize,
    pub clock_khz: Option<u32>,
    pub memory_clock_khz: Option<u32>,
    pub memory_bus_bits: Option<u32>,
    pub l2_cache_bytes: Option<u32>,
}

impl DeviceInfo {
    /// Nominal DRAM bandwidth in bytes per second: two transfers per reported
    /// memory clock across the whole bus.
    pub fn peak_bandwidth(&self) -> Option<f64> {
        let clock = self.memory_clock_khz? as f64 * 1e3;
        Some(2.0 * clock * self.memory_bus_bits? as f64 / 8.0)
    }
}

impl Device {
    /// Number of CUDA devices.
    pub fn count() -> Result<usize> {
        let api = driver::api()?;
        let mut n = 0;
        // SAFETY: `n` is a valid out-pointer.
        api.check("cuDeviceGetCount", unsafe {
            (api.device_get_count)(&mut n)
        })?;
        Ok(n as usize)
    }

    /// The device with driver ordinal `ordinal`.
    pub fn get(ordinal: usize) -> Result<Device> {
        let api = driver::api()?;
        let mut raw = 0;
        // SAFETY: `raw` is a valid out-pointer; the driver validates the ordinal.
        api.check("cuDeviceGet", unsafe {
            (api.device_get)(&mut raw, ordinal as c_int)
        })?;
        Ok(Device { raw })
    }

    pub fn info(&self) -> Result<DeviceInfo> {
        let api = driver::api()?;
        let mut name = [0 as c_char; 256];
        // SAFETY: the buffer is writable for the length passed.
        api.check("cuDeviceGetName", unsafe {
            (api.device_get_name)(name.as_mut_ptr(), name.len() as c_int, self.raw)
        })?;
        // SAFETY: the driver wrote a NUL-terminated name into the buffer.
        let name = unsafe { CStr::from_ptr(name.as_ptr()) }
            .to_string_lossy()
            .into_owned();
        let mut total_memory = 0;
        // SAFETY: `total_memory` is a valid out-pointer.
        api.check("cuDeviceTotalMem", unsafe {
            (api.device_total_mem)(&mut total_memory, self.raw)
        })?;
        let optional = |attr| self.attribute(api, attr).ok().filter(|&v| v > 0);
        Ok(DeviceInfo {
            name,
            compute_capability: (
                self.attribute(api, COMPUTE_CAPABILITY_MAJOR)?,
                self.attribute(api, COMPUTE_CAPABILITY_MINOR)?,
            ),
            multiprocessors: self.attribute(api, MULTIPROCESSOR_COUNT)?,
            total_memory,
            clock_khz: optional(CLOCK_RATE),
            memory_clock_khz: optional(MEMORY_CLOCK_RATE),
            memory_bus_bits: optional(GLOBAL_MEMORY_BUS_WIDTH),
            l2_cache_bytes: optional(L2_CACHE_SIZE),
        })
    }

    fn attribute(&self, api: &Api, attr: c_int) -> Result<u32> {
        let mut value = 0;
        // SAFETY: `value` is a valid out-pointer; the driver validates `attr`.
        api.check("cuDeviceGetAttribute", unsafe {
            (api.device_get_attribute)(&mut value, attr, self.raw)
        })?;
        Ok(value as u32)
    }
}

/// The installed driver's CUDA version as (major, minor).
pub fn driver_version() -> Result<(u32, u32)> {
    let api = driver::api()?;
    let mut version = 0;
    // SAFETY: `version` is a valid out-pointer.
    api.check("cuDriverGetVersion", unsafe {
        (api.driver_get_version)(&mut version)
    })?;
    Ok((version as u32 / 1000, version as u32 % 1000 / 10))
}
