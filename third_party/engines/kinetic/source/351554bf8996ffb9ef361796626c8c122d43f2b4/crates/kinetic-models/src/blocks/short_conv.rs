use kinetic_cpu::dot;
use kinetic_quant::Matrix;

use super::conv_window::ConvWindow;
use super::tree::Tree;

/// Gated short causal convolution: the input projection gives an input
/// gate `b`, an output gate `c` and a value `x`; `b * x` goes through a
/// depthwise convolution and the result is scaled by `c`.
pub struct ShortConv<'a> {
    pub in_proj: Matrix<'a>,
    /// `taps` per channel, oldest input first.
    pub conv: Vec<f32>,
    pub taps: usize,
    pub out_proj: Matrix<'a>,
}

/// The previous `taps - 1` gated inputs per channel.
#[derive(Clone)]
pub struct ShortConvState {
    pub(super) window: ConvWindow,
}

impl ShortConvState {
    pub fn checkpoint(&mut self) {
        self.window.checkpoint();
    }

    /// See [`ConvWindow::rollback`].
    pub fn rollback(&mut self, rows: &[usize]) {
        self.window.rollback(rows);
    }
}

impl ShortConv<'_> {
    pub fn new_state(&self) -> ShortConvState {
        ShortConvState {
            window: ConvWindow::new(self.out_proj.cols, self.taps),
        }
    }

    /// Runs a batch; with `tree`, each row continues from its parent row.
    pub fn forward(&self, h: &[f32], tree: Option<&Tree>, state: &mut ShortConvState) -> Vec<f32> {
        let n = h.len() / self.in_proj.cols;
        let mixed = self.mix(self.project(h), n, tree, state);
        super::output(&self.out_proj, &mixed)
    }

    /// The gates and values of a batch.
    pub(super) fn project(&self, h: &[f32]) -> Vec<Vec<f32>> {
        vec![super::output(&self.in_proj, h)]
    }

    /// [`ShortConv::forward`] from the projection of its `n` tokens, up to
    /// the input of the output projection.
    pub(super) fn mix(
        &self,
        p: Vec<Vec<f32>>,
        n: usize,
        tree: Option<&Tree>,
        state: &mut ShortConvState,
    ) -> Vec<f32> {
        let d = self.out_proj.cols;
        let taps = self.taps;
        let [bcx]: [Vec<f32>; 1] = p.try_into().expect("one projection");

        let mut y = vec![0.0; n * d];
        if tree.is_none() {
            let gated: Vec<f32> = (0..n * d)
                .map(|i| bcx[i / d * 3 * d + i % d] * bcx[i / d * 3 * d + 2 * d + i % d])
                .collect();
            state.window.run_batch(&gated, d, &mut y, |t, ch, past, x| {
                let w = &self.conv[ch * taps..][..taps];
                let acc = dot(&w[..taps - 1], past) + w[taps - 1] * x;
                bcx[t * 3 * d + d + ch] * acc
            });
            return y;
        }
        state.window.run(n, tree, |t, window| {
            let (b, rest) = bcx[t * 3 * d..][..3 * d].split_at(d);
            let (gate, x) = rest.split_at(d);
            let y = &mut y[t * d..][..d];
            let inputs: Vec<f32> = b.iter().zip(x).map(|(b, x)| b * x).collect();
            for ch in 0..d {
                let w = &self.conv[ch * taps..][..taps];
                let acc = dot(&w[..taps - 1], window.past(ch)) + w[taps - 1] * inputs[ch];
                y[ch] = gate[ch] * acc;
            }
            inputs
        });

        y
    }
}
