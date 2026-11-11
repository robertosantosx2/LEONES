use std::fmt;

use ash::vk;
use kinetic_quant::TensorType;

/// Errors from the Vulkan loader and driver and from this crate's own checks.
#[derive(Clone, Debug)]
pub enum Error {
    /// The Vulkan loader library could not be opened.
    LoaderNotFound(String),
    /// A Vulkan call failed.
    Vulkan {
        call: &'static str,
        result: vk::Result,
    },
    /// The device lacks something the kernels need; the message says what.
    DeviceUnsupported(String),
    /// No GEMV kernel exists for this weight type.
    Unsupported(TensorType),
    /// Sizes that do not fit together.
    Shape(String),
}

/// `Result` with this crate's [`Error`].
pub type Result<T, E = Error> = std::result::Result<T, E>;

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::LoaderNotFound(why) => write!(f, "Vulkan loader not found: {why}"),
            Error::Vulkan { call, result } => write!(f, "{call} failed: {result}"),
            Error::DeviceUnsupported(why) => write!(f, "device not supported: {why}"),
            Error::Unsupported(ty) => write!(f, "no Vulkan GEMV kernel for {ty}"),
            Error::Shape(msg) => f.write_str(msg),
        }
    }
}

impl std::error::Error for Error {}

/// Maps a failed call's result into an [`Error`] naming the call.
pub(crate) trait Check<T> {
    fn check(self, call: &'static str) -> Result<T>;
}

impl<T> Check<T> for std::result::Result<T, vk::Result> {
    fn check(self, call: &'static str) -> Result<T> {
        self.map_err(|result| Error::Vulkan { call, result })
    }
}
