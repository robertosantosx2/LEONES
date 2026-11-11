use std::fmt;

#[derive(Debug)]
pub enum Error {
    Io(std::io::Error),
    /// The file does not start with the expected magic bytes.
    BadMagic,
    UnsupportedVersion(u32),
    /// The file breaks a rule of its format.
    Invalid(String),
    /// The GGUF source of a conversion could not be read.
    Gguf(kinetic_gguf::Error),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Io(e) => write!(f, "{e}"),
            Error::BadMagic => f.write_str("unrecognised file magic"),
            Error::UnsupportedVersion(v) => write!(f, "unsupported format version {v}"),
            Error::Invalid(msg) => f.write_str(msg),
            Error::Gguf(e) => write!(f, "GGUF source: {e}"),
        }
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Error::Io(e) => Some(e),
            Error::Gguf(e) => Some(e),
            _ => None,
        }
    }
}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::Io(e)
    }
}

impl From<kinetic_gguf::Error> for Error {
    fn from(e: kinetic_gguf::Error) -> Self {
        Error::Gguf(e)
    }
}

pub(crate) fn invalid(msg: impl Into<String>) -> Error {
    Error::Invalid(msg.into())
}
