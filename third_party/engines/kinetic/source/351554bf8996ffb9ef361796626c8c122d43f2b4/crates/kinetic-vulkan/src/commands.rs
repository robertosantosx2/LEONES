use std::rc::Rc;

use ash::vk;

use crate::device::Device;
use crate::error::{Check, Error, Result};
use crate::memory::Allocation;
use crate::pipeline::Kernel;

/// Timestamps one command list can record.
const MAX_TIMESTAMPS: u32 = 16;

/// Kernel launches recorded for one submission.
///
/// Like a CUDA stream, every command waits for the one before it, so a
/// kernel always sees the results of earlier ones. Nothing runs until
/// [`Commands::submit`], which waits for completion.
pub struct Commands {
    device: Rc<Device>,
    cmd: vk::CommandBuffer,
    queries: vk::QueryPool,
    timestamps: u32,
    kernels: Vec<Rc<Kernel>>,
    buffers: Vec<Rc<Allocation>>,
    /// Inside [`Commands::independent`]: whether a command of the group
    /// was recorded, after which the group's commands need no barrier.
    group: Option<bool>,
}

/// A timestamp recorded in a [`Commands`] list.
#[derive(Clone, Copy, Debug)]
pub struct Timestamp(u32);

/// The timestamps of a finished command list.
pub struct Timings {
    ticks: Vec<u64>,
    period: f64,
}

impl Timings {
    /// Device time from `start` to `end`.
    pub fn seconds(&self, start: Timestamp, end: Timestamp) -> f64 {
        self.ticks[end.0 as usize].wrapping_sub(self.ticks[start.0 as usize]) as f64 * self.period
    }
}

impl Commands {
    pub fn new(device: &Rc<Device>) -> Result<Commands> {
        let mut commands = Commands {
            device: Rc::clone(device),
            cmd: device.begin()?,
            queries: vk::QueryPool::null(),
            timestamps: 0,
            kernels: Vec::new(),
            buffers: Vec::new(),
            group: None,
        };
        if device.info().features.timestamps {
            let info = vk::QueryPoolCreateInfo::default()
                .query_type(vk::QueryType::TIMESTAMP)
                .query_count(MAX_TIMESTAMPS);
            // SAFETY: `info` is valid; `Drop` destroys the pool.
            commands.queries =
                unsafe { device.raw.create_query_pool(&info, None) }.check("vkCreateQueryPool")?;
            // SAFETY: `cmd` is recording and the pool belongs to its device.
            unsafe {
                device
                    .raw
                    .cmd_reset_query_pool(commands.cmd, commands.queries, 0, MAX_TIMESTAMPS)
            };
        }
        Ok(commands)
    }

    /// Records the device time once all earlier commands are done.
    pub fn timestamp(&mut self) -> Result<Timestamp> {
        if self.queries == vk::QueryPool::null() {
            return Err(Error::DeviceUnsupported(
                "the compute queue has no timestamps".into(),
            ));
        }
        if self.timestamps == MAX_TIMESTAMPS {
            return Err(Error::Shape(format!(
                "more than {MAX_TIMESTAMPS} timestamps in one command list"
            )));
        }
        let index = self.timestamps;
        self.timestamps += 1;
        // SAFETY: `cmd` is recording and the query was reset at the start.
        unsafe {
            self.device.raw.cmd_write_timestamp(
                self.cmd,
                vk::PipelineStageFlags::BOTTOM_OF_PIPE,
                self.queries,
                index,
            )
        };
        Ok(Timestamp(index))
    }

    /// Records the commands `f` records with no barriers between them, so
    /// the device may run them side by side; they still wait for the
    /// commands before. None of them may read memory another one writes,
    /// nor write memory another one writes.
    pub fn independent<T>(&mut self, f: impl FnOnce(&mut Self) -> Result<T>) -> Result<T> {
        self.group = Some(false);
        let result = f(self);
        self.group = None;
        result
    }

    /// Records the barrier before a command unless an earlier command of
    /// the same independent group already did.
    fn order(&mut self) {
        if self.group != Some(true) {
            // SAFETY: `cmd` is recording on this device.
            unsafe { self.device.barrier(self.cmd) };
        }
        if let Some(recorded) = &mut self.group {
            *recorded = true;
        }
    }

    /// Ends the recording, keeping the commands to run as often as wanted.
    pub fn finish(mut self) -> Result<Graph> {
        // SAFETY: `cmd` is recording; the barrier makes the last writes
        // visible to the host once a run is waited for.
        unsafe { self.device.barrier(self.cmd) };
        let cmd = std::mem::replace(&mut self.cmd, vk::CommandBuffer::null());
        if let Err(e) = self.device.end(cmd) {
            self.device.free(cmd);
            return Err(e);
        }
        Ok(Graph {
            device: Rc::clone(&self.device),
            cmd,
            _kernels: std::mem::take(&mut self.kernels),
            _buffers: std::mem::take(&mut self.buffers),
        })
    }

    /// Runs the recorded commands and waits for them.
    pub fn submit(mut self) -> Result<Timings> {
        let cmd = std::mem::replace(&mut self.cmd, vk::CommandBuffer::null());
        self.device.submit(cmd)?;
        let mut ticks = vec![0u64; self.timestamps as usize];
        if !ticks.is_empty() {
            // SAFETY: the queries were written by the finished submission.
            unsafe {
                self.device.raw.get_query_pool_results(
                    self.queries,
                    0,
                    &mut ticks,
                    vk::QueryResultFlags::TYPE_64 | vk::QueryResultFlags::WAIT,
                )
            }
            .check("vkGetQueryPoolResults")?;
        }
        Ok(Timings {
            ticks,
            period: self.device.info().timestamp_period,
        })
    }

    /// Records `kernel` over `groups` workgroups with `buffers` at bindings
    /// 0, 1, ... and `push` as its push constants.
    ///
    /// # Safety
    ///
    /// The buffers and constants must be what the kernel's shader declares,
    /// and the shader must stay inside the buffers for these constants.
    pub(crate) unsafe fn dispatch(
        &mut self,
        kernel: &Rc<Kernel>,
        buffers: &[&Rc<Allocation>],
        push: &[u32],
        groups: [u32; 3],
    ) {
        debug_assert_eq!(buffers.len(), kernel.bindings);
        debug_assert_eq!(push.len(), kernel.push_words);
        let infos: Vec<[vk::DescriptorBufferInfo; 1]> = buffers
            .iter()
            .map(|b| {
                [vk::DescriptorBufferInfo::default()
                    .buffer(b.buffer)
                    .range(vk::WHOLE_SIZE)]
            })
            .collect();
        let writes: Vec<_> = infos
            .iter()
            .enumerate()
            .map(|(i, info)| {
                vk::WriteDescriptorSet::default()
                    .dst_binding(i as u32)
                    .descriptor_type(vk::DescriptorType::STORAGE_BUFFER)
                    .buffer_info(info)
            })
            .collect();
        let push: Vec<u8> = push.iter().flat_map(|w| w.to_ne_bytes()).collect();
        self.order();
        let (raw, cmd) = (&self.device.raw, self.cmd);
        // SAFETY: `cmd` is recording on the kernel's device; the caller
        // vouches for the bindings, and the `Rc`s kept below hold the
        // kernel and buffers alive until the list is submitted.
        unsafe {
            raw.cmd_bind_pipeline(cmd, vk::PipelineBindPoint::COMPUTE, kernel.pipeline);
            self.device.push.cmd_push_descriptor_set(
                cmd,
                vk::PipelineBindPoint::COMPUTE,
                kernel.layout,
                0,
                &writes,
            );
            raw.cmd_push_constants(cmd, kernel.layout, vk::ShaderStageFlags::COMPUTE, 0, &push);
            raw.cmd_dispatch(cmd, groups[0], groups[1], groups[2]);
        }
        self.kernels.push(Rc::clone(kernel));
        self.buffers.extend(buffers.iter().map(|&b| Rc::clone(b)));
    }

    /// Records a copy of `bytes` bytes from `src` at byte `src_offset` to
    /// `dst` at byte `dst_offset`, ordered like a kernel.
    ///
    /// # Safety
    ///
    /// Both ranges must lie inside their buffers.
    pub(crate) unsafe fn copy(
        &mut self,
        src: &Rc<Allocation>,
        src_offset: usize,
        dst: &Rc<Allocation>,
        dst_offset: usize,
        bytes: usize,
    ) {
        let region = vk::BufferCopy {
            src_offset: src_offset as u64,
            dst_offset: dst_offset as u64,
            size: bytes as u64,
        };
        self.order();
        // SAFETY: `cmd` is recording; both buffers belong to its device and
        // the caller vouches for the ranges.
        unsafe {
            self.device
                .raw
                .cmd_copy_buffer(self.cmd, src.buffer, dst.buffer, &[region]);
        }
        self.buffers.extend([Rc::clone(src), Rc::clone(dst)]);
    }
}

/// Commands recorded once and run many times, like a CUDA graph. Buffers
/// and constants are fixed at recording; what changes between runs is the
/// contents of the buffers.
pub struct Graph {
    device: Rc<Device>,
    cmd: vk::CommandBuffer,
    _kernels: Vec<Rc<Kernel>>,
    _buffers: Vec<Rc<Allocation>>,
}

impl Graph {
    /// Runs the commands and waits for them; every write is then visible
    /// to the host.
    pub fn launch(&self) -> Result<()> {
        self.device.execute(self.cmd)
    }
}

impl Drop for Graph {
    fn drop(&mut self) {
        self.device.free(self.cmd);
    }
}

impl Drop for Commands {
    fn drop(&mut self) {
        // SAFETY: an unsubmitted buffer never ran, and a submitted one was
        // waited for; destroying a null pool is a no-op.
        unsafe {
            if self.cmd != vk::CommandBuffer::null() {
                self.device.free(self.cmd);
            }
            self.device.raw.destroy_query_pool(self.queries, None);
        }
    }
}
