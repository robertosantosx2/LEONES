mod common;
use rusting_strata::{gguf::Gguf, model::{Model, State}, ops, tokenizer::Tokenizer};

#[test]
fn greedy_continuation_is_sane() {
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let ids = tok.encode("The capital of France is").unwrap();
    let mut st = State::new(&m.cfg);
    let mut logits = vec![];
    let t0 = std::time::Instant::now();
    for &t in &ids { logits = m.step(&mut st, t); }
    let next = ops::argmax(&logits) as u32;
    eprintln!("{} tokens in {:?}; next = {next} {:?}", ids.len(), t0.elapsed(), tok.decode(&[next]).unwrap());
    assert_eq!(tok.decode(&[next]).unwrap().trim(), "Paris");
}

/// MTP draft acceptance on the CPU reference: the nextn block's greedy draft for position p + 2 against the main
/// model's greedy token over 24 generated tokens. (#19: 24/25; feeding the post-output_norm state instead gave the same.)
#[test]
#[ignore]
fn mtp_draft_acceptance() {
    use rusting_strata::model::Mtp;
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let mut ids = tok.encode("Write a short story about a dragon.").unwrap();
    let n_prompt = ids.len();
    let (mut st, mut mtp, mut drafts) = (State::new(&m.cfg), Mtp::default(), vec![]);
    for i in 0..n_prompt + 24 {
        let (logits, x) = m.step_h(&mut st, ids[i]);
        if i + 1 == ids.len() { ids.push(ops::argmax(&logits) as u32); }
        drafts.push(ops::argmax(&m.mtp_step(&mut mtp, &x, ids[i + 1]).0) as u32);
    }
    // drafts[p] predicts ids[p + 2]; score generated tokens only.
    let hits: Vec<bool> = (n_prompt - 2..drafts.len() - 1).map(|p| drafts[p] == ids[p + 2]).collect();
    let n_ok = hits.iter().filter(|&&b| b).count();
    eprintln!("MTP acceptance {n_ok}/{} on {:?}", hits.len(), tok.decode(&ids[n_prompt..]).unwrap());
    assert!(n_ok * 10 >= hits.len() * 6, "MTP acceptance {n_ok}/{}", hits.len());
}

const QWEN4EXP: &str = "/mnt/ollama/qwen4exp/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf";

/// PLE n-gram hash against original Strata's oracle (src/kernels/ple_oracle_vectors.inc, case 0 "window
/// direction": each token with its own synthetic predecessors, oldest first).
#[test]
fn qwen4exp_ple_rows() {
    let p = std::path::Path::new(QWEN4EXP);
    if !p.exists() { return }
    let g = Gguf::open(p).unwrap();
    let m = Model::load(&g).unwrap();
    let mut st = State::new(&m.cfg);
    let case = [(11, [-1, -1]), (22, [11, -1]), (33, [22, 11]), (44, [33, 22])];
    let rows: Vec<u64> = case.iter().flat_map(|&(t, [old, new])| { st.ple_prev = [new, old]; m.ple_rows(&mut st.ple_prev, t) }).collect();
    assert_eq!(&rows[..16], &[13555483, 24877159, 54278900, 63631058, 98394898, 117447587, 136774765, 157274238,
        173487882, 192109366, 213364329, 236577563, 258758149, 262164274, 283572184, 312653920]);
    assert_eq!(&rows[48..], &[12721672, 27113445, 44309803, 60385209, 97021817, 115900810, 134219364, 151977589,
        161183764, 181257609, 201344488, 221596875, 241635416, 261674107, 281687144, 301751935]);
}

#[test]
fn qwen4exp_greedy_paris() {
    let p = std::path::Path::new(QWEN4EXP);
    if !p.exists() { return }
    let g = Gguf::open(p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let mut st = State::new(&m.cfg);
    let mut logits = vec![];
    for t in tok.encode("The capital of France is").unwrap() { logits = m.step(&mut st, t); }
    assert_eq!(tok.decode(&[ops::argmax(&logits) as u32]).unwrap().trim(), "Paris");
}

/// QSA sparse attention with top_k lowered to 8 cells (2 pooled blocks) so a short prompt runs sparse: the
/// log-probabilities of the next token, teacher-forced, against llama.cpp (`--override-kv
/// qwen4exp.attention.indexer.top_k=int:8`, CUDA, -cmoe). The block scores are close, so a rounding difference can
/// flip a pick: the bound is on the mean error (0.023 here). Dense attention is 0.07 off on average from llama.cpp's
/// sparse run (step 1: -0.118, step 6 picks token 61366), while our dense run is within 0.01 of llama.cpp's dense one.
#[test]
fn qwen4exp_qsa_matches_llama() {
    let p = std::path::Path::new(QWEN4EXP);
    if !p.exists() { return }
    let g = Gguf::open(p).unwrap();
    let mut m = Model::load(&g).unwrap();
    m.cfg.idx_top_k = 8;
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let ids = tok.encode("The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. \
        Once upon a time, in a small village").unwrap();
    assert_eq!(ids.len(), 29);
    let want: [(u32, f32); 12] = [(85624, -0.179), (1881, -0.198), (19484, -0.395), (33002, -0.076), (321, -0.602),
        (264, -0.573), (51924, -0.914), (14367, -0.006), (11, -0.012), (1017, -0.337), (11815, -0.018), (264, -0.31)];
    let mut st = State::new(&m.cfg);
    let mut logits = vec![];
    for &t in &ids { logits = m.step(&mut st, t); }
    let mut err = 0f32;
    for (i, &(t, lp)) in want.iter().enumerate() {
        let mx = logits.iter().fold(f32::MIN, |a, &b| a.max(b));
        let lse = mx + logits.iter().map(|&x| (x - mx).exp()).sum::<f32>().ln();
        let got = logits[t as usize] - lse;
        eprintln!("step {i}: token {t} logprob {got:.3} (llama.cpp {lp}), argmax {}", ops::argmax(&logits));
        assert!((got - lp).abs() < 0.1, "step {i}: {got} vs {lp}");
        err += (got - lp).abs() / want.len() as f32;
        logits = m.step(&mut st, t);
    }
    assert!(err < 0.04, "mean |dlogprob| {err}");
}
