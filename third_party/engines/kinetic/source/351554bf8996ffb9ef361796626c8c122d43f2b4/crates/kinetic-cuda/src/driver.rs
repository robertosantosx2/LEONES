//! Driver API entry points, resolved from the system driver at runtime so
//! the crate builds and runs on machines without CUDA.

use std::ffi::{c_char, c_int, c_uint, c_void, CStr};
use std::ptr;
use std::sync::OnceLock;

use libloading::{Library, Symbol};

use crate::error::{Error, Result};

pub(crate) type CuResult = c_int;
pub(crate) type CuDevice = c_int;
pub(crate) type CuDevicePtr = u64;
pub(crate) type CuContext = *mut c_void;
pub(crate) type CuModule = *mut c_void;
pub(crate) type CuFunction = *mut c_void;
pub(crate) type CuStream = *mut c_void;
pub(crate) type CuEvent = *mut c_void;
pub(crate) type CuGraph = *mut c_void;
pub(crate) type CuGraphExec = *mut c_void;

const SUCCESS: CuResult = 0;

#[cfg(windows)]
const LIBRARY: &str = "nvcuda.dll";
#[cfg(not(windows))]
const LIBRARY: &str = "libcuda.so.1";

macro_rules! entry_points {
    ($($field:ident = $symbol:literal ($($arg:ty),*);)*) => {
        pub(crate) struct Api {
            $(pub(crate) $field: unsafe extern "system" fn($($arg),*) -> CuResult,)*
            _library: Library,
        }

        impl Api {
            /// # Safety
            ///
            /// `library` must be the CUDA driver, whose exports have the
            /// signatures listed in `entry_points!`.
            unsafe fn resolve(library: Library) -> Result<Api> {
                Ok(Api {
                    $($field: {
                        // SAFETY: the caller guarantees the export has this type.
                        let symbol: Result<Symbol<unsafe extern "system" fn($($arg),*) -> CuResult>, _> =
                            unsafe { library.get(concat!($symbol, "\0").as_bytes()) };
                        *symbol.map_err(|_| Error::MissingSymbol($symbol))?
                    },)*
                    _library: library,
                })
            }
        }
    };
}

entry_points! {
    init = "cuInit"(c_uint);
    get_error_name = "cuGetErrorName"(CuResult, *mut *const c_char);
    driver_get_version = "cuDriverGetVersion"(*mut c_int);
    device_get_count = "cuDeviceGetCount"(*mut c_int);
    device_get = "cuDeviceGet"(*mut CuDevice, c_int);
    device_get_name = "cuDeviceGetName"(*mut c_char, c_int, CuDevice);
    device_total_mem = "cuDeviceTotalMem_v2"(*mut usize, CuDevice);
    device_get_attribute = "cuDeviceGetAttribute"(*mut c_int, c_int, CuDevice);
    primary_ctx_retain = "cuDevicePrimaryCtxRetain"(*mut CuContext, CuDevice);
    primary_ctx_release = "cuDevicePrimaryCtxRelease_v2"(CuDevice);
    ctx_set_current = "cuCtxSetCurrent"(CuContext);
    ctx_synchronize = "cuCtxSynchronize"();
    mem_get_info = "cuMemGetInfo_v2"(*mut usize, *mut usize);
    mem_alloc = "cuMemAlloc_v2"(*mut CuDevicePtr, usize);
    mem_free = "cuMemFree_v2"(CuDevicePtr);
    memcpy_htod = "cuMemcpyHtoD_v2"(CuDevicePtr, *const c_void, usize);
    memcpy_dtoh = "cuMemcpyDtoH_v2"(*mut c_void, CuDevicePtr, usize);
    memcpy_htod_async = "cuMemcpyHtoDAsync_v2"(CuDevicePtr, *const c_void, usize, CuStream);
    memcpy_dtoh_async = "cuMemcpyDtoHAsync_v2"(*mut c_void, CuDevicePtr, usize, CuStream);
    memcpy_dtod_async = "cuMemcpyDtoDAsync_v2"(CuDevicePtr, CuDevicePtr, usize, CuStream);
    memset_d8 = "cuMemsetD8_v2"(CuDevicePtr, u8, usize);
    memset_d8_async = "cuMemsetD8Async"(CuDevicePtr, u8, usize, CuStream);
    mem_host_alloc = "cuMemHostAlloc"(*mut *mut c_void, usize, c_uint);
    mem_free_host = "cuMemFreeHost"(*mut c_void);
    module_load_data = "cuModuleLoadData"(*mut CuModule, *const c_void);
    module_unload = "cuModuleUnload"(CuModule);
    module_get_function = "cuModuleGetFunction"(*mut CuFunction, CuModule, *const c_char);
    func_set_attribute = "cuFuncSetAttribute"(CuFunction, c_int, c_int);
    launch_kernel = "cuLaunchKernel"(
        CuFunction, c_uint, c_uint, c_uint, c_uint, c_uint, c_uint, c_uint, CuStream,
        *mut *mut c_void, *mut *mut c_void
    );
    stream_create = "cuStreamCreate"(*mut CuStream, c_uint);
    stream_destroy = "cuStreamDestroy_v2"(CuStream);
    stream_synchronize = "cuStreamSynchronize"(CuStream);
    stream_wait_event = "cuStreamWaitEvent"(CuStream, CuEvent, c_uint);
    event_create = "cuEventCreate"(*mut CuEvent, c_uint);
    event_destroy = "cuEventDestroy_v2"(CuEvent);
    event_record = "cuEventRecord"(CuEvent, CuStream);
    event_synchronize = "cuEventSynchronize"(CuEvent);
    event_elapsed_time = "cuEventElapsedTime"(*mut f32, CuEvent, CuEvent);
    stream_begin_capture = "cuStreamBeginCapture_v2"(CuStream, c_uint);
    stream_end_capture = "cuStreamEndCapture"(CuStream, *mut CuGraph);
    graph_instantiate = "cuGraphInstantiateWithFlags"(*mut CuGraphExec, CuGraph, u64);
    graph_launch = "cuGraphLaunch"(CuGraphExec, CuStream);
    graph_destroy = "cuGraphDestroy"(CuGraph);
    graph_exec_destroy = "cuGraphExecDestroy"(CuGraphExec);
}

impl Api {
    /// Turns a driver status into a `Result` that names the failed call.
    pub(crate) fn check(&self, call: &'static str, status: CuResult) -> Result<()> {
        if status == SUCCESS {
            return Ok(());
        }
        let mut name: *const c_char = ptr::null();
        // SAFETY: `name` is a valid out-pointer.
        let known = unsafe { (self.get_error_name)(status, &mut name) } == SUCCESS;
        let name = if known && !name.is_null() {
            // SAFETY: the driver returned a static NUL-terminated string, and
            // the library is never unloaded.
            unsafe { CStr::from_ptr(name) }
                .to_str()
                .unwrap_or("CUDA_ERROR_UNKNOWN")
        } else {
            "CUDA_ERROR_UNKNOWN"
        };
        Err(Error::Cuda {
            call,
            code: status,
            name,
        })
    }
}

/// The process-wide driver, loaded and initialized on first use.
pub(crate) fn api() -> Result<&'static Api> {
    static API: OnceLock<Result<Api>> = OnceLock::new();
    API.get_or_init(load).as_ref().map_err(Error::clone)
}

fn load() -> Result<Api> {
    // SAFETY: loading the driver runs only its own initialization code.
    let library =
        unsafe { Library::new(LIBRARY) }.map_err(|e| Error::DriverNotFound(e.to_string()))?;
    // SAFETY: the library is the CUDA driver.
    let api = unsafe { Api::resolve(library) }?;
    // SAFETY: cuInit takes only flags, which must be zero.
    api.check("cuInit", unsafe { (api.init)(0) })?;
    Ok(api)
}
