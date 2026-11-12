//! Sampler flags beyond the common ones, under llama.cpp's names.

use clap::Args;
use kinetic_server::Sampling;

#[derive(Args)]
pub struct SamplerArgs {
    /// Subtracted once from the logit of every recently seen token
    #[arg(long, value_name = "X", allow_negative_numbers = true)]
    presence_penalty: Option<f32>,
    /// Subtracted from a recent token's logit for each time it appears
    #[arg(long, value_name = "X", allow_negative_numbers = true)]
    frequency_penalty: Option<f32>,
    /// Locally typical sampling with mass P; 1 for none
    #[arg(long = "typical", value_name = "P")]
    typical_p: Option<f32>,
    /// Keep tokens within N standard deviations of the best logit; -1 for none
    #[arg(long = "top-nsigma", value_name = "N", allow_negative_numbers = true)]
    top_n_sigma: Option<f32>,
    /// Chance that XTC drops the likeliest tokens; 0 for none
    #[arg(long, value_name = "P")]
    xtc_probability: Option<f32>,
    /// XTC drops tokens at least this likely but the least likely
    #[arg(long, value_name = "P")]
    xtc_threshold: Option<f32>,
    /// DRY repetition penalty strength; 0 for none
    #[arg(long, value_name = "X")]
    dry_multiplier: Option<f32>,
    /// How fast the DRY penalty grows with the repetition's length
    #[arg(long, value_name = "X")]
    dry_base: Option<f32>,
    /// Repetitions this long go unpunished by DRY
    #[arg(long, value_name = "N")]
    dry_allowed_length: Option<usize>,
    /// Recent tokens DRY looks at; -1 for all
    #[arg(long, value_name = "N", allow_negative_numbers = true)]
    dry_penalty_last_n: Option<i64>,
    /// Text that ends a repetition for DRY, repeatable; "none" for none
    #[arg(long = "dry-sequence-breaker", value_name = "TEXT")]
    dry_sequence_breakers: Vec<String>,
    /// Mirostat version: 1, 2, or 0 for none
    #[arg(long, value_name = "N", value_parser = clap::value_parser!(u8).range(0..=2))]
    mirostat: Option<u8>,
    /// Mirostat learning rate (eta)
    #[arg(long = "mirostat-lr", value_name = "X")]
    mirostat_eta: Option<f32>,
    /// Mirostat target surprise (tau)
    #[arg(long = "mirostat-ent", value_name = "X")]
    mirostat_tau: Option<f32>,
}

impl SamplerArgs {
    pub fn apply(&self, s: &mut Sampling) {
        let set = |to: &mut f32, v: Option<f32>| *to = v.unwrap_or(*to);
        set(&mut s.presence_penalty, self.presence_penalty);
        set(&mut s.frequency_penalty, self.frequency_penalty);
        set(&mut s.typical_p, self.typical_p);
        set(&mut s.top_n_sigma, self.top_n_sigma);
        set(&mut s.xtc_probability, self.xtc_probability);
        set(&mut s.xtc_threshold, self.xtc_threshold);
        set(&mut s.dry_multiplier, self.dry_multiplier);
        set(&mut s.dry_base, self.dry_base);
        set(&mut s.mirostat_eta, self.mirostat_eta);
        set(&mut s.mirostat_tau, self.mirostat_tau);
        s.dry_allowed_length = self.dry_allowed_length.unwrap_or(s.dry_allowed_length);
        if let Some(n) = self.dry_penalty_last_n {
            s.dry_penalty_last_n = usize::try_from(n).unwrap_or(usize::MAX);
        }
        if !self.dry_sequence_breakers.is_empty() {
            s.dry_sequence_breakers = self
                .dry_sequence_breakers
                .iter()
                .filter(|b| *b != "none")
                .cloned()
                .collect();
        }
        s.mirostat = self.mirostat.unwrap_or(s.mirostat);
    }
}
