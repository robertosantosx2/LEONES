use std::ffi::c_void;
use std::marker::PhantomData;
use std::mem::size_of;
use std::ops::Range;
use std::ptr;
use std::rc::Rc;

use crate::context::Context;
use crate::error::{Error, Result};
use crate::memory::{DeviceBuffer, DeviceCopy};
use crate::stream::Stream;

/// Page-locked host memory, which the device reads and writes directly, so
/// copies to and from it run asynchronously alongside other work.
pub struct PinnedBuffer<T: DeviceCopy> {
    ptr: *mut T,
    len: usize,
    ctx: Rc<Context>,
    _elements: PhantomData<T>,
}

impl<T: DeviceCopy> PinnedBuffer<T> {
    /// Allocates `len` elements, zeroed.
    pub fn new(ctx: &Rc<Context>, len: usize) -> Result<PinnedBuffer<T>> {
        let bytes = len
            .checked_mul(size_of::<T>())
            .ok_or_else(|| Error::Shape(format!("{len} elements overflow the address space")))?;
        let api = ctx.enter()?;
        let mut raw: *mut c_void = ptr::null_mut();
        if bytes > 0 {
            // SAFETY: `raw` is a valid out-pointer; flags 0 asks for plain
            // page-locked memory.
            api.check("cuMemHostAlloc", unsafe {
                (api.mem_host_alloc)(&mut raw, bytes, 0)
            })?;
            // SAFETY: the allocation holds `bytes` bytes, and zero bytes are a
            // valid `T`.
            unsafe { ptr::write_bytes(raw.cast::<u8>(), 0, bytes) };
        }
        Ok(PinnedBuffer {
            ptr: raw.cast(),
            len,
            ctx: ctx.clone(),
            _elements: PhantomData,
        })
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    pub fn as_slice(&self) -> &[T] {
        if self.len == 0 {
            return &[];
        }
        // SAFETY: the allocation holds `len` initialized elements.
        unsafe { std::slice::from_raw_parts(self.ptr, self.len) }
    }

    pub fn as_mut_slice(&mut self) -> &mut [T] {
        if self.len == 0 {
            return &mut [];
        }
        // SAFETY: as in `as_slice`, borrowed mutably once.
        unsafe { std::slice::from_raw_parts_mut(self.ptr, self.len) }
    }

    /// Queues a copy of elements `range` into `dst` from element `start` on
    /// `stream`.
    ///
    /// # Safety
    ///
    /// The elements in `range` must not be written, and neither buffer
    /// freed, until `stream` has passed the copy.
    pub unsafe fn upload(
        &self,
        range: Range<usize>,
        dst: &mut DeviceBuffer<T>,
        start: usize,
        stream: &Stream,
    ) -> Result<()> {
        let src = self
            .as_slice()
            .get(range.clone())
            .ok_or_else(|| Error::Shape(format!("elements {range:?} of {}", self.len)))?;
        // SAFETY: `src` is page-locked; the caller keeps it alive and
        // unchanged until the stream passes the copy.
        unsafe { dst.copy_range_from_async(start, src, stream) }
    }

    /// Queues a copy of elements `range` of `src` into this buffer from
    /// element `at` on `stream`.
    ///
    /// # Safety
    ///
    /// The destination elements must not be read or written, and neither
    /// buffer freed, until `stream` has passed the copy.
    pub unsafe fn download(
        &mut self,
        at: usize,
        src: &DeviceBuffer<T>,
        range: Range<usize>,
        stream: &Stream,
    ) -> Result<()> {
        src.check_holds(range.end, "download source")?;
        let len = range.len();
        if at.checked_add(len).is_none_or(|end| end > self.len) {
            return Err(Error::Shape(format!(
                "{len} elements at {at} of a pinned buffer of {}",
                self.len
            )));
        }
        if len == 0 {
            return Ok(());
        }
        let api = self.ctx.enter()?;
        // SAFETY: both ranges were checked; the caller keeps the destination
        // untouched until the stream passes the copy.
        api.check("cuMemcpyDtoHAsync", unsafe {
            (api.memcpy_dtoh_async)(
                self.ptr.add(at).cast::<c_void>(),
                src.ptr_at(range.start),
                len * size_of::<T>(),
                stream.raw(),
            )
        })
    }
}

impl<T: DeviceCopy> Drop for PinnedBuffer<T> {
    fn drop(&mut self) {
        if self.ptr.is_null() {
            return;
        }
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `ptr` came from cuMemHostAlloc and is freed once.
            unsafe { (api.mem_free_host)(self.ptr.cast()) };
        }
    }
}
