//! Samplers that narrow the candidates: top-n-sigma, locally typical, XTC
//! and Mirostat, with llama.cpp's definitions. Candidates are `(token,
//! value)` pairs, the value a logit or a probability as each one says.

use super::sampler::{by_logit, draw, normalize, softmax};

/// Keeps the logits at most `n` standard deviations below the highest.
pub(super) fn top_n_sigma(c: &mut Vec<(u32, f32)>, n: f32) {
    if c.len() <= 1 {
        return;
    }
    let len = c.len() as f32;
    let max = c.iter().map(|x| x.1).fold(f32::NEG_INFINITY, f32::max);
    let mean = c.iter().map(|x| x.1).sum::<f32>() / len;
    let var = c.iter().map(|x| (x.1 - mean).powi(2)).sum::<f32>() / len;
    let floor = max - n * var.sqrt();
    c.retain(|x| x.1 >= floor);
}

/// Keeps the tokens whose surprise is closest to the expected surprise
/// until their probabilities add up to more than `p`; takes and leaves
/// probabilities, most likely first.
pub(super) fn typical(c: &mut Vec<(u32, f32)>, p: f32) {
    let entropy: f32 = c
        .iter()
        .filter(|x| x.1 > 0.0)
        .map(|x| -x.1 * x.1.ln())
        .sum();
    let shift = |prob: f32| (-prob.ln() - entropy).abs();
    let mut order: Vec<usize> = (0..c.len()).collect();
    order.sort_by(|&a, &b| shift(c[a].1).total_cmp(&shift(c[b].1)));
    let mut sum = 0.0;
    let keep = order
        .iter()
        .position(|&i| {
            sum += c[i].1;
            sum > p
        })
        .map_or(c.len(), |i| i + 1);
    let mut kept = vec![false; c.len()];
    order[..keep].iter().for_each(|&i| kept[i] = true);
    let mut i = 0;
    c.retain(|_| {
        i += 1;
        kept[i - 1]
    });
    normalize(c);
}

/// XTC: with chance `probability`, drops every token at least `threshold`
/// likely except the least likely of them. `chance` draws the uniform
/// number that decides, only when XTC could apply. Takes and leaves
/// probabilities, most likely first.
pub(super) fn xtc(
    c: &mut Vec<(u32, f32)>,
    probability: f32,
    threshold: f32,
    chance: impl FnOnce() -> f32,
) {
    if probability <= 0.0 || threshold > 0.5 || c.len() < 2 || chance() > probability {
        return;
    }
    normalize(c);
    let above = c.iter().take_while(|x| x.1 >= threshold).count();
    if above > 1 {
        c.drain(..above - 1);
    }
}

/// The settings and state of Mirostat; `mu` starts at twice `tau`.
pub(super) struct Mirostat {
    pub version: u8,
    pub tau: f32,
    pub eta: f32,
    pub mu: f32,
}

impl Mirostat {
    /// Mirostat's tokens considered in its estimate of the distribution's
    /// shape, as llama.cpp fixes it.
    const M: usize = 100;

    /// Chooses from logits `c` at `temperature`, a vocabulary of `n_vocab`,
    /// with uniform number `r`, and moves `mu` towards the target surprise.
    pub fn choose(
        &mut self,
        c: &mut Vec<(u32, f32)>,
        temperature: f32,
        n_vocab: usize,
        r: f32,
    ) -> u32 {
        c.sort_unstable_by(by_logit);
        softmax(c, temperature);
        if self.version == 1 {
            let (mut ti_bi, mut ti_sq) = (0.0, 0.0);
            for i in 0..(Self::M - 1).min(c.len() - 1) {
                let t = ((i + 2) as f32 / (i + 1) as f32).ln();
                ti_bi += t * (c[i].1 / c[i + 1].1).ln();
                ti_sq += t * t;
            }
            let s = ti_bi / ti_sq;
            let e = s - 1.0;
            let k = (e * 2f32.powf(self.mu) / (1.0 - (n_vocab as f32).powf(-e))).powf(1.0 / s);
            c.truncate((k as usize).max(1));
        } else {
            let keep = c.iter().take_while(|x| -x.1.log2() <= self.mu).count();
            c.truncate(keep.max(1));
        }
        normalize(c);
        let i = draw(c, r);
        self.mu -= self.eta * (-c[i].1.log2() - self.tau);
        c[i].0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn probs(c: &[(u32, f32)]) -> Vec<f32> {
        c.iter().map(|x| (x.1 * 1e4).round() / 1e4).collect()
    }

    #[test]
    fn top_n_sigma_keeps_logits_near_the_top() {
        // mean 1, std 1.549: one sigma keeps only 4, two keep 1 as well
        let mut c = vec![(0, 4.0), (1, 1.0), (2, 0.0), (3, 0.0), (4, 0.0)];
        top_n_sigma(&mut c, 1.0);
        assert_eq!(c, [(0, 4.0)]);
        let mut c = vec![(0, 4.0), (1, 1.0), (2, 0.0), (3, 0.0), (4, 0.0)];
        top_n_sigma(&mut c, 2.0);
        assert_eq!(c.len(), 2);
    }

    #[test]
    fn typical_keeps_tokens_near_the_entropy() {
        // entropy of [0.5, 0.3, 0.2] is 1.0297; surprises 0.693, 1.204,
        // 1.609: distances 0.337, 0.174, 0.580, so 0.3 then 0.5 go first
        let mut c = vec![(0, 0.5), (1, 0.3), (2, 0.2)];
        typical(&mut c, 0.4);
        assert_eq!((c[0].0, c[1].0), (0, 1));
        assert_eq!(probs(&c), [0.625, 0.375]);
        let mut c = vec![(0, 0.5), (1, 0.3), (2, 0.2)];
        typical(&mut c, 0.2);
        assert_eq!(c, [(1, 1.0)]);
    }

    #[test]
    fn xtc_drops_all_likely_tokens_but_the_last() {
        let start = vec![(0, 0.5), (1, 0.3), (2, 0.15), (3, 0.05)];
        let mut c = start.clone();
        xtc(&mut c, 1.0, 0.1, || 0.5);
        assert_eq!(c.iter().map(|x| x.0).collect::<Vec<_>>(), [2, 3]);
        let mut c = start.clone();
        xtc(&mut c, 0.4, 0.1, || 0.5);
        assert_eq!(c, start);
        let mut c = start.clone();
        xtc(&mut c, 1.0, 0.6, || unreachable!());
        assert_eq!(c, start);
    }

    #[test]
    fn mirostat_2_cuts_at_the_surprise_and_learns() {
        // probabilities 0.5, 0.25, 0.25: surprises 1, 2, 2 bits
        let ln = |p: f32| p.ln();
        let mut m = Mirostat {
            version: 2,
            tau: 1.5,
            eta: 0.5,
            mu: 1.5,
        };
        let mut c = vec![(0, ln(0.5)), (1, ln(0.25)), (2, ln(0.25))];
        assert_eq!(m.choose(&mut c, 1.0, 3, 0.99), 0);
        assert_eq!(probs(&c), [1.0]);
        // surprise 0 after the cut: mu += 0.5 * 1.5
        assert!((m.mu - 2.25).abs() < 1e-6);
        let mut c = vec![(0, ln(0.5)), (1, ln(0.25)), (2, ln(0.25))];
        assert_eq!(m.choose(&mut c, 1.0, 3, 0.99), 2);
    }

    #[test]
    fn mirostat_1_estimates_the_cut_from_the_slope() {
        // Zipf with s = 1 over 1000 tokens: s_hat 1, k from mu alone
        let mut c: Vec<(u32, f32)> = (0..1000).map(|i| (i, -((i + 1) as f32).ln())).collect();
        let mut m = Mirostat {
            version: 1,
            tau: 3.0,
            eta: 0.1,
            mu: 3.0,
        };
        m.choose(&mut c, 1.0, 1000, 0.0);
        // e -> 0: k = (e 2^mu / (1 - n^-e))^(1/s) -> 2^mu / ln(n) = 1.158
        assert_eq!(c.len(), 1);
    }
}
