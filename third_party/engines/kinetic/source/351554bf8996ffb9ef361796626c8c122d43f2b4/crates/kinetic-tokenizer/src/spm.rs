//! SentencePiece-style tokenization (`tokenizer.ggml.model = "llama"`):
//! spaces become `▁`, and adjacent symbols merge into the vocabulary entry
//! with the highest score until no pair forms one. Characters left without
//! a token fall back to their byte tokens. Files that store merge rules
//! (`"gemma4"`) merge by rule rank instead, as byte-pair encoding does.

use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

use kinetic_gguf::Gguf;

use crate::bpe::{Bpe, Merge, Scratch};
use crate::special::Specials;
use crate::vocab::{self, token_type};
use crate::Error;

const SPACE: &str = "\u{2581}";

pub(crate) struct Spm {
    /// What each token decodes to.
    pub pieces: Vec<Box<[u8]>>,
    pub specials: Specials,
    /// Token ids by their text as stored, `▁` included.
    ids: HashMap<Box<str>, u32>,
    scores: Vec<f32>,
    byte_ids: [u32; 256],
    /// Every run of text after the start or a special token gets a space in
    /// front.
    pub add_space_prefix: bool,
    /// Ranked merge rules, which replace the scores when present.
    merges: Option<Box<Bpe>>,
}

struct Symbol {
    start: usize,
    len: usize,
    prev: usize,
    next: usize,
}

const NONE: usize = usize::MAX;

/// A pair of adjacent symbols whose joined text is a token. The best score
/// pops first, and among equal scores the leftmost pair.
struct Bigram {
    score: f32,
    left: usize,
    right: usize,
    len: usize,
}

impl Ord for Bigram {
    fn cmp(&self, other: &Self) -> Ordering {
        self.score
            .total_cmp(&other.score)
            .then(other.left.cmp(&self.left))
    }
}

impl PartialOrd for Bigram {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl PartialEq for Bigram {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for Bigram {}

impl Spm {
    pub(crate) fn load(gguf: &Gguf) -> Result<Spm, Error> {
        let (tokens, types) = vocab::tokens_and_types(gguf)?;
        let scores = match gguf.get("tokenizer.ggml.scores") {
            Some(v) => {
                let items = vocab::array(v, "tokenizer.ggml.scores")?;
                if items.len() != tokens.len() {
                    return Err(Error::Invalid(
                        "tokenizer.ggml.scores does not match the token count".into(),
                    ));
                }
                items
                    .iter()
                    .map(|s| {
                        s.as_f32()
                            .ok_or_else(|| vocab::wrong_type("tokenizer.ggml.scores"))
                    })
                    .collect::<Result<Vec<_>, _>>()?
            }
            None => vec![0.0; tokens.len()],
        };

        let mut ids = HashMap::with_capacity(tokens.len());
        let mut pieces = Vec::with_capacity(tokens.len());
        let mut specials = Vec::new();
        for (id, (&text, &ty)) in (0u32..).zip(tokens.iter().zip(&types)) {
            // Later duplicates win, matching the reference's text-to-id map.
            ids.insert(Box::from(text), id);
            let piece = if let Some(control) = vocab::special(text, ty) {
                specials.push((text.to_owned(), id, control));
                text.as_bytes().to_vec()
            } else {
                match ty {
                    token_type::NORMAL => text.replace(SPACE, " ").into_bytes(),
                    token_type::BYTE => byte_token(text).map_or_else(Vec::new, |b| vec![b]),
                    _ => Vec::new(),
                }
            };
            pieces.push(piece.into_boxed_slice());
        }

        let unk = gguf
            .get("tokenizer.ggml.unknown_token_id")
            .and_then(|v| v.as_u64())
            .and_then(|id| u32::try_from(id).ok())
            .filter(|&id| (id as usize) < tokens.len())
            .unwrap_or(0);
        let mut byte_ids = [unk; 256];
        for (b, slot) in (0..=u8::MAX).zip(&mut byte_ids) {
            let found = ids.get(format!("<0x{b:02X}>").as_str()).or_else(|| {
                b.is_ascii()
                    .then(|| char::from(b).to_string())
                    .and_then(|c| ids.get(c.as_str()))
            });
            if let Some(&id) = found {
                *slot = id;
            }
        }

        let add_space_prefix = match gguf.get("tokenizer.ggml.add_space_prefix") {
            Some(v) => v.as_bool().ok_or_else(|| {
                Error::Invalid("tokenizer.ggml.add_space_prefix is not a bool".into())
            })?,
            None => true,
        };

        Ok(Spm {
            pieces,
            specials: Specials::new(specials),
            ids,
            scores,
            byte_ids,
            add_space_prefix,
            merges: None,
        })
    }

    /// [`Spm::load`] for a vocabulary that merges by `tokenizer.ggml.merges`.
    pub(crate) fn load_with_merges(gguf: &Gguf) -> Result<Spm, Error> {
        let mut spm = Spm::load(gguf)?;
        let rules = vocab::strings(gguf, "tokenizer.ggml.merges")?;
        let rules = (0u32..).zip(rules).filter_map(|(rank, rule)| {
            let (left, right) = vocab::split_merge(rule)?;
            let id = *spm.ids.get([left, right].concat().as_str())?;
            Some((
                *spm.ids.get(left)?,
                *spm.ids.get(right)?,
                Merge { rank, id },
            ))
        });
        spm.merges = Some(Box::new(Bpe::new([None; 256], rules)));
        Ok(spm)
    }

    /// Tokenizes one run of plain text, which must not be empty.
    pub(crate) fn encode(&self, text: &str, space_prefix: bool, out: &mut Vec<u32>) {
        let mut escaped = String::with_capacity(text.len() + SPACE.len());
        if space_prefix {
            escaped.push_str(SPACE);
        }
        escaped.push_str(&text.replace(' ', SPACE));
        let text = escaped.as_str();
        if let Some(bpe) = &self.merges {
            return self.encode_ranked(bpe, text, out);
        }

        let count = text.chars().count();
        let mut symbols: Vec<Symbol> = text
            .char_indices()
            .enumerate()
            .map(|(i, (start, c))| Symbol {
                start,
                len: c.len_utf8(),
                prev: if i == 0 { NONE } else { i - 1 },
                next: if i + 1 == count { NONE } else { i + 1 },
            })
            .collect();

        let mut queue = BinaryHeap::new();
        for left in 1..symbols.len() {
            self.push_pair(text, &symbols, &mut queue, left - 1, left);
        }
        while let Some(b) = queue.pop() {
            let (l, r) = (&symbols[b.left], &symbols[b.right]);
            // Either side has merged since; the pair is stale.
            if l.len == 0 || r.len == 0 || l.len + r.len != b.len {
                continue;
            }
            let (prev, next) = (l.prev, r.next);
            symbols[b.left].len = b.len;
            symbols[b.left].next = next;
            symbols[b.right].len = 0;
            if next != NONE {
                symbols[next].prev = b.left;
            }
            if prev != NONE {
                self.push_pair(text, &symbols, &mut queue, prev, b.left);
            }
            if next != NONE {
                self.push_pair(text, &symbols, &mut queue, b.left, next);
            }
        }

        let mut i = 0;
        while i != NONE {
            let s = &symbols[i];
            let piece = &text[s.start..s.start + s.len];
            match self.ids.get(piece) {
                Some(&id) => out.push(id),
                None => out.extend(piece.bytes().map(|b| self.byte_ids[usize::from(b)])),
            }
            i = s.next;
        }
    }

    /// Starts from one symbol per character, or its bytes when the
    /// character has no token, and merges by rule rank.
    fn encode_ranked(&self, bpe: &Bpe, text: &str, out: &mut Vec<u32>) {
        let mut start = Vec::with_capacity(text.len());
        let mut buf = [0; 4];
        for c in text.chars() {
            let c = c.encode_utf8(&mut buf);
            match self.ids.get(&*c) {
                Some(&id) => start.push(id),
                None => start.extend(c.bytes().map(|b| self.byte_ids[usize::from(b)])),
            }
        }
        bpe.merge(start.into_iter(), &mut Scratch::default(), out);
    }

    fn push_pair(
        &self,
        text: &str,
        symbols: &[Symbol],
        queue: &mut BinaryHeap<Bigram>,
        left: usize,
        right: usize,
    ) {
        let start = symbols[left].start;
        let len = symbols[left].len + symbols[right].len;
        if let Some(&id) = self.ids.get(&text[start..start + len]) {
            queue.push(Bigram {
                score: self.scores[id as usize],
                left,
                right,
                len,
            });
        }
    }
}

/// The byte a `<0xXX>` token stands for.
fn byte_token(text: &str) -> Option<u8> {
    let hex = text.strip_prefix("<0x")?.strip_suffix('>')?;
    (hex.len() == 2).then(|| u8::from_str_radix(hex, 16).ok())?
}
