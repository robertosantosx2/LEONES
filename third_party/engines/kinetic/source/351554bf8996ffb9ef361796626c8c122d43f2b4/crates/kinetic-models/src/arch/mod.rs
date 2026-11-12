//! Model families. Each file declares the [`Family`] it builds; [`FAMILIES`]
//! lists them all, and loading, support checks and listings read only that
//! list.

pub(crate) mod bert;
pub(crate) mod falcon_h1;
pub(crate) mod gemma4;
pub(crate) mod gemma_embedding;
pub(crate) mod granite;
pub(crate) mod lfm2;
pub(crate) mod lfm3;
mod mamba;
mod moe;
pub(crate) mod qwen35;
pub(crate) mod rope;
pub(crate) mod transformer;

use crate::arch::bert::Encoder;
use crate::folds::Folds;
use crate::loader::Loader;
use crate::model::{Layer, Mtp};
use crate::per_layer::PerLayer;
use crate::LoadError;

/// Every family Kinetic runs.
pub(crate) const FAMILIES: &[Family] = &[
    qwen35::FAMILY,
    lfm3::FAMILY,
    lfm2::FAMILY,
    transformer::FAMILY,
    transformer::GEMMA3,
    gemma4::FAMILY,
    granite::FAMILY,
    falcon_h1::FAMILY,
    bert::FAMILY,
    transformer::GEMMA_EMBEDDING,
];

/// The family whose GGUF architecture name is `arch`.
pub(crate) fn family(arch: &str) -> Option<&'static Family> {
    FAMILIES.iter().find(|f| f.names.contains(&arch))
}

/// One model family: the GGUF architecture names it answers to, how its
/// layers are built and the few ways its embedding and head differ.
#[derive(Clone, Copy)]
pub(crate) struct Family {
    pub names: &'static [&'static str],
    pub body: Body,
    /// Tensor holding the weights of the norm before the output head.
    pub output_norm: &'static str,
    /// Embeddings are scaled by the square root of the width, as in Gemma.
    pub sqrt_embd_scale: bool,
    /// Logits are divided by the file's `logit_scale`, as in Granite.
    pub logit_scale: bool,
}

impl Family {
    /// A text decoder with the usual embedding and head.
    pub const fn decoder(names: &'static [&'static str], layers: BuildLayers) -> Family {
        Family {
            names,
            body: Body::Decoder(layers),
            output_norm: "output_norm.weight",
            sqrt_embd_scale: false,
            logit_scale: false,
        }
    }
}

#[derive(Clone, Copy)]
pub(crate) enum Body {
    /// Generates text.
    Decoder(BuildLayers),
    /// Decoder layers in which every token sees the whole input, for
    /// embeddings only.
    Bidirectional(BuildLayers),
    /// A BERT-style encoder with its own loader, for embeddings only.
    Encoder(BuildEncoder),
}

pub(crate) type BuildLayers = for<'a> fn(&Loader<'a>, &Basics) -> Result<Stack<'a>, LoadError>;
pub(crate) type BuildEncoder = for<'a> fn(&Loader<'a>, &str) -> Result<Encoder<'a>, LoadError>;

/// What every layer builder gets besides the file.
pub(crate) struct Basics<'f> {
    /// The file's architecture name, for families that answer to several.
    pub arch: &'f str,
    pub d: usize,
    pub eps: f32,
    pub folds: Option<&'f Folds>,
}

/// The layers a builder returns, the prediction block if the file has one
/// and the per-layer token inputs if the model has them.
pub(crate) struct Stack<'a> {
    pub layers: Vec<Layer<'a>>,
    pub mtp: Option<Mtp<'a>>,
    pub per_layer: Option<PerLayer<'a>>,
}

impl<'a> From<Vec<Layer<'a>>> for Stack<'a> {
    fn from(layers: Vec<Layer<'a>>) -> Self {
        Stack {
            layers,
            mtp: None,
            per_layer: None,
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn every_name_belongs_to_one_family() {
        let mut names: Vec<_> = crate::architectures().collect();
        let n = names.len();
        names.sort_unstable();
        names.dedup();
        assert_eq!(names.len(), n);
    }
}
