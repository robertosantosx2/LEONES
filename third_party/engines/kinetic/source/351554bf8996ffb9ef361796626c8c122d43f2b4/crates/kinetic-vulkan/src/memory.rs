use std::marker::PhantomData;
use std::mem::size_of;
use std::rc::Rc;

use ash::vk;

use crate::commands::Commands;
use crate::device::Device;
use crate::error::{Check, Error, Result};

/// Host-visible bounce buffer size for copies to and from device memory.
const STAGING_BYTES: usize = 64 << 20;

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

/// A buffer and the memory bound to it. Recorded commands hold an `Rc` to
/// each allocation they use, so it outlives their execution.
pub(crate) struct Allocation {
    device: Rc<Device>,
    pub(crate) buffer: vk::Buffer,
    memory: vk::DeviceMemory,
}

impl Allocation {
    /// Tries each allowed memory type in [`Device::memory_types`] order
    /// until one has room.
    fn new(
        device: &Rc<Device>,
        bytes: u64,
        usage: vk::BufferUsageFlags,
        required: vk::MemoryPropertyFlags,
        prefer_local: bool,
    ) -> Result<Allocation> {
        let info = vk::BufferCreateInfo::default()
            .size(bytes.max(4))
            .usage(usage)
            .sharing_mode(vk::SharingMode::EXCLUSIVE);
        let raw = &device.raw;
        // SAFETY: `info` is valid for the call.
        let buffer = unsafe { raw.create_buffer(&info, None) }.check("vkCreateBuffer")?;
        let mut alloc = Allocation {
            device: Rc::clone(device),
            buffer,
            memory: vk::DeviceMemory::null(),
        };
        // SAFETY: `buffer` belongs to this device.
        let needs = unsafe { raw.get_buffer_memory_requirements(buffer) };
        let mut last = vk::Result::ERROR_OUT_OF_DEVICE_MEMORY;
        for ty in device.memory_types(needs.memory_type_bits, required, prefer_local) {
            if device.heap_size(ty) < needs.size {
                continue;
            }
            let info = vk::MemoryAllocateInfo::default()
                .allocation_size(needs.size)
                .memory_type_index(ty);
            // SAFETY: the type index is one the buffer allows.
            match unsafe { raw.allocate_memory(&info, None) } {
                Ok(memory) => {
                    alloc.memory = memory;
                    // SAFETY: fresh memory of the required size and type.
                    unsafe { raw.bind_buffer_memory(buffer, memory, 0) }
                        .check("vkBindBufferMemory")?;
                    return Ok(alloc);
                }
                Err(
                    e @ (vk::Result::ERROR_OUT_OF_DEVICE_MEMORY
                    | vk::Result::ERROR_OUT_OF_HOST_MEMORY),
                ) => last = e,
                Err(result) => {
                    return Err(Error::Vulkan {
                        call: "vkAllocateMemory",
                        result,
                    })
                }
            }
        }
        Err(Error::Vulkan {
            call: "vkAllocateMemory",
            result: last,
        })
    }
}

impl Drop for Allocation {
    fn drop(&mut self) {
        // SAFETY: work using the buffer was waited for by whoever submitted it.
        unsafe {
            self.device.raw.destroy_buffer(self.buffer, None);
            self.device.raw.free_memory(self.memory, None);
        }
    }
}

/// An array of `T` in device memory, bindable as a storage buffer.
///
/// Device-local memory is used when it has room; integrated GPUs with a
/// small device-local heap fall back to system memory, the same DRAM behind
/// a different mapping, which they read somewhat slower.
pub struct DeviceBuffer<T: DeviceCopy> {
    alloc: Rc<Allocation>,
    len: usize,
    _elements: PhantomData<T>,
}

impl<T: DeviceCopy> DeviceBuffer<T> {
    /// Allocates `len` zeroed elements.
    pub fn new(device: &Rc<Device>, len: usize) -> Result<Self> {
        let bytes = len
            .checked_mul(size_of::<T>())
            .map(|b| b as u64)
            .filter(|&b| b <= device.info().max_buffer_bytes)
            .ok_or_else(|| {
                Error::Shape(format!(
                    "buffer of {len} elements exceeds the device's storage buffer limit"
                ))
            })?;
        let alloc = Allocation::new(
            device,
            bytes,
            vk::BufferUsageFlags::STORAGE_BUFFER
                | vk::BufferUsageFlags::TRANSFER_SRC
                | vk::BufferUsageFlags::TRANSFER_DST,
            vk::MemoryPropertyFlags::empty(),
            true,
        )?;
        let mut buf = DeviceBuffer {
            alloc: Rc::new(alloc),
            len,
            _elements: PhantomData,
        };
        buf.zero()?;
        Ok(buf)
    }

    /// Sets every element to zero once all submitted work is done.
    pub fn zero(&mut self) -> Result<()> {
        let device = self.device();
        let cmd = device.begin()?;
        // SAFETY: `cmd` is recording and the buffer belongs to its device.
        unsafe {
            device.barrier(cmd);
            device
                .raw
                .cmd_fill_buffer(cmd, self.raw(), 0, vk::WHOLE_SIZE, 0);
            device.barrier(cmd);
        }
        device.submit(cmd)
    }

    pub fn from_slice(device: &Rc<Device>, data: &[T]) -> Result<Self> {
        let mut buf = Self::new(device, data.len())?;
        buf.copy_from(data)?;
        Ok(buf)
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    pub(crate) fn raw(&self) -> vk::Buffer {
        self.alloc.buffer
    }

    pub(crate) fn allocation(&self) -> &Rc<Allocation> {
        &self.alloc
    }

    fn device(&self) -> &Rc<Device> {
        &self.alloc.device
    }

    /// Copies `src` into the buffer; returns once the copy is done.
    pub fn copy_from(&mut self, src: &[T]) -> Result<()> {
        self.check_len(src.len())?;
        self.copy_range_from(0, src)
    }

    /// Copies the buffer into `dst` once all submitted work is done.
    pub fn copy_to(&self, dst: &mut [T]) -> Result<()> {
        self.check_len(dst.len())?;
        self.copy_range_to(0, dst)
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

    /// Copies `src` into the buffer from element `at`; returns once the
    /// copy is done.
    pub fn copy_range_from(&mut self, at: usize, src: &[T]) -> Result<()> {
        check_range("copy", at, src.len(), self.len)?;
        if src.is_empty() {
            return Ok(());
        }
        // SAFETY: `T` is plain data, so its bytes may be read as `u8`.
        let bytes = unsafe { std::slice::from_raw_parts(src.as_ptr().cast(), size_of_val(src)) };
        let start = at * size_of::<T>();
        let mut staging = Staging::new(self.device(), bytes.len())?;
        for (i, chunk) in bytes.chunks(STAGING_BYTES).enumerate() {
            staging.slice()[..chunk.len()].copy_from_slice(chunk);
            staging.copy(
                staging.buf.alloc.buffer,
                self.raw(),
                0,
                (start + i * STAGING_BYTES) as u64,
                chunk.len(),
            )?;
        }
        Ok(())
    }

    /// Copies `dst.len()` elements from element `at` into `dst` once all
    /// submitted work is done.
    pub fn copy_range_to(&self, at: usize, dst: &mut [T]) -> Result<()> {
        check_range("copy", at, dst.len(), self.len)?;
        if dst.is_empty() {
            return Ok(());
        }
        // SAFETY: `T` is plain data and every byte pattern is a valid `T`.
        let bytes = unsafe {
            std::slice::from_raw_parts_mut(dst.as_mut_ptr().cast::<u8>(), size_of_val(dst))
        };
        let start = at * size_of::<T>();
        let mut staging = Staging::new(self.device(), bytes.len())?;
        for (i, chunk) in bytes.chunks_mut(STAGING_BYTES).enumerate() {
            staging.copy(
                self.raw(),
                staging.buf.alloc.buffer,
                (start + i * STAGING_BYTES) as u64,
                0,
                chunk.len(),
            )?;
            chunk.copy_from_slice(&staging.slice()[..chunk.len()]);
        }
        Ok(())
    }

    pub fn to_vec(&self) -> Result<Vec<T>> {
        let mut out = vec![T::default(); self.len];
        self.copy_to(&mut out)?;
        Ok(out)
    }
}

/// An array of `T` in host-visible memory, mapped for the life of the
/// buffer: the host reads and writes it in place, and recorded commands
/// copy between it and device buffers.
///
/// The device touches it only while commands run, and running them waits
/// for them, so host access never races with the device.
pub struct HostBuffer<T: DeviceCopy> {
    alloc: Rc<Allocation>,
    ptr: *mut T,
    len: usize,
}

impl<T: DeviceCopy> HostBuffer<T> {
    /// Allocates `len` zeroed elements.
    pub fn new(device: &Rc<Device>, len: usize) -> Result<Self> {
        let bytes = len
            .checked_mul(size_of::<T>())
            .ok_or_else(|| Error::Shape(format!("host buffer of {len} elements")))?;
        let alloc = Allocation::new(
            device,
            bytes as u64,
            vk::BufferUsageFlags::STORAGE_BUFFER
                | vk::BufferUsageFlags::TRANSFER_SRC
                | vk::BufferUsageFlags::TRANSFER_DST,
            vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
            false,
        )?;
        // SAFETY: the memory is host-visible, not yet mapped, and freed only
        // after `alloc` is dropped, which unmaps it implicitly.
        let ptr = unsafe {
            device
                .raw
                .map_memory(alloc.memory, 0, vk::WHOLE_SIZE, vk::MemoryMapFlags::empty())
        }
        .check("vkMapMemory")?
        .cast::<T>();
        // SAFETY: the mapping covers `bytes` bytes, and zero bytes are a valid `T`.
        unsafe { std::ptr::write_bytes(ptr, 0, len) };
        Ok(HostBuffer {
            alloc: Rc::new(alloc),
            ptr,
            len,
        })
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    pub fn as_slice(&self) -> &[T] {
        // SAFETY: the mapping holds `len` initialised elements and lives as
        // long as `self`; see the type's comment on device access.
        unsafe { std::slice::from_raw_parts(self.ptr, self.len) }
    }

    pub fn as_mut_slice(&mut self) -> &mut [T] {
        // SAFETY: as in `as_slice`, and `&mut self` makes the access unique.
        unsafe { std::slice::from_raw_parts_mut(self.ptr, self.len) }
    }

    pub(crate) fn allocation(&self) -> &Rc<Allocation> {
        &self.alloc
    }
}

fn check_range(what: &str, at: usize, len: usize, size: usize) -> Result<()> {
    match at.checked_add(len) {
        Some(end) if end <= size => Ok(()),
        _ => Err(Error::Shape(format!(
            "{what} of {len} elements at {at} past a buffer of {size}"
        ))),
    }
}

impl Commands {
    /// Records a copy of `len` elements from `src` at `src_at` to `dst` at
    /// `dst_at`.
    pub fn upload<T: DeviceCopy>(
        &mut self,
        src: &HostBuffer<T>,
        src_at: usize,
        dst: &DeviceBuffer<T>,
        dst_at: usize,
        len: usize,
    ) -> Result<()> {
        check_range("upload", src_at, len, src.len())?;
        check_range("upload", dst_at, len, dst.len())?;
        let t = size_of::<T>();
        // SAFETY: both ranges were checked above.
        unsafe {
            self.copy(
                src.allocation(),
                src_at * t,
                dst.allocation(),
                dst_at * t,
                len * t,
            )
        };
        Ok(())
    }

    /// Records a copy of `len` elements from `src` at `src_at` to `dst` at
    /// `dst_at`.
    pub fn download<T: DeviceCopy>(
        &mut self,
        src: &DeviceBuffer<T>,
        src_at: usize,
        dst: &HostBuffer<T>,
        dst_at: usize,
        len: usize,
    ) -> Result<()> {
        check_range("download", src_at, len, src.len())?;
        check_range("download", dst_at, len, dst.len())?;
        let t = size_of::<T>();
        // SAFETY: both ranges were checked above.
        unsafe {
            self.copy(
                src.allocation(),
                src_at * t,
                dst.allocation(),
                dst_at * t,
                len * t,
            )
        };
        Ok(())
    }
}

/// A host buffer of at most [`STAGING_BYTES`] for one-off copies.
struct Staging {
    buf: HostBuffer<u8>,
}

impl Staging {
    fn new(device: &Rc<Device>, bytes: usize) -> Result<Staging> {
        Ok(Staging {
            buf: HostBuffer::new(device, bytes.min(STAGING_BYTES))?,
        })
    }

    fn slice(&mut self) -> &mut [u8] {
        self.buf.as_mut_slice()
    }

    /// Copies `bytes` between two buffers and waits for it.
    fn copy(
        &self,
        src: vk::Buffer,
        dst: vk::Buffer,
        src_offset: u64,
        dst_offset: u64,
        bytes: usize,
    ) -> Result<()> {
        let device = &self.buf.alloc.device;
        let cmd = device.begin()?;
        let region = vk::BufferCopy {
            src_offset,
            dst_offset,
            size: bytes as u64,
        };
        // SAFETY: `cmd` is recording; both buffers belong to its device and
        // hold the copied range.
        unsafe {
            device.barrier(cmd);
            device.raw.cmd_copy_buffer(cmd, src, dst, &[region]);
            device.barrier(cmd);
        }
        device.submit(cmd)
    }
}
