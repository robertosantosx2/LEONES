//! Device layout of weight matrices.
//!
//! Blocks whose size is not a multiple of 16 bytes (Q6_K, Q8_0 and the
//! formats below Q4_K) would rule out 128-bit loads. On the device their
//! fields are stored planar instead: each field of every block in turn,
//! quants first, so every plane starts aligned. The codebook formats then
//! append their codebook at the next multiple of 16 bytes.

use std::borrow::Cow;

use kinetic_quant::grids::{IQ1S_GRID, IQ2S_GRID, IQ3S_GRID};
use kinetic_quant::{Matrix, TensorType};

/// (offset, length) of each field in a block, in plane order.
const Q6_K_FIELDS: &[(usize, usize)] = &[(0, 128), (128, 64), (192, 16), (208, 2)];
const Q8_0_FIELDS: &[(usize, usize)] = &[(2, 32), (0, 2)];
const Q4_0_FIELDS: &[(usize, usize)] = &[(2, 16), (0, 2)];
const Q4_1_FIELDS: &[(usize, usize)] = &[(4, 16), (0, 4)];
const Q5_0_FIELDS: &[(usize, usize)] = &[(6, 16), (2, 4), (0, 2)];
const Q5_1_FIELDS: &[(usize, usize)] = &[(8, 16), (4, 4), (0, 4)];
const IQ4_NL_FIELDS: &[(usize, usize)] = &[(2, 16), (0, 2)];
const MXFP4_FIELDS: &[(usize, usize)] = &[(1, 16), (0, 1)];
const Q2_K_FIELDS: &[(usize, usize)] = &[(16, 64), (0, 16), (80, 4)];
const Q3_K_FIELDS: &[(usize, usize)] = &[(32, 64), (0, 32), (96, 12), (108, 2)];
const IQ3_S_FIELDS: &[(usize, usize)] = &[(2, 64), (66, 8), (74, 32), (106, 4), (0, 2)];
const IQ2_S_FIELDS: &[(usize, usize)] = &[(2, 32), (34, 32), (66, 8), (74, 8), (0, 2)];
const IQ1_S_FIELDS: &[(usize, usize)] = &[(2, 32), (34, 16), (0, 2)];
const IQ1_M_FIELDS: &[(usize, usize)] = &[(0, 32), (32, 16), (48, 8)];
const TQ1_0_FIELDS: &[(usize, usize)] = &[(0, 48), (48, 4), (52, 2)];
const TQ2_0_FIELDS: &[(usize, usize)] = &[(0, 64), (64, 2)];
const PQ2_0_FIELDS: &[(usize, usize)] = &[(2, 32), (0, 2)];

/// The bytes of `m` as the GEMV kernels expect them.
pub(crate) fn device_layout<'a>(m: &Matrix<'a>) -> Cow<'a, [u8]> {
    let fields = match m.ty {
        TensorType::Q6K => Q6_K_FIELDS,
        TensorType::Q8_0 => Q8_0_FIELDS,
        TensorType::Q4_0 => Q4_0_FIELDS,
        TensorType::Q4_1 => Q4_1_FIELDS,
        TensorType::Q5_0 => Q5_0_FIELDS,
        TensorType::Q5_1 => Q5_1_FIELDS,
        TensorType::IQ4NL => IQ4_NL_FIELDS,
        TensorType::MXFP4 => MXFP4_FIELDS,
        TensorType::Q2K => Q2_K_FIELDS,
        TensorType::Q3K => Q3_K_FIELDS,
        TensorType::IQ3S => IQ3_S_FIELDS,
        TensorType::IQ2S => IQ2_S_FIELDS,
        TensorType::IQ1S => IQ1_S_FIELDS,
        TensorType::IQ1M => IQ1_M_FIELDS,
        TensorType::TQ1_0 => TQ1_0_FIELDS,
        TensorType::TQ2_0 => TQ2_0_FIELDS,
        TensorType::PQ2_0 => PQ2_0_FIELDS,
        _ => return Cow::Borrowed(m.data),
    };
    let mut out = planar(m.data, m.ty.block_bytes(), fields);
    if let Some(grid) = codebook(m.ty) {
        out.resize(out.len().next_multiple_of(16), 0);
        out.extend(grid);
    }
    Cow::Owned(out)
}

/// The codebook bytes the kernels of `ty` read after the blocks.
fn codebook(ty: TensorType) -> Option<Vec<u8>> {
    Some(match ty {
        TensorType::IQ3S => IQ3S_GRID.as_flattened().to_vec(),
        TensorType::IQ2S => IQ2S_GRID.as_flattened().to_vec(),
        TensorType::IQ1S | TensorType::IQ1M => {
            IQ1S_GRID.as_flattened().iter().map(|&v| v as u8).collect()
        }
        _ => return None,
    })
}

fn planar(data: &[u8], block_bytes: usize, fields: &[(usize, usize)]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len());
    for &(start, len) in fields {
        for block in data.chunks_exact(block_bytes) {
            out.extend_from_slice(&block[start..start + len]);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn q8_0_planes_hold_quants_then_scales() {
        let blocks: Vec<u8> = (0..68).collect();
        let m = Matrix::new(TensorType::Q8_0, &blocks, 1, 64);
        let out = device_layout(&m);
        let expected: Vec<u8> = (2..34).chain(36..68).chain([0, 1, 34, 35]).collect();
        assert_eq!(*out, expected[..]);
    }

    #[test]
    fn planes_hold_every_byte_once() {
        for ty in [
            TensorType::Q6K,
            TensorType::Q8_0,
            TensorType::Q4_0,
            TensorType::Q4_1,
            TensorType::Q5_0,
            TensorType::Q5_1,
            TensorType::IQ4NL,
            TensorType::MXFP4,
            TensorType::Q2K,
            TensorType::Q3K,
            TensorType::TQ1_0,
            TensorType::TQ2_0,
        ] {
            let size = ty.block_bytes();
            let blocks: Vec<u8> = (0..16 * size).map(|i| (i % size) as u8).collect();
            let m = Matrix::new(ty, &blocks, 1, 16 * ty.block_len());
            let out = device_layout(&m);
            let mut counts = vec![0; size];
            for &b in out.iter() {
                counts[b as usize] += 1;
            }
            assert!(counts.iter().all(|&c| c == 16), "{ty}");
        }
    }

    #[test]
    fn aligned_formats_are_borrowed() {
        let blocks = [0u8; 144];
        let m = Matrix::new(TensorType::Q4K, &blocks, 1, 256);
        assert!(matches!(device_layout(&m), Cow::Borrowed(_)));
    }
}
