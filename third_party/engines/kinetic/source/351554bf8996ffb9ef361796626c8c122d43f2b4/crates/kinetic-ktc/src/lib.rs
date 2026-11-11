//! The `.ktc` model format.
//!
//! A `.ktc` file holds weights, tokenizer, chat template, an optional
//! execution profile and a manifest that hashes every section, optionally
//! signed with Ed25519. `FORMAT.md` is the specification.
//!
//! - [`KtcFile::open`] maps a file, validates its header against the file
//!   and exposes tensors without copying, also as a GGUF view
//!   ([`KtcFile::gguf`]) so GGUF loaders read it unchanged.
//! - [`verify`] recomputes every hash and checks the signature.
//! - [`convert_gguf`] and [`convert_safetensors`] build `.ktc` files;
//!   [`write`] is the general writer.

mod convert;
mod error;
mod file;
mod manifest;
mod metadata;
mod sign;
mod verify;
mod writer;

pub use convert::{convert_gguf, convert_safetensors, ConvertOptions};
pub use error::Error;
pub use file::{Ktc, KtcFile, ALIGNMENT, TENSORS, VERSION};
pub use manifest::{ExecutionProfile, Manifest, Section, Tensor, Tokenizer};
pub use metadata::Metadata;
pub use sign::{public_key, sign, sign_file, verify_signature};
pub use verify::{verify, Report, SectionCheck, SignatureStatus};
pub use writer::{write, Contents, TensorData};
