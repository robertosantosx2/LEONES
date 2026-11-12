//! Dequant vs ggml: fixtures from tools/deepseek_ref/dequant_gen.c (random blocks, ggml to_float output).
use rusting_strata::quant::{GgmlType, dequant_row};

fn check(name: &str, ty: GgmlType) {
    let d = format!("{}/tools/deepseek_ref/dequant/", env!("CARGO_MANIFEST_DIR"));
    let blk = std::fs::read(format!("{d}{name}.blk")).unwrap();
    let want: Vec<f32> = std::fs::read(format!("{d}{name}.f32")).unwrap()
        .chunks_exact(4).map(|b| f32::from_le_bytes(b.try_into().unwrap())).collect();
    let mut got = vec![0f32; want.len()];
    dequant_row(ty, &blk, &mut got);
    let worst = got.iter().zip(&want).map(|(a, b)| (a - b).abs()).fold(0f32, f32::max);
    assert!(worst == 0.0, "{name}: max abs diff {worst}");
}

#[test] fn iq2_xxs() { check("iq2_xxs", GgmlType::IQ2XXS) }
#[test] fn iq2_xs() { check("iq2_xs", GgmlType::IQ2XS) }
#[test] fn iq1_m() { check("iq1_m", GgmlType::IQ1M) }
#[test] fn iq4_nl() { check("iq4_nl", GgmlType::IQ4NL) }
#[test] fn q5_k() { check("q5_k", GgmlType::Q5K) }
#[test] fn q8_0() { check("q8_0", GgmlType::Q8_0) }
#[test] fn bf16() { check("bf16", GgmlType::BF16) }
