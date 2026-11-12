//! A lazily built automaton over the parse stacks of a grammar.
//!
//! A stack is a list of program positions still to match, its top always a
//! byte set; stacks share their tails and are interned, so equal stacks have
//! equal ids. A state is the sorted set of stacks the bytes so far can be in,
//! interned the same way, so stepping a state by a byte is a table lookup
//! once it has been computed.
//!
//! A state can also be cut to the top frames of its stacks, standing for
//! every state that agrees on those frames. Stepping a cut state below its
//! cut gives [`OPEN`]: what follows depends on the frames left out.

use crate::hash::{FastMap, FastSet};
use crate::program::{Elem, Program};

/// No input leads out of this state.
pub(crate) const DEAD: u32 = u32::MAX;
const UNKNOWN: u32 = u32::MAX - 1;
/// The step left a cut state's frames.
pub(crate) const OPEN: u32 = u32::MAX - 2;

/// The empty stack: the grammar has been matched completely.
const EMPTY: u32 = u32::MAX;
/// The frames a cut stack leaves out.
const CONTEXT: u32 = u32::MAX - 1;

pub(crate) struct Dfa<'g> {
    program: &'g Program,
    /// Interned stack frames: a position and the stack beneath it.
    frames: Vec<(u32, u32)>,
    frame_ids: FastMap<(u32, u32), u32>,
    states: Vec<Box<[u32]>>,
    state_ids: FastMap<Box<[u32]>, u32>,
    /// `next[state * 256 + byte]`, filled on first use.
    next: Vec<u32>,
    /// The cut of each state, filled on first use.
    cuts: Vec<u32>,
    todo: Vec<u32>,
    seen: FastSet<u32>,
    out: Vec<u32>,
}

impl<'g> Dfa<'g> {
    pub(crate) fn new(program: &'g Program) -> Dfa<'g> {
        Dfa {
            program,
            frames: Vec::new(),
            frame_ids: FastMap::default(),
            states: Vec::new(),
            state_ids: FastMap::default(),
            next: Vec::new(),
            cuts: Vec::new(),
            todo: Vec::new(),
            seen: FastSet::default(),
            out: Vec::new(),
        }
    }

    /// The state before any input.
    pub(crate) fn start(&mut self) -> u32 {
        let mut out = std::mem::take(&mut self.out);
        out.clear();
        let root = self.program.root as usize;
        for i in 0..self.program.rules[root].len() {
            let stack = self.continue_at(self.program.rules[root][i], EMPTY);
            self.advance(stack, &mut out);
        }
        let state = self.intern(&mut out);
        self.out = out;
        state
    }

    /// The state after `byte`: a state id, [`DEAD`] or, from a cut state,
    /// [`OPEN`].
    #[inline]
    pub(crate) fn step(&mut self, state: u32, byte: u8) -> u32 {
        let next = self.next[state as usize * 256 + usize::from(byte)];
        if next != UNKNOWN {
            return next;
        }
        self.compute(state, byte)
    }

    /// Whether the input so far is a complete match.
    pub(crate) fn is_accepting(&self, state: u32) -> bool {
        self.states[state as usize].last() == Some(&EMPTY)
    }

    /// `state` with its stacks cut at one height, just under the top frame
    /// of the shortest, the frames below replaced by [`CONTEXT`]. States
    /// that differ only below that height share their cut: the inside of a
    /// string is the same wherever the string is.
    pub(crate) fn cut(&mut self, state: u32) -> u32 {
        let known = self.cuts[state as usize];
        if known != UNKNOWN {
            return known;
        }
        let stacks: Vec<Vec<u32>> = self.states[state as usize]
            .iter()
            .map(|&s| self.positions(s))
            .collect();
        let base = stacks
            .iter()
            .map(Vec::len)
            .min()
            .unwrap_or(0)
            .saturating_sub(1);
        let cut = if base == 0 {
            state
        } else {
            let mut ids: Vec<u32> = stacks
                .iter()
                .map(|p| {
                    p[base..]
                        .iter()
                        .fold(CONTEXT, |below, &pos| self.push(pos, below))
                })
                .collect();
            self.intern(&mut ids)
        };
        self.cuts[state as usize] = cut;
        cut
    }

    /// Number of states built so far.
    pub(crate) fn len(&self) -> usize {
        self.states.len()
    }

    /// Forgets every state but `keep`, returning its new id. Neither this
    /// nor [`Dfa::cut`] takes a cut state.
    pub(crate) fn reset(&mut self, keep: u32) -> u32 {
        let stacks: Vec<Vec<u32>> = self.states[keep as usize]
            .iter()
            .map(|&s| self.positions(s))
            .collect();
        *self = Dfa::new(self.program);
        let mut ids: Vec<u32> = stacks
            .iter()
            .map(|positions| {
                positions
                    .iter()
                    .fold(EMPTY, |below, &pos| self.push(pos, below))
            })
            .collect();
        self.intern(&mut ids)
    }

    /// The positions of a stack, bottom first.
    fn positions(&self, mut stack: u32) -> Vec<u32> {
        let mut out = Vec::new();
        while stack != EMPTY {
            let (pos, below) = self.frames[stack as usize];
            out.push(pos);
            stack = below;
        }
        out.reverse();
        out
    }

    #[cold]
    fn compute(&mut self, state: u32, byte: u8) -> u32 {
        let mut out = std::mem::take(&mut self.out);
        out.clear();
        for i in 0..self.states[state as usize].len() {
            let stack = self.states[state as usize][i];
            if stack == EMPTY || stack == CONTEXT {
                continue;
            }
            let (pos, below) = self.frames[stack as usize];
            let Elem::Bytes(set) = self.program.elems[pos as usize] else {
                unreachable!("stack tops are byte sets")
            };
            if self.program.sets[set as usize].contains(byte) {
                let rest = self.continue_at(pos + 1, below);
                self.advance(rest, &mut out);
            }
        }
        let next = if out.is_empty() {
            DEAD
        } else if out.contains(&CONTEXT) {
            OPEN
        } else {
            self.intern(&mut out)
        };
        self.out = out;
        self.next[state as usize * 256 + usize::from(byte)] = next;
        next
    }

    /// Adds to `out` every stack `stack` can become without consuming input:
    /// rule references at the top are replaced by each of their alternatives.
    fn advance(&mut self, stack: u32, out: &mut Vec<u32>) {
        self.seen.clear();
        self.todo.push(stack);
        while let Some(stack) = self.todo.pop() {
            if !self.seen.insert(stack) {
                continue;
            }
            if stack == EMPTY || stack == CONTEXT {
                out.push(stack);
                continue;
            }
            let (pos, below) = self.frames[stack as usize];
            match self.program.elems[pos as usize] {
                Elem::Bytes(_) => out.push(stack),
                Elem::Rule(rule) => {
                    let rest = self.continue_at(pos + 1, below);
                    for i in 0..self.program.rules[rule as usize].len() {
                        let next = self.continue_at(self.program.rules[rule as usize][i], rest);
                        self.todo.push(next);
                    }
                }
                Elem::End => unreachable!("ends are never pushed"),
            }
        }
    }

    /// The stack that still has to match from `pos` on, above `below`.
    fn continue_at(&mut self, pos: u32, below: u32) -> u32 {
        if self.program.elems[pos as usize] == Elem::End {
            below
        } else {
            self.push(pos, below)
        }
    }

    fn push(&mut self, pos: u32, below: u32) -> u32 {
        *self.frame_ids.entry((pos, below)).or_insert_with(|| {
            self.frames.push((pos, below));
            self.frames.len() as u32 - 1
        })
    }

    fn intern(&mut self, stacks: &mut Vec<u32>) -> u32 {
        stacks.sort_unstable();
        stacks.dedup();
        if let Some(&id) = self.state_ids.get(&stacks[..]) {
            return id;
        }
        let id = self.states.len() as u32;
        let stacks: Box<[u32]> = stacks[..].into();
        self.states.push(stacks.clone());
        self.state_ids.insert(stacks, id);
        self.next.resize(self.next.len() + 256, UNKNOWN);
        self.cuts.push(UNKNOWN);
        id
    }
}
