use std::ptr;
use std::rc::Rc;

use crate::context::Context;
use crate::driver::{CuEvent, CuStream};
use crate::error::Result;

/// A queue of device work. Created blocking, so it also orders against the
/// synchronous copies of [`DeviceBuffer`](crate::DeviceBuffer).
pub struct Stream {
    raw: CuStream,
    ctx: Rc<Context>,
}

impl Stream {
    pub fn new(ctx: &Rc<Context>) -> Result<Stream> {
        let api = ctx.enter()?;
        let mut raw = ptr::null_mut();
        // SAFETY: `raw` is a valid out-pointer; flags 0 is the default stream kind.
        api.check("cuStreamCreate", unsafe {
            (api.stream_create)(&mut raw, 0)
        })?;
        Ok(Stream {
            raw,
            ctx: ctx.clone(),
        })
    }

    /// Waits until all work queued so far has finished.
    pub fn synchronize(&self) -> Result<()> {
        let api = self.ctx.enter()?;
        // SAFETY: `raw` is a live stream.
        api.check("cuStreamSynchronize", unsafe {
            (api.stream_synchronize)(self.raw)
        })
    }

    /// Makes work queued from now on wait until `event` has passed.
    pub fn wait(&self, event: &Event) -> Result<()> {
        let api = self.ctx.enter()?;
        // SAFETY: both handles are live; flags 0 is the only kind.
        api.check("cuStreamWaitEvent", unsafe {
            (api.stream_wait_event)(self.raw, event.raw, 0)
        })
    }

    pub(crate) fn raw(&self) -> CuStream {
        self.raw
    }

    pub(crate) fn context(&self) -> &Rc<Context> {
        &self.ctx
    }
}

impl Drop for Stream {
    fn drop(&mut self) {
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `raw` is live and destroyed once; queued work still completes.
            unsafe { (api.stream_destroy)(self.raw) };
        }
    }
}

/// A marker in a stream, used to time device work or to order streams.
pub struct Event {
    raw: CuEvent,
    ctx: Rc<Context>,
}

impl Event {
    pub fn new(ctx: &Rc<Context>) -> Result<Event> {
        let api = ctx.enter()?;
        let mut raw = ptr::null_mut();
        // SAFETY: `raw` is a valid out-pointer; flags 0 records timing.
        api.check("cuEventCreate", unsafe { (api.event_create)(&mut raw, 0) })?;
        Ok(Event {
            raw,
            ctx: ctx.clone(),
        })
    }

    /// Marks the point in `stream` after all work queued so far.
    pub fn record(&self, stream: &Stream) -> Result<()> {
        let api = self.ctx.enter()?;
        // SAFETY: both handles are live.
        api.check("cuEventRecord", unsafe {
            (api.event_record)(self.raw, stream.raw())
        })
    }

    /// Waits until the stream has passed this event.
    pub fn synchronize(&self) -> Result<()> {
        let api = self.ctx.enter()?;
        // SAFETY: `raw` is a live event.
        api.check("cuEventSynchronize", unsafe {
            (api.event_synchronize)(self.raw)
        })
    }

    /// Milliseconds from this event to `later`; both must have completed.
    pub fn elapsed_ms(&self, later: &Event) -> Result<f32> {
        let api = self.ctx.enter()?;
        let mut ms = 0.0;
        // SAFETY: `ms` is a valid out-pointer and both events are live.
        api.check("cuEventElapsedTime", unsafe {
            (api.event_elapsed_time)(&mut ms, self.raw, later.raw)
        })?;
        Ok(ms)
    }
}

impl Drop for Event {
    fn drop(&mut self) {
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `raw` is live and destroyed once.
            unsafe { (api.event_destroy)(self.raw) };
        }
    }
}
