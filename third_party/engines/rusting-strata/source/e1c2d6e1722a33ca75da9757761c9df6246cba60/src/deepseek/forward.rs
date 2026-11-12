//! Slow single-token CPU reference forward for DeepSeek-V4.1 (mirrors llama.cpp deepseek41.cpp).
//! Not implemented: indexer top-k (only matters beyond 512 visible compressed rows, i.e. >1024 tokens)
//! and the candidate-block prune (beyond 4096 rows). The window boundary (128) is unverified.
use super::mat::{Mat, matvec_many, vec_f32};
use super::ops::*;
use super::{AttnKind, DsConfig};
use crate::gguf::Gguf;
use anyhow::Result;

struct Hcw<'a> {
    f: Mat<'a>,
    base: Vec<f32>,
    scale: Vec<f32>,
}

struct CompW<'a> {
    kv: Mat<'a>,
    gate: Option<Mat<'a>>,
    norm: Vec<f32>,
}

struct Layer<'a> {
    attn_norm: Vec<f32>,
    sinks: Vec<f32>,
    q_a_norm: Vec<f32>,
    kv_a_norm: Vec<f32>,
    wq_a: Mat<'a>,
    wq_b: Mat<'a>,
    wkv: Mat<'a>,
    wo_a: Mat<'a>,
    wo_b: Mat<'a>,
    hc_attn: Hcw<'a>,
    hc_ffn: Hcw<'a>,
    ffn_norm: Vec<f32>,
    gate_inp: Mat<'a>,
    bias: Vec<f32>,
    gexps: Mat<'a>,
    uexps: Mat<'a>,
    dexps: Mat<'a>,
    gsh: Mat<'a>,
    ush: Mat<'a>,
    dsh: Mat<'a>,
    comp: Option<CompW<'a>>,
    engram: Option<(Mat<'a>, Vec<f32>)>,
    rope: Rope,
}

#[derive(Default)]
struct Cache {
    raw: Vec<Vec<f32>>,
    comp: Vec<Vec<f32>>,
    pend_v: Vec<Vec<f32>>,
    pend_s: Vec<Vec<f32>>,
}

pub struct DsModel<'a> {
    pub cfg: DsConfig,
    tok_embd: Mat<'a>,
    out_norm: Vec<f32>,
    out_w: Mat<'a>,
    engram_tab: Option<Mat<'a>>,
    layers: Vec<Layer<'a>>,
    cache: Vec<Cache>,
    pre_prev: [f32; 4],
    pub toks: Vec<u32>,
    pub trace: bool,
}

fn act(gate: f32, up: f32, limit: f32) -> f32 {
    if limit > 1e-6 { swiglu_clamp(gate, up, limit) } else { gate / (1.0 + (-gate).exp()) * up }
}

impl<'a> DsModel<'a> {
    pub fn new(g: &'a Gguf) -> Result<Self> {
        let cfg = DsConfig::from_gguf(g)?;
        let rope_for = |k: AttnKind| match k {
            AttnKind::Window => Rope::new(cfg.rope_base, 1.0, 0.0, cfg.n_rot, 0, cfg.yarn_beta_fast, cfg.yarn_beta_slow),
            _ => Rope::new(cfg.compress_rope_base, 1.0 / cfg.yarn_factor, 1.0, cfg.n_rot, cfg.yarn_orig_ctx as u32, cfg.yarn_beta_fast, cfg.yarn_beta_slow),
        };
        let mut layers = vec![];
        for il in 0..cfg.n_layer {
            let m = |n: &str| Mat::load(g, &format!("blk.{il}.{n}"));
            let v = |n: &str| vec_f32(g, &format!("blk.{il}.{n}"));
            let hcw = |s: &str| -> Result<Hcw> { Ok(Hcw { f: m(&format!("hc_{s}_fn.weight"))?, base: v(&format!("hc_{s}_base.weight"))?, scale: v(&format!("hc_{s}_scale.weight"))? }) };
            let comp = if cfg.kv_src[il] == il as i32 {
                Some(CompW {
                    kv: m("attn_compressor_kv.weight")?,
                    gate: if cfg.attn[il] == AttnKind::Csa { Some(m("attn_compressor_gate.weight")?) } else { None },
                    norm: v("attn_compressor_norm.weight")?,
                })
            } else { None };
            let engram = if cfg.engram_index(il).is_some() { Some((m("engram_kv.weight")?, v("engram_gate.weight")?)) } else { None };
            layers.push(Layer {
                attn_norm: v("attn_norm.weight")?, sinks: v("attn_sinks.weight")?, q_a_norm: v("attn_q_a_norm.weight")?, kv_a_norm: v("attn_kv_a_norm.weight")?,
                wq_a: m("attn_q_a.weight")?, wq_b: m("attn_q_b.weight")?, wkv: m("attn_kv.weight")?, wo_a: Mat::load_groups(g, &format!("blk.{il}.attn_output_a.weight"), cfg.o_groups)?, wo_b: m("attn_output_b.weight")?,
                hc_attn: hcw("attn")?, hc_ffn: hcw("ffn")?, ffn_norm: v("ffn_norm.weight")?, gate_inp: m("ffn_gate_inp.weight")?, bias: v("exp_probs_b.bias")?,
                gexps: m("ffn_gate_exps.weight")?, uexps: m("ffn_up_exps.weight")?, dexps: m("ffn_down_exps.weight")?,
                gsh: m("ffn_gate_shexp.weight")?, ush: m("ffn_up_shexp.weight")?, dsh: m("ffn_down_shexp.weight")?,
                comp, engram, rope: rope_for(cfg.attn[il]),
            });
        }
        let engram_tab = if cfg.engram.is_some() { Some(Mat::load(g, "per_layer_token_embd.weight")?) } else { None };
        let n = cfg.n_layer;
        Ok(DsModel {
            tok_embd: Mat::load(g, "token_embd.weight")?, out_norm: vec_f32(g, "output_norm.weight")?, out_w: Mat::load(g, "output.weight")?,
            engram_tab, layers, cache: (0..n).map(|_| Cache::default()).collect(), pre_prev: [1.0, 0.0, 0.0, 0.0], toks: vec![], trace: std::env::var("STRATA_DS_TRACE").is_ok(), cfg,
        })
    }

    /// Forget the whole sequence (new conversation).
    pub fn reset(&mut self) {
        self.cache.iter_mut().for_each(|c| *c = Cache::default());
        self.pre_prev = [1.0, 0.0, 0.0, 0.0];
        self.toks.clear();
    }

    fn tr(&self, name: &str, il: i32, v: &[f32]) {
        if let Ok(dir) = std::env::var("STRATA_DS_DUMP") {
            use std::io::Write;
            let fname = if il < 0 { format!("{dir}/{name}.f32") } else { format!("{dir}/{name}-{il}.f32") };
            let bytes: Vec<u8> = v.iter().flat_map(|x| x.to_le_bytes()).collect();
            std::fs::OpenOptions::new().create(true).append(true).open(fname).unwrap().write_all(&bytes).unwrap();
        }
        if self.trace {
            let n = v.len();
            let f = |i: usize| format!("{:12.4}", v[i]);
            eprintln!("TRACE {name}-{il} [{} {} {} ... {} {} {}] sum={:.6}", f(0), f(1), f(2), f(n - 3), f(n - 2), f(n - 1), v.iter().sum::<f32>());
        }
    }

    fn engram(&self, e: usize, il: usize, pos: usize, x: &mut [f32]) {
        let en = self.cfg.engram.as_ref().unwrap();
        let (kvw, gatew) = self.layers[il].engram.as_ref().unwrap();
        let tab = self.engram_tab.unwrap();
        let (ng, nh) = (en.ngram, en.heads_per_ngram);
        let ncol = (ng - 1) * nh;
        let cid = |t: u32| -> i64 { en.token_map.get(t as usize).map_or(-1, |&c| c as i64) };
        let pad = en.token_map[en.pad_id] as u64;
        let mut toks = vec![0u64; ng];
        let mut c = cid(self.toks[pos]);
        let mut blocked = c < 0;
        toks[0] = if blocked { pad } else { c as u64 };
        for s in 1..ng {
            c = if pos < s { -1 } else { cid(self.toks[pos - s]) };
            blocked |= c < 0;
            toks[s] = if blocked { pad } else { c as u64 };
        }
        let mult = &en.multipliers[e * ng..];
        let mut rolling = toks[0].wrapping_mul(mult[0]);
        let mut rows = vec![0f32; ncol * en.head_dim];
        for o in 1..ng {
            rolling ^= toks[o].wrapping_mul(mult[o]);
            for h in 0..nh {
                let col = (o - 1) * nh + h;
                let id = rolling % en.primes[e * ncol + col] + en.offsets[e * ncol + col];
                tab.row_into(id as usize, &mut rows[col * en.head_dim..(col + 1) * en.head_dim]);
            }
        }
        let n = self.cfg.n_embd;
        let mut kv = vec![0f32; kvw.rows];
        kvw.matvec(&rows, &mut kv);
        let (mut xn, mut kn) = (vec![0f32; n], vec![0f32; n]);
        for s in 0..4 {
            rms_norm(&x[s * n..(s + 1) * n], self.cfg.eps, &mut xn);
            rms_norm(&kv[s * n..(s + 1) * n], self.cfg.eps, &mut kn);
            let dot = (0..n).map(|j| xn[j] * kn[j] * gatew[s * n + j]).sum::<f32>() / (n as f32).sqrt();
            let g = 1.0 / (1.0 + (-(dot.signum() * dot.abs().max(1e-6).sqrt())).exp());
            for j in 0..n {
                x[s * n + j] += kv[4 * n + j] * g;
            }
        }
    }

    fn hc_mix(&self, h: &Hcw, x: &[f32]) -> Hc {
        let mut xn = vec![0f32; x.len()];
        rms_norm(x, self.cfg.eps, &mut xn);
        let mut mixes = vec![0f32; 24];
        h.f.matvec(&xn, &mut mixes);
        hc_coeffs(&mixes, &h.scale, &h.base, self.cfg.hc_eps, self.cfg.hc_iters)
    }

    fn attention(&mut self, il: usize, pos: usize, cur: &[f32]) -> Vec<f32> {
        let cfg = &self.cfg;
        let (nh, hd, nr) = (cfg.n_head, cfg.head_dim, cfg.n_rot);
        let l = &self.layers[il];
        // wq_a, wkv and the compressor's kv/gate all read `cur`: one GPU round trip.
        let mut first = vec![l.wq_a, l.wkv];
        if let Some(cw) = &l.comp { first.push(cw.kv); first.extend(cw.gate); }
        let y0 = matvec_many(&first, cur, 0);
        let (qa, kv0_pre) = (y0[..cfg.q_lora].to_vec(), &y0[cfg.q_lora..]);
        let mut qr = vec![0f32; cfg.q_lora];
        rms_norm_w(&qa, &l.q_a_norm, cfg.eps, &mut qr);
        self.tr("qr_norm", il as i32, &qr);
        let mut q = vec![0f32; nh * hd];
        l.wq_b.matvec(&qr, &mut q);
        for h in 0..nh {
            l.rope.apply(&mut q[h * hd..(h + 1) * hd], pos, false);
        }
        let kv0 = &kv0_pre[..hd];
        let mut kv = vec![0f32; hd];
        rms_norm_w(kv0, &l.kv_a_norm, cfg.eps, &mut kv);
        l.rope.apply(&mut kv, pos, false);
        self.tr("q", il as i32, &q);
        self.tr("kv", il as i32, &kv);

        // compressor on source layers
        let src = cfg.kv_src[il].max(0) as usize;
        let ratio = match cfg.attn[il] { AttnKind::Window => 0, AttnKind::Csa => 2, AttnKind::Hca => 1 };
        if let Some(cw) = &self.layers[il].comp {
            let v = kv0_pre[hd..2 * hd].to_vec();
            let s = if cw.gate.is_some() { kv0_pre[2 * hd..3 * hd].to_vec() } else { vec![0f32; hd] };
            let c = &mut self.cache[il];
            c.pend_v.push(v);
            c.pend_s.push(s);
            if c.pend_v.len() == ratio {
                let mut comp = vec![0f32; hd];
                for j in 0..hd {
                    let mx = c.pend_s.iter().map(|s| s[j]).fold(f32::NEG_INFINITY, f32::max);
                    let ws: Vec<f32> = c.pend_s.iter().map(|s| (s[j] - mx).exp()).collect();
                    let z: f32 = ws.iter().sum();
                    comp[j] = ws.iter().zip(&c.pend_v).map(|(w, v)| w / z * v[j]).sum();
                }
                c.pend_v.clear();
                c.pend_s.clear();
                let g = c.comp.len();
                let mut row = vec![0f32; hd];
                rms_norm_w(&comp, &cw.norm, cfg.eps, &mut row);
                self.tr("comp_latent", il as i32, &row);
                self.layers[il].rope.apply(&mut row, g * ratio, false);
                self.cache[il].comp.push(row);
            }
        }
        self.cache[il].raw.push(kv);

        let l = &self.layers[il];
        let raw = &self.cache[il].raw;
        let w0 = (pos + 1).saturating_sub(cfg.window);
        let ncomp = if ratio == 0 { 0 } else { ((pos + 1) / ratio).min(self.cache[src].comp.len()) };
        let comp = &self.cache[src].comp;
        let scale = 1.0 / (hd as f32).sqrt();
        let mut out = vec![0f32; nh * hd];
        let keys: Vec<&[f32]> = raw[w0..=pos].iter().map(|k| &k[..]).chain(comp[..ncomp].iter().map(|k| &k[..hd])).collect();
        // heads are independent: same math per head, spread over the cores
        use rayon::prelude::*;
        out.par_chunks_mut(hd).enumerate().for_each(|(h, o)| {
            let qh = &q[h * hd..(h + 1) * hd];
            let mut sc: Vec<f32> = keys.iter().map(|k| k.iter().zip(qh).map(|(a, b)| a * b).sum::<f32>() * scale).collect();
            let mx = sc.iter().cloned().fold(l.sinks[h], f32::max);
            let mut z = (l.sinks[h] - mx).exp();
            for s in sc.iter_mut() { *s = (*s - mx).exp(); z += *s; }
            for (s, k) in sc.iter().zip(&keys) {
                for j in 0..hd { o[j] += s / z * k[j]; }
            }
            l.rope.apply(o, pos, true);
        });
        let _ = nr;
        self.tr("attn_derope", il as i32, &out);
        let gsz = nh * hd / cfg.o_groups;
        let subs: Vec<_> = (0..cfg.o_groups).map(|g| l.wo_a.group(g, cfg.o_groups)).collect();
        let oa = matvec_many(&subs, &out, gsz);
        self.tr("attn_wo_a", il as i32, &oa);
        let mut res = vec![0f32; cfg.n_embd];
        l.wo_b.matvec(&oa, &mut res);
        res
    }

    fn ffn(&self, il: usize, cur: &[f32]) -> Vec<f32> {
        let t0 = std::time::Instant::now();
        let cfg = &self.cfg;
        let l = &self.layers[il];
        let mut logits = vec![0f32; cfg.n_expert];
        l.gate_inp.matvec(cur, &mut logits);
        self.tr("ffn_moe_logits", il as i32, &logits);
        let mut sel = route(&logits, &l.bias, cfg.n_used, cfg.weights_norm, cfg.weights_scale);
        // debug: force llama.cpp's expert ids (STRATA_DS_FORCE_TOPK=dir of i32 dumps, prompt tokens only) to separate routing flips from math errors
        if let Some(dir) = std::env::var_os("STRATA_DS_FORCE_TOPK") {
            let pos = self.cache[0].raw.len().saturating_sub(1);
            if let Ok(b) = std::fs::read(std::path::Path::new(&dir).join(format!("ffn_moe_topk-{il}.f32"))) {
                if (pos + 1) * 24 <= b.len() {
                    let ids: Vec<usize> = (0..6).map(|k| u32::from_le_bytes(b[(pos * 6 + k) * 4..][..4].try_into().unwrap()) as usize).collect();
                    let p = |i: usize| { let l = logits[i]; (if l > 20.0 { l } else { l.exp().ln_1p() }).sqrt() };
                    let sum: f32 = ids.iter().map(|&i| p(i)).sum();
                    sel = ids.into_iter().map(|i| (i, p(i) / (sum + 1e-20) * cfg.weights_scale)).collect();
                }
            }
        }
        let ids: Vec<f32> = sel.iter().map(|s| s.0 as f32).collect();
        self.tr("ffn_moe_topk", il as i32, &ids);
        let n = cfg.n_embd;
        let mut out = vec![0f32; n];
        let (mut g, mut u, mut d) = (vec![0f32; cfg.n_ff_exp], vec![0f32; cfg.n_ff_exp], vec![0f32; n]);
        if std::env::var_os("STRATA_DS_NOPREFETCH").is_none() {
            for &(e, _) in &sel {
                for m in [&l.gexps, &l.uexps, &l.dexps] { m.prefetch_expert(e, cfg.n_expert); }
            }
        }
        let t1 = std::time::Instant::now();
        // All selected experts resident in VRAM: 2 GPU round trips per layer instead of 3 per expert.
        let gu: Vec<_> = sel.iter().map(|s| l.gexps.expert(s.0, cfg.n_expert)).chain(sel.iter().map(|s| l.uexps.expert(s.0, cfg.n_expert))).collect();
        let nf = cfg.n_ff_exp;
        let fast = gu.iter().all(|m| m.gpu.is_some_and(|i| i != u32::MAX)).then(|| {
            let gu_y = matvec_many(&gu, cur, 0);
            let k = sel.len();
            let a: Vec<f32> = (0..k * nf).map(|i| act(gu_y[i], gu_y[k * nf + i], cfg.clamp_exp[il])).collect();
            let dm: Vec<_> = sel.iter().map(|s| l.dexps.expert(s.0, cfg.n_expert)).collect();
            matvec_many(&dm, &a, nf)
        });
        if let Some(dy) = &fast {
            PROF[3].fetch_add(1000 * sel.len() as u64, std::sync::atomic::Ordering::Relaxed);
            for (i, &(_, w)) in sel.iter().enumerate() { for j in 0..n { out[j] += w * dy[i * n + j]; } }
        }
        for (e, w) in sel.into_iter().filter(|_| fast.is_none()) {
            let ge = l.gexps.expert(e, cfg.n_expert);
            PROF[3].fetch_add((ge.gpu.is_some_and(|i| i != u32::MAX)) as u64 * 1000, std::sync::atomic::Ordering::Relaxed);
            ge.matvec(cur, &mut g);
            l.uexps.expert(e, cfg.n_expert).matvec(cur, &mut u);
            for j in 0..g.len() { g[j] = act(g[j], u[j], cfg.clamp_exp[il]); }
            l.dexps.expert(e, cfg.n_expert).matvec(&g, &mut d);
            for j in 0..n { out[j] += w * d[j]; }
        }
        PROF[1].fetch_add(t1.elapsed().as_micros() as u64, std::sync::atomic::Ordering::Relaxed);
        PROF[0].fetch_add((t1 - t0).as_micros() as u64, std::sync::atomic::Ordering::Relaxed);
        self.tr("ffn_moe_out", il as i32, &out);
        let fs = cfg.n_ff_exp * cfg.n_shared;
        let (mut g, mut u, mut d) = (vec![0f32; fs], vec![0f32; fs], vec![0f32; n]);
        l.gsh.matvec(cur, &mut g);
        l.ush.matvec(cur, &mut u);
        for j in 0..fs { g[j] = act(g[j], u[j], cfg.clamp_shexp[il]); }
        l.dsh.matvec(&g, &mut d);
        self.tr("ffn_shexp", il as i32, &d);
        for j in 0..n { out[j] += d[j]; }
        out
    }

    /// Feed one token at the next position; returns logits.
    pub fn step(&mut self, tok: u32) -> Vec<f32> { self.step_opt(tok, true) }

    /// Feed prompt tokens; only the last one computes logits (the vocab matvec is wasted on the rest).
    pub fn prefill(&mut self, toks: &[u32]) -> Vec<f32> {
        let mut logits = vec![];
        for (i, &t) in toks.iter().enumerate() { logits = self.step_opt(t, i + 1 == toks.len()); }
        logits
    }

    fn step_opt(&mut self, tok: u32, want: bool) -> Vec<f32> {
        let t_all = std::time::Instant::now();
        let pos = self.toks.len();
        self.toks.push(tok);
        let n = self.cfg.n_embd;
        let mut emb = vec![0f32; n];
        self.tok_embd.row_into(tok as usize, &mut emb);
        let mut x: Vec<f32> = (0..4).flat_map(|_| emb.iter().cloned()).collect();
        self.tr("hc_init", -1, &x);
        self.pre_prev = [1.0, 0.0, 0.0, 0.0];
        let (mut cur, mut nrm) = (vec![0f32; n], vec![0f32; n]);
        for il in 0..self.cfg.n_layer {
            if let Some(e) = self.cfg.engram_index(il) {
                self.engram(e, il, pos, &mut x);
                self.tr("engram_out", il as i32, &x);
            }
            self.tr("layer_inp", il as i32, &x);
            let a = self.hc_mix(&self.layers[il].hc_attn, &x);
            hc_collapse(&x, &self.pre_prev, &mut cur);
            self.tr("hc_attn_pre", il as i32, &cur);
            rms_norm_w(&cur, &self.layers[il].attn_norm, self.cfg.eps, &mut nrm);
            self.tr("attn_norm", il as i32, &nrm);
            let ta = std::time::Instant::now();
            let att = self.attention(il, pos, &nrm);
            PROF[2].fetch_add(ta.elapsed().as_micros() as u64, std::sync::atomic::Ordering::Relaxed);
            self.tr("attn_out", il as i32, &att);
            let mut x2 = vec![0f32; 4 * n];
            hc_post(&att, &x, &a, &mut x2);
            x = x2;
            self.tr("hc_attn_post", il as i32, &x);
            let f = self.hc_mix(&self.layers[il].hc_ffn, &x);
            hc_collapse(&x, &a.pre, &mut cur);
            self.tr("hc_ffn_pre", il as i32, &cur);
            rms_norm_w(&cur, &self.layers[il].ffn_norm, self.cfg.eps, &mut nrm);
            self.tr("ffn_norm", il as i32, &nrm);
            let ff = self.ffn(il, &nrm);
            self.tr("ffn_out", il as i32, &ff);
            let mut x2 = vec![0f32; 4 * n];
            hc_post(&ff, &x, &f, &mut x2);
            x = x2;
            self.pre_prev = f.pre;
            self.tr("l_out", il as i32, &x);
        }
        if std::env::var_os("STRATA_DS_PROF").is_some() {
            let g = |i: usize| PROF[i].swap(0, std::sync::atomic::Ordering::Relaxed) as f64 / 1e3;
            let rb = std::fs::read_to_string("/proc/self/io").ok().and_then(|t| t.lines().find_map(|l| l.strip_prefix("read_bytes: ")?.trim().parse::<u64>().ok())).unwrap_or(0);
            eprintln!("disk_read_MB {} prof ms: route {:.0} experts {:.0} attn {:.0} vram-expert-lookups hit {} miss {} total {:.0}", rb >> 20, g(0), g(1), g(2), super::mat::EX_LOOKUPS[0].swap(0, std::sync::atomic::Ordering::Relaxed), super::mat::EX_LOOKUPS[1].swap(0, std::sync::atomic::Ordering::Relaxed), t_all.elapsed().as_secs_f64() * 1e3);
        }
        if !want { return vec![]; }
        hc_collapse(&x, &self.pre_prev, &mut cur);
        self.tr("hc_out", -1, &cur);
        rms_norm_w(&cur, &self.out_norm, self.cfg.eps, &mut nrm);
        self.tr("result_norm", -1, &nrm);
        let mut logits = vec![0f32; self.cfg.n_vocab];
        self.out_w.matvec(&nrm, &mut logits);
        self.tr("result_output", -1, &logits);
        logits
    }
}

static PROF: [std::sync::atomic::AtomicU64; 4] = [std::sync::atomic::AtomicU64::new(0), std::sync::atomic::AtomicU64::new(0), std::sync::atomic::AtomicU64::new(0), std::sync::atomic::AtomicU64::new(0)];
