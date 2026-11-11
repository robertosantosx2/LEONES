use std::rc::Rc;

use crate::context::Context;
use crate::error::{Error, Result};
use crate::memory::DeviceBuffer;
use crate::stream::Stream;

/// The tokens a model runs next and the position of the first, on the
/// device as `[position, ids...]`. Kernels read both from there rather than
/// taking them as launch arguments, so a captured [`Graph`](crate::Graph)
/// replays with whatever the batch holds when it is launched.
///
/// A batch with grid positions also carries a (time, row, column) rotary
/// position for every token after the ids, for models whose rotary pairs
/// turn by those in turn.
pub struct Batch {
    device: DeviceBuffer<u32>,
    host: Vec<u32>,
    capacity: usize,
    /// How far text positions trail cache positions after images, when the
    /// batch carries grid positions.
    grid_shift: Option<usize>,
}

impl Batch {
    /// Room for `capacity` tokens.
    pub fn new(ctx: &Rc<Context>, capacity: usize) -> Result<Batch> {
        Ok(Batch {
            device: DeviceBuffer::new(ctx, 4 * capacity + 1)?,
            host: vec![0],
            capacity,
            grid_shift: None,
        })
    }

    /// Makes every later batch carry grid positions; text tokens get their
    /// own position, less [`Batch::set_grid_shift`], in all three.
    pub fn use_grid(&mut self) {
        self.grid_shift.get_or_insert(0);
    }

    /// Sets how far the positions of text tokens trail their cache slots.
    pub fn set_grid_shift(&mut self, shift: usize) {
        if let Some(s) = self.grid_shift.as_mut() {
            *s = shift;
        }
    }

    /// How far the positions of text tokens trail their cache slots.
    pub fn grid_shift(&self) -> usize {
        self.grid_shift.unwrap_or(0)
    }

    /// Queues the upload of `tokens`, the first at position `pos`, on `stream`.
    pub fn set(&mut self, pos: usize, tokens: &[u32], stream: &Stream) -> Result<()> {
        let shift = self.grid_shift.unwrap_or(0);
        let grid = (pos..pos + tokens.len()).map(|p| [(p - shift) as u32; 3]);
        self.fill(pos, tokens, grid, stream)
    }

    /// Queues the upload of embedding rows at position `pos` on, each with
    /// its (time, row, column) rotary position, on `stream`. Needs
    /// [`Batch::use_grid`].
    pub fn set_grid(&mut self, pos: usize, grid: &[[u32; 3]], stream: &Stream) -> Result<()> {
        if self.grid_shift.is_none() {
            return Err(Error::Shape("grid positions in a plain batch".into()));
        }
        let ids = vec![0; grid.len()];
        self.fill(pos, &ids, grid.iter().copied(), stream)
    }

    fn fill(
        &mut self,
        pos: usize,
        tokens: &[u32],
        grid: impl Iterator<Item = [u32; 3]>,
        stream: &Stream,
    ) -> Result<()> {
        if tokens.len() > self.capacity || u32::try_from(pos + tokens.len()).is_err() {
            return Err(Error::Shape(format!(
                "batch of {} tokens at {pos} into room for {} below position 2^32",
                tokens.len(),
                self.capacity
            )));
        }
        self.host.clear();
        self.host.push(pos as u32);
        self.host.extend_from_slice(tokens);
        if self.grid_shift.is_some() {
            self.host.extend(grid.flatten());
        }
        // SAFETY: `host` is ordinary pageable memory, which the driver stages
        // before returning, so it may change right after.
        unsafe { self.device.copy_range_from_async(0, &self.host, stream) }
    }

    /// Tokens in the batch.
    pub fn len(&self) -> usize {
        match self.grid_shift {
            Some(_) => (self.host.len() - 1) / 4,
            None => self.host.len() - 1,
        }
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Position of the first token.
    pub fn pos(&self) -> usize {
        self.host[0] as usize
    }

    pub(crate) fn device_ptr(&self) -> u64 {
        self.device.device_ptr()
    }

    /// Where the grid positions of the batch start on the device, or 0.
    pub(crate) fn grid_ptr(&self) -> u64 {
        match self.grid_shift {
            Some(_) => self.device.device_ptr() + 4 * (1 + self.len() as u64),
            None => 0,
        }
    }
}
