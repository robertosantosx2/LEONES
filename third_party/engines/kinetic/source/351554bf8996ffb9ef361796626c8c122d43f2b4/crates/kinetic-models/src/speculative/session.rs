use std::collections::HashMap;

use super::{Drafter, Target};

const NONE: u32 = u32::MAX;

/// Suffix states whose latest occurrence each new token records. Deeper
/// states, which stand for short suffixes, keep an older occurrence, which
/// is still a real one.
const RECENCY_DEPTH: usize = 64;

/// Drafts from everything the session has seen: every token observed, in
/// every sequence, plus anything fed in with [`SessionIndex::extend`], such
/// as files the session works on. A suffix automaton over that history
/// finds the longest suffix of the context that occurred before and
/// proposes what followed its latest occurrence.
///
/// Adding a token costs amortized constant time. The index holds at most
/// `capacity` tokens; past that it forgets the older half and rebuilds,
/// which keeps memory near 100 bytes per token held.
pub struct SessionIndex {
    tokens: Vec<u32>,
    nodes: Vec<Node>,
    /// Transitions, by state and token.
    edges: HashMap<(u32, u32), u32>,
    /// Each state's transition tokens as a linked list, for cloning states.
    out: Vec<(u32, u32)>,
    /// The state of the whole history.
    last: u32,
    capacity: usize,
    /// Shortest match, counting the token about to run, worth drafting from.
    pub min_match: usize,
}

struct Node {
    /// Length of the longest string the state stands for.
    len: u32,
    /// The state of the longest suffix that ends in more places.
    link: u32,
    /// Head of the state's list in `out`.
    first_out: u32,
    /// Latest and second latest end positions of the state's strings.
    recent: u32,
    earlier: u32,
}

impl Default for SessionIndex {
    fn default() -> Self {
        SessionIndex::new(1 << 18)
    }
}

impl SessionIndex {
    /// An empty index that holds up to `capacity` tokens.
    pub fn new(capacity: usize) -> Self {
        let mut index = SessionIndex {
            tokens: Vec::new(),
            nodes: Vec::new(),
            edges: HashMap::new(),
            out: Vec::new(),
            last: 0,
            capacity: capacity.max(2),
            min_match: 3,
        };
        index.clear();
        index
    }

    /// Tokens held.
    pub fn len(&self) -> usize {
        self.tokens.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tokens.is_empty()
    }

    /// Appends `tokens` to the history.
    pub fn extend(&mut self, tokens: &[u32]) {
        for &t in tokens {
            if self.tokens.len() == self.capacity {
                let keep = self.tokens.split_off(self.capacity / 2);
                self.clear();
                keep.iter().for_each(|&t| self.push(t));
            }
            self.push(t);
        }
    }

    /// Up to `limit` tokens that followed the latest earlier occurrence of
    /// the longest suffix of the history followed by `next`.
    pub fn draft(&self, next: u32, limit: usize) -> Vec<u32> {
        let mut v = self.last;
        while v != NONE && !self.edges.contains_key(&(v, next)) {
            v = self.node(v).link;
        }
        if v == NONE || (self.node(v).len as usize) < self.min_match.saturating_sub(1) {
            return Vec::new();
        }
        let found = self.node(self.edges[&(v, next)]);
        let n = self.tokens.len();
        [found.recent, found.earlier]
            .into_iter()
            .map(|end| end as usize + 1)
            .find(|&start| start < n)
            .map_or_else(Vec::new, |start| {
                self.tokens[start..(start + limit).min(n)].to_vec()
            })
    }

    fn clear(&mut self) {
        self.tokens.clear();
        self.nodes.clear();
        self.edges.clear();
        self.out.clear();
        self.nodes.push(Node {
            len: 0,
            link: NONE,
            first_out: NONE,
            recent: NONE,
            earlier: NONE,
        });
        self.last = 0;
    }

    fn node(&self, i: u32) -> &Node {
        &self.nodes[i as usize]
    }

    fn new_node(&mut self, len: u32, link: u32, recent: u32, earlier: u32) -> u32 {
        self.nodes.push(Node {
            len,
            link,
            first_out: NONE,
            recent,
            earlier,
        });
        (self.nodes.len() - 1) as u32
    }

    fn add_edge(&mut self, from: u32, token: u32, to: u32) {
        self.edges.insert((from, token), to);
        let node = &mut self.nodes[from as usize];
        self.out.push((token, node.first_out));
        node.first_out = (self.out.len() - 1) as u32;
    }

    fn push(&mut self, c: u32) {
        let end = self.tokens.len() as u32;
        self.tokens.push(c);
        let cur = self.new_node(self.node(self.last).len + 1, NONE, end, NONE);
        let mut p = self.last;
        while p != NONE && !self.edges.contains_key(&(p, c)) {
            self.add_edge(p, c, cur);
            p = self.node(p).link;
        }
        let link = if p == NONE {
            0
        } else {
            let q = self.edges[&(p, c)];
            if self.node(p).len + 1 == self.node(q).len {
                q
            } else {
                self.split(p, q, c)
            }
        };
        self.nodes[cur as usize].link = link;
        self.last = cur;

        let mut s = link;
        for _ in 0..RECENCY_DEPTH {
            if s == 0 {
                break;
            }
            let node = &mut self.nodes[s as usize];
            node.earlier = node.recent;
            node.recent = end;
            s = node.link;
        }
    }

    /// Clones `q` into a state for its strings no longer than `len(p) + 1`,
    /// which now also end at the new token `c`, and redirects to it.
    fn split(&mut self, mut p: u32, q: u32, c: u32) -> u32 {
        let (link, recent, earlier) = {
            let q = self.node(q);
            (q.link, q.recent, q.earlier)
        };
        let clone = self.new_node(self.node(p).len + 1, link, recent, earlier);
        let mut e = self.node(q).first_out;
        while e != NONE {
            let (token, next) = self.out[e as usize];
            let to = self.edges[&(q, token)];
            self.add_edge(clone, token, to);
            e = next;
        }
        while p != NONE && self.edges.get(&(p, c)) == Some(&q) {
            self.edges.insert((p, c), clone);
            p = self.node(p).link;
        }
        self.nodes[q as usize].link = clone;
        clone
    }
}

impl<M: Target> Drafter<M> for SessionIndex {
    fn observe(&mut self, _model: &M, tokens: &[u32], _hidden: &[f32]) {
        self.extend(tokens);
    }

    fn propose(&mut self, _model: &M, context: &[u32], limit: usize) -> Vec<u32> {
        context
            .last()
            .map_or_else(Vec::new, |&next| self.draft(next, limit))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// What [`SessionIndex::draft`] should return, by brute force.
    fn expected(history: &[u32], next: u32, limit: usize, min_match: usize) -> Vec<u32> {
        let mut text = history.to_vec();
        text.push(next);
        let n = history.len();
        let occurs = |len: usize| {
            let suffix = &text[text.len() - len..];
            (0..=n - len)
                .rev()
                .filter(|&i| &history[i..i + len] == suffix)
                .map(|i| i + len)
                .collect::<Vec<_>>()
        };
        let Some(len) = (1..=n).rev().find(|&len| !occurs(len).is_empty()) else {
            return Vec::new();
        };
        if len < min_match {
            return Vec::new();
        }
        match occurs(len).into_iter().find(|&start| start < n) {
            Some(start) => history[start..(start + limit).min(n)].to_vec(),
            None => Vec::new(),
        }
    }

    #[test]
    fn drafts_like_brute_force() {
        let mut rng = 12345u64;
        let mut random = |m: u64| {
            rng = rng
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            ((rng >> 33) % m) as u32
        };
        for alphabet in [2, 3, 5] {
            let mut index = SessionIndex::new(1 << 12);
            index.min_match = 2;
            let mut history = Vec::new();
            for _ in 0..400 {
                let t = random(alphabet);
                index.extend(&[t]);
                history.push(t);
                let next = random(alphabet);
                assert_eq!(
                    index.draft(next, 6),
                    expected(&history, next, 6, 2),
                    "{history:?} then {next}"
                );
            }
        }
    }

    #[test]
    fn continues_the_longest_and_latest_match() {
        let mut index = SessionIndex::new(64);
        index.min_match = 2;
        index.extend(&[1, 2, 3, 4, 9, 9, 2, 3, 5, 7, 1, 2]);
        assert_eq!(index.draft(3, 3), vec![4, 9, 9]);
        index.extend(&[3, 8, 8, 2]);
        assert_eq!(index.draft(3, 2), vec![8, 8]);
    }

    #[test]
    fn forgets_the_older_half_when_full() {
        let mut index = SessionIndex::new(8);
        index.min_match = 2;
        index.extend(&[1, 2, 3, 4, 5, 6, 7, 8, 9]);
        assert_eq!(index.len(), 5);
        assert!(index.draft(2, 2).is_empty());
        index.extend(&[5]);
        assert_eq!(index.draft(6, 2), vec![7, 8]);
    }
}
