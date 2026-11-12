//! Reads the vocabulary of a byte-level BPE model from GGUF metadata.

use std::collections::HashMap;

use kinetic_gguf::{Gguf, Value};

use crate::bpe::{Bpe, Merge};
use crate::byte_level;
use crate::special::Specials;
use crate::Error;

/// `tokenizer.ggml.token_type` values.
pub(crate) mod token_type {
    pub const NORMAL: i64 = 1;
    pub const UNKNOWN: i64 = 2;
    pub const CONTROL: i64 = 3;
    pub const USER_DEFINED: i64 = 4;
    pub const BYTE: i64 = 6;
}

pub(crate) struct Vocab {
    /// What each token decodes to.
    pub pieces: Vec<Box<[u8]>>,
    /// Token ids by the bytes they stand for.
    pub ids: HashMap<Box<[u8]>, u32>,
    pub specials: Specials,
    pub bpe: Bpe,
}

impl Vocab {
    pub(crate) fn load(gguf: &Gguf) -> Result<Vocab, Error> {
        let (tokens, types) = tokens_and_types(gguf)?;

        let mut ids = HashMap::with_capacity(tokens.len());
        let mut pieces = Vec::with_capacity(tokens.len());
        let mut specials = Vec::new();
        for (id, (&text, &ty)) in (0u32..).zip(tokens.iter().zip(&types)) {
            // Later duplicates win, matching the reference's text-to-id map.
            if let Some(bytes) = byte_level::decode(text) {
                ids.insert(bytes.into_boxed_slice(), id);
            }
            let piece = if let Some(control) = special(text, ty) {
                specials.push((text.to_owned(), id, control));
                text.as_bytes().to_vec()
            } else if matches!(ty, token_type::NORMAL | token_type::BYTE) {
                byte_level::decode_lossy(text)
            } else {
                Vec::new()
            };
            pieces.push(piece.into_boxed_slice());
        }

        let byte_ids = std::array::from_fn(|b| ids.get(&[b as u8][..]).copied());

        let merges = strings(gguf, "tokenizer.ggml.merges")?;
        let rules = (0u32..).zip(merges).filter_map(|(rank, rule)| {
            let (left, right) = split_merge(rule)?;
            let left = byte_level::decode(left)?;
            let right = byte_level::decode(right)?;
            let left_id = *ids.get(left.as_slice())?;
            let right_id = *ids.get(right.as_slice())?;
            let id = *ids.get([left, right].concat().as_slice())?;
            Some((left_id, right_id, Merge { rank, id }))
        });
        let bpe = Bpe::new(byte_ids, rules);

        Ok(Vocab {
            pieces,
            ids,
            specials: Specials::new(specials),
            bpe,
        })
    }
}

/// Token texts the reference treats as control tokens whatever type the
/// file gives them: end-of-turn, end-of-generation and fill-in-the-middle
/// markers.
const CONTROL_TEXTS: &[&str] = &[
    "</s>",
    "<EOT>",
    "_<EOT>",
    "[EOT]",
    "[EOS]",
    "[PAD]",
    "[e~[",
    "<eos>",
    "<turn|>",
    "<|eot_id|>",
    "<|eot|>",
    "<|eom_id|>",
    "<|im_end|>",
    "<|end|>",
    "<|endoftext|>",
    "<|end_of_text|>",
    "<end_of_turn>",
    "<end_of_utterance>",
    "<|return|>",
    "<|call|>",
    "<|calls|>",
    "<|flush|>",
    "<|tool_response>",
    "<|ifm|im_end|>",
    "<\u{ff5c}end\u{2581}of\u{2581}sentence\u{ff5c}>",
    "<|fim_prefix|>",
    "<|fim_suffix|>",
    "<|fim_middle|>",
    "<|fim_pad|>",
    "<|fim_repo|>",
    "<|file_sep|>",
    "<|repo_name|>",
    "<fim-prefix>",
    "<fim-suffix>",
    "<fim-middle>",
    "<fim-pad>",
    "<fim-repo>",
    "<fim_prefix>",
    "<fim_suffix>",
    "<fim_middle>",
    "<fim_pad>",
    "<reponame>",
    "<PRE>",
    "<SUF>",
    "<MID>",
    "<PAD>",
    "<REPO>",
    "\u{2581}<PRE>",
    "\u{2581}<SUF>",
    "\u{2581}<MID>",
    "<|code_prefix|>",
    "<|code_suffix|>",
    "<|code_middle|>",
    "<|prefix|>",
    "<|suffix|>",
    "<|middle|>",
    "<\u{ff5c}fim\u{2581}begin\u{ff5c}>",
    "<\u{ff5c}fim\u{2581}hole\u{ff5c}>",
    "<\u{ff5c}fim\u{2581}end\u{ff5c}>",
    "<|plamo:fim_prefix|>",
    "<|plamo:fim_suffix|>",
    "<|plamo:fim_middle|>",
    "<|plamo:file_separator|>",
];

/// Whether a token is matched whole in the input text, and if so whether
/// only when special tokens are parsed.
pub(crate) fn special(text: &str, ty: i64) -> Option<bool> {
    let control_text = CONTROL_TEXTS.contains(&text);
    match ty {
        token_type::USER_DEFINED => Some(control_text),
        token_type::CONTROL | token_type::UNKNOWN => Some(true),
        _ => control_text.then_some(true),
    }
}

/// The token texts and their types, which default to normal.
pub(crate) fn tokens_and_types(gguf: &Gguf) -> Result<(Vec<&str>, Vec<i64>), Error> {
    let tokens = strings(gguf, "tokenizer.ggml.tokens")?;
    if u32::try_from(tokens.len()).is_err() {
        return Err(Error::Invalid("too many tokens".into()));
    }
    let types = match gguf.get("tokenizer.ggml.token_type") {
        Some(v) => {
            let items = array(v, "tokenizer.ggml.token_type")?;
            if items.len() != tokens.len() {
                return Err(Error::Invalid(
                    "tokenizer.ggml.token_type does not match the token count".into(),
                ));
            }
            items
                .iter()
                .map(|t| {
                    t.as_i64()
                        .ok_or_else(|| wrong_type("tokenizer.ggml.token_type"))
                })
                .collect::<Result<Vec<_>, _>>()?
        }
        None => vec![token_type::NORMAL; tokens.len()],
    };
    Ok((tokens, types))
}

/// Splits `"left right"` at the first space after the first character, so a
/// rule may merge a space-like character.
pub(crate) fn split_merge(rule: &str) -> Option<(&str, &str)> {
    let first = rule.chars().next()?.len_utf8();
    let sep = first + rule[first..].find(' ')?;
    Some((&rule[..sep], &rule[sep + 1..]))
}

pub(crate) fn array<'g>(value: &'g Value, key: &str) -> Result<&'g [Value], Error> {
    value.as_array().ok_or_else(|| wrong_type(key))
}

pub(crate) fn strings<'g>(gguf: &'g Gguf, key: &'static str) -> Result<Vec<&'g str>, Error> {
    let value = gguf.get(key).ok_or(Error::Missing(key))?;
    array(value, key)?
        .iter()
        .map(|v| v.as_str().ok_or_else(|| wrong_type(key)))
        .collect()
}

pub(crate) fn wrong_type(key: &str) -> Error {
    Error::Invalid(format!("{key} has the wrong type"))
}
