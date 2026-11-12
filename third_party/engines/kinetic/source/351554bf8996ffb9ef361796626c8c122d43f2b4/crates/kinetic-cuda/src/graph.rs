use std::ffi::c_uint;
use std::ptr;
use std::rc::Rc;

use crate::context::Context;
use crate::driver::{CuGraph, CuGraphExec};
use crate::error::Result;
use crate::stream::Stream;

/// CU_STREAM_CAPTURE_MODE_THREAD_LOCAL: only this thread's calls may not
/// interfere with the capture.
const CAPTURE_THREAD_LOCAL: c_uint = 1;

/// Recorded stream work that replays with one launch, cutting the launch
/// cost of many small kernels.
pub struct Graph {
    exec: CuGraphExec,
    ctx: Rc<Context>,
}

impl Stream {
    /// Records the kernels `record` queues on this stream into a graph
    /// instead of running them. Only kernel launches, copies to page-locked
    /// memory and event records and waits, which also bring other streams'
    /// work into the graph, may be queued while recording.
    pub fn capture(&self, record: impl FnOnce() -> Result<()>) -> Result<Graph> {
        let ctx = self.context().clone();
        let api = ctx.enter()?;
        // SAFETY: the stream is live and not being captured.
        api.check("cuStreamBeginCapture", unsafe {
            (api.stream_begin_capture)(self.raw(), CAPTURE_THREAD_LOCAL)
        })?;
        let recorded = record();
        let mut graph: CuGraph = ptr::null_mut();
        // SAFETY: ends the capture begun above, whatever `record` did.
        let ended = api.check("cuStreamEndCapture", unsafe {
            (api.stream_end_capture)(self.raw(), &mut graph)
        });
        let graph = OwnedGraph {
            raw: graph,
            ctx: &ctx,
        };
        recorded?;
        ended?;
        let mut exec = ptr::null_mut();
        // SAFETY: `graph` is a complete graph; flags 0 is the default.
        api.check("cuGraphInstantiate", unsafe {
            (api.graph_instantiate)(&mut exec, graph.raw, 0)
        })?;
        Ok(Graph {
            exec,
            ctx: ctx.clone(),
        })
    }
}

impl Graph {
    /// Queues the recorded work on `stream`.
    pub fn launch(&self, stream: &Stream) -> Result<()> {
        let api = self.ctx.enter()?;
        // SAFETY: both handles are live; the buffers the work uses are kept
        // alive by its owner.
        api.check("cuGraphLaunch", unsafe {
            (api.graph_launch)(self.exec, stream.raw())
        })
    }
}

impl Drop for Graph {
    fn drop(&mut self) {
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `exec` is live and destroyed once; launched work still completes.
            unsafe { (api.graph_exec_destroy)(self.exec) };
        }
    }
}

/// The template a capture produces, freed once instantiated.
struct OwnedGraph<'a> {
    raw: CuGraph,
    ctx: &'a Rc<Context>,
}

impl Drop for OwnedGraph<'_> {
    fn drop(&mut self) {
        if self.raw.is_null() {
            return;
        }
        if let Ok(api) = self.ctx.enter() {
            // SAFETY: `raw` came from cuStreamEndCapture and is destroyed once.
            unsafe { (api.graph_destroy)(self.raw) };
        }
    }
}
