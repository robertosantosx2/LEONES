//! Shared by the speculative examples: drafters by name, plain and
//! speculative runs on any target, and the sampling settings they test.

// Each example uses only part of this module.
#![allow(dead_code)]

use std::time::Instant;

use kinetic_models::speculative::{
    Decoder, Drafter, Ensemble, Lookup, MtpDrafter, Policy, Predictor, Sampling, SessionIndex,
    Target,
};

pub const DRAFTERS: &str = "lookup|session|mtp|all|chain|tree";

pub struct Run {
    pub tokens: Vec<u32>,
    pub passes: usize,
    pub drafted: usize,
    pub seconds: f64,
}

impl Run {
    pub fn tokens_per_second(&self) -> f64 {
        self.tokens.len() as f64 / self.seconds
    }

    pub fn tokens_per_pass(&self) -> f64 {
        self.tokens.len() as f64 / self.passes as f64
    }
}

/// The server's default sampling with a mild repeat penalty, so that
/// penalties are part of what is checked.
pub fn sampling(temperature: f32, seed: u64) -> Sampling {
    Sampling {
        temperature,
        repeat_penalty: 1.1,
        seed: Some(seed),
        ..Sampling::default()
    }
}

/// A decoder drafting with `name`, one of [`DRAFTERS`]: `mtp` is the
/// prediction block with a context lookup first, `all` lets the context, the
/// session and the block compete and verifies their tree when it pays,
/// `chain` is `all` verifying only the tree's heaviest path, `tree` is
/// `all` verifying every tree whole.
pub fn decoder<'a, M: Predictor + 'a>(
    model: &M,
    name: &str,
) -> Result<Decoder<Box<dyn Drafter<M> + 'a>>, String> {
    let mtp = MtpDrafter::new(model);
    let drafter: Box<dyn Drafter<M> + 'a> = match name {
        "lookup" => Box::new(Lookup::default()),
        "session" => Box::new(SessionIndex::default()),
        "mtp" => Box::new(mtp.ok_or("model has no prediction block")?),
        "all" | "chain" | "tree" => {
            let mut sources: Vec<Box<dyn Drafter<M> + 'a>> = vec![
                Box::new(Lookup::default()),
                Box::new(SessionIndex::default()),
            ];
            if let Some(mut mtp) = mtp {
                mtp.lookup = None;
                sources.push(Box::new(mtp));
            }
            Box::new(Ensemble::new(sources))
        }
        other => return Err(format!("unknown drafter {other}, expected {DRAFTERS}")),
    };
    let mut decoder = Decoder::new(drafter);
    let ensemble = matches!(name, "all" | "chain" | "tree");
    if name == "mtp" || (ensemble && model.new_mtp_state().is_some()) {
        decoder.max_pause = 0;
    }
    match name {
        "chain" => decoder.row_cost = f32::INFINITY,
        "tree" => decoder.row_cost = 0.0,
        _ => {}
    }
    Ok(decoder)
}

/// Runs `prompt` and then one token per pass, at most `n`.
pub fn plain<M: Target, P: Policy<M>>(
    model: &M,
    policy: &mut P,
    state: &mut M::State,
    prompt: &[u32],
    n: usize,
    stop: impl Fn(u32) -> bool,
) -> Run {
    let mut context = prompt.to_vec();
    let (mut scores, _) = policy.score(model, state, prompt, false);
    let start = Instant::now();
    while context.len() - prompt.len() < n {
        let t = policy.choose(model, &scores, 0, &context);
        context.push(t);
        if stop(t) {
            break;
        }
        scores = policy.score(model, state, &[t], false).0;
    }
    let tokens = context.split_off(prompt.len());
    Run {
        passes: tokens.len(),
        tokens,
        drafted: 0,
        seconds: start.elapsed().as_secs_f64(),
    }
}

/// Runs `prompt` and generates at most `n` tokens speculatively.
pub fn speculative<M: Target, P: Policy<M>, D: Drafter<M>>(
    model: &M,
    policy: &mut P,
    decoder: &mut Decoder<D>,
    state: &mut M::State,
    prompt: &[u32],
    n: usize,
    stop: impl Fn(u32) -> bool + Copy,
) -> Run {
    let mut context = prompt.to_vec();
    decoder.prefill(model, policy, state, &context, 0);
    let (mut passes, mut drafted) = (0, 0);
    let start = Instant::now();
    while context.len() - prompt.len() < n {
        let limit = n - (context.len() - prompt.len());
        let step = decoder.step(model, policy, state, &mut context, limit, stop);
        passes += 1;
        drafted += step.drafted;
        if context.last().copied().is_some_and(stop) {
            break;
        }
    }
    Run {
        tokens: context.split_off(prompt.len()),
        passes,
        drafted,
        seconds: start.elapsed().as_secs_f64(),
    }
}

/// Prints how `fast` compares with `plain`.
pub fn report(name: &str, plain: &Run, fast: &Run) {
    let first_diff = plain
        .tokens
        .iter()
        .zip(&fast.tokens)
        .position(|(a, b)| a != b);
    println!(
        "identical: {} (first difference at {first_diff:?})",
        fast.tokens == plain.tokens
    );
    println!(
        "plain:  {:.3}s, {:.2} tok/s",
        plain.seconds,
        plain.tokens_per_second()
    );
    println!(
        "{name}: {:.3}s, {:.2} tok/s, {} passes, {:.2} tokens/pass, {}/{} drafts accepted",
        fast.seconds,
        fast.tokens_per_second(),
        fast.passes,
        fast.tokens_per_pass(),
        fast.tokens.len() - fast.passes,
        fast.drafted,
    );
    println!("speedup {:.2}x", plain.seconds / fast.seconds);
}

/// Two-sample chi-square test of whether `a` and `b` come from one
/// distribution, with tokens seen fewer than ten times in all pooled.
/// Returns the statistic, its degrees of freedom and the Wilson-Hilferty
/// normal score, which stays within about 2 when they do.
pub fn chi_square(a: &[u32], b: &[u32]) -> (f64, usize, f64) {
    let mut counts: std::collections::BTreeMap<u32, (f64, f64)> = Default::default();
    a.iter()
        .for_each(|&t| counts.entry(t).or_default().0 += 1.0);
    b.iter()
        .for_each(|&t| counts.entry(t).or_default().1 += 1.0);
    let mut cells: Vec<(f64, f64)> = Vec::new();
    let mut pooled = (0.0, 0.0);
    for (x, y) in counts.into_values() {
        if x + y < 10.0 {
            pooled = (pooled.0 + x, pooled.1 + y);
        } else {
            cells.push((x, y));
        }
    }
    if pooled.0 + pooled.1 > 0.0 {
        cells.push(pooled);
    }
    let (na, nb) = (a.len() as f64, b.len() as f64);
    let stat: f64 = cells
        .iter()
        .map(|&(x, y)| {
            let total = x + y;
            let (ea, eb) = (total * na / (na + nb), total * nb / (na + nb));
            (x - ea).powi(2) / ea + (y - eb).powi(2) / eb
        })
        .sum();
    let dof = cells.len().saturating_sub(1);
    let k = dof.max(1) as f64;
    let z = ((stat / k).cbrt() - (1.0 - 2.0 / (9.0 * k))) / (2.0 / (9.0 * k)).sqrt();
    (stat, dof, z)
}

/// Total variation distance between the empirical distributions of `a`
/// and `b`.
pub fn total_variation(a: &[u32], b: &[u32]) -> f64 {
    let mut diff: std::collections::HashMap<u32, f64> = Default::default();
    a.iter()
        .for_each(|&t| *diff.entry(t).or_default() += 1.0 / a.len() as f64);
    b.iter()
        .for_each(|&t| *diff.entry(t).or_default() -= 1.0 / b.len() as f64);
    diff.values().map(|d| d.abs()).sum::<f64>() / 2.0
}

/// Prints how seeded speculative runs compare with plain ones: `same` used
/// the seeds of `plain`, `other` different ones.
pub fn summarize(source: &str, plain: &[Run], same: &[Run], other: &[Run], n: usize) {
    let identical = plain
        .iter()
        .zip(same)
        .filter(|(a, b)| a.tokens == b.tokens)
        .count();
    let rate = |runs: &[Run]| {
        let tokens: usize = runs.iter().map(|r| r.tokens.len()).sum();
        let passes: usize = runs.iter().map(|r| r.passes).sum();
        let seconds: f64 = runs.iter().map(|r| r.seconds).sum();
        (tokens as f64 / seconds, tokens as f64 / passes as f64)
    };
    let (plain_rate, _) = rate(plain);
    let (fast_rate, per_pass) = rate(same);
    println!(
        "{} seeds, seeded runs identical: {identical}/{}",
        plain.len(),
        plain.len()
    );
    println!(
        "plain {plain_rate:.2} tok/s; {source} {fast_rate:.2} tok/s, {per_pass:.2} tokens/pass, speedup {:.2}x",
        fast_rate / plain_rate
    );
    println!("plain vs {source} with other seeds, token distribution at each step:");
    let mut step = 0;
    while step < n {
        let at = |runs: &[Run]| -> Vec<u32> {
            runs.iter()
                .filter_map(|r| r.tokens.get(step).copied())
                .collect()
        };
        let (a, b) = (at(plain), at(other));
        if a.is_empty() || b.is_empty() {
            break;
        }
        let (stat, dof, z) = chi_square(&a, &b);
        println!(
            "  step {step:>3}: {} vs {} samples, {} distinct, TV {:.3}, chi2 {stat:.1} on {dof} dof, z {z:+.2}",
            a.len(),
            b.len(),
            a.iter().chain(&b).collect::<std::collections::HashSet<_>>().len(),
            total_variation(&a, &b)
        );
        step = if step == 0 { 1 } else { step * 2 };
    }
}
