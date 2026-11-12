//! Scalar CPU reference forward for the architectures in `config::arch`, one token at a time.
//! Mirrors llama.cpp `src/models/qwen35moe.cpp`; this is the correctness oracle, not the fast path.

use crate::config::{LayerKind, ModelConfig};
use crate::gguf::Gguf;
use crate::ops;
use crate::weights::{Tensor, Weights};
use anyhow::Context;
use std::collections::HashMap;
use std::path::Path;

#[derive(Clone)]
pub struct LoraEntry {
    pub rank: usize,
    pub in_dim: usize,
    pub out_dim: usize,
    pub n_expert: usize,
    pub a: Vec<Vec<f32>>,
    pub b: Vec<Vec<f32>>,
}

#[derive(Clone)]
pub struct Lora {
    pub scale: f32,
    pub alpha: f32,
    pub entries: HashMap<String, LoraEntry>,
}

pub struct Model<'a> {
    pub cfg: ModelConfig,
    pub w: Weights<'a>,
    pub loras: Vec<Lora>,
    ple: Option<Ple>,
}

impl Model<'_> {
    /// Host memory this process owns outright: baked/synthesized tensors and LoRA factors. The mmapped GGUF is
    /// evictable page cache and is not counted, so models larger than RAM still load.
    pub fn ram_estimate(&self) -> usize {
        let lora: usize = self.loras.iter().flat_map(|l| l.entries.values()).map(|e| (e.a.len() * e.in_dim + e.b.len() * e.out_dim) * 4).sum();
        self.w.built.values().map(|t| t.data.len()).sum::<usize>() + lora
    }
}

/// qwen4exp per-layer embedding (PLE): n-gram hash constants from the GGUF.
struct Ple { mult: Vec<u64>, off: Vec<u64>, vocab: Vec<u64>, eos: i64 }

// PLE geometry, checked against the GGUF at load: n-grams up to 3 tokens, 8 hash heads per n-gram order,
// a 4-tap causal conv dilated by the n-gram size, so it reads rows t-9, t-6, t-3, t.
const PLE_NGRAM: usize = 3;
const PLE_HEADS: usize = 8;
const PLE_KERNEL: usize = 4;
const PLE_HIST: usize = (PLE_KERNEL - 1) * PLE_NGRAM;
/// QSA: cells per pooled indexer key.
const QSA_POOL: usize = 4;

pub enum LayerState {
    /// conv: last (ssm_conv - 1) inputs per channel, oldest first; s: dt_rank x head_v x head_k.
    Recurrent { conv: Vec<f32>, s: Vec<f32> },
    /// k, v: pos x n_head_kv x head_dim; ik: pos x idx_head_dim raw QSA indexer keys (empty without an indexer).
    Attn { k: Vec<f32>, v: Vec<f32>, ik: Vec<f32> },
}

pub struct State {
    pub layers: Vec<LayerState>,
    pub pos: usize,
    /// qwen4exp PLE: the last PLE_HIST normalized rows (hc * n_embd each, oldest first), and the two previous
    /// tokens (newest first, -1 for none) for the n-gram hash.
    pub ple_hist: Vec<f32>,
    pub ple_prev: [i64; 2],
}

impl State {
    pub fn new(c: &ModelConfig) -> State {
        let channels = c.ssm_d_inner + 2 * c.ssm_n_group * c.ssm_d_state;
        let layers = c.layers.iter()
            .map(|k| match k {
                LayerKind::Delta => LayerState::Recurrent {
                    conv: vec![0.0; (c.ssm_conv - 1) * channels],
                    s: vec![0.0; c.ssm_dt_rank * c.ssm_dv() * c.ssm_d_state],
                },
                LayerKind::Attn => LayerState::Attn { k: Vec::new(), v: Vec::new(), ik: Vec::new() },
            })
            .collect();
        let ple = if c.n_embd_ple > 0 { PLE_HIST * c.hc_n * c.n_embd } else { 0 };
        State { layers, pos: 0, ple_hist: vec![0.0; ple], ple_prev: [-1, -1] }
    }
}

/// MTP draft state: the KV cache of the nextn block.
pub struct Mtp { pub kv: LayerState, pub pos: usize }

impl Default for Mtp {
    fn default() -> Mtp { Mtp { kv: LayerState::Attn { k: Vec::new(), v: Vec::new(), ik: Vec::new() }, pos: 0 } }
}

fn mv(t: &Tensor, x: &[f32]) -> Vec<f32> {
    let mut y = vec![0f32; t.rows];
    t.matvec(x, &mut y);
    y
}

impl<'a> Model<'a> {
    pub fn load(g: &'a Gguf) -> anyhow::Result<Model<'a>> { Self::load_with_lora(g, &[]) }
    pub fn load_with_lora(g: &'a Gguf, loras: &[(String, f32)]) -> anyhow::Result<Model<'a>> {
        let mut cfg = ModelConfig::from_gguf(g)?;
        let w = Weights::new(g)?;
        if !w.validate(cfg.n_layer)? && cfg.n_nextn > 0 {
            eprintln!("note: the MTP (nextn) layer has a quant type this engine does not support; loading without MTP");
            cfg.n_nextn = 0;
        }
        w.get("token_embd.weight")?;
        let ple = if cfg.n_embd_ple > 0 {
            let p = |k: &str| format!("{}.ple.{k}", cfg.arch);
            let arr = |k: &str| -> anyhow::Result<Vec<u64>> {
                g.get(&p(k))?.as_arr().with_context(|| p(k))?.iter().map(|v| v.as_u64().with_context(|| p(k))).collect()
            };
            let int = |k: &str| -> anyhow::Result<u64> { g.get(&p(k))?.as_u64().with_context(|| p(k)) };
            anyhow::ensure!(int("ngram_size")? == PLE_NGRAM as u64 && int("heads_per_ngram")? == PLE_HEADS as u64
                && int("conv_kernel")? == PLE_KERNEL as u64, "unsupported PLE geometry");
            let ple = Ple { mult: arr("layer_multipliers")?, off: arr("head_offsets")?, vocab: arr("head_vocab_sizes")?, eos: int("eos_token_id")? as i64 };
            let heads = (PLE_NGRAM - 1) * PLE_HEADS;
            anyhow::ensure!(ple.mult.len() == PLE_NGRAM && ple.off.len() == heads && ple.vocab.len() == heads
                && ple.vocab.iter().all(|&v| v > 0) && heads * cfg.n_embd_ple == cfg.n_embd, "bad PLE metadata");
            w.get("per_layer_token_embd.weight")?;
            Some(ple)
        } else {
            w.get("output_norm.weight")?;
            None
        };
        let mut m = Model { cfg, w, loras: Vec::new(), ple };
        m.apply_lora(loras)?;
        Ok(m)
    }

    pub fn apply_lora(&mut self, specs: &[(String, f32)]) -> anyhow::Result<()> {
        // Load everything before touching the current overlays, so a bad adapter leaves the model unchanged.
        let loras: Vec<Lora> = specs.iter().map(|(path, scale)| load_lora(path, *scale)).collect::<anyhow::Result<_>>()?;
        self.w.clear_baked();
        self.loras = loras;
        self.w.bake_lora(&self.loras);
        Ok(())
    }

    pub fn lora_delta(&self, name: &str, x: &[f32], y: &mut [f32], expert: Option<usize>) {
        for lora in &self.loras {
            if let Some(e) = lora.entries.get(name) {
                let ei = if e.n_expert == 1 { 0 } else { expert.unwrap_or(0) };
                if ei >= e.n_expert && e.n_expert > 1 { continue; }
                let a = &e.a[ei];
                let b = &e.b[ei];
                let rank = e.rank;
                let in_dim = e.in_dim;
                let out_dim = e.out_dim;
                for r in 0..rank {
                    let mut s = 0f32;
                    for i in 0..in_dim {
                        if i < x.len() { s += a[r * in_dim + i] * x[i]; }
                    }
                    let coef = if lora.alpha > 0.0 { lora.scale * lora.alpha / rank as f32 * s } else { lora.scale * s };
                    for o in 0..out_dim {
                        if o < y.len() { y[o] += coef * b[o * rank + r]; }
                    }
                }
            }
        }
    }

    fn t(&self, il: usize, suffix: &str) -> Tensor<'a> {
        self.w.layer(il, suffix).unwrap_or_else(|e| panic!("{e:#}"))
    }
    fn f(&self, il: usize, suffix: &str) -> Vec<f32> { self.t(il, suffix).to_f32() }

    pub fn embed(&self, token: u32) -> Vec<f32> {
        let mut x = vec![0f32; self.cfg.n_embd];
        self.w.get("token_embd.weight").unwrap().row(token as usize, &mut x);
        x
    }

    /// Run one token; returns logits over the vocabulary.
    pub fn step(&self, st: &mut State, token: u32) -> Vec<f32> { self.step_h(st, token).0 }

    /// Run one token; returns logits and the last hidden state (before output_norm).
    pub fn step_h(&self, st: &mut State, token: u32) -> (Vec<f32>, Vec<f32>) {
        if self.cfg.hc_n > 0 { return self.step_hc(st, token); }
        let mut x = self.embed(token);
        for il in 0..self.cfg.n_layer { self.block(il, &mut x, &mut st.layers[il], st.pos); }
        st.pos += 1;
        (self.head(&x, &self.w.get("output_norm.weight").unwrap().to_f32()), x)
    }

    /// qwen4exp: the residual is a stack of hc_n streams (hyper-connections). Every half-layer reads the stack
    /// down to one vector, runs its block and writes the output back into every stream with a per-stream weight.
    /// Layers holding `ple_key` first add the per-layer n-gram embedding (PLE) to the stack. Returns the logits
    /// and the head's mixed vector. Mirrors original Strata's `Engine::enqueue` (llama.cpp qwen4exp.cpp).
    fn step_hc(&self, st: &mut State, token: u32) -> (Vec<f32>, Vec<f32>) {
        let c = &self.cfg;
        let mut r = self.embed(token).repeat(c.hc_n);
        let emb = self.ple_embed(&mut st.ple_prev, token);
        for il in 0..c.n_layer {
            if self.w.layer(il, "ple_key.weight").is_ok() { self.ple(il, &mut r, &emb, &mut st.ple_hist); }
            let (h, inj) = self.hc_read(&r, &format!("blk.{il}.hc_attn_"));
            let mix = match &mut st.layers[il] {
                LayerState::Recurrent { conv, s } => self.deltanet(il, &h, conv, s),
                LayerState::Attn { k, v, ik } => self.attention(il, &h, k, v, ik, st.pos),
            };
            Self::hc_write(&mut r, &mix, &inj);
            let (h, inj) = self.hc_read(&r, &format!("blk.{il}.hc_ffn_"));
            Self::hc_write(&mut r, &self.moe(il, &h), &inj);
        }
        st.pos += 1;
        let (h, _) = self.hc_read(&r, "output_hc_");
        (mv(&self.w.get("output.weight").unwrap(), &h), h)
    }

    /// Hyper-connection read (`build_hc_mix`) of the stack `r` with the tensors `{p}norm/down/up/inject.weight`:
    /// xn = per-stream RMSNorm(r), lo = silu(down·xn / hc), mixed = mean over streams of xn ⊙ sigmoid(up·lo),
    /// inject = inject·xn (empty when there is no inject tensor, as in the head).
    fn hc_read(&self, r: &[f32], p: &str) -> (Vec<f32>, Vec<f32>) {
        let (n, hc) = (self.cfg.n_embd, self.cfg.hc_n as f32);
        let t = |s: &str| self.w.get(&format!("{p}{s}.weight"));
        let mut xn = vec![0f32; r.len()];
        self.gnorm(r, &t("norm").unwrap().to_f32(), &mut xn);
        let lo: Vec<f32> = mv(&t("down").unwrap(), &xn).into_iter().map(|v| ops::silu(v / hc)).collect();
        let mut mixed = vec![0f32; n];
        for (i, g) in mv(&t("up").unwrap(), &lo).into_iter().enumerate() { mixed[i % n] += xn[i] * ops::sigmoid(g) / hc; }
        (mixed, t("inject").map(|w| mv(&w, &xn)).unwrap_or_default())
    }

    /// Hyper-connection write (`build_hc_combine`): stream c += out * 2 sigmoid(inject[c] / hc).
    fn hc_write(r: &mut [f32], out: &[f32], inj: &[f32]) {
        let hc = inj.len() as f32;
        for (rc, &j) in r.chunks_exact_mut(out.len()).zip(inj) {
            let w = 2.0 * ops::sigmoid(j / hc);
            for (a, b) in rc.iter_mut().zip(out) { *a += b * w; }
        }
    }

    /// Per-stream RMSNorm of an hc_n x n_embd stack with an hc_n x n_embd gamma.
    fn gnorm(&self, x: &[f32], w: &[f32], out: &mut [f32]) {
        let n = self.cfg.n_embd;
        for ((xc, wc), oc) in x.chunks_exact(n).zip(w.chunks_exact(n)).zip(out.chunks_exact_mut(n)) {
            ops::rms_norm(xc, wc, self.cfg.eps, oc);
        }
    }

    /// The PLE table rows of `token`: its 2- and 3-grams hashed (XOR of token x multiplier, mod each head's vocab,
    /// plus the head's offset), 8 heads per order. EOS or the sequence start cut the context: that position and
    /// every older one read as EOS. Advances `prev` (the last two tokens, -1 before the start).
    /// ponytail: image tokens are not mapped to `ple.image_token_id` (text only).
    pub fn ple_rows(&self, prev: &mut [i64; 2], token: u32) -> Vec<u64> {
        let Some(p) = &self.ple else { return Vec::new() };
        let mut ctx = [token as i64; PLE_NGRAM];
        let mut cut = false;
        for s in 1..PLE_NGRAM {
            let t = prev[s - 1];
            cut = cut || t < 0 || t == p.eos;
            ctx[s] = if cut { p.eos } else { t };
        }
        *prev = [token as i64, prev[0]];
        let mut rows = Vec::with_capacity(p.vocab.len());
        for n in 2..=PLE_NGRAM {
            let mut m = (ctx[0] as u64).wrapping_mul(p.mult[0]);
            for j in 1..n { m ^= (ctx[j] as u64).wrapping_mul(p.mult[j]); }
            for h in (n - 2) * PLE_HEADS..(n - 1) * PLE_HEADS { rows.push(m % p.vocab[h] + p.off[h]); }
        }
        rows
    }

    /// The PLE input of `token`: its 16 table rows, head after head (empty for models without PLE).
    pub fn ple_embed(&self, prev: &mut [i64; 2], token: u32) -> Vec<f32> {
        let rows = self.ple_rows(prev, token);
        if rows.is_empty() { return Vec::new() }
        let (table, d) = (self.w.get("per_layer_token_embd.weight").unwrap(), self.cfg.n_embd_ple);
        let mut emb = vec![0f32; self.cfg.n_embd];
        for (r, e) in rows.into_iter().zip(emb.chunks_exact_mut(d)) { table.row(r as usize, e); }
        emb
    }

    /// The PLE block (`build_ple`) on the stack `r`: a per-stream gate from key·query scales the value, and the
    /// normalized gated rows feed a causal conv dilated by the n-gram size. r += gated + silu(conv).
    fn ple(&self, il: usize, r: &mut [f32], emb: &[f32], hist: &mut [f32]) {
        let (n, d) = (self.cfg.n_embd, r.len());
        let mut key = vec![0f32; d];
        self.gnorm(&mv(&self.t(il, "ple_key.weight"), emb), &self.f(il, "ple_norm_key.weight"), &mut key);
        let mut query = vec![0f32; d];
        self.gnorm(r, &self.f(il, "ple_norm_query.weight"), &mut query);
        let value = mv(&self.t(il, "ple_value.weight"), emb);
        let mut gated = vec![0f32; d];
        for (c, gc) in gated.chunks_exact_mut(n).enumerate() {
            let s = key[c * n..(c + 1) * n].iter().zip(&query[c * n..(c + 1) * n]).map(|(a, b)| a * b).sum::<f32>() / (n as f32).sqrt();
            let sign = if s > 0.0 { 1.0 } else if s < 0.0 { -1.0 } else { 0.0 };
            let gate = ops::sigmoid(sign * s.abs().max(1e-6).sqrt());
            for (o, v) in gc.iter_mut().zip(&value) { *o = v * gate; }
        }
        let mut norm = vec![0f32; d];
        self.gnorm(&gated, &self.f(il, "ple_norm_conv.weight"), &mut norm);
        let kw = self.f(il, "ple_conv1d.weight"); // [channel][tap]
        for i in 0..d {
            let mut acc = kw[i * PLE_KERNEL + PLE_KERNEL - 1] * norm[i];
            for k in 0..PLE_KERNEL - 1 { acc += kw[i * PLE_KERNEL + k] * hist[k * PLE_NGRAM * d + i]; }
            r[i] += gated[i] + ops::silu(acc);
        }
        hist.copy_within(d.., 0);
        hist[(PLE_HIST - 1) * d..].copy_from_slice(&norm);
    }

    /// One decoder block (mixer and FFN, each with residual) on x at position `pos`.
    fn block(&self, il: usize, x: &mut [f32], ls: &mut LayerState, pos: usize) {
        let c = &self.cfg;
        let mut h = vec![0f32; c.n_embd];
        ops::rms_norm(x, &self.f(il, "attn_norm.weight"), c.eps, &mut h);
        let mix = match ls {
            LayerState::Recurrent { conv, s } => self.deltanet(il, &h, conv, s),
            LayerState::Attn { k, v, ik } => self.attention(il, &h, k, v, ik, pos),
        };
        for (a, b) in x.iter_mut().zip(&mix) { *a += b; }
        ops::rms_norm(x, &self.f(il, "post_attention_norm.weight"), c.eps, &mut h);
        let ffn = if c.is_moe() { self.moe(il, &h) } else { self.dense_ffn(il, &h) };
        for (a, b) in x.iter_mut().zip(&ffn) { *a += b; }
    }

    /// Logits of the output head on rms_norm(x) with weights `norm`.
    fn head(&self, x: &[f32], norm: &[f32]) -> Vec<f32> {
        let mut h = vec![0f32; self.cfg.n_embd];
        ops::rms_norm(x, norm, self.cfg.eps, &mut h);
        let head = self.w.get("output.weight").or_else(|_| self.w.get("token_embd.weight")).unwrap();
        mv(&head, &h)
    }

    /// MTP draft (`nextn` block, stored as layer n_layer): logits for the token after `token`, from `hid`, the main
    /// model's last hidden state at the position that predicted `token`. Input is eh_proj [enorm(embed), hnorm(hid)].
    pub fn mtp_step(&self, ms: &mut Mtp, hid: &[f32], token: u32) -> (Vec<f32>, Vec<f32>) {
        let (c, il) = (&self.cfg, self.cfg.n_layer);
        let n = c.n_embd;
        let mut eh = vec![0f32; 2 * n];
        ops::rms_norm(&self.embed(token), &self.f(il, "nextn.enorm.weight"), c.eps, &mut eh[..n]);
        ops::rms_norm(hid, &self.f(il, "nextn.hnorm.weight"), c.eps, &mut eh[n..]);
        let mut x = mv(&self.t(il, "nextn.eh_proj.weight"), &eh);
        self.block(il, &mut x, &mut ms.kv, ms.pos);
        ms.pos += 1;
        (self.head(&x, &self.f(il, "nextn.shared_head_norm.weight")), x)
    }

    fn deltanet(&self, il: usize, h: &[f32], conv: &mut [f32], s: &mut [f32]) -> Vec<f32> {
        let c = &self.cfg;
        let (dk, nk, nv) = (c.ssm_d_state, c.ssm_n_group, c.ssm_dt_rank);
        let dv = c.ssm_dv();
        let channels = c.ssm_d_inner + 2 * nk * dk;
        let kw = c.ssm_conv;

        let qkv = mv(&self.t(il, "attn_qkv.weight"), h);
        let z = mv(&self.t(il, "attn_gate.weight"), h);
        let beta: Vec<f32> = mv(&self.t(il, "ssm_beta.weight"), h).into_iter().map(ops::sigmoid).collect();
        let (dt_bias, a) = (self.f(il, "ssm_dt.bias"), self.f(il, "ssm_a"));
        let g: Vec<f32> = mv(&self.t(il, "ssm_alpha.weight"), h).iter().enumerate()
            .map(|(i, &al)| ops::softplus(al + dt_bias[i]) * a[i]).collect();

        // Causal depthwise conv over [state..., current], then SiLU.
        let w = self.f(il, "ssm_conv1d.weight");
        let mut y = vec![0f32; channels];
        for ch in 0..channels {
            let mut acc = 0.0;
            for k in 0..kw - 1 { acc += conv[k * channels + ch] * w[ch * kw + k]; }
            acc += qkv[ch] * w[ch * kw + kw - 1];
            y[ch] = ops::silu(acc);
        }
        conv.copy_within(channels.., 0);
        conv[(kw - 2) * channels..].copy_from_slice(&qkv);

        let (q, rest) = y.split_at_mut(nk * dk);
        let (k, v) = rest.split_at_mut(nk * dk);
        for hd in q.chunks_exact_mut(dk).chain(k.chunks_exact_mut(dk)) { ops::l2_norm(hd, c.eps); }

        let norm_w = self.f(il, "ssm_norm.weight");
        let scale = 1.0 / (dk as f32).sqrt();
        let mut out = vec![0f32; nv * dv];
        let mut o = vec![0f32; dv];
        for vh in 0..nv {
            let kh = if c.k_interleave { vh / (nv / nk) } else { vh % nk };
            let (qh, khv, vv) = (&q[kh * dk..(kh + 1) * dk], &k[kh * dk..(kh + 1) * dk], &v[vh * dv..(vh + 1) * dv]);
            let sm = &mut s[vh * dv * dk..(vh + 1) * dv * dk]; // row j (value dim) x col i (key dim)
            let decay = g[vh].exp();
            for x in sm.iter_mut() { *x *= decay; }
            for j in 0..dv {
                let row = &mut sm[j * dk..(j + 1) * dk];
                let sk: f32 = row.iter().zip(khv).map(|(a, b)| a * b).sum();
                let d = beta[vh] * (vv[j] - sk);
                for (r, kk) in row.iter_mut().zip(khv) { *r += d * kk; }
                o[j] = row.iter().zip(qh.iter()).map(|(a, b)| a * b).sum::<f32>() * scale;
            }
            let oh = &mut out[vh * dv..(vh + 1) * dv];
            ops::rms_norm(&o, &norm_w, c.eps, oh);
            // qwen4exp gates with sigmoid(z), the others with silu(z)
            let gate = if c.arch == "qwen4exp" { ops::sigmoid } else { ops::silu };
            for (x, zz) in oh.iter_mut().zip(&z[vh * dv..(vh + 1) * dv]) { *x *= gate(*zz); }
        }
        mv(&self.t(il, "ssm_out.weight"), &out)
    }

    /// QSA (qwen4exp sparse attention): the cells row `pos` attends to, or None for all of them. Keys are pooled
    /// in blocks of QSA_POOL cells: mean of the raw indexer keys, RMS-normed and rotated to the block's first
    /// position. Each complete block scores sum over heads of relu(q_h . k) / sqrt(head_dim); the top
    /// idx_top_k / QSA_POOL blocks (ties to the lower block) and the incomplete tail block are kept. Dense while
    /// there are no more complete blocks than that. Mirrors llama.cpp qwen4exp.cpp `build_qsa_sel`.
    fn qsa(&self, il: usize, h: &[f32], ik: &mut Vec<f32>, pos: usize) -> Option<Vec<usize>> {
        let c = &self.cfg;
        let (nh, d) = (c.idx_n_head, c.idx_head_dim);
        if c.idx_top_k == 0 || self.w.layer(il, "indexer.k_proj.weight").is_err() { return None; }
        ik.extend_from_slice(&mv(&self.t(il, "indexer.k_proj.weight"), h));
        let (nb, top) = ((pos + 1) / QSA_POOL, c.idx_top_k / QSA_POOL);
        if nb <= top { return None; }
        let (qn, kn) = (self.f(il, "indexer.q_norm.weight"), self.f(il, "indexer.k_norm.weight"));
        let qr = mv(&self.t(il, "indexer.q_proj.weight"), h);
        let mut q = vec![0f32; nh * d];
        for i in 0..nh {
            ops::rms_norm(&qr[i * d..(i + 1) * d], &qn, c.eps, &mut q[i * d..(i + 1) * d]);
            ops::rope_neox(&mut q[i * d..(i + 1) * d], c.n_rot, pos, c.rope_base);
        }
        let mut score = vec![0f32; nb];
        let (mut mean, mut k) = (vec![0f32; d], vec![0f32; d]);
        for (b, s) in score.iter_mut().enumerate() {
            mean.fill(0.0);
            for t in b * QSA_POOL..(b + 1) * QSA_POOL {
                for (m, x) in mean.iter_mut().zip(&ik[t * d..(t + 1) * d]) { *m += x / QSA_POOL as f32; }
            }
            ops::rms_norm(&mean, &kn, c.eps, &mut k);
            ops::rope_neox(&mut k, c.n_rot, b * QSA_POOL, c.rope_base);
            *s = q.chunks(d).map(|qh| qh.iter().zip(&k).map(|(a, b)| a * b).sum::<f32>().max(0.0)).sum::<f32>()
                / (d as f32).sqrt();
        }
        let mut blocks = ops::top_k(&score, top);
        blocks.sort_unstable();
        Some(blocks.iter().flat_map(|b| b * QSA_POOL..(b + 1) * QSA_POOL).chain(nb * QSA_POOL..pos + 1).collect())
    }

    fn attention(&self, il: usize, h: &[f32], kc: &mut Vec<f32>, vc: &mut Vec<f32>, ik: &mut Vec<f32>, pos: usize)
        -> Vec<f32> {
        let c = &self.cfg;
        let cells = self.qsa(il, h, ik, pos).unwrap_or_else(|| (0..pos + 1).collect());
        let (hd, nh, nkv) = (c.head_dim, c.n_head, c.n_head_kv);
        let qs = if c.q_gate { 2 * hd } else { hd };  // per-head row of attn_q: query, then the gate if any
        let qg = mv(&self.t(il, "attn_q.weight"), h);
        let (qn, kn) = (self.f(il, "attn_q_norm.weight"), self.f(il, "attn_k_norm.weight"));
        let mut q = vec![0f32; nh * hd];
        for i in 0..nh {
            let qh = &mut q[i * hd..(i + 1) * hd];
            ops::rms_norm(&qg[i * qs..i * qs + hd], &qn, c.eps, qh);
            ops::rope_neox(qh, c.n_rot, pos, c.rope_base);
        }
        let kraw = mv(&self.t(il, "attn_k.weight"), h);
        let v = mv(&self.t(il, "attn_v.weight"), h);
        let mut k = vec![0f32; nkv * hd];
        for i in 0..nkv {
            let kh = &mut k[i * hd..(i + 1) * hd];
            ops::rms_norm(&kraw[i * hd..(i + 1) * hd], &kn, c.eps, kh);
            ops::rope_neox(kh, c.n_rot, pos, c.rope_base);
        }
        kc.extend_from_slice(&k);
        vc.extend_from_slice(&v);
        let scale = 1.0 / (hd as f32).sqrt();
        let mut out = vec![0f32; nh * hd];
        let mut sc = vec![0f32; cells.len()];
        for i in 0..nh {
            let g = i / (nh / nkv);
            let qh = &q[i * hd..(i + 1) * hd];
            for (&t, s) in cells.iter().zip(sc.iter_mut()) {
                let kt = &kc[(t * nkv + g) * hd..(t * nkv + g + 1) * hd];
                *s = qh.iter().zip(kt).map(|(a, b)| a * b).sum::<f32>() * scale;
            }
            ops::softmax(&mut sc);
            let oh = &mut out[i * hd..(i + 1) * hd];
            for (&t, p) in cells.iter().zip(&sc) {
                let vt = &vc[(t * nkv + g) * hd..(t * nkv + g + 1) * hd];
                for (o, vv) in oh.iter_mut().zip(vt) { *o += p * vv; }
            }
            if c.q_gate {
                let gate = &qg[i * qs + hd..(i + 1) * qs];
                for (o, gg) in oh.iter_mut().zip(gate) { *o *= ops::sigmoid(*gg); }
            }
        }
        mv(&self.t(il, "attn_output.weight"), &out)
    }

    fn ffn(&self, il: usize, gate: &Tensor, up: &Tensor, down: &Tensor, down_name: &str, expert: Option<usize>, h: &[f32]) -> Vec<f32> {
        let mut a = mv(gate, h);
        for (x, u) in a.iter_mut().zip(mv(up, h)) { *x = ops::silu(*x) * u; }
        let mut y = mv(down, &a);
        if down_name == "ffn_down_exps.weight" {
            self.lora_delta(&format!("blk.{il}.{down_name}"), &a, &mut y, expert);
        }
        y
    }

    fn dense_ffn(&self, il: usize, h: &[f32]) -> Vec<f32> {
        self.ffn(il, &self.t(il, "ffn_gate.weight"), &self.t(il, "ffn_up.weight"), &self.t(il, "ffn_down.weight"), "ffn_down.weight", None, h)
    }

    fn moe(&self, il: usize, h: &[f32]) -> Vec<f32> {
        let mut y = self.routed_experts(il, h);
        if let Ok(sg) = self.w.layer(il, "ffn_gate_inp_shexp.weight") {
            let s = ops::sigmoid(mv(&sg, h)[0]);
            let o = self.ffn(il, &self.t(il, "ffn_gate_shexp.weight"), &self.t(il, "ffn_up_shexp.weight"), &self.t(il, "ffn_down_shexp.weight"), "ffn_down_shexp.weight", Some(0), h);
            for (a, b) in y.iter_mut().zip(o) { *a += s * b; }
        }
        y
    }

    /// Router softmax, top-k and normalized weights: (expert, weight) pairs.
    pub fn route(&self, il: usize, h: &[f32]) -> Vec<(usize, f32)> {
        let c = &self.cfg;
        let mut p = mv(&self.t(il, "ffn_gate_inp.weight"), h);
        ops::softmax(&mut p);
        let top = ops::top_k(&p, c.n_expert_used);
        let sum = top.iter().map(|&e| p[e]).sum::<f32>().max(6.103515625e-5);
        let mut scale = 1.0 / sum;
        if c.expert_weights_scale != 0.0 { scale *= c.expert_weights_scale; }
        top.into_iter().map(|e| (e, p[e] * scale)).collect()
    }

    /// Router, top-k and the weighted sum of routed experts (no shared expert).
    pub fn routed_experts(&self, il: usize, h: &[f32]) -> Vec<f32> {
        let (gate, up, down) = (self.t(il, "ffn_gate_exps.weight"), self.t(il, "ffn_up_exps.weight"), self.t(il, "ffn_down_exps.weight"));
        let n = self.cfg.n_expert;
        let mut y = vec![0f32; self.cfg.n_embd];
        for (e, w) in self.route(il, h) {
            let o = self.ffn(il, &gate.expert(e, n), &up.expert(e, n), &down.expert(e, n), "ffn_down_exps.weight", Some(e), h);
            for (a, b) in y.iter_mut().zip(o) { *a += w * b; }
        }
        y
    }
}


pub fn load_lora(path: &str, scale: f32) -> anyhow::Result<Lora> {
    use crate::quant::GgmlType;
    use crate::weights::Tensor;
    anyhow::ensure!(scale.is_finite(), "lora: {path}: scale must be finite");
    let g = Gguf::open(Path::new(path))?;
    let alpha = g.meta.get("adapter.lora.alpha").and_then(|v| v.as_f32()).unwrap_or(0.0);
    let mut bases = std::collections::BTreeSet::new();
    for name in g.tensors.keys() {
        if let Some(b) = name.strip_suffix(".lora_a") { bases.insert(b.to_string()); }
        if let Some(b) = name.strip_suffix(".lora_b") { bases.insert(b.to_string()); }
    }
    let mut entries = HashMap::new();
    for base in bases {
        let a_info = g.tensors.get(&format!("{base}.lora_a")).context("missing lora_a")?;
        let b_info = g.tensors.get(&format!("{base}.lora_b")).context("missing lora_b")?;
        let a_t = Tensor { ty: GgmlType::from_u32(a_info.ty)?, cols: a_info.dims[0] as usize, rows: a_info.dims[1..].iter().product::<u64>() as usize, data: g.bytes(a_info) };
        let b_t = Tensor { ty: GgmlType::from_u32(b_info.ty)?, cols: b_info.dims[0] as usize, rows: b_info.dims[1..].iter().product::<u64>() as usize, data: g.bytes(b_info) };
        let a_flat = a_t.to_f32();
        let b_flat = b_t.to_f32();
        let a_dims = &a_info.dims;
        let b_dims = &b_info.dims;
        anyhow::ensure!(a_dims.len() >= 2 && b_dims.len() >= 2, "lora: {base}: rank or dimensions missing");
        let in_dim = a_dims[0] as usize;
        let rank = a_dims[1] as usize;
        let n_expert = *a_dims.get(2).unwrap_or(&1) as usize;
        let out_dim = b_dims[1] as usize;
        anyhow::ensure!(rank > 0 && in_dim > 0 && out_dim > 0 && n_expert > 0, "lora: {base}: empty dimension");
        anyhow::ensure!(b_dims[0] as usize == rank, "lora: {base}: lora_b rank {} != lora_a rank {rank}", b_dims[0]);
        anyhow::ensure!(*b_dims.get(2).unwrap_or(&1) as usize == n_expert, "lora: {base}: expert count differs between lora_a and lora_b");
        anyhow::ensure!(a_flat.len() >= n_expert * rank * in_dim, "lora: {base}: truncated lora_a");
        anyhow::ensure!(b_flat.len() >= n_expert * out_dim * rank, "lora: {base}: truncated lora_b");
        let mut a_experts = vec![vec![0f32; rank * in_dim]; n_expert];
        let mut b_experts = vec![vec![0f32; out_dim * rank]; n_expert];
        for e in 0..n_expert {
            for r in 0..rank {
                for i in 0..in_dim {
                    a_experts[e][r * in_dim + i] = a_flat[(r + e * rank) * in_dim + i];
                }
                for o in 0..out_dim {
                    b_experts[e][o * rank + r] = b_flat[(o + e * out_dim) * rank + r];
                }
            }
        }
        entries.insert(base, LoraEntry { rank, in_dim, out_dim, n_expert, a: a_experts, b: b_experts });
    }
    Ok(Lora { scale, alpha, entries })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn w_str(b: &mut Vec<u8>, s: &str) { b.extend((s.len() as u64).to_le_bytes()); b.extend(s.as_bytes()); }

    fn tiny_adapter(tag: &str) -> std::path::PathBuf {
        let (in_dim, rank, out_dim) = (4u64, 2u64, 3u64);
        let (mut b, mut off) = (Vec::new(), 0u64);
        b.extend(b"GGUF");
        b.extend(3u32.to_le_bytes());
        b.extend(2u64.to_le_bytes());
        b.extend(1u64.to_le_bytes());
        w_str(&mut b, "adapter.lora.alpha");
        b.extend(6u32.to_le_bytes());
        b.extend(2.0f32.to_le_bytes());
        for (name, dims) in [("blk.0.ffn_down_exps.weight.lora_a", [in_dim, rank, 1]), ("blk.0.ffn_down_exps.weight.lora_b", [rank, out_dim, 1])] {
            w_str(&mut b, name);
            b.extend(3u32.to_le_bytes());
            for d in dims { b.extend(d.to_le_bytes()); }
            b.extend(0u32.to_le_bytes());  // F32
            b.extend(off.to_le_bytes());
            off += (dims[0] * dims[1] * dims[2] * 4).next_multiple_of(32);
        }
        while b.len() % 32 != 0 { b.push(0); }
        let a: Vec<f32> = (0..8).map(|i| i as f32).collect();
        let w: Vec<f32> = (0..6).map(|i| 10.0 + i as f32).collect();
        b.extend(a.iter().flat_map(|f| f.to_le_bytes()));
        b.extend(w.iter().flat_map(|f| f.to_le_bytes()));
        let p = std::env::temp_dir().join(format!("strata-lora-{}-{tag}.gguf", std::process::id()));
        std::fs::write(&p, &b).unwrap();
        p
    }

    #[test]
    fn load_lora_adapter() {
        let p = tiny_adapter("parse");
        let l = load_lora(p.to_str().unwrap(), 0.5).unwrap();
        std::fs::remove_file(&p).ok();
        assert_eq!((l.scale, l.alpha), (0.5, 2.0));
        let e = &l.entries["blk.0.ffn_down_exps.weight"];
        assert_eq!((e.rank, e.in_dim, e.out_dim, e.n_expert), (2, 4, 3, 1));
        assert_eq!(e.a[0], (0..8).map(|i| i as f32).collect::<Vec<_>>());
        assert_eq!(e.b[0], (0..6).map(|i| 10.0 + i as f32).collect::<Vec<_>>());
    }
}
