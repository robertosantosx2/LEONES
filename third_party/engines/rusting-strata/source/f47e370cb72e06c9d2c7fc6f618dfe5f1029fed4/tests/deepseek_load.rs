//! Gated by STRATA_DS_MODEL (path to shard 1 of DeepSeek-V4.1-Flash). Skips when unset.
use rusting_strata::{deepseek::DsConfig, gguf::Gguf};

#[test]
fn deepseek_config_and_tensors() {
    let Ok(p) = std::env::var("STRATA_DS_MODEL") else { eprintln!("STRATA_DS_MODEL unset, skipping"); return };
    let g = Gguf::open(std::path::Path::new(&p)).unwrap();
    let c = DsConfig::from_gguf(&g).unwrap();
    assert_eq!((c.n_layer, c.n_expert, c.n_used), (40, 384, 6));
    c.validate(&g).unwrap();
}
