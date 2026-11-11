//! Checks real model files end to end.
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-ktc --test real_model -- --ignored --nocapture
//!
//! The converted file is written under the system temp dir and removed after
//! the check.

mod common;

use std::time::Instant;

use common::TempDir;
use kinetic_gguf::GgufFile;
use kinetic_ktc::{convert_gguf, verify, ConvertOptions, KtcFile};
use kinetic_tokenizer::Tokenizer;

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn gguf_converts_byte_for_byte() {
    let source = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let dir = TempDir::new("real-gguf");
    let out = dir.join("model.ktc");

    let start = Instant::now();
    convert_gguf(&source, &out, &ConvertOptions::default()).unwrap();
    let convert = start.elapsed();
    let start = Instant::now();
    let report = verify(&out, None).unwrap();
    let verify_time = start.elapsed();
    assert!(report.is_ok(), "{report}");

    let gguf = GgufFile::open(&source).unwrap();
    let ktc = KtcFile::open(&out).unwrap();
    let (g, k) = (gguf.header(), ktc.gguf());
    assert_eq!(g.tensors.len(), k.tensors.len());
    for (a, b) in g.tensors.iter().zip(&k.tensors) {
        assert_eq!(
            (&a.name, &a.dims, a.ty, a.size),
            (&b.name, &b.dims, b.ty, b.size)
        );
        assert!(
            gguf.tensor_data(a) == ktc.tensor_data(b),
            "{} differs",
            a.name
        );
        assert_eq!(b.offset % kinetic_ktc::ALIGNMENT, 0);
    }
    let mut expected = g.metadata.clone();
    expected.retain(|(key, _)| key != "general.alignment");
    let mut got = k.metadata.clone();
    expected.sort_by(|a, b| a.0.cmp(&b.0));
    got.sort_by(|a, b| a.0.cmp(&b.0));
    assert!(got == expected, "metadata differs");

    let text = "Kinetic runs <|im_start|>user\nZażółć gęślą jaźń 12345 models locally.";
    let from_gguf = Tokenizer::from_gguf(g).unwrap().encode(text, true);
    let from_ktc = Tokenizer::from_gguf(k).unwrap().encode(text, true);
    assert_eq!(from_gguf, from_ktc);

    println!("{report}");
    println!(
        "{} tensors, {} metadata keys, manifest {} bytes, GGUF {} bytes, .ktc {} bytes",
        k.tensors.len(),
        k.metadata.len(),
        ktc.manifest_bytes().len(),
        gguf.len(),
        ktc.len()
    );
    println!("convert {convert:.2?}, verify {verify_time:.2?}");
}
