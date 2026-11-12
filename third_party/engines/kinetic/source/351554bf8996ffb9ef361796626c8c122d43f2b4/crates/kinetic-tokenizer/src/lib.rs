//! Tokenizers for GGUF models: byte-level BPE (`tokenizer.ggml.model =
//! "gpt2"`), SentencePiece (`"llama"`, as in Llama 2, Mistral and Gemma;
//! `"gemma4"` with merge rules) and
//! WordPiece (`"bert"`, as in BERT-style embedding models).
//!
//! Produces the same token ids as llama.cpp for the supported BPE
//! pre-tokenizers: `qwen35`, `qwen2`, `llama-bpe`, `lfm2`, `falcon-h1`,
//! `dbrx`, `smollm`, `refact`, `exaone4`, `hunyuan-dense` and `gpt-2`.
//!
//! ```no_run
//! # fn main() -> Result<(), Box<dyn std::error::Error>> {
//! use kinetic_gguf::GgufFile;
//! use kinetic_tokenizer::Tokenizer;
//!
//! let file = GgufFile::open("model.gguf")?;
//! let tokenizer = Tokenizer::from_gguf(file.header())?;
//! let ids = tokenizer.encode("<|im_start|>user\nCześć!", true);
//! assert_eq!(tokenizer.decode(&ids), "<|im_start|>user\nCześć!");
//! # Ok(())
//! # }
//! ```

mod bpe;
mod byte_level;
mod pretokenize;
mod special;
mod spm;
mod stream;
mod unicode;
mod vocab;
mod wpm;

use std::fmt;

use kinetic_gguf::Gguf;

use bpe::Scratch;
use pretokenize::Pattern;
use special::{Segment, Specials};
use spm::Spm;
pub use stream::StreamDecoder;
use vocab::Vocab;
use wpm::Wpm;

/// Why a tokenizer could not be built from a model file.
#[derive(Debug)]
pub enum Error {
    /// A required metadata key is absent.
    Missing(&'static str),
    /// The model uses a tokenizer or pre-tokenizer this crate does not have.
    Unsupported(String),
    /// The metadata is present but malformed.
    Invalid(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Missing(key) => write!(f, "missing {key}"),
            Error::Unsupported(what) => write!(f, "unsupported {what}"),
            Error::Invalid(msg) => f.write_str(msg),
        }
    }
}

impl std::error::Error for Error {}

/// A tokenizer loaded from GGUF metadata.
pub struct Tokenizer {
    model: Model,
    bos: Option<u32>,
    eos: Option<u32>,
    add_bos: bool,
    add_eos: bool,
    /// Closes every encoding after EOS, as the separator of WordPiece models.
    sep: Option<u32>,
}

enum Model {
    Bpe {
        vocab: Vocab,
        pattern: Pattern,
        /// A piece that is itself a token is emitted whole, skipping the
        /// merges.
        ignore_merges: bool,
    },
    Spm(Spm),
    Wpm(Wpm),
}

impl Tokenizer {
    /// Builds the tokenizer described by the `tokenizer.ggml.*` keys.
    pub fn from_gguf(gguf: &Gguf) -> Result<Tokenizer, Error> {
        let (model, default_add_bos, default_ids) = match string(gguf, "tokenizer.ggml.model")? {
            "gpt2" => {
                let pre = string(gguf, "tokenizer.ggml.pre")?;
                let (pattern, ignore_merges, default_add_bos) = match pre {
                    "qwen35" => (pretokenize::QWEN35, false, false),
                    "qwen2" => (pretokenize::QWEN2, false, false),
                    "llama3" | "llama-v3" | "llama-bpe" | "lfm2" | "falcon-h1" => {
                        (pretokenize::LLAMA3, true, true)
                    }
                    "dbrx" => (pretokenize::LLAMA3, false, false),
                    "smollm" | "refact" => (pretokenize::SMOLLM, false, false),
                    "gpt-2" | "exaone4" => (pretokenize::GPT2, false, false),
                    "hunyuan-dense" => (pretokenize::HUNYUAN, false, false),
                    _ => return Err(Error::Unsupported(format!("pre-tokenizer {pre:?}"))),
                };
                let model = Model::Bpe {
                    vocab: Vocab::load(gguf)?,
                    pattern,
                    ignore_merges,
                };
                (model, default_add_bos, (None, None))
            }
            // Files written before the ids were stored use these.
            "llama" => (Model::Spm(Spm::load(gguf)?), true, (Some(1), Some(2))),
            "gemma4" => (Model::Spm(Spm::load_with_merges(gguf)?), true, (None, None)),
            "bert" => (Model::Wpm(Wpm::load(gguf)?), true, (Some(101), None)),
            other => return Err(Error::Unsupported(format!("tokenizer model {other:?}"))),
        };

        let n_tokens = model.pieces().len();
        let valid = |id: u32| (id as usize) < n_tokens;
        let token_id = |key: &'static str| -> Result<Option<u32>, Error> {
            gguf.get(key)
                .map(|v| {
                    v.as_u64()
                        .and_then(|id| u32::try_from(id).ok())
                        .filter(|&id| valid(id))
                        .ok_or_else(|| Error::Invalid(format!("{key} is not a token id")))
                })
                .transpose()
        };
        let flag = |key: &'static str, default: bool| -> Result<bool, Error> {
            gguf.get(key).map_or(Ok(default), |v| {
                v.as_bool()
                    .ok_or_else(|| Error::Invalid(format!("{key} is not a bool")))
            })
        };
        let bos =
            token_id("tokenizer.ggml.bos_token_id")?.or(default_ids.0.filter(|&id| valid(id)));
        let eos =
            token_id("tokenizer.ggml.eos_token_id")?.or(default_ids.1.filter(|&id| valid(id)));
        let mut add_bos = flag("tokenizer.ggml.add_bos_token", default_add_bos)?;
        let add_eos = flag("tokenizer.ggml.add_eos_token", false)?;
        let mut sep = None;
        // The reference wraps WordPiece input in CLS and SEP whatever the
        // file's flags say.
        if let Model::Wpm(_) = model {
            add_bos = true;
            sep = Some(
                token_id("tokenizer.ggml.seperator_token_id")?
                    .or(Some(102).filter(|&id| valid(id)))
                    .ok_or(Error::Missing("tokenizer.ggml.seperator_token_id"))?,
            );
        }
        if add_bos && bos.is_none() {
            return Err(Error::Missing("tokenizer.ggml.bos_token_id"));
        }
        if add_eos && eos.is_none() {
            return Err(Error::Missing("tokenizer.ggml.eos_token_id"));
        }

        Ok(Tokenizer {
            model,
            bos,
            eos,
            add_bos,
            add_eos,
            sep,
        })
    }

    /// Tokenizes `text`, adding BOS and EOS where the model asks for them.
    ///
    /// User-defined tokens written in the text always become their ids. With
    /// `parse_special`, control tokens such as `<|im_start|>` do as well;
    /// without it they are tokenized as plain text.
    pub fn encode(&self, text: &str, parse_special: bool) -> Vec<u32> {
        let mut out = Vec::with_capacity(text.len() / 3 + 2);
        out.extend(self.bos.filter(|_| self.add_bos));
        let mut scratch = Scratch::default();
        let mut after_special = true;
        for segment in self.model.specials().split(text, parse_special) {
            match segment {
                Segment::Token(id) => {
                    out.push(id);
                    after_special = true;
                }
                Segment::Text(text) => {
                    match &self.model {
                        Model::Bpe {
                            vocab,
                            pattern,
                            ignore_merges,
                        } => encode_bpe(
                            vocab,
                            *pattern,
                            *ignore_merges,
                            text,
                            &mut scratch,
                            &mut out,
                        ),
                        Model::Spm(spm) => {
                            spm.encode(text, spm.add_space_prefix && after_special, &mut out)
                        }
                        Model::Wpm(wpm) => wpm.encode(text, &mut out),
                    }
                    after_special = false;
                }
            }
        }
        out.extend(self.eos.filter(|_| self.add_eos));
        out.extend(self.sep);
        out
    }

    /// Joins the text of `ids`, special tokens included. Ids outside the
    /// vocabulary, which padded output layers can produce, decode to nothing.
    pub fn decode(&self, ids: &[u32]) -> String {
        let bytes: Vec<u8> = ids.iter().flat_map(|&id| self.piece(id)).copied().collect();
        String::from_utf8_lossy(&bytes).into_owned()
    }

    /// A decoder for generated tokens that never splits a character.
    pub fn stream(&self) -> StreamDecoder<'_> {
        StreamDecoder::new(self)
    }

    /// The bytes token `id` stands for; empty for unknown ids.
    pub fn piece(&self, id: u32) -> &[u8] {
        self.model
            .pieces()
            .get(id as usize)
            .map_or(&[], |p| p.as_ref())
    }

    /// Number of tokens in the vocabulary.
    pub fn vocab_size(&self) -> usize {
        self.model.pieces().len()
    }

    /// The beginning-of-sequence token, if the model has one.
    pub fn bos(&self) -> Option<u32> {
        self.bos
    }

    /// The end-of-sequence token, if the model has one.
    pub fn eos(&self) -> Option<u32> {
        self.eos
    }
}

impl Model {
    fn pieces(&self) -> &[Box<[u8]>] {
        match self {
            Model::Bpe { vocab, .. } => &vocab.pieces,
            Model::Spm(spm) => &spm.pieces,
            Model::Wpm(wpm) => &wpm.pieces,
        }
    }

    fn specials(&self) -> &Specials {
        match self {
            Model::Bpe { vocab, .. } => &vocab.specials,
            Model::Spm(spm) => &spm.specials,
            Model::Wpm(wpm) => &wpm.specials,
        }
    }
}

fn encode_bpe(
    vocab: &Vocab,
    pattern: Pattern,
    ignore_merges: bool,
    text: &str,
    scratch: &mut Scratch,
    out: &mut Vec<u32>,
) {
    for piece in pattern.split(text) {
        let bytes = piece.as_bytes();
        if ignore_merges {
            if let Some(&id) = vocab.ids.get(bytes) {
                out.push(id);
                continue;
            }
        }
        vocab.bpe.encode(bytes, scratch, out);
    }
}

fn string<'g>(gguf: &'g Gguf, key: &'static str) -> Result<&'g str, Error> {
    gguf.get(key)
        .ok_or(Error::Missing(key))?
        .as_str()
        .ok_or_else(|| Error::Invalid(format!("{key} is not a string")))
}

#[cfg(test)]
mod tests;
