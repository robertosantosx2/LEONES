//! Gated by STRATA_DS_MODEL (path to shard 1 of DeepSeek-V4.1-Flash). Skips when unset. About 30 s on 12 cores.
use rusting_strata::{deepseek::forward::DsModel, gguf::Gguf, tokenizer::Tokenizer};

#[test]
fn first_token_after_france_prompt_is_paris() {
    let Ok(p) = std::env::var("STRATA_DS_MODEL") else { eprintln!("STRATA_DS_MODEL unset, skipping"); return };
    let g = Gguf::open(std::path::Path::new(&p)).unwrap();
    let ids = Tokenizer::from_gguf(&g).unwrap().encode("The capital of France is").unwrap();
    assert_eq!(ids, [671, 6102, 294, 8760, 344]);
    let mut m = DsModel::new(&g).unwrap();
    let mut logits = vec![];
    for &t in &ids { logits = m.step(t); }
    let top = logits.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0;
    assert_eq!(top, 11111, "llama.cpp greedy picks ' Paris' (11111)");
}
