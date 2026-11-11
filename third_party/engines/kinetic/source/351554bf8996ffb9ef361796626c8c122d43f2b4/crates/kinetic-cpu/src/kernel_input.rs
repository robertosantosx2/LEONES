//! The activation values the integer kernels multiply a matrix by.

use kinetic_quant::Matrix;

use crate::kdot;
use crate::q8::{Q8, QK};
use crate::q8k::{Q8K, QK_K};

/// `x`, rows of `w.cols` values, after the quantization
/// [`matmul`](crate::matmul) applies to it for `w`, each value exact as an
/// f64. `None` when `matmul` reads `x` unquantized.
pub fn kernel_input(w: &Matrix, x: &[f32]) -> Option<Vec<f64>> {
    let cols = w.cols;
    assert!(cols > 0 && x.len().is_multiple_of(cols));
    let rows = x.chunks_exact(cols);
    // The same choice of kernel as `matmul` makes.
    let values = if kdot::kernel(w.ty).is_some() && cols.is_multiple_of(QK_K) {
        rows.flat_map(|x| {
            let q = Q8K::quantize(x);
            exact(&q.d, &q.qs, QK_K)
        })
        .collect()
    } else if kdot::kernel32(w.ty).is_some() {
        rows.flat_map(|x| {
            let q = Q8::quantize(x);
            exact(&q.d, &q.qs, QK)
        })
        .collect()
    } else {
        return None;
    };
    Some(values)
}

/// Blocks of `block` values `qs` with one scale each, multiplied out.
fn exact(d: &[f32], qs: &[i8], block: usize) -> Vec<f64> {
    qs.iter()
        .enumerate()
        .map(|(i, &q)| d[i / block] as f64 * q as f64)
        .collect()
}

#[cfg(test)]
mod tests {
    use kinetic_quant::{dequantize, TensorType};

    use super::*;
    use crate::kdot::tests::{random_row, Lcg};
    use crate::matmul;

    /// A wrong quantization would be off by far more than f32 rounding.
    #[test]
    fn matmul_multiplies_by_these_values() {
        let (rows, cols) = (8, 512);
        let mut rng = Lcg(3);
        let x: Vec<f32> = (0..cols).map(|_| rng.f32() * 4.0).collect();
        for ty in [TensorType::Q6K, TensorType::Q4K, TensorType::Q8_0] {
            let data = random_row(ty, rows * cols / ty.block_len(), &mut rng);
            let w = Matrix::new(ty, &data, rows, cols);
            let input = kernel_input(&w, &x).unwrap();
            let mut got = vec![0.0; rows];
            matmul(&w, &x, &mut got);
            let mut row = vec![0.0; cols];
            for (r, got) in got.iter().enumerate() {
                dequantize(ty, w.row(r), &mut row).unwrap();
                let want: f64 = row.iter().zip(&input).map(|(&w, x)| w as f64 * x).sum();
                assert!(
                    (*got as f64 - want).abs() <= 1e-5 * want.abs().max(1.0),
                    "{ty}"
                );
            }
        }
        let f16 = vec![0u8; 2 * cols];
        assert!(kernel_input(&Matrix::new(TensorType::F16, &f16, 1, cols), &x).is_none());
    }
}
