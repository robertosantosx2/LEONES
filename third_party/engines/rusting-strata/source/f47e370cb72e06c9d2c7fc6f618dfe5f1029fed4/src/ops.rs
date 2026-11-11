//! Scalar f32 reference math.

pub fn rms_norm(x: &[f32], w: &[f32], eps: f32, out: &mut [f32]) {
    let ms = x.iter().map(|v| v * v).sum::<f32>() / x.len() as f32;
    let s = 1.0 / (ms + eps).sqrt();
    for ((o, v), w) in out.iter_mut().zip(x).zip(w) { *o = v * s * w; }
}

pub fn l2_norm(x: &mut [f32], eps: f32) {
    let s = 1.0 / x.iter().map(|v| v * v).sum::<f32>().sqrt().max(eps);
    for v in x { *v *= s; }
}

pub fn silu(x: f32) -> f32 { x / (1.0 + (-x).exp()) }
pub fn sigmoid(x: f32) -> f32 { 1.0 / (1.0 + (-x).exp()) }
pub fn softplus(x: f32) -> f32 { if x > 20.0 { x } else { x.exp().ln_1p() } }

pub fn softmax(x: &mut [f32]) {
    let m = x.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
    let mut s = 0.0;
    for v in x.iter_mut() { *v = (*v - m).exp(); s += *v; }
    for v in x { *v /= s; }
}

/// NEOX-style rotary embedding on the first `n_rot` dims: pairs (i, i + n_rot/2).
pub fn rope_neox(x: &mut [f32], n_rot: usize, pos: usize, base: f32) {
    let half = n_rot / 2;
    for i in 0..half {
        let theta = pos as f64 * (base as f64).powf(-2.0 * i as f64 / n_rot as f64);
        let (s, c) = (theta.sin() as f32, theta.cos() as f32);
        let (a, b) = (x[i], x[i + half]);
        x[i] = a * c - b * s;
        x[i + half] = a * s + b * c;
    }
}

/// Indices of the `k` largest values, descending; ties go to the lower index.
pub fn top_k(p: &[f32], k: usize) -> Vec<usize> {
    let mut idx: Vec<usize> = (0..p.len()).collect();
    idx.sort_by(|&a, &b| p[b].total_cmp(&p[a]).then(a.cmp(&b)));
    idx.truncate(k);
    idx
}

/// Index of the largest value; the first one on ties (same order as `top_k`).
pub fn argmax(x: &[f32]) -> usize {
    (1..x.len()).fold(0, |b, i| if x[i].total_cmp(&x[b]).is_gt() { i } else { b })
}

const NON_FINITE: &str = "the forward pass produced NaN or infinite logits";

/// Token choice after the logits: greedy when `temp` is 0, else softmax(logits / temp) cut to the `top_k` most likely
/// tokens (0 = no cut) and then to the smallest set whose probability reaches `top_p`.
#[derive(Clone, Debug)]
pub struct Sampler {
    pub temp: f32,
    pub top_k: usize,
    pub top_p: f32,
    /// xorshift64 state; must not be 0.
    pub rng: u64,
}

impl Sampler {
    pub fn greedy() -> Self { Sampler { temp: 0.0, top_k: 0, top_p: 1.0, rng: 1 } }

    pub fn pick(&mut self, logits: &[f32]) -> anyhow::Result<usize> {
        if self.temp <= 0.0 {
            let i = argmax(logits);
            anyhow::ensure!(logits[i].is_finite(), NON_FINITE);
            return Ok(i);
        }
        let c = self.cands(logits);
        self.draw(&c)
    }

    /// Speculative sampling with a fixed draft `d`: keeps `d` (None) with its probability under this sampler, else
    /// returns a token drawn from the others, renormalized. The result has the distribution of `pick`. `temp` > 0.
    pub fn accept(&mut self, logits: &[f32], d: usize) -> anyhow::Result<Option<usize>> {
        let c = self.cands(logits);
        anyhow::ensure!(!c.is_empty(), NON_FINITE);
        let q = c.iter().find(|x| x.0 == d).map_or(0.0, |x| x.1);
        if self.rand() * c.iter().map(|x| x.1).sum::<f32>() < q { return Ok(None); }
        Ok(Some(self.draw(&c.into_iter().filter(|x| x.0 != d).collect::<Vec<_>>())?))
    }

    /// The tokens `pick` draws from, with their weights (exp of the scaled logit, not normalized), most likely first.
    fn cands(&self, logits: &[f32]) -> Vec<(usize, f32)> {
        // The max in 16 lanes, which vectorizes (a scan with `total_cmp` does not): 0.3 ms per token less on a
        // 248K vocabulary, with the logits that are below e^-21 of the best skipped before the divide.
        let ch = logits.chunks_exact(16);
        let tail = ch.remainder().iter().fold(f32::NEG_INFINITY, |a, &x| a.max(x));
        let m = ch.fold([f32::NEG_INFINITY; 16], |mut a, c| { for j in 0..16 { a[j] = a[j].max(c[j]) } a })
            .into_iter().fold(tail, f32::max);
        let lo = m - 21.0 * self.temp;
        // Tokens below e^-20 of the best one are dropped first so only a few are sorted, not the whole vocabulary.
        let mut c: Vec<(usize, f32)> = logits.iter().enumerate().filter(|x| *x.1 >= lo)
            .map(|(i, &l)| (i, (l - m) / self.temp)).filter(|x| x.1 > -20.0).map(|(i, x)| (i, x.exp())).collect();
        c.sort_by(|a, b| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0)));
        if self.top_k > 0 { c.truncate(self.top_k); }
        let total: f32 = c.iter().map(|x| x.1).sum();
        let (mut acc, mut n) = (0.0, c.len());
        for (j, x) in c.iter().enumerate() {
            acc += x.1;
            if acc >= self.top_p * total { n = j + 1; break; }
        }
        c.truncate(n);
        c
    }

    /// A token drawn from `c` in proportion to the weights.
    fn draw(&mut self, c: &[(usize, f32)]) -> anyhow::Result<usize> {
        // Empty only when no logit is finite (`cands` drops NaN and infinity).
        anyhow::ensure!(!c.is_empty(), NON_FINITE);
        let mut r = self.rand() * c.iter().map(|x| x.1).sum::<f32>();
        for &(i, p) in c {
            r -= p;
            if r < 0.0 { return Ok(i); }
        }
        Ok(c[c.len() - 1].0)
    }

    /// Uniform in [0, 1).
    fn rand(&mut self) -> f32 {
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 7;
        self.rng ^= self.rng << 17;
        (self.rng >> 40) as f32 / (1u64 << 24) as f32
    }
}
