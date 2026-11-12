//! Exactness checks for a real model of any architecture: a batch gives the
//! logits its tokens give one by one, every row of a tree batch gives what
//! its path gives alone and keeping that path leaves the state it leaves,
//! and speculative decoding, with drafts verified as chains and as trees,
//! reproduces plain greedy decoding token for token.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models --test architectures -- --ignored

use kinetic_gguf::GgufFile;
use kinetic_models::speculative::{
    Decoder, Drafter, Ensemble, Greedy, Lookup, Policy, SessionIndex,
};
use kinetic_models::Model;

fn open() -> GgufFile {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    GgufFile::open(path).unwrap()
}

/// A prompt that repeats itself, so drafts from the context get accepted.
fn prompt(vocab: usize) -> Vec<u32> {
    let part: Vec<u32> = (0..24u32)
        .map(|i| 100 + (i * 7919) % (vocab as u32 / 2))
        .collect();
    part.repeat(3)
}

fn bits(x: &[f32]) -> Vec<u32> {
    x.iter().map(|v| v.to_bits()).collect()
}

fn plain(model: &Model, prompt: &[u32], n: usize) -> Vec<u32> {
    let mut state = model.new_state();
    let mut context = prompt.to_vec();
    let (mut scores, _) = Greedy.score(model, &mut state, prompt, false);
    while context.len() < prompt.len() + n {
        let t = Greedy.choose(model, &scores, 0, &context);
        context.push(t);
        scores = Greedy.score(model, &mut state, &[t], false).0;
    }
    context.split_off(prompt.len())
}

fn speculative<'a>(
    model: &'a Model,
    drafter: Box<dyn Drafter<Model<'a>> + 'a>,
    row_cost: f32,
    prompt: &[u32],
    n: usize,
) -> Vec<u32> {
    let mut decoder = Decoder::new(drafter);
    decoder.row_cost = row_cost;
    let mut state = model.new_state();
    let mut context = prompt.to_vec();
    decoder.prefill(model, &mut Greedy, &mut state, &context, 0);
    while context.len() < prompt.len() + n {
        let limit = prompt.len() + n - context.len();
        decoder.step(model, &mut Greedy, &mut state, &mut context, limit, |_| {
            false
        });
    }
    context.split_off(prompt.len())
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn batches_match_tokens_one_by_one() {
    let file = open();
    let model = kinetic_models::load(&file).unwrap();
    // Short enough for every mixer to take its token-by-token arithmetic.
    let prompt = &prompt(model.n_vocab())[..24];
    let batched = model.run(&mut model.new_state(), prompt, true).logits;
    let mut state = model.new_state();
    for (t, row) in prompt.iter().zip(batched.chunks_exact(model.n_vocab())) {
        assert_eq!(bits(&model.forward(&mut state, *t)), bits(row));
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn tree_rows_match_their_paths_alone() {
    let file = open();
    let model = kinetic_models::load(&file).unwrap();
    let v = model.n_vocab();
    let tokens = &prompt(v)[..12];
    let (before, tree) = tokens.split_at(4);
    let parents = [
        None,
        Some(0),
        Some(0),
        Some(1),
        Some(2),
        Some(3),
        Some(1),
        None,
    ];
    let mut base = model.new_state();
    model.run(&mut base, before, false);

    let mut state = base.clone();
    model.checkpoint(&mut state);
    let rows = model.run_tree(&mut state, tree, &parents).logits;
    for (row, logits) in rows.chunks_exact(v).enumerate() {
        let mut path = vec![row];
        while let Some(p) = parents[*path.last().unwrap()] {
            path.push(p);
        }
        path.reverse();
        let ids: Vec<u32> = path.iter().map(|&r| tree[r]).collect();
        let mut alone = base.clone();
        let want = model.run(&mut alone, &ids, false).logits;
        assert_eq!(bits(logits), bits(&want), "row {row}");

        let mut kept = state.clone();
        model.rollback_rows(&mut kept, &path);
        let next = tokens[0];
        assert_eq!(
            bits(&model.forward(&mut kept, next)),
            bits(&model.forward(&mut alone, next)),
            "after keeping {path:?}"
        );
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn speculative_greedy_is_plain_greedy() {
    let file = open();
    let model = kinetic_models::load(&file).unwrap();
    let prompt = prompt(model.n_vocab());
    let n = 96;
    let want = plain(&model, &prompt, n);
    assert_eq!(
        speculative(
            &model,
            Box::new(Lookup::default()),
            f32::INFINITY,
            &prompt,
            n
        ),
        want,
        "chains"
    );
    let tree = Ensemble::new(vec![
        Box::new(Lookup::default()) as Box<dyn Drafter<Model>>,
        Box::new(SessionIndex::default()),
    ]);
    // A free extra row makes every branching draft pay as a tree.
    assert_eq!(
        speculative(&model, Box::new(tree), 0.0, &prompt, n),
        want,
        "trees"
    );
}
