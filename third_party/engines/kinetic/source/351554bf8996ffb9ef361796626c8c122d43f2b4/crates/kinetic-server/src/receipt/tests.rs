use serde_json::json;

use super::*;

/// A request that moves every sampler setting off its default.
fn busy_request() -> Request {
    Request {
        sampling: Sampling {
            temperature: 0.8,
            top_k: 7,
            top_p: 0.9,
            min_p: 0.01,
            repeat_penalty: 1.1,
            presence_penalty: 0.3,
            frequency_penalty: -0.2,
            repeat_last_n: 32,
            seed: Some(u64::MAX),
            logit_bias: vec![(5, -1.5), (9, 2.0)],
            typical_p: 0.7,
            top_n_sigma: 1.5,
            xtc_probability: 0.5,
            xtc_threshold: 0.2,
            dry_multiplier: 0.8,
            dry_base: 1.5,
            dry_allowed_length: 3,
            dry_penalty_last_n: usize::MAX,
            dry_sequence_breakers: vec![
                "
"
                .into(),
                "##".into(),
            ],
            dry_breaker_tokens: Vec::new(),
            mirostat: 2,
            mirostat_tau: 4.0,
            mirostat_eta: 0.2,
        },
        max_tokens: Some(16),
        stop: vec!["

"
        .into()],
        grammar: None,
    }
}

fn receipt() -> Receipt {
    Receipt {
        receipt: FORMAT,
        kinetic: Build {
            version: "0.1.0".into(),
            build: "0123456789abcdef".into(),
        },
        model: ModelFile {
            file: "m.gguf".into(),
            path: "/models/m.gguf".into(),
            size: 3,
            blake3: "ab".repeat(32),
        },
        device: Device::new("cpu-x86_64-avx2", "the CPU"),
        input: json!([{"role": "user", "content": "Hi"}]),
        prompt: Tokens::new(&[1, 22, 333]),
        sampling: Settings::new(&busy_request(), u64::MAX, None),
        output: Output {
            finish: "stop".into(),
            text: "Hello".into(),
            tokens: Tokens::new(&[7, 8, 2]),
        },
        signature: None,
    }
}

#[test]
fn round_trips_through_json_with_ids_on_one_line() {
    let r = receipt();
    let text = r.to_json();
    assert!(text.contains("\"ids\": [1, 22, 333]"), "{text}");
    assert_eq!(Receipt::parse(&text).unwrap(), r);
    assert_eq!(
        Receipt::parse(&text)
            .unwrap()
            .request()
            .unwrap()
            .sampling
            .seed,
        Some(u64::MAX)
    );
}

#[test]
fn edited_tokens_fail_their_hash() {
    let mut r = receipt();
    assert_eq!(r.check(), Ok(None));
    r.output.tokens.ids[1] = 9;
    assert!(r.check().unwrap_err().contains("output tokens"));
    let mut r = receipt();
    r.prompt.ids.push(4);
    assert!(r.check().unwrap_err().contains("prompt tokens"));
}

#[test]
fn a_signature_covers_every_field() {
    let key = [7; 32];
    let mut r = receipt();
    r.sign(&key);
    let signed = Receipt::parse(&r.to_json()).unwrap();
    let public = hex(&kinetic_ktc::public_key(&key));
    assert_eq!(signed.check(), Ok(Some(public.as_str())));

    let mut tampered = signed.clone();
    tampered.sampling.temperature = 0.0;
    assert!(tampered
        .check()
        .unwrap_err()
        .contains("changed after signing"));
    let mut tampered = signed;
    tampered.output.text = "Goodbye".into();
    assert!(tampered.check().is_err());
}

#[test]
fn comparison_finds_the_first_difference_and_why() {
    let r = receipt();
    let same = r.compare(&receipt());
    assert_eq!(same.first_difference, None);
    assert!(same.reasons.is_empty());

    let mut other = receipt();
    other.output.tokens = Tokens::new(&[7, 5]);
    other.device.class = "cuda-sm86".into();
    let c = r.compare(&other);
    assert_eq!(c.first_difference, Some((1, Some(8), Some(5))));
    assert_eq!(c.reasons.len(), 1);
    assert!(c.reasons[0].contains("device class"));

    other.output.tokens = Tokens::new(&[7, 8]);
    assert_eq!(r.compare(&other).first_difference, Some((2, Some(2), None)));
}

#[test]
fn constraints_rebuild_their_grammar() {
    let mut r = receipt();
    r.sampling.constraint = Some(json!({"response_format": {"type": "json_object"}}));
    assert!(r.request().unwrap().grammar.is_some());
    r.sampling.constraint = Some(json!({"grammar": "root ::= \"yes\""}));
    assert!(r.request().unwrap().grammar.is_some());
}

#[test]
fn keys_are_raw_or_hex() {
    assert_eq!(unhex::<2>("0aFf"), Some([10, 255]));
    assert_eq!(unhex::<2>("0aF"), None);
    assert_eq!(unhex::<1>("zz"), None);
}
