mod gguf;
mod safetensors;

pub use gguf::convert_gguf;
pub use safetensors::convert_safetensors;

/// Settings shared by the converters.
#[derive(Clone, Default)]
pub struct ConvertOptions {
    /// Ed25519 secret key to sign the result with; unsigned when `None`.
    pub secret_key: Option<[u8; 32]>,
}
