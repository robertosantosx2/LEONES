//! Reference quantization: floats to blocks, choosing codes as llama.cpp's
//! reference quantizers do, so files match llama-quantize's to the byte.

mod k;
mod legacy;

use crate::TensorType;

/// Types [`quantize`] writes.
pub const QUANTIZABLE: &[TensorType] = &[
    TensorType::Q4_0,
    TensorType::Q5_0,
    TensorType::Q5_1,
    TensorType::Q8_0,
    TensorType::Q4K,
    TensorType::Q5K,
    TensorType::Q6K,
];

/// Quantizes `src`, a whole number of `ty` blocks, into `dst`, which holds
/// exactly the bytes of those blocks; false for a type not in
/// [`QUANTIZABLE`].
pub fn quantize(ty: TensorType, src: &[f32], dst: &mut [u8]) -> bool {
    let block: fn(&[f32], &mut [u8]) = match ty {
        TensorType::Q4_0 => legacy::q4_0,
        TensorType::Q5_0 => legacy::q5_0,
        TensorType::Q5_1 => legacy::q5_1,
        TensorType::Q8_0 => legacy::q8_0,
        TensorType::Q4K => k::q4_k,
        TensorType::Q5K => k::q5_k,
        TensorType::Q6K => k::q6_k,
        _ => return false,
    };
    let (n, bytes) = (ty.block_len(), ty.block_bytes());
    assert_eq!(src.len() / n * bytes, dst.len(), "dst must fit src exactly");
    for (x, out) in src.chunks_exact(n).zip(dst.chunks_exact_mut(bytes)) {
        block(x, out);
    }
    true
}

fn f16(v: f32) -> [u8; 2] {
    half::f16::from_f32(v).to_bits().to_le_bytes()
}

fn f16_to_f32(b: [u8; 2]) -> f32 {
    half::f16::from_bits(u16::from_le_bytes(b)).to_f32()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dequantize;

    #[test]
    fn round_trips_stay_close() {
        let x: Vec<f32> = (0..1024)
            .map(|i| ((i * 7919 % 1000) as f32 / 500.0 - 1.0) * (1.0 + (i % 13) as f32))
            .collect();
        let rms = |e: &[f32]| (e.iter().map(|v| v * v).sum::<f32>() / e.len() as f32).sqrt();
        let scale = rms(&x);
        for (&ty, limit) in QUANTIZABLE
            .iter()
            .zip([0.12, 0.06, 0.06, 0.01, 0.08, 0.04, 0.02])
        {
            let mut q = vec![0u8; ty.bytes_for(1024).unwrap() as usize];
            assert!(quantize(ty, &x, &mut q));
            let mut back = vec![0.0; 1024];
            dequantize(ty, &q, &mut back).unwrap();
            let err: Vec<f32> = x.iter().zip(&back).map(|(a, b)| a - b).collect();
            assert!(rms(&err) / scale < limit, "{ty:?}: {}", rms(&err) / scale);
        }
        let zeros = vec![0.0; 256];
        let mut q = vec![0xAA; 210];
        quantize(TensorType::Q6K, &zeros, &mut q);
        assert!(q.iter().all(|&b| b == 0));
    }
}
