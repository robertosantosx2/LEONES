use std::fmt;

use kinetic_quant::TensorType;

/// Errors from the CUDA driver and from this crate's own checks.
#[derive(Clone, Debug)]
pub enum Error {
    /// The CUDA driver library could not be loaded.
    DriverNotFound(String),
    /// The driver lacks an entry point this crate needs.
    MissingSymbol(&'static str),
    /// A driver call failed.
    Cuda {
        call: &'static str,
        code: i32,
        /// The driver's name for `code`, such as `CUDA_ERROR_OUT_OF_MEMORY`.
        name: &'static str,
    },
    /// The crate was compiled without nvcc and carries no kernels.
    KernelsNotBuilt,
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
            Error::DriverNotFound(why) => write!(f, "CUDA driver not found: {why}"),
            Error::MissingSymbol(symbol) => {
                write!(f, "CUDA driver has no {symbol}; update the driver")
            }
            Error::Cuda { call, code, name } => write!(f, "{call} failed: {name} ({code})"),
            Error::KernelsNotBuilt => f.write_str(
                "CUDA kernels not built: nvcc was not found when kinetic-cuda was compiled",
            ),
            Error::Unsupported(ty) => write!(f, "no CUDA GEMV kernel for {ty}"),
            Error::Shape(msg) => f.write_str(msg),
        }
    }
}

impl std::error::Error for Error {}
