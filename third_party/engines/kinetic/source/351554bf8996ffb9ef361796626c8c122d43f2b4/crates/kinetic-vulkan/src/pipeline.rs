use std::io::Cursor;
use std::rc::Rc;

use ash::vk;

use crate::device::Device;
use crate::error::{Check, Error, Result};
use crate::physical::SUBGROUP;

/// A compute pipeline whose storage buffers are pushed with each dispatch
/// and whose parameters are push constants.
pub(crate) struct Kernel {
    device: Rc<Device>,
    set_layout: vk::DescriptorSetLayout,
    pub(crate) layout: vk::PipelineLayout,
    pub(crate) pipeline: vk::Pipeline,
    pub(crate) bindings: usize,
    pub(crate) push_words: usize,
}

impl Kernel {
    /// Builds the `main` entry point of `spirv`, which binds `bindings`
    /// storage buffers in set 0 and reads `push_words` 32-bit push constants.
    /// Every kernel runs with full subgroups of [`SUBGROUP`] invocations.
    pub(crate) fn new(
        device: &Rc<Device>,
        name: &str,
        spirv: &[u8],
        bindings: usize,
        push_words: usize,
    ) -> Result<Rc<Kernel>> {
        let code = ash::util::read_spv(&mut Cursor::new(spirv))
            .map_err(|e| Error::Shape(format!("embedded SPIR-V of {name}: {e}")))?;
        let raw = &device.raw;
        let mut kernel = Kernel {
            device: Rc::clone(device),
            set_layout: vk::DescriptorSetLayout::null(),
            layout: vk::PipelineLayout::null(),
            pipeline: vk::Pipeline::null(),
            bindings,
            push_words,
        };

        let slots: Vec<_> = (0..bindings as u32)
            .map(|i| {
                vk::DescriptorSetLayoutBinding::default()
                    .binding(i)
                    .descriptor_type(vk::DescriptorType::STORAGE_BUFFER)
                    .descriptor_count(1)
                    .stage_flags(vk::ShaderStageFlags::COMPUTE)
            })
            .collect();
        let set_info = vk::DescriptorSetLayoutCreateInfo::default()
            .flags(vk::DescriptorSetLayoutCreateFlags::PUSH_DESCRIPTOR_KHR)
            .bindings(&slots);
        // SAFETY: each create call below gets valid info structures; the
        // objects are destroyed by `Kernel::drop`, also on early return.
        kernel.set_layout = unsafe { raw.create_descriptor_set_layout(&set_info, None) }
            .check("vkCreateDescriptorSetLayout")?;

        let push = [vk::PushConstantRange::default()
            .stage_flags(vk::ShaderStageFlags::COMPUTE)
            .size(4 * push_words as u32)];
        let sets = [kernel.set_layout];
        let layout_info = vk::PipelineLayoutCreateInfo::default()
            .set_layouts(&sets)
            .push_constant_ranges(&push);
        // SAFETY: as above.
        kernel.layout = unsafe { raw.create_pipeline_layout(&layout_info, None) }
            .check("vkCreatePipelineLayout")?;

        let module_info = vk::ShaderModuleCreateInfo::default().code(&code);
        // SAFETY: as above; the code is naga's SPIR-V output.
        let module = unsafe { raw.create_shader_module(&module_info, None) }
            .check("vkCreateShaderModule")?;
        let mut subgroup = vk::PipelineShaderStageRequiredSubgroupSizeCreateInfo::default()
            .required_subgroup_size(SUBGROUP);
        let stage = vk::PipelineShaderStageCreateInfo::default()
            .flags(vk::PipelineShaderStageCreateFlags::REQUIRE_FULL_SUBGROUPS)
            .stage(vk::ShaderStageFlags::COMPUTE)
            .module(module)
            .name(c"main")
            .push_next(&mut subgroup);
        let info = [vk::ComputePipelineCreateInfo::default()
            .stage(stage)
            .layout(kernel.layout)];
        // SAFETY: as above; the module may be destroyed once the pipeline exists.
        let pipelines = unsafe {
            let made = raw.create_compute_pipelines(vk::PipelineCache::null(), &info, None);
            raw.destroy_shader_module(module, None);
            made
        };
        kernel.pipeline = pipelines
            .map_err(|(_, result)| result)
            .check("vkCreateComputePipelines")?[0];
        Ok(Rc::new(kernel))
    }
}

impl Drop for Kernel {
    fn drop(&mut self) {
        // SAFETY: recorded commands hold an `Rc` to the kernel, so none that
        // uses it is pending; destroying null handles is a no-op.
        unsafe {
            self.device.raw.destroy_pipeline(self.pipeline, None);
            self.device.raw.destroy_pipeline_layout(self.layout, None);
            self.device
                .raw
                .destroy_descriptor_set_layout(self.set_layout, None);
        }
    }
}
