//! WordPiece tokenization (`tokenizer.ggml.model = "bert"`), as in BERT and
//! the encoders built on it. The text splits into words at whitespace and
//! around punctuation, is optionally lowercased and stripped of accents, and
//! each word becomes its longest vocabulary entries from left to right. The
//! GGUF vocabulary marks word starts with `▁` instead of marking
//! continuations with `##`.

use std::collections::HashMap;

use kinetic_gguf::Gguf;
use unicode_general_category::{get_general_category, GeneralCategory as G};
use unicode_normalization::char::decompose_canonical;

use crate::special::Specials;
use crate::vocab::{self, token_type};
use crate::Error;

const SPACE: &str = "\u{2581}";

pub(crate) struct Wpm {
    /// What each token decodes to.
    pub pieces: Vec<Box<[u8]>>,
    pub specials: Specials,
    /// Token ids by their text as stored, `▁` included.
    ids: HashMap<Box<[u8]>, u32>,
    /// Bytes in the longest token text.
    max_len: usize,
    unk: u32,
    lowercase: bool,
    strip_accents: bool,
}

impl Wpm {
    pub(crate) fn load(gguf: &Gguf) -> Result<Wpm, Error> {
        let (tokens, types) = vocab::tokens_and_types(gguf)?;
        let mut ids = HashMap::with_capacity(tokens.len());
        let mut pieces = Vec::with_capacity(tokens.len());
        let mut specials = Vec::new();
        for (id, (&text, &ty)) in (0u32..).zip(tokens.iter().zip(&types)) {
            // Later duplicates win, matching the reference's text-to-id map.
            ids.insert(Box::from(text.as_bytes()), id);
            let piece = if let Some(control) = vocab::special(text, ty) {
                specials.push((text.to_owned(), id, control));
                text.as_bytes().to_vec()
            } else if ty == token_type::NORMAL {
                text.replace(SPACE, " ").into_bytes()
            } else {
                Vec::new()
            };
            pieces.push(piece.into_boxed_slice());
        }

        let flag = |key: &str, default: bool| -> Result<bool, Error> {
            gguf.get(key).map_or(Ok(default), |v| {
                v.as_bool()
                    .ok_or_else(|| Error::Invalid(format!("{key} is not a bool")))
            })
        };
        let lowercase = flag("tokenizer.ggml.normalizer.lowercase", true)?;
        let strip_accents = flag("tokenizer.ggml.normalizer.strip_accents", lowercase)?;
        let unk = match gguf.get("tokenizer.ggml.unknown_token_id") {
            Some(v) => v
                .as_u64()
                .and_then(|id| u32::try_from(id).ok())
                .ok_or_else(|| {
                    Error::Invalid("tokenizer.ggml.unknown_token_id is invalid".into())
                })?,
            None => 100,
        };
        if unk as usize >= tokens.len() {
            return Err(Error::Invalid(
                "the unknown token is not in the vocabulary".into(),
            ));
        }

        Ok(Wpm {
            max_len: tokens.iter().map(|t| t.len()).max().unwrap_or(0),
            pieces,
            specials: Specials::new(specials),
            ids,
            unk,
            lowercase,
            strip_accents,
        })
    }

    /// Tokenizes one run of plain text.
    pub(crate) fn encode(&self, text: &str, out: &mut Vec<u32>) {
        let mut word = String::from(SPACE);
        let finish = |word: &mut String, out: &mut Vec<u32>| {
            if word.len() > SPACE.len() {
                self.encode_word(word.as_bytes(), out);
                word.truncate(SPACE.len());
            }
        };
        for c in text.chars() {
            let c = if self.strip_accents { base(c) } else { c };
            if c.is_whitespace() {
                finish(&mut word, out);
                continue;
            }
            let category = get_general_category(c);
            if c == '\0' || c == '\u{FFFD}' || is_control(category) {
                continue;
            }
            if self.strip_accents && is_mark(category) {
                continue;
            }
            let lower = if self.lowercase { lowercase(c) } else { c };
            if is_punctuation(category) || (c < '\u{7F}' && is_symbol(category)) || is_cjk(c) {
                finish(&mut word, out);
                word.push(lower);
                finish(&mut word, out);
            } else {
                word.push(lower);
            }
        }
        finish(&mut word, out);
    }

    /// Covers `word`, `▁` included, with the longest tokens from the left;
    /// a word that cannot be covered becomes the unknown token.
    fn encode_word(&self, word: &[u8], out: &mut Vec<u32>) {
        let start = out.len();
        let mut i = 0;
        while i < word.len() {
            let longest = (i + 1..=(i + self.max_len).min(word.len()))
                .rev()
                .find_map(|j| self.ids.get(&word[i..j]).map(|&id| (j, id)));
            match longest {
                Some((j, id)) => {
                    out.push(id);
                    i = j;
                }
                None => {
                    out.truncate(start);
                    break;
                }
            }
        }
        if out.len() == start {
            out.push(self.unk);
        }
    }
}

/// The first character of the canonical decomposition, which drops the
/// accents of a precomposed letter.
fn base(c: char) -> char {
    let mut first = None;
    decompose_canonical(c, |d| {
        first.get_or_insert(d);
    });
    first.unwrap_or(c)
}

/// The simple lowercase mapping, one character to one.
fn lowercase(c: char) -> char {
    c.to_lowercase().next().unwrap_or(c)
}

fn is_control(g: G) -> bool {
    matches!(g, G::Control | G::Format | G::PrivateUse | G::Surrogate)
}

fn is_mark(g: G) -> bool {
    matches!(g, G::NonspacingMark | G::SpacingMark | G::EnclosingMark)
}

fn is_punctuation(g: G) -> bool {
    matches!(
        g,
        G::ConnectorPunctuation
            | G::DashPunctuation
            | G::OpenPunctuation
            | G::ClosePunctuation
            | G::InitialPunctuation
            | G::FinalPunctuation
            | G::OtherPunctuation
    )
}

fn is_symbol(g: G) -> bool {
    matches!(
        g,
        G::MathSymbol | G::CurrencySymbol | G::ModifierSymbol | G::OtherSymbol
    )
}

/// CJK ideographs, each tokenized as a word of its own. The ranges follow
/// the reference, including its start of extension E.
fn is_cjk(c: char) -> bool {
    matches!(
        c as u32,
        0x4E00..=0x9FFF
            | 0x3400..=0x4DBF
            | 0x20000..=0x2A6DF
            | 0x2A700..=0x2B73F
            | 0x2B740..=0x2B81F
            | 0x2B920..=0x2CEAF
            | 0xF900..=0xFAFF
            | 0x2F800..=0x2FA1F
    )
}
