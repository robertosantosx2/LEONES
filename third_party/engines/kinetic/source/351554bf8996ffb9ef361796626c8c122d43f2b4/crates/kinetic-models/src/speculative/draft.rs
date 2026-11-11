/// Draft tokens as a tree. Token `i` follows token `parents[i]`, or the
/// token about to run when `None`; parents come before their children.
/// Laid out depth first with each node's likeliest child first, so the
/// leading tokens that follow one another are the draft's best single
/// guess.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Draft {
    pub tokens: Vec<u32>,
    pub parents: Vec<Option<usize>>,
    /// The drafter's estimate of the chance that verification accepts each
    /// token, its whole path included.
    pub chances: Vec<f32>,
}

impl Draft {
    /// A draft without branches, of tokens the drafter is sure of.
    pub fn chain(tokens: Vec<u32>) -> Draft {
        let n = tokens.len();
        Draft {
            tokens,
            parents: (0..n).map(|i| i.checked_sub(1)).collect(),
            chances: vec![1.0; n],
        }
    }

    pub fn len(&self) -> usize {
        self.tokens.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tokens.is_empty()
    }

    /// Appends a token and returns its index.
    pub fn push(&mut self, token: u32, parent: Option<usize>, chance: f32) -> usize {
        self.tokens.push(token);
        self.parents.push(parent);
        self.chances.push(chance);
        self.tokens.len() - 1
    }

    /// How many leading tokens each follow the one before.
    pub fn chain_len(&self) -> usize {
        self.parents
            .iter()
            .enumerate()
            .take_while(|&(i, &p)| p == i.checked_sub(1))
            .count()
    }

    /// Whether the draft has no branches.
    pub fn is_chain(&self) -> bool {
        self.chain_len() == self.len()
    }

    /// Keeps only the leading chain.
    pub fn keep_chain(&mut self) {
        let n = self.chain_len();
        self.tokens.truncate(n);
        self.parents.truncate(n);
        self.chances.truncate(n);
    }

    /// The most tokens on one path.
    pub fn depth(&self) -> usize {
        self.depths().into_iter().max().map_or(0, |d| d + 1)
    }

    /// Drops every token more than `depth` tokens deep.
    pub fn truncate(&mut self, depth: usize) {
        let depths = self.depths();
        let mut index = vec![None; self.len()];
        let mut kept = Draft::default();
        for i in 0..self.len() {
            if depths[i] < depth {
                let parent = self.parents[i].map(|p| index[p].expect("parent kept"));
                index[i] = Some(kept.push(self.tokens[i], parent, self.chances[i]));
            }
        }
        *self = kept;
    }

    /// Tokens above each token.
    fn depths(&self) -> Vec<usize> {
        let mut depths: Vec<usize> = Vec::with_capacity(self.len());
        for p in &self.parents {
            depths.push(p.map_or(0, |p| depths[p] + 1));
        }
        depths
    }
}

#[cfg(test)]
mod tests {
    use super::Draft;

    fn tree() -> Draft {
        let mut d = Draft::default();
        let a = d.push(1, None, 0.9);
        let b = d.push(2, Some(a), 0.8);
        d.push(3, Some(b), 0.7);
        d.push(4, Some(a), 0.1);
        d.push(5, None, 0.05);
        d
    }

    #[test]
    fn the_leading_chain_is_the_best_guess() {
        let mut d = tree();
        assert_eq!((d.chain_len(), d.depth(), d.is_chain()), (3, 3, false));
        d.keep_chain();
        assert_eq!(d.tokens, Draft::chain(vec![1, 2, 3]).tokens);
        assert_eq!(d.parents, Draft::chain(vec![1, 2, 3]).parents);
    }

    #[test]
    fn truncation_keeps_shallow_tokens_and_their_links() {
        let mut d = tree();
        d.truncate(2);
        assert_eq!(d.tokens, [1, 2, 4, 5]);
        assert_eq!(d.parents, [None, Some(0), Some(0), None]);
    }
}
