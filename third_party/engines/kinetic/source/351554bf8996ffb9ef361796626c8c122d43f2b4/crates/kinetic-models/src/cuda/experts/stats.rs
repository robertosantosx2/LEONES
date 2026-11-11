use std::fmt;

/// What the expert runtime did, counted since load or the last reset.
#[derive(Clone, Copy, Debug, Default)]
pub struct Stats {
    pub tokens: u64,
    /// Routed (token, expert) pairs.
    pub picks: u64,
    /// Picks whose expert was on the device when its layer ran.
    pub hits: u64,
    /// Experts the next layer's router predicted, per layer and pass.
    pub predicted: u64,
    /// Predicted experts the layer then picked.
    pub predicted_used: u64,
    /// Experts a layer picked, per layer and pass.
    pub used: u64,
    /// Experts copied to the device ahead of their layer, and their bytes.
    pub prefetched: u64,
    pub prefetched_bytes: u64,
    /// Experts copied to the device when their layer needed them.
    pub loaded: u64,
    pub loaded_bytes: u64,
    /// Experts the host ran, and the weight bytes it read for them.
    pub host_experts: u64,
    pub host_bytes: u64,
}

impl Stats {
    pub fn hit_rate(&self) -> f64 {
        ratio(self.hits, self.picks)
    }

    /// Share of predicted experts that their layer used.
    pub fn prefetch_precision(&self) -> f64 {
        ratio(self.predicted_used, self.predicted)
    }

    /// Share of used experts that were predicted.
    pub fn prefetch_recall(&self) -> f64 {
        ratio(self.predicted_used, self.used)
    }
}

fn ratio(a: u64, b: u64) -> f64 {
    a as f64 / b.max(1) as f64
}

impl fmt::Display for Stats {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let per_token = |bytes: u64| bytes as f64 / self.tokens.max(1) as f64 / (1 << 20) as f64;
        write!(
            f,
            "{} tokens: device hit rate {:.1}%, prediction precision {:.1}% recall {:.1}%, \
             per token {:.1} MiB prefetched, {:.1} MiB loaded, {:.1} MiB read by the host",
            self.tokens,
            100.0 * self.hit_rate(),
            100.0 * self.prefetch_precision(),
            100.0 * self.prefetch_recall(),
            per_token(self.prefetched_bytes),
            per_token(self.loaded_bytes),
            per_token(self.host_bytes),
        )
    }
}
