//! Model architectures, built from shared blocks.
//!
//! [`load`] reads a GGUF file's architecture and assembles a [`Model`] whose
//! weights stay in the memory-mapped file.

mod arch;
mod blocks;
mod convoy;
#[cfg(feature = "cuda")]
pub mod cuda;
#[cfg(any(feature = "cuda", feature = "vulkan"))]
mod device_state;
mod embed;
mod folds;
mod head;
mod input;
mod loader;
pub mod lora;
pub mod memory;
mod model;
mod per_layer;
pub mod speculative;
#[cfg(feature = "vulkan")]
pub mod vulkan;
pub mod warm;

use std::fmt;

use kinetic_gguf::TensorSource;

pub use arch::rope::{RopeScaling, ScalingKind};
use arch::{Basics, Body, Stack};
pub use convoy::Seat;
pub use embed::{Embedder, Pooling};
use folds::Folds;
pub use input::Input;
use loader::Loader;
use model::Layer;
pub use model::{Forward, Model, MtpState, State};

#[derive(Debug)]
pub struct LoadError(pub String);

impl fmt::Display for LoadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for LoadError {}

/// Architectures Kinetic can run, by their GGUF name.
pub fn architectures() -> impl Iterator<Item = &'static str> {
    arch::FAMILIES.iter().flat_map(|f| f.names.iter().copied())
}

/// Whether Kinetic runs the GGUF architecture `arch`.
pub fn supports(arch: &str) -> bool {
    arch::family(arch).is_some()
}

/// Whether `arch` is a BERT-style encoder, which only embeds.
pub fn is_encoder(arch: &str) -> bool {
    arch::family(arch).is_some_and(|f| matches!(f.body, Body::Encoder(_)))
}

/// Builds the model stored in `file`.
pub fn load(file: &dyn TensorSource) -> Result<Model<'_>, LoadError> {
    load_with(file, &RopeScaling::default())
}

/// [`load`] with the rotary scaling `rope` overriding the file's.
pub fn load_with<'a>(
    file: &'a dyn TensorSource,
    rope: &RopeScaling,
) -> Result<Model<'a>, LoadError> {
    let arch = architecture(file)?;
    if arch::family(arch).is_some_and(|f| !matches!(f.body, Body::Decoder(_))) {
        return Err(LoadError(format!(
            "{arch} is an encoder; load it with Embedder"
        )));
    }
    build(file, rope)
}

fn architecture(file: &dyn TensorSource) -> Result<&str, LoadError> {
    file.header()
        .architecture()
        .ok_or_else(|| LoadError("file does not name its architecture".into()))
}

/// The layers and head stored in `file`, encoders whose layers fit a
/// [`Model`] included.
pub(crate) fn build<'a>(
    file: &'a dyn TensorSource,
    rope: &RopeScaling,
) -> Result<Model<'a>, LoadError> {
    let l = Loader::new(file);
    let arch = architecture(file)?;
    let d = l.usize("embedding_length")?;
    let eps = l.f32("attention.layer_norm_rms_epsilon")?;
    let folds = Folds::read(file.header())?;
    let family = arch::family(arch)
        .ok_or_else(|| LoadError(format!("architecture {arch} is not supported yet")))?;
    let (Body::Decoder(build_layers) | Body::Bidirectional(build_layers)) = family.body else {
        return Err(LoadError(format!(
            "{arch} is an encoder; load it with Embedder"
        )));
    };
    let basics = Basics {
        arch,
        d,
        eps,
        folds: folds.as_ref(),
    };
    let Stack {
        mut layers,
        mut mtp,
        per_layer,
    } = build_layers(&l, &basics)?;

    let mut scaled: Vec<&mut Layer> = layers
        .iter_mut()
        .chain(mtp.as_mut().map(|m| &mut m.layer))
        .collect();
    arch::rope::apply(&l, &mut scaled, rope)?;

    let n_vocab = file
        .header()
        .tensor("token_embd.weight")
        .map(|t| t.dims[1] as usize)
        .ok_or_else(|| LoadError("missing tensor token_embd.weight".into()))?;
    let embd = l.matrix("token_embd.weight", d, n_vocab)?;
    let output = match file.header().tensor("output.weight") {
        Some(_) => l.matrix("output.weight", d, n_vocab)?,
        None => embd,
    };
    let (head_folding, embd_folding) = match &folds {
        Some(f) => (
            f.block(&[("output.weight", d)])?,
            f.table("token_embd.weight", d)?,
        ),
        None => (None, None),
    };
    if head_folding.is_none() && embd_folding.is_some() && std::ptr::eq(output.data, embd.data) {
        return Err(LoadError(
            "a folded embedding table cannot double as the output head".into(),
        ));
    }
    if let Some(f) = &folds {
        f.finish()?;
    }
    let mut output_norm = l.vector(family.output_norm, d)?;
    // scaling the final norm's weights divides the logits through the
    // linear output head
    if family.logit_scale {
        let scale = l.f32_or("logit_scale", 1.0)?;
        output_norm.iter_mut().for_each(|w| *w /= scale);
    }
    let embd_scale = match family.sqrt_embd_scale {
        true => Some((d as f32).sqrt()),
        false => Some(l.f32_or("embedding_scale", 0.0)?).filter(|&s| s != 0.0),
    };
    Ok(Model {
        n_embd: d,
        eps,
        embd,
        embd_scale,
        embd_folding,
        output,
        head_folding,
        #[cfg(any(feature = "cuda", feature = "vulkan"))]
        folded: folds.is_some(),
        output_norm,
        logit_cap: Some(l.f32_or("final_logit_softcapping", 0.0)?).filter(|&c| c != 0.0),
        layers,
        per_layer,
        mtp,
        grid_rope: file.header().arch_key("rope.dimension_sections").is_some(),
        shortlist: Default::default(),
        convoy: Default::default(),
    })
}
