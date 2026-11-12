use kinetic_cpu::pool;

use super::tree::Tree;

/// Outputs one parallel task of [`ConvWindow::run_batch`] computes, a few
/// tasks per token so short batches spread over the pool too.
const VALUES_PER_TASK: usize = 512;

/// The last `taps - 1` inputs of each channel of a causal convolution,
/// oldest first, with an optional record of the inputs since a checkpoint.
#[derive(Clone)]
pub struct ConvWindow {
    len: usize,
    pub(super) past: Vec<f32>,
    journal: Option<Journal>,
}

#[derive(Clone)]
struct Journal {
    start: Vec<f32>,
    /// One row of `channels` inputs per token.
    inputs: Vec<f32>,
}

impl ConvWindow {
    pub fn new(channels: usize, taps: usize) -> Self {
        ConvWindow {
            len: taps - 1,
            past: vec![0.0; channels * (taps - 1)],
            journal: None,
        }
    }

    fn channels(&self) -> usize {
        self.past.len() / self.len
    }

    /// The stored inputs of channel `ch`, oldest first.
    pub fn past(&self, ch: usize) -> &[f32] {
        &self.past[ch * self.len..][..self.len]
    }

    /// Appends one token's inputs, one per channel, dropping the oldest.
    pub fn push(&mut self, inputs: &[f32]) {
        if let Some(j) = &mut self.journal {
            j.inputs.extend_from_slice(inputs);
        }
        for (past, &x) in self.past.chunks_exact_mut(self.len).zip(inputs) {
            past.rotate_left(1);
            past[self.len - 1] = x;
        }
    }

    /// Calls `step` for each of `n` batch rows in order with the window
    /// that row sees, and pushes the inputs `step` returns for it. With
    /// `tree`, a row sees the window after its parent; the window left is
    /// that after every row in order, which [`ConvWindow::rollback`] then
    /// corrects to one path.
    pub fn run(
        &mut self,
        n: usize,
        tree: Option<&Tree>,
        mut step: impl FnMut(usize, &ConvWindow) -> Vec<f32>,
    ) {
        let Some(tree) = tree else {
            for t in 0..n {
                let inputs = step(t, self);
                self.push(&inputs);
            }
            return;
        };
        let start = ConvWindow {
            len: self.len,
            past: self.past.clone(),
            journal: None,
        };
        let mut after: Vec<ConvWindow> = Vec::with_capacity(n);
        for t in 0..n {
            let before = tree.parent(t).map_or(&start, |p| &after[p]);
            let inputs = step(t, before);
            let mut window = before.clone();
            window.push(&inputs);
            after.push(window);
            self.push(&inputs);
        }
    }

    /// [`ConvWindow::run`] for a batch without a tree, in parallel over
    /// tokens. Row `t` of `out` gets `f(t, ch, window, x)` for every channel
    /// `ch`, where `window` holds what the channel's window holds before
    /// token `t`, oldest first, and `x` is its input: row `t` of `inputs`,
    /// read every `stride` values. Every input is then pushed.
    pub fn run_batch(
        &mut self,
        inputs: &[f32],
        stride: usize,
        out: &mut [f32],
        f: impl Fn(usize, usize, &[f32], f32) -> f32 + Sync,
    ) {
        let (channels, len) = (self.channels(), self.len);
        let n = out.len() / channels;
        let input = |t: usize, ch: usize| inputs[t * stride + ch];
        // Slot `j` before token `t` holds the input of token `t - len + j`,
        // which before the batch sits in slot `t + j` of the stored window.
        let slot = |past: &[f32], t: usize, j: usize, ch: usize| match (t + j).checked_sub(len) {
            Some(s) => input(s, ch),
            None => past[ch * len + t + j],
        };
        pool::for_each_chunk(out, VALUES_PER_TASK, |task, out| {
            let mut window = vec![0.0; len];
            let first = task * VALUES_PER_TASK;
            let (mut t, mut ch) = (first / channels, first % channels);
            for o in out {
                for (j, w) in window.iter_mut().enumerate() {
                    *w = slot(&self.past, t, j, ch);
                }
                *o = f(t, ch, &window, input(t, ch));
                ch += 1;
                if ch == channels {
                    (t, ch) = (t + 1, 0);
                }
            }
        });
        if let Some(j) = &mut self.journal {
            for t in 0..n {
                j.inputs
                    .extend_from_slice(&inputs[t * stride..][..channels]);
            }
        }
        let mut past = vec![0.0; self.past.len()];
        for (ch, p) in past.chunks_exact_mut(len).enumerate() {
            for (j, p) in p.iter_mut().enumerate() {
                *p = slot(&self.past, n, j, ch);
            }
        }
        self.past = past;
    }

    pub fn checkpoint(&mut self) {
        self.journal = Some(Journal {
            start: self.past.clone(),
            inputs: Vec::new(),
        });
    }

    /// Keeps `rows`, an increasing path through the tokens pushed since the
    /// checkpoint, as if only they had been pushed, and stops recording.
    pub fn rollback(&mut self, rows: &[usize]) {
        let Some(j) = self.journal.take() else { return };
        let channels = self.channels();
        if j.inputs.len() == rows.len() * channels {
            return;
        }
        self.past = j.start;
        for &row in rows {
            self.push(&j.inputs[row * channels..][..channels]);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A batch sees and leaves the windows that pushing token by token
    /// does, for batches shorter and longer than the window.
    #[test]
    fn batches_match_tokens_one_by_one() {
        let (channels, stride) = (3, 5);
        for n in [1, 2, 3, 7, 40] {
            let inputs: Vec<f32> = (0..n * stride).map(|i| i as f32 * 0.5 - 7.0).collect();
            let mut alone = ConvWindow::new(channels, 4);
            alone.push(&[1.0, 2.0, 3.0]);
            let mut first = alone.clone();
            first.push(&inputs[..channels]);
            let mut batch = alone.clone();
            batch.checkpoint();
            let f = |t: usize, ch: usize, w: &[f32], x: f32| {
                w.iter().sum::<f32>() * 3.0 + x + (t * channels + ch) as f32 * 1e-3
            };
            let mut want = vec![0.0; n * channels];
            for t in 0..n {
                let row = &inputs[t * stride..][..channels];
                for ch in 0..channels {
                    want[t * channels + ch] = f(t, ch, alone.past(ch), row[ch]);
                }
                alone.push(row);
            }
            let mut out = vec![0.0; n * channels];
            batch.run_batch(&inputs, stride, &mut out, f);
            assert_eq!(out, want, "{n} tokens");
            assert_eq!(batch.past, alone.past, "{n} tokens");
            batch.rollback(&[0]);
            assert_eq!(batch.past, first.past, "{n} tokens, first kept");
        }
    }

    #[test]
    fn rollback_equals_pushing_only_the_kept_tokens() {
        let tokens: Vec<Vec<f32>> = (0..5).map(|t| vec![t as f32, 10.0 + t as f32]).collect();
        let mut a = ConvWindow::new(2, 4);
        a.push(&tokens[0]);
        a.checkpoint();
        for t in &tokens[1..] {
            a.push(t);
        }
        a.rollback(&[0, 1]);

        let mut b = ConvWindow::new(2, 4);
        for t in &tokens[..3] {
            b.push(t);
        }
        assert_eq!(a.past, b.past);
    }
}
