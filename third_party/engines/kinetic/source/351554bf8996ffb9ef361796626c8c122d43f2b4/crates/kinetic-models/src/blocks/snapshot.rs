//! What exact copies of a sequence need from each mixer: its state as plain
//! buffers in a fixed order, and cutting attention caches back in place.

use super::{Mixer, MixerState};

impl MixerState {
    /// The buffers that make up the state, in a fixed order. An open
    /// checkpoint is not part of it.
    pub fn buffers(&self) -> Vec<&[f32]> {
        match self {
            MixerState::Attention(c) => vec![&c.k, &c.v],
            MixerState::DeltaNet(s) => vec![&s.s, &s.conv.past],
            MixerState::ShortConv(s) => vec![&s.window.past],
            MixerState::Mamba2(s) => vec![&s.s, &s.conv.past],
            MixerState::Parallel(s) => s.iter().flat_map(MixerState::buffers).collect(),
        }
    }

    /// The buffers of [`MixerState::buffers`], to fill in place.
    pub fn buffers_mut(&mut self) -> Vec<&mut Vec<f32>> {
        match self {
            MixerState::Attention(c) => vec![&mut c.k, &mut c.v],
            MixerState::DeltaNet(s) => vec![&mut s.s, &mut s.conv.past],
            MixerState::ShortConv(s) => vec![&mut s.window.past],
            MixerState::Mamba2(s) => vec![&mut s.s, &mut s.conv.past],
            MixerState::Parallel(s) => s.iter_mut().flat_map(MixerState::buffers_mut).collect(),
        }
    }
}

impl Mixer<'_> {
    /// The length of each buffer of a state after `pos` tokens, in the order
    /// of [`MixerState::buffers`].
    pub fn buffer_lens(&self, pos: usize) -> Vec<usize> {
        match self {
            Mixer::Attention(a) => {
                let rows = a.window.map_or(pos, |w| pos.min(w));
                vec![rows * a.n_head_kv * a.head_dim; 2]
            }
            Mixer::DeltaNet(d) => vec![
                d.n_v_heads * d.head_v_dim * d.head_k_dim,
                d.qkv.rows * (d.conv_taps - 1),
            ],
            Mixer::ShortConv(s) => vec![s.out_proj.cols * (s.taps - 1)],
            Mixer::Mamba2(m) => vec![
                m.n_head * m.head_dim * m.d_state,
                m.conv_bias.len() * (m.conv_taps - 1),
            ],
            Mixer::Parallel(ms) => ms.iter().flat_map(|m| m.buffer_lens(pos)).collect(),
        }
    }

    /// Whether a mark has to copy this mixer's state for a later truncation
    /// to return to it; a cache of every position can always be cut instead.
    pub fn needs_mark(&self) -> bool {
        match self {
            Mixer::Attention(a) => a.window.is_some(),
            Mixer::Parallel(ms) => ms.iter().any(Mixer::needs_mark),
            _ => true,
        }
    }

    /// Whether a state after `pos` tokens can be cut back to any shorter
    /// length in place: attention caches can, until a window ring starts
    /// overwriting old positions; recurrent states never can.
    pub fn truncates_in_place(&self, pos: usize) -> bool {
        match self {
            Mixer::Attention(a) => a.window.is_none_or(|w| pos <= w),
            Mixer::Parallel(ms) => ms.iter().all(|m| m.truncates_in_place(pos)),
            Mixer::DeltaNet(_) | Mixer::ShortConv(_) | Mixer::Mamba2(_) => false,
        }
    }

    /// Keeps the first `len` positions of an attention cache that
    /// [`Mixer::truncates_in_place`].
    pub fn truncate(&self, state: &mut MixerState, len: usize) {
        match (self, state) {
            (Mixer::Attention(a), MixerState::Attention(c)) => {
                let n = len * a.n_head_kv * a.head_dim;
                c.k.truncate(n);
                c.v.truncate(n);
            }
            (Mixer::Parallel(ms), MixerState::Parallel(ss)) => {
                ms.iter().zip(ss).for_each(|(m, s)| m.truncate(s, len))
            }
            _ => unreachable!("only attention caches truncate in place"),
        }
    }
}
