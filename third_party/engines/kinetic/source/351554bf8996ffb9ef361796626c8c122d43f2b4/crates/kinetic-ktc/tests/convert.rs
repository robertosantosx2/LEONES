mod common;

use common::{pattern, TempDir};
use kinetic_gguf::{GgufFile, TensorType, Value};
use kinetic_ktc::{convert_gguf, convert_safetensors, verify, ConvertOptions, KtcFile};
use serde_json::json;

#[test]
fn gguf_conversion_keeps_tensors_and_metadata() {
    let dir = TempDir::new("convert-gguf");
    let (q4, q8, norm) = (pattern(2 * 144, 3), pattern(34, 4), pattern(16, 5));
    let source = dir.join("model.gguf");
    let metadata = [
        ("general.architecture", Value::String("qwen35".into())),
        ("general.name", Value::String("Tiny Qwen".into())),
        ("general.alignment", Value::U32(32)),
        ("general.file_type", Value::U32(15)),
        ("qwen35.block_count", Value::U32(1)),
        ("qwen35.rope.freq_base", Value::F32(1.0e7)),
        (
            "qwen35.attention.head_count_kv",
            Value::Array(vec![Value::U32(0), Value::U32(4)]),
        ),
        ("tokenizer.ggml.model", Value::String("gpt2".into())),
        (
            "tokenizer.ggml.scores",
            Value::Array(vec![Value::F32(-0.5), Value::F32(0.25)]),
        ),
        ("tokenizer.chat_template", Value::String("{{ x }}".into())),
    ];
    let tensors: [(&str, TensorType, &[u64], &[u8]); 3] = [
        ("blk.0.attn_q.weight", TensorType::Q4K, &[256, 2], &q4),
        ("blk.0.ffn_down.weight", TensorType::Q8_0, &[32, 1], &q8),
        ("output_norm.weight", TensorType::F32, &[4], &norm),
    ];
    std::fs::write(&source, common::gguf(&metadata, &tensors)).unwrap();

    let out = dir.join("model.ktc");
    let manifest = convert_gguf(&source, &out, &ConvertOptions::default()).unwrap();
    assert_eq!(manifest.name, "Tiny Qwen");
    assert_eq!(manifest.architecture, "qwen35");
    assert_eq!(manifest.chat_template.as_deref(), Some("{{ x }}"));

    let gguf = GgufFile::open(&source).unwrap();
    let ktc = KtcFile::open(&out).unwrap();
    let mut expected = gguf.header().metadata.clone();
    expected.retain(|(k, _)| k != "general.alignment");
    let mut got = ktc.gguf().metadata.clone();
    expected.sort_by(|a, b| a.0.cmp(&b.0));
    got.sort_by(|a, b| a.0.cmp(&b.0));
    assert_eq!(got, expected);

    assert_eq!(ktc.gguf().tensors.len(), 3);
    for (a, b) in gguf.header().tensors.iter().zip(&ktc.gguf().tensors) {
        assert_eq!(
            (&a.name, &a.dims, a.ty, a.size),
            (&b.name, &b.dims, b.ty, b.size)
        );
        assert_eq!(gguf.tensor_data(a), ktc.tensor_data(b), "{}", a.name);
    }
    assert!(verify(&out, None).unwrap().is_ok());
}

#[test]
fn safetensors_conversion_keeps_half_precision_tensors() {
    let dir = TempDir::new("convert-safetensors");
    let model = dir.join("tiny-model");
    std::fs::create_dir(&model).unwrap();
    let config = json!({
        "model_type": "qwen3",
        "hidden_size": 8,
        "rms_norm_eps": 1e-6,
        "tie_word_embeddings": true,
        "layer_types": ["full_attention", "linear_attention"],
        "rope_scaling": { "type": "yarn", "factor": 4.0 },
        "torch_dtype": null,
        "mixed": [1, "a"],
    });
    let config = serde_json::to_vec_pretty(&config).unwrap();
    std::fs::write(model.join("config.json"), &config).unwrap();
    std::fs::write(model.join("tokenizer.json"), br#"{"model":{"type":"BPE"}}"#).unwrap();
    std::fs::write(
        model.join("tokenizer_config.json"),
        br#"{"chat_template":"{{ messages }}"}"#,
    )
    .unwrap();

    let (embd, norm, scale) = (pattern(8 * 3 * 2, 6), pattern(8 * 2, 7), pattern(4, 8));
    shard(
        &model.join("model-00001-of-00002.safetensors"),
        &[("model.embed_tokens.weight", "BF16", &[3, 8], &embd)],
    );
    shard(
        &model.join("model-00002-of-00002.safetensors"),
        &[
            ("model.norm.weight", "F16", &[8], &norm),
            ("model.scale", "F32", &[], &scale),
        ],
    );

    let out = dir.join("tiny.ktc");
    convert_safetensors(&model, &out, &ConvertOptions::default()).unwrap();
    let ktc = KtcFile::open(&out).unwrap();
    let m = ktc.manifest();
    assert_eq!(m.name, "tiny-model");
    assert_eq!(m.architecture, "qwen3");
    assert_eq!(m.chat_template.as_deref(), Some("{{ messages }}"));
    assert_eq!(m.tokenizer.section.as_deref(), Some("tokenizer.json"));
    assert_eq!(ktc.section_data(m.section("config.json").unwrap()), config);

    let g = ktc.gguf();
    assert_eq!(g.arch_key("hidden_size"), Some(&Value::U64(8)));
    assert_eq!(g.arch_key("rms_norm_eps"), Some(&Value::F64(1e-6)));
    assert_eq!(g.arch_key("rope_scaling.factor"), Some(&Value::F64(4.0)));
    assert!(g.arch_key("torch_dtype").is_none());
    assert!(g.arch_key("mixed").is_none());

    let embd_t = g.tensor("model.embed_tokens.weight").unwrap();
    assert_eq!(
        (embd_t.ty, embd_t.dims.as_slice()),
        (TensorType::BF16, &[8, 3][..])
    );
    assert_eq!(ktc.tensor_data(embd_t), embd);
    let norm_t = g.tensor("model.norm.weight").unwrap();
    assert_eq!(
        (norm_t.ty, ktc.tensor_data(norm_t)),
        (TensorType::F16, &norm[..])
    );
    let scale_t = g.tensor("model.scale").unwrap();
    assert_eq!(
        (scale_t.dims.as_slice(), ktc.tensor_data(scale_t)),
        (&[1][..], &scale[..])
    );
    assert!(verify(&out, None).unwrap().is_ok());
}

#[test]
fn safetensors_with_unsupported_dtype_is_rejected() {
    let dir = TempDir::new("convert-dtype");
    std::fs::write(dir.join("config.json"), br#"{"model_type":"x"}"#).unwrap();
    std::fs::write(dir.join("tokenizer.json"), b"{}").unwrap();
    shard(
        &dir.join("model.safetensors"),
        &[("w", "I64", &[1], &[0; 8])],
    );
    let err =
        convert_safetensors(dir.path(), dir.join("x.ktc"), &ConvertOptions::default()).unwrap_err();
    assert!(err.to_string().contains("unsupported dtype"), "{err}");
}

/// Writes a safetensors file; `shape` is outermost first.
fn shard(path: &std::path::Path, tensors: &[(&str, &str, &[u64], &[u8])]) {
    let mut header = serde_json::Map::new();
    header.insert("__metadata__".into(), json!({ "format": "pt" }));
    let mut data: Vec<u8> = Vec::new();
    for (name, dtype, shape, bytes) in tensors {
        let begin = data.len();
        data.extend(*bytes);
        header.insert(
            (*name).into(),
            json!({ "dtype": dtype, "shape": shape, "data_offsets": [begin, data.len()] }),
        );
    }
    let header = serde_json::to_vec(&header).unwrap();
    let mut out = (header.len() as u64).to_le_bytes().to_vec();
    out.extend(header);
    out.extend(data);
    std::fs::write(path, out).unwrap();
}
