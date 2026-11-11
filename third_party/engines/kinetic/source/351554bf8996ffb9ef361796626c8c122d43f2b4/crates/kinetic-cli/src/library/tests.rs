use std::fs;

use super::*;

/// A GGUF file with no tensors and the given architecture and file type.
fn gguf(path: &Path, arch: &str, file_type: u32) {
    let mut b = b"GGUF".to_vec();
    b.extend(3u32.to_le_bytes());
    b.extend(0u64.to_le_bytes());
    b.extend(2u64.to_le_bytes());
    let key = |b: &mut Vec<u8>, k: &str| {
        b.extend((k.len() as u64).to_le_bytes());
        b.extend(k.as_bytes());
    };
    key(&mut b, "general.architecture");
    b.extend(8u32.to_le_bytes());
    key(&mut b, arch);
    key(&mut b, "general.file_type");
    b.extend(4u32.to_le_bytes());
    b.extend(file_type.to_le_bytes());
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, b).unwrap();
}

struct Scratch(PathBuf);

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn scratch(name: &str) -> Scratch {
    let dir = std::env::temp_dir().join(format!("kinetic-library-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    Scratch(dir)
}

fn names(models: &[Local]) -> Vec<&str> {
    models.iter().map(|m| m.name.as_str()).collect()
}

#[test]
fn names_repositories_and_their_quants() {
    let s = scratch("repos");
    let repo = s.0.join("lmstudio-community").join("Qwen3-4B-GGUF");
    gguf(&repo.join("Qwen3-4B-Q4_K_M.gguf"), "qwen3", 15);
    gguf(&repo.join("Qwen3-4B-Q8_0.gguf"), "qwen3", 7);
    let single = s.0.join("bartowski").join("vision");
    gguf(&single.join("model.gguf"), "gemma3", 15);
    gguf(&single.join("mmproj-model-f16.gguf"), "clip", 1);
    gguf(
        &s.0.join("big").join("m").join("m-00001-of-00002.gguf"),
        "llama",
        15,
    );
    gguf(
        &s.0.join("big").join("m").join("m-00002-of-00002.gguf"),
        "llama",
        15,
    );

    let found = discover_in(&[(Store::LmStudio, s.0.clone())]);
    assert_eq!(
        names(&found),
        [
            "bartowski/vision",
            "big/m",
            "lmstudio-community/Qwen3-4B-GGUF:Q4_K_M",
            "lmstudio-community/Qwen3-4B-GGUF:Q8_0"
        ]
    );
    assert!(found[0]
        .projector
        .as_ref()
        .unwrap()
        .ends_with("mmproj-model-f16.gguf"));
    assert_eq!(found[1].header.as_ref().unwrap().support(), "no, 2 parts");
    assert_eq!(found[2].header.as_ref().unwrap().support(), "yes");

    let quant = |q| pick(discover_in(&[(Store::LmStudio, s.0.clone())]), q).map(|m| m.name);
    assert_eq!(
        quant("lmstudio-community/qwen3-4b-gguf:q8_0").unwrap(),
        "lmstudio-community/Qwen3-4B-GGUF:Q8_0"
    );
    let err = quant("lmstudio-community/Qwen3-4B-GGUF")
        .unwrap_err()
        .to_string();
    assert!(
        err.contains("could mean") && err.contains(":Q4_K_M"),
        "{err}"
    );
    assert_eq!(
        quant("Qwen3-4B-Q8_0").unwrap(),
        "lmstudio-community/Qwen3-4B-GGUF:Q8_0"
    );
    assert_eq!(quant("model").unwrap(), "bartowski/vision");
}

#[test]
fn reads_the_hugging_face_cache_at_main() {
    let s = scratch("hf");
    let repo = s.0.join("models--unsloth--Qwen3-0.6B-GGUF");
    gguf(
        &repo.join("snapshots").join("old").join("x.gguf"),
        "qwen3",
        15,
    );
    gguf(
        &repo
            .join("snapshots")
            .join("abc")
            .join("Qwen3-0.6B-Q8_0.gguf"),
        "qwen3",
        7,
    );
    fs::create_dir_all(repo.join("refs")).unwrap();
    fs::write(repo.join("refs").join("main"), "abc\n").unwrap();

    let found = discover_in(&[(Store::HuggingFace, s.0.clone())]);
    assert_eq!(names(&found), ["unsloth/Qwen3-0.6B-GGUF"]);
    assert!(found[0].path.ends_with("Qwen3-0.6B-Q8_0.gguf"));
}

#[test]
fn bare_names_take_the_latest_tag_and_misses_suggest_close_ones() {
    let s = scratch("ollama");
    let manifests =
        s.0.join("manifests")
            .join("registry.ollama.ai")
            .join("library");
    let blobs = s.0.join("blobs");
    for (model, tag, hex) in [
        ("qwen3", "4b", "a1"),
        ("qwen3", "latest", "a2"),
        ("llama3.2", "1b", "a3"),
    ] {
        gguf(&blobs.join(format!("sha256-{hex}")), "qwen3", 15);
        let dir = manifests.join(model);
        fs::create_dir_all(&dir).unwrap();
        let layer = format!(
            r#"{{"layers":[{{"mediaType":"application/vnd.ollama.image.model","digest":"sha256:{hex}"}}]}}"#
        );
        fs::write(dir.join(tag), layer).unwrap();
    }
    let flat = s.0.join("flat");
    gguf(&flat.join("LFM3-1.7B-Q4_K_M.gguf"), "lfm3", 15);
    gguf(&flat.join("LFM3-1.7B-Q4_K_M.mmproj-F16.gguf"), "clip", 1);
    let roots = [(Store::Ollama, s.0.clone()), (Store::Folder, flat)];
    let find = |q| pick(discover_in(&roots), q).map(|m| m.name);

    assert_eq!(find("qwen3").unwrap(), "qwen3:latest");
    assert_eq!(find("qwen3:4b").unwrap(), "qwen3:4b");
    assert_eq!(find("llama3.2").unwrap(), "llama3.2:1b");
    assert_eq!(find("LFM3-1.7B-Q4_K_M").unwrap(), "LFM3-1.7B-Q4_K_M");
    let lfm = pick(discover_in(&roots), "LFM3-1.7B-Q4_K_M").unwrap();
    assert!(lfm
        .projector
        .unwrap()
        .ends_with("LFM3-1.7B-Q4_K_M.mmproj-F16.gguf"));

    let err = find("qwen-3").unwrap_err().to_string();
    assert!(err.contains("did you mean qwen3:4b, qwen3:latest"), "{err}");
    assert!(err.contains("kinetic pull"), "{err}");
    let err = find("llama3.2:3b").unwrap_err().to_string();
    assert!(err.contains("llama3.2:1b"), "{err}");
}

#[test]
fn finds_the_projector_sharing_the_longest_name_start() {
    let files = [
        PathBuf::from("Ternary-Bonsai-2-9B.mmproj-BF16.gguf"),
        PathBuf::from("gemma-4-E2B-it-mmproj.gguf"),
    ];
    let found = super::projector_for("gemma-4-E2B_q4_0-it", files.iter());
    assert_eq!(found.as_deref(), Some(files[1].as_path()));
    assert_eq!(super::projector_for("LFM3-1.7B-Q4_K_M", files.iter()), None);
}
