//! Byte-pair merging over token ids.

use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::hash::{BuildHasherDefault, Hasher};

/// A merge rule: the pair it applies to becomes `id`, lower `rank` first.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Merge {
    pub rank: u32,
    pub id: u32,
}

/// Merge rules keyed by the ids of the left and right halves.
pub(crate) struct Bpe {
    merges: HashMap<u64, Merge, BuildHasherDefault<PairHasher>>,
    byte_ids: [u32; 256],
}

/// Per-call buffers, reused across the pieces of one text.
#[derive(Default)]
pub(crate) struct Scratch {
    symbols: Vec<Symbol>,
    queue: BinaryHeap<Reverse<Candidate>>,
}

#[derive(Clone, Copy)]
struct Symbol {
    id: u32,
    prev: usize,
    next: usize,
}

/// A pair that could merge, ordered by rank and then by position, as the
/// reference implementation does. Stale entries are skipped when popped.
#[derive(PartialEq, Eq, PartialOrd, Ord)]
struct Candidate {
    rank: u32,
    left: usize,
    right: usize,
    left_id: u32,
    right_id: u32,
    id: u32,
}

const NONE: usize = usize::MAX;
const MERGED: u32 = u32::MAX;
/// A byte the vocabulary has no token for. It never merges and is left out
/// of the output, as the reference does.
const NO_TOKEN: u32 = u32::MAX - 1;

fn key(left: u32, right: u32) -> u64 {
    (u64::from(left) << 32) | u64::from(right)
}

// the model never sees letters, only these merges; that is why it cannot count the r's
impl Bpe {
    pub(crate) fn new(
        byte_ids: [Option<u32>; 256],
        merges: impl IntoIterator<Item = (u32, u32, Merge)>,
    ) -> Bpe {
        let mut map = HashMap::default();
        for (left, right, merge) in merges {
            map.entry(key(left, right)).or_insert(merge);
        }
        Bpe {
            merges: map,
            byte_ids: byte_ids.map(|id| id.unwrap_or(NO_TOKEN)),
        }
    }

    pub(crate) fn encode(&self, piece: &[u8], scratch: &mut Scratch, out: &mut Vec<u32>) {
        if let [b] = piece {
            out.extend(Some(self.byte_ids[usize::from(*b)]).filter(|&id| id != NO_TOKEN));
            return;
        }
        self.merge(
            piece.iter().map(|&b| self.byte_ids[usize::from(b)]),
            scratch,
            out,
        );
    }

    /// Merges a run of starting symbols, given as token ids; [`NO_TOKEN`]
    /// marks one that never merges and is dropped.
    pub(crate) fn merge(
        &self,
        ids: impl Iterator<Item = u32>,
        scratch: &mut Scratch,
        out: &mut Vec<u32>,
    ) {
        let Scratch { symbols, queue } = scratch;
        symbols.clear();
        queue.clear();
        symbols.extend(ids.enumerate().map(|(i, id)| Symbol {
            id,
            prev: if i == 0 { NONE } else { i - 1 },
            next: i + 1,
        }));
        let Some(last) = symbols.len().checked_sub(1) else {
            return;
        };
        symbols[last].next = NONE;
        for left in 0..last {
            self.push_pair(symbols, queue, left, left + 1);
        }

        while let Some(Reverse(c)) = queue.pop() {
            let (l, r) = (symbols[c.left], symbols[c.right]);
            if l.id != c.left_id || r.id != c.right_id || l.next != c.right {
                continue;
            }
            symbols[c.left].id = c.id;
            symbols[c.left].next = r.next;
            symbols[c.right].id = MERGED;
            if r.next != NONE {
                symbols[r.next].prev = c.left;
            }
            if l.prev != NONE {
                self.push_pair(symbols, queue, l.prev, c.left);
            }
            if r.next != NONE {
                self.push_pair(symbols, queue, c.left, r.next);
            }
        }

        let mut i = 0;
        while i != NONE {
            if symbols[i].id != NO_TOKEN {
                out.push(symbols[i].id);
            }
            i = symbols[i].next;
        }
    }

    fn push_pair(
        &self,
        symbols: &[Symbol],
        queue: &mut BinaryHeap<Reverse<Candidate>>,
        left: usize,
        right: usize,
    ) {
        let (left_id, right_id) = (symbols[left].id, symbols[right].id);
        if let Some(m) = self.merges.get(&key(left_id, right_id)) {
            queue.push(Reverse(Candidate {
                rank: m.rank,
                left,
                right,
                left_id,
                right_id,
                id: m.id,
            }));
        }
    }
}

/// Multiplicative hash for packed id pairs; SipHash costs more than the
/// merge itself.
#[derive(Default)]
struct PairHasher(u64);

impl Hasher for PairHasher {
    fn finish(&self) -> u64 {
        self.0
    }

    fn write(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 = (self.0 ^ u64::from(b)).wrapping_mul(0x0100_0000_01b3);
        }
    }

    fn write_u64(&mut self, v: u64) {
        let h = v.wrapping_mul(0x9E37_79B9_7F4A_7C15);
        self.0 = h ^ (h >> 29);
    }
}
