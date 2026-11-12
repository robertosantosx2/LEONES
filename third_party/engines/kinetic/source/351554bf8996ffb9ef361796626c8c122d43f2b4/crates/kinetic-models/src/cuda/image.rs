//! Prompts with image rows on the device.

use kinetic_cuda::{Flow, MAX_BATCH};

use super::{shape, CudaModel, CudaState};
use crate::Input;

impl CudaModel<'_> {
    /// Whether [`CudaModel::run_inputs`] takes images, which it does when
    /// every layer runs on the device.
    pub fn takes_images(&self) -> bool {
        self.front == 0 && !self.routes_on_host()
    }

    /// Runs `inputs` in order as [`Model::run_inputs`](crate::Model::run_inputs)
    /// does, outside any checkpoint.
    pub fn run_inputs(&self, state: &mut CudaState, inputs: &[Input]) -> kinetic_cuda::Result<()> {
        if !self.takes_images() || state.checkpoint.is_some() {
            return Err(shape(
                "images need every layer on the device and no checkpoint".into(),
            ));
        }
        for input in inputs {
            match *input {
                Input::Tokens([]) => {}
                Input::Tokens(tokens) => {
                    self.forward(state, tokens, false, false)?;
                }
                Input::Image {
                    rows,
                    width,
                    height,
                } => self.run_image(state, rows, width, height)?,
            }
        }
        Ok(())
    }

    fn run_image(
        &self,
        state: &mut CudaState,
        rows: &[f32],
        width: usize,
        height: usize,
    ) -> kinetic_cuda::Result<()> {
        let n = width * height;
        if rows.len() != n * self.n_embd || state.pos + n > self.context {
            return Err(shape(format!(
                "image of {width}x{height} rows of {} values at {} of {}",
                rows.len() / n.max(1),
                state.pos,
                self.context
            )));
        }
        let grid_rope = self.host.grid_rope;
        let shift = state.work.batch.grid_shift();
        let t = (state.pos - shift) as u32;
        let grid: Vec<[u32; 3]> = (0..height as u32)
            .flat_map(|r| (0..width as u32).map(move |c| [t, t + r, t + c]))
            .collect();
        match self.spare.as_ref().filter(|_| n > MAX_BATCH) {
            Some(spare) => {
                let mut spare = spare.borrow_mut();
                let step = state.step.take();
                spare.swap(&mut state.work);
                state.work.batch.set_grid_shift(shift);
                let out = self.queue_image(state, rows, &grid, self.batch_rows());
                spare.swap(&mut state.work);
                state.step = step;
                out?;
            }
            None => self.queue_image(state, rows, &grid, self.state_rows())?,
        }
        if grid_rope {
            // the image spans as many positions as its longer side
            state
                .work
                .batch
                .set_grid_shift(shift + n - width.max(height));
        }
        Ok(())
    }

    fn queue_image(
        &self,
        state: &mut CudaState,
        rows: &[f32],
        grid: &[[u32; 3]],
        chunk: usize,
    ) -> kinetic_cuda::Result<()> {
        let stream = &self.gpu.stream;
        for (rows, grid) in rows.chunks(chunk * self.n_embd).zip(grid.chunks(chunk)) {
            let work = &mut state.work;
            match self.host.grid_rope {
                true => work.batch.set_grid(state.pos, grid, stream)?,
                false => work.batch.set(state.pos, &vec![0; grid.len()], stream)?,
            }
            work.scratch.x.copy_range_from(0, rows)?;
            self.queue_layers(work, Flow::Commit)?;
            state.pos += grid.len();
        }
        Ok(())
    }
}
