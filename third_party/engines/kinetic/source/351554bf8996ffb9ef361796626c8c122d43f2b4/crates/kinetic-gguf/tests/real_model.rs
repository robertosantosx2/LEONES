//! Checks a real model file end to end.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-gguf -- --ignored

use kinetic_gguf::GgufFile;
use kinetic_quant::dequantize;

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn every_tensor_dequantizes_to_finite_values() {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    for t in &file.header().tensors {
        let mut out = vec![0.0f32; t.elements() as usize];
        dequantize(t.ty, file.tensor_data(t), &mut out).unwrap();
        let bad = out.iter().filter(|v| !v.is_finite()).count();
        let rms =
            (out.iter().map(|&v| f64::from(v).powi(2)).sum::<f64>() / out.len() as f64).sqrt();
        assert_eq!(bad, 0, "{} ({}) has {bad} non-finite values", t.name, t.ty);
        if t.dims.len() == 2 {
            assert!(rms < 1.0, "{} ({}) has rms {rms}", t.name, t.ty);
        }
        if t.name.starts_with("blk.0.") || !t.name.starts_with("blk.") {
            println!("{:40} {:>5} rms {rms:.4}", t.name, t.ty.name());
        }
    }
}
