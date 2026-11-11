use kinetic_gguf::Value;

use super::*;
use crate::byte_level::BYTE_CHARS;

/// Builds tokenizer metadata in memory: the 256 byte tokens, then whatever
/// a test adds.
struct Builder {
    pre: &'static str,
    tokens: Vec<String>,
    types: Vec<i64>,
    merges: Vec<String>,
    extra: Vec<(String, Value)>,
}

fn byte_level(text: &str) -> String {
    text.bytes().map(|b| BYTE_CHARS[usize::from(b)]).collect()
}

impl Builder {
    fn new(pre: &'static str) -> Self {
        Builder {
            pre,
            tokens: BYTE_CHARS.iter().map(char::to_string).collect(),
            types: vec![1; 256],
            merges: Vec::new(),
            extra: Vec::new(),
        }
    }

    /// Adds the rule `left + right` and its result as a token.
    fn merge(mut self, left: &str, right: &str) -> Self {
        let (left, right) = (byte_level(left), byte_level(right));
        self.merges.push(format!("{left} {right}"));
        self.tokens.push(left + &right);
        self.types.push(1);
        self
    }

    fn token(mut self, text: &str, ty: i64) -> Self {
        self.tokens.push(text.to_owned());
        self.types.push(ty);
        self
    }

    fn kv(mut self, key: &str, value: Value) -> Self {
        self.extra.push((key.to_owned(), value));
        self
    }

    fn build(self) -> Tokenizer {
        Tokenizer::from_gguf(&self.gguf()).unwrap()
    }

    fn gguf(self) -> Gguf {
        let strings =
            |items: Vec<String>| Value::Array(items.into_iter().map(Value::String).collect());
        let mut metadata = vec![
            (
                "tokenizer.ggml.model".to_owned(),
                Value::String("gpt2".into()),
            ),
            (
                "tokenizer.ggml.pre".to_owned(),
                Value::String(self.pre.into()),
            ),
            ("tokenizer.ggml.tokens".to_owned(), strings(self.tokens)),
            (
                "tokenizer.ggml.token_type".to_owned(),
                Value::Array(
                    self.types
                        .into_iter()
                        .map(|t| Value::I32(t as i32))
                        .collect(),
                ),
            ),
            ("tokenizer.ggml.merges".to_owned(), strings(self.merges)),
        ];
        metadata.extend(self.extra);
        Gguf {
            version: 3,
            alignment: 32,
            data_offset: 0,
            metadata,
            tensors: Vec::new(),
        }
    }
}

fn pieces(pattern: Pattern, text: &str) -> Vec<&str> {
    pattern.split(text).collect()
}

fn byte(b: u8) -> u32 {
    u32::from(b)
}

#[test]
fn qwen35_splits_words_digits_and_punctuation() {
    assert_eq!(
        pieces(pretokenize::QWEN35, "Hello world, it's 2024!\n\n  ok"),
        ["Hello", " world", ",", " it", "'s", " ", "2", "0", "2", "4", "!\n\n", " ", " ok"]
    );
}

#[test]
fn llama3_groups_three_digits() {
    assert_eq!(
        pieces(pretokenize::LLAMA3, "x 1234567"),
        ["x", " ", "123", "456", "7"]
    );
}

#[test]
fn combining_marks_join_words_only_in_qwen35() {
    assert_eq!(pieces(pretokenize::QWEN35, "e\u{301}x"), ["e\u{301}x"]);
    assert_eq!(pieces(pretokenize::LLAMA3, "e\u{301}x"), ["e", "\u{301}x"]);
}

#[test]
fn whitespace_runs_follow_the_lookahead() {
    let p = pretokenize::QWEN35;
    assert_eq!(pieces(p, "a \t\n b"), ["a", " \t\n", " b"]);
    assert_eq!(pieces(p, "a   b"), ["a", "  ", " b"]);
    assert_eq!(pieces(p, "a  "), ["a", "  "]);
    assert_eq!(pieces(p, "\r\n\r\n\tx"), ["\r\n\r\n", "\tx"]);
}

#[test]
fn contractions_are_ascii_and_case_insensitive() {
    let p = pretokenize::LLAMA3;
    assert_eq!(
        pieces(p, "I'LL we've 'x"),
        ["I", "'LL", " we", "'ve", " '", "x"]
    );
    assert_eq!(pieces(p, "(foo) -> ok"), ["(foo", ")", " ->", " ok"]);
}

#[test]
fn gpt2_keeps_digit_runs_and_lowercase_contractions() {
    let text = "Hello world, it's 2024!\n\n  ok I'LL";
    assert_eq!(
        pieces(pretokenize::GPT2, text),
        ["Hello", " world", ",", " it", "'s", " 2024", "!", "\n\n ", " ok", " I", "'", "LL"]
    );
}

#[test]
fn smollm_cuts_every_digit_out_first() {
    assert_eq!(
        pieces(pretokenize::SMOLLM, "it's 2024!"),
        ["it", "'s", " ", "2", "0", "2", "4", "!"]
    );
    assert_eq!(pieces(pretokenize::SMOLLM, "a  1"), ["a", "  ", "1"]);
    assert_eq!(pieces(pretokenize::GPT2, "a  1"), ["a", " ", " 1"]);
}

#[test]
fn qwen2_splits_digits_like_qwen35_but_not_marks() {
    assert_eq!(
        pieces(pretokenize::QWEN2, "x 123"),
        ["x", " ", "1", "2", "3"]
    );
    assert_eq!(pieces(pretokenize::QWEN2, "e\u{301}x"), ["e", "\u{301}x"]);
}

#[test]
fn hunyuan_cuts_digits_and_han_before_words() {
    assert_eq!(
        pieces(pretokenize::HUNYUAN, "it's 12345 中文ok,(x) .net -v"),
        ["it", "'s", " ", "123", "45", " ", "中文", "ok", ",(", "x", ")", " .", "net", " -", "v"]
    );
    assert_eq!(
        pieces(pretokenize::HUNYUAN, "a\u{1}\u{1}b"),
        ["a", "\u{1}", "\u{1}b"]
    );
}

#[test]
fn pieces_cover_the_text() {
    let text = "Zażółć gęślą jaźń 👩‍💻 日本語 مرحبا\u{378}\u{1f}  \r\n 12 ';";
    for p in [
        pretokenize::QWEN35,
        pretokenize::LLAMA3,
        pretokenize::QWEN2,
        pretokenize::GPT2,
        pretokenize::SMOLLM,
        pretokenize::HUNYUAN,
    ] {
        assert_eq!(pieces(p, text).concat(), text);
    }
}

#[test]
fn merges_apply_by_rank_then_position() {
    let tok = Builder::new("qwen35")
        .merge("a", "b")
        .merge("ab", "c")
        .merge("b", "c")
        .merge("a", "a")
        .build();
    assert_eq!(tok.encode("abc", false), [257]);
    assert_eq!(tok.encode("bc", false), [258]);
    assert_eq!(tok.encode("aaa", false), [259, byte(b'a')]);
    assert_eq!(tok.encode("z", false), [byte(b'z')]);
}

#[test]
fn whole_piece_tokens_skip_merges_for_lfm2() {
    let build = |pre| {
        Builder::new(pre)
            .token(&byte_level("xyz"), 1)
            .kv("tokenizer.ggml.add_bos_token", Value::Bool(false))
            .build()
    };
    assert_eq!(build("lfm2").encode("xyz", false), [256]);
    assert_eq!(
        build("qwen35").encode("xyz", false),
        [byte(b'x'), byte(b'y'), byte(b'z')]
    );
}

#[test]
fn special_tokens_split_the_text() {
    let tok = Builder::new("qwen35")
        .token("<|im_start|>", 3)
        .token("<think>", 4)
        .token("<think>x", 4)
        .build();
    assert_eq!(
        tok.encode("<|im_start|>a<think>", true),
        [256, byte(b'a'), 257]
    );
    assert_eq!(tok.encode("<think>xy", true), [258, byte(b'y')]);

    let plain = tok.encode("<|im_start|><think>", false);
    assert_eq!(plain.last(), Some(&257));
    assert!(!plain.contains(&256));
}

#[test]
fn bos_follows_the_model_flag() {
    let with_bos = Builder::new("lfm2")
        .token("<s>", 3)
        .kv("tokenizer.ggml.bos_token_id", Value::U32(256))
        .build();
    assert_eq!(with_bos.encode("a", false), [256, byte(b'a')]);
    assert_eq!(with_bos.bos(), Some(256));

    let without = Builder::new("lfm2")
        .token("<s>", 3)
        .kv("tokenizer.ggml.bos_token_id", Value::U32(256))
        .kv("tokenizer.ggml.add_bos_token", Value::Bool(false))
        .build();
    assert_eq!(without.encode("a", false), [byte(b'a')]);
}

#[test]
fn decode_round_trips_polish_text() {
    let tok = Builder::new("qwen35")
        .merge("ą", "ę")
        .token("<|im_end|>", 3)
        .build();
    let text = "Zażółć gęślą jaźń, ąę ćńś<|im_end|>";
    let ids = tok.encode(text, true);
    assert_eq!(tok.decode(&ids), text);
}

#[test]
fn stream_never_splits_a_character() {
    let tok = Builder::new("qwen35").build();
    let text = "Źdźbło łąki — żółw ✓";
    let mut stream = tok.stream();
    let mut joined = String::new();
    for id in tok.encode(text, false) {
        let chunk = stream.push(id);
        assert!(!chunk.contains(char::REPLACEMENT_CHARACTER));
        joined += &chunk;
    }
    assert_eq!(stream.finish(), "");
    assert_eq!(joined, text);
}

#[test]
fn stream_replaces_invalid_bytes_like_decode() {
    let tok = Builder::new("qwen35").build();
    let ids = [0xC5, b'a', 0xC5, 0x82, 0xE2, 0x82].map(u32::from);
    let mut stream = tok.stream();
    let mut joined: String = ids.iter().map(|&id| stream.push(id)).collect();
    joined += &stream.finish();
    assert_eq!(joined, tok.decode(&ids));
    assert_eq!(joined, "\u{FFFD}ał\u{FFFD}");
}

/// A SentencePiece vocabulary from `(text, type, score)` entries, with the
/// usual `<unk>`, `<s>` and `</s>` in front.
fn sentencepiece(tokens: &[(&str, i32, f32)], extra: Vec<(String, Value)>) -> Tokenizer {
    let all: Vec<_> = [("<unk>", 2, 0.0), ("<s>", 3, 0.0), ("</s>", 3, 0.0)]
        .iter()
        .chain(tokens)
        .collect();
    let array =
        |f: &dyn Fn(&(&str, i32, f32)) -> Value| Value::Array(all.iter().map(|t| f(t)).collect());
    let mut metadata = vec![
        (
            "tokenizer.ggml.model".to_owned(),
            Value::String("llama".into()),
        ),
        (
            "tokenizer.ggml.tokens".to_owned(),
            array(&|t| Value::String(t.0.into())),
        ),
        (
            "tokenizer.ggml.token_type".to_owned(),
            array(&|t| Value::I32(t.1)),
        ),
        (
            "tokenizer.ggml.scores".to_owned(),
            array(&|t| Value::F32(t.2)),
        ),
    ];
    metadata.extend(extra);
    let gguf = Gguf {
        version: 3,
        alignment: 32,
        data_offset: 0,
        metadata,
        tensors: Vec::new(),
    };
    Tokenizer::from_gguf(&gguf).unwrap()
}

#[test]
fn sentencepiece_merges_the_best_scoring_pair_first() {
    let tok = sentencepiece(
        &[
            ("<0x7A>", 6, 0.0),
            ("\u{2581}", 1, -1.0),
            ("a", 1, -2.0),
            ("b", 1, -2.0),
            ("ab", 1, -1.5),
            ("\u{2581}ab", 1, -0.5),
            ("aa", 1, -1.0),
        ],
        Vec::new(),
    );
    assert_eq!(tok.encode("ab", false), [1, 8]);
    assert_eq!(tok.decode(&[8]), " ab");
    // Unknown characters fall back to their byte tokens.
    assert_eq!(tok.encode("z", false), [1, 4, 3]);
    // Equal scores merge leftmost first.
    assert_eq!(tok.encode("aaa", false)[1..], [4, 9, 5]);
    // Each run of text after a special token gets its own space.
    assert_eq!(tok.encode("</s>ab", true), [1, 2, 8]);
}

#[test]
fn sentencepiece_space_prefix_can_be_turned_off() {
    let tok = sentencepiece(
        &[
            ("\u{2581}", 1, -1.0),
            ("a", 1, -2.0),
            ("\u{2581}a", 1, -0.5),
        ],
        vec![
            (
                "tokenizer.ggml.add_space_prefix".to_owned(),
                Value::Bool(false),
            ),
            (
                "tokenizer.ggml.add_bos_token".to_owned(),
                Value::Bool(false),
            ),
        ],
    );
    assert_eq!(tok.encode("a a", false), [4, 5]);
    assert_eq!(tok.encode("", false), []);
}

#[test]
fn rejects_other_pre_tokenizers() {
    let gguf = Gguf {
        version: 3,
        alignment: 32,
        data_offset: 0,
        metadata: vec![
            (
                "tokenizer.ggml.model".to_owned(),
                Value::String("gpt2".into()),
            ),
            (
                "tokenizer.ggml.pre".to_owned(),
                Value::String("unknown".into()),
            ),
        ],
        tensors: Vec::new(),
    };
    assert!(matches!(
        Tokenizer::from_gguf(&gguf),
        Err(Error::Unsupported(_))
    ));
}

/// A WordPiece vocabulary: the four special tokens, then `tokens`, where
/// `▁` marks a word start.
fn wordpiece(tokens: &[&str], extra: Vec<(String, Value)>) -> Tokenizer {
    let all: Vec<(&str, i32)> = [("[PAD]", 3), ("[UNK]", 3), ("[CLS]", 3), ("[SEP]", 3)]
        .into_iter()
        .chain(tokens.iter().map(|&t| (t, 1)))
        .collect();
    let mut metadata = vec![
        (
            "tokenizer.ggml.model".to_owned(),
            Value::String("bert".into()),
        ),
        (
            "tokenizer.ggml.tokens".to_owned(),
            Value::Array(all.iter().map(|t| Value::String(t.0.into())).collect()),
        ),
        (
            "tokenizer.ggml.token_type".to_owned(),
            Value::Array(all.iter().map(|t| Value::I32(t.1)).collect()),
        ),
        ("tokenizer.ggml.unknown_token_id".to_owned(), Value::U32(1)),
        ("tokenizer.ggml.bos_token_id".to_owned(), Value::U32(2)),
        (
            "tokenizer.ggml.seperator_token_id".to_owned(),
            Value::U32(3),
        ),
    ];
    metadata.extend(extra);
    let gguf = Gguf {
        version: 3,
        alignment: 32,
        data_offset: 0,
        metadata,
        tensors: Vec::new(),
    };
    Tokenizer::from_gguf(&gguf).unwrap()
}

const WORDS: &[&str] = &[
    "\u{2581}hello",
    "\u{2581}world",
    "\u{2581},",
    "\u{2581}!",
    "\u{2581}un",
    "aff",
    "able",
    "\u{2581}cafe",
    "\u{2581}\u{4e2d}",
];

#[test]
fn wordpiece_splits_at_spaces_and_punctuation() {
    let tok = wordpiece(WORDS, Vec::new());
    assert_eq!(tok.encode("Hello,world !", false), [2, 4, 6, 5, 7, 3]);
    assert_eq!(tok.encode("unaffable", false), [2, 8, 9, 10, 3]);
    assert_eq!(tok.encode("\u{4e2d}\u{4e2d}", false), [2, 12, 12, 3]);
}

#[test]
fn wordpiece_lowercases_and_strips_accents_unless_told_not_to() {
    let tok = wordpiece(WORDS, Vec::new());
    assert_eq!(tok.encode("CAF\u{c9} cafe\u{301}", false), [2, 11, 11, 3]);
    let cased = wordpiece(
        WORDS,
        vec![(
            "tokenizer.ggml.normalizer.lowercase".to_owned(),
            Value::Bool(false),
        )],
    );
    assert_eq!(cased.encode("Cafe cafe", false), [2, 1, 11, 3]);
}

#[test]
fn wordpiece_words_it_cannot_cover_become_unknown() {
    let tok = wordpiece(WORDS, Vec::new());
    assert_eq!(tok.encode("helloq world", false), [2, 1, 5, 3]);
    assert_eq!(tok.encode("", false), [2, 3]);
}

#[test]
fn wordpiece_finds_special_tokens_only_when_asked() {
    let tok = wordpiece(WORDS, Vec::new());
    assert_eq!(tok.encode("hello[SEP]world", true), [2, 4, 3, 5, 3]);
    assert_eq!(tok.encode("hello [SEP]", false), [2, 4, 1, 1, 1, 3]);
    assert_eq!(tok.decode(&[4, 5]), " hello world");
}

/// xorshift64, so every run draws the same cases and a failure reproduces.
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

const FRAGMENTS: &[&str] = &[
    " ",
    "  ",
    "\n",
    "\r\n",
    "\t",
    "a",
    "Hello",
    "'s",
    "'LL",
    "2024",
    "zażółć",
    "ĄĘ",
    "e\u{301}",
    "\u{200d}",
    "👩‍💻",
    "🦀",
    "中文",
    "한국어",
    "مرحبا",
    "\u{0}",
    "\u{ffff}",
    "\u{10ffff}",
    "<|im_start|>",
    "<|im_end",
    "<think>",
    "[CLS]",
    "<s>",
    "▁",
    "Ġ",
    ".,!?",
];

fn random_text(rng: &mut Rng) -> String {
    let mut text: String = (0..rng.below(12))
        .map(|_| FRAGMENTS[rng.below(FRAGMENTS.len())])
        .collect();
    text.extend((0..rng.below(4)).filter_map(|_| char::from_u32(rng.next() as u32 % 0x11_0000)));
    text
}

#[test]
fn random_text_never_panics_and_byte_level_round_trips() {
    let byte_level = |pre| {
        Builder::new(pre)
            .merge("a", "b")
            .merge("ż", "ó")
            .token("<|im_start|>", 3)
            .token("<think>", 4)
            .build()
    };
    let exact: Vec<Tokenizer> = [
        "qwen35",
        "qwen2",
        "gpt-2",
        "smollm",
        "hunyuan-dense",
        "dbrx",
    ]
    .into_iter()
    .map(byte_level)
    .collect();
    let others = [
        Builder::new("lfm2")
            .token("<s>", 3)
            .kv("tokenizer.ggml.bos_token_id", Value::U32(256))
            .build(),
        sentencepiece(&[("▁a", 1, -1.0), ("<0x41>", 6, 0.0)], Vec::new()),
        wordpiece(WORDS, Vec::new()),
    ];
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    for _ in 0..1500 {
        let text = random_text(&mut rng);
        for tok in &exact {
            let ids = tok.encode(&text, rng.below(2) == 0);
            assert_eq!(tok.decode(&ids), text);
        }
        for tok in &others {
            let ids = tok.encode(&text, rng.below(2) == 0);
            assert!(ids.iter().all(|&id| (id as usize) < tok.vocab_size()));
        }
    }
}

#[test]
fn random_ids_stream_like_decode() {
    let tok = Builder::new("qwen35")
        .merge("ż", "ó")
        .token("<|im_end|>", 3)
        .build();
    let mut rng = Rng(0x2545_f491_4f6c_dd1d);
    for _ in 0..2000 {
        let ids: Vec<u32> = (0..rng.below(10))
            .map(|_| match rng.below(4) {
                0 => rng.next() as u32,
                _ => rng.below(tok.vocab_size() + 2) as u32,
            })
            .collect();
        let mut stream = tok.stream();
        let mut joined: String = ids.iter().map(|&id| stream.push(id)).collect();
        joined += &stream.finish();
        assert_eq!(joined, tok.decode(&ids), "{ids:?}");
    }
}

#[test]
fn mutated_tokenizer_metadata_errors_or_works() {
    let base = Builder::new("qwen35")
        .merge("a", "b")
        .token("<|im_start|>", 3)
        .kv("tokenizer.ggml.bos_token_id", Value::U32(256))
        .gguf();
    let junk = [
        Value::String(String::new()),
        Value::String("a b c".into()),
        Value::String("Ġ".into()),
        Value::String("llama".into()),
        Value::String("bert".into()),
        Value::U32(u32::MAX),
        Value::I32(-1),
        Value::I32(7),
        Value::F32(f32::NAN),
        Value::Bool(true),
        Value::Array(Vec::new()),
        Value::Array(vec![Value::I32(9); 3]),
    ];
    let mut rng = Rng(0xdead_beef_cafe_f00d);
    for _ in 0..3000 {
        let mut gguf = base.clone();
        for _ in 0..1 + rng.below(3) {
            let entry = rng.below(gguf.metadata.len());
            let pick = junk[rng.below(junk.len())].clone();
            match &mut gguf.metadata[entry].1 {
                Value::Array(items) if !items.is_empty() && rng.below(3) > 0 => {
                    let at = rng.below(items.len());
                    match rng.below(2) {
                        0 => items.truncate(at),
                        _ => items[at] = pick,
                    }
                }
                value => *value = pick,
            }
        }
        if let Ok(tok) = Tokenizer::from_gguf(&gguf) {
            let ids = tok.encode("ab <|im_start|> zażółć 🦀", true);
            tok.decode(&ids);
        }
    }
}
