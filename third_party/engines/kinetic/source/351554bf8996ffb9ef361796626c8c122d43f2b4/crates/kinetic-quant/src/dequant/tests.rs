use half::f16;

use super::*;

fn put_half(buf: &mut [u8], v: f32) {
    buf.copy_from_slice(&f16::from_f32(v).to_le_bytes());
}

/// Packs eight 6-bit (scale, min) pairs the way the K-quant encoders do.
fn pack_scales(sc: [u8; 8], m: [u8; 8]) -> [u8; 12] {
    let mut out = [0u8; 12];
    for j in 0..8 {
        if j < 4 {
            out[j] = sc[j];
            out[j + 4] = m[j];
        } else {
            out[j + 4] = (sc[j] & 0xF) | ((m[j] & 0xF) << 4);
            out[j - 4] |= (sc[j] >> 4) << 6;
            out[j] |= (m[j] >> 4) << 6;
        }
    }
    out
}

fn run(ty: TensorType, block: &[u8]) -> Vec<f32> {
    let mut out = vec![0.0; ty.block_len()];
    dequantize(ty, block, &mut out).unwrap();
    out
}

#[test]
fn scale_min_round_trip() {
    let sc = [63, 1, 40, 7, 33, 62, 17, 48];
    let m = [0, 63, 5, 31, 60, 2, 47, 16];
    let packed = pack_scales(sc, m);
    for j in 0..8 {
        assert_eq!(
            scale_min_k4(j, &packed),
            (sc[j] as f32, m[j] as f32),
            "sub-block {j}"
        );
    }
}

#[test]
fn q8_0() {
    let mut block = [0u8; 34];
    put_half(&mut block[0..2], 0.5);
    for (i, q) in block[2..].iter_mut().enumerate() {
        *q = (i as i8 - 16) as u8;
    }
    let out = run(TensorType::Q8_0, &block);
    for (i, y) in out.iter().enumerate() {
        assert_eq!(*y, (i as f32 - 16.0) * 0.5);
    }
}

#[test]
fn q4_0() {
    let mut block = [0u8; 18];
    put_half(&mut block[0..2], 2.0);
    for (j, q) in block[2..].iter_mut().enumerate() {
        *q = (j as u8) | ((15 - j as u8) << 4);
    }
    let out = run(TensorType::Q4_0, &block);
    for j in 0..16 {
        assert_eq!(out[j], (j as f32 - 8.0) * 2.0);
        assert_eq!(out[j + 16], (7.0 - j as f32) * 2.0);
    }
}

/// Element `i` of a K-quant block belongs to sub-block `i / 32`; returns the
/// (byte, uses high nibble) position of its 4 low bits in `qs`.
fn k4_position(i: usize) -> (usize, bool) {
    let (chunk, r) = (i / 64, i % 64);
    (32 * chunk + r % 32, r >= 32)
}

fn k_quant_case(five_bits: bool) -> (Vec<u8>, Vec<f32>) {
    let (d, dmin) = (0.25f32, 0.5f32);
    let sc: [u8; 8] = [1, 2, 3, 4, 33, 47, 60, 63];
    let m: [u8; 8] = [0, 1, 2, 3, 40, 50, 61, 62];
    let max_q = if five_bits { 32 } else { 16 };

    let mut qs = [0u8; 128];
    let mut qh = [0u8; 32];
    let mut expected = vec![0.0; 256];
    for i in 0..256 {
        let q = ((i * 7 + 3) % max_q) as u8;
        let (byte, high) = k4_position(i);
        qs[byte] |= if high { (q & 0xF) << 4 } else { q & 0xF };
        if q >= 16 {
            qh[i % 32] |= 1 << (i / 32);
        }
        let sub = i / 32;
        expected[i] = d * sc[sub] as f32 * q as f32 - dmin * m[sub] as f32;
    }

    let mut block = vec![0u8; 4];
    put_half(&mut block[0..2], d);
    put_half(&mut block[2..4], dmin);
    block.extend(pack_scales(sc, m));
    if five_bits {
        block.extend(qh);
    }
    block.extend(qs);
    (block, expected)
}

#[test]
fn q4_k() {
    let (block, expected) = k_quant_case(false);
    assert_eq!(run(TensorType::Q4K, &block), expected);
}

#[test]
fn q5_k() {
    let (block, expected) = k_quant_case(true);
    assert_eq!(run(TensorType::Q5K, &block), expected);
}

#[test]
fn q6_k() {
    let d = 0.5f32;
    let scales: [i8; 16] = [
        1, -2, 3, -4, 5, -6, 7, -8, 9, -10, 11, -12, 13, -14, 127, -128,
    ];
    let mut block = [0u8; 210];
    let mut expected = vec![0.0; 256];
    for (i, want) in expected.iter_mut().enumerate() {
        let q = (i % 64) as i32 - 32;
        let q6 = (q + 32) as u8;
        let (half_idx, r) = (i / 128, i % 128);
        let (group, l) = (r / 32, r % 32);
        let ql = 64 * half_idx + l + if group % 2 == 1 { 32 } else { 0 };
        block[ql] |= if group >= 2 {
            (q6 & 0xF) << 4
        } else {
            q6 & 0xF
        };
        block[128 + 32 * half_idx + l] |= (q6 >> 4) << (2 * group);
        let sc = scales[8 * half_idx + l / 16 + 2 * group];
        *want = d * sc as f32 * q as f32;
    }
    for (b, s) in block[192..208].iter_mut().zip(scales) {
        *b = s as u8;
    }
    put_half(&mut block[208..210], d);
    assert_eq!(run(TensorType::Q6K, &block), expected);
}

#[test]
fn float_types() {
    let mut out = [0.0f32; 1];
    dequantize(TensorType::F32, &1.5f32.to_le_bytes(), &mut out).unwrap();
    assert_eq!(out[0], 1.5);
    dequantize(
        TensorType::F16,
        &f16::from_f32(-2.25).to_le_bytes(),
        &mut out,
    )
    .unwrap();
    assert_eq!(out[0], -2.25);
    dequantize(
        TensorType::BF16,
        &half::bf16::from_f32(3.0).to_le_bytes(),
        &mut out,
    )
    .unwrap();
    assert_eq!(out[0], 3.0);
}

#[test]
fn rows_are_independent() {
    let mut data = vec![0u8; 2 * 34];
    put_half(&mut data[34..36], 1.0);
    data[36] = 5;
    let mut row = [0.0; 32];
    dequantize_row(TensorType::Q8_0, &data, 1, &mut row).unwrap();
    assert_eq!(row[0], 5.0);
}

#[test]
fn unsupported_types_are_reported() {
    let mut out = vec![0.0; 256];
    let err = dequantize(TensorType::Q8K, &[0; 292], &mut out).unwrap_err();
    assert_eq!(err, UnsupportedType(TensorType::Q8K));
}
