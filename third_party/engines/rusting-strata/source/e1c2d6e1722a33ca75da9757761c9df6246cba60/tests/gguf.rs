mod common;
use rusting_strata::{config::{LayerKind, ModelConfig}, gguf::Gguf, weights::{Tensor, Weights}};

fn w_str(b: &mut Vec<u8>, s: &str) {
    b.extend((s.len() as u64).to_le_bytes());
    b.extend(s.as_bytes());
}

#[test]
fn parses_synthetic_file() {
    let mut b = Vec::new();
    b.extend(b"GGUF");
    b.extend(3u32.to_le_bytes());
    b.extend(1u64.to_le_bytes()); // tensors
    b.extend(2u64.to_le_bytes()); // kv
    w_str(&mut b, "general.architecture");
    b.extend(8u32.to_le_bytes());
    w_str(&mut b, "qwen35moe");
    w_str(&mut b, "qwen35moe.block_count");
    b.extend(4u32.to_le_bytes());
    b.extend(41u32.to_le_bytes());
    w_str(&mut b, "t");
    b.extend(2u32.to_le_bytes());
    b.extend(4u64.to_le_bytes());
    b.extend(2u64.to_le_bytes());
    b.extend(0u32.to_le_bytes()); // F32
    b.extend(0u64.to_le_bytes()); // offset
    while b.len() % 32 != 0 { b.push(0); }
    for v in [1.0f32, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0] { b.extend(v.to_le_bytes()); }
    let p = std::env::temp_dir().join(format!("strata-{}-syn.gguf", std::process::id()));
    std::fs::write(&p, &b).unwrap();
    let g = Gguf::open(&p).unwrap();
    std::fs::remove_file(&p).ok();
    // Cut 4 bytes off the tensor data: a clean error, not a panic in `bytes`. A new path, since `g` maps the file.
    let cut = p.with_extension("cut.gguf");
    std::fs::write(&cut, &b[..b.len() - 4]).unwrap();
    let e = Gguf::open(&cut).err().unwrap();
    std::fs::remove_file(&cut).ok();
    assert!(format!("{e}").contains("GGUF truncated (tensor t "), "{e}");
    assert_eq!(g.get("general.architecture").unwrap().as_str(), Some("qwen35moe"));
    assert_eq!(g.get("qwen35moe.block_count").unwrap().as_u64(), Some(41));
    let t = &g.tensors["t"];
    assert_eq!(t.dims, vec![4, 2]);
    let bytes = g.bytes(t);
    assert_eq!(bytes.len(), 32);
    assert_eq!(f32::from_le_bytes(bytes[28..32].try_into().unwrap()), 8.0);
}

#[test]
fn real_file_config() {
    let Some(p) = common::model_path().filter(|p| common::is_default_model(p)) else { return };
    let g = Gguf::open(&p).unwrap();
    let c = ModelConfig::from_gguf(&g).unwrap();
    assert_eq!(c.arch, "qwen35moe");
    assert_eq!((c.n_layer, c.n_nextn, c.n_embd, c.n_head, c.n_head_kv, c.head_dim), (40, 1, 2048, 16, 2, 256));
    assert_eq!((c.n_expert, c.n_expert_used, c.n_ff_exp, c.n_ff_shexp), (256, 8, 512, 512));
    assert_eq!((c.ssm_d_inner, c.ssm_d_state, c.ssm_n_group, c.ssm_dt_rank, c.ssm_conv), (4096, 128, 16, 32, 4));
    assert_eq!((c.n_rot, c.n_vocab), (64, 248320));
    assert_eq!(&c.layers[..4], &[LayerKind::Delta, LayerKind::Delta, LayerKind::Delta, LayerKind::Attn]);
    assert!(c.q_gate && !c.k_interleave);
    // IQ3_XXS: 98 bytes per 256 elements; [512, 2048, 256].
    assert_eq!(g.bytes(&g.tensors["blk.0.ffn_down_exps.weight"]).len(), 2048 * 256 * 2 * 98);
}

/// Arch-table fields of whichever model STRATA_MODEL names; canonical tensor names resolve through the aliases.
#[test]
fn arch_table_fields() {
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let c = ModelConfig::from_gguf(&g).unwrap();
    let attn = c.layers.iter().filter(|&&k| k == LayerKind::Attn).count();
    assert_eq!(c.layers.len(), c.n_layer);
    match c.arch.as_str() {
        "qwen3" | "qwen3moe" => assert!(attn == c.n_layer && !c.q_gate && !c.k_interleave && c.ssm_dv() == 0),
        "qwen3next" => assert!(attn == c.n_layer / 4 && c.q_gate && c.k_interleave),
        _ => assert!(attn == c.n_layer / 4 && c.q_gate && !c.k_interleave),
    }
    let w = Weights::new(&g).unwrap();
    w.layer(0, "post_attention_norm.weight").unwrap();
    w.layer(c.n_layer - 1, "post_attention_norm.weight").unwrap();
}

/// qwen3next fuses beta and alpha in `ssm_ba`: per key head group, r = nv / nk beta rows, then r alpha rows.
#[test]
fn qwen3next_ssm_ba_split() {
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let c = ModelConfig::from_gguf(&g).unwrap();
    if c.arch != "qwen3next" { return; }
    let w = Weights::new(&g).unwrap();
    let (ba, b, a) = (w.layer(0, "ssm_ba.weight").unwrap(), w.layer(0, "ssm_beta.weight").unwrap(), w.layer(0, "ssm_alpha.weight").unwrap());
    assert_eq!((b.rows, a.rows, b.cols, a.cols), (c.ssm_dt_rank, c.ssm_dt_rank, ba.cols, ba.cols));
    let row = |t: &Tensor, i: usize| { let mut v = vec![0f32; t.cols]; t.row(i, &mut v); v };
    let r = c.ssm_dt_rank / c.ssm_n_group;
    for grp in 0..c.ssm_n_group {
        for j in 0..r {
            assert_eq!(row(&b, grp * r + j), row(&ba, grp * 2 * r + j), "beta group {grp} row {j}");
            assert_eq!(row(&a, grp * r + j), row(&ba, grp * 2 * r + r + j), "alpha group {grp} row {j}");
        }
    }
}

/// Minimal qwen3next file: u32 metadata (plus the rms epsilon) and F32 tensors.
fn qwen3next_syn(tag: &str, kv: &[(&str, u32)], tensors: &[(&str, [u64; 2])]) -> Gguf {
    let mut b = Vec::new();
    b.extend(b"GGUF");
    b.extend(3u32.to_le_bytes());
    b.extend((tensors.len() as u64).to_le_bytes());
    b.extend((kv.len() as u64 + 2).to_le_bytes());
    w_str(&mut b, "general.architecture");
    b.extend(8u32.to_le_bytes());
    w_str(&mut b, "qwen3next");
    w_str(&mut b, "qwen3next.attention.layer_norm_rms_epsilon");
    b.extend(6u32.to_le_bytes());
    b.extend(1e-6f32.to_le_bytes());
    for (k, v) in kv {
        w_str(&mut b, &format!("qwen3next.{k}"));
        b.extend(4u32.to_le_bytes());
        b.extend(v.to_le_bytes());
    }
    let mut off = 0u64;
    for (name, dims) in tensors {
        w_str(&mut b, name);
        b.extend(2u32.to_le_bytes());
        for d in dims { b.extend(d.to_le_bytes()); }
        b.extend(0u32.to_le_bytes()); // F32
        b.extend(off.to_le_bytes());
        off += (dims[0] * dims[1] * 4).next_multiple_of(32);
    }
    while b.len() % 32 != 0 { b.push(0); }
    b.resize(b.len() + off as usize, 0);
    let p = std::env::temp_dir().join(format!("strata-{}-{tag}.gguf", std::process::id()));
    std::fs::write(&p, &b).unwrap();
    let g = Gguf::open(&p).unwrap();
    std::fs::remove_file(&p).ok();
    g
}

/// Malformed DeltaNet metadata or a mis-sized `ssm_ba` is an error, not a divide by zero or an out of bounds kernel read.
#[test]
fn rejects_bad_ssm_dims() {
    let kv = |groups: u32| [("block_count", 4), ("embedding_length", 8), ("attention.head_count", 2), ("attention.head_count_kv", 1),
        ("ssm.inner_size", 8), ("ssm.state_size", 4), ("ssm.group_count", groups), ("ssm.time_step_rank", 4), ("ssm.conv_kernel", 4)];
    let emb = ("token_embd.weight", [8, 16]);
    for groups in [0, 3, 8] {
        let g = qwen3next_syn("ssm", &kv(groups), &[emb]);
        assert!(ModelConfig::from_gguf(&g).is_err(), "group_count {groups}");
    }
    let ok = qwen3next_syn("ssm-ok", &kv(2), &[emb, ("blk.0.ssm_ba.weight", [8, 8])]);
    Weights::new(&ok).unwrap();
    let bad = qwen3next_syn("ssm-ba", &kv(2), &[emb, ("blk.0.ssm_ba.weight", [8, 6])]);
    assert!(Weights::new(&bad).is_err());
}

/// One shard: `split.count` (u16) = 2 and one 4-float F32 tensor `name` holding `v`.
fn shard(name: &str, v: f32) -> Vec<u8> {
    let mut b = Vec::new();
    b.extend(b"GGUF");
    b.extend(3u32.to_le_bytes());
    b.extend(1u64.to_le_bytes());
    b.extend(1u64.to_le_bytes());
    w_str(&mut b, "split.count");
    b.extend(2u32.to_le_bytes());
    b.extend(2u16.to_le_bytes());
    w_str(&mut b, name);
    b.extend(1u32.to_le_bytes());
    b.extend(4u64.to_le_bytes());
    b.extend(0u32.to_le_bytes());
    b.extend(0u64.to_le_bytes());
    while b.len() % 32 != 0 { b.push(0); }
    for _ in 0..4 { b.extend(v.to_le_bytes()); }
    b
}

#[test]
fn opens_split_model() {
    let d = std::env::temp_dir().join(format!("strata-{}-split", std::process::id()));
    std::fs::create_dir_all(&d).unwrap();
    let (p1, p2) = (d.join("m-00001-of-00002.gguf"), d.join("m-00002-of-00002.gguf"));
    std::fs::write(&p1, shard("a", 1.5)).unwrap();
    std::fs::write(&p2, shard("b", 2.5)).unwrap();
    let g = Gguf::open(&p1).unwrap();
    let e = Gguf::open(&p2).err().unwrap();
    std::fs::remove_file(&p1).ok();
    std::fs::remove_file(&p2).ok();
    std::fs::remove_dir(&d).ok();
    assert!(format!("{e}").contains("open its first shard"), "{e}");
    for (n, v) in [("a", 1.5f32), ("b", 2.5)] {
        assert_eq!(f32::from_le_bytes(g.bytes(&g.tensors[n])[12..16].try_into().unwrap()), v, "{n}");
    }
}

#[test]
fn qwen4exp_config() {
    let p = std::path::Path::new("/mnt/ollama/qwen4exp/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf");
    if !p.exists() { return }
    let g = Gguf::open(p).unwrap();
    assert_eq!(g.tensors.len(), 1224); // both shards; shard 2 is the PLE table
    assert!(g.tensors.contains_key("per_layer_token_embd.weight"));
    let c = ModelConfig::from_gguf(&g).unwrap();
    assert_eq!((c.n_layer, c.n_embd, c.n_head, c.n_head_kv, c.head_dim, c.n_rot), (48, 2560, 24, 2, 256, 64));
    assert_eq!((c.n_expert, c.n_expert_used, c.n_ff_exp, c.n_ff_shexp), (512, 10, 640, 640));
    assert_eq!((c.ssm_d_inner, c.ssm_d_state, c.ssm_n_group, c.ssm_dt_rank), (6144, 128, 16, 48));
    assert_eq!((c.hc_n, c.hc_rank, c.n_embd_ple), (4, 320, 160));
    assert!(c.layers.iter().enumerate().all(|(i, &k)| (k == LayerKind::Attn) == (i % 4 == 3)));
    assert!(!c.k_interleave);
}

#[test]
fn malformed_metadata_must_not_panic() {
    let mut fixtures = Vec::new();
    let mut zero_alignment = Vec::new();
    zero_alignment.extend(b"GGUF");
    zero_alignment.extend(3u32.to_le_bytes());
    zero_alignment.extend(0u64.to_le_bytes());
    zero_alignment.extend(1u64.to_le_bytes());
    w_str(&mut zero_alignment, "general.alignment");
    zero_alignment.extend(4u32.to_le_bytes());
    zero_alignment.extend(0u32.to_le_bytes());
    fixtures.push(("zero-alignment", zero_alignment));

    let mut giant_key = Vec::new();
    giant_key.extend(b"GGUF");
    giant_key.extend(3u32.to_le_bytes());
    giant_key.extend(0u64.to_le_bytes());
    giant_key.extend(1u64.to_le_bytes());
    giant_key.extend(u64::MAX.to_le_bytes());
    fixtures.push(("oversized-key", giant_key));

    let mut giant_array = Vec::new();
    giant_array.extend(b"GGUF");
    giant_array.extend(3u32.to_le_bytes());
    giant_array.extend(0u64.to_le_bytes());
    giant_array.extend(1u64.to_le_bytes());
    w_str(&mut giant_array, "array");
    giant_array.extend(9u32.to_le_bytes());
    giant_array.extend(0u32.to_le_bytes());
    giant_array.extend(u64::MAX.to_le_bytes());
    fixtures.push(("oversized-array", giant_array));

    let mut failures = Vec::new();
    for (label, bytes) in fixtures {
        let path = std::env::temp_dir().join(format!("rustingstrata-{}-{label}.gguf", std::process::id()));
        std::fs::write(&path, bytes).unwrap();
        let outcome = std::panic::catch_unwind(|| Gguf::open(&path));
        std::fs::remove_file(&path).ok();
        match outcome {
            Err(_) => failures.push(format!("parser panicked on {label}")),
            Ok(Ok(_)) => failures.push(format!("parser accepted malformed {label}")),
            Ok(Err(_)) => {}
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("; "));
}
