//! Small CPU f32 building blocks of the DeepSeek-V4.1 forward, mirroring llama.cpp deepseek41.cpp.

/// RMS norm without weight: x / sqrt(mean(x^2) + eps).
pub fn rms_norm(x: &[f32], eps: f32, out: &mut [f32]) {
    let ms = x.iter().map(|v| v * v).sum::<f32>() / x.len() as f32;
    let s = 1.0 / (ms + eps).sqrt();
    for (o, v) in out.iter_mut().zip(x) {
        *o = v * s;
    }
}

/// RMS norm then scale by weight.
pub fn rms_norm_w(x: &[f32], w: &[f32], eps: f32, out: &mut [f32]) {
    rms_norm(x, eps, out);
    for (o, w) in out.iter_mut().zip(w) {
        *o *= w;
    }
}

/// ggml YaRN rope parameters for one layer kind.
#[derive(Clone, Copy, Debug)]
pub struct Rope {
    pub base: f32,
    pub freq_scale: f32,
    pub ext: f32,
    pub corr: [f32; 2],
    /// rotated dims (64)
    pub n_dims: usize,
}

impl Rope {
    pub fn new(base: f32, freq_scale: f32, ext: f32, n_dims: usize, n_ctx_orig: u32, beta_fast: f32, beta_slow: f32) -> Self {
        let cd = |n_rot: f32| n_dims as f32 * (n_ctx_orig as f32 / (n_rot * 2.0 * std::f32::consts::PI)).ln() / (2.0 * base.ln());
        let corr = if ext != 0.0 {
            [cd(beta_fast).floor().max(0.0), cd(beta_slow).ceil().min(n_dims as f32 - 1.0)]
        } else {
            [0.0, 0.0]
        };
        Rope { base, freq_scale, ext, corr, n_dims }
    }

    /// (cos, sin) for pair index i (dim 2i,2i+1) at position pos. Net mscale is 1 (attn factor cancels).
    fn cs(&self, pos: f32, i: usize) -> (f32, f32) {
        let extrap = pos * self.base.powf(-2.0 * i as f32 / self.n_dims as f32);
        let interp = self.freq_scale * extrap;
        let theta = if self.ext != 0.0 {
            let y = (i as f32 - self.corr[0]) / (self.corr[1] - self.corr[0]).max(0.001);
            let mix = (1.0 - y.clamp(0.0, 1.0)) * self.ext;
            interp * (1.0 - mix) + extrap * mix
        } else {
            interp
        };
        (theta.cos(), theta.sin())
    }

    /// Rotate the LAST n_dims of v in place (NORM pairing). inverse=true de-ropes.
    pub fn apply(&self, v: &mut [f32], pos: usize, inverse: bool) {
        let off = v.len() - self.n_dims;
        let sgn = if inverse { -1.0 } else { 1.0 };
        for i in 0..self.n_dims / 2 {
            let (c, s) = self.cs(pos as f32, i);
            let (a, b) = (v[off + 2 * i], v[off + 2 * i + 1]);
            v[off + 2 * i] = a * c - sgn * b * s;
            v[off + 2 * i + 1] = a * s * sgn + b * c;
        }
    }
}

/// Hyper-connection coefficients for one sublayer.
pub struct Hc {
    pub pre: [f32; 4],
    pub post: [f32; 4],
    /// comb[d + 4*s]
    pub comb: [f32; 16],
}

fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + (-x).exp())
}

/// mixes: 24 values (hc_fn @ rms(flat x)); scale: 3; base: 24.
pub fn hc_coeffs(mixes: &[f32], scale: &[f32], base: &[f32], hc_eps: f32, iters: usize) -> Hc {
    let mut pre = [0.0; 4];
    let mut post = [0.0; 4];
    for i in 0..4 {
        pre[i] = sigmoid(mixes[i] * scale[0] + base[i]) + hc_eps;
        post[i] = 2.0 * sigmoid(mixes[4 + i] * scale[1] + base[4 + i]);
    }
    let mut m = [0.0f32; 16];
    for i in 0..16 {
        m[i] = mixes[8 + i] * scale[2] + base[8 + i];
    }
    // softmax over d for each s, then eps
    for s in 0..4 {
        let mx = (0..4).map(|d| m[d + 4 * s]).fold(f32::NEG_INFINITY, f32::max);
        let mut sum = 0.0;
        for d in 0..4 {
            m[d + 4 * s] = (m[d + 4 * s] - mx).exp();
            sum += m[d + 4 * s];
        }
        for d in 0..4 {
            m[d + 4 * s] = m[d + 4 * s] / sum + hc_eps;
        }
    }
    // norm_cols: M[d][s] /= sum_s M[d][s] + eps
    let norm_cols = |m: &mut [f32; 16]| {
        for d in 0..4 {
            let t: f32 = (0..4).map(|s| m[d + 4 * s]).sum::<f32>() + hc_eps;
            for s in 0..4 {
                m[d + 4 * s] /= t;
            }
        }
    };
    let norm_rows = |m: &mut [f32; 16]| {
        for s in 0..4 {
            let t: f32 = (0..4).map(|d| m[d + 4 * s]).sum::<f32>() + hc_eps;
            for d in 0..4 {
                m[d + 4 * s] /= t;
            }
        }
    };
    norm_cols(&mut m);
    for _ in 1..iters {
        norm_rows(&mut m);
        norm_cols(&mut m);
    }
    Hc { pre, post, comb: m }
}

/// sum_s x[s] * w[s]; x is 4 streams of n each.
pub fn hc_collapse(x: &[f32], w: &[f32; 4], out: &mut [f32]) {
    let n = out.len();
    for j in 0..n {
        out[j] = (0..4).map(|s| x[s * n + j] * w[s]).sum();
    }
}

/// out[d] = f * post[d] + sum_s residual[s] * comb[d + 4s]
pub fn hc_post(f: &[f32], residual: &[f32], hc: &Hc, out: &mut [f32]) {
    let n = f.len();
    for d in 0..4 {
        for j in 0..n {
            let mut a = f[j] * hc.post[d];
            for s in 0..4 {
                a += residual[s * n + j] * hc.comb[d + 4 * s];
            }
            out[d * n + j] = a;
        }
    }
}

/// Router: sqrt(softplus(logit)); pick top n_used by probs+bias; weights = probs[sel], normalised, scaled.
pub fn route(logits: &[f32], bias: &[f32], n_used: usize, norm: bool, scale: f32) -> Vec<(usize, f32)> {
    let probs: Vec<f32> = logits.iter().map(|&l| (if l > 20.0 { l } else { l.exp().ln_1p() }).sqrt()).collect();
    let mut idx: Vec<usize> = (0..probs.len()).collect();
    idx.sort_by(|&a, &b| (probs[b] + bias[b]).partial_cmp(&(probs[a] + bias[a])).unwrap().then(a.cmp(&b)));
    if std::env::var_os("STRATA_DS_MARGIN").is_some() {
        let s = |i: usize| probs[i] + bias[i];
        eprintln!("margin {:.4} sel={:?} next={}", s(idx[n_used - 1]) - s(idx[n_used]), &idx[..n_used], idx[n_used]);
    }
    idx.truncate(n_used);
    let sum: f32 = idx.iter().map(|&i| probs[i]).sum();
    idx.into_iter()
        .map(|i| (i, if norm && n_used > 1 { probs[i] / (sum + 1e-20) } else { probs[i] } * scale))
        .collect()
}

/// ggml swiglu_clamp.
pub fn swiglu_clamp(gate: f32, up: f32, limit: f32) -> f32 {
    let g = gate.min(limit);
    g / (1.0 + (-g).exp()) * up.clamp(-limit, limit)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rope_roundtrip_and_plain() {
        let r = Rope::new(10000.0, 1.0, 0.0, 64, 0, 32.0, 1.0);
        let orig: Vec<f32> = (0..512).map(|i| (i as f32 * 0.37).sin()).collect();
        let mut v = orig.clone();
        r.apply(&mut v, 17, false);
        assert_eq!(&v[..448], &orig[..448]);
        assert!((v[448] - orig[448]).abs() > 1e-3);
        r.apply(&mut v, 17, true);
        for (a, b) in v.iter().zip(&orig) {
            assert!((a - b).abs() < 1e-5);
        }
        // pair 0 theta = pos
        let mut p = vec![0.0; 64];
        p[0] = 1.0;
        r.apply(&mut p, 3, false);
        assert!((p[0] - 3f32.cos()).abs() < 1e-6 && (p[1] - 3f32.sin()).abs() < 1e-6);
    }

    #[test]
    fn yarn_limits() {
        let r = Rope::new(160000.0, 1.0 / 16.0, 1.0, 64, 65536, 32.0, 1.0);
        // fast dims (i < corr0) are pure extrapolation, slow dims (i > corr1) pure interpolation
        assert!(r.corr[0] < r.corr[1]);
        let (c0, s0) = r.cs(100.0, 0);
        assert!((c0 - 100f32.cos()).abs() < 1e-5 && (s0 - 100f32.sin()).abs() < 1e-5);
        let i = 31;
        let th = 100.0 * 160000f32.powf(-2.0 * i as f32 / 64.0) / 16.0;
        let (c, s) = r.cs(100.0, i);
        assert!((c - th.cos()).abs() < 1e-6 && (s - th.sin()).abs() < 1e-6);
    }

    #[test]
    fn sinkhorn_doubly_stochastic() {
        let mixes: Vec<f32> = (0..24).map(|i| (i as f32 * 0.7).cos()).collect();
        let hc = hc_coeffs(&mixes, &[1.0, 1.0, 1.0], &[0.0; 24], 1e-6, 20);
        for d in 0..4 {
            let r: f32 = (0..4).map(|s| hc.comb[d + 4 * s]).sum();
            assert!((r - 1.0).abs() < 1e-3, "{r}");
        }
        for s in 0..4 {
            let c: f32 = (0..4).map(|d| hc.comb[d + 4 * s]).sum();
            assert!((c - 1.0).abs() < 1e-3, "{c}");
        }
    }

    #[test]
    fn route_picks_and_normalises() {
        let mut logits = vec![-5.0; 16];
        logits[3] = 2.0;
        logits[9] = 1.0;
        let mut bias = vec![0.0; 16];
        bias[5] = 10.0; // bias selects but weight uses probs only
        let r = route(&logits, &bias, 3, true, 1.5);
        assert_eq!(r[0].0, 5);
        let s: f32 = r.iter().map(|x| x.1).sum();
        assert!((s - 1.5).abs() < 1e-5);
    }
}
