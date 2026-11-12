//! Slow single-token CPU reference forward for GLM-5.3-Flash (mirrors llama.cpp glm5-next.cpp).
//! Not implemented: the k-pool indexer top-k (it selects everything while the context is <= idx_top_k tokens, so
//! longer contexts are rejected) and the NextN/MTP block.
use super::{GlmConfig, LayerKind};
use crate::deepseek::mat::{Mat, vec_f32};
use crate::deepseek::ops::*;
use crate::gguf::Gguf;
use anyhow::Result;
use rayon::prelude::*;

struct Hcw<'a> {
    f: Mat<'a>,
    base: Vec<f32>,
    scale: Vec<f32>,
}

struct Kda<'a> {
    wq: Mat<'a>,
    wk: Mat<'a>,
    wv: Mat<'a>,
    wo: Mat<'a>,
    /// depthwise conv taps, [channel * conv_k + tap]
    conv: [Vec<f32>; 3],
    dt_b: Vec<f32>,
    a: Vec<f32>,
    beta: Mat<'a>,
    f_a: Mat<'a>,
    f_b: Mat<'a>,
    g_a: Mat<'a>,
    g_b: Mat<'a>,
    norm: Vec<f32>,
}

struct Dsa<'a> {
    q_a: Mat<'a>,
    q_a_norm: Vec<f32>,
    q_b: Mat<'a>,
    kv_a: Mat<'a>,
    kv_a_norm: Vec<f32>,
    k_b: Mat<'a>,
    v_b: Mat<'a>,
    wo: Mat<'a>,
    /// k-pool indexer
    ix_k: Mat<'a>,
    ix_qb: Mat<'a>,
    ix_proj: Mat<'a>,
    ix_gate: Mat<'a>,
    ix_kn_w: Vec<f32>,
    ix_kn_b: Vec<f32>,
    /// [kpool][head_dim]
    ix_ape: Vec<f32>,
}

enum Mixer<'a> {
    Kda(Kda<'a>),
    Dsa(Dsa<'a>),
}

enum Ffn<'a> {
    Dense { gate: Mat<'a>, up: Mat<'a>, down: Mat<'a> },
    Moe { gate_inp: Mat<'a>, bias: Vec<f32>, g: Mat<'a>, u: Mat<'a>, d: Mat<'a>, gsh: Mat<'a>, ush: Mat<'a>, dsh: Mat<'a> },
}

struct Layer<'a> {
    attn_norm: Vec<f32>,
    ffn_norm: Vec<f32>,
    hc_attn: Hcw<'a>,
    hc_ffn: Hcw<'a>,
    mixer: Mixer<'a>,
    ffn: Ffn<'a>,
}

/// Recurrent / cached state of one layer.
#[derive(Default)]
struct State {
    /// KDA: last conv_k-1 projected inputs for q, k, v; [3][tap][channel].
    conv: Vec<f32>,
    /// KDA: [head][key channel][value channel]
    s: Vec<f32>,
    /// DSA: latent rows
    lat: Vec<Vec<f32>>,
    /// DSA indexer: per-position normed key and pool gate [pos][dim], and pooled keys of the complete pools [pool][dim]
    ik: Vec<f32>,
    ig: Vec<f32>,
    pooled: Vec<f32>,
}

pub struct GlmModel<'a> {
    pub cfg: GlmConfig,
    tok_embd: Mat<'a>,
    out_norm: Vec<f32>,
    out_w: Mat<'a>,
    layers: Vec<Layer<'a>>,
    state: Vec<State>,
    pub toks: Vec<u32>,
    pub trace: bool,
}

/// Context limit: the trained context unless `STRATA_GLM_CTX` says otherwise. Beyond `idx_top_k` the k-pool indexer
/// selects rows; that path is checked against llama.cpp up to ~3.6k tokens. The KV cache grows with the sequence, so RAM is the real bound.
pub fn max_ctx(cfg: &GlmConfig) -> usize {
    std::env::var("STRATA_GLM_CTX").ok().and_then(|v| v.parse().ok()).unwrap_or(cfg.n_ctx_train)
}

fn silu(x: f32) -> f32 {
    x / (1.0 + (-x).exp())
}
fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + (-x).exp())
}

/// x / max(||x||, eps), in place (ggml l2_norm).
fn l2_norm(x: &mut [f32], eps: f32) {
    let s = 1.0 / x.iter().map(|v| v * v).sum::<f32>().sqrt().max(eps);
    x.iter_mut().for_each(|v| *v *= s);
}

impl<'a> GlmModel<'a> {
    pub fn new(g: &'a Gguf) -> Result<Self> {
        let cfg = GlmConfig::from_gguf(g)?;
        let mut layers = vec![];
        for il in 0..cfg.n_layer {
            let m = |n: &str| Mat::load(g, &format!("blk.{il}.{n}"));
            let v = |n: &str| vec_f32(g, &format!("blk.{il}.{n}"));
            let hcw = |s: &str| -> Result<Hcw> { Ok(Hcw { f: m(&format!("hc_{s}_fn.weight"))?, base: v(&format!("hc_{s}_base.weight"))?, scale: v(&format!("hc_{s}_scale.weight"))? }) };
            let mixer = match cfg.kind[il] {
                LayerKind::Kda => Mixer::Kda(Kda {
                    wq: m("attn_q.weight")?, wk: m("attn_k.weight")?, wv: m("attn_v.weight")?, wo: m("attn_output.weight")?,
                    conv: [v("ssm_conv1d_q.weight")?, v("ssm_conv1d_k.weight")?, v("ssm_conv1d_v.weight")?],
                    dt_b: v("ssm_dt.bias")?, a: v("ssm_a")?, beta: m("ssm_beta.weight")?,
                    f_a: m("ssm_f_a.weight")?, f_b: m("ssm_f_b.weight")?, g_a: m("ssm_g_a.weight")?, g_b: m("ssm_g_b.weight")?, norm: v("ssm_norm.weight")?,
                }),
                LayerKind::Dsa => Mixer::Dsa(Dsa {
                    q_a: m("attn_q_a.weight")?, q_a_norm: v("attn_q_a_norm.weight")?, q_b: m("attn_q_b.weight")?,
                    kv_a: m("attn_kv_a_mqa.weight")?, kv_a_norm: v("attn_kv_a_norm.weight")?,
                    k_b: m("attn_k_b.weight")?, v_b: m("attn_v_b.weight")?, wo: m("attn_output.weight")?,
                    ix_k: m("indexer.attn_k.weight")?, ix_qb: m("indexer.attn_q_b.weight")?, ix_proj: m("indexer.proj.weight")?, ix_gate: m("indexer_compressor_gate.weight")?,
                    ix_kn_w: v("indexer.k_norm.weight")?, ix_kn_b: v("indexer.k_norm.bias")?, ix_ape: v("indexer_compressor_ape.weight")?,
                }),
            };
            let ffn = if il < cfg.n_dense {
                Ffn::Dense { gate: m("ffn_gate.weight")?, up: m("ffn_up.weight")?, down: m("ffn_down.weight")? }
            } else {
                Ffn::Moe {
                    gate_inp: m("ffn_gate_inp.weight")?, bias: v("exp_probs_b.bias")?,
                    g: m("ffn_gate_exps.weight")?, u: m("ffn_up_exps.weight")?, d: m("ffn_down_exps.weight")?,
                    gsh: m("ffn_gate_shexp.weight")?, ush: m("ffn_up_shexp.weight")?, dsh: m("ffn_down_shexp.weight")?,
                }
            };
            layers.push(Layer { attn_norm: v("attn_norm.weight")?, ffn_norm: v("ffn_norm.weight")?, hc_attn: hcw("attn")?, hc_ffn: hcw("ffn")?, mixer, ffn });
        }
        let n = cfg.n_layer;
        Ok(GlmModel {
            tok_embd: Mat::load(g, "token_embd.weight")?, out_norm: vec_f32(g, "output_norm.weight")?, out_w: Mat::load(g, "output.weight")?,
            layers, state: (0..n).map(|_| State::default()).collect(), toks: vec![], trace: std::env::var("STRATA_GLM_TRACE").is_ok(), cfg,
        })
    }

    /// Forget the whole sequence (new conversation).
    pub fn reset(&mut self) {
        self.state.iter_mut().for_each(|s| *s = State::default());
        self.toks.clear();
    }

    fn tr(&self, name: &str, il: i32, v: &[f32]) {
        if let Ok(dir) = std::env::var("STRATA_GLM_DUMP") {
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

    fn hc_mix(&self, h: &Hcw, x: &[f32]) -> Hc {
        let mut xn = vec![0f32; x.len()];
        rms_norm(x, self.cfg.eps, &mut xn);
        let mut mixes = vec![0f32; 24];
        h.f.matvec(&xn, &mut mixes);
        hc_coeffs(&mixes, &h.scale, &h.base, self.cfg.hc_eps, self.cfg.hc_iters)
    }

    /// Kimi Delta Attention for one token.
    fn kda(&mut self, il: usize, cur: &[f32]) -> Vec<f32> {
        let cfg = &self.cfg;
        let Mixer::Kda(w) = &self.layers[il].mixer else { unreachable!() };
        let (nh, hd, ck) = (cfg.n_head, cfg.kda_head_dim, cfg.conv_k);
        let di = nh * hd;
        let st = &mut self.state[il];
        if st.conv.is_empty() {
            st.conv = vec![0.0; 3 * (ck - 1) * di];
            st.s = vec![0.0; nh * hd * hd];
        }
        // q/k/v: projection, causal depthwise conv over [ck-1 previous inputs, current], silu
        let mut qkv = [vec![0f32; di], vec![0f32; di], vec![0f32; di]];
        for (i, m) in [&w.wq, &w.wk, &w.wv].into_iter().enumerate() {
            let mut p = vec![0f32; di];
            m.matvec(cur, &mut p);
            let hist = &mut st.conv[i * (ck - 1) * di..(i + 1) * (ck - 1) * di];
            for c in 0..di {
                let mut acc = 0.0;
                for t in 0..ck - 1 {
                    acc += w.conv[i][c * ck + t] * hist[t * di + c];
                }
                acc += w.conv[i][c * ck + ck - 1] * p[c];
                qkv[i][c] = silu(acc);
            }
            hist.copy_within(di.., 0);
            hist[(ck - 2) * di..].copy_from_slice(&p);
        }
        let [mut q, mut k, v] = qkv;
        for h in 0..nh {
            l2_norm(&mut q[h * hd..(h + 1) * hd], 1e-6);
            l2_norm(&mut k[h * hd..(h + 1) * hd], 1e-6);
        }
        self.tr("kda_q_conv", il as i32, &q);
        // decay gate g = lower_bound * sigmoid(-(g1 * A)), per key channel
        let mut fa = vec![0f32; hd];
        w.f_a.matvec(cur, &mut fa);
        let mut g1 = vec![0f32; di];
        w.f_b.matvec(&fa, &mut g1);
        let lb = cfg.gate_lower_bound;
        for c in 0..di {
            g1[c] = lb * sigmoid(-((g1[c] + w.dt_b[c]) * w.a[c / hd]));
        }
        let mut beta = vec![0f32; nh];
        w.beta.matvec(cur, &mut beta);
        beta.iter_mut().for_each(|b| *b = sigmoid(*b));
        // recurrence per head: S = diag(exp(g)) S; S += k (beta (v - S^T k))^T; o = S^T q / sqrt(hd)
        let scale = 1.0 / (hd as f32).sqrt();
        let mut o = vec![0f32; di];
        let s = &mut self.state[il].s;
        s.par_chunks_mut(hd * hd).zip(o.par_chunks_mut(hd)).enumerate().for_each(|(h, (sh, oh))| {
            let (qh, kh, vh, gh) = (&q[h * hd..(h + 1) * hd], &k[h * hd..(h + 1) * hd], &v[h * hd..(h + 1) * hd], &g1[h * hd..(h + 1) * hd]);
            let mut kv = vec![0f32; hd];
            for i in 0..hd {
                let e = gh[i].exp();
                for j in 0..hd {
                    sh[i * hd + j] *= e;
                    kv[j] += sh[i * hd + j] * kh[i];
                }
            }
            let d: Vec<f32> = (0..hd).map(|j| (vh[j] - kv[j]) * beta[h]).collect();
            for i in 0..hd {
                for j in 0..hd {
                    sh[i * hd + j] += kh[i] * d[j];
                    oh[j] += sh[i * hd + j] * qh[i];
                }
            }
            oh.iter_mut().for_each(|v| *v *= scale);
        });
        self.tr("kda_scan_out", il as i32, &o);
        // output gate: rms_norm(o) * sigmoid(g_b(g_a x))
        let mut ga = vec![0f32; hd];
        w.g_a.matvec(cur, &mut ga);
        let mut g2 = vec![0f32; di];
        w.g_b.matvec(&ga, &mut g2);
        let mut gated = vec![0f32; di];
        for h in 0..nh {
            rms_norm_w(&o[h * hd..(h + 1) * hd], &w.norm, cfg.eps, &mut gated[h * hd..(h + 1) * hd]);
        }
        for c in 0..di {
            gated[c] *= sigmoid(g2[c]);
        }
        let mut res = vec![0f32; cfg.n_embd];
        w.wo.matvec(&gated, &mut res);
        res
    }

    /// Nope MLA with absorbed K/V over the latent cache. All previous tokens are visible (context <= idx_top_k).
    fn dsa(&mut self, il: usize, cur: &[f32]) -> Vec<f32> {
        let cfg = &self.cfg;
        let Mixer::Dsa(w) = &self.layers[il].mixer else { unreachable!() };
        let (nh, kd, kl) = (cfg.n_head, cfg.k_mla, cfg.kv_lora);
        let mut qa = vec![0f32; cfg.q_lora];
        w.q_a.matvec(cur, &mut qa);
        let mut qr = vec![0f32; cfg.q_lora];
        rms_norm_w(&qa, &w.q_a_norm, cfg.eps, &mut qr);
        let mut q = vec![0f32; nh * kd];
        w.q_b.matvec(&qr, &mut q);
        let mut kv = vec![0f32; kl];
        w.kv_a.matvec(cur, &mut kv);
        let mut lat = vec![0f32; kl];
        rms_norm_w(&kv, &w.kv_a_norm, cfg.eps, &mut lat);
        self.tr("kv_cmpr", il as i32, &lat);
        // indexer key (layer norm) and pool gate of this position
        let (hd, nih, kp) = (cfg.idx_head_dim, cfg.idx_n_head, cfg.kpool);
        let mut ik = vec![0f32; hd];
        w.ix_k.matvec(cur, &mut ik);
        let mean = ik.iter().sum::<f32>() / hd as f32;
        let var = ik.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / hd as f32;
        let inv = 1.0 / (var + cfg.kda_eps).sqrt();
        ik.iter_mut().enumerate().for_each(|(i, v)| *v = (*v - mean) * inv * w.ix_kn_w[i] + w.ix_kn_b[i]);
        let mut ig = vec![0f32; hd];
        w.ix_gate.matvec(cur, &mut ig);
        let st = &mut self.state[il];
        st.lat.push(lat);
        st.ik.extend_from_slice(&ik);
        st.ig.extend_from_slice(&ig);
        let pos = st.lat.len() - 1;
        if (pos + 1) % kp == 0 {
            // pooled key = sum over the pool of softmax_k(gate + ape) * key, per dimension
            let b0 = (pos + 1 - kp) * hd;
            for d in 0..hd {
                let l: Vec<f32> = (0..kp).map(|k| st.ig[b0 + k * hd + d] + w.ix_ape[k * hd + d]).collect();
                let mx = l.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
                let e: Vec<f32> = l.iter().map(|x| (x - mx).exp()).collect();
                let z: f32 = e.iter().sum();
                st.pooled.push((0..kp).map(|k| e[k] / z * st.ik[b0 + k * hd + d]).sum());
            }
        }
        // sparse selection: only beyond idx_top_k rows; the top idx_top_k/kpool pools by indexer score plus the incomplete tail
        let rows: Vec<usize> = if pos < cfg.idx_top_k {
            (0..=pos).collect()
        } else {
            let mut iq = vec![0f32; nih * hd];
            w.ix_qb.matvec(&qr, &mut iq);
            let mut wt = vec![0f32; nih];
            w.ix_proj.matvec(cur, &mut wt);
            let sc = 1.0 / ((hd * nih) as f32).sqrt();
            let nv = (pos + 1) / kp;
            let pooled = &st.pooled;
            let score: Vec<f32> = (0..nv)
                .into_par_iter()
                .map(|j| (0..nih).map(|h| iq[h * hd..(h + 1) * hd].iter().zip(&pooled[j * hd..(j + 1) * hd]).map(|(a, b)| a * b).sum::<f32>().max(0.0) * wt[h] * sc).sum())
                .collect();
            let mut order: Vec<usize> = (0..nv).collect();
            order.sort_by(|&a, &b| score[b].partial_cmp(&score[a]).unwrap().then(a.cmp(&b)));
            order.truncate(cfg.idx_top_k / kp);
            order.sort_unstable();
            order.iter().flat_map(|&j| j * kp..(j + 1) * kp).chain(nv * kp..=pos).collect()
        };
        let cache = &st.lat;
        let scale = 1.0 / (kd as f32).sqrt();
        let mut out = vec![0f32; nh * cfg.v_mla];
        let mut qabs = vec![0f32; nh * kl];
        for h in 0..nh {
            w.k_b.group(h, nh).matvec(&q[h * kd..(h + 1) * kd], &mut qabs[h * kl..(h + 1) * kl]);
        }
        let accs: Vec<Vec<f32>> = (0..nh)
            .into_par_iter()
            .map(|h| {
                let qa = &qabs[h * kl..(h + 1) * kl];
                let mut sc: Vec<f32> = rows.iter().map(|&i| cache[i].iter().zip(qa).map(|(a, b)| a * b).sum::<f32>() * scale).collect();
                let mx = sc.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
                let mut z = 0.0;
                for s in sc.iter_mut() {
                    *s = (*s - mx).exp();
                    z += *s;
                }
                let mut acc = vec![0f32; kl];
                for (s, &i) in sc.iter().zip(&rows) {
                    let (p, r) = (s / z, &cache[i]);
                    for j in 0..kl {
                        acc[j] += p * r[j];
                    }
                }
                acc
            })
            .collect();
        for h in 0..nh {
            w.v_b.group(h, nh).matvec(&accs[h], &mut out[h * cfg.v_mla..(h + 1) * cfg.v_mla]);
        }
        let mut res = vec![0f32; cfg.n_embd];
        w.wo.matvec(&out, &mut res);
        res
    }

    fn ffn(&self, il: usize, cur: &[f32]) -> Vec<f32> {
        let cfg = &self.cfg;
        let n = cfg.n_embd;
        let mut out = vec![0f32; n];
        match &self.layers[il].ffn {
            Ffn::Dense { gate, up, down } => {
                let (mut g, mut u) = (vec![0f32; cfg.n_ff], vec![0f32; cfg.n_ff]);
                gate.matvec(cur, &mut g);
                up.matvec(cur, &mut u);
                g.iter_mut().zip(&u).for_each(|(g, u)| *g = silu(*g) * u);
                down.matvec(&g, &mut out);
            }
            Ffn::Moe { gate_inp, bias, g: ge, u: ue, d: de, gsh, ush, dsh } => {
                let mut logits = vec![0f32; cfg.n_expert];
                gate_inp.matvec(cur, &mut logits);
                self.tr("ffn_moe_logits", il as i32, &logits);
                let sel = route_sigmoid(&logits, bias, cfg.n_used, cfg.weights_norm, cfg.weights_scale);
                let ids: Vec<f32> = sel.iter().map(|s| s.0 as f32).collect();
                self.tr("ffn_moe_topk", il as i32, &ids);
                for &(e, _) in &sel {
                    for m in [ge, ue, de] {
                        m.prefetch_expert(e, cfg.n_expert);
                    }
                }
                let nf = cfg.n_ff_exp;
                let (mut g, mut u, mut d) = (vec![0f32; nf], vec![0f32; nf], vec![0f32; n]);
                for (e, w) in sel {
                    ge.expert(e, cfg.n_expert).matvec(cur, &mut g);
                    ue.expert(e, cfg.n_expert).matvec(cur, &mut u);
                    for j in 0..nf {
                        g[j] = swiglu_clamp(g[j], u[j], cfg.clamp_exp[il]);
                    }
                    de.expert(e, cfg.n_expert).matvec(&g, &mut d);
                    for j in 0..n {
                        out[j] += w * d[j];
                    }
                }
                self.tr("ffn_moe_out", il as i32, &out);
                // shared expert: plain silu (llama.cpp builds it with build_ffn, no clamp)
                let fs = cfg.n_ff_exp * cfg.n_shared;
                let (mut g, mut u) = (vec![0f32; fs], vec![0f32; fs]);
                gsh.matvec(cur, &mut g);
                ush.matvec(cur, &mut u);
                g.iter_mut().zip(&u).for_each(|(g, u)| *g = silu(*g) * u);
                let mut d = vec![0f32; n];
                dsh.matvec(&g, &mut d);
                self.tr("ffn_shexp", il as i32, &d);
                for j in 0..n {
                    out[j] += d[j];
                }
            }
        }
        out
    }

    /// FFN for several tokens of one layer: each routed expert is loaded once and applied to every token that picked it.
    /// Per-token numerics equal `ffn` (expert outputs summed in the token's own selection order).
    fn ffn_batch(&self, il: usize, curs: &[Vec<f32>]) -> Vec<Vec<f32>> {
        let cfg = &self.cfg;
        let Ffn::Moe { gate_inp, bias, g: ge, u: ue, d: de, gsh, ush, dsh } = &self.layers[il].ffn else {
            return curs.iter().map(|c| self.ffn(il, c)).collect();
        };
        let (n, nf) = (cfg.n_embd, cfg.n_ff_exp);
        let sels: Vec<Vec<(usize, f32)>> = curs
            .iter()
            .map(|c| {
                let mut logits = vec![0f32; cfg.n_expert];
                gate_inp.matvec(c, &mut logits);
                route_sigmoid(&logits, bias, cfg.n_used, cfg.weights_norm, cfg.weights_scale)
            })
            .collect();
        let mut by_e: std::collections::BTreeMap<usize, Vec<(usize, usize)>> = Default::default();
        for (t, sel) in sels.iter().enumerate() {
            for (k, &(e, _)) in sel.iter().enumerate() {
                by_e.entry(e).or_default().push((t, k));
            }
        }
        for &e in by_e.keys() {
            for m in [ge, ue, de] {
                m.prefetch_expert(e, cfg.n_expert);
            }
        }
        let mut ds: Vec<Vec<Vec<f32>>> = sels.iter().map(|s| vec![vec![]; s.len()]).collect();
        let (mut g, mut u) = (vec![0f32; nf], vec![0f32; nf]);
        for (e, uses) in by_e {
            let (me_g, me_u, me_d) = (ge.expert(e, cfg.n_expert), ue.expert(e, cfg.n_expert), de.expert(e, cfg.n_expert));
            for (t, k) in uses {
                me_g.matvec(&curs[t], &mut g);
                me_u.matvec(&curs[t], &mut u);
                for j in 0..nf {
                    g[j] = swiglu_clamp(g[j], u[j], cfg.clamp_exp[il]);
                }
                let mut d = vec![0f32; n];
                me_d.matvec(&g, &mut d);
                ds[t][k] = d;
            }
        }
        let fs = nf * cfg.n_shared;
        curs.iter()
            .enumerate()
            .map(|(t, c)| {
                let mut out = vec![0f32; n];
                for (k, &(_, w)) in sels[t].iter().enumerate() {
                    for j in 0..n {
                        out[j] += w * ds[t][k][j];
                    }
                }
                let (mut g, mut u) = (vec![0f32; fs], vec![0f32; fs]);
                gsh.matvec(c, &mut g);
                ush.matvec(c, &mut u);
                g.iter_mut().zip(&u).for_each(|(g, u)| *g = silu(*g) * u);
                let mut d = vec![0f32; n];
                dsh.matvec(&g, &mut d);
                for j in 0..n {
                    out[j] += d[j];
                }
                out
            })
            .collect()
    }

    /// Layer-major pass over a chunk of prompt tokens (no logits).
    fn prefill_chunk(&mut self, toks: &[u32]) {
        let n = self.cfg.n_embd;
        assert!(self.toks.len() + toks.len() <= max_ctx(&self.cfg), "GLM context is limited to {} tokens ", max_ctx(&self.cfg));
        self.toks.extend_from_slice(toks);
        let mut xs: Vec<Vec<f32>> = toks
            .iter()
            .map(|&t| {
                let mut emb = vec![0f32; n];
                self.tok_embd.row_into(t as usize, &mut emb);
                (0..4).flat_map(|_| emb.iter().cloned()).collect()
            })
            .collect();
        let (mut cur, mut nrm) = (vec![0f32; n], vec![0f32; n]);
        let t0 = std::time::Instant::now();
        for il in 0..self.cfg.n_layer {
            for x in xs.iter_mut() {
                let a = self.hc_mix(&self.layers[il].hc_attn, x);
                hc_collapse(x, &a.pre, &mut cur);
                rms_norm_w(&cur, &self.layers[il].attn_norm, self.cfg.eps, &mut nrm);
                let att = match self.cfg.kind[il] {
                    LayerKind::Kda => self.kda(il, &nrm),
                    LayerKind::Dsa => self.dsa(il, &nrm),
                };
                let mut x2 = vec![0f32; 4 * n];
                hc_post(&att, x, &a, &mut x2);
                *x = x2;
            }
            let mut fs = vec![];
            let mut nrms = vec![];
            for x in xs.iter() {
                let f = self.hc_mix(&self.layers[il].hc_ffn, x);
                hc_collapse(x, &f.pre, &mut cur);
                rms_norm_w(&cur, &self.layers[il].ffn_norm, self.cfg.eps, &mut nrm);
                nrms.push(nrm.clone());
                fs.push(f);
            }
            let ffs = self.ffn_batch(il, &nrms);
            for ((x, f), ff) in xs.iter_mut().zip(&fs).zip(&ffs) {
                let mut x2 = vec![0f32; 4 * n];
                hc_post(ff, x, f, &mut x2);
                *x = x2;
            }
        }
        if std::env::var_os("STRATA_GLM_PROF").is_some() {
            eprintln!("PROF chunk {} toks, now {} total {:.0}ms", toks.len(), self.toks.len(), t0.elapsed().as_secs_f64() * 1e3);
        }
    }

    /// Feed one token at the next position; returns logits.
    pub fn step(&mut self, tok: u32) -> Vec<f32> {
        self.step_opt(tok, true)
    }

    /// Feed prompt tokens; only the last one computes logits.
    pub fn prefill(&mut self, toks: &[u32]) -> Vec<f32> {
        let chunk: usize = std::env::var("STRATA_GLM_CHUNK").ok().and_then(|v| v.parse().ok()).unwrap_or(512);
        if toks.is_empty() {
            return vec![];
        }
        let (head, last) = toks.split_at(toks.len() - 1);
        if chunk > 1 {
            for c in head.chunks(chunk) {
                self.prefill_chunk(c);
            }
        } else {
            for &t in head {
                self.step_opt(t, false);
            }
        }
        self.step_opt(last[0], true)
    }

    fn step_opt(&mut self, tok: u32, want: bool) -> Vec<f32> {
        let n = self.cfg.n_embd;
        assert!(self.toks.len() < max_ctx(&self.cfg), "GLM context is limited to {} tokens ", max_ctx(&self.cfg));
        self.toks.push(tok);
        let mut emb = vec![0f32; n];
        self.tok_embd.row_into(tok as usize, &mut emb);
        let mut x: Vec<f32> = (0..4).flat_map(|_| emb.iter().cloned()).collect();
        self.tr("hc_init", -1, &x);
        let (mut cur, mut nrm) = (vec![0f32; n], vec![0f32; n]);
        let (mut prof, tstep) = ([0f64; 2], std::time::Instant::now());
        for il in 0..self.cfg.n_layer {
            let a = self.hc_mix(&self.layers[il].hc_attn, &x);
            hc_collapse(&x, &a.pre, &mut cur);
            self.tr("hc_attn_pre", il as i32, &cur);
            rms_norm_w(&cur, &self.layers[il].attn_norm, self.cfg.eps, &mut nrm);
            self.tr("attn_norm", il as i32, &nrm);
            let t0 = std::time::Instant::now();
            let att = match self.cfg.kind[il] {
                LayerKind::Kda => self.kda(il, &nrm),
                LayerKind::Dsa => self.dsa(il, &nrm),
            };
            prof[0] += t0.elapsed().as_secs_f64();
            self.tr("attn_out", il as i32, &att);
            let mut x2 = vec![0f32; 4 * n];
            hc_post(&att, &x, &a, &mut x2);
            x = x2;
            self.tr("hc_attn_post", il as i32, &x);
            let f = self.hc_mix(&self.layers[il].hc_ffn, &x);
            hc_collapse(&x, &f.pre, &mut cur);
            self.tr("hc_ffn_pre", il as i32, &cur);
            rms_norm_w(&cur, &self.layers[il].ffn_norm, self.cfg.eps, &mut nrm);
            self.tr("ffn_norm", il as i32, &nrm);
            let t1 = std::time::Instant::now();
            let ff = self.ffn(il, &nrm);
            prof[1] += t1.elapsed().as_secs_f64();
            self.tr("ffn_out", il as i32, &ff);
            let mut x2 = vec![0f32; 4 * n];
            hc_post(&ff, &x, &f, &mut x2);
            x = x2;
            self.tr("l_out", il as i32, &x);
        }
        if std::env::var_os("STRATA_GLM_PROF").is_some() {
            let l = &crate::deepseek::mat::EX_LOOKUPS;
            let (h, m) = (l[0].swap(0, std::sync::atomic::Ordering::Relaxed), l[1].swap(0, std::sync::atomic::Ordering::Relaxed));
            eprintln!("PROF tok{} total {:.0}ms attn {:.0}ms ffn {:.0}ms expert-cache hit {h} miss {m}", self.toks.len(), tstep.elapsed().as_secs_f64() * 1e3, prof[0] * 1e3, prof[1] * 1e3);
        }
        if !want {
            return vec![];
        }
        hc_collapse(&x, &[0.25; 4], &mut cur);
        self.tr("hc_head", -1, &cur);
        rms_norm_w(&cur, &self.out_norm, self.cfg.eps, &mut nrm);
        self.tr("result_norm", -1, &nrm);
        let mut logits = vec![0f32; self.cfg.n_vocab];
        self.out_w.matvec(&nrm, &mut logits);
        self.tr("result_output", -1, &logits);
        logits
    }
}

/// Sigmoid router: probs = sigmoid(logit); pick top n_used by probs+bias (ties to the lower index);
/// weights = probs[sel], normalised by their sum (clamped like ggml), then scaled.
pub fn route_sigmoid(logits: &[f32], bias: &[f32], n_used: usize, norm: bool, scale: f32) -> Vec<(usize, f32)> {
    let probs: Vec<f32> = logits.iter().map(|&l| sigmoid(l)).collect();
    let mut idx: Vec<usize> = (0..probs.len()).collect();
    idx.sort_by(|&a, &b| (probs[b] + bias[b]).partial_cmp(&(probs[a] + bias[a])).unwrap().then(a.cmp(&b)));
    idx.truncate(n_used);
    let sum = idx.iter().map(|&i| probs[i]).sum::<f32>().max(6.103515625e-5);
    idx.into_iter().map(|i| (i, if norm { probs[i] / sum } else { probs[i] } * scale)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn router_picks_by_bias_weights_by_prob() {
        let mut logits = vec![-5.0; 8];
        logits[2] = 2.0;
        logits[6] = 1.0;
        let mut bias = vec![0.0; 8];
        bias[4] = 5.0;
        let r = route_sigmoid(&logits, &bias, 3, true, 2.5);
        assert_eq!(r.iter().map(|x| x.0).collect::<Vec<_>>(), vec![4, 2, 6]);
        assert!((r.iter().map(|x| x.1).sum::<f32>() - 2.5).abs() < 1e-5);
        assert!(r[0].1 < r[1].1); // expert 4 won on bias only, its prob is tiny
    }

    #[test]
    fn l2_norm_unit_and_floor() {
        let mut v = vec![3.0, 4.0];
        l2_norm(&mut v, 1e-6);
        assert!((v[0] - 0.6).abs() < 1e-6 && (v[1] - 0.8).abs() < 1e-6);
        let mut z = vec![0.0; 4];
        l2_norm(&mut z, 1e-6);
        assert_eq!(z, vec![0.0; 4]);
    }
}
