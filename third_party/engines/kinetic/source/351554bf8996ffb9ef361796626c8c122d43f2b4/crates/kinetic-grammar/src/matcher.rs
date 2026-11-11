//! Follows generation token by token and computes the allowed next tokens.

use std::fmt;

use crate::dfa::{Dfa, DEAD, OPEN};
use crate::hash::FastMap;
use crate::vocab::{TokenSet, Vocabulary};
use crate::Grammar;

/// States kept before the automaton starts over from the current one; each
/// costs about a kilobyte.
const MAX_STATES: usize = 1 << 15;
/// Masks kept per cache.
const MAX_MASKS: usize = 128;

/// The grammar state of one generation.
pub struct Matcher<'a> {
    vocab: &'a Vocabulary,
    dfa: Dfa<'a>,
    state: u32,
    stopped: bool,
    /// Finished masks by state.
    masks: FastMap<u32, Box<[u64]>>,
    /// Masks of cut states, shared by every state with the same top frames.
    partials: FastMap<u32, Partial>,
    walk: Walk,
}

/// The mask of a cut state and the subtrees it could not decide.
struct Partial {
    mask: Box<[u64]>,
    open: Open,
}

/// Trie nodes to walk again from the full state, each with the range of
/// `prefixes` that spells the path to its parent.
#[derive(Default)]
struct Open {
    nodes: Vec<(u32, u32, u32)>,
    prefixes: Vec<u8>,
}

/// Scratch for trie walks: the state and byte at each depth.
struct Walk {
    states: Vec<u32>,
    bytes: Vec<u8>,
}

/// A token the grammar does not allow at this point.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rejected(pub u32);

impl fmt::Display for Rejected {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "token {} is not allowed by the grammar here", self.0)
    }
}

impl std::error::Error for Rejected {}

impl<'a> Matcher<'a> {
    /// A matcher at the start of `grammar`.
    pub fn new(grammar: &'a Grammar, vocab: &'a Vocabulary) -> Matcher<'a> {
        let mut dfa = Dfa::new(&grammar.program);
        let state = dfa.start();
        Matcher {
            vocab,
            dfa,
            state,
            stopped: false,
            masks: FastMap::default(),
            partials: FastMap::default(),
            walk: Walk {
                states: vec![DEAD; vocab.max_len + 1],
                bytes: vec![0; vocab.max_len + 1],
            },
        }
    }

    /// Fills `out` with the tokens that may come next. Stop tokens are in it
    /// once the grammar is complete; an empty set means generation is over.
    pub fn allowed(&mut self, out: &mut TokenSet) {
        let words = out.words_mut(self.vocab.len());
        if self.stopped {
            words.fill(0);
            return;
        }
        if let Some(mask) = self.masks.get(&self.state) {
            words.copy_from_slice(mask);
        } else {
            self.compute(words);
            if self.masks.len() >= MAX_MASKS {
                self.masks.clear();
            }
            self.masks.insert(self.state, words.into());
        }
        if self.dfa.is_accepting(self.state) {
            for &stop in self.vocab.stop_tokens() {
                TokenSet::insert(words, stop);
            }
        }
    }

    /// Advances past `token`; a token that is not allowed changes nothing.
    pub fn accept(&mut self, token: u32) -> Result<(), Rejected> {
        if self.stopped {
            return Err(Rejected(token));
        }
        if self.vocab.stop_tokens().contains(&token) {
            if !self.dfa.is_accepting(self.state) {
                return Err(Rejected(token));
            }
            self.stopped = true;
            return Ok(());
        }
        let piece = self.vocab.piece(token);
        if piece.is_empty() {
            return Err(Rejected(token));
        }
        let mut state = self.state;
        for &b in piece {
            state = self.dfa.step(state, b);
            if state == DEAD {
                return Err(Rejected(token));
            }
        }
        self.state = state;
        if self.dfa.len() > MAX_STATES {
            self.state = self.dfa.reset(state);
            self.masks.clear();
            self.partials.clear();
        }
        Ok(())
    }

    /// Whether the tokens accepted so far form a complete match.
    pub fn is_complete(&self) -> bool {
        self.dfa.is_accepting(self.state)
    }

    /// The mask of the current state: that of its cut state, plus what the
    /// full state allows in the subtrees the cut could not decide.
    fn compute(&mut self, words: &mut [u64]) {
        let Matcher {
            vocab,
            dfa,
            state,
            partials,
            walk,
            ..
        } = self;
        let cut = dfa.cut(*state);
        if !partials.contains_key(&cut) {
            let mut partial = Partial {
                mask: vec![0; words.len()].into(),
                open: Open::default(),
            };
            let whole = 0..vocab.nodes.len();
            walk.run(
                dfa,
                vocab,
                whole,
                cut,
                &mut partial.mask,
                Some(&mut partial.open),
            );
            if partials.len() >= MAX_MASKS {
                partials.clear();
            }
            partials.insert(cut, partial);
        }
        let partial = &partials[&cut];
        words.copy_from_slice(&partial.mask);
        for &(node, from, to) in &partial.open.nodes {
            let parent = partial.open.prefixes[from as usize..to as usize]
                .iter()
                .try_fold(*state, |s, &b| Some(dfa.step(s, b)).filter(|&s| s != DEAD));
            if let Some(parent) = parent {
                let subtree = node as usize..vocab.nodes[node as usize].skip as usize;
                walk.run(dfa, vocab, subtree, parent, words, None);
            }
        }
    }
}

impl Walk {
    /// Marks the tokens in `nodes`, a run of sibling subtrees, that `state`
    /// at their parent can take. Walking a cut state records in `open` the
    /// subtrees it cannot decide.
    fn run(
        &mut self,
        dfa: &mut Dfa<'_>,
        vocab: &Vocabulary,
        nodes: std::ops::Range<usize>,
        state: u32,
        words: &mut [u64],
        mut open: Option<&mut Open>,
    ) {
        let Some(first) = vocab.nodes.get(nodes.start) else {
            return;
        };
        self.states[usize::from(first.depth)] = state;
        let mut i = nodes.start;
        while i < nodes.end {
            let node = vocab.nodes[i];
            let depth = usize::from(node.depth);
            let next = dfa.step(self.states[depth], node.byte);
            if next >= OPEN {
                if next == OPEN {
                    let open = open.as_deref_mut().expect("only cut states step to OPEN");
                    let from = open.prefixes.len() as u32;
                    open.prefixes.extend_from_slice(&self.bytes[..depth]);
                    open.nodes
                        .push((i as u32, from, open.prefixes.len() as u32));
                }
                i = node.skip as usize;
                continue;
            }
            self.states[depth + 1] = next;
            self.bytes[depth] = node.byte;
            for &token in &vocab.trie_tokens[node.tokens.0 as usize..node.tokens.1 as usize] {
                TokenSet::insert(words, token);
            }
            i += 1;
        }
    }
}
