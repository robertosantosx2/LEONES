//! CPU kernels.
//!
//! [`matvec`] picks an integer SIMD kernel when the weight type has one, a
//! SIMD kernel on f32 activations for f16 and bf16 weights, and otherwise
//! falls back to dequantizing each row to f32, which is also the reference
//! the fast kernels are tested against.

mod fdot;
mod kdot;
mod kernel_input;
mod matmul;
mod ops;
pub mod pool;
mod q8;
mod q8k;

use kinetic_quant::{dequantize, Matrix};
use rayon::prelude::*;

pub use kernel_input::kernel_input;
pub use matmul::{matmul, matmul_many};
pub use ops::*;
pub use q8k::Q8K;

/// Rows handed to one rayon task by [`matvec_reference`].
const ROWS_PER_TASK: usize = 16;

/// `y = W x` for a quantized `W` of shape `y.len() x x.len()`.
pub fn matvec(w: &Matrix, x: &[f32], y: &mut [f32]) {
    assert_eq!(x.len(), w.cols);
    matmul(w, x, y);
}

/// `matvec` through f32 dequantization, exact with respect to
/// `kinetic_quant::dequantize`.
pub fn matvec_reference(w: &Matrix, x: &[f32], y: &mut [f32]) {
    assert_eq!(x.len(), w.cols);
    assert_eq!(y.len(), w.rows);
    y.par_chunks_mut(ROWS_PER_TASK).enumerate().for_each_init(
        || vec![0.0f32; w.cols],
        |row, (chunk, out)| {
            for (i, y) in out.iter_mut().enumerate() {
                dequantize(w.ty, w.row(chunk * ROWS_PER_TASK + i), row)
                    .expect("unsupported weight type");
                *y = dot(row, x);
            }
        },
    );
}

#[cfg(test)]
mod tests {
    use kinetic_quant::TensorType;

    use super::*;

    #[test]
    fn matmul_matches_matvec_per_row() {
        let (rows, cols, n) = (33, 256, 3);
        let dense: Vec<f32> = (0..rows * cols)
            .map(|i| ((i * 7) % 19) as f32 - 9.0)
            .collect();
        let bytes: Vec<u8> = dense.iter().flat_map(|v| v.to_le_bytes()).collect();
        let w = Matrix::new(TensorType::F32, &bytes, rows, cols);
        let x: Vec<f32> = (0..n * cols).map(|i| (i % 11) as f32 * 0.5).collect();
        let mut y = vec![0.0; n * rows];
        matmul(&w, &x, &mut y);
        for t in 0..n {
            let mut want = vec![0.0; rows];
            matvec(&w, &x[t * cols..][..cols], &mut want);
            assert_eq!(&y[t * rows..][..rows], &want[..]);
        }
    }

    #[test]
    fn matvec_matches_dense() {
        let (rows, cols) = (37, 64);
        let dense: Vec<f32> = (0..rows * cols).map(|i| (i % 13) as f32 - 6.0).collect();
        let bytes: Vec<u8> = dense.iter().flat_map(|v| v.to_le_bytes()).collect();
        let w = Matrix::new(TensorType::F32, &bytes, rows, cols);
        let x: Vec<f32> = (0..cols).map(|i| i as f32 * 0.25).collect();
        let mut y = vec![0.0; rows];
        matvec(&w, &x, &mut y);
        for (r, y) in y.iter().enumerate() {
            assert_eq!(*y, dot(&dense[r * cols..(r + 1) * cols], &x));
        }
    }
}
