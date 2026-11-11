use std::ffi::c_void;
use std::marker::PhantomData;
use std::mem::{size_of, size_of_val};
use std::rc::Rc;

use crate::context::Context;
use crate::driver::CuDevicePtr;
use crate::error::{Error, Result};
use crate::stream::Stream;

mod sealed {
    pub trait Sealed {}
}

/// Plain values that can be copied to and from the device byte for byte.
pub trait DeviceCopy: Copy + Default + sealed::Sealed {}

macro_rules! device_copy {
    ($($t:ty),*) => {$(
        impl sealed::Sealed for $t {}
        impl DeviceCopy for $t {}
    )*};
}

device_copy!(u8, i8, u16, u32, f32);

/// An array of `T` in device memory.
pub struct DeviceBuffer<T: DeviceCopy> {
    ptr: CuDevicePtr,
    len: usize,
    ctx: Rc<Context>,
    _elements: PhantomData<T>,
}

impl<T: DeviceCopy> DeviceBuffer<T> {
    /// Allocates `len` elements with unspecified contents.
    pub fn new(ctx: &Rc<Context>, len: usize) -> Result<Self> {
        let bytes = len
            .checked_mul(size_of::<T>())
            .ok_or_else(|| Error::Shape(format!("{len} elements overflow the address space")))?;
        let mut ptr = 0;
        if bytes > 0 {
            let api = ctx.enter()?;
            // SAFETY: `ptr` is a valid out-pointer.
            api.check("cuMemAlloc", unsafe { (api.mem_alloc)(&mut ptr, bytes) })?;
        }
        Ok(DeviceBuffer {
            ptr,
            len,
            ctx: ctx.clone(),
            _elements: PhantomData,
        })
    }

    pub fn from_slice(ctx: &Rc<Context>, data: &[T]) -> Result<Self> {
        let mut buf = Self::new(ctx, data.len())?;
        buf.copy_from(data)?;
        Ok(buf)
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// The device address, for passing to kernels.
    pub fn device_ptr(&self) -> u64 {
        self.ptr
    }

    fn bytes(&self) -> usize {
        self.len * size_of::<T>()
    }

    fn check_len(&self, other: usize) -> Result<()> {
        if other == self.len {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "copy of {other} elements into or out of a buffer of {}",
                self.len
            )))
        }
    }

    /// Copies `src` into the buffer; returns once `src` may be reused.
    pub fn copy_from(&mut self, src: &[T]) -> Result<()> {
        self.check_len(src.len())?;
        if self.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: both sides hold `bytes()` bytes and `T` is plain data.
        api.check("cuMemcpyHtoD", unsafe {
            (api.memcpy_htod)(self.ptr, src.as_ptr().cast::<c_void>(), self.bytes())
        })
    }

    /// Copies the buffer into `dst` after all earlier work in the context.
    pub fn copy_to(&self, dst: &mut [T]) -> Result<()> {
        self.check_len(dst.len())?;
        if self.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: both sides hold `bytes()` bytes and any bytes are a valid `T`.
        api.check("cuMemcpyDtoH", unsafe {
            (api.memcpy_dtoh)(dst.as_mut_ptr().cast::<c_void>(), self.ptr, self.bytes())
        })
    }

    /// Copies elements `start..start + dst.len()` into `dst` after all
    /// earlier work in the context.
    pub fn copy_range_to(&self, start: usize, dst: &mut [T]) -> Result<()> {
        self.check_range(start, dst.len())?;
        if dst.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: the range lies inside the buffer and `dst` holds as many
        // elements; any bytes are a valid `T`.
        api.check("cuMemcpyDtoH", unsafe {
            (api.memcpy_dtoh)(
                dst.as_mut_ptr().cast::<c_void>(),
                self.ptr_at(start),
                size_of_val(dst),
            )
        })
    }

    /// Copies `src` into elements `start..start + src.len()`; returns once
    /// `src` may be reused.
    pub fn copy_range_from(&mut self, start: usize, src: &[T]) -> Result<()> {
        self.check_range(start, src.len())?;
        if src.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: the range lies inside the buffer and `src` holds as many
        // elements of plain data.
        api.check("cuMemcpyHtoD", unsafe {
            (api.memcpy_htod)(
                self.ptr_at(start),
                src.as_ptr().cast::<c_void>(),
                size_of_val(src),
            )
        })
    }

    /// Queues a copy of `src` into elements `start..start + src.len()` on
    /// `stream`.
    ///
    /// # Safety
    ///
    /// As for [`DeviceBuffer::copy_from_async`].
    pub(crate) unsafe fn copy_range_from_async(
        &mut self,
        start: usize,
        src: &[T],
        stream: &Stream,
    ) -> Result<()> {
        self.check_range(start, src.len())?;
        if src.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: the range lies inside the buffer; the caller keeps `src`
        // alive for the copy.
        api.check("cuMemcpyHtoDAsync", unsafe {
            (api.memcpy_htod_async)(
                self.ptr_at(start),
                src.as_ptr().cast::<c_void>(),
                size_of_val(src),
                stream.raw(),
            )
        })
    }

    /// Sets every byte to zero.
    pub fn zero(&mut self) -> Result<()> {
        if self.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: the buffer holds `bytes()` bytes.
        api.check("cuMemsetD8", unsafe {
            (api.memset_d8)(self.ptr, 0, self.bytes())
        })
    }

    /// Queues setting elements `..len` to zero on `stream`.
    pub(crate) fn zero_prefix(&mut self, len: usize, stream: &Stream) -> Result<()> {
        self.check_holds(len, "zeroed range")?;
        if len == 0 {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: the range lies inside the buffer.
        api.check("cuMemsetD8Async", unsafe {
            (api.memset_d8_async)(self.ptr, 0, len * size_of::<T>(), stream.raw())
        })
    }

    /// The device address of element `index`.
    pub(crate) fn ptr_at(&self, index: usize) -> u64 {
        self.ptr + (index * size_of::<T>()) as u64
    }

    /// Fails unless the buffer holds at least `len` elements, naming it `what`.
    pub(crate) fn check_holds(&self, len: usize, what: &str) -> Result<()> {
        if len <= self.len {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "{what} needs {len} elements, its buffer holds {}",
                self.len
            )))
        }
    }

    fn check_range(&self, start: usize, len: usize) -> Result<()> {
        if start.checked_add(len).is_some_and(|end| end <= self.len) {
            Ok(())
        } else {
            Err(Error::Shape(format!(
                "elements {start}..{start}+{len} of a buffer of {}",
                self.len
            )))
        }
    }

    pub fn to_vec(&self) -> Result<Vec<T>> {
        let mut out = vec![T::default(); self.len];
        self.copy_to(&mut out)?;
        Ok(out)
    }

    /// Queues a copy of `src` into the buffer on `stream`.
    ///
    /// # Safety
    ///
    /// If `src` is page-locked host memory the copy runs after this returns,
    /// so `src` must not be written or freed until `stream` has passed it.
    /// Ordinary pageable memory is staged before the call returns.
    pub unsafe fn copy_from_async(&mut self, src: &[T], stream: &Stream) -> Result<()> {
        self.check_len(src.len())?;
        if self.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: sizes match; the caller keeps `src` alive for the copy.
        api.check("cuMemcpyHtoDAsync", unsafe {
            (api.memcpy_htod_async)(
                self.ptr,
                src.as_ptr().cast::<c_void>(),
                self.bytes(),
                stream.raw(),
            )
        })
    }

    /// Queues a copy of elements `range` of `src` into this buffer from
    /// element `start` on `stream`.
    pub fn copy_from_device(
        &mut self,
        start: usize,
        src: &DeviceBuffer<T>,
        range: std::ops::Range<usize>,
        stream: &Stream,
    ) -> Result<()> {
        src.check_range(range.start, range.len())?;
        self.check_range(start, range.len())?;
        if range.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: both ranges lie inside their buffers, and the driver
        // waits for queued work before freeing either.
        api.check("cuMemcpyDtoDAsync", unsafe {
            (api.memcpy_dtod_async)(
                self.ptr_at(start),
                src.ptr_at(range.start),
                range.len() * size_of::<T>(),
                stream.raw(),
            )
        })
    }

    /// Queues a copy of the buffer into `dst` on `stream`.
    ///
    /// # Safety
    ///
    /// If `dst` is page-locked host memory the copy runs after this returns,
    /// so `dst` must not be read, written or freed until `stream` has passed
    /// it. Copies into pageable memory finish before the call returns.
    pub unsafe fn copy_to_async(&self, dst: &mut [T], stream: &Stream) -> Result<()> {
        self.check_len(dst.len())?;
        if self.is_empty() {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: sizes match; the caller keeps `dst` alive for the copy.
        api.check("cuMemcpyDtoHAsync", unsafe {
            (api.memcpy_dtoh_async)(
                dst.as_mut_ptr().cast::<c_void>(),
                self.ptr,
                self.bytes(),
                stream.raw(),
            )
        })
    }
}

impl<T: DeviceCopy> Drop for DeviceBuffer<T> {
    fn drop(&mut self) {
        if self.ptr == 0 {
            return;
        }
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `ptr` came from cuMemAlloc and is freed once; the driver
            // waits for kernels still using it.
            unsafe { (api.mem_free)(self.ptr) };
        }
    }
}
