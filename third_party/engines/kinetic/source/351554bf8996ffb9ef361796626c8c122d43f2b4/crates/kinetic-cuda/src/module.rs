use std::ffi::{c_int, c_void, CStr};
use std::ptr;
use std::rc::Rc;

use crate::context::Context;
use crate::driver::{CuFunction, CuModule};
use crate::error::Result;
use crate::stream::Stream;

/// Loaded device code.
pub struct Module {
    raw: CuModule,
    ctx: Rc<Context>,
}

impl Module {
    /// Loads a fatbin, cubin or PTX image.
    ///
    /// # Safety
    ///
    /// `image` must be a well-formed module image; PTX must end with a NUL
    /// byte. The driver reads past the slice when either is not the case.
    pub unsafe fn load(ctx: &Rc<Context>, image: &[u8]) -> Result<Rc<Module>> {
        let api = ctx.enter()?;
        let mut raw = ptr::null_mut();
        // SAFETY: the caller guarantees the image is well-formed.
        api.check("cuModuleLoadData", unsafe {
            (api.module_load_data)(&mut raw, image.as_ptr().cast::<c_void>())
        })?;
        Ok(Rc::new(Module {
            raw,
            ctx: ctx.clone(),
        }))
    }

    /// The kernel named `name`, which must be declared `extern "C"`.
    pub fn function(self: &Rc<Self>, name: &CStr) -> Result<Function> {
        let api = self.ctx.enter()?;
        let mut raw = ptr::null_mut();
        // SAFETY: `raw` is a valid out-pointer and `name` is NUL-terminated.
        api.check("cuModuleGetFunction", unsafe {
            (api.module_get_function)(&mut raw, self.raw, name.as_ptr())
        })?;
        Ok(Function {
            raw,
            module: self.clone(),
        })
    }
}

impl Drop for Module {
    fn drop(&mut self) {
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `raw` is loaded and unloaded once; every `Function`
            // holds an `Rc` to this module, so none is left.
            unsafe { (api.module_unload)(self.raw) };
        }
    }
}

/// Grid and block shape of a kernel launch.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LaunchConfig {
    pub grid: [u32; 3],
    pub block: [u32; 3],
    pub shared_bytes: u32,
}

impl LaunchConfig {
    /// `blocks` blocks of `threads` threads along x, without dynamic shared memory.
    pub fn linear(blocks: u32, threads: u32) -> LaunchConfig {
        LaunchConfig {
            grid: [blocks, 1, 1],
            block: [threads, 1, 1],
            shared_bytes: 0,
        }
    }
}

/// CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES from cuda.h.
const MAX_DYNAMIC_SHARED_SIZE_BYTES: c_int = 8;

/// A kernel in a loaded [`Module`].
pub struct Function {
    raw: CuFunction,
    module: Rc<Module>,
}

impl Function {
    /// Lets launches of this kernel ask for up to `bytes` of dynamic shared
    /// memory, beyond the default limit of 48 KiB.
    pub fn allow_shared(&self, bytes: u32) -> Result<()> {
        let api = self.module.ctx.enter()?;
        // SAFETY: the function is live; the driver validates the size.
        api.check("cuFuncSetAttribute", unsafe {
            (api.func_set_attribute)(self.raw, MAX_DYNAMIC_SHARED_SIZE_BYTES, bytes as c_int)
        })
    }

    /// Queues the kernel on `stream`.
    ///
    /// # Safety
    ///
    /// `args` must hold one pointer per kernel parameter, each to a value of
    /// that parameter's type, and every device address among the values must
    /// be valid for all accesses the kernel makes with this configuration.
    pub unsafe fn launch(
        &self,
        config: LaunchConfig,
        stream: &Stream,
        args: &mut [*mut c_void],
    ) -> Result<()> {
        let api = self.module.ctx.enter()?;
        let ([gx, gy, gz], [bx, by, bz]) = (config.grid, config.block);
        // SAFETY: the caller guarantees `args` matches the kernel; the
        // function and stream are live.
        api.check("cuLaunchKernel", unsafe {
            (api.launch_kernel)(
                self.raw,
                gx,
                gy,
                gz,
                bx,
                by,
                bz,
                config.shared_bytes,
                stream.raw(),
                args.as_mut_ptr(),
                ptr::null_mut(),
            )
        })
    }
}
