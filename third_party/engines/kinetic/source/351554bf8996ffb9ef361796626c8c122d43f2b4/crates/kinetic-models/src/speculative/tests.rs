//! Speculative decoding against a toy model whose logits depend only on the
//! last two tokens, so batches and single tokens agree exactly and seeded
//! runs must match plain decoding token for token.

use super::*;

const VOCAB: usize = 16;

struct Toy;

#[derive(Default)]
struct ToyState {
    tokens: Vec<u32>,
    mark: Option<usize>,
    /// The tokens of the tree run since the checkpoint, if one was.
    tree: Option<Vec<u32>>,
    /// Trees run so far.
    trees: usize,
}

/// Mostly counts up, with hashed noise, so drafts are sometimes right.
fn toy_logits(tokens: &[u32]) -> Vec<f32> {
    let a = tokens.last().copied().unwrap_or(0) as u64;
    let b = tokens.len().checked_sub(2).map_or(0, |i| tokens[i]) as u64;
    (0..VOCAB as u64)
        .map(|v| {
            let h = (a * 31 + b * 17 + v * 7 + 3).wrapping_mul(0x9e37_79b9_7f4a_7c15) >> 40;
            let noise = (h % 1000) as f32 / 250.0 - 2.0;
            noise
                + if v == (a + 1) % VOCAB as u64 {
                    3.0
                } else {
                    0.0
                }
        })
        .collect()
}

impl Target for Toy {
    type State = ToyState;
    type Scores = Vec<f32>;

    fn n_embd(&self) -> usize {
        1
    }

    fn n_vocab(&self) -> usize {
        VOCAB
    }

    fn score(&self, state: &mut ToyState, tokens: &[u32], all_rows: bool) -> (Vec<f32>, Vec<f32>) {
        let mut rows = Vec::new();
        for &t in tokens {
            state.tokens.push(t);
            if all_rows {
                rows.extend(toy_logits(&state.tokens));
            }
        }
        if !all_rows {
            rows = toy_logits(&state.tokens);
        }
        (rows, vec![0.0; tokens.len()])
    }

    fn logits(&self, state: &mut ToyState, tokens: &[u32], all_rows: bool) -> (Vec<f32>, Vec<f32>) {
        self.score(state, tokens, all_rows)
    }

    fn score_tree(
        &self,
        state: &mut ToyState,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Option<(Vec<f32>, Vec<f32>)> {
        let mut rows = Vec::new();
        for row in 0..tokens.len() {
            let mut path = vec![row];
            while let Some(p) = parents[path[path.len() - 1]] {
                path.push(p);
            }
            let mut seen = state.tokens.clone();
            seen.extend(path.iter().rev().map(|&r| tokens[r]));
            rows.extend(toy_logits(&seen));
        }
        state.tree = Some(tokens.to_vec());
        state.trees += 1;
        Some((rows, vec![0.0; tokens.len()]))
    }

    fn logits_tree(
        &self,
        state: &mut ToyState,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Option<(Vec<f32>, Vec<f32>)> {
        self.score_tree(state, tokens, parents)
    }

    fn greedy(&self, scores: &Vec<f32>, row: usize) -> u32 {
        argmax(&scores[row * VOCAB..][..VOCAB])
    }

    fn checkpoint(&self, state: &mut ToyState) {
        state.mark = Some(state.tokens.len());
    }

    fn rollback(&self, state: &mut ToyState, keep: usize) {
        let start = state.mark.take().expect("checkpoint");
        state.tokens.truncate(start + keep);
    }

    fn rollback_rows(&self, state: &mut ToyState, rows: &[usize]) {
        match state.tree.take() {
            Some(tree) => {
                let start = state.mark.take().expect("checkpoint");
                state.tokens.truncate(start);
                state.tokens.extend(rows.iter().map(|&r| tree[r]));
            }
            None => self.rollback(state, rows.len()),
        }
    }
}

/// Guesses that the count goes on.
struct Counting;

impl Drafter<Toy> for Counting {
    fn propose(&mut self, _model: &Toy, context: &[u32], limit: usize) -> Vec<u32> {
        let last = *context.last().unwrap();
        (1..=limit as u32)
            .map(|i| (last + i) % VOCAB as u32)
            .collect()
    }
}

/// Guesses the toy's own greedy continuation, which sampling often leaves.
struct Greedier;

impl Drafter<Toy> for Greedier {
    fn propose(&mut self, _model: &Toy, context: &[u32], limit: usize) -> Vec<u32> {
        let mut seen = context.to_vec();
        for _ in 0..limit {
            seen.push(argmax(&toy_logits(&seen)));
        }
        seen.split_off(context.len())
    }
}

/// Always wrong in the same way.
struct Zeros;

impl Drafter<Toy> for Zeros {
    fn propose(&mut self, _model: &Toy, _context: &[u32], limit: usize) -> Vec<u32> {
        vec![0; limit]
    }
}

const PROMPT: [u32; 8] = [1, 2, 3, 1, 2, 3, 1, 2];
const N: usize = 40;

fn plain<P: Policy<Toy>>(policy: &mut P) -> Vec<u32> {
    let mut state = ToyState::default();
    let mut context = PROMPT.to_vec();
    let (mut scores, _) = policy.score(&Toy, &mut state, &PROMPT, false);
    for _ in 0..N {
        let t = policy.choose(&Toy, &scores, 0, &context);
        context.push(t);
        scores = policy.score(&Toy, &mut state, &[t], false).0;
    }
    context.split_off(PROMPT.len())
}

/// The output, the number of passes it took and how many of them ran a
/// tree.
fn speculative<P: Policy<Toy>, D: Drafter<Toy>>(
    policy: &mut P,
    decoder: &mut Decoder<D>,
) -> (Vec<u32>, usize, usize) {
    let mut state = ToyState::default();
    let mut context = PROMPT.to_vec();
    decoder.prefill(&Toy, policy, &mut state, &context, 0);
    let mut passes = 0;
    while context.len() - PROMPT.len() < N {
        let limit = N - (context.len() - PROMPT.len());
        decoder.step(&Toy, policy, &mut state, &mut context, limit, |_| false);
        passes += 1;
        assert_eq!(state.tokens, context, "the state holds the context");
    }
    (context.split_off(PROMPT.len()), passes, state.trees)
}

fn drafters() -> Vec<Box<dyn Drafter<Toy>>> {
    vec![
        Box::new(Counting),
        Box::new(Zeros),
        Box::new(Lookup::default()),
        Box::new(SessionIndex::default()),
        Box::new(Ensemble::new(vec![
            Box::new(Zeros) as Box<dyn Drafter<Toy>>,
            Box::new(Lookup::default()),
            Box::new(Counting),
        ])),
    ]
}

fn sampling(seed: u64) -> Sampling {
    Sampling {
        temperature: 0.9,
        top_k: 8,
        top_p: 0.9,
        min_p: 0.02,
        repeat_penalty: 1.2,
        presence_penalty: 0.1,
        frequency_penalty: 0.05,
        repeat_last_n: 16,
        seed: Some(seed),
        ..Sampling::default()
    }
}

#[test]
fn greedy_output_is_plain_greedy() {
    let expected = plain(&mut Greedy);
    for drafter in drafters() {
        let mut decoder = Decoder::new(drafter);
        assert_eq!(speculative(&mut Greedy, &mut decoder).0, expected);
    }
}

#[test]
fn seeded_sampling_is_plain_sampling() {
    let mut saved = 0;
    for seed in 0..64 {
        let expected = plain(&mut Sampler::new(sampling(seed)));
        for drafter in drafters() {
            let mut decoder = Decoder::new(drafter);
            let (tokens, passes, _) = speculative(&mut Sampler::new(sampling(seed)), &mut decoder);
            assert_eq!(tokens, expected, "seed {seed}");
            saved += N - passes;
        }
    }
    assert!(saved > 1000, "drafts were accepted: {saved} passes saved");
}

#[test]
fn ensemble_scores_follow_the_hits() {
    let ensemble = Ensemble::new(vec![
        Box::new(Zeros) as Box<dyn Drafter<Toy>>,
        Box::new(Counting),
    ]);
    let mut decoder = Decoder::new(ensemble);
    let (tokens, _, _) = speculative(&mut Greedy, &mut decoder);
    assert_eq!(tokens, plain(&mut Greedy));
    let scores = decoder.drafter.scores();
    assert!(scores[1] > scores[0] + 0.3, "{scores:?}");
}

/// Sources that disagree make trees; verifying them whole keeps greedy and
/// seeded output exactly plain, and gets further per pass than verifying
/// only their leading chains.
#[test]
fn trees_are_verified_losslessly() {
    let decoder = |row_cost| {
        let mut decoder = Decoder::new(Ensemble::new(vec![
            Box::new(Counting) as Box<dyn Drafter<Toy>>,
            Box::new(Greedier),
            Box::new(Zeros),
        ]));
        decoder.row_cost = row_cost;
        decoder
    };
    let (tokens, _, trees) = speculative(&mut Greedy, &mut decoder(0.0));
    assert_eq!(tokens, plain(&mut Greedy));
    assert!(trees > 0);
    let (mut tree_passes, mut chain_passes) = (0, 0);
    for seed in 0..64 {
        let expected = plain(&mut Sampler::new(sampling(seed)));
        let (tokens, passes, trees) =
            speculative(&mut Sampler::new(sampling(seed)), &mut decoder(0.0));
        assert_eq!(tokens, expected, "seed {seed}");
        assert!(trees > 0, "seed {seed}");
        tree_passes += passes;
        let (tokens, passes, trees) = speculative(
            &mut Sampler::new(sampling(seed)),
            &mut decoder(f32::INFINITY),
        );
        assert_eq!((tokens, trees), (expected, 0), "seed {seed}");
        chain_passes += passes;
    }
    assert!(
        tree_passes < chain_passes,
        "{tree_passes} vs {chain_passes} passes"
    );
}

#[test]
fn a_stop_token_ends_the_step() {
    let mut decoder = Decoder::new(Counting);
    let mut state = ToyState::default();
    let mut context = PROMPT.to_vec();
    decoder.prefill(&Toy, &mut Greedy, &mut state, &context, 0);
    let first = plain(&mut Greedy)[0];
    let step = decoder.step(&Toy, &mut Greedy, &mut state, &mut context, 8, |t| {
        t == first
    });
    assert_eq!(step.tokens, 1);
    assert_eq!(*context.last().unwrap(), first);
}

#[test]
fn argmax_prefers_the_lowest_index() {
    assert_eq!(argmax(&[1.0, 3.0, 3.0, 2.0]), 1);
}

/// Every sampler, history-dependent and stateful ones included, keeps
/// drafted output token for token what plain seeded sampling gives, and
/// logprobs come out the same.
#[test]
fn every_sampler_is_exact_under_drafting() {
    let base = Sampling {
        temperature: 1.1,
        top_k: 0,
        top_p: 1.0,
        min_p: 0.0,
        ..Sampling::default()
    };
    let cases = [
        Sampling {
            logit_bias: vec![(3, 2.0), (5, f32::NEG_INFINITY)],
            ..base.clone()
        },
        Sampling {
            dry_multiplier: 0.8,
            dry_breaker_tokens: vec![(7, Vec::new()), (2, vec![3])],
            ..base.clone()
        },
        Sampling {
            xtc_probability: 0.5,
            xtc_threshold: 0.1,
            ..base.clone()
        },
        Sampling {
            typical_p: 0.7,
            top_k: 10,
            ..base.clone()
        },
        Sampling {
            top_n_sigma: 1.0,
            ..base.clone()
        },
        Sampling {
            mirostat: 1,
            mirostat_tau: 3.0,
            ..base.clone()
        },
        Sampling {
            mirostat: 2,
            mirostat_tau: 2.0,
            ..base.clone()
        },
        Sampling {
            temperature: 0.0,
            dry_multiplier: 1.0,
            logit_bias: vec![(4, -1.0)],
            ..base.clone()
        },
    ];
    for params in cases {
        for seed in 0..16 {
            let params = Sampling {
                seed: Some(seed),
                ..params.clone()
            };
            let log = Logprobs::new(3);
            let expected = plain(&mut Sampler::new(params.clone()).with_logprobs(log.clone()));
            for drafter in drafters() {
                let drafted = Logprobs::new(3);
                let mut sampler = Sampler::new(params.clone()).with_logprobs(drafted.clone());
                let (tokens, _, _) = speculative(&mut sampler, &mut Decoder::new(drafter));
                assert_eq!(tokens, expected, "{params:?}");
                assert_eq!(drafted.range(0, N), log.range(0, N), "{params:?}");
            }
        }
    }
}
