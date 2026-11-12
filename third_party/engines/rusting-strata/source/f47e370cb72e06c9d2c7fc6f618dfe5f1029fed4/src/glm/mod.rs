//! GLM-5.3-Flash (GGUF arch `glm5-next`): hyperparameters and tensor-table validation.
//! Mirrors llama.cpp `src/models/glm5-next.cpp` (hparams and tensor creation).

pub mod forward;
use crate::chat::{Json, Msg};
use crate::gguf::Gguf;
use anyhow::{Context, ensure};

/// Token mixer of a layer: Kimi Delta Attention (linear) or DSA (MLA with a k-pool indexer).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LayerKind { Kda, Dsa }

#[derive(Clone, Debug)]
pub struct GlmConfig {
    /// All blocks in the file, including the trailing NextN (MTP) block.
    pub n_layer_file: usize,
    /// Blocks used for normal decoding (file blocks minus NextN blocks).
    pub n_layer: usize,
    pub n_embd: usize,
    pub n_head: usize,
    pub n_vocab: usize,
    pub n_ff: usize,
    pub n_dense: usize,
    pub eps: f32,
    pub kda_eps: f32,
    pub kind: Vec<LayerKind>,
    pub conv_k: usize,
    pub kda_head_dim: usize,
    pub gate_lower_bound: f32,
    pub q_lora: usize,
    pub kv_lora: usize,
    /// MLA per-head widths before absorption (k = v = 256).
    pub k_mla: usize,
    pub v_mla: usize,
    pub idx_n_head: usize,
    pub idx_head_dim: usize,
    pub idx_top_k: usize,
    /// Trained context (`glm5-next.context_length`), the default request limit.
    pub n_ctx_train: usize,
    pub kpool: usize,
    pub hc_n: usize,
    pub hc_eps: f32,
    pub hc_iters: usize,
    pub n_expert: usize,
    pub n_used: usize,
    pub n_ff_exp: usize,
    pub n_ff_shexp: usize,
    pub n_shared: usize,
    pub weights_norm: bool,
    pub weights_scale: f32,
    pub clamp_exp: Vec<f32>,
    pub clamp_shexp: Vec<f32>,
    pub n_nextn: usize,
}

impl GlmConfig {
    pub fn from_gguf(g: &Gguf) -> anyhow::Result<GlmConfig> {
        let arch = g.get("general.architecture")?.as_str().unwrap_or("");
        ensure!(arch == "glm5-next", "architecture '{arch}' is not glm5-next");
        let k = |s: &str| format!("glm5-next.{s}");
        let u = |s: &str| -> anyhow::Result<usize> { Ok(g.get(&k(s))?.as_u64().with_context(|| k(s))? as usize) };
        let f = |s: &str| -> anyhow::Result<f32> { g.get(&k(s))?.as_f32().with_context(|| k(s)) };
        let arr_f = |s: &str| -> anyhow::Result<Vec<f32>> {
            g.get(&k(s))?.as_arr().with_context(|| k(s))?.iter().map(|v| v.as_f32().with_context(|| k(s))).collect()
        };
        let n_layer_file = u("block_count")?;
        let n_nextn = u("nextn_predict_layers")?;
        ensure!(n_nextn <= n_layer_file, "nextn_predict_layers > block_count");
        let kv_heads: Vec<usize> = g.get(&k("attention.head_count_kv"))?.as_arr().context("head_count_kv")?
            .iter().map(|v| v.as_u64().context("head_count_kv entry")).collect::<anyhow::Result<Vec<_>>>()?
            .into_iter().map(|x| x as usize).collect();
        ensure!(kv_heads.len() >= n_layer_file, "head_count_kv has {} entries for {n_layer_file} layers", kv_heads.len());
        let kind = kv_heads.iter().take(n_layer_file).map(|&h| if h == 0 { LayerKind::Kda } else { LayerKind::Dsa }).collect();
        let emb = g.tensors.get("token_embd.weight").context("missing token_embd.weight")?;
        let c = GlmConfig {
            n_layer_file,
            n_layer: n_layer_file - n_nextn,
            n_embd: u("embedding_length")?,
            n_head: u("attention.head_count")?,
            n_vocab: emb.dims[1] as usize,
            n_ff: u("feed_forward_length")?,
            n_dense: u("leading_dense_block_count")?,
            eps: f("attention.layer_norm_rms_epsilon")?,
            kda_eps: f("attention.layer_norm_epsilon")?,
            kind,
            conv_k: u("ssm.conv_kernel")?,
            kda_head_dim: u("kda.head_dim")?,
            gate_lower_bound: f("kda.gate_lower_bound")?,
            q_lora: u("attention.q_lora_rank")?,
            kv_lora: u("attention.kv_lora_rank")?,
            k_mla: u("attention.key_length_mla")?,
            v_mla: u("attention.value_length_mla")?,
            idx_n_head: u("attention.indexer.head_count")?,
            idx_head_dim: u("attention.indexer.key_length")?,
            idx_top_k: u("attention.indexer.top_k")?,
            n_ctx_train: u("context_length")?,
            kpool: u("attention.indexer.kpool")?,
            hc_n: u("hyper_connection.count")?,
            hc_eps: f("hyper_connection.epsilon")?,
            hc_iters: u("hyper_connection.sinkhorn_iterations")?,
            n_expert: u("expert_count")?,
            n_used: u("expert_used_count")?,
            n_ff_exp: u("expert_feed_forward_length")?,
            n_ff_shexp: u("expert_shared_feed_forward_length")?,
            n_shared: u("expert_shared_count")?,
            weights_norm: g.get(&k("expert_weights_norm"))?.as_u64().unwrap_or(0) != 0,
            weights_scale: f("expert_weights_scale")?,
            clamp_exp: arr_f("swiglu_clamp_exp")?,
            clamp_shexp: arr_f("swiglu_clamp_shexp")?,
            n_nextn,
        };
        ensure!(u("expert_gating_func")? == 2, "only sigmoid expert gating (2) is supported");
        ensure!(c.hc_n == 4, "only 4 hyper-connection streams are supported");
        ensure!(c.n_shared == 1 && c.n_ff_shexp == c.n_ff_exp, "unexpected shared-expert shape");
        ensure!(c.n_head * c.kda_head_dim == 8192 && c.kda_head_dim == 128, "unexpected KDA dimensions");
        ensure!(c.clamp_exp.len() >= n_layer_file && c.clamp_shexp.len() >= n_layer_file, "swiglu clamp arrays too short");
        ensure!(c.n_dense <= c.n_layer, "leading_dense_block_count out of range");
        Ok(c)
    }

    pub fn n_kda(&self) -> usize { self.kind[..self.n_layer].iter().filter(|&&k| k == LayerKind::Kda).count() }
    pub fn n_dsa(&self) -> usize { self.n_layer - self.n_kda() }

    /// Every tensor of the model with its expected dims (GGUF order: fastest first), as llama.cpp creates them.
    pub fn expected_tensors(&self) -> Vec<(String, Vec<u64>)> {
        let (e, h, nh) = (self.n_embd as u64, self.hc_n as u64, self.n_head as u64);
        let (ff, ffe, ne) = (self.n_ff as u64, self.n_ff_exp as u64, self.n_expert as u64);
        let (ql, kl, kd) = (self.q_lora as u64, self.kv_lora as u64, self.k_mla as u64);
        let (vd, di) = (self.v_mla as u64, nh * self.kda_head_dim as u64);
        let (ni, nih, hd) = (self.idx_head_dim as u64, self.idx_n_head as u64, self.kda_head_dim as u64);
        let mix = (2 + h) * h;
        let mut v: Vec<(String, Vec<u64>)> = vec![
            ("token_embd.weight".into(), vec![e, self.n_vocab as u64]),
            ("output_norm.weight".into(), vec![e]),
            ("output.weight".into(), vec![e, self.n_vocab as u64]),
        ];
        for il in 0..self.n_layer_file {
            let b = |n: &str| format!("blk.{il}.{n}");
            let mut t = |n: &str, d: Vec<u64>| v.push((b(n), d));
            t("attn_norm.weight", vec![e]);
            t("ffn_norm.weight", vec![e]);
            for s in ["attn", "ffn"].into_iter().filter(|_| il < self.n_layer) { // the NextN block has no hyper-connections
                t(&format!("hc_{s}_fn.weight"), vec![h * e, mix]);
                t(&format!("hc_{s}_base.weight"), vec![mix]);
                t(&format!("hc_{s}_scale.weight"), vec![3]);
            }
            match self.kind[il] {
                LayerKind::Kda => {
                    t("attn_q.weight", vec![e, di]);
                    t("attn_k.weight", vec![e, di]);
                    t("attn_v.weight", vec![e, di]);
                    t("attn_output.weight", vec![di, e]);
                    t("ssm_a", vec![nh]);
                    t("ssm_beta.weight", vec![e, nh]);
                    for s in ["q", "k", "v"] { t(&format!("ssm_conv1d_{s}.weight"), vec![self.conv_k as u64, 1, di]); }
                    t("ssm_dt.bias", vec![di]);
                    t("ssm_f_a.weight", vec![e, hd]);
                    t("ssm_f_b.weight", vec![hd, di]);
                    t("ssm_g_a.weight", vec![e, hd]);
                    t("ssm_g_b.weight", vec![hd, di]);
                    t("ssm_norm.weight", vec![hd]);
                }
                LayerKind::Dsa => {
                    t("attn_q_a.weight", vec![e, ql]);
                    t("attn_q_a_norm.weight", vec![ql]);
                    t("attn_q_b.weight", vec![ql, nh * kd]);
                    t("attn_kv_a_mqa.weight", vec![e, kl]);
                    t("attn_kv_a_norm.weight", vec![kl]);
                    t("attn_k_b.weight", vec![kd, kl, nh]);
                    t("attn_v_b.weight", vec![kl, vd, nh]);
                    t("attn_output.weight", vec![nh * vd, e]);
                    t("indexer.attn_k.weight", vec![e, ni]);
                    t("indexer.attn_q_b.weight", vec![ql, nih * ni]);
                    t("indexer.k_norm.weight", vec![ni]);
                    t("indexer.k_norm.bias", vec![ni]);
                    t("indexer.proj.weight", vec![e, nih]);
                    t("indexer_compressor_ape.weight", vec![ni, self.kpool as u64]);
                    t("indexer_compressor_gate.weight", vec![e, ni]);
                }
            }
            if il < self.n_dense {
                t("ffn_gate.weight", vec![e, ff]);
                t("ffn_up.weight", vec![e, ff]);
                t("ffn_down.weight", vec![ff, e]);
            } else {
                t("ffn_gate_inp.weight", vec![e, ne]);
                t("exp_probs_b.bias", vec![ne]);
                t("ffn_gate_exps.weight", vec![e, ffe, ne]);
                t("ffn_up_exps.weight", vec![e, ffe, ne]);
                t("ffn_down_exps.weight", vec![ffe, e, ne]);
                let fs = ffe * self.n_shared as u64;
                t("ffn_gate_shexp.weight", vec![e, fs]);
                t("ffn_up_shexp.weight", vec![e, fs]);
                t("ffn_down_shexp.weight", vec![fs, e]);
            }
            if il >= self.n_layer {
                t("nextn.eh_proj.weight", vec![2 * e, e]);
                t("nextn.enorm.weight", vec![e]);
                t("nextn.hnorm.weight", vec![e]);
                t("nextn.shared_head_norm.weight", vec![e]);
            }
        }
        v
    }

    /// Check every expected tensor exists with the expected dims and a supported quant type, and nothing else is in the file.
    pub fn validate(&self, g: &Gguf) -> anyhow::Result<()> {
        let mut errs = vec![];
        let exp = self.expected_tensors();
        for (name, dims) in &exp {
            match g.tensors.get(name) {
                None => errs.push(format!("missing tensor {name}")),
                Some(t) => {
                    // Per-expert and 2-D conv tensors may carry trailing 1s; compare ignoring them.
                    let trim = |d: &[u64]| { let mut d = d.to_vec(); while d.len() > 1 && d.last() == Some(&1) { d.pop(); } d };
                    if trim(&t.dims) != trim(dims) { errs.push(format!("{name}: dims {:?}, expected {:?}", t.dims, dims)); }
                    if let Err(e) = crate::quant::GgmlType::from_u32(t.ty) { errs.push(format!("{name}: {e}")); }
                }
            }
        }
        if g.tensors.len() != exp.len() {
            let known: std::collections::HashSet<&str> = exp.iter().map(|(n, _)| n.as_str()).collect();
            for n in g.tensors.keys().filter(|n| !known.contains(n.as_str())) { errs.push(format!("unexpected tensor {n}")); }
        }
        ensure!(errs.is_empty(), "{} tensor problems:\n{}", errs.len(), errs.iter().take(40).cloned().collect::<Vec<_>>().join("\n"));
        Ok(())
    }
}

/// `rustingstrata generate` for glm5-next: raw prompt (no template), greedy, prints the continuation. GPU matvecs unless STRATA_GLM_CPU is set.
pub fn generate(g: &Gguf, prompt: &str, n: usize) -> anyhow::Result<()> {
    use std::io::Write;
    gpu_defaults();
    let tok = crate::tokenizer::Tokenizer::from_gguf(g)?;
    let mut m = forward::GlmModel::new(g)?;
    let eos = tok.eos_ids();
    let ids = tok.encode(prompt)?;
    if std::env::var_os("STRATA_GLM_TRACE").is_some() { eprintln!("prompt ids {ids:?}"); }
    let mut logits = m.prefill(&ids);
    let (mut out, mut shown) = (vec![], 0);
    // STRATA_GLM_FORCE=<file of comma-separated token ids>: teacher-force those tokens (compare top-5 per step with a reference run).
    let forced: Vec<u32> = std::env::var("STRATA_GLM_FORCE").ok().and_then(|p| std::fs::read_to_string(p).ok()).map(|t| t.split(',').filter_map(|x| x.trim().parse().ok()).collect()).unwrap_or_default();
    for i in 0..n {
        let mut next = logits.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0 as u32;
        if std::env::var_os("STRATA_GLM_TOP5").is_some() {
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
    Ok(())
}

/// GLM-5.3 chat template (default reasoning effort, thinking on). `msgs` = (role, content) with role system|user|assistant.
/// Matches llama.cpp `/apply-template` for plain text messages (no tools).
pub fn chat_prompt(msgs: &[(&str, &str)]) -> String {
    chat_prompt_tools(&msgs.iter().map(|(r, c)| Msg::new(r, c)).collect::<Vec<_>>(), &[])
}

/// The template with tools (from `chat::tool_def`), assistant `calls` and `tool` messages; matches llama.cpp
/// `/apply-template` (tools/glm_ref/tpl_tools.json).
// ponytail: tool results print in message order; the template re-sorts them by tool_call_id to the order of the calls.
pub fn chat_prompt_tools(msgs: &[Msg], tools: &[Json]) -> String {
    let mut s = String::from("[gMASK]<sop><|system|>Reasoning Effort: Max");
    if !tools.is_empty() {
        s += "<|system|>\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>";
        for t in tools { s += "\n"; s += &t.get("function").dump(); }
        s += "\n</tools>\n\nFor each function call, output the function name and arguments within the following XML format:\n<tool_call>{function-name}<arg_key>{arg-key-1}</arg_key><arg_value>{arg-value-1}</arg_value><arg_key>{arg-key-2}</arg_key><arg_value>{arg-value-2}</arg_value>...</tool_call>";
    }
    for (i, m) in msgs.iter().enumerate() {
        let c = m.content.as_str();
        match m.role.as_str() {
            "user" => s += &format!("<|user|>{c}"),
            "assistant" => {
                let (r, a) = match (&m.reasoning, c.split_once("</think>")) {
                    // earlier reasoning is kept (template default clear_thinking=false)
                    (Some(r), _) => (r.as_str(), c),
                    (None, Some((r, a))) => (r.rsplit("<think>").next().unwrap_or(r), a),
                    (None, None) => ("", c),
                };
                s += &format!("<|assistant|><think>{r}</think>{}", a.trim());
                for call in &m.calls {
                    s += &format!("<tool_call>{}", call.name);
                    if let Json::Obj(o) = &call.args {
                        for (k, v) in o { s += &format!("<arg_key>{k}</arg_key><arg_value>{}</arg_value>", v.as_str().map_or_else(|| v.dump(), String::from)); }
                    }
                    s += "</tool_call>";
                }
            }
            "tool" => {
                if i == 0 || msgs[i - 1].role != "tool" { s += "<|observation|>"; }
                s += &format!("<tool_response>{c}</tool_response>");
            }
            _ => s += &format!("<|system|>{c}"),
        }
    }
    s + "<|assistant|><think>"
}

/// Tool calls in a reply (after its think block): the text before them and each call's name and JSON arguments.
/// None when there is no call or one is malformed. A value is a string when the tool's schema says so, else JSON if
/// it parses, else a string.
fn parse_calls(text: &str, tools: &[Json]) -> Option<(String, Vec<(String, String)>)> {
    let from = text.rfind("</think>").map_or(0, |p| p + 8);
    let start = from + text[from..].find("<tool_call>")?;
    let (mut rest, mut calls) = (&text[start..], vec![]);
    while !rest.trim_start().is_empty() {
        let (inner, r) = rest.trim_start().strip_prefix("<tool_call>")?.split_once("</tool_call>")?;
        rest = r;
        let p = inner.find("<arg_key>").unwrap_or(inner.len());
        let (name, mut a) = (inner[..p].trim(), &inner[p..]);
        let props = tools.iter().map(|t| t.get("function")).find(|f| f.get("name").as_str() == Some(name)).map_or(&Json::Null, |f| f.get("parameters").get("properties"));
        let mut args = vec![];
        while let Some(x) = a.strip_prefix("<arg_key>") {
            let (k, x) = x.split_once("</arg_key>")?;
            let (v, x) = x.strip_prefix("<arg_value>")?.split_once("</arg_value>")?;
            a = x;
            let string = props.get(k).get("type").as_str() == Some("string");
            args.push((k.to_string(), if string { Json::Str(v.into()) } else { serde_json::from_str(v).unwrap_or_else(|_| Json::Str(v.into())) }));
        }
        if !a.is_empty() { return None; }
        calls.push((name.to_string(), Json::Obj(args).dump()));
    }
    Some((text[..start].trim_end().to_string(), calls))
}

/// Greedy decode up to `n` tokens from `logits`; `emit` gets each new text piece. Returns (ids, finish reason).
fn decode_greedy(m: &mut forward::GlmModel, tok: &crate::tokenizer::Tokenizer, eos: &[u32], mut logits: Vec<f32>, n: usize, emit: &mut dyn FnMut(&str) -> bool) -> (Vec<u32>, &'static str) {
    let (mut out, mut shown, mut done) = (vec![], 0, "length");
    for i in 0..n {
        let next = logits.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0 as u32;
        if eos.contains(&next) { done = "stop"; break; }
        out.push(next);
        let s = tok.decode(&out).unwrap_or_default();
        if !s.ends_with('\u{FFFD}') && s.len() > shown && s.is_char_boundary(shown) {
            let ok = emit(&s[shown..]);
            shown = s.len();
            if !ok { break; }
        }
        if i + 1 < n { logits = m.step(next); }
    }
    (out, done)
}

/// Stop ids: eos plus the end-of-turn / end-of-message tokens (<|user|>, <|observation|>) that llama.cpp treats as EOG.
fn stop_ids(g: &Gguf, tok: &crate::tokenizer::Tokenizer) -> Vec<u32> {
    let mut e = tok.eos_ids();
    for k in ["tokenizer.ggml.eot_token_id", "tokenizer.ggml.eom_token_id"] {
        if let Some(v) = g.meta.get(k).and_then(|v| v.as_u64()) && !e.contains(&(v as u32)) { e.push(v as u32); }
    }
    e
}

fn gpu_defaults() {
    if std::env::var_os("STRATA_GLM_CPU").is_some() { return; }
    // VRAM budget is absolute (includes the ~non-expert weights): 11.5 GB gave the best hit rate on a 12 GB card.
    for (k, v) in [("STRATA_DS_GPU", "1"), ("STRATA_DS_GPU_EXPERTS", "11")] {
        if std::env::var_os(k).is_none() { unsafe { std::env::set_var(k, v) } }
    }
}

/// Context limit per request: the model's trained context, or `STRATA_GLM_CTX`.
fn ctx_limit(m: &forward::GlmModel) -> usize { forward::max_ctx(&m.cfg) }

/// `rustingstrata chat` for GLM: greedy, thinking on, KV kept across turns while the history extends it.
pub fn chat(g: &Gguf, system: Option<String>, n: usize) -> anyhow::Result<()> {
    use std::io::{BufRead, Write};
    gpu_defaults();
    let tok = crate::tokenizer::Tokenizer::from_gguf(g)?;
    let mut m = forward::GlmModel::new(g)?;
    let stop = stop_ids(g, &tok);
    let mut msgs: Vec<(String, String)> = system.into_iter().map(|s| ("system".to_string(), s)).collect();
    loop {
        print!("> ");
        std::io::stdout().flush()?;
        let mut line = String::new();
        if std::io::stdin().lock().read_line(&mut line)? == 0 { break; }
        if line.trim().is_empty() { continue; }
        msgs.push(("user".into(), line.trim_end().into()));
        let view: Vec<(&str, &str)> = msgs.iter().map(|(a, b)| (a.as_str(), b.as_str())).collect();
        let ids = tok.encode(&chat_prompt(&view))?;
        if ids.len() >= ctx_limit(&m) { eprintln!("context full ({} tokens)", ids.len()); break; }
        let keep = if m.toks.len() < ids.len() && ids.starts_with(&m.toks) { m.toks.len() } else { m.reset(); 0 };
        let logits = m.prefill(&ids[keep..]);
        let room = n.min(ctx_limit(&m) - ids.len());
        let (out, _) = decode_greedy(&mut m, &tok, &stop, logits, room, &mut |t| { print!("{t}"); let _ = std::io::stdout().flush(); true });
        println!();
        msgs.push(("assistant".into(), tok.decode(&out)?));
    }
    Ok(())
}

/// `rustingstrata serve` for GLM: one request at a time, OpenAI `/v1/chat/completions` (JSON or SSE), `/v1/models`, `/health`.
/// ponytail: greedy only, no stop strings; prompt + reply limited to the model's context (STRATA_GLM_CTX overrides); KV reused when the prompt extends it.
pub fn serve(g: &Gguf, name: &str, addr: &str, api_key: Option<&str>) -> anyhow::Result<()> {
    use serde_json::json;
    use std::io::Write;
    gpu_defaults();
    let tok = crate::tokenizer::Tokenizer::from_gguf(g)?;
    let mut m = forward::GlmModel::new(g)?;
    let stop = stop_ids(g, &tok);
    let ctx = ctx_limit(&m);
    let l = std::net::TcpListener::bind(addr)?;
    eprintln!("glm serve on http://{addr}/ model {name}");
    for c in l.incoming() {
        let Ok(mut c) = c else { continue };
        let _ = c.set_read_timeout(Some(std::time::Duration::from_secs(30)));
        let _ = c.set_write_timeout(Some(std::time::Duration::from_secs(30)));
        let Ok(r) = crate::serve::read_request(&mut std::io::BufReader::new(&c)) else { continue };
        let send = |c: &mut std::net::TcpStream, status: &str, ty: &str, b: &str| {
            let _ = write!(c, "HTTP/1.1 {status}\r\nContent-Type: {ty}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{b}", b.len());
        };
        let path = r.path.split('?').next().unwrap_or("");
        if path != "/health" && api_key.is_none() && !crate::serve::host_ok(&r.host, addr, &[]) {
            send(&mut c, "403 Forbidden", "application/json", r#"{"error":{"message":"bad Host header"}}"#);
            continue;
        }
        if path != "/health" && api_key.is_some_and(|k| !crate::serve::key_ok(&r.auth, k)) {
            send(&mut c, "401 Unauthorized", "application/json", r#"{"error":{"message":"missing or wrong API key","type":"invalid_api_key"}}"#);
            continue;
        }
        match (r.method.as_str(), path) {
            ("GET", "/health") => send(&mut c, "200 OK", "application/json", r#"{"status":"ok"}"#),
            ("GET", "/v1/models") => send(&mut c, "200 OK", "application/json", &json!({"object": "list", "data": [{"id": name, "object": "model", "owned_by": "strata"}]}).to_string()),
            ("POST", "/v1/chat/completions") => {
                let q = match crate::serve::chat_request(&r.body) {
                    Ok(q) => q,
                    Err(e) => { send(&mut c, "400 Bad Request", "application/json", &json!({"error": {"message": format!("{e:#}"), "type": "invalid_request_error"}}).to_string()); continue }
                };
                let ids = match tok.encode(&chat_prompt_tools(&q.messages, &q.tools)) {
                    Ok(i) if !i.is_empty() => i,
                    _ => { send(&mut c, "400 Bad Request", "application/json", r#"{"error":{"message":"cannot encode prompt"}}"#); continue }
                };
                if ids.len() >= ctx {
                    send(&mut c, "400 Bad Request", "application/json", &json!({"error": {"message": format!("prompt is {} tokens, the limit is {}", ids.len(), ctx - 1), "type": "invalid_request_error"}}).to_string());
                    continue;
                }
                let keep = if m.toks.len() < ids.len() && ids.starts_with(&m.toks) { m.toks.len() } else { m.reset(); 0 };
                let logits = m.prefill(&ids[keep..]);
                let n = q.max_tokens.unwrap_or(256).min(ctx - ids.len());
                if q.stream { let _ = write!(c, "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"); }
                let chunk = |d: serde_json::Value, fin: Option<&str>| json!({"object": "chat.completion.chunk", "model": name, "choices": [{"index": 0, "delta": d, "finish_reason": fin}]});
                let stream = q.stream;
                let tools = q.tool_calls && !q.tools.is_empty();
                let mut hold = crate::chat::Hold::new(tools, vec![]);
                let (out, done) = decode_greedy(&mut m, &tok, &stop, logits, n, &mut |t| {
                    let t = hold.push(t);
                    !stream || t.is_empty() || write!(c, "data: {}\n\n", chunk(json!({"content": t}), None)).is_ok()
                });
                let calls = if tools { parse_calls(&hold.text, &q.tools) } else { None };
                let done = if calls.is_some() { "tool_calls" } else { done };
                let calls_json = |(content, calls): &(String, Vec<(String, String)>), stream: bool| {
                    let c: Vec<_> = calls.iter().enumerate().map(|(k, (f, a))| {
                        let mut c = json!({"id": format!("call_{k}"), "type": "function", "function": {"name": f, "arguments": a}});
                        if stream { c["index"] = k.into(); }
                        c
                    }).collect();
                    if stream { json!({"tool_calls": c}) } else { json!({"role": "assistant", "content": if content.is_empty() { None } else { Some(content) }, "tool_calls": c}) }
                };
                if stream {
                    match &calls {
                        Some(x) => { let _ = write!(c, "data: {}\n\n", chunk(calls_json(x, true), None)); }
                        None if !hold.rest().is_empty() => { let _ = write!(c, "data: {}\n\n", chunk(json!({"content": hold.rest()}), None)); }
                        None => {}
                    }
                    let _ = write!(c, "data: {}\n\ndata: [DONE]\n\n", chunk(json!({}), Some(done)));
                } else {
                    let message = match &calls { Some(x) => calls_json(x, false), None => json!({"role": "assistant", "content": hold.text}) };
                    let b = json!({"object": "chat.completion", "model": name, "choices": [{"index": 0, "message": message, "finish_reason": done}],
                        "usage": {"prompt_tokens": ids.len(), "completion_tokens": out.len(), "total_tokens": ids.len() + out.len()}});
                    send(&mut c, "200 OK", "application/json", &b.to_string());
                }
            }
            _ => send(&mut c, "404 Not Found", "application/json", r#"{"error":{"message":"not found"}}"#),
        }
    }
    Ok(())
}

#[cfg(test)]
mod chat_tests {
    use super::{chat_prompt, chat_prompt_tools, parse_calls};

    /// Expected strings come from llama.cpp b12119 `/apply-template` (tools/glm_ref/llama_tok.json).
    #[test]
    fn template_matches_llama() {
        let j: serde_json::Value = serde_json::from_str(include_str!("../../tools/glm_ref/llama_tok.json")).unwrap();
        let t = &j["tpl"];
        assert_eq!(chat_prompt(&[("user", "Hello")]), t[0]["prompt"].as_str().unwrap());
        let m = [("system", "Be brief."), ("user", "Hi"), ("assistant", "Hey"), ("user", "Bye")];
        assert_eq!(chat_prompt(&m), t[1]["prompt"].as_str().unwrap());
    }

    #[test]
    fn tools_match_llama() {
        // crate Json keeps key order; serde_json::Value would sort the tool schemas' keys.
        let j: crate::chat::Json = serde_json::from_str(include_str!("../../tools/glm_ref/tpl_tools.json")).unwrap();
        let crate::chat::Json::Arr(cases) = j else { panic!() };
        for c in &cases {
            let q = crate::serve::chat_request(c.get("req").dump().as_bytes()).unwrap();
            assert_eq!(chat_prompt_tools(&q.messages, &q.tools), c.get("prompt").as_str().unwrap());
        }
    }

    #[test]
    fn parses_calls() {
        let t = r#"[{"type":"function","function":{"name":"f","parameters":{"properties":{"s":{"type":"string"}}}}}]"#;
        let tools: Vec<crate::chat::Json> = serde_json::from_str(t).unwrap();
        let (txt, c) = parse_calls("<think>a <tool_call> b</think>ok <tool_call>f<arg_key>s</arg_key><arg_value>12</arg_value><arg_key>n</arg_key><arg_value>[1, 2]</arg_value></tool_call>", &tools).unwrap();
        assert_eq!(txt, "<think>a <tool_call> b</think>ok");
        assert_eq!(c, vec![("f".to_string(), r#"{"s": "12", "n": [1, 2]}"#.to_string())]);
        assert!(parse_calls("plain", &tools).is_none());
    }
}
