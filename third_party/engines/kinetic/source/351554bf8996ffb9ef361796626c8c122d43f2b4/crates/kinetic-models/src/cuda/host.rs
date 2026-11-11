//! Exact host copies of device states, in the form the CPU path keeps, so
//! the warm cache can store and restore them. Cached keys and values come
//! back as f32 and return unchanged; every other value is f32 already.

use std::cell::Cell;

use kinetic_cuda::{HostState, KvCache, Stream};

use super::layer::{CudaMixer, LayerState};
use super::{CudaModel, CudaState};
use crate::blocks::MixerState;
use crate::device_state::{past_to_ring, ring_to_past, slots_to_window, window_to_slots};
use crate::model::Mark;
use crate::warm::Runner;
use crate::{Model, State};

impl CudaMixer {
    /// The state after `pos` tokens as the buffers of the CPU mixer state,
    /// in the order of `MixerState::buffers`.
    fn save(&self, state: &LayerState, pos: usize) -> kinetic_cuda::Result<Vec<Vec<f32>>> {
        Ok(match (self, state) {
            (CudaMixer::Attention(a), LayerState::Attention(c)) => {
                let (k, v) = save_cache(c, a.window(), pos)?;
                vec![k, v]
            }
            (CudaMixer::DeltaNet(d), LayerState::DeltaNet(s)) => {
                recurrent(s.save()?, d.conv(), pos)
            }
            (CudaMixer::ShortConv(c), LayerState::ShortConv(s)) => {
                let (channels, taps) = c.conv();
                let host = s.save()?;
                vec![ring_to_past(
                    &host.ring,
                    host.ring_rows,
                    channels,
                    taps,
                    pos,
                )]
            }
            (CudaMixer::Mamba2(m), LayerState::Mamba2(s)) => recurrent(s.save()?, m.conv(), pos),
            (CudaMixer::Parallel(ms), LayerState::Parallel(ss)) => {
                let mut out = Vec::new();
                for (m, s) in ms.iter().zip(ss) {
                    out.extend(m.save(s, pos)?);
                }
                out
            }
            _ => unreachable!("state does not belong to this mixer"),
        })
    }

    /// Fills a fresh `state` from buffers in the order [`CudaMixer::save`]
    /// gives them, and returns the buffers it did not use.
    fn load<'b>(
        &self,
        state: &mut LayerState,
        pos: usize,
        bufs: &'b [&'b [f32]],
    ) -> kinetic_cuda::Result<&'b [&'b [f32]]> {
        let ring = |rows, (channels, taps), past| HostState {
            ring: past_to_ring(past, channels, taps, pos, rows),
            ring_rows: rows,
            state: Vec::new(),
        };
        match (self, state) {
            (CudaMixer::Attention(a), LayerState::Attention(c)) => {
                load_cache(c, a.window(), pos, bufs[0], bufs[1])?;
                Ok(&bufs[2..])
            }
            (CudaMixer::DeltaNet(d), LayerState::DeltaNet(s)) => {
                let host = ring(s.ring_rows(), d.conv(), bufs[1]);
                s.load(&HostState {
                    state: bufs[0].to_vec(),
                    ..host
                })?;
                Ok(&bufs[2..])
            }
            (CudaMixer::ShortConv(c), LayerState::ShortConv(s)) => {
                s.load(&ring(s.ring_rows(), c.conv(), bufs[0]))?;
                Ok(&bufs[1..])
            }
            (CudaMixer::Mamba2(m), LayerState::Mamba2(s)) => {
                let host = ring(s.ring_rows(), m.conv(), bufs[1]);
                s.load(&HostState {
                    state: bufs[0].to_vec(),
                    ..host
                })?;
                Ok(&bufs[2..])
            }
            (CudaMixer::Parallel(ms), LayerState::Parallel(ss)) => {
                let mut rest = bufs;
                for (m, s) in ms.iter().zip(ss) {
                    rest = m.load(s, pos, rest)?;
                }
                Ok(rest)
            }
            _ => unreachable!("state does not belong to this mixer"),
        }
    }
}

/// The CPU buffers of a recurrent state: the state, then the window.
fn recurrent(host: HostState, (channels, taps): (usize, usize), pos: usize) -> Vec<Vec<f32>> {
    let past = ring_to_past(&host.ring, host.ring_rows, channels, taps, pos);
    vec![host.state, past]
}

/// The CPU layout of a cache after `pos` tokens: every position in order,
/// or for a window the last `w` of them at index `p % w`.
fn save_cache(
    c: &KvCache,
    window: Option<usize>,
    pos: usize,
) -> kinetic_cuda::Result<(Vec<f32>, Vec<f32>)> {
    let Some(w) = window else {
        return c.save(0..pos);
    };
    let slots = c.slots();
    let (k, v) = c.save(0..slots)?;
    let kv_dim = k.len() / slots;
    let host = |x: &[f32]| slots_to_window(x, kv_dim, w, pos);
    Ok((host(&k), host(&v)))
}

/// Writes a cache in the layout of [`save_cache`] back to the device.
fn load_cache(
    c: &mut KvCache,
    window: Option<usize>,
    pos: usize,
    k: &[f32],
    v: &[f32],
) -> kinetic_cuda::Result<()> {
    let Some(w) = window else {
        return c.load(0, k, v);
    };
    let n = pos.min(w);
    if n == 0 {
        return Ok(());
    }
    let (slots, kv_dim) = (c.slots(), k.len() / n);
    let device = |x: &[f32]| window_to_slots(x, kv_dim, slots, pos);
    c.load(0, &device(k), &device(v))
}

/// Zeroes a recurrent layer's state; caches simply start over.
pub(super) fn clear_layer(state: &mut LayerState, stream: &Stream) -> kinetic_cuda::Result<()> {
    match state {
        LayerState::Attention(_) => Ok(()),
        LayerState::DeltaNet(s) => s.clear(stream),
        LayerState::ShortConv(s) => s.clear(stream),
        LayerState::Mamba2(s) => s.clear(stream),
        LayerState::Parallel(ss) => ss.iter_mut().try_for_each(|s| clear_layer(s, stream)),
    }
}

impl CudaModel<'_> {
    /// The host form of `state`, which `model`, the model this one was
    /// uploaded from, runs on the CPU. It holds exactly the device values,
    /// so [`CudaModel::device_state`] gives the same state back.
    pub fn host_state(&self, model: &Model, state: &CudaState) -> kinetic_cuda::Result<State> {
        assert!(state.checkpoint.is_none(), "host copy inside a checkpoint");
        let mut host = model.new_state();
        host.pos = state.pos;
        host.layers[..self.front].clone_from_slice(&state.work.front);
        for ((layer, ls), hs) in self
            .layers
            .iter()
            .zip(&state.work.layers)
            .zip(&mut host.layers[self.front..])
        {
            let bufs = layer.mixer.save(ls, state.pos)?;
            for (dst, src) in hs.buffers_mut().into_iter().zip(bufs) {
                *dst = src;
            }
        }
        host.marks = state.marks.clone();
        Ok(host)
    }

    /// A new device state holding `state`, the host form of one this model
    /// ran, as [`CudaModel::host_state`] or the warm cache give it.
    pub fn device_state(&self, state: &State) -> kinetic_cuda::Result<CudaState> {
        let mut dev = self.new_state()?;
        self.load_state(&mut dev, state)?;
        Ok(dev)
    }

    /// [`CudaModel::device_state`] into the buffers of `dev`, a state of
    /// this model whose contents it replaces, which saves allocating them.
    pub fn load_state(&self, dev: &mut CudaState, state: &State) -> kinetic_cuda::Result<()> {
        if state.pos == 0 {
            return self.reset_state(dev);
        }
        dev.pos = state.pos;
        dev.checkpoint = None;
        dev.work.front = state.layers[..self.front].to_vec();
        for ((layer, ls), hs) in self
            .layers
            .iter()
            .zip(&mut dev.work.layers)
            .zip(&state.layers[self.front..])
        {
            layer.mixer.load(ls, state.pos, &hs.buffers())?;
        }
        dev.marks = state.marks.clone();
        Ok(())
    }

    /// Empties `dev`, a state of this model, for a new sequence in the same
    /// buffers: recurrent layers are zeroed on the device, caches simply
    /// start over.
    pub fn reset_state(&self, dev: &mut CudaState) -> kinetic_cuda::Result<()> {
        if dev.pos == 0 && dev.checkpoint.is_none() {
            return Ok(());
        }
        dev.pos = 0;
        dev.checkpoint = None;
        dev.marks.clear();
        dev.work.batch.set_grid_shift(0);
        let stream = &self.gpu.stream;
        dev.work
            .layers
            .iter_mut()
            .try_for_each(|s| clear_layer(s, stream))
    }

    /// Cuts `state` back to `len` tokens on the device as [`Model::truncate`]
    /// cuts a host state: to the length [`Model::reach`] gives, the layers
    /// that cannot cut back in place restored from the mark there. Returns
    /// the length reached.
    pub fn truncate(
        &self,
        model: &Model,
        state: &mut CudaState,
        len: usize,
    ) -> kinetic_cuda::Result<usize> {
        assert!(state.checkpoint.is_none(), "truncate inside a checkpoint");
        let len = len.min(state.pos);
        let in_place = model
            .layers
            .iter()
            .all(|l| l.mixer.truncates_in_place(state.pos));
        let to = match len == state.pos || in_place {
            true => len,
            false => state
                .marks
                .iter()
                .map(|m| m.pos)
                .filter(|&p| p <= len)
                .max()
                .unwrap_or(0),
        };
        if to == state.pos {
            return Ok(to);
        }
        if to == 0 {
            self.reset_state(state)?;
            return Ok(0);
        }
        let mark = state.marks.iter().position(|m| m.pos == to);
        let saved = |i: usize| mark.and_then(|m| state.marks[m].layers[i].as_ref());
        for (i, (host, ls)) in model.layers.iter().zip(&mut state.work.front).enumerate() {
            match saved(i) {
                Some(s) => *ls = s.clone(),
                None => host.mixer.truncate(ls, to),
            }
        }
        for (i, (layer, ls)) in self.layers.iter().zip(&mut state.work.layers).enumerate() {
            if let Some(s) = saved(self.front + i) {
                layer.mixer.load(ls, to, &s.buffers())?;
            }
        }
        state.marks.retain(|m| m.pos <= to);
        state.pos = to;
        Ok(to)
    }

    /// Keeps host copies of the layers a truncation cannot cut back in
    /// place, as [`Model::mark`] does.
    fn mark(&self, model: &Model, state: &mut CudaState) -> kinetic_cuda::Result<()> {
        if state.marks.last().is_some_and(|m| m.pos == state.pos) {
            return Ok(());
        }
        let mut layers: Vec<Option<MixerState>> = model.layers[..self.front]
            .iter()
            .zip(&state.work.front)
            .map(|(host, ls)| host.mixer.needs_mark().then(|| ls.clone()))
            .collect();
        for ((layer, ls), host) in self
            .layers
            .iter()
            .zip(&state.work.layers)
            .zip(&model.layers[self.front..])
        {
            layers.push(match host.mixer.needs_mark() {
                true => {
                    let mut hs = host.mixer.new_state();
                    let bufs = layer.mixer.save(ls, state.pos)?;
                    for (dst, src) in hs.buffers_mut().into_iter().zip(bufs) {
                        *dst = src;
                    }
                    Some(hs)
                }
                false => None,
            });
        }
        state.marks.push(Mark {
            pos: state.pos,
            layers,
        });
        Ok(())
    }
}

/// Runs the uncached part of warm prefills on the device: `gpu`, uploaded
/// from `model`. The first state restored reuses the buffers of `spare`.
pub struct CudaRunner<'a, 'm> {
    pub gpu: &'a CudaModel<'m>,
    pub model: &'a Model<'m>,
    pub spare: Cell<Option<CudaState>>,
}

fn device<T>(r: kinetic_cuda::Result<T>) -> T {
    r.unwrap_or_else(|e| panic!("CUDA: {e}"))
}

/// Panics on device failures, as [`Target`](crate::speculative::Target) does.
impl Runner for CudaRunner<'_, '_> {
    type State = CudaState;

    fn restore(&self, state: State) -> CudaState {
        match self.spare.take() {
            Some(mut dev) => {
                device(self.gpu.load_state(&mut dev, &state));
                dev
            }
            None => device(self.gpu.device_state(&state)),
        }
    }

    fn len(&self, state: &CudaState) -> usize {
        state.len()
    }

    fn forward(&self, state: &mut CudaState, tokens: &[u32]) -> Vec<f32> {
        device(self.gpu.run(state, tokens, false)).logits
    }

    fn mark(&self, state: &mut CudaState) {
        device(self.gpu.mark(self.model, state));
    }

    fn restore_rate(&self) -> f64 {
        // Narrowing keys and values and copying over PCIe, as measured on
        // an RTX 3060 Laptop; the cache then times its own restores.
        1.0 / 1.5e9
    }
}
