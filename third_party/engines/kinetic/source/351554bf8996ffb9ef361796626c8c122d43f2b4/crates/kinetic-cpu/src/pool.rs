//! A pool of threads that spin between jobs, for the hundreds of short
//! parallel steps of every decoded token.
//!
//! Rayon parks idle threads and splits work by stealing, which costs more
//! than a whole matrix product of a small model. Here the workers spin on
//! one atomic word between jobs and claim tasks from it, so a job reaches
//! every thread within a cache-line transfer. The thread that starts a job
//! works on it too and returns once every task has finished; a worker that
//! is slow to notice a job simply finds no task left. Workers park after
//! spinning idle for a while, so a pool that is not used costs nothing.

use std::cell::UnsafeCell;
use std::panic::{self, AssertUnwindSafe};
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Condvar, Mutex, OnceLock};
use std::thread;
use std::time::{Duration, Instant};

/// How long an idle worker spins before it parks: longer than the gaps
/// between the parallel steps of a token and between tokens.
const SPIN: Duration = Duration::from_millis(2);

/// Busy-wait steps between offers of the core to other threads.
const YIELD_EVERY: u32 = 256;

/// Most tasks one job may have, so that a task index fits in [`State`].
const MAX_TASKS: usize = u16::MAX as usize;

/// Runs `f(i)` for every `i` in `0..tasks`, spread over the pool and the
/// calling thread, and returns when all have run. Calls made while the pool
/// is busy, from a task or from another thread, go through rayon instead.
pub fn for_each(tasks: usize, f: &(dyn Fn(usize) + Sync)) {
    match tasks {
        0 => {}
        1 => f(0),
        _ if tasks <= MAX_TASKS => pool().run(tasks, f),
        _ => {
            let per = tasks.div_ceil(MAX_TASKS);
            pool().run(tasks.div_ceil(per), &|c| {
                (c * per..tasks.min(c * per + per)).for_each(f)
            })
        }
    }
}

/// Calls `f(i, chunk)` for chunk `i` of `data` cut into `len` values (the
/// last chunk may be shorter), in parallel as [`for_each`] does.
pub fn for_each_chunk<T: Send>(data: &mut [T], len: usize, f: impl Fn(usize, &mut [T]) + Sync) {
    assert!(len > 0);
    let total = data.len();
    let data = Parts(data.as_mut_ptr());
    for_each(total.div_ceil(len), &|i| {
        let start = i * len;
        // SAFETY: the chunks are disjoint and inside `data`, which outlives
        // the job.
        let chunk =
            unsafe { std::slice::from_raw_parts_mut(data.at(start), len.min(total - start)) };
        f(i, chunk)
    });
}

/// [`for_each_chunk`] over two slices with as many chunks each: `f(i, a, b)`
/// gets chunk `i` of `a` cut into `a_len` values and of `b` cut into `b_len`.
pub fn for_each_chunk_pair<A: Send, B: Send>(
    a: &mut [A],
    a_len: usize,
    b: &mut [B],
    b_len: usize,
    f: impl Fn(usize, &mut [A], &mut [B]) + Sync,
) {
    assert!(a_len > 0 && b_len > 0);
    let tasks = a.len() / a_len;
    assert!(a.len() == tasks * a_len && b.len() == tasks * b_len);
    let (a, b) = (Parts(a.as_mut_ptr()), Parts(b.as_mut_ptr()));
    for_each(tasks, &|i| {
        // SAFETY: as in `for_each_chunk`, for both slices.
        let (a, b) = unsafe {
            (
                std::slice::from_raw_parts_mut(a.at(i * a_len), a_len),
                std::slice::from_raw_parts_mut(b.at(i * b_len), b_len),
            )
        };
        f(i, a, b)
    });
}

/// `(0..n).map(f).collect()`, with the calls spread over the pool.
pub fn map<T: Send>(n: usize, f: impl Fn(usize) -> T + Sync) -> Vec<T> {
    let mut out = Vec::<T>::with_capacity(n);
    let ptr = Parts(out.as_mut_ptr());
    for_each(n, &|i| {
        // SAFETY: each index is written once, inside the capacity.
        unsafe { ptr.at(i).write(f(i)) }
    });
    // SAFETY: every element below `n` has been written.
    unsafe { out.set_len(n) };
    out
}

/// A pointer into a buffer whose disjoint parts go to different tasks.
struct Parts<T>(*mut T);

impl<T> Parts<T> {
    fn at(&self, i: usize) -> *mut T {
        // SAFETY: callers stay inside the buffer.
        unsafe { self.0.add(i) }
    }
}

// SAFETY: tasks only touch disjoint elements through it.
unsafe impl<T: Send> Sync for Parts<T> {}

fn pool() -> &'static Pool {
    static POOL: OnceLock<Pool> = OnceLock::new();
    POOL.get_or_init(|| Pool::new(rayon::current_num_threads()))
}

/// The job word: epoch (32 bits), task count (16) and next task (16). One
/// word, so that a claim can only succeed for the job it was read from.
struct State;

impl State {
    fn pack(epoch: u32, tasks: usize, next: usize) -> u64 {
        (epoch as u64) << 32 | (tasks as u64) << 16 | next as u64
    }

    fn epoch(s: u64) -> u32 {
        (s >> 32) as u32
    }

    fn tasks(s: u64) -> usize {
        (s >> 16) as usize & 0xFFFF
    }

    fn next(s: u64) -> usize {
        s as usize & 0xFFFF
    }
}

struct Pool {
    shared: &'static Shared,
    threads: usize,
}

struct Shared {
    state: AtomicU64,
    /// The current job, valid while any of its tasks is unfinished.
    job: UnsafeCell<*const (dyn Fn(usize) + Sync)>,
    finished: AtomicUsize,
    busy: AtomicBool,
    panicked: AtomicBool,
    parked: AtomicUsize,
    lock: Mutex<()>,
    wake: Condvar,
}

// SAFETY: `job` is written only by the thread holding `busy`, while no task
// of an earlier job can still read it, and read only after a successful
// claim, which orders the read after the write (see `Pool::run`).
unsafe impl Sync for Shared {}
unsafe impl Send for Shared {}

impl Pool {
    fn new(threads: usize) -> Pool {
        let shared: &'static Shared = Box::leak(Box::new(Shared {
            state: AtomicU64::new(0),
            job: UnsafeCell::new(&(|_| {}) as &(dyn Fn(usize) + Sync)),
            finished: AtomicUsize::new(0),
            busy: AtomicBool::new(false),
            panicked: AtomicBool::new(false),
            parked: AtomicUsize::new(0),
            lock: Mutex::new(()),
            wake: Condvar::new(),
        }));
        for i in 1..threads {
            thread::Builder::new()
                .name(format!("kinetic-{i}"))
                .spawn(move || shared.work())
                .expect("spawn a pool thread");
        }
        Pool { shared, threads }
    }

    fn run(&self, tasks: usize, f: &(dyn Fn(usize) + Sync)) {
        let s = self.shared;
        if self.threads < 2 || s.busy.swap(true, Ordering::Acquire) {
            use rayon::prelude::*;
            (0..tasks).into_par_iter().for_each(f);
            return;
        }
        // SAFETY: the lifetime is erased only for the duration of this call,
        // which returns after every task, the last reader of `job`, is done.
        let f: *const (dyn Fn(usize) + Sync) = unsafe { std::mem::transmute(f) };
        // SAFETY: every task of the previous job has finished, so no thread
        // reads `job` until the release store of the new state below.
        unsafe { *s.job.get() = f };
        s.finished.store(0, Ordering::Relaxed);
        let epoch = State::epoch(s.state.load(Ordering::Relaxed)).wrapping_add(1);
        s.state
            .store(State::pack(epoch, tasks, 0), Ordering::SeqCst);
        if s.parked.load(Ordering::SeqCst) > 0 {
            let _guard = s.lock.lock().unwrap_or_else(|e| e.into_inner());
            s.wake.notify_all();
        }
        s.help(epoch);
        let mut spins = 0u32;
        while s.finished.load(Ordering::Acquire) < tasks {
            spin(&mut spins);
        }
        let panicked = s.panicked.swap(false, Ordering::Relaxed);
        s.busy.store(false, Ordering::Release);
        assert!(!panicked, "a parallel task panicked");
    }
}

/// One step of a busy wait. Now and then the core is offered to other
/// threads, so that a preempted worker holding a task gets it back soon on
/// a machine busy with other work.
fn spin(spins: &mut u32) {
    *spins = spins.wrapping_add(1);
    if spins.is_multiple_of(YIELD_EVERY) {
        thread::yield_now();
    } else {
        std::hint::spin_loop();
    }
}

impl Shared {
    /// Runs tasks of job `epoch` until none is left.
    fn help(&self, epoch: u32) {
        let mut s = self.state.load(Ordering::Acquire);
        loop {
            if State::epoch(s) != epoch || State::next(s) >= State::tasks(s) {
                return;
            }
            let claimed = State::pack(epoch, State::tasks(s), State::next(s) + 1);
            match self
                .state
                .compare_exchange_weak(s, claimed, Ordering::AcqRel, Ordering::Acquire)
            {
                Ok(_) => {
                    // SAFETY: the claim succeeded for `epoch`, whose job
                    // stays valid until this task counts as finished.
                    let f = unsafe { &**self.job.get() };
                    // A panic must not leave the job unfinished: the thread
                    // that started it waits for every task.
                    if panic::catch_unwind(AssertUnwindSafe(|| f(State::next(s)))).is_err() {
                        self.panicked.store(true, Ordering::Relaxed);
                    }
                    self.finished.fetch_add(1, Ordering::Release);
                    s = self.state.load(Ordering::Acquire);
                }
                Err(now) => s = now,
            }
        }
    }

    fn work(&self) {
        let mut seen = State::epoch(self.state.load(Ordering::Acquire));
        loop {
            let idle = Instant::now();
            let mut spins = 0u32;
            let epoch = loop {
                let epoch = State::epoch(self.state.load(Ordering::Acquire));
                if epoch != seen {
                    break epoch;
                }
                spin(&mut spins);
                if spins.is_multiple_of(YIELD_EVERY) && idle.elapsed() > SPIN {
                    self.park(seen);
                }
            };
            seen = epoch;
            self.help(epoch);
        }
    }

    /// Sleeps until a job after `seen` starts.
    fn park(&self, seen: u32) {
        let mut guard = self.lock.lock().unwrap_or_else(|e| e.into_inner());
        self.parked.fetch_add(1, Ordering::SeqCst);
        while State::epoch(self.state.load(Ordering::SeqCst)) == seen {
            guard = self.wake.wait(guard).unwrap_or_else(|e| e.into_inner());
        }
        self.parked.fetch_sub(1, Ordering::SeqCst);
    }
}

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicUsize, Ordering};

    use super::*;

    #[test]
    fn every_task_runs_once() {
        for tasks in [0, 1, 2, 7, 100, 1000, 70_000] {
            let counts: Vec<AtomicUsize> = (0..tasks).map(|_| AtomicUsize::new(0)).collect();
            for _ in 0..50 {
                for_each(tasks, &|i| {
                    counts[i].fetch_add(1, Ordering::Relaxed);
                });
            }
            assert!(counts.iter().all(|c| c.load(Ordering::Relaxed) == 50));
        }
    }

    #[test]
    fn nested_and_concurrent_jobs_finish() {
        let total = AtomicUsize::new(0);
        thread::scope(|scope| {
            for _ in 0..4 {
                scope.spawn(|| {
                    for _ in 0..20 {
                        for_each(8, &|_| {
                            for_each(3, &|_| {
                                total.fetch_add(1, Ordering::Relaxed);
                            });
                        });
                    }
                });
            }
        });
        assert_eq!(total.load(Ordering::Relaxed), 4 * 20 * 8 * 3);
    }

    #[test]
    fn chunks_and_maps_cover_everything() {
        let mut a = vec![0usize; 103];
        for_each_chunk(&mut a, 10, |i, c| c.iter_mut().for_each(|v| *v += i + 1));
        assert!(a.iter().enumerate().all(|(j, &v)| v == j / 10 + 1));
        let mut b = vec![0usize; 12];
        for_each_chunk_pair(&mut a[..100], 25, &mut b, 3, |i, a, b| {
            b.fill(a.len() + i);
        });
        assert_eq!(b, [25, 25, 25, 26, 26, 26, 27, 27, 27, 28, 28, 28]);
        assert_eq!(
            map(1000, |i| i * 2),
            (0..1000).map(|i| i * 2).collect::<Vec<_>>()
        );
    }

    #[test]
    fn a_panicking_task_fails_the_job_and_the_pool_carries_on() {
        let job = panic::catch_unwind(|| for_each(16, &|i| assert_ne!(i, 7)));
        assert!(job.is_err());
        let total = AtomicUsize::new(0);
        for_each(16, &|_| {
            total.fetch_add(1, Ordering::Relaxed);
        });
        assert_eq!(total.load(Ordering::Relaxed), 16);
    }

    #[test]
    fn workers_wake_after_parking() {
        let total = AtomicUsize::new(0);
        for _ in 0..3 {
            for_each(64, &|_| {
                total.fetch_add(1, Ordering::Relaxed);
            });
            thread::sleep(SPIN * 3);
        }
        assert_eq!(total.load(Ordering::Relaxed), 3 * 64);
    }
}
