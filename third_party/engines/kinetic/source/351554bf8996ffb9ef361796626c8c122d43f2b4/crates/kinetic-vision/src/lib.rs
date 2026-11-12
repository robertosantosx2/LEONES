//! Image input for language models.
//!
//! [`VisionEncoder::load`] reads a vision projector file (the `mmproj` GGUF
//! that ships beside a multimodal model), [`VisionEncoder::prepare`] resizes
//! and normalizes a picture the way the model was trained, and
//! [`VisionEncoder::encode`] turns it into rows of language-model embeddings
//! that take the place of the image's placeholder tokens in a prompt.
//!
//! Each projector type lives in its own module and is listed in
//! `PROJECTORS` under its `clip.projector_type`.

#[cfg(feature = "cuda")]
mod device;
#[cfg(target_arch = "x86_64")]
mod flash;
mod gemma4v;
mod loader;
mod ops;
mod preprocess;
mod qwen3vl;

use std::fmt;
#[cfg(feature = "cuda")]
use std::sync::Mutex;

use kinetic_gguf::TensorSource;

pub use image::RgbImage;
pub use preprocess::{decode, Pixels};

use loader::Loader;

/// An encoded image: one row of the language model's embedding width per
/// image token, in row-major order over a `width x height` grid.
pub struct Embeddings {
    pub rows: Vec<f32>,
    pub width: usize,
    pub height: usize,
}

impl Embeddings {
    /// Number of image tokens.
    pub fn len(&self) -> usize {
        self.width * self.height
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

#[derive(Debug)]
pub struct Error(pub String);

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for Error {}

/// One projector type: the vision tower and projection of a model family.
trait Projector<'a>: Send + Sync {
    /// Width of the embeddings it produces.
    fn n_embd_out(&self) -> usize;

    /// Resizes and normalizes `img` to at most `max_tokens` image tokens.
    fn prepare(&self, img: &RgbImage, max_tokens: usize) -> Pixels;

    /// Encodes pixels made by [`Projector::prepare`].
    fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error>;

    /// The encoder uploaded to the first CUDA device.
    #[cfg(feature = "cuda")]
    fn cuda(&self) -> Result<Box<dyn CudaProjector + 'a>, Error> {
        Err(Error("this projector runs on the CPU only".into()))
    }
}

/// A projector on a CUDA device.
#[cfg(feature = "cuda")]
trait CudaProjector {
    fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error>;
}

/// A projector on the device, used by one thread at a time.
#[cfg(feature = "cuda")]
struct OnDevice<'a>(Box<dyn CudaProjector + 'a>);

// SAFETY: device resources are not `Send` only because they share their
// context through `Rc`. Every such `Rc` lives inside this box, which is only
// reached through the encoder's mutex, so no two threads touch them or their
// counts at once; each driver call makes the context current on the calling
// thread first.
#[cfg(feature = "cuda")]
unsafe impl Send for OnDevice<'_> {}

type Load = for<'a> fn(&Loader<'a>) -> Result<Box<dyn Projector<'a> + 'a>, Error>;

/// Every supported `clip.projector_type` and its loader.
const PROJECTORS: &[(&str, Load)] = &[
    ("qwen3vl_merger", qwen3vl::load),
    ("gemma4v", gemma4v::load),
];

/// Largest image the processor accepts by default, in image tokens.
const MAX_TOKENS: usize = 4096;

/// A vision encoder with weights borrowed from its projector file.
pub struct VisionEncoder<'a> {
    projector: Box<dyn Projector<'a> + 'a>,
    #[cfg(feature = "cuda")]
    device: Option<Mutex<OnDevice<'a>>>,
    /// Images are scaled down to at most this many tokens.
    pub max_tokens: usize,
}

impl<'a> VisionEncoder<'a> {
    /// Reads the encoder from a vision projector file.
    pub fn load(file: &'a dyn TensorSource) -> Result<Self, Error> {
        let l = Loader(file);
        // files with an audio tower too keep the vision type under clip.vision
        let ty = l
            .value("clip.vision.projector_type")
            .or_else(|_| l.value("clip.projector_type"))?
            .as_str()
            .unwrap_or_default();
        let (_, load) = PROJECTORS
            .iter()
            .find(|(name, _)| *name == ty)
            .ok_or_else(|| Error(format!("vision projector {ty:?} is not supported yet")))?;
        Ok(VisionEncoder {
            projector: load(&l)?,
            #[cfg(feature = "cuda")]
            device: None,
            max_tokens: MAX_TOKENS,
        })
    }

    /// Width of the embeddings [`VisionEncoder::encode`] produces, which is
    /// the language model's embedding width.
    pub fn n_embd_out(&self) -> usize {
        self.projector.n_embd_out()
    }

    /// Resizes `img` to the nearest size the encoder takes, within
    /// [`VisionEncoder::max_tokens`] and the model's own limits, and
    /// normalizes it.
    pub fn prepare(&self, img: &RgbImage) -> Pixels {
        self.projector.prepare(img, self.max_tokens)
    }

    /// Encodes pixels from [`VisionEncoder::prepare`] into one embedding per
    /// image token.
    pub fn encode(&self, pixels: &Pixels) -> Result<Embeddings, Error> {
        #[cfg(feature = "cuda")]
        if let Some(device) = &self.device {
            let device = device.lock().unwrap_or_else(|e| e.into_inner());
            return device.0.encode(pixels);
        }
        self.projector.encode(pixels)
    }

    /// Moves encoding to the first CUDA device; results agree with the CPU
    /// to float rounding. Fails, leaving encoding on the CPU, for projectors
    /// without a device version or when the device has no room.
    #[cfg(feature = "cuda")]
    pub fn use_cuda(&mut self) -> Result<(), Error> {
        self.device = Some(Mutex::new(OnDevice(self.projector.cuda()?)));
        Ok(())
    }
}
