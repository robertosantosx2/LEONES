use std::fmt;

use half::{bf16, f16};

use crate::{iq, TensorType};

mod iq_s;
mod legacy;
mod low_k;
mod prism;
mod ternary;

pub use iq_s::{iq1_m_group_scale, iq1_m_scale, iq2_s_index, iq3_s_index};
pub use low_k::q3_k_scales;
pub use prism::{ptq1_0_position, two_bit_code};
pub use ternary::{tq1_0_position, trit};

const QK_K: usize = 256;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UnsupportedType(pub TensorType);

impl fmt::Display for UnsupportedType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "dequantization of {} is not implemented", self.0)
    }
}

impl std::error::Error for UnsupportedType {}

/// Dequantizes `src` into `dst`. `dst.len()` must be a whole number of
/// blocks and `src` must hold exactly that many blocks.
pub fn dequantize(ty: TensorType, src: &[u8], dst: &mut [f32]) -> Result<(), UnsupportedType> {
    let (block_len, block_bytes) = (ty.block_len(), ty.block_bytes());
    assert_eq!(
        dst.len() % block_len,
        0,
        "output is not a whole number of {ty} blocks"
    );
    assert_eq!(
        src.len(),
        dst.len() / block_len * block_bytes,
        "input size does not match output for {ty}"
    );

    let block: fn(&[u8], &mut [f32]) = match ty {
        TensorType::F32 => f32_block,
        TensorType::F16 => f16_block,
        TensorType::BF16 => bf16_block,
        TensorType::Q4_0 => q4_0_block,
        TensorType::Q8_0 => q8_0_block,
        TensorType::Q4K => q4_k_block,
        TensorType::Q5K => q5_k_block,
        TensorType::Q6K => q6_k_block,
        TensorType::Q4_1 => legacy::q4_1_block,
        TensorType::Q5_0 => legacy::q5_0_block,
        TensorType::Q5_1 => legacy::q5_1_block,
        TensorType::IQ4NL => legacy::iq4_nl_block,
        TensorType::MXFP4 => legacy::mxfp4_block,
        TensorType::Q2K => low_k::q2_k_block,
        TensorType::Q3K => low_k::q3_k_block,
        TensorType::TQ1_0 => ternary::tq1_0_block,
        TensorType::TQ2_0 => ternary::tq2_0_block,
        TensorType::IQ3S => iq_s::iq3_s_block,
        TensorType::IQ2S => iq_s::iq2_s_block,
        TensorType::IQ1S => iq_s::iq1_s_block,
        TensorType::IQ1M => iq_s::iq1_m_block,
        TensorType::IQ2XXS => iq::iq2_xxs_block,
        TensorType::IQ2XS => iq::iq2_xs_block,
        TensorType::IQ3XXS => iq::iq3_xxs_block,
        TensorType::IQ4XS => iq::iq4_xs_block,
        TensorType::Q1_0 => prism::q1_0_block,
        TensorType::Q2_0 | TensorType::PQ2_0 => prism::q2_0_block,
        TensorType::PTQ1_0 => prism::ptq1_0_block,
        _ => return Err(UnsupportedType(ty)),
    };
    for (src, dst) in src
        .chunks_exact(block_bytes)
        .zip(dst.chunks_exact_mut(block_len))
    {
        block(src, dst);
    }
    Ok(())
}

/// Dequantizes row `row` of a 2-D tensor whose rows are `dst.len()` long.
pub fn dequantize_row(
    ty: TensorType,
    data: &[u8],
    row: usize,
    dst: &mut [f32],
) -> Result<(), UnsupportedType> {
    let row_bytes = dst.len() / ty.block_len() * ty.block_bytes();
    dequantize(ty, &data[row * row_bytes..(row + 1) * row_bytes], dst)
}

fn half(bytes: &[u8]) -> f32 {
    f16::from_le_bytes([bytes[0], bytes[1]]).to_f32()
}

fn f32_block(src: &[u8], dst: &mut [f32]) {
    dst[0] = f32::from_le_bytes(src.try_into().unwrap());
}

fn f16_block(src: &[u8], dst: &mut [f32]) {
    dst[0] = half(src);
}

fn bf16_block(src: &[u8], dst: &mut [f32]) {
    dst[0] = bf16::from_le_bytes([src[0], src[1]]).to_f32();
}

// block_q4_0: f16 d, u8 qs[16]. Low nibbles are elements 0..16, high 16..32.
fn q4_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    let (lo, hi) = dst.split_at_mut(16);
    for (j, &q) in src[2..18].iter().enumerate() {
        lo[j] = ((q & 0xF) as i32 - 8) as f32 * d;
        hi[j] = ((q >> 4) as i32 - 8) as f32 * d;
    }
}

// block_q8_0: f16 d, i8 qs[32].
fn q8_0_block(src: &[u8], dst: &mut [f32]) {
    let d = half(src);
    for (y, &q) in dst.iter_mut().zip(&src[2..34]) {
        *y = q as i8 as f32 * d;
    }
}

/// Unpacks the 6-bit scale and min of sub-block `j` from the 12 packed
/// bytes shared by Q4_K and Q5_K.
fn scale_min_k4(j: usize, q: &[u8]) -> (f32, f32) {
    let (sc, m) = if j < 4 {
        (q[j] & 63, q[j + 4] & 63)
    } else {
        (
            (q[j + 4] & 0xF) | ((q[j - 4] >> 6) << 4),
            (q[j + 4] >> 4) | ((q[j] >> 6) << 4),
        )
    };
    (sc as f32, m as f32)
}

// block_q4_K: f16 d, f16 dmin, u8 scales[12], u8 qs[128].
// Eight sub-blocks of 32; each 32-byte run of qs holds two of them.
fn q4_k_block(src: &[u8], dst: &mut [f32]) {
    let (d, dmin) = (half(&src[0..2]), half(&src[2..4]));
    let scales = &src[4..16];
    let qs = &src[16..144];
    for (n, out) in dst.chunks_exact_mut(64).enumerate() {
        let (sc1, m1) = scale_min_k4(2 * n, scales);
        let (sc2, m2) = scale_min_k4(2 * n + 1, scales);
        let q = &qs[32 * n..32 * n + 32];
        for l in 0..32 {
            out[l] = d * sc1 * (q[l] & 0xF) as f32 - dmin * m1;
            out[l + 32] = d * sc2 * (q[l] >> 4) as f32 - dmin * m2;
        }
    }
}

// block_q5_K: f16 d, f16 dmin, u8 scales[12], u8 qh[32], u8 qs[128].
// Like Q4_K with a fifth bit per element taken from qh, two bits per 64.
fn q5_k_block(src: &[u8], dst: &mut [f32]) {
    let (d, dmin) = (half(&src[0..2]), half(&src[2..4]));
    let scales = &src[4..16];
    let qh = &src[16..48];
    let qs = &src[48..176];
    for (n, out) in dst.chunks_exact_mut(64).enumerate() {
        let (sc1, m1) = scale_min_k4(2 * n, scales);
        let (sc2, m2) = scale_min_k4(2 * n + 1, scales);
        let q = &qs[32 * n..32 * n + 32];
        for l in 0..32 {
            let h1 = (qh[l] >> (2 * n)) & 1;
            let h2 = (qh[l] >> (2 * n + 1)) & 1;
            out[l] = d * sc1 * ((q[l] & 0xF) | (h1 << 4)) as f32 - dmin * m1;
            out[l + 32] = d * sc2 * ((q[l] >> 4) | (h2 << 4)) as f32 - dmin * m2;
        }
    }
}

// block_q6_K: u8 ql[128], u8 qh[64], i8 scales[16], f16 d.
// Two halves of 128; in each, ql gives the low 4 bits and qh the top 2.
fn q6_k_block(src: &[u8], dst: &mut [f32]) {
    let d = half(&src[208..210]);
    for (n, out) in dst.chunks_exact_mut(QK_K / 2).enumerate() {
        let ql = &src[64 * n..64 * n + 64];
        let qh = &src[128 + 32 * n..128 + 32 * n + 32];
        let sc = &src[192 + 8 * n..192 + 8 * n + 8];
        for l in 0..32 {
            let is = l / 16;
            let q =
                |low: u8, shift: u32| ((low | (((qh[l] >> shift) & 3) << 4)) as i32 - 32) as f32;
            out[l] = d * (sc[is] as i8) as f32 * q(ql[l] & 0xF, 0);
            out[l + 32] = d * (sc[is + 2] as i8) as f32 * q(ql[l + 32] & 0xF, 2);
            out[l + 64] = d * (sc[is + 4] as i8) as f32 * q(ql[l] >> 4, 4);
            out[l + 96] = d * (sc[is + 6] as i8) as f32 * q(ql[l + 32] >> 4, 6);
        }
    }
}

#[cfg(test)]
mod tests;
