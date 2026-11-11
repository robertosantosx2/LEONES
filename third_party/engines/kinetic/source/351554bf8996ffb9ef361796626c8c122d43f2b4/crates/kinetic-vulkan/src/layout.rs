//! Device layout of weight matrices.
//!
//! Q6_K (210-byte) and Q8_0 (34-byte) blocks are not 16-byte aligned, so
//! kernels could not read them as 16-byte words. On the device their
//! fields are stored planar instead: each field of every block in turn, so
//! every plane starts aligned. The byte count does not change.

use std::borrow::Cow;

use kinetic_quant::{Matrix, TensorType};

/// (offset, length) of each field in a block, in plane order.
const Q6_K_FIELDS: &[(usize, usize)] = &[(0, 128), (128, 64), (192, 16), (208, 2)];
const Q8_0_FIELDS: &[(usize, usize)] = &[(2, 32), (0, 2)];

/// The bytes of `m` as the GEMV kernels expect them.
pub(crate) fn device_layout<'a>(m: &Matrix<'a>) -> Cow<'a, [u8]> {
    let fields = match m.ty {
        TensorType::Q6K => Q6_K_FIELDS,
        TensorType::Q8_0 => Q8_0_FIELDS,
        _ => return Cow::Borrowed(m.data),
    };
    Cow::Owned(planar(m.data, m.ty.block_bytes(), fields))
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
    fn aligned_formats_are_borrowed() {
        let blocks = [0u8; 144];
        let m = Matrix::new(TensorType::Q4K, &blocks, 1, 256);
        assert!(matches!(device_layout(&m), Cow::Borrowed(_)));
    }
}
