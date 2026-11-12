//! Token pieces arranged as a byte trie for computing masks.

use kinetic_tokenizer::Tokenizer;

/// A trie node, stored in depth-first order so a walk is a forward scan.
#[derive(Clone, Copy)]
pub(crate) struct Node {
    /// The index just past this node's subtree.
    pub skip: u32,
    /// The range of `Vocabulary::trie_tokens` whose pieces end here.
    pub tokens: (u32, u32),
    /// Depth of the parent; children of the root have 0.
    pub depth: u16,
    pub byte: u8,
}

/// The token pieces of a model, ready to be matched against grammars.
///
/// Build it once per model and share it between requests.
pub struct Vocabulary {
    pieces: Vec<Box<[u8]>>,
    stop: Vec<u32>,
    pub(crate) nodes: Vec<Node>,
    pub(crate) trie_tokens: Vec<u32>,
    pub(crate) max_len: usize,
}

impl Vocabulary {
    /// A vocabulary from the bytes each token id stands for. Tokens with an
    /// empty piece, or one longer than 65535 bytes, are never allowed; `stop` tokens end generation and are
    /// allowed once the grammar is complete.
    pub fn new(pieces: impl IntoIterator<Item = Vec<u8>>, stop: &[u32]) -> Vocabulary {
        let pieces: Vec<Box<[u8]>> = pieces.into_iter().map(Vec::into_boxed_slice).collect();
        let mut order: Vec<u32> = (0..pieces.len() as u32)
            .filter(|&id| {
                let len = pieces[id as usize].len();
                (1..=usize::from(u16::MAX)).contains(&len) && !stop.contains(&id)
            })
            .collect();
        order.sort_unstable_by(|&a, &b| pieces[a as usize].cmp(&pieces[b as usize]));

        let mut nodes: Vec<Node> = Vec::new();
        let mut trie_tokens = Vec::with_capacity(order.len());
        // The node index at each depth of the current path.
        let mut path: Vec<usize> = Vec::new();
        let mut prev: &[u8] = &[];
        for &id in &order {
            let piece = &pieces[id as usize][..];
            let common = piece.iter().zip(prev).take_while(|(a, b)| a == b).count();
            for open in path.drain(common..) {
                nodes[open].skip = nodes.len() as u32;
            }
            for (depth, &byte) in piece.iter().enumerate().skip(common) {
                path.push(nodes.len());
                let at = trie_tokens.len() as u32;
                nodes.push(Node {
                    skip: 0,
                    tokens: (at, at),
                    depth: depth as u16,
                    byte,
                });
            }
            trie_tokens.push(id);
            let last = *path.last().expect("pieces are not empty");
            nodes[last].tokens.1 = trie_tokens.len() as u32;
            prev = piece;
        }
        for open in path {
            nodes[open].skip = nodes.len() as u32;
        }
        let max_len = order
            .iter()
            .map(|&id| pieces[id as usize].len())
            .max()
            .unwrap_or(0);

        Vocabulary {
            pieces,
            stop: stop.to_vec(),
            nodes,
            trie_tokens,
            max_len,
        }
    }

    /// The vocabulary of `tokenizer`, with its end-of-sequence token as the
    /// stop token. Control tokens such as `<|im_start|>` are never allowed:
    /// their text is markup, not output.
    pub fn from_tokenizer(tokenizer: &Tokenizer) -> Vocabulary {
        let n = tokenizer.vocab_size() as u32;
        let pieces = (0..n).map(|id| {
            let piece = tokenizer.piece(id);
            if is_control(tokenizer, id, piece) {
                Vec::new()
            } else {
                piece.to_vec()
            }
        });
        let stop: Vec<u32> = tokenizer.eos().into_iter().collect();
        Vocabulary::new(pieces, &stop)
    }

    /// The same vocabulary ending generation at `stop` instead, such as a
    /// chat model's end-of-turn tokens.
    pub fn with_stop_tokens(mut self, stop: &[u32]) -> Vocabulary {
        self.stop = stop.to_vec();
        self
    }

    /// Number of token ids, allowed or not.
    pub fn len(&self) -> usize {
        self.pieces.len()
    }

    /// Whether there are no tokens at all.
    pub fn is_empty(&self) -> bool {
        self.pieces.is_empty()
    }

    /// The bytes of `token`; empty for tokens that are never allowed.
    pub fn piece(&self, token: u32) -> &[u8] {
        self.pieces.get(token as usize).map_or(&[], |p| p)
    }

    /// The tokens that end generation.
    pub fn stop_tokens(&self) -> &[u32] {
        &self.stop
    }
}

/// Whether `id` is a control token. Its piece is its text, as for
/// `<|im_end|>`, but encoding that text without special-token parsing gives
/// other tokens; user-defined tokens such as `<think>` encode to themselves.
fn is_control(tokenizer: &Tokenizer, id: u32, piece: &[u8]) -> bool {
    if Some(id) == tokenizer.bos() || Some(id) == tokenizer.eos() {
        return true;
    }
    let bracketed = piece.len() > 2 && piece[0] == b'<' && piece[piece.len() - 1] == b'>';
    let Some(text) = std::str::from_utf8(piece).ok().filter(|_| bracketed) else {
        return false;
    };
    let ids = tokenizer.encode(text, false);
    let ids = ids
        .strip_prefix(&[tokenizer.bos().unwrap_or(u32::MAX)])
        .unwrap_or(&ids);
    let ids = ids
        .strip_suffix(&[tokenizer.eos().unwrap_or(u32::MAX)])
        .unwrap_or(ids);
    ids != [id]
}

/// A set of token ids, one bit each.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TokenSet {
    words: Vec<u64>,
    len: usize,
}

impl TokenSet {
    /// An empty set for token ids below `len`.
    pub fn new(len: usize) -> TokenSet {
        TokenSet {
            words: vec![0; len.div_ceil(64)],
            len,
        }
    }

    /// Whether `token` is in the set.
    #[inline]
    pub fn contains(&self, token: u32) -> bool {
        self.words
            .get(token as usize >> 6)
            .is_some_and(|w| w >> (token & 63) & 1 != 0)
    }

    /// Number of tokens in the set.
    pub fn count(&self) -> usize {
        self.words.iter().map(|w| w.count_ones() as usize).sum()
    }

    /// The tokens in the set, in increasing order.
    pub fn iter(&self) -> impl Iterator<Item = u32> + '_ {
        (0..self.len as u32).filter(|&t| self.contains(t))
    }

    pub(crate) fn words_mut(&mut self, len: usize) -> &mut [u64] {
        if self.len != len {
            *self = TokenSet::new(len);
        }
        &mut self.words
    }

    #[inline]
    pub(crate) fn insert(words: &mut [u64], token: u32) {
        words[token as usize >> 6] |= 1 << (token & 63);
    }
}
