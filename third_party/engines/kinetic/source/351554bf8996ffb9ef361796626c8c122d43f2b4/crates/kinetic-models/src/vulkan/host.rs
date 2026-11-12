//! Exact host copies of device states, in the form the CPU path keeps, so
//! the warm cache can store and restore them.

use std::cell::Cell;

use kinetic_vulkan::{ConvRing, KvCache};

use super::layer::{LayerState, VulkanLayer};
use super::{VulkanModel, VulkanState};
use crate::device_state::{
    narrow, past_to_ring, ring_to_past, slots_to_window, widen, window_to_slots,
};
use crate::model::Mark;
use crate::warm::Runner;
use crate::{Model, State};

type R<T> = kinetic_vulkan::Result<T>;

fn ring_past(ring: &ConvRing, pos: usize) -> R<Vec<f32>> {
    let slots = ring.save()?;
    Ok(ring_to_past(
        &slots,
        ring.slots(),
        ring.channels(),
        ring.taps(),
        pos,
    ))
}

fn load_ring(ring: &mut ConvRing, past: &[f32], pos: usize) -> R<()> {
    let slots = past_to_ring(past, ring.channels(), ring.taps(), pos, ring.slots());
    ring.load(&slots)
}

fn save_cache(c: &KvCache, window: Option<usize>, pos: usize) -> R<Vec<Vec<f32>>> {
    let Some(w) = window else {
        let (k, v) = c.save(0..pos)?;
        return Ok(vec![widen(&k), widen(&v)]);
    };
    let (k, v) = c.save(0..c.slots())?;
    let row = k.len() / c.slots();
    let host = |x: &[u16]| widen(&slots_to_window(x, row, w, pos));
    Ok(vec![host(&k), host(&v)])
}

fn load_cache(c: &mut KvCache, window: Option<usize>, pos: usize, k: &[f32], v: &[f32]) -> R<()> {
    let Some(w) = window else {
        return c.load(0, &narrow(k), &narrow(v));
    };
    let n = pos.min(w);
    if n == 0 {
        return Ok(());
    }
    let (slots, row) = (c.slots(), k.len() / n);
    let device = |x: &[f32]| window_to_slots(&narrow(x), row, slots, pos);
    c.load(0, &device(k), &device(v))
}

impl VulkanLayer {
    /// The state after `pos` tokens as the buffers of the CPU mixer state,
    /// in the order of `MixerState::buffers`.
    fn save(&self, state: &LayerState, pos: usize) -> R<Vec<Vec<f32>>> {
        match state {
            LayerState::Attention(c) => save_cache(c, self.window(), pos),
            LayerState::ShortConv(ring) => Ok(vec![ring_past(ring, pos)?]),
            LayerState::DeltaNet(s) => Ok(vec![s.save()?, ring_past(s.ring(), pos)?]),
        }
    }

    /// Fills `state` from buffers in the order [`VulkanLayer::save`] gives.
    fn load(&self, state: &mut LayerState, pos: usize, bufs: &[&[f32]]) -> R<()> {
        match state {
            LayerState::Attention(c) => load_cache(c, self.window(), pos, bufs[0], bufs[1]),
            LayerState::ShortConv(ring) => load_ring(ring, bufs[0], pos),
            LayerState::DeltaNet(s) => {
                s.load(bufs[0])?;
                load_ring(s.ring_mut(), bufs[1], pos)
            }
        }
    }
}

impl VulkanModel<'_> {
    /// The host form of `state`, which `model`, the model this one was
    /// uploaded from, runs on the CPU. It holds exactly the device values,
    /// so [`VulkanModel::device_state`] gives the same state back.
    pub fn host_state(&self, model: &Model, state: &VulkanState) -> R<State> {
        assert!(state.checkpoint.is_none(), "host copy inside a checkpoint");
        let mut host = model.new_state();
        host.pos = state.pos;
        let layers = self.layers.iter().zip(&state.layers).zip(&mut host.layers);
        for ((layer, s), hs) in layers {
            for (dst, src) in hs.buffers_mut().into_iter().zip(layer.save(s, state.pos)?) {
                *dst = src;
            }
        }
        host.marks = state.marks.clone();
        Ok(host)
    }

    /// A new device state holding `state`, the host form of one this model
    /// ran, as [`VulkanModel::host_state`] or the warm cache give it.
    pub fn device_state(&self, state: &State) -> R<VulkanState> {
        let mut dev = self.new_state()?;
        self.load_state(&mut dev, state)?;
        Ok(dev)
    }

    /// [`VulkanModel::device_state`] into the buffers of `dev`, a state of
    /// this model whose contents it replaces.
    pub fn load_state(&self, dev: &mut VulkanState, state: &State) -> R<()> {
        dev.pos = state.pos;
        dev.checkpoint = None;
        let layers = self.layers.iter().zip(&mut dev.layers).zip(&state.layers);
        for ((layer, s), hs) in layers {
            layer.load(s, state.pos, &hs.buffers())?;
        }
        dev.marks = state.marks.clone();
        Ok(())
    }

    /// Keeps host copies of the layers a truncation cannot cut back in
    /// place, as [`Model::mark`] does.
    fn mark(&self, model: &Model, state: &mut VulkanState) -> R<()> {
        if state.marks.last().is_some_and(|m| m.pos == state.pos) {
            return Ok(());
        }
        let mut layers = Vec::with_capacity(self.layers.len());
        let all = self.layers.iter().zip(&state.layers).zip(&model.layers);
        for ((layer, s), host) in all {
            layers.push(match host.mixer.needs_mark() {
                true => {
                    let mut hs = host.mixer.new_state();
                    for (dst, src) in hs.buffers_mut().into_iter().zip(layer.save(s, state.pos)?) {
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
pub struct VulkanRunner<'a, 'm> {
    pub gpu: &'a VulkanModel<'m>,
    pub model: &'a Model<'m>,
    pub spare: Cell<Option<VulkanState>>,
}

fn device<T>(r: R<T>) -> T {
    r.unwrap_or_else(|e| panic!("Vulkan: {e}"))
}

/// Panics on device failures, as [`Target`](crate::speculative::Target) does.
impl Runner for VulkanRunner<'_, '_> {
    type State = VulkanState;

    fn restore(&self, state: State) -> VulkanState {
        match self.spare.take() {
            Some(mut dev) => {
                device(self.gpu.load_state(&mut dev, &state));
                dev
            }
            None => device(self.gpu.device_state(&state)),
        }
    }

    fn len(&self, state: &VulkanState) -> usize {
        state.len()
    }

    fn forward(&self, state: &mut VulkanState, tokens: &[u32]) -> Vec<f32> {
        device(self.gpu.run(state, tokens, false)).logits
    }

    fn mark(&self, state: &mut VulkanState) {
        device(self.gpu.mark(self.model, state));
    }

    fn restore_rate(&self) -> f64 {
        // perf: staging copies, ~1 GB/s on the RTX 3060 Laptop; the cache
        // times its own restores after the first
        1.0 / 1e9
    }
}
