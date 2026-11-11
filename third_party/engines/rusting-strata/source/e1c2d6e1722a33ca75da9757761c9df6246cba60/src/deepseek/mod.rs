//! DeepSeek-V4.1-Flash (GGUF arch `deepseek41`): hyperparameters and tensor-table validation.
//! Mirrors llama.cpp `llama_model_deepseek41::load_arch_hparams` / `load_arch_tensors`.

pub mod chat;
pub mod forward;
pub mod mat;
pub mod ops;

use crate::gguf::Gguf;
use anyhow::{Context, bail, ensure};

/// How a layer attends: sliding window only, or window plus compressed rows (CSA: ratio code 2, HCA: ratio code 1).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AttnKind { Window, Csa, Hca }

#[derive(Clone, Debug)]
pub struct DsConfig {
    pub n_layer: usize,
    pub n_embd: usize,
    pub n_head: usize,
    /// Per-head width (K = V = 512), of which the last `n_rot` carry RoPE.
    pub head_dim: usize,
    pub n_rot: usize,
    pub q_lora: usize,
    pub o_groups: usize,
    pub o_lora: usize,
    pub n_vocab: usize,
    pub eps: f32,
    pub window: usize,
    pub hc_n: usize,
    pub hc_eps: f32,
    pub hc_iters: usize,
    pub n_expert: usize,
    pub n_used: usize,
    pub n_ff_exp: usize,
    pub n_shared: usize,
    pub gating_func: u32,
    pub weights_norm: bool,
    pub weights_scale: f32,
    pub clamp_exp: Vec<f32>,
    pub clamp_shexp: Vec<f32>,
    pub rope_base: f32,
    pub compress_rope_base: f32,
    pub yarn_factor: f32,
    pub yarn_orig_ctx: usize,
    pub yarn_beta_fast: f32,
    pub yarn_beta_slow: f32,
    pub attn: Vec<AttnKind>,
    /// Layer whose compressed KV rows this layer reads (-1 = none).
    pub kv_src: Vec<i32>,
    /// Layer whose indexer top-k this layer reads (-1 = none).
    pub topk_src: Vec<i32>,
    pub idx_n_head: usize,
    pub idx_head_dim: usize,
    pub idx_top_k: usize,
    pub cand_src: i32,
    pub cand_block: usize,
    pub cand_top_blocks: usize,
    pub engram: Option<EngramConfig>,
}

#[derive(Clone, Debug)]
pub struct EngramConfig {
    /// Layers that have an Engram block, ascending.
    pub layers: Vec<usize>,
    pub ngram: usize,
    pub heads_per_ngram: usize,
    pub head_dim: usize,
    /// Per Engram layer, `ngram` hash multipliers.
    pub multipliers: Vec<u64>,
    /// Per Engram layer, `(ngram - 1) * heads_per_ngram` row offsets and bucket counts.
    pub offsets: Vec<u64>,
    pub primes: Vec<u64>,
    pub pad_id: usize,
    pub token_map: Vec<i32>,
}

impl DsConfig {
    pub fn from_gguf(g: &Gguf) -> anyhow::Result<DsConfig> {
        let arch = g.get("general.architecture")?.as_str().unwrap_or("");
        ensure!(arch == "deepseek41", "architecture '{arch}' is not deepseek41");
        let k = |s: &str| format!("deepseek41.{s}");
        let u = |s: &str| -> anyhow::Result<usize> { Ok(g.get(&k(s))?.as_u64().with_context(|| k(s))? as usize) };
        let f = |s: &str| -> anyhow::Result<f32> { g.get(&k(s))?.as_f32().with_context(|| k(s)) };
        let opt_u = |s: &str| g.meta.get(&k(s)).and_then(|v| v.as_u64()).unwrap_or(0) as usize;
        let arr_u = |s: &str| -> anyhow::Result<Vec<u64>> {
            g.get(&k(s))?.as_arr().with_context(|| k(s))?.iter().map(|v| v.as_u64().with_context(|| k(s))).collect()
        };
        let arr_f = |s: &str| -> anyhow::Result<Vec<f32>> {
            g.get(&k(s))?.as_arr().with_context(|| k(s))?.iter().map(|v| v.as_f32().with_context(|| k(s))).collect()
        };

        let n_layer = u("block_count")?;
        let ratios = arr_u("attention.compress_ratios")?;
        ensure!(ratios.len() >= n_layer, "compress_ratios has {} entries for {n_layer} layers", ratios.len());
        let kv_set: Vec<usize> = arr_u("attention.kv_source_layers")?.into_iter().map(|v| v as usize).collect();
        let idx_set: Vec<usize> = arr_u("attention.indexer.source_layers")?.into_iter().map(|v| v as usize).collect();
        ensure!(kv_set.iter().chain(&idx_set).all(|&l| l < n_layer), "kv/index source layer out of range");

        // Each compressed layer reads the KV rows / top-k of the latest source layer at or before it.
        let (mut attn, mut kv_src, mut topk_src) = (vec![], vec![-1i32; n_layer], vec![-1i32; n_layer]);
        let (mut last_kv, mut last_idx) = (-1i32, -1i32);
        for il in 0..n_layer {
            let r = ratios[il];
            let (is_kv, is_idx) = (kv_set.contains(&il), idx_set.contains(&il));
            if (is_kv || is_idx) && r == 0 { bail!("source layer {il} has compress ratio 0"); }
            if is_kv { last_kv = il as i32; }
            if is_idx { last_idx = il as i32; }
            attn.push(match r { 0 => AttnKind::Window, 1 => AttnKind::Hca, 2 => AttnKind::Csa, _ => bail!("layer {il}: compress ratio code {r}") });
            if r == 0 { continue; }
            ensure!(last_kv >= 0 && last_idx >= last_kv && ratios[last_kv as usize] == r && ratios[last_idx as usize] == r,
                "layer {il}: ratio {r} without a matching kv/index source");
            kv_src[il] = last_kv;
            topk_src[il] = last_idx;
        }

        let cand_src = g.meta.get(&k("attention.indexer.candidate_source_layer")).and_then(|v| v.as_u64().map(|x| x as i32)).unwrap_or(-1);
        let cand_src = match g.meta.get(&k("attention.indexer.candidate_source_layer")) {
            Some(crate::gguf::Value::I32(v)) => *v,
            _ => cand_src,
        };

        let engram = if g.meta.contains_key(&k("ple.layers")) {
            let layers: Vec<usize> = arr_u("ple.layers")?.into_iter().map(|v| v as usize).collect();
            let (ngram, hpn) = (u("ple.ngram_size")?, u("ple.heads_per_ngram")?);
            let n_cols = (ngram - 1) * hpn;
            let (mult, offsets, primes) = (arr_u("ple.layer_multipliers")?, arr_u("ple.head_offsets")?, arr_u("ple.head_vocab_sizes")?);
            ensure!(mult.len() == layers.len() * ngram && offsets.len() == layers.len() * n_cols && primes.len() == offsets.len(),
                "engram metadata is inconsistent");
            let token_map: Vec<i32> = g.get(&k("engram.token_map"))?.as_arr().context("engram.token_map")?
                .iter().map(|v| v.as_u64().map(|x| x as i32).or(if let crate::gguf::Value::I32(x) = v { Some(*x) } else { None }).context("token_map"))
                .collect::<anyhow::Result<_>>()?;
            let pad_id = u("engram.pad_token_id")?;
            ensure!(pad_id < token_map.len() && layers.iter().all(|&l| l < n_layer) && layers.windows(2).all(|w| w[0] < w[1]),
                "engram layers or pad token out of range");
            Some(EngramConfig { layers, ngram, heads_per_ngram: hpn, head_dim: u("embedding_length_per_layer_input")?,
                multipliers: mult, offsets, primes, pad_id, token_map })
        } else { None };

        let emb = g.tensors.get("token_embd.weight").context("missing token_embd.weight")?;
        let c = DsConfig {
            n_layer,
            n_embd: u("embedding_length")?,
            n_head: u("attention.head_count")?,
            head_dim: u("attention.key_length")?,
            n_rot: u("rope.dimension_count")?,
            q_lora: u("attention.q_lora_rank")?,
            o_groups: u("attention.output_group_count")?,
            o_lora: u("attention.output_lora_rank")?,
            n_vocab: emb.dims[1] as usize,
            eps: f("attention.layer_norm_rms_epsilon")?,
            window: u("attention.sliding_window")?,
            hc_n: u("hyper_connection.count")?,
            hc_eps: f("hyper_connection.epsilon")?,
            hc_iters: u("hyper_connection.sinkhorn_iterations")?,
            n_expert: u("expert_count")?,
            n_used: u("expert_used_count")?,
            n_ff_exp: u("expert_feed_forward_length")?,
            n_shared: u("expert_shared_count")?,
            gating_func: u("expert_gating_func")? as u32,
            weights_norm: g.get(&k("expert_weights_norm"))?.as_u64().unwrap_or(0) != 0,
            weights_scale: f("expert_weights_scale")?,
            clamp_exp: arr_f("swiglu_clamp_exp")?,
            clamp_shexp: arr_f("swiglu_clamp_shexp")?,
            rope_base: f("rope.freq_base")?,
            compress_rope_base: f("attention.compress_rope_freq_base")?,
            yarn_factor: f("rope.scaling.factor")?,
            yarn_orig_ctx: u("rope.scaling.original_context_length")?,
            yarn_beta_fast: f("rope.scaling.yarn_beta_fast")?,
            yarn_beta_slow: f("rope.scaling.yarn_beta_slow")?,
            attn, kv_src, topk_src,
            idx_n_head: u("attention.indexer.head_count")?,
            idx_head_dim: u("attention.indexer.key_length")?,
            idx_top_k: u("attention.indexer.top_k")?,
            cand_src,
            cand_block: opt_u("attention.indexer.candidate_block_size"),
            cand_top_blocks: opt_u("attention.indexer.candidate_top_k_blocks"),
            engram,
        };
        ensure!(c.hc_n == 4, "only 4 hyper-connection streams are supported");
        ensure!(c.clamp_exp.len() >= n_layer && c.clamp_shexp.len() >= n_layer, "swiglu clamp arrays too short");
        ensure!(c.n_head % c.o_groups == 0 && c.idx_top_k > 0, "bad attention dimensions");
        Ok(c)
    }

    /// Index of this layer among the Engram layers, if it has an Engram block.
    pub fn engram_index(&self, il: usize) -> Option<usize> {
        self.engram.as_ref()?.layers.iter().position(|&l| l == il)
    }

    /// Every tensor of the model with its expected dims (GGUF order: fastest first), as llama.cpp creates them.
    pub fn expected_tensors(&self) -> Vec<(String, Vec<u64>)> {
        let (e, h, nh, hd) = (self.n_embd as u64, self.hc_n as u64, self.n_head as u64, self.head_dim as u64);
        let (ql, og, ol, ff, ne) = (self.q_lora as u64, self.o_groups as u64, self.o_lora as u64, self.n_ff_exp as u64, self.n_expert as u64);
        let mut v: Vec<(String, Vec<u64>)> = vec![
            ("token_embd.weight".into(), vec![e, self.n_vocab as u64]),
            ("output_norm.weight".into(), vec![e]),
            ("output.weight".into(), vec![e, self.n_vocab as u64]),
        ];
        if let Some(en) = &self.engram {
            let rows = en.offsets.iter().zip(&en.primes).map(|(o, p)| o + p).max().unwrap_or(0);
            v.push(("per_layer_token_embd.weight".into(), vec![en.head_dim as u64, rows])); // actual file may have more rows
        }
        let (ni, nih) = (self.idx_head_dim as u64, self.idx_n_head as u64);
        let mix = (2 + h) * h;
        for il in 0..self.n_layer {
            let b = |n: &str| format!("blk.{il}.{n}");
            let mut t = |n: &str, d: Vec<u64>| v.push((b(n), d));
            t("attn_norm.weight", vec![e]);
            t("attn_sinks.weight", vec![nh]);
            t("attn_q_a.weight", vec![e, ql]);
            t("attn_q_a_norm.weight", vec![ql]);
            t("attn_q_b.weight", vec![ql, nh * hd]);
            t("attn_kv.weight", vec![e, hd]);
            t("attn_kv_a_norm.weight", vec![hd]);
            t("attn_output_a.weight", vec![nh * hd / og, ol * og]);
            t("attn_output_b.weight", vec![og * ol, e]);
            for s in ["attn", "ffn"] {
                t(&format!("hc_{s}_fn.weight"), vec![h * e, mix]);
                t(&format!("hc_{s}_base.weight"), vec![mix]);
                t(&format!("hc_{s}_scale.weight"), vec![3]);
            }
            if self.kv_src[il] == il as i32 {
                t("attn_compressor_kv.weight", vec![e, hd]);
                t("attn_compressor_norm.weight", vec![hd]);
                if self.attn[il] == AttnKind::Csa { t("attn_compressor_gate.weight", vec![e, hd]); }
                t("indexer.attn_k.weight", vec![hd, ni]);
                t("indexer.k_norm.weight", vec![ni]);
            }
            if self.topk_src[il] == il as i32 {
                t("indexer.attn_q_b.weight", vec![ql, nih * ni]);
                t("indexer.proj.weight", vec![e, nih]);
            }
            if let (Some(_), Some(en)) = (self.engram_index(il), &self.engram) {
                t("engram_kv.weight", vec![en.heads_per_ngram as u64 * (en.ngram as u64 - 1) * en.head_dim as u64, e * (h + 1)]);
                t("engram_gate.weight", vec![e, h]);
            }
            t("ffn_gate_inp.weight", vec![e, ne]);
            t("exp_probs_b.bias", vec![ne]);
            t("ffn_norm.weight", vec![e]);
            t("ffn_gate_exps.weight", vec![e, ff, ne]);
            t("ffn_down_exps.weight", vec![ff, e, ne]);
            t("ffn_up_exps.weight", vec![e, ff, ne]);
            let fs = ff * self.n_shared as u64;
            t("ffn_gate_shexp.weight", vec![e, fs]);
            t("ffn_down_shexp.weight", vec![fs, e]);
            t("ffn_up_shexp.weight", vec![e, fs]);
        }
        v
    }

    /// Check every expected tensor exists with the expected dims and a supported quant type.
    pub fn validate(&self, g: &Gguf) -> anyhow::Result<()> {
        let mut errs = vec![];
        for (name, dims) in self.expected_tensors() {
            match g.tensors.get(&name) {
                None => errs.push(format!("missing tensor {name}")),
                Some(t) => {
                    // attn_output_a is stored 2-D [4096, 8192] (llama.cpp reshapes it to [4096, 1024, 8]); the Engram table only needs enough rows.
                    let ok = if name == "per_layer_token_embd.weight" { t.dims[0] == dims[0] && t.dims[1] >= dims[1] } else { t.dims == dims };
                    if !ok { errs.push(format!("{name}: dims {:?}, expected {:?}", t.dims, dims)); }
                    if let Err(e) = crate::quant::GgmlType::from_u32(t.ty) { errs.push(format!("{name}: {e}")); }
                }
            }
        }
        ensure!(errs.is_empty(), "{} tensor problems:\n{}", errs.len(), errs.join("\n"));
        Ok(())
    }
}
