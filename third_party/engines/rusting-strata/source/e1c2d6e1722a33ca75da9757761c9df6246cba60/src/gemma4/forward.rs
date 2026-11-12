//! Single-token CPU reference forward for Gemma 4 26B-A4B (mirrors llama.cpp gemma4.cpp). Matvecs use the GPU when enabled.
use super::Gemma4Config;
use crate::deepseek::mat::{Mat, vec_f32};
use crate::deepseek::ops::{rms_norm, rms_norm_w};
use crate::gguf::Gguf;
use anyhow::Result;
use rayon::prelude::*;

struct Layer<'a> {
    attn_norm: Vec<f32>,
    wq: Mat<'a>,
    wk: Mat<'a>,
    /// full-attention layers have no V projection: V = K before its norm
    wv: Option<Mat<'a>>,
    wo: Mat<'a>,
    q_norm: Vec<f32>,
    k_norm: Vec<f32>,
    post_attn_norm: Vec<f32>,
    ffn_norm: Vec<f32>,
    gate: Mat<'a>,
    up: Mat<'a>,
    down: Mat<'a>,
    post_ffw_norm: Vec<f32>,
    post_ffw_norm_1: Vec<f32>,
    pre_ffw_norm_2: Vec<f32>,
    post_ffw_norm_2: Vec<f32>,
    router: Mat<'a>,
    router_scale: Vec<f32>,
    gate_up: Mat<'a>,
    down_exps: Mat<'a>,
    down_scale: Vec<f32>,
    out_scale: f32,
}

#[derive(Default)]
struct Cache {
    k: Vec<f32>,
    v: Vec<f32>,
}

pub struct Gemma4Model<'a> {
    pub cfg: Gemma4Config,
    tok_embd: Mat<'a>,
    out_norm: Vec<f32>,
    /// proportional-rope frequency factors of the full-attention layers
    rope_freqs: Vec<f32>,
    layers: Vec<Layer<'a>>,
    cache: Vec<Cache>,
    pub toks: Vec<u32>,
    pub trace: bool,
}

fn gelu(x: f32) -> f32 {
    0.5 * x * (1.0 + (0.797_884_6 * x * (1.0 + 0.044715 * x * x)).tanh())
}

/// NEOX rope on one head: pairs (i, i + n_rot/2), theta = pos * base^(-2i/n_rot) / factor[i].
fn rope(x: &mut [f32], pos: usize, n_rot: usize, base: f32, factors: Option<&[f32]>) {
    let h = n_rot / 2;
    for i in 0..h {
        let mut theta = pos as f32 * base.powf(-2.0 * i as f32 / n_rot as f32);
        if let Some(f) = factors { theta /= f[i]; }
        let (s, c) = theta.sin_cos();
        let (a, b) = (x[i], x[i + h]);
        x[i] = a * c - b * s;
        x[i + h] = a * s + b * c;
    }
}

pub static PROF: [std::sync::atomic::AtomicU64; 6] = [const { std::sync::atomic::AtomicU64::new(0) }; 6];
fn lap(i: usize, t: &mut std::time::Instant) { PROF[i].fetch_add(t.elapsed().as_nanos() as u64, std::sync::atomic::Ordering::Relaxed); *t = std::time::Instant::now(); }

impl<'a> Gemma4Model<'a> {
    pub fn new(g: &'a Gguf) -> Result<Self> {
        let cfg = Gemma4Config::from_gguf(g)?;
        let mut layers = vec![];
        for il in 0..cfg.n_layer {
            let m = |n: &str| Mat::load(g, &format!("blk.{il}.{n}"));
            let v = |n: &str| vec_f32(g, &format!("blk.{il}.{n}"));
            layers.push(Layer {
                attn_norm: v("attn_norm.weight")?,
                wq: m("attn_q.weight")?,
                wk: m("attn_k.weight")?,
                wv: if g.tensors.contains_key(&format!("blk.{il}.attn_v.weight")) { Some(m("attn_v.weight")?) } else { None },
                wo: m("attn_output.weight")?,
                q_norm: v("attn_q_norm.weight")?,
                k_norm: v("attn_k_norm.weight")?,
                post_attn_norm: v("post_attention_norm.weight")?,
                ffn_norm: v("ffn_norm.weight")?,
                gate: m("ffn_gate.weight")?,
                up: m("ffn_up.weight")?,
                down: m("ffn_down.weight")?,
                post_ffw_norm: v("post_ffw_norm.weight")?,
                post_ffw_norm_1: v("post_ffw_norm_1.weight")?,
                pre_ffw_norm_2: v("pre_ffw_norm_2.weight")?,
                post_ffw_norm_2: v("post_ffw_norm_2.weight")?,
                router: m("ffn_gate_inp.weight")?,
                router_scale: v("ffn_gate_inp.scale")?,
                gate_up: m("ffn_gate_up_exps.weight")?,
                down_exps: m("ffn_down_exps.weight")?,
                down_scale: v("ffn_down_exps.scale")?,
                out_scale: v("layer_output_scale.weight")?[0],
            });
        }
        let n = cfg.n_layer;
        Ok(Gemma4Model {
            tok_embd: Mat::load(g, "token_embd.weight")?,
            out_norm: vec_f32(g, "output_norm.weight")?,
            rope_freqs: vec_f32(g, "rope_freqs.weight")?,
            layers,
            cache: (0..n).map(|_| Cache::default()).collect(),
            toks: vec![],
            trace: std::env::var("STRATA_G4_TRACE").is_ok(),
            cfg,
        })
    }

    pub fn reset(&mut self) {
        self.cache.iter_mut().for_each(|c| { c.k.clear(); c.v.clear(); });
        self.toks.clear();
    }

    fn tr(&self, name: &str, il: i32, v: &[f32]) {
        if let Ok(dir) = std::env::var("STRATA_G4_DUMP") {
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

    /// Attention of one token at position `pos` (the cache holds `pos` earlier rows). Returns the output projection.
    fn attn(&mut self, il: usize, h: &[f32], pos: usize) -> Vec<f32> {
        let cfg = &self.cfg;
        let (nh, nkv, hd) = (cfg.n_head, cfg.n_kv[il], cfg.hd(il));
        let swa = cfg.swa[il];
        let l = &self.layers[il];
        let (base, factors) = if swa { (cfg.base_swa, None) } else { (cfg.base_full, Some(&self.rope_freqs[..])) };
        let ms: Vec<_> = [Some(l.wq), Some(l.wk), l.wv].into_iter().flatten().collect();
        let qkv = crate::deepseek::mat::matvec_many(&ms, h, 0);
        let (q, kv) = qkv.split_at(nh * hd);
        let mut q = q.to_vec();
        let mut kraw = kv[..nkv * hd].to_vec();
        let mut vraw = if l.wv.is_some() { kv[nkv * hd..].to_vec() } else { kraw.clone() };
        let mut tmp = vec![0f32; hd];
        for hq in q.chunks_exact_mut(hd) {
            rms_norm_w(hq, &l.q_norm, cfg.eps, &mut tmp);
            hq.copy_from_slice(&tmp);
            rope(hq, pos, hd, base, factors);
        }
        for hk in kraw.chunks_exact_mut(hd) {
            rms_norm_w(hk, &l.k_norm, cfg.eps, &mut tmp);
            hk.copy_from_slice(&tmp);
            rope(hk, pos, hd, base, factors);
        }
        for hv in vraw.chunks_exact_mut(hd) {
            rms_norm(hv, cfg.eps, &mut tmp);
            hv.copy_from_slice(&tmp);
        }
        let c = &mut self.cache[il];
        c.k.extend_from_slice(&kraw);
        c.v.extend_from_slice(&vraw);
        let lo = if swa { (pos + 1).saturating_sub(cfg.window) } else { 0 };
        let rep = nh / nkv;
        let (ck, cv) = (&c.k, &c.v);
        let mut o = vec![0f32; nh * hd];
        o.par_chunks_mut(hd).enumerate().for_each(|(hq, oh)| {
            let kvh = hq / rep;
            let qh = &q[hq * hd..(hq + 1) * hd];
            let mut sc: Vec<f32> = (lo..=pos).map(|p| {
                let kp = &ck[(p * nkv + kvh) * hd..(p * nkv + kvh + 1) * hd];
                qh.iter().zip(kp).map(|(a, b)| a * b).sum::<f32>()
            }).collect();
            let mx = sc.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let mut sum = 0f32;
            sc.iter_mut().for_each(|s| { *s = (*s - mx).exp(); sum += *s; });
            for (i, p) in (lo..=pos).enumerate() {
                let w = sc[i] / sum;
                let vp = &cv[(p * nkv + kvh) * hd..(p * nkv + kvh + 1) * hd];
                oh.iter_mut().zip(vp).for_each(|(o, v)| *o += w * v);
            }
        });
        self.tr("attn_core", il as i32, &o);
        let mut out = vec![0f32; cfg.n_embd];
        self.layers[il].wo.matvec(&o, &mut out);
        out
    }

    /// Dense FFN + routed experts for one token (`x` = attention output with residual).
    fn ffn(&self, il: usize, x: &[f32]) -> Vec<f32> {
        let cfg = &self.cfg;
        let (n, eps) = (cfg.n_embd, cfg.eps);
        let l = &self.layers[il];
        let mut nrm = vec![0f32; n];
        rms_norm_w(x, &l.ffn_norm, eps, &mut nrm);
        let gu = crate::deepseek::mat::matvec_many(&[l.gate, l.up], &nrm, 0);
        let (mut g, u) = (gu[..cfg.n_ff].to_vec(), &gu[cfg.n_ff..]);
        g.iter_mut().zip(u).for_each(|(g, u)| *g = gelu(*g) * u);
        let mut mlp = vec![0f32; n];
        l.down.matvec(&g, &mut mlp);
        let mut mlp_n = vec![0f32; n];
        rms_norm_w(&mlp, &l.post_ffw_norm_1, eps, &mut mlp_n);
        self.tr("ffn_mlp", il as i32, &mlp_n);

        // router sees the unweighted-normed attention output scaled by 1/sqrt(n_embd) and the learned scale
        let mut t = vec![0f32; n];
        rms_norm(x, eps, &mut t);
        let s = 1.0 / (n as f32).sqrt();
        t.iter_mut().zip(&l.router_scale).for_each(|(t, w)| *t *= s * w);
        let mut logits = vec![0f32; cfg.n_expert];
        l.router.matvec(&t, &mut logits);
        self.tr("ffn_moe_logits", il as i32, &logits);
        let sel = route(&logits, cfg.n_used);
        let ids: Vec<f32> = sel.iter().map(|s| s.0 as f32).collect();
        self.tr("ffn_moe_topk", il as i32, &ids);

        let mut t1 = std::time::Instant::now();
        let mut moe_in = vec![0f32; n];
        rms_norm_w(x, &l.pre_ffw_norm_2, eps, &mut moe_in);
        lap(3, &mut t1);
        let nf = cfg.n_ff_exp;
        let mut moe = vec![0f32; n];
        let mut cpu_sel = vec![];
        let mut gpu_sel = vec![];
        for (e, w) in sel {
            let (gu_m, dn_m) = (l.gate_up.expert(e, cfg.n_expert), l.down_exps.expert(e, cfg.n_expert));
            let sc = w * l.down_scale[e];
            if gu_m.gpu.is_some() || dn_m.gpu.is_some() { gpu_sel.push((gu_m, dn_m, sc)); } else { cpu_sel.push((gu_m, dn_m, sc)); }
        }
        if !gpu_sel.is_empty() {
            use crate::deepseek::mat::matvec_many;
            let gms: Vec<_> = gpu_sel.iter().map(|g| g.0).collect();
            let dms: Vec<_> = gpu_sel.iter().map(|g| g.1).collect();
            let gu = matvec_many(&gms, &moe_in, 0);
            let act: Vec<f32> = (0..gpu_sel.len()).flat_map(|i| { let g = &gu[i * 2 * nf..(i + 1) * 2 * nf]; (0..nf).map(move |j| gelu(g[j]) * g[nf + j]) }).collect();
            let d = matvec_many(&dms, &act, nf);
            for (i, g) in gpu_sel.iter().enumerate() {
                moe.iter_mut().zip(&d[i * n..(i + 1) * n]).for_each(|(m, d)| *m += g.2 * d);
            }
        }
        lap(4, &mut t1);
        if !cpu_sel.is_empty() {
            for (g, d, _) in &cpu_sel { g.prefetch_expert(0, 1); d.prefetch_expert(0, 1); }
            use crate::cpu_moe::{int_dot, quantize_q8k};
            use rayon::prelude::*;
            let k = cpu_sel.len();
            let (dgu, ddn) = (int_dot(cpu_sel[0].0.ty).unwrap(), int_dot(cpu_sel[0].1.ty).unwrap());
            let xq = quantize_q8k(&moe_in);
            let mut gu = vec![0f32; k * 2 * nf];
            gu.par_chunks_mut(16).enumerate().for_each(|(c, ys)| for (j, v) in ys.iter_mut().enumerate() {
                let i = c * 16 + j;
                let (m, r) = (&cpu_sel[i / (2 * nf)].0, i % (2 * nf));
                let rb = m.data.len() / m.rows;
                *v = dgu(&m.data[r * rb..(r + 1) * rb], &xq);
            });
            let aq: Vec<_> = (0..k).map(|i| {
                let g = &gu[i * 2 * nf..(i + 1) * 2 * nf];
                let act: Vec<f32> = (0..nf).map(|j| gelu(g[j]) * g[nf + j]).collect();
                quantize_q8k(&act)
            }).collect();
            let mut dv = vec![0f32; k * n];
            dv.par_chunks_mut(16).enumerate().for_each(|(c, ys)| for (j, v) in ys.iter_mut().enumerate() {
                let i = c * 16 + j;
                let (m, r) = (&cpu_sel[i / n].1, i % n);
                let rb = m.data.len() / m.rows;
                *v = ddn(&m.data[r * rb..(r + 1) * rb], &aq[i / n]);
            });
            for (i, (_, _, sc)) in cpu_sel.iter().enumerate() {
                moe.iter_mut().zip(&dv[i * n..(i + 1) * n]).for_each(|(m, d)| *m += sc * d);
            }
        }
        lap(5, &mut t1);
        PROF[3].fetch_add(0, std::sync::atomic::Ordering::Relaxed);
        let mut moe_n = vec![0f32; n];
        rms_norm_w(&moe, &l.post_ffw_norm_2, eps, &mut moe_n);
        self.tr("ffn_moe", il as i32, &moe_n);
        let sum: Vec<f32> = mlp_n.iter().zip(&moe_n).map(|(a, b)| a + b).collect();
        let mut out = vec![0f32; n];
        rms_norm_w(&sum, &l.post_ffw_norm, eps, &mut out);
        out
    }

    pub fn step(&mut self, tok: u32) -> Vec<f32> {
        self.step_opt(tok, true)
    }

    pub fn prefill(&mut self, toks: &[u32]) -> Vec<f32> {
        if toks.is_empty() { return vec![]; }
        let (head, last) = toks.split_at(toks.len() - 1);
        for &t in head { self.step_opt(t, false); }
        self.step_opt(last[0], true)
    }

    fn step_opt(&mut self, tok: u32, want: bool) -> Vec<f32> {
        let n = self.cfg.n_embd;
        let pos = self.toks.len();
        self.toks.push(tok);
        let mut x = vec![0f32; n];
        self.tok_embd.row_into(tok as usize, &mut x);
        let sc = (n as f32).sqrt();
        x.iter_mut().for_each(|v| *v *= sc);
        self.tr("inp_scaled", -1, &x);
        let mut nrm = vec![0f32; n];
        for il in 0..self.cfg.n_layer {
            rms_norm_w(&x, &self.layers[il].attn_norm, self.cfg.eps, &mut nrm);
            let mut t0 = std::time::Instant::now();
            let a = self.attn(il, &nrm, pos);
            lap(0, &mut t0);
            let mut an = vec![0f32; n];
            rms_norm_w(&a, &self.layers[il].post_attn_norm, self.cfg.eps, &mut an);
            an.iter_mut().zip(&x).for_each(|(a, x)| *a += x);
            self.tr("attn_out", il as i32, &an);
            let f = self.ffn(il, &an);
            lap(1, &mut t0);
            let os = self.layers[il].out_scale;
            x = an.iter().zip(&f).map(|(a, f)| (a + f) * os).collect();
            self.tr("l_out", il as i32, &x);
        }
        if !want { return vec![]; }
        let mut t0 = std::time::Instant::now();
        rms_norm_w(&x, &self.out_norm, self.cfg.eps, &mut nrm);
        self.tr("result_norm", -1, &nrm);
        let mut logits = vec![0f32; self.cfg.n_vocab];
        self.tok_embd.matvec(&nrm, &mut logits);
        let cap = self.cfg.softcap;
        if cap > 0.0 { logits.iter_mut().for_each(|l| *l = cap * (*l / cap).tanh()); }
        lap(2, &mut t0);
        self.tr("result_output", -1, &logits);
        logits
    }
}

/// softmax over all experts, top `k` by probability (ties to the lower index), weights = their probs normalised by the sum (clamped like ggml).
pub fn route(logits: &[f32], k: usize) -> Vec<(usize, f32)> {
    let mx = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
    let mut p: Vec<f32> = logits.iter().map(|&l| (l - mx).exp()).collect();
    let s: f32 = p.iter().sum();
    p.iter_mut().for_each(|v| *v /= s);
    let mut idx: Vec<usize> = (0..p.len()).collect();
    idx.sort_by(|&a, &b| p[b].partial_cmp(&p[a]).unwrap().then(a.cmp(&b)));
    idx.truncate(k);
    let sum = idx.iter().map(|&i| p[i]).sum::<f32>().max(6.103_515_6e-5);
    idx.into_iter().map(|i| (i, p[i] / sum)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn route_normalises_top_k() {
        let r = route(&[0.0, 2.0, 1.0, 2.0], 2);
        assert_eq!(r.iter().map(|x| x.0).collect::<Vec<_>>(), vec![1, 3]);
        assert!((r.iter().map(|x| x.1).sum::<f32>() - 1.0).abs() < 1e-6);
    }
    #[test]
    fn rope_pos0_is_identity() {
        let mut x = [1.0, 2.0, 3.0, 4.0];
        rope(&mut x, 0, 4, 10000.0, None);
        assert_eq!(x, [1.0, 2.0, 3.0, 4.0]);
    }
}
