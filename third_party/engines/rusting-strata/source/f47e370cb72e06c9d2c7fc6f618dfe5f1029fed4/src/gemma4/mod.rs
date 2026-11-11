//! Gemma 4 (26B-A4B): sliding-window + full attention, dense FFN beside 128 routed experts, final logit softcapping.
//! CPU reference forward mirroring llama.cpp `gemma4.cpp`; matvecs go to the GPU when STRATA_DS_GPU is set (see `gpu_defaults`).
use crate::gguf::Gguf;
use anyhow::{Context, ensure};

pub mod forward;

pub struct Gemma4Config {
    pub n_layer: usize,
    pub n_embd: usize,
    pub n_head: usize,
    pub n_vocab: usize,
    pub n_ff: usize,
    pub n_expert: usize,
    pub n_used: usize,
    pub n_ff_exp: usize,
    pub eps: f32,
    pub softcap: f32,
    pub window: usize,
    pub n_ctx_train: usize,
    /// per layer: sliding-window layer?
    pub swa: Vec<bool>,
    pub n_kv: Vec<usize>,
    pub hd_swa: usize,
    pub hd_full: usize,
    pub base_swa: f32,
    pub base_full: f32,
}

impl Gemma4Config {
    pub fn from_gguf(g: &Gguf) -> anyhow::Result<Gemma4Config> {
        let arch = g.get("general.architecture")?.as_str().unwrap_or("");
        ensure!(arch == "gemma4", "architecture '{arch}' is not gemma4");
        let k = |s: &str| format!("gemma4.{s}");
        let u = |s: &str| -> anyhow::Result<usize> { Ok(g.get(&k(s))?.as_u64().with_context(|| k(s))? as usize) };
        let f = |s: &str| -> anyhow::Result<f32> { g.get(&k(s))?.as_f32().with_context(|| k(s)) };
        let arr = |s: &str| -> anyhow::Result<Vec<usize>> {
            g.get(&k(s))?.as_arr().with_context(|| k(s))?.iter().map(|v| v.as_u64().map(|x| x as usize).with_context(|| k(s))).collect()
        };
        let n_layer = u("block_count")?;
        let swa: Vec<bool> = arr("attention.sliding_window_pattern")?.into_iter().map(|b| b != 0).collect();
        let n_kv = arr("attention.head_count_kv")?;
        ensure!(swa.len() == n_layer && n_kv.len() == n_layer, "per-layer arrays do not match block_count");
        ensure!(u("attention.shared_kv_layers").unwrap_or(0) == 0, "shared-KV layers (E2B/E4B) are not supported");
        ensure!(u("embedding_length_per_layer_input").unwrap_or(0) == 0, "per-layer embeddings (E2B/E4B) are not supported");
        let emb = g.tensors.get("token_embd.weight").context("missing token_embd.weight")?;
        Ok(Gemma4Config {
            n_layer,
            n_embd: u("embedding_length")?,
            n_head: u("attention.head_count")?,
            n_vocab: emb.dims[1] as usize,
            n_ff: u("feed_forward_length")?,
            n_expert: u("expert_count")?,
            n_used: u("expert_used_count")?,
            n_ff_exp: u("expert_feed_forward_length")?,
            eps: f("attention.layer_norm_rms_epsilon")?,
            softcap: f("final_logit_softcapping").unwrap_or(0.0),
            window: u("attention.sliding_window")?,
            n_ctx_train: u("context_length")?,
            swa,
            n_kv,
            hd_swa: u("attention.key_length_swa")?,
            hd_full: u("attention.key_length")?,
            base_swa: f("rope.freq_base_swa")?,
            base_full: f("rope.freq_base")?,
        })
    }
    pub fn hd(&self, il: usize) -> usize { if self.swa[il] { self.hd_swa } else { self.hd_full } }
}

/// Gemma 4 chat template for plain text messages: `<bos>` is added by the caller. Roles: system, user, assistant (rendered as `model`).
pub fn chat_prompt(msgs: &[(&str, &str)]) -> String {
    let mut s = String::new();
    for (role, text) in msgs {
        let r = if *role == "assistant" { "model" } else { role };
        s.push_str(&format!("<|turn>{r}\n{}<turn|>\n", text.trim()));
    }
    s.push_str("<|turn>model\n");
    s
}

fn gpu_defaults() {
    if std::env::var_os("STRATA_G4_CPU").is_some() { return; }
    for (k, v) in [("STRATA_DS_GPU", "1"), ("STRATA_DS_GPU_EXPERTS", "11"), ("STRATA_DS_NOEVICT", "1")] {
        if std::env::var_os(k).is_none() { unsafe { std::env::set_var(k, v) } }
    }
}

/// `rustingstrata generate` for gemma4: raw prompt (BOS prepended, no template), greedy.
/// STRATA_G4_FORCE=<file of comma-separated ids> teacher-forces those tokens, STRATA_G4_TOP5 prints top-5 log-probs per step.
pub fn generate(g: &Gguf, prompt: &str, n: usize) -> anyhow::Result<()> {
    use std::io::Write;
    gpu_defaults();
    let tok = crate::tokenizer::Tokenizer::from_gguf(g)?;
    let mut m = forward::Gemma4Model::new(g)?;
    let eos = tok.eos_ids();
    let mut ids = vec![2u32];
    ids.extend(tok.encode(prompt)?);
    if std::env::var_os("STRATA_G4_TRACE").is_some() { eprintln!("prompt ids {ids:?}"); }
    let mut logits = m.prefill(&ids);
    forward::PROF.iter().for_each(|a| a.store(0, std::sync::atomic::Ordering::Relaxed));
    let t_dec = std::time::Instant::now();
    let (mut out, mut shown) = (vec![], 0);
    let forced: Vec<u32> = std::env::var("STRATA_G4_FORCE").ok().and_then(|p| std::fs::read_to_string(p).ok()).map(|t| t.split(',').filter_map(|x| x.trim().parse().ok()).collect()).unwrap_or_default();
    for i in 0..n {
        let mut next = logits.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0 as u32;
        if std::env::var_os("STRATA_G4_TOP5").is_some() {
            let mx = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let lz = mx as f64 + logits.iter().map(|&l| ((l - mx) as f64).exp()).sum::<f64>().ln();
            let mut idx: Vec<usize> = (0..logits.len()).collect();
            idx.sort_by(|&a, &b| logits[b].partial_cmp(&logits[a]).unwrap());
            let t: Vec<String> = idx[..5].iter().map(|&k| format!("{k}:{:.4}", logits[k] as f64 - lz)).collect();
            eprintln!("TOP5 {i} {}", t.join(" "));
        }
        if let Some(&f) = forced.get(i) { next = f; }
        if eos.contains(&next) { break; }
        out.push(next);
        let s = tok.decode(&out)?;
        if !s.ends_with('\u{FFFD}') && s.len() > shown && s.is_char_boundary(shown) {
            print!("{}", &s[shown..]);
            std::io::stdout().flush()?;
            shown = s.len();
        }
        if i + 1 < n { logits = m.step(next); }
    }
    println!();
    if std::env::var_os("STRATA_G4_PROF").is_some() { let p: Vec<f64> = forward::PROF.iter().map(|a| a.load(std::sync::atomic::Ordering::Relaxed) as f64 / 1e6).collect(); eprintln!("PROF decode {:.1} ms/token over {n} tokens", t_dec.elapsed().as_secs_f64() * 1e3 / n as f64); eprintln!("PROF ms attn={:.0} ffn(total)={:.0} head={:.0} prefetch={:.0} gpu_exp={:.0} cpu_exp={:.0}", p[0], p[1], p[2], p[3], p[4], p[5]); }
    Ok(())
}
