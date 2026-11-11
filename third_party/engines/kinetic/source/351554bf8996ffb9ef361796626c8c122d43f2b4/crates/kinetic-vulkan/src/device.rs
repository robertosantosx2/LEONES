use std::rc::Rc;

use ash::vk;

use crate::error::{Check, Error, Result};
use crate::physical::{DeviceInfo, PhysicalDevice};

/// Memory property bits of AMD's device-coherent types, which need a feature
/// this crate does not enable.
const AMD_COHERENT: vk::MemoryPropertyFlags = vk::MemoryPropertyFlags::from_raw(
    vk::MemoryPropertyFlags::DEVICE_COHERENT_AMD.as_raw()
        | vk::MemoryPropertyFlags::DEVICE_UNCACHED_AMD.as_raw(),
);

/// An opened device with one compute queue.
///
/// Everything made from a device holds an `Rc` to it; the queue is used
/// from one thread at a time, which `Rc` enforces.
pub struct Device {
    physical: PhysicalDevice,
    pub(crate) raw: ash::Device,
    pub(crate) push: ash::khr::push_descriptor::Device,
    queue: vk::Queue,
    pool: vk::CommandPool,
}

impl Device {
    /// Opens `physical`, or fails with [`Error::DeviceUnsupported`] when it
    /// lacks what the kernels need (see [`DeviceInfo::missing`]).
    pub fn new(physical: &PhysicalDevice) -> Result<Rc<Device>> {
        if let Some(why) = physical.info().missing() {
            return Err(Error::DeviceUnsupported(why));
        }
        let family = physical
            .compute_family
            .ok_or_else(|| Error::DeviceUnsupported("no compute queue".into()))?;
        let priorities = [1.0];
        let queues = [vk::DeviceQueueCreateInfo::default()
            .queue_family_index(family)
            .queue_priorities(&priorities)];
        let extensions = [ash::khr::push_descriptor::NAME.as_ptr()];
        let mut features13 = vk::PhysicalDeviceVulkan13Features::default()
            .subgroup_size_control(true)
            .compute_full_subgroups(true)
            .shader_integer_dot_product(true);
        let info = vk::DeviceCreateInfo::default()
            .queue_create_infos(&queues)
            .enabled_extension_names(&extensions)
            .push_next(&mut features13);
        let instance = &physical.instance.raw;
        // SAFETY: `info` and what it points to are valid for the call; the
        // features and extension were checked by `missing` above.
        let raw =
            unsafe { instance.create_device(physical.raw, &info, None) }.check("vkCreateDevice")?;
        // SAFETY: the queue family and index were requested above.
        let queue = unsafe { raw.get_device_queue(family, 0) };
        let pool_info = vk::CommandPoolCreateInfo::default()
            .queue_family_index(family)
            .flags(vk::CommandPoolCreateFlags::TRANSIENT);
        // SAFETY: `raw` is a valid device.
        let pool = match unsafe { raw.create_command_pool(&pool_info, None) } {
            Ok(pool) => pool,
            Err(result) => {
                // SAFETY: nothing else was made from the device yet.
                unsafe { raw.destroy_device(None) };
                return Err(Error::Vulkan {
                    call: "vkCreateCommandPool",
                    result,
                });
            }
        };
        let push = ash::khr::push_descriptor::Device::new(instance, &raw);
        Ok(Rc::new(Device {
            physical: physical.clone(),
            raw,
            push,
            queue,
            pool,
        }))
    }

    pub fn info(&self) -> &DeviceInfo {
        self.physical.info()
    }

    /// Allocates a primary command buffer and begins recording it; it can
    /// be submitted any number of times once ended.
    pub(crate) fn begin(&self) -> Result<vk::CommandBuffer> {
        let info = vk::CommandBufferAllocateInfo::default()
            .command_pool(self.pool)
            .level(vk::CommandBufferLevel::PRIMARY)
            .command_buffer_count(1);
        // SAFETY: the pool belongs to this device and is only used from the
        // thread that owns the device.
        let cmd = unsafe { self.raw.allocate_command_buffers(&info) }
            .check("vkAllocateCommandBuffers")?[0];
        let begin = vk::CommandBufferBeginInfo::default();
        // SAFETY: `cmd` was just allocated and is not recording.
        if let Err(result) = unsafe { self.raw.begin_command_buffer(cmd, &begin) } {
            self.free(cmd);
            return Err(Error::Vulkan {
                call: "vkBeginCommandBuffer",
                result,
            });
        }
        Ok(cmd)
    }

    /// Ends `cmd`, runs it and waits for it to finish, then frees it.
    pub(crate) fn submit(&self, cmd: vk::CommandBuffer) -> Result<()> {
        let result = self.end(cmd).and_then(|()| self.execute(cmd));
        self.free(cmd);
        result
    }

    /// Ends the recording of `cmd`.
    pub(crate) fn end(&self, cmd: vk::CommandBuffer) -> Result<()> {
        // SAFETY: `cmd` is recording and was allocated from this device.
        unsafe { self.raw.end_command_buffer(cmd) }.check("vkEndCommandBuffer")
    }

    /// Runs the ended command buffer `cmd` and waits for it to finish.
    pub(crate) fn execute(&self, cmd: vk::CommandBuffer) -> Result<()> {
        // SAFETY: a fence with default flags has no preconditions.
        let fence = unsafe { self.raw.create_fence(&vk::FenceCreateInfo::default(), None) }
            .check("vkCreateFence")?;
        let cmds = [cmd];
        let submit = [vk::SubmitInfo::default().command_buffers(&cmds)];
        // SAFETY: the queue is used from this thread only; `cmd` is
        // executable and `fence` unsignalled. Waiting before destroying the
        // fence keeps both alive while the queue uses them.
        let result = unsafe {
            self.raw
                .queue_submit(self.queue, &submit, fence)
                .check("vkQueueSubmit")
                .and_then(|()| {
                    self.raw
                        .wait_for_fences(&[fence], true, u64::MAX)
                        .check("vkWaitForFences")
                })
        };
        if result.is_err() {
            // SAFETY: as above; idling the queue makes the fence safe to free.
            let _ = unsafe { self.raw.queue_wait_idle(self.queue) };
        }
        // SAFETY: the fence is no longer in use.
        unsafe { self.raw.destroy_fence(fence, None) };
        result
    }

    /// Records a barrier after which every earlier write in `cmd`, or in work
    /// already finished, is visible to later commands and to the host.
    ///
    /// # Safety
    ///
    /// `cmd` must be recording and belong to this device.
    pub(crate) unsafe fn barrier(&self, cmd: vk::CommandBuffer) {
        let barrier = vk::MemoryBarrier::default()
            .src_access_mask(vk::AccessFlags::MEMORY_WRITE)
            .dst_access_mask(
                vk::AccessFlags::MEMORY_READ
                    | vk::AccessFlags::MEMORY_WRITE
                    | vk::AccessFlags::HOST_READ,
            );
        // SAFETY: the caller guarantees `cmd` is recording on this device.
        unsafe {
            self.raw.cmd_pipeline_barrier(
                cmd,
                vk::PipelineStageFlags::ALL_COMMANDS,
                vk::PipelineStageFlags::ALL_COMMANDS | vk::PipelineStageFlags::HOST,
                vk::DependencyFlags::empty(),
                &[barrier],
                &[],
                &[],
            )
        };
    }

    pub(crate) fn free(&self, cmd: vk::CommandBuffer) {
        // SAFETY: `cmd` came from this pool and is not executing.
        unsafe { self.raw.free_command_buffers(self.pool, &[cmd]) };
    }

    /// Memory types allowed by `bits` with all of `required`, in order of
    /// preference: device-local first when `prefer_local`, host memory
    /// after, so allocations larger than a small device-local heap (as on
    /// integrated GPUs) still succeed.
    pub(crate) fn memory_types(
        &self,
        bits: u32,
        required: vk::MemoryPropertyFlags,
        prefer_local: bool,
    ) -> Vec<u32> {
        let memory = &self.physical.memory;
        let mut types: Vec<u32> = (0..memory.memory_type_count)
            .filter(|&i| bits & (1 << i) != 0)
            .filter(|&i| {
                let flags = memory.memory_types[i as usize].property_flags;
                flags.contains(required) && !flags.intersects(AMD_COHERENT)
            })
            .collect();
        types.sort_by_key(|&i| {
            let flags = memory.memory_types[i as usize].property_flags;
            flags.contains(vk::MemoryPropertyFlags::DEVICE_LOCAL) != prefer_local
        });
        types
    }

    /// The size of the heap that memory type `ty` allocates from.
    pub(crate) fn heap_size(&self, ty: u32) -> u64 {
        let memory = &self.physical.memory;
        memory.memory_heaps[memory.memory_types[ty as usize].heap_index as usize].size
    }
}

impl Drop for Device {
    fn drop(&mut self) {
        // SAFETY: every object made from the device holds an `Rc` to it and
        // is gone; waiting for idle first ends any work still queued.
        unsafe {
            let _ = self.raw.device_wait_idle();
            self.raw.destroy_command_pool(self.pool, None);
            self.raw.destroy_device(None);
        }
    }
}
