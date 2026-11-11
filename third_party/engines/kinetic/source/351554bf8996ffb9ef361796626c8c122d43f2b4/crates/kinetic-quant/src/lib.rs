//! Tensor storage types, scalar reference dequantization and quantization.
//!
//! The functions here define what each block format means. Fast CPU and GPU
//! kernels are tested against them.

mod dequant;
mod encode;
pub mod grids;
pub mod iq;
mod matrix;
mod types;

pub use dequant::{
    dequantize, dequantize_row, iq1_m_group_scale, iq1_m_scale, iq2_s_index, iq3_s_index,
    ptq1_0_position, q3_k_scales, tq1_0_position, trit, two_bit_code, UnsupportedType,
};
pub use encode::{quantize, QUANTIZABLE};
pub use matrix::Matrix;
pub use types::TensorType;
