use super::{CudaModel, CudaMtpState, CudaState};
use crate::speculative::{Predictor, Target};

fn device<T>(r: kinetic_cuda::Result<T>) -> T {
    r.unwrap_or_else(|e| panic!("CUDA: {e}"))
}

/// Scores are the greedy tokens themselves: logits stay on the device.
impl Target for CudaModel<'_> {
    type State = CudaState;
    type Scores = Vec<u32>;

    fn n_embd(&self) -> usize {
        self.n_embd
    }

    fn n_vocab(&self) -> usize {
        CudaModel::n_vocab(self)
    }

    fn score(&self, state: &mut CudaState, tokens: &[u32], all_rows: bool) -> (Vec<u32>, Vec<f32>) {
        let ran = self.run_seated(state, tokens, all_rows, false);
        (ran.greedy, ran.forward.hidden)
    }

    fn logits(
        &self,
        state: &mut CudaState,
        tokens: &[u32],
        all_rows: bool,
    ) -> (Vec<f32>, Vec<f32>) {
        let ran = self.run_seated(state, tokens, all_rows, true);
        (ran.forward.logits, ran.forward.hidden)
    }

    fn greedy(&self, scores: &Vec<u32>, row: usize) -> u32 {
        scores[row]
    }

    fn checkpoint(&self, state: &mut CudaState) {
        device(CudaModel::checkpoint(self, state));
    }

    fn rollback(&self, state: &mut CudaState, keep: usize) {
        device(CudaModel::rollback(self, state, keep));
    }
}

impl Predictor for CudaModel<'_> {
    type MtpState = CudaMtpState;

    fn new_mtp_state(&self) -> Option<CudaMtpState> {
        device(CudaModel::new_mtp_state(self))
    }

    fn clear_mtp_state(&self, state: &mut CudaMtpState) {
        device(CudaModel::clear_mtp_state(self, state));
    }

    fn mtp_len(&self, state: &CudaMtpState) -> usize {
        state.len()
    }

    fn mtp_forward(&self, state: &mut CudaMtpState, hidden: &[f32], tokens: &[u32]) -> Vec<f32> {
        device(CudaModel::mtp_forward(self, state, hidden, tokens))
    }

    fn draft_token(&self, state: &mut CudaMtpState, hidden: &[f32], vocab: usize) -> u32 {
        device(CudaModel::draft_token(self, state, hidden, vocab))
    }

    fn mtp_checkpoint(&self, state: &mut CudaMtpState) {
        device(CudaModel::mtp_checkpoint(self, state));
    }

    fn mtp_rollback(&self, state: &mut CudaMtpState, fed: usize, keep: usize) {
        device(CudaModel::mtp_rollback(self, state, fed, keep));
    }
}
