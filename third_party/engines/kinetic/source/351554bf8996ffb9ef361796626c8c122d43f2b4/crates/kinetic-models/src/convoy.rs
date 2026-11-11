//! Passes that several sequences share.
//!
//! Every sequence that runs at once calls [`Convoy::run`] from its own
//! thread with the work of its next pass. The calls gather until every
//! sequence holding a [`Seat`] has one waiting, or until the first has
//! waited [`GATHER`], and then the last caller runs all of them as one pass
//! over the weights while the others wait for their results. A sequence
//! joins by taking a seat and leaves by dropping it, so requests come and
//! go between passes.
//!
//! A convoy can also hold a device that only one thread may drive at a
//! time. A seat then holds the device too, except while its sequence waits
//! for a pass or steps [`Seat::away`], so seated threads take turns on it
//! and the one that starts a pass drives it for everyone.

use std::panic::{self, AssertUnwindSafe};
use std::sync::{Condvar, Mutex, MutexGuard, PoisonError};
use std::thread::{self, ThreadId};
use std::time::{Duration, Instant};

/// Longest a pass waits for seated sequences that are busy elsewhere, such
/// as one writing to a slow client.
const GATHER: Duration = Duration::from_millis(5);

/// Gathers the work of concurrent callers into shared passes.
pub(crate) struct Convoy<J, R> {
    queue: Mutex<Queue<J, R>>,
    turn: Condvar,
    /// Whether seats and passes hold the device.
    device: bool,
}

struct Queue<J, R> {
    seats: usize,
    next: u64,
    waiting: Vec<(u64, J)>,
    /// When the oldest call in `waiting` began to wait for a pass.
    since: Option<Instant>,
    /// Results not yet collected; `None` for jobs of a pass that panicked.
    done: Vec<(u64, Option<R>)>,
    running: bool,
    /// The thread driving the device.
    holder: Option<ThreadId>,
}

/// A sequence's place in the passes of a model: they wait for its work
/// while it is held.
pub struct Seat<'c> {
    convoy: &'c dyn Turns,
}

trait Turns {
    fn leave(&self);
    fn release(&self);
    fn take(&self);
}

impl Seat<'_> {
    /// Runs `f` without holding the device, as for work that may block,
    /// such as handing tokens to a client.
    pub fn away<T>(&self, f: impl FnOnce() -> T) -> T {
        self.convoy.release();
        let out = f();
        self.convoy.take();
        out
    }
}

impl Drop for Seat<'_> {
    fn drop(&mut self) {
        self.convoy.leave();
    }
}

impl<J, R> Default for Convoy<J, R> {
    fn default() -> Self {
        Convoy {
            queue: Mutex::new(Queue {
                seats: 0,
                next: 0,
                waiting: Vec::new(),
                since: None,
                done: Vec::new(),
                running: false,
                holder: None,
            }),
            turn: Condvar::new(),
            device: false,
        }
    }
}

impl<J, R> Turns for Convoy<J, R> {
    fn leave(&self) {
        let mut q = self.lock();
        q.seats -= 1;
        Self::let_go(&mut q);
        drop(q);
        self.turn.notify_all();
    }

    fn release(&self) {
        Self::let_go(&mut self.lock());
        self.turn.notify_all();
    }

    fn take(&self) {
        let q = self.lock();
        drop(self.hold(q));
    }
}

impl<J, R> Convoy<J, R> {
    fn lock(&self) -> MutexGuard<'_, Queue<J, R>> {
        self.queue.lock().unwrap_or_else(PoisonError::into_inner)
    }

    /// A convoy whose seats and passes hold a device.
    #[cfg(any(test, feature = "cuda"))]
    pub fn for_device() -> Self {
        Convoy {
            device: true,
            ..Convoy::default()
        }
    }

    /// A seat for one more sequence; on a device, once the device is free.
    pub fn seat(&self) -> Seat<'_> {
        let mut q = self.hold(self.lock());
        q.seats += 1;
        Seat { convoy: self }
    }

    /// Seats held now.
    #[cfg(feature = "cuda")]
    pub fn seats(&self) -> usize {
        self.lock().seats
    }

    /// Waits until this thread may drive the device and takes it.
    fn hold<'q>(&self, mut q: MutexGuard<'q, Queue<J, R>>) -> MutexGuard<'q, Queue<J, R>> {
        if !self.device {
            return q;
        }
        let me = thread::current().id();
        while q.holder.is_some_and(|h| h != me) {
            q = self.turn.wait(q).unwrap_or_else(PoisonError::into_inner);
        }
        q.holder = Some(me);
        q
    }

    fn let_go(q: &mut Queue<J, R>) {
        if q.holder == Some(thread::current().id()) {
            q.holder = None;
        }
    }

    /// Runs `job` in the next pass and returns its result. The caller that
    /// starts a pass runs `pass` on the jobs of everyone in it, in the order
    /// they arrived, and must give one result per job back.
    pub fn run(&self, job: J, pass: impl FnOnce(Vec<J>) -> Vec<R>) -> R {
        let me = thread::current().id();
        let mut q = self.lock();
        // seated callers hold the device and get it back with their result
        let seated = q.holder == Some(me);
        let id = q.next;
        q.next += 1;
        q.waiting.push((id, job));
        q.since.get_or_insert_with(Instant::now);
        loop {
            if let Some(i) = q.done.iter().position(|d| d.0 == id) {
                let (_, result) = q.done.swap_remove(i);
                if seated {
                    q = self.hold(q);
                }
                drop(q);
                return result.expect("a shared pass failed");
            }
            let waited = q.since.map_or(Duration::ZERO, |t| t.elapsed());
            let free = q.holder.is_none_or(|h| h == me);
            if !q.running && free && (q.waiting.len() >= q.seats || waited >= GATHER) {
                break;
            }
            if self.device {
                Self::let_go(&mut q);
                self.turn.notify_all();
            }
            // past GATHER only a pass ending or the device coming free lets us on
            let left = GATHER.saturating_sub(waited);
            q = if q.running || left.is_zero() {
                self.turn.wait(q).unwrap_or_else(PoisonError::into_inner)
            } else {
                let (q, _) = self
                    .turn
                    .wait_timeout(q, left)
                    .unwrap_or_else(PoisonError::into_inner);
                q
            };
        }

        q.running = true;
        q.since = None;
        if self.device {
            q.holder = Some(me);
        }
        let (ids, jobs): (Vec<u64>, Vec<J>) = std::mem::take(&mut q.waiting).into_iter().unzip();
        drop(q);
        let results = panic::catch_unwind(AssertUnwindSafe(|| pass(jobs)));
        let mut q = self.lock();
        q.running = false;
        if !seated {
            Self::let_go(&mut q);
        }
        if !q.waiting.is_empty() {
            q.since = Some(Instant::now());
        }
        let mut mine = None;
        let outcome = match results {
            Ok(results) => {
                assert_eq!(results.len(), ids.len(), "one result per job");
                for (i, r) in ids.into_iter().zip(results) {
                    match i == id {
                        true => mine = Some(r),
                        false => q.done.push((i, Some(r))),
                    }
                }
                Ok(())
            }
            Err(payload) => {
                q.done.extend(ids.into_iter().map(|i| (i, None)));
                Err(payload)
            }
        };
        drop(q);
        self.turn.notify_all();
        if let Err(payload) = outcome {
            panic::resume_unwind(payload);
        }
        mine.expect("the caller's job ran")
    }
}

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Barrier;

    use super::Convoy;

    #[test]
    fn seated_callers_share_passes_and_get_their_own_results() {
        let convoy = Convoy::<usize, usize>::default();
        let passes = AtomicUsize::new(0);
        let widest = AtomicUsize::new(0);
        let seated = Barrier::new(4);
        std::thread::scope(|s| {
            for caller in 0..4 {
                let (convoy, passes, widest, seated) = (&convoy, &passes, &widest, &seated);
                s.spawn(move || {
                    let _seat = convoy.seat();
                    seated.wait();
                    for step in 0..50 {
                        let job = caller * 1000 + step;
                        let got = convoy.run(job, |jobs| {
                            passes.fetch_add(1, Ordering::Relaxed);
                            widest.fetch_max(jobs.len(), Ordering::Relaxed);
                            jobs.iter().map(|j| j * 2).collect()
                        });
                        assert_eq!(got, job * 2);
                    }
                });
            }
        });
        assert_eq!(widest.load(Ordering::Relaxed), 4);
        assert!(passes.load(Ordering::Relaxed) < 200);
    }

    #[test]
    fn seats_on_a_device_take_turns_and_still_share_passes() {
        let convoy = Convoy::<usize, usize>::for_device();
        let inside = AtomicUsize::new(0);
        let widest = AtomicUsize::new(0);
        let alone = |inside: &AtomicUsize| {
            assert_eq!(
                inside.fetch_add(1, Ordering::SeqCst),
                0,
                "two threads on the device"
            );
            std::thread::yield_now();
            inside.fetch_sub(1, Ordering::SeqCst);
        };
        // sharing passes depends on scheduling, so a busy runner gets a few
        // rounds before the test calls it a failure
        for _ in 0..50 {
            if widest.load(Ordering::Relaxed) > 1 {
                break;
            }
            std::thread::scope(|s| {
                for caller in 0..4 {
                    let (convoy, inside, widest) = (&convoy, &inside, &widest);
                    s.spawn(move || {
                        let seat = convoy.seat();
                        for step in 0..30 {
                            alone(inside);
                            let job = caller * 1000 + step;
                            let got = convoy.run(job, |jobs| {
                                alone(inside);
                                widest.fetch_max(jobs.len(), Ordering::Relaxed);
                                jobs.iter().map(|j| j + 1).collect()
                            });
                            assert_eq!(got, job + 1);
                            seat.away(std::thread::yield_now);
                        }
                    });
                }
            });
        }
        assert!(widest.load(Ordering::Relaxed) > 1);
    }

    #[test]
    fn a_failed_pass_fails_every_job_in_it() {
        let convoy = Convoy::<usize, usize>::default();
        let r = std::panic::catch_unwind(|| convoy.run(1, |_| panic!("device lost")));
        assert!(r.is_err());
        assert_eq!(convoy.run(2, |jobs| jobs), 2);
    }
}
