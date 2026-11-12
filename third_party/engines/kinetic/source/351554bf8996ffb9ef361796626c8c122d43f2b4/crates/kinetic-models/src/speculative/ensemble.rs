use super::{Draft, Drafter, Target};

/// How fast a source's score follows its latest drafts.
const RATE: f32 = 0.2;

/// Drafts with several drafters at once, so new and repeated text both get
/// the drafter that suits them.
///
/// Every step each source proposes a branch, and the branches form a token
/// tree whose shared prefixes add up their sources' scores. Children are
/// ordered heaviest first, so the tree's leading chain is its heaviest path:
/// at each depth, the token whose branches weigh most. A source's score is
/// the running mean of how many leading tokens of its drafts came true,
/// measured against the tokens produced whether or not its branch was
/// verified, so no source needs to be tried to be judged.
///
/// Each token's chance of acceptance is estimated from the best source
/// through it: a mean run of `s` hits is what a per-token hit rate of
/// `s / (1 + s)` gives, and siblings, which cannot both be right, share at
/// most their parent's chance.
///
/// Sources of different types go in as boxed trait objects.
pub struct Ensemble<D> {
    sources: Vec<Source<D>>,
}

struct Source<D> {
    drafter: D,
    score: f32,
    /// The latest draft and the context length it continues.
    last: Option<(usize, Vec<u32>)>,
}

impl<D> Ensemble<D> {
    /// Earlier sources win ties.
    pub fn new(drafters: Vec<D>) -> Self {
        Ensemble {
            sources: drafters
                .into_iter()
                .map(|drafter| Source {
                    drafter,
                    score: 1.0,
                    last: None,
                })
                .collect(),
        }
    }

    /// Each source's score, in the order given to [`Ensemble::new`].
    pub fn scores(&self) -> Vec<f32> {
        self.sources.iter().map(|s| s.score).collect()
    }
}

impl<M: Target, D: Drafter<M>> Drafter<M> for Ensemble<D> {
    fn observe(&mut self, model: &M, tokens: &[u32], hidden: &[f32]) {
        for s in &mut self.sources {
            s.drafter.observe(model, tokens, hidden);
        }
    }

    fn propose(&mut self, model: &M, context: &[u32], limit: usize) -> Vec<u32> {
        let mut draft = self.propose_tree(model, context, limit);
        draft.keep_chain();
        draft.tokens
    }

    fn propose_tree(&mut self, model: &M, context: &[u32], limit: usize) -> Draft {
        let mut branches = Vec::with_capacity(self.sources.len());
        for s in &mut self.sources {
            if let Some((at, draft)) = s.last.take() {
                let hits = draft
                    .iter()
                    .zip(context.get(at..).unwrap_or_default())
                    .take_while(|(a, b)| a == b)
                    .count();
                s.score += RATE * (hits as f32 - s.score);
            }
            let draft = s.drafter.propose(model, context, limit);
            if !draft.is_empty() {
                branches.push((draft.clone(), s.score));
                s.last = Some((context.len(), draft));
            }
        }
        merge(&branches)
    }

    fn reset(&mut self, model: &M) {
        for s in &mut self.sources {
            s.drafter.reset(model);
            s.last = None;
        }
    }
}

/// A token of the merged tree, before it is laid out.
struct Node {
    token: u32,
    parent: Option<usize>,
    weight: f32,
    rate: f32,
}

/// The tree of `branches`, each with its source's score, laid out depth
/// first with heavier children first; the earlier branch wins a tie.
fn merge(branches: &[(Vec<u32>, f32)]) -> Draft {
    let mut nodes: Vec<Node> = Vec::new();
    for (branch, score) in branches {
        let mut parent = None;
        for &token in branch {
            let i = match nodes
                .iter()
                .position(|n| n.parent == parent && n.token == token)
            {
                Some(i) => i,
                None => {
                    nodes.push(Node {
                        token,
                        parent,
                        weight: 0.0,
                        rate: 0.0,
                    });
                    nodes.len() - 1
                }
            };
            nodes[i].weight += score;
            nodes[i].rate = nodes[i].rate.max(score / (1.0 + score));
            parent = Some(i);
        }
    }
    let mut draft = Draft::default();
    lay_out(&nodes, None, None, 1.0, &mut draft);
    draft
}

/// Appends the children of `node`, placed at `at` in `draft` with chance
/// `chance`, and everything below them.
fn lay_out(nodes: &[Node], node: Option<usize>, at: Option<usize>, chance: f32, draft: &mut Draft) {
    let mut children: Vec<usize> = (0..nodes.len())
        .filter(|&i| nodes[i].parent == node)
        .collect();
    children.sort_by(|&a, &b| nodes[b].weight.total_cmp(&nodes[a].weight));
    let total: f32 = children.iter().map(|&c| nodes[c].rate).sum();
    let share = chance / total.max(1.0);
    for c in children {
        let chance = share * nodes[c].rate;
        let i = draft.push(nodes[c].token, at, chance);
        lay_out(nodes, Some(c), Some(i), chance, draft);
    }
}

#[cfg(test)]
mod tests {
    use super::merge;

    #[test]
    fn agreeing_branches_outweigh_a_heavier_one() {
        let chain = |branches: &[(Vec<u32>, f32)]| {
            let mut draft = merge(branches);
            draft.keep_chain();
            draft.tokens
        };
        let branches = [
            (vec![1, 2, 3, 4], 0.6),
            (vec![1, 2, 7], 0.5),
            (vec![5, 6], 1.0),
        ];
        assert_eq!(chain(&branches), vec![1, 2, 3, 4]);
        let branches = [(vec![1, 2, 3, 4], 0.4), (vec![1, 7], 0.5), (vec![5], 0.8)];
        assert_eq!(chain(&branches), vec![1, 7]);
        assert!(merge(&[]).is_empty());
    }

    #[test]
    fn branches_share_prefixes_and_their_parents_chance() {
        let draft = merge(&[(vec![1, 2, 3], 3.0), (vec![1, 4], 1.0), (vec![5], 1.0)]);
        assert_eq!(draft.tokens, [1, 2, 3, 4, 5]);
        assert_eq!(draft.parents, [None, Some(0), Some(1), Some(0), None]);
        // Roots 1 and 5 rate 0.75 and 0.5, so they split the whole chance.
        let c = &draft.chances;
        assert!(
            (c[0] - 0.6).abs() < 1e-6 && (c[4] - 0.4).abs() < 1e-6,
            "{c:?}"
        );
        assert!(c[1] + c[3] <= c[0] && c[2] < c[1], "{c:?}");
    }
}
