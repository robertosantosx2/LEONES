//! What the server has done so far, for `/metrics` and `/slots`.

use std::fmt::Write;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, PoisonError};
use std::time::Duration;

use crate::backend::Timings;
use crate::engine::Request;

/// Totals since the server started and the state of each slot.
#[derive(Default)]
pub struct Stats {
    requests: AtomicU64,
    prompt_tokens: AtomicU64,
    cached_tokens: AtomicU64,
    prompt_us: AtomicU64,
    generated: AtomicU64,
    decode_us: AtomicU64,
    longest: AtomicU64,
    tasks: AtomicU64,
    slots: Mutex<Vec<Slot>>,
}

/// One slot's current or last request.
#[derive(Clone, Debug, Default)]
pub struct Slot {
    pub processing: bool,
    pub task: Option<u64>,
    pub request: Option<Request>,
    pub prompt: String,
    pub prompt_tokens: usize,
    pub cached_tokens: usize,
    pub decoded: usize,
    pub max_tokens: usize,
}

/// The gauges `/metrics` adds to the totals.
pub struct Load {
    pub processing: usize,
    pub deferred: usize,
}

impl Stats {
    pub fn new(slots: usize) -> Self {
        Stats {
            slots: Mutex::new(vec![Slot::default(); slots]),
            ..Stats::default()
        }
    }

    pub fn resize(&mut self, slots: usize) {
        self.slots
            .get_mut()
            .unwrap_or_else(PoisonError::into_inner)
            .resize(slots, Slot::default());
    }

    /// Marks slot `id` busy with a new request and returns its task id.
    pub fn start(&self, id: usize, request: &Request, prompt: String, max_tokens: usize) -> u64 {
        let task = self.tasks.fetch_add(1, Ordering::Relaxed);
        self.update(id, |s| {
            *s = Slot {
                processing: true,
                task: Some(task),
                request: Some(request.clone()),
                prompt,
                max_tokens,
                ..Slot::default()
            }
        });
        task
    }

    pub fn update(&self, id: usize, f: impl FnOnce(&mut Slot)) {
        let mut slots = self.slots.lock().unwrap_or_else(PoisonError::into_inner);
        if let Some(slot) = slots.get_mut(id) {
            f(slot);
        }
    }

    /// Adds a finished request to the totals and frees its slot.
    pub fn finish(&self, id: usize, t: &Timings) {
        let us = |d: Duration| d.as_micros() as u64;
        self.requests.fetch_add(1, Ordering::Relaxed);
        let fresh = t.prompt_tokens.saturating_sub(t.cached_tokens) as u64;
        self.prompt_tokens.fetch_add(fresh, Ordering::Relaxed);
        self.cached_tokens
            .fetch_add(t.cached_tokens as u64, Ordering::Relaxed);
        self.prompt_us.fetch_add(us(t.prefill), Ordering::Relaxed);
        self.generated
            .fetch_add(t.generated as u64, Ordering::Relaxed);
        self.decode_us.fetch_add(us(t.decode), Ordering::Relaxed);
        self.longest
            .fetch_max((t.prompt_tokens + t.generated) as u64, Ordering::Relaxed);
        self.update(id, |s| {
            s.processing = false;
            s.prompt_tokens = t.prompt_tokens;
            s.cached_tokens = t.cached_tokens;
            s.decoded = t.generated;
        });
    }

    pub fn slots(&self) -> Vec<Slot> {
        self.slots
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .clone()
    }

    /// The totals in Prometheus' text format, under llama-server's names.
    pub fn prometheus(&self, load: &Load) -> String {
        let get = |a: &AtomicU64| a.load(Ordering::Relaxed);
        let secs = |a: &AtomicU64| get(a) as f64 / 1e6;
        let rate = |n: &AtomicU64, us: &AtomicU64| match get(us) {
            0 => 0.0,
            t => get(n) as f64 * 1e6 / t as f64,
        };
        let counters = [
            (
                "requests_total",
                "Requests answered",
                get(&self.requests) as f64,
            ),
            (
                "prompt_tokens_total",
                "Number of prompt tokens processed, excluding cached tokens",
                get(&self.prompt_tokens) as f64,
            ),
            (
                "prompt_tokens_cached_total",
                "Number of prompt tokens reused from the cache",
                get(&self.cached_tokens) as f64,
            ),
            (
                "prompt_seconds_total",
                "Total time spent processing prompts",
                secs(&self.prompt_us),
            ),
            (
                "tokens_predicted_total",
                "Number of generation tokens processed",
                get(&self.generated) as f64,
            ),
            (
                "tokens_predicted_seconds_total",
                "Total time spent generating tokens",
                secs(&self.decode_us),
            ),
            (
                "n_tokens_max",
                "Largest observed sequence length (prompt + generation)",
                get(&self.longest) as f64,
            ),
        ];
        let gauges = [
            (
                "prompt_tokens_seconds",
                "Average prompt throughput in tokens/s",
                rate(&self.prompt_tokens, &self.prompt_us),
            ),
            (
                "predicted_tokens_seconds",
                "Average generation throughput in tokens/s",
                rate(&self.generated, &self.decode_us),
            ),
            (
                "requests_processing",
                "Number of requests processing",
                load.processing as f64,
            ),
            (
                "requests_deferred",
                "Number of requests deferred",
                load.deferred as f64,
            ),
        ];
        let mut out = String::new();
        for (kind, items) in [("counter", &counters[..]), ("gauge", &gauges[..])] {
            for (name, help, value) in items {
                let _ = writeln!(out, "# HELP llamacpp:{name} {help}");
                let _ = writeln!(out, "# TYPE llamacpp:{name} {kind}");
                let _ = writeln!(out, "llamacpp:{name} {value}");
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn totals_and_rates() {
        let stats = Stats::new(2);
        let req = Request {
            sampling: Default::default(),
            max_tokens: Some(8),
            stop: Vec::new(),
            grammar: None,
        };
        assert_eq!(stats.start(1, &req, "hi".into(), 8), 0);
        assert!(stats.slots()[1].processing);
        stats.finish(
            1,
            &Timings {
                prompt_tokens: 120,
                cached_tokens: 20,
                prefill: Duration::from_millis(500),
                generated: 50,
                decode: Duration::from_secs(1),
            },
        );
        let text = stats.prometheus(&Load {
            processing: 0,
            deferred: 3,
        });
        for line in [
            "llamacpp:requests_total 1\n",
            "llamacpp:prompt_tokens_total 100\n",
            "llamacpp:prompt_tokens_cached_total 20\n",
            "llamacpp:prompt_seconds_total 0.5\n",
            "llamacpp:tokens_predicted_total 50\n",
            "llamacpp:prompt_tokens_seconds 200\n",
            "llamacpp:predicted_tokens_seconds 50\n",
            "llamacpp:n_tokens_max 170\n",
            "llamacpp:requests_deferred 3\n",
            "# TYPE llamacpp:requests_processing gauge\n",
        ] {
            assert!(text.contains(line), "{line:?} not in\n{text}");
        }
        let slot = &stats.slots()[1];
        assert!(!slot.processing);
        assert_eq!((slot.decoded, slot.cached_tokens), (50, 20));
    }
}
