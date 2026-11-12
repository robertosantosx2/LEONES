use std::ops::Range;
use std::rc::Rc;

use crate::commands::Commands;
use crate::device::Device;
use crate::error::{Error, Result};
use crate::memory::{DeviceBuffer, HostBuffer};

/// Words of the batch before its tables.
pub const BATCH_HEADER: usize = 16;

/// What every model kernel reads about the pass it is part of: how many
/// tokens run and from which position, which rows the output head takes,
/// where recurrent layers start, and tables the host computes per pass,
/// such as rotary angles.
///
/// Commands recorded once read the batch from the device, so one recording
/// serves passes of any size up to [`Batch::rows`]. The host sets the words
/// before each run; a copy recorded by [`Batch::record_upload`] moves them
/// to the device.
pub struct Batch {
    host: HostBuffer<u32>,
    device: DeviceBuffer<u32>,
    rows: usize,
    head_rows: usize,
    positions: usize,
}

impl Batch {
    /// A batch for passes of up to `rows` tokens within the first
    /// `positions` positions, the output head taking up to `head_rows` of
    /// them, with `table_words` words of tables after the header.
    pub fn new(
        device: &Rc<Device>,
        rows: usize,
        head_rows: usize,
        positions: usize,
        table_words: usize,
    ) -> Result<Batch> {
        let words = BATCH_HEADER + table_words;
        if rows == 0 || head_rows > rows || u32::try_from(positions.max(words)).is_err() {
            return Err(Error::Shape(format!(
                "batch of {rows} rows, {head_rows} for the head, {positions} positions"
            )));
        }
        Ok(Batch {
            host: HostBuffer::new(device, words)?,
            device: DeviceBuffer::new(device, words)?,
            rows,
            head_rows,
            positions,
        })
    }

    /// Most tokens a pass runs.
    pub fn rows(&self) -> usize {
        self.rows
    }

    /// Most rows the output head runs on in one pass.
    pub fn head_rows(&self) -> usize {
        self.head_rows
    }

    /// Positions a pass may reach.
    pub fn positions(&self) -> usize {
        self.positions
    }

    /// Words of tables after the header.
    pub fn table_words(&self) -> usize {
        self.host.len() - BATCH_HEADER
    }

    /// Sets the next pass: `n` tokens from position `pos`, the output head
    /// on rows `head` of them. With `since`, the position of a checkpoint,
    /// recurrent layers replay the tokens run since it before the pass and
    /// leave their state as it was at the checkpoint; without, they run
    /// on from their state and keep it.
    pub fn set(
        &mut self,
        n: usize,
        pos: usize,
        head: Range<usize>,
        since: Option<usize>,
    ) -> Result<()> {
        let from = since.unwrap_or(pos);
        let fits = (1..=self.rows).contains(&n)
            && pos + n <= self.positions
            && from <= pos
            && pos + n - from <= self.rows
            && head.start <= head.end
            && head.end <= n
            && head.len() <= self.head_rows;
        if !fits {
            return Err(Error::Shape(format!(
                "pass of {n} tokens from position {pos}, head on rows {head:?}, in a batch of \
                 {} rows, {} positions and {} head rows",
                self.rows, self.positions, self.head_rows
            )));
        }
        let keep = since.is_none();
        let words = [n, pos, head.start, head.len(), from, keep as usize].map(|w| w as u32);
        self.host.as_mut_slice()[..6].copy_from_slice(&words);
        Ok(())
    }

    /// Sets a pass that runs no token: recurrent layers replay the tokens
    /// from position `from`, a checkpoint, up to `to` and keep the state
    /// after them, which is how a rollback keeps what it keeps.
    pub fn set_replay(&mut self, from: usize, to: usize) -> Result<()> {
        if from > to || to - from > self.rows || to > self.positions {
            return Err(Error::Shape(format!(
                "replay of positions {from} to {to} in a batch of {} rows",
                self.rows
            )));
        }
        let words = [0, to, 0, 0, from, 1].map(|w| w as u32);
        self.host.as_mut_slice()[..6].copy_from_slice(&words);
        Ok(())
    }

    /// The tables, from word [`BATCH_HEADER`] on.
    pub fn tables_mut(&mut self) -> &mut [u32] {
        &mut self.host.as_mut_slice()[BATCH_HEADER..]
    }

    /// Records the copy of the words to the device; kernels recorded after
    /// it read them.
    pub fn record_upload(&self, commands: &mut Commands) -> Result<()> {
        commands.upload(&self.host, 0, &self.device, 0, self.host.len())
    }

    pub(crate) fn device(&self) -> &DeviceBuffer<u32> {
        &self.device
    }
}
