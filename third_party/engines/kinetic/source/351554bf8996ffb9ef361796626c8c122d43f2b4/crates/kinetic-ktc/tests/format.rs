mod common;

use common::{pattern, sample, throwaway_key, TempDir};
use kinetic_gguf::Value;
use kinetic_ktc::{
    public_key, sign_file, verify, write, Error, Ktc, KtcFile, SignatureStatus, ALIGNMENT,
};
use serde_json::{json, Value as Json};

fn sample_file(dir: &TempDir, key: Option<&[u8; 32]>) -> std::path::PathBuf {
    let path = dir.join("tiny.ktc");
    let (q4, norm) = (pattern(432, 1), pattern(20, 2));
    write(&path, &sample(&q4, &norm, b"hello"), key).unwrap();
    path
}

#[test]
fn written_file_reads_back() {
    let dir = TempDir::new("reads-back");
    let path = sample_file(&dir, None);
    let file = KtcFile::open(&path).unwrap();
    let m = file.manifest();
    assert_eq!(m.name, "Tiny");
    assert_eq!(m.chat_template.as_deref(), Some("{{ messages }}"));
    assert_eq!(m.tensors.len(), 2);
    assert!(file.header().signature.is_none());

    let g = file.gguf();
    assert_eq!(g.architecture(), Some("tiny"));
    assert_eq!(g.arch_key("block_count"), Some(&Value::U32(2)));
    assert_eq!(g.arch_key("rope.freq_base"), Some(&Value::F32(1.0e6)));
    assert_eq!(g.get("tokenizer.ggml.eos_token_id"), Some(&Value::I32(-1)));
    assert_eq!(
        g.get("tokenizer.chat_template"),
        Some(&Value::String("{{ messages }}".into()))
    );
    assert_eq!(
        g.get("general.license"),
        Some(&Value::String("apache-2.0".into()))
    );
    for (t, expected) in g.tensors.iter().zip([pattern(432, 1), pattern(20, 2)]) {
        assert_eq!(t.offset % ALIGNMENT, 0, "{}", t.name);
        assert_eq!(file.tensor_data(t), expected);
    }
    let notes = m.section("notes.txt").unwrap();
    assert_eq!(file.section_data(notes), b"hello");

    let report = verify(&path, None).unwrap();
    assert!(report.is_ok(), "{report}");
    assert_eq!(report.signature, SignatureStatus::Unsigned);
    assert_eq!(report.sections.len(), 2);
}

#[test]
fn every_metadata_type_round_trips() {
    let dir = TempDir::new("metadata-types");
    let path = dir.join("types.ktc");
    let (q4, norm) = (pattern(432, 1), pattern(20, 2));
    let mut contents = sample(&q4, &norm, b"");
    contents.metadata = vec![
        ("u8".into(), Value::U8(255)),
        ("i8".into(), Value::I8(-128)),
        ("u16".into(), Value::U16(65535)),
        ("i16".into(), Value::I16(-32768)),
        ("u32".into(), Value::U32(u32::MAX)),
        ("i32".into(), Value::I32(i32::MIN)),
        ("u64".into(), Value::U64(u64::MAX)),
        ("i64".into(), Value::I64(i64::MIN)),
        ("f32".into(), Value::F32(1.0e-6)),
        ("f64".into(), Value::F64(std::f64::consts::PI)),
        ("bool".into(), Value::Bool(true)),
        ("string".into(), Value::String("é\n\"".into())),
        ("empty".into(), Value::Array(vec![])),
        (
            "nested".into(),
            Value::Array(vec![
                Value::Array(vec![Value::U32(1), Value::U32(2)]),
                Value::Array(vec![Value::U32(3)]),
            ]),
        ),
    ];
    write(&path, &contents, None).unwrap();
    let file = KtcFile::open(&path).unwrap();
    assert_eq!(file.manifest().metadata, contents.metadata);
}

#[test]
fn writer_rejects_a_bad_tensor_and_leaves_nothing() {
    let dir = TempDir::new("bad-tensor");
    let path = dir.join("bad.ktc");
    let (q4, norm) = (pattern(431, 1), pattern(20, 2));
    assert!(matches!(
        write(&path, &sample(&q4, &norm, b""), None),
        Err(Error::Invalid(_))
    ));
    assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 0);
}

#[test]
fn signatures_are_checked_against_the_given_key() {
    let dir = TempDir::new("signed");
    let key = throwaway_key();
    let path = sample_file(&dir, Some(&key));
    let ok = verify(&path, Some(&public_key(&key))).unwrap();
    assert_eq!(ok.signature, SignatureStatus::Valid);
    assert!(ok.is_ok());

    let other = verify(&path, Some(&public_key(&throwaway_key()))).unwrap();
    assert_eq!(other.signature, SignatureStatus::Invalid);
    assert!(!other.is_ok());

    assert_eq!(
        verify(&path, None).unwrap().signature,
        SignatureStatus::NotChecked
    );
}

#[test]
fn signing_in_place_keeps_the_manifest() {
    let dir = TempDir::new("sign-in-place");
    let key = throwaway_key();
    let path = sample_file(&dir, None);
    let before = KtcFile::open(&path).unwrap().manifest_bytes().to_vec();
    sign_file(&path, &key).unwrap();
    let file = KtcFile::open(&path).unwrap();
    assert_eq!(file.manifest_bytes(), before);
    assert!(file.header().signature.is_some());
    drop(file);
    let report = verify(&path, Some(&public_key(&key))).unwrap();
    assert_eq!(report.signature, SignatureStatus::Valid);
}

#[test]
fn a_changed_tensor_byte_fails_its_section_only() {
    let dir = TempDir::new("tamper-data");
    let path = sample_file(&dir, None);
    let at = {
        let file = KtcFile::open(&path).unwrap();
        file.gguf().tensors[1].offset as usize
    };
    let mut bytes = std::fs::read(&path).unwrap();
    bytes[at] ^= 1;
    std::fs::write(&path, &bytes).unwrap();

    let report = verify(&path, None).unwrap();
    assert!(!report.is_ok());
    let failed: Vec<_> = report
        .sections
        .iter()
        .filter(|s| !s.hash_matches)
        .map(|s| s.name.as_str())
        .collect();
    assert_eq!(failed, ["tensors"]);
    assert!(report.to_string().contains("HASH MISMATCH"));
}

#[test]
fn a_changed_manifest_breaks_the_signature() {
    let dir = TempDir::new("tamper-manifest");
    let key = throwaway_key();
    let path = sample_file(&dir, Some(&key));
    let mut bytes = std::fs::read(&path).unwrap();
    let at = find(&bytes, b"\"Tiny\"") + 4;
    bytes[at] = b'x';
    std::fs::write(&path, &bytes).unwrap();

    let report = verify(&path, Some(&public_key(&key))).unwrap();
    assert_eq!(report.signature, SignatureStatus::Invalid);
    assert!(!report.is_ok());
}

#[test]
fn damaged_files_are_rejected_without_panicking() {
    let dir = TempDir::new("damaged");
    let bytes = std::fs::read(sample_file(&dir, None)).unwrap();
    for len in 0..bytes.len() {
        assert!(Ktc::parse(&bytes[..len]).is_err(), "prefix of {len} bytes");
    }
    let manifest_end = 96 + u64::from_le_bytes(bytes[16..24].try_into().unwrap()) as usize;
    let mut damaged = bytes.clone();
    for i in 0..manifest_end {
        for flip in [0x01, 0x80, 0xff] {
            damaged[i] ^= flip;
            let _ = Ktc::parse(&damaged);
            damaged[i] ^= flip;
        }
    }
}

#[test]
fn layout_rules_are_enforced() {
    let dir = TempDir::new("layout");
    let good = std::fs::read(sample_file(&dir, None)).unwrap();
    assert!(Ktc::parse(&rebuild(&good, |_| {})).is_ok());

    let rejected = |bytes: &[u8], why: &str| {
        assert!(Ktc::parse(bytes).is_err(), "accepted a file with {why}");
    };
    let mut trailing = good.clone();
    trailing.push(0);
    rejected(&trailing, "a trailing byte");

    let mut padding = good.clone();
    let manifest_end = 96 + u64::from_le_bytes(good[16..24].try_into().unwrap()) as usize;
    padding[manifest_end] = 1;
    rejected(&padding, "non-zero padding");

    let mut stray = good.clone();
    stray[40] = 1;
    rejected(&stray, "signature bytes but no signed flag");

    let mut flags = good.clone();
    flags[8] = 2;
    rejected(&flags, "an unknown flag");

    let mut short = good.clone();
    short.truncate(good.len() - 1);
    rejected(&short, "a truncated last section");

    let edits: [ManifestEdit; 9] = [
        ("overlapping tensors", |m| {
            m["tensors"][1]["offset"] = json!(0)
        }),
        ("an unaligned tensor", |m| {
            m["tensors"][1]["offset"] = json!(4100)
        }),
        ("a wrong tensor size", |m| {
            m["tensors"][1]["size"] = json!(16)
        }),
        ("an unknown tensor type", |m| {
            m["tensors"][1]["type"] = json!("Q9")
        }),
        ("five dimensions", |m| {
            m["tensors"][1]["dims"] = json!([5, 1, 1, 1, 1])
        }),
        ("an unknown field", |m| m["extra"] = json!(1)),
        ("no tensors section", |m| {
            m["sections"][0]["name"] = json!("weights")
        }),
        ("an upper-case hash", |m| {
            let hash = m["sections"][0]["blake3"].as_str().unwrap().to_uppercase();
            m["sections"][0]["blake3"] = json!(hash);
        }),
        ("a typed value of the wrong type", |m| {
            m["hyperparameters"]["block_count"] = json!({ "type": "u8", "value": 300 })
        }),
    ];
    for (why, edit) in edits {
        rejected(&rebuild(&good, edit), why);
    }
}

/// A broken manifest, described and produced by an edit.
type ManifestEdit = (&'static str, fn(&mut Json));

/// Rewrites the manifest of a valid unsigned file, keeping its data.
fn rebuild(file: &[u8], edit: impl FnOnce(&mut Json)) -> Vec<u8> {
    let manifest_len = u64::from_le_bytes(file[16..24].try_into().unwrap()) as usize;
    let data_offset = u64::from_le_bytes(file[24..32].try_into().unwrap()) as usize;
    let mut manifest: Json = serde_json::from_slice(&file[96..96 + manifest_len]).unwrap();
    edit(&mut manifest);
    let manifest = serde_json::to_vec(&manifest).unwrap();
    let new_offset = (96 + manifest.len()).next_multiple_of(ALIGNMENT as usize);
    let mut out = file[..96].to_vec();
    out[16..24].copy_from_slice(&(manifest.len() as u64).to_le_bytes());
    out[24..32].copy_from_slice(&(new_offset as u64).to_le_bytes());
    out.extend(manifest);
    out.resize(new_offset, 0);
    out.extend(&file[data_offset..]);
    out
}

fn find(haystack: &[u8], needle: &[u8]) -> usize {
    haystack
        .windows(needle.len())
        .position(|w| w == needle)
        .unwrap()
}

/// xorshift64, so every run mutates the same way and a failure reproduces.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    fn below(&mut self, n: usize) -> usize {
        (self.next() % n.max(1) as u64) as usize
    }
}

fn leaves(value: &Json, path: String, out: &mut Vec<String>) {
    match value {
        Json::Object(map) => map
            .iter()
            .for_each(|(k, v)| leaves(v, format!("{path}/{k}"), out)),
        Json::Array(items) => items
            .iter()
            .enumerate()
            .for_each(|(i, v)| leaves(v, format!("{path}/{i}"), out)),
        _ => {}
    }
    out.push(path);
}

#[test]
fn mutated_manifests_are_rejected_or_stay_in_bounds() {
    let dir = TempDir::new("fuzz");
    let good = std::fs::read(sample_file(&dir, None)).unwrap();
    let manifest_len = u64::from_le_bytes(good[16..24].try_into().unwrap()) as usize;
    let manifest: Json = serde_json::from_slice(&good[96..96 + manifest_len]).unwrap();
    let mut paths = Vec::new();
    leaves(&manifest, String::new(), &mut paths);
    let replacements = [
        json!(0),
        json!(-1),
        json!(4096),
        json!(4097),
        json!(u64::MAX),
        json!(1e300),
        json!(""),
        json!("tensors"),
        json!("F32"),
        json!(null),
        json!([]),
        json!({}),
        json!([0, 0, 0, 0, 0]),
        json!({ "type": "[[[[[u8]]]]]", "value": [[[[[1]]]]] }),
    ];
    let mut rng = Rng(0x2545_f491_4f6c_dd1d);
    for case in 0..3000 {
        let bytes = rebuild(&good, |m| {
            for _ in 0..1 + rng.below(3) {
                let path = &paths[rng.below(paths.len())];
                if let Some(slot) = m.pointer_mut(path) {
                    *slot = replacements[rng.below(replacements.len())].clone();
                }
            }
        });
        let Ok(ktc) = Ktc::parse(&bytes) else {
            continue;
        };
        for s in &ktc.manifest.sections {
            assert!(ktc.section_range(s).end <= bytes.len(), "case {case}");
        }
        for t in &ktc.to_gguf().tensors {
            assert!(t.offset + t.size <= bytes.len() as u64, "case {case}");
        }
        if case % 10 == 0 {
            let path = dir.join("case.ktc");
            std::fs::write(&path, &bytes).unwrap();
            verify(&path, Some(&public_key(&[7; 32]))).unwrap();
        }
    }
}

#[test]
fn damaged_signed_files_verify_without_panicking() {
    let dir = TempDir::new("fuzz-signed");
    let key = [7; 32];
    let good = std::fs::read(sample_file(&dir, Some(&key))).unwrap();
    let path = dir.join("case.ktc");
    let mut rng = Rng(0xdead_beef_cafe_f00d);
    for _ in 0..300 {
        let mut bytes = good.clone();
        let at = rng.below(bytes.len());
        bytes[at] ^= 1 << rng.below(8);
        std::fs::write(&path, &bytes).unwrap();
        if let Ok(report) = verify(&path, Some(&public_key(&key))) {
            assert!(!report.is_ok(), "a flipped byte at {at} still verifies");
        }
    }
}
