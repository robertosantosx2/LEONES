//! Lowers parsed rules to a flat program over bytes.
//!
//! Every terminal becomes a set of bytes: literals spell their UTF-8 bytes
//! and character classes turn into alternatives of byte range sequences, so
//! matching never decodes UTF-8 and tokens that end inside a character work
//! like any other prefix.

use std::collections::HashMap;

use crate::gbnf::{Alternatives, Ast, Item};
use crate::utf8;
use crate::Error;

/// Programs larger than this many elements are refused.
const MAX_ELEMS: usize = 1 << 22;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum Elem {
    /// One byte from the set with this index.
    Bytes(u32),
    /// Any alternative of the rule with this index.
    Rule(u32),
    /// The end of an alternative.
    End,
}

/// A 256-bit set of bytes.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Default)]
pub(crate) struct ByteSet([u64; 4]);

impl ByteSet {
    fn range(lo: u8, hi: u8) -> ByteSet {
        let mut set = ByteSet::default();
        for b in lo..=hi {
            set.0[usize::from(b >> 6)] |= 1 << (b & 63);
        }
        set
    }

    fn union(self, other: ByteSet) -> ByteSet {
        ByteSet(std::array::from_fn(|i| self.0[i] | other.0[i]))
    }

    #[inline]
    pub(crate) fn contains(&self, b: u8) -> bool {
        self.0[usize::from(b >> 6)] >> (b & 63) & 1 != 0
    }
}

pub(crate) struct Program {
    pub elems: Vec<Elem>,
    /// Where each alternative of each rule starts in `elems`.
    pub rules: Vec<Vec<u32>>,
    pub sets: Vec<ByteSet>,
    pub root: u32,
}

pub(crate) fn compile(ast: &Ast) -> Result<Program, Error> {
    let mut c = Compiler {
        bodies: vec![Vec::new(); ast.rules.len()],
        names: ast.names.clone(),
        sets: Vec::new(),
        set_ids: HashMap::new(),
        classes: HashMap::new(),
        size: 0,
    };
    for (id, alts) in ast.rules.iter().enumerate() {
        c.bodies[id] = c.alternatives(alts, id)?;
    }

    let mut program = Program {
        elems: Vec::with_capacity(c.size + c.bodies.len()),
        rules: Vec::with_capacity(c.bodies.len()),
        sets: c.sets,
        root: ast.root as u32,
    };
    for body in &c.bodies {
        let starts = body
            .iter()
            .map(|alt| {
                let start = program.elems.len() as u32;
                program.elems.extend_from_slice(alt);
                program.elems.push(Elem::End);
                start
            })
            .collect();
        program.rules.push(starts);
    }
    if let Some(rule) = left_recursive(&program) {
        return Err(Error::LeftRecursion(c.names[rule].clone()));
    }
    Ok(program)
}

struct Compiler {
    /// The alternatives of every rule, named and synthesized.
    bodies: Vec<Vec<Vec<Elem>>>,
    names: Vec<String>,
    sets: Vec<ByteSet>,
    set_ids: HashMap<ByteSet, u32>,
    /// Rules already made for multi-byte character classes.
    classes: HashMap<Vec<(u32, u32)>, u32>,
    size: usize,
}

impl Compiler {
    fn alternatives(&mut self, alts: &Alternatives, owner: usize) -> Result<Vec<Vec<Elem>>, Error> {
        alts.iter()
            .map(|seq| {
                let mut out = Vec::new();
                for item in seq {
                    self.item(item, owner, &mut out)?;
                }
                Ok(out)
            })
            .collect()
    }

    fn item(&mut self, item: &Item, owner: usize, out: &mut Vec<Elem>) -> Result<(), Error> {
        match item {
            Item::Literal(bytes) => {
                for &b in bytes {
                    out.push(Elem::Bytes(self.set(ByteSet::range(b, b))));
                }
            }
            Item::Class { negated, ranges } => {
                let mut ranges = ranges.clone();
                utf8::normalize(&mut ranges);
                if *negated {
                    ranges = utf8::complement(&ranges);
                }
                out.push(self.class(ranges, owner));
            }
            Item::Any => out.push(self.class(vec![(0, utf8::MAX_CHAR)], owner)),
            Item::Rule(id) => out.push(Elem::Rule(*id as u32)),
            Item::Group(alts) if alts.len() == 1 => {
                for item in &alts[0] {
                    self.item(item, owner, out)?;
                }
            }
            Item::Group(alts) => {
                let body = self.alternatives(alts, owner)?;
                out.push(self.rule(owner, body));
            }
            Item::Repeat { item, min, max } => {
                let mut once = Vec::new();
                self.item(item, owner, &mut once)?;
                self.repeat(&once, *min, *max, owner, out)?;
            }
        }
        Ok(())
    }

    /// `x{m,n}` becomes `x` m times then `x-opt(n-m)`, with
    /// `x-opt(k) ::= x x-opt(k-1) |`; `x{m,}` ends in `x-star ::= x x-star |`.
    fn repeat(
        &mut self,
        once: &[Elem],
        min: u32,
        max: Option<u32>,
        owner: usize,
        out: &mut Vec<Elem>,
    ) -> Result<(), Error> {
        self.size = self
            .size
            .saturating_add(once.len().saturating_mul(min as usize));
        if self.size > MAX_ELEMS {
            return Err(Error::TooLarge);
        }
        for _ in 0..min {
            out.extend_from_slice(once);
        }
        match max {
            None => {
                let id = self.bodies.len() as u32;
                let mut more = once.to_vec();
                more.push(Elem::Rule(id));
                out.push(self.rule(owner, vec![more, Vec::new()]));
            }
            Some(max) => {
                let mut tail = None;
                for _ in min..max {
                    let mut more = once.to_vec();
                    more.extend(tail);
                    tail = Some(self.rule(owner, vec![more, Vec::new()]));
                    self.size += once.len() + 1;
                    if self.size > MAX_ELEMS {
                        return Err(Error::TooLarge);
                    }
                }
                out.extend(tail);
            }
        }
        Ok(())
    }

    /// A class of normalized code point ranges: one byte set when every
    /// character is ASCII, otherwise a rule over its UTF-8 spellings.
    fn class(&mut self, ranges: Vec<(u32, u32)>, owner: usize) -> Elem {
        if let Some(&id) = self.classes.get(&ranges) {
            return Elem::Rule(id);
        }
        let mut seqs = Vec::new();
        for &(lo, hi) in &ranges {
            utf8::sequences(lo, hi, &mut seqs);
        }
        let mut single = ByteSet::default();
        let mut multi = Vec::new();
        for seq in &seqs {
            match seq[..] {
                [(lo, hi)] => single = single.union(ByteSet::range(lo, hi)),
                _ => multi.push(
                    seq.iter()
                        .map(|&(lo, hi)| Elem::Bytes(self.set(ByteSet::range(lo, hi))))
                        .collect(),
                ),
            }
        }
        let single = (single != ByteSet::default()).then(|| Elem::Bytes(self.set(single)));
        if multi.is_empty() {
            if let Some(elem) = single {
                return elem;
            }
        }
        let mut body: Vec<Vec<Elem>> = single.map(|e| vec![e]).into_iter().collect();
        body.extend(multi);
        let elem = self.rule(owner, body);
        if let Elem::Rule(id) = elem {
            self.classes.insert(ranges, id);
        }
        elem
    }

    fn rule(&mut self, owner: usize, body: Vec<Vec<Elem>>) -> Elem {
        let id = self.bodies.len();
        self.names.push(format!("{}-{id}", self.names[owner]));
        self.bodies.push(body);
        Elem::Rule(id as u32)
    }

    fn set(&mut self, set: ByteSet) -> u32 {
        *self.set_ids.entry(set).or_insert_with(|| {
            self.sets.push(set);
            self.sets.len() as u32 - 1
        })
    }
}

/// A rule that can reach itself without consuming a byte, which would make
/// matching loop forever.
fn left_recursive(p: &Program) -> Option<usize> {
    let n = p.rules.len();
    let mut nullable = vec![false; n];
    let alt = |start: u32| {
        p.elems[start as usize..]
            .iter()
            .take_while(|e| **e != Elem::End)
    };
    loop {
        let mut changed = false;
        for r in 0..n {
            if !nullable[r]
                && p.rules[r]
                    .iter()
                    .any(|&s| alt(s).all(|e| matches!(e, Elem::Rule(x) if nullable[*x as usize])))
            {
                nullable[r] = true;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }

    let leftmost: Vec<Vec<usize>> = (0..n)
        .map(|r| {
            let mut refs = Vec::new();
            for &s in &p.rules[r] {
                for e in alt(s) {
                    let Elem::Rule(x) = *e else { break };
                    refs.push(x as usize);
                    if !nullable[x as usize] {
                        break;
                    }
                }
            }
            refs
        })
        .collect();

    // Iterative depth-first search: 0 unvisited, 1 on the path, 2 done.
    let mut color = vec![0u8; n];
    for start in 0..n {
        if color[start] != 0 {
            continue;
        }
        let mut path = vec![(start, 0)];
        color[start] = 1;
        while let Some(&mut (r, ref mut next)) = path.last_mut() {
            if let Some(&x) = leftmost[r].get(*next) {
                *next += 1;
                match color[x] {
                    0 => {
                        color[x] = 1;
                        path.push((x, 0));
                    }
                    1 => return Some(x),
                    _ => {}
                }
            } else {
                color[r] = 2;
                path.pop();
            }
        }
    }
    None
}
