//! Uploading projector weights to a CUDA device.

use std::rc::Rc;

use kinetic_cuda::{Context, DeviceMatrix};
use kinetic_quant::{dequantize, Matrix, TensorType};

use crate::Error;

pub fn cuda_error(e: kinetic_cuda::Error) -> Error {
    Error(format!("CUDA: {e}"))
}

pub fn to_f32(m: &Matrix) -> Result<Vec<f32>, Error> {
    let mut out = vec![0.0; m.rows * m.cols];
    dequantize(m.ty, m.data, &mut out).map_err(|e| Error(e.to_string()))?;
    Ok(out)
}

pub fn f16_matrix(
    ctx: &Rc<Context>,
    values: &[f32],
    rows: usize,
    cols: usize,
) -> Result<DeviceMatrix, Error> {
    let bytes: Vec<u8> = values
        .iter()
        .flat_map(|&v| half::f16::from_f32(v).to_le_bytes())
        .collect();
    DeviceMatrix::upload(ctx, &Matrix::new(TensorType::F16, &bytes, rows, cols)).map_err(cuda_error)
}

/// Uploads `m` as it is, or as f16 when the device kernels do not read its
/// type (bf16 projectors).
pub fn upload_matrix(ctx: &Rc<Context>, m: &Matrix) -> Result<DeviceMatrix, Error> {
    match DeviceMatrix::upload(ctx, m) {
        Err(kinetic_cuda::Error::Unsupported(_)) => f16_matrix(ctx, &to_f32(m)?, m.rows, m.cols),
        r => r.map_err(cuda_error),
    }
}
