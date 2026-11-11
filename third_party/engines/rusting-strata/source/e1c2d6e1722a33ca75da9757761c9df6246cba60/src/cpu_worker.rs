//! CPU side of the expert split, without per-layer stream syncs. For each MoE layer the GPU writes routing ids,
//! weights, cache slots and (when some expert missed) the normed activation into host-mapped pinned memory, then
//! raises the layer's request flag (on CUDA a layer with no miss raises only its skip flag). This worker spins on the
//! flag, computes the missed experts with `cpu_moe`, writes their weighted sum back and raises the done flag, which the
//! GPU combine kernel waits on only if the layer missed.

use crate::model::Model;
use crate::backend::{Backend, Buf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering, fence};
use std::sync::{Arc, mpsc};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

/// Word offsets inside one layer's mailbox. Flags sit on separate cache lines.
pub const REQ: usize = 0;
/// Tokens in the request (1 for decode, up to `TMAX` for a multi-token verify).
pub const NTOK: usize = 1;
/// Raised instead of REQ, with no data, when no expert of the layer missed (CUDA only; Vulkan raises REQ).
pub const SKIP: usize = 2;
/// Vulkan: the combine's verdict on its wait (0 open, 1 the worker answered, 2 gave up; see mb_wait.glsl).
pub const VERDICT: usize = 8;
pub const DONE: usize = 16;
pub const IDS: usize = 32;

/// Most tokens one request may carry.
pub const TMAX: usize = 4;

/// Per layer: ids, weights and slots for up to TMAX tokens of `k` entries (token t at t * k; the three arrays are
/// each NTOK * k long), then TMAX activations of `n` floats at `h` and TMAX results at `y`.
pub struct Mailbox { pub k: usize, pub n: usize, pub h: usize, pub y: usize, pub stride: usize }

impl Mailbox {
    pub fn new(k: usize, n: usize) -> Mailbox {
        let h = (IDS + 3 * TMAX * k).next_multiple_of(16);
        Mailbox { k, n, h, y: h + TMAX * n, stride: (h + 2 * TMAX * n).next_multiple_of(16) }
    }
}

pub struct CpuWorker {
    _mem: Buf,
    host: usize,
    /// Device address of the mailboxes (layer `il` at `dev + 4 * il * layout.stride`).
    pub dev: u64,
    pub layout: Mailbox,
    seq: u32,
    layers: Vec<usize>,
    tx: Option<mpsc::Sender<u32>>,
    stop: Arc<AtomicBool>,
    busy_ns: Arc<AtomicU64>,
    thread: Option<JoinHandle<()>>,
}

impl CpuWorker {
    /// Mailboxes cover layers up to the largest of `moe_layers`. Safety: `m` must outlive the worker (it is joined on drop).
    pub fn new(m: &Model, gpu: &dyn Backend, moe_layers: Vec<usize>) -> anyhow::Result<CpuWorker> {
        let c = &m.cfg;
        let layout = Mailbox::new(c.n_expert_used, c.n_embd);
        let len = layout.stride * moe_layers.iter().max().map_or(0, |&il| il + 1);
        let (mem, host) = gpu.host_mailbox(len)?;
        let (host, dev) = (host as usize, mem.addr());

        let (tx, rx) = mpsc::channel::<u32>();
        let (stop, busy_ns) = (Arc::new(AtomicBool::new(false)), Arc::new(AtomicU64::new(0)));
        let (st, bn) = (stop.clone(), busy_ns.clone());
        let mp = m as *const Model as usize;
        let lay = Mailbox::new(c.n_expert_used, c.n_embd);
        let layers = moe_layers.clone();
        // STRATA_TEST_WORKER_DELAY=ms: answer some requests (layer and seq picked by a hash) that much later, as a
        // worker reading experts from a cold drive would (tests the combines that give up).
        let delay = std::env::var("STRATA_TEST_WORKER_DELAY").ok().and_then(|v| v.parse::<u64>().ok()).map(Duration::from_millis);
        // The loop runs on a thread of its own pool, so the expert passes start on it at once and it takes part
        // in them instead of sleeping until a woken pool finishes (~12 us less per layer).
        let pool = rayon::ThreadPoolBuilder::new().num_threads(rayon::current_num_threads())
            .thread_name(|i| format!("strata-experts-{i}")).build()?;
        let thread = std::thread::Builder::new().name("strata-cpu-experts".into()).spawn(move || pool.install(move || {
            let m = unsafe { &*(mp as *const Model) };
            // Missed experts not in the page cache are read from the drive: reading all of a layer's ahead keeps
            // the reads in flight together instead of one page fault at a time per compute thread.
            let pre = crate::weights::Prefetch::start();
            let w = |i: usize| host as *mut u32 as usize + 4 * i;
            while let Ok(seq) = rx.recv() {
                for &il in &moe_layers {
                    let b = il * lay.stride;
                    let at = |o: usize| (w(b + o)) as *mut u32;
                    // Skip the layer on its skip flag, or on a newer seq anywhere (the GPU already moved on to the
                    // next token, so it did not wait for this one). Waiting for the old seq would hang.
                    let ahead = |v: u32| v != 0 && (v.wrapping_sub(seq) as i32) >= 0;
                    let mut r;
                    while { r = unsafe { at(REQ).read_volatile() }; r != seq } {
                        if st.load(Ordering::Relaxed) { return; }
                        if ahead(r) || ahead(unsafe { at(SKIP).read_volatile() }) { break; }
                        std::hint::spin_loop();
                    }
                    if r != seq { continue; }
                    // mfence: loads of write-combining memory (the Vulkan BAR mailbox) are weakly ordered, so an
                    // acquire fence (no instruction on x86) would not keep them after the REQ load.
                    fence(Ordering::SeqCst);
                    let t0 = Instant::now();
                    let rd = |o: usize| unsafe { at(o).read_volatile() };
                    let nt = (rd(NTOK) as usize).clamp(1, TMAX);
                    let (k, kt, n) = (lay.k, lay.k * nt, lay.n);
                    // Bulk streaming reads, as in `routing`: plain loads of the Vulkan BAR mailbox are each an
                    // uncached read (~130 us for one activation).
                    let mut v = vec![0u32; (3 * kt).next_multiple_of(4)];
                    unsafe { read_wc(at(IDS), &mut v) };
                    let missed: Vec<usize> = (0..kt).filter(|&j| (v[2 * kt + j] as i32) < 0).map(|j| v[j] as usize).collect();
                    if !missed.is_empty() {
                        // Gate and up first: they are read first.
                        pre.send(["ffn_gate_exps.weight", "ffn_up_exps.weight", "ffn_down_exps.weight"].iter()
                            .filter_map(|s| m.w.layer(il, s).ok())
                            .flat_map(|t| missed.iter().map(move |&e| { let d = t.expert(e, m.cfg.n_expert).data; (d.as_ptr() as usize, d.len()) }).collect::<Vec<_>>())
                            .collect());
                    }
                    for t in 0..nt {
                        let sel: Vec<(usize, f32)> = (t * k..(t + 1) * k).filter(|&j| (v[2 * kt + j] as i32) < 0)
                            .map(|j| (v[j] as usize, f32::from_bits(v[kt + j]))).collect();
                        if sel.is_empty() { continue; }
                        let mut h = vec![0u32; n];
                        unsafe { read_wc(at(lay.h + t * n), &mut h) };
                        let h: Vec<f32> = h.into_iter().map(f32::from_bits).collect();
                        let y = crate::cpu_moe::experts(m, il, &h, &sel);
                        unsafe { std::ptr::copy_nonoverlapping(y.as_ptr(), at(lay.y + t * n) as *mut f32, n) };
                    }
                    // SeqCst fences (mfence on x86) also order and flush write-combining stores (Vulkan maps the
                    // mailbox through the BAR): y before DONE, and DONE out now.
                    if let Some(d) = delay { if (seq as usize * 31 + il) % 17 == 0 { std::thread::sleep(d) } }
                    fence(Ordering::SeqCst);
                    unsafe { at(DONE).write_volatile(seq) };
                    fence(Ordering::SeqCst);
                    bn.fetch_add(t0.elapsed().as_nanos() as u64, Ordering::Relaxed);
                }
            }
        }))?;
        Ok(CpuWorker { _mem: mem, host, dev, layout, seq: 0, layers, tx: Some(tx), stop, busy_ns, thread: Some(thread) })
    }

    /// Start a new token: returns the sequence number the GPU must publish with.
    pub fn begin(&mut self) -> u32 {
        self.seq = self.seq.wrapping_add(1).max(1);
        let _ = self.tx.as_ref().unwrap().send(self.seq);
        self.seq
    }

    /// Routing of layer `il` from the last finished request, all its tokens: (expert id, routed weight, slot or -1).
    pub fn routing(&self, il: usize) -> Vec<(i32, f32, i32)> {
        let b = il * self.layout.stride;
        let rd = |o: usize| unsafe { (self.host as *const u32).add(b + o).read_volatile() };
        let k = self.layout.k * (rd(NTOK) as usize).clamp(1, TMAX);
        // One bulk read: on Vulkan the mailbox is BAR memory, where each host read is a slow uncached access.
        let mut v = vec![0u32; (3 * k).next_multiple_of(4)];
        unsafe { read_wc((self.host as *const u32).add(b + IDS), &mut v) };
        (0..k).map(|j| (v[j] as i32, f32::from_bits(v[k + j]), v[2 * k + j] as i32)).collect()
    }

    /// The first layer whose combine gave up waiting (verdict 2) in the last request: the layers before it ran.
    pub fn stalled_layer(&self) -> Option<usize> {
        self.layers.iter().copied().find(|&il| unsafe { (self.host as *const u32).add(il * self.layout.stride + VERDICT).read_volatile() } == 2)
    }

    /// Wait until the worker has answered layer `il` of the current request, then reopen the layer's verdict so its
    /// combine can run again.
    pub fn wait_done(&self, il: usize) -> anyhow::Result<()> {
        let at = |o: usize| unsafe { (self.host as *mut u32).add(il * self.layout.stride + o) };
        while unsafe { at(DONE).read_volatile() } != self.seq {
            anyhow::ensure!(!self.thread.as_ref().is_some_and(|t| t.is_finished()), "the CPU expert worker stopped");
            std::thread::sleep(Duration::from_micros(50));
        }
        unsafe { at(VERDICT).write_volatile(0) };
        fence(Ordering::SeqCst);
        Ok(())
    }

    /// Total time the worker spent computing experts.
    pub fn busy(&self) -> Duration { Duration::from_nanos(self.busy_ns.load(Ordering::Relaxed)) }
}

/// Copies `out.len()` (a multiple of 4) words from 16-byte aligned `p`. On write-combining memory (the Vulkan BAR
/// mailbox) streaming loads fetch a whole 64-byte line per read instead of one uncached read per load.
unsafe fn read_wc(p: *const u32, out: &mut [u32]) {
    #[cfg(target_feature = "sse4.1")]
    for (i, c) in out.chunks_exact_mut(4).enumerate() {
        use std::arch::x86_64::*;
        unsafe { _mm_storeu_si128(c.as_mut_ptr() as *mut __m128i, _mm_stream_load_si128(p.add(4 * i) as *const __m128i)) };
    }
    #[cfg(not(target_feature = "sse4.1"))]
    unsafe { std::ptr::copy_nonoverlapping(p, out.as_mut_ptr(), out.len()) };
}

impl Drop for CpuWorker {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        self.tx = None;
        if let Some(t) = self.thread.take() { let _ = t.join(); }
    }
}
