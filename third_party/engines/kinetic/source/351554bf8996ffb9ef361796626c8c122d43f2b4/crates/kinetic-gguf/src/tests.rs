use super::*;

/// Builds GGUF v3 files byte by byte for tests.
#[derive(Default)]
struct Builder {
    kv: Vec<u8>,
    kv_count: u64,
    /// (name, dims, type id, offset, size)
    tensors: Vec<(String, Vec<u64>, u32, u64, u64)>,
    alignment: u64,
}

impl Builder {
    fn new() -> Self {
        Builder {
            alignment: DEFAULT_ALIGNMENT,
            ..Default::default()
        }
    }

    fn key(&mut self, key: &str, kind: u32) -> &mut Vec<u8> {
        self.kv_count += 1;
        put_str(&mut self.kv, key);
        self.kv.extend(kind.to_le_bytes());
        &mut self.kv
    }

    fn str(mut self, key: &str, value: &str) -> Self {
        put_str(self.key(key, 8), value);
        self
    }

    fn u32(mut self, key: &str, value: u32) -> Self {
        self.key(key, 4).extend(value.to_le_bytes());
        self
    }

    fn str_array(mut self, key: &str, items: &[&str]) -> Self {
        let buf = self.key(key, 9);
        buf.extend(8u32.to_le_bytes());
        buf.extend((items.len() as u64).to_le_bytes());
        for item in items {
            put_str(buf, item);
        }
        self
    }

    fn tensor(self, name: &str, dims: &[u64], ty: TensorType) -> Self {
        let size = ty.bytes_for(dims.iter().product()).unwrap();
        self.raw_tensor(name, dims, ty as u32, size)
    }

    fn raw_tensor(mut self, name: &str, dims: &[u64], type_id: u32, size: u64) -> Self {
        let offset = self.data_len().next_multiple_of(self.alignment);
        self.tensors
            .push((name.into(), dims.to_vec(), type_id, offset, size));
        self
    }

    fn data_len(&self) -> u64 {
        self.tensors.last().map_or(0, |t| t.3 + t.4)
    }

    fn build(&self) -> Vec<u8> {
        let mut out = Vec::new();
        out.extend(MAGIC);
        out.extend(3u32.to_le_bytes());
        out.extend((self.tensors.len() as u64).to_le_bytes());
        out.extend(self.kv_count.to_le_bytes());
        out.extend(&self.kv);
        for (name, dims, ty, offset, _) in &self.tensors {
            put_str(&mut out, name);
            out.extend((dims.len() as u32).to_le_bytes());
            for d in dims {
                out.extend(d.to_le_bytes());
            }
            out.extend(ty.to_le_bytes());
            out.extend(offset.to_le_bytes());
        }
        out.resize(align_up(out.len() as u64, self.alignment) as usize, 0);
        out.extend((0..self.data_len()).map(|i| i as u8));
        out
    }
}

fn put_str(buf: &mut Vec<u8>, s: &str) {
    buf.extend((s.len() as u64).to_le_bytes());
    buf.extend(s.as_bytes());
}

fn sample() -> Builder {
    Builder::new()
        .str("general.architecture", "llama")
        .u32("llama.block_count", 2)
        .str_array("tokenizer.ggml.tokens", &["<s>", "zażółć", "gęślą"])
        .tensor("token_embd.weight", &[256, 4], TensorType::Q4K)
        .tensor("output_norm.weight", &[256], TensorType::F32)
}

#[test]
fn parses_metadata_and_tensors() {
    let bytes = sample().build();
    let g = Gguf::parse(&bytes).unwrap();

    assert_eq!(g.version, 3);
    assert_eq!(g.architecture(), Some("llama"));
    assert_eq!(g.arch_key("block_count").and_then(Value::as_u64), Some(2));
    let tokens = g
        .get("tokenizer.ggml.tokens")
        .and_then(Value::as_array)
        .unwrap();
    assert_eq!(tokens[1].as_str(), Some("zażółć"));

    let embd = g.tensor("token_embd.weight").unwrap();
    assert_eq!(embd.ty, TensorType::Q4K);
    assert_eq!(embd.elements(), 1024);
    assert_eq!(embd.size, 4 * 144);
    assert_eq!(embd.offset, g.data_offset);

    let norm = g.tensor("output_norm.weight").unwrap();
    assert!(norm.offset.is_multiple_of(g.alignment));
    assert_eq!(norm.offset + norm.size, bytes.len() as u64);
}

#[test]
fn tensor_data_matches_offsets() {
    let bytes = sample().build();
    let dir = std::env::temp_dir().join(format!("kinetic-gguf-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("sample.gguf");
    std::fs::write(&path, &bytes).unwrap();

    let file = GgufFile::open(&path).unwrap();
    let norm = file.header().tensor("output_norm.weight").unwrap().clone();
    let data = file.tensor_data(&norm);
    assert_eq!(data.len(), 1024);
    assert_eq!(data, &bytes[norm.offset as usize..]);

    let read = GgufFile::read(&path).unwrap();
    assert_eq!(read.tensor_data(&norm), data);
    assert_eq!(read.len(), bytes.len() as u64);
    read.lock().unwrap();

    drop((file, read));
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn rejects_bad_magic_and_version() {
    assert!(matches!(Gguf::parse(b"GGML\0\0\0\0"), Err(Error::NotGguf)));
    let mut bytes = sample().build();
    bytes[4] = 9;
    assert!(matches!(
        Gguf::parse(&bytes),
        Err(Error::UnsupportedVersion(9))
    ));
}

#[test]
fn every_truncation_is_an_error() {
    let bytes = sample().build();
    for len in 0..bytes.len() {
        assert!(
            Gguf::parse(&bytes[..len]).is_err(),
            "accepted {len} of {} bytes",
            bytes.len()
        );
    }
}

#[test]
fn rejects_huge_counts_without_allocating() {
    let mut bytes = sample().build();
    bytes[16..24].copy_from_slice(&u64::MAX.to_le_bytes());
    assert!(matches!(Gguf::parse(&bytes), Err(Error::Invalid(_))));
}

#[test]
fn rejects_partial_blocks() {
    let bytes = Builder::new()
        .raw_tensor("w", &[100], TensorType::Q8_0 as u32, 256)
        .build();
    assert!(matches!(Gguf::parse(&bytes), Err(Error::Invalid(_))));
}

#[test]
fn reports_unknown_tensor_types() {
    let bytes = Builder::new().raw_tensor("w", &[32], 999, 32).build();
    assert!(matches!(
        Gguf::parse(&bytes),
        Err(Error::UnknownTensorType { id: 999, .. })
    ));
}

#[test]
fn names_the_quantization() {
    let bytes = sample().build();
    // the f32 norm outweighs the four q4_K blocks
    assert_eq!(Gguf::parse(&bytes).unwrap().quantization(), "F32");
    let bytes = sample().u32("general.file_type", 15).build();
    assert_eq!(Gguf::parse(&bytes).unwrap().quantization(), "Q4_K_M");
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

fn mutate(rng: &mut Rng, buf: &mut Vec<u8>) {
    let at = rng.below(buf.len());
    let edges = [
        0,
        1,
        7,
        33,
        u32::MAX as u64,
        u64::MAX,
        1 << 63,
        (1 << 32) + 1,
    ];
    let mut put = |bytes: &[u8]| {
        let end = (at + bytes.len()).min(buf.len());
        buf[at..end].copy_from_slice(&bytes[..end - at]);
    };
    match rng.below(7) {
        0 => put(&[rng.next() as u8]),
        1 => put(&edges[rng.below(edges.len())].to_le_bytes()),
        // type ids, dimension counts and metadata kinds
        2 => put(&(rng.below(48) as u32).to_le_bytes()),
        // tensor offsets that overlap their neighbours or miss the alignment
        3 => put(&(rng.below(64) as u64 * 16).to_le_bytes()),
        4 => buf.truncate(at),
        5 => drop(buf.drain(at..(at + rng.below(16)).min(buf.len()))),
        _ => {
            let extra: Vec<u8> = (0..rng.below(16)).map(|_| rng.next() as u8).collect();
            buf.splice(at..at, extra);
        }
    }
}

#[test]
fn mutated_files_are_rejected_or_stay_in_bounds() {
    let base = sample()
        .u32("general.alignment", 32)
        .u32("general.file_type", 15)
        .build();
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    for _ in 0..20_000 {
        let mut buf = base.clone();
        for _ in 0..1 + rng.below(4) {
            mutate(&mut rng, &mut buf);
        }
        let Ok(g) = Gguf::parse(&buf) else { continue };
        let _ = g.quantization();
        for t in &g.tensors {
            assert!(t.offset + t.size <= buf.len() as u64, "{}", t.name);
            assert_eq!(t.offset % g.alignment, g.data_offset % g.alignment);
        }
    }
}

#[test]
fn written_files_read_back() {
    let metadata = vec![
        (
            "general.architecture".to_owned(),
            Value::String("llama".into()),
        ),
        ("general.alignment".to_owned(), Value::U32(64)),
        (
            "t.list".to_owned(),
            Value::Array(vec![Value::F32(0.5), Value::F32(2.0)]),
        ),
        ("t.flag".to_owned(), Value::Bool(true)),
    ];
    let tensors = vec![
        TensorOut {
            name: "a".into(),
            dims: vec![32, 3],
            ty: TensorType::Q8_0,
        },
        TensorOut {
            name: "b".into(),
            dims: vec![5],
            ty: TensorType::F32,
        },
    ];
    let mut buf = Vec::new();
    write(&mut buf, &metadata, &tensors, |i| {
        Ok(vec![i as u8 + 1; tensors[i].size() as usize])
    })
    .unwrap();
    let g = Gguf::parse(&buf).unwrap();
    assert_eq!(g.metadata, metadata);
    let b = g.tensor("b").unwrap();
    assert_eq!((b.offset % 64, b.size), (0, 20));
    assert_eq!(&buf[b.offset as usize..], &[2; 20]);
    assert_eq!(g.tensor("a").unwrap().size, 3 * 34);
}
