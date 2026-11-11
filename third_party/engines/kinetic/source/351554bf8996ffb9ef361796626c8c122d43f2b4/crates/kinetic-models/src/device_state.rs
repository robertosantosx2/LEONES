//! Conversions between the state layouts GPUs keep and the CPU's, for the
//! warm cache. Every value comes back bit for bit.

#[cfg(feature = "vulkan")]
use half::f16;
#[cfg(feature = "vulkan")]
use half::slice::{HalfBitsSliceExt, HalfFloatSliceExt};

/// The last `taps - 1` inputs per channel before `pos`, oldest first and
/// zero before the start, from a ring that holds position `p` at row
/// `p % rows`.
pub(crate) fn ring_to_past(
    ring: &[f32],
    rows: usize,
    channels: usize,
    taps: usize,
    pos: usize,
) -> Vec<f32> {
    let len = taps - 1;
    let mut past = vec![0.0; channels * len];
    for i in 0..len {
        let Some(p) = (pos + i).checked_sub(len) else {
            continue;
        };
        let row = &ring[p % rows * channels..][..channels];
        for (ch, &x) in row.iter().enumerate() {
            past[ch * len + i] = x;
        }
    }
    past
}

/// The ring [`ring_to_past`] reads `past` from; rows of other positions
/// are zero, which is what a fresh ring holds before the start.
pub(crate) fn past_to_ring(
    past: &[f32],
    channels: usize,
    taps: usize,
    pos: usize,
    rows: usize,
) -> Vec<f32> {
    let len = taps - 1;
    let mut ring = vec![0.0; rows * channels];
    for i in 0..len {
        let Some(p) = (pos + i).checked_sub(len) else {
            continue;
        };
        let row = &mut ring[p % rows * channels..][..channels];
        for (ch, x) in row.iter_mut().enumerate() {
            *x = past[ch * len + i];
        }
    }
    ring
}

/// The positions a window of `window` keeps after `pos` tokens, at index
/// `p % window` as the CPU keeps them, from cache rows of `row` values that
/// hold position `p` at slot `p % slots`.
pub(crate) fn slots_to_window<T: Copy + Default>(
    slots: &[T],
    row: usize,
    window: usize,
    pos: usize,
) -> Vec<T> {
    let (n, count) = (pos.min(window), slots.len() / row);
    let mut out = vec![T::default(); n * row];
    for p in pos - n..pos {
        out[p % window * row..][..row].copy_from_slice(&slots[p % count * row..][..row]);
    }
    out
}

/// The `slots` cache rows [`slots_to_window`] reads `window` from.
/// The window holds `min(pos, window size)` positions, so that count works
/// as its modulus too.
pub(crate) fn window_to_slots<T: Copy + Default>(
    window: &[T],
    row: usize,
    slots: usize,
    pos: usize,
) -> Vec<T> {
    let mut out = vec![T::default(); slots * row];
    let n = window.len() / row.max(1);
    if n == 0 {
        return out;
    }
    for p in pos - n..pos {
        out[p % slots * row..][..row].copy_from_slice(&window[p % n * row..][..row]);
    }
    out
}

#[cfg(feature = "vulkan")]
pub(crate) fn widen(bits: &[u16]) -> Vec<f32> {
    let mut out = vec![0.0; bits.len()];
    bits.reinterpret_cast::<f16>()
        .convert_to_f32_slice(&mut out);
    out
}

#[cfg(feature = "vulkan")]
pub(crate) fn narrow(x: &[f32]) -> Vec<u16> {
    let mut out = vec![f16::ZERO; x.len()];
    out.convert_from_f32_slice(x);
    out.reinterpret_cast().to_vec()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn window_round_trips_through_slots() {
        let (row, window, slots, pos) = (2, 3, 5, 7);
        let ring: Vec<u16> = (0..(slots * row) as u16).collect();
        let host = slots_to_window(&ring, row, window, pos);
        let back = window_to_slots(&host, row, slots, pos);
        for p in pos - window..pos {
            assert_eq!(
                back[p % slots * row..][..row],
                ring[p % slots * row..][..row]
            );
        }
    }
}
