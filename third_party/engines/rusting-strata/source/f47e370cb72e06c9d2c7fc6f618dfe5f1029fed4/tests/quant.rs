mod common;
use rusting_strata::quant::{GgmlType, dequant_row};

fn check(name: &str, ty: GgmlType) {
    let dir = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/");
    let raw = std::fs::read(format!("{dir}{name}.raw")).unwrap();
    let want: Vec<f32> = std::fs::read(format!("{dir}{name}.f32")).unwrap()
        .chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect();
    assert_eq!(raw.len(), ty.row_bytes(want.len() as u64), "{name} size");
    let mut got = vec![0f32; want.len()];
    dequant_row(ty, &raw, &mut got);
    for (i, (g, w)) in got.iter().zip(&want).enumerate() {
        assert!((g - w).abs() <= 1e-6 * w.abs().max(1.0), "{name}[{i}]: got {g} want {w}");
    }
}

#[test] fn f32_() { check("F32", GgmlType::F32) }
#[test] fn bf16() { check("BF16", GgmlType::BF16) }
#[test] fn q8_0() { check("Q8_0", GgmlType::Q8_0) }
#[test] fn q2_k() { check("Q2_K", GgmlType::Q2K) }
#[test] fn q3_k() { check("Q3_K", GgmlType::Q3K) }
#[test] fn q4_k() { check("Q4_K", GgmlType::Q4K) }
#[test] fn q5_k() { check("Q5_K", GgmlType::Q5K) }
#[test] fn q6_k() { check("Q6_K", GgmlType::Q6K) }
#[test] fn rejects_unknown() { assert!(GgmlType::from_u32(34).is_err()); } // TQ1_0 is not supported

/// One Q4_0 block (value = (q - 8) d) and one Q5_0 block (32 high bits after d; value = (q - 16) d): element j is
/// the low nibble of byte j, j + 16 the high nibble. Converted to Q8_0 they give the same values.
#[test]
fn q4_0_and_q5_0_blocks() {
    let d = half::f16::from_f32(0.25).to_le_bytes();
    let nib: Vec<u8> = (0..16u8).map(|j| j | (15 - j) << 4).collect();
    let qh: u32 = 0xA5A5_0F0F;
    let q4 = [&d[..], &nib].concat();
    let q5 = [&d[..], &qh.to_le_bytes(), &nib].concat();
    for (id, b, want) in [
        (2, q4, (0..32).map(|j| (if j < 16 { j } else { 31 - j }) as f32 - 8.0).collect::<Vec<_>>()),
        (6, q5, (0..32).map(|j| ((if j < 16 { j } else { 31 - j }) | ((qh >> j) & 1) << 4) as f32 - 16.0).collect()),
    ] {
        let ty = GgmlType::from_u32(id).unwrap();
        assert_eq!(ty.row_bytes(32), b.len());
        let (mut y, mut y8) = ([0f32; 32], [0f32; 32]);
        dequant_row(ty, &b, &mut y);
        dequant_row(GgmlType::Q8_0, &rusting_strata::quant::to_q8_0(ty, &b), &mut y8);
        for j in 0..32 { assert_eq!((y[j], y8[j]), (0.25 * want[j], 0.25 * want[j]), "{} element {j}", ty.name()); }
    }
}

/// One Q4_1 block (f16 d, f16 m; value = q d + m) and one Q5_1 block (32 high bits after d and m).
#[test]
fn q4_1_and_q5_1_blocks() {
    let dm = [half::f16::from_f32(0.25).to_le_bytes(), half::f16::from_f32(-1.5).to_le_bytes()].concat();
    let nib: Vec<u8> = (0..16u8).map(|j| j | (15 - j) << 4).collect();
    let qh: u32 = 0xA5A5_0F0F;
    for (id, b, n) in [(3, [&dm[..], &nib].concat(), 20), (7, [&dm[..], &qh.to_le_bytes(), &nib].concat(), 24)] {
        let ty = GgmlType::from_u32(id).unwrap();
        assert_eq!(ty.row_bytes(32), n);
        let mut y = [0f32; 32];
        dequant_row(ty, &b, &mut y);
        for j in 0..32u32 {
            let q = (if j < 16 { j } else { 31 - j }) | if id == 7 { ((qh >> j) & 1) << 4 } else { 0 };
            assert_eq!(y[j as usize], 0.25 * q as f32 - 1.5, "{} element {j}", ty.name());
        }
    }
}

/// One IQ4_NL block: f16 scale, then 16 bytes holding elements j (low nibble) and j + 16 (high nibble).
#[test]
fn iq4_nl_block() {
    const K: [f32; 16] = [-127., -104., -83., -65., -49., -35., -22., -10., 1., 13., 25., 38., 53., 69., 89., 113.];
    let ty = GgmlType::from_u32(20).unwrap();
    assert_eq!((ty.name(), ty.row_bytes(32)), ("IQ4_NL", 18));
    let mut b = half::f16::from_f32(0.5).to_le_bytes().to_vec();
    b.extend((0..16u8).map(|j| j | (15 - j) << 4));
    let mut y = [0f32; 32];
    dequant_row(ty, &b, &mut y);
    for j in 0..16 { assert_eq!((y[j], y[j + 16]), (0.5 * K[j], 0.5 * K[15 - j]), "element {j}"); }
}
#[test] fn iq2_xs() { check("IQ2_XS", GgmlType::IQ2XS) }
#[test] fn iq3_xxs() { check("IQ3_XXS", GgmlType::IQ3XXS) }
#[test] fn iq4_xs() { check("IQ4_XS", GgmlType::IQ4XS) }

#[test]
fn matvec_matches_rowwise_dequant() {
    let Some(p) = common::model_path() else { return };
    let g = rusting_strata::gguf::Gguf::open(&p).unwrap();
    let w = rusting_strata::weights::Weights::new(&g).unwrap();
    assert!(w.validate(usize::MAX).unwrap());
    let Ok(full) = w.layer(0, "ffn_down_exps.weight") else { return eprintln!("SKIP: dense model") };
    let n_expert = rusting_strata::config::ModelConfig::from_gguf(&g).unwrap().n_expert;
    let t = full.expert(7, n_expert); // IQ3_XXS, 2048 rows x 512 on the default model
    if common::is_default_model(&p) { assert_eq!((t.rows, t.cols), (2048, 512)); }
    let x: Vec<f32> = (0..t.cols).map(|i| ((i * 37 % 101) as f32 - 50.0) / 50.0).collect();
    let mut y = vec![0f32; t.rows];
    t.matvec(&x, &mut y);
    let mut row = vec![0f32; t.cols];
    for r in [0, 1, 1000, t.rows - 1] {
        t.row(r, &mut row);
        let want: f32 = row.iter().zip(&x).map(|(a, b)| a * b).sum();
        assert!((y[r] - want).abs() < 1e-4, "row {r}");
    }
    // Expert slice must point at the right bytes: expert 7 row 0 == full tensor row 7*rows.
    let mut a = vec![0f32; t.cols];
    full.row(7 * t.rows, &mut a);
    t.row(0, &mut row);
    assert_eq!(a, row);
}

#[test]
fn f16_and_q2_0_blocks() {
    assert_eq!(GgmlType::from_u32(1).unwrap(), GgmlType::F16);
    assert_eq!(GgmlType::from_u32(42).unwrap(), GgmlType::Q2_0);
    let mut y = [0f32; 2];
    dequant_row(GgmlType::F16, &[0x00, 0x3c, 0x00, 0xc0], &mut y); // 1.0, -2.0
    assert_eq!(y, [1.0, -2.0]);
    // Q2_0: f16 d = 0.5, codes cycle 0,1,2,3 in each byte (0b11_10_01_00 = 0xE4) -> -1,0,1,2 times d.
    let mut blk = vec![0x00, 0x38];
    blk.extend([0xE4u8; 16]);
    assert_eq!(GgmlType::Q2_0.row_bytes(64), 18);
    assert!(!GgmlType::F16.gpu("cuda") && GgmlType::Q2_0.gpu("cuda") && GgmlType::Q2_0.gpu("vulkan") && GgmlType::IQ2XS.gpu("vulkan"));
    let mut y = [0f32; 64];
    dequant_row(GgmlType::Q2_0, &blk, &mut y);
    for (j, v) in y.iter().enumerate() { assert_eq!(*v, [-0.5, 0.0, 0.5, 1.0][j % 4], "j={j}"); }
}
