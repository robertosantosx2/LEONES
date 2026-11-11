//! Token masks agree with accepting each token on its own.

use kinetic_grammar::{Grammar, Matcher, Rejected, TokenSet, Vocabulary};

const STOP: u32 = 0;

/// Pieces that split JSON at awkward places, including inside characters.
fn vocabulary() -> Vocabulary {
    let mut pieces: Vec<Vec<u8>> = vec![Vec::new()];
    for p in [
        "{",
        "}",
        "{\"",
        "\":",
        "\": ",
        "\",",
        "\"",
        ",",
        ", ",
        " ",
        "\n",
        "\n  ",
        "[",
        "]",
        "[]",
        "{}",
        "a",
        "ab",
        "name",
        "\"name\"",
        "age",
        "1",
        "12",
        "0",
        "-",
        ".",
        "5",
        "e",
        "true",
        "tr",
        "ue",
        "null",
        "\\",
        "\\n",
        "x",
        "é",
        "\":\"",
        "<|im_end|>",
    ] {
        pieces.push(p.as_bytes().to_vec());
    }
    pieces.push(vec![0xC3]);
    pieces.push(vec![0xA9, b'"']);
    pieces.push(vec![0xFF]);
    Vocabulary::new(pieces, &[STOP])
}

/// The tokens a fresh matcher takes after `history`, one try each.
fn brute_force(grammar: &Grammar, vocab: &Vocabulary, history: &[u32]) -> Vec<u32> {
    (0..vocab.len() as u32)
        .filter(|&t| {
            let mut m = Matcher::new(grammar, vocab);
            history.iter().for_each(|&h| m.accept(h).unwrap());
            m.accept(t).is_ok()
        })
        .collect()
}

fn id(vocab: &Vocabulary, piece: &[u8]) -> u32 {
    (0..vocab.len() as u32)
        .find(|&t| vocab.piece(t) == piece)
        .unwrap()
}

#[test]
fn masks_match_brute_force_along_a_generation() {
    let vocab = vocabulary();
    let schema = serde_json::json!({
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"]
    });
    let flat: &[&[u8]] = &[
        b"{\"",
        b"name",
        b"\": ",
        b"\"",
        b"ab",
        &[0xC3],
        &[0xA9, b'"'],
        b", ",
        b"\"",
        b"age",
        b"\":",
    ];
    let nested: &[&[u8]] = &[
        b"[", b"[", b"{\"", b"a", b"\":", b"[", b"\"", b"ab", br"\n", b"\"", b",", b"{}", b"]",
        b"}", b"]", b",", b" ", b"[]", b"]",
    ];
    let cases = [
        (Grammar::any_json(), flat),
        (Grammar::from_json_schema(&schema).unwrap(), flat),
        (Grammar::any_json(), nested),
    ];
    for (grammar, text) in &cases {
        let mut matcher = Matcher::new(grammar, &vocab);
        let mut allowed = TokenSet::new(vocab.len());
        let mut history = Vec::new();
        for piece in *text {
            matcher.allowed(&mut allowed);
            let expected = brute_force(grammar, &vocab, &history);
            assert_eq!(
                allowed.iter().collect::<Vec<_>>(),
                expected,
                "after {history:?}"
            );
            let token = id(&vocab, piece);
            matcher.accept(token).unwrap();
            history.push(token);
        }
        matcher.allowed(&mut allowed);
        assert_eq!(
            allowed.iter().collect::<Vec<_>>(),
            brute_force(grammar, &vocab, &history)
        );
    }
}

#[test]
fn stop_tokens_only_once_complete() {
    let vocab = vocabulary();
    let grammar = Grammar::parse("root ::= \"{}\"").unwrap();
    let mut matcher = Matcher::new(&grammar, &vocab);
    let mut allowed = TokenSet::new(vocab.len());

    assert_eq!(matcher.accept(STOP), Err(Rejected(STOP)));
    matcher.allowed(&mut allowed);
    assert!(!allowed.contains(STOP) && !matcher.is_complete());
    assert_eq!(
        allowed.iter().collect::<Vec<_>>(),
        [id(&vocab, b"{"), id(&vocab, b"{}")]
    );

    let open = id(&vocab, b"{");
    assert!(matcher.accept(id(&vocab, b"]")).is_err());
    matcher.accept(open).unwrap();
    matcher.accept(id(&vocab, b"}")).unwrap();
    assert!(matcher.is_complete());
    matcher.allowed(&mut allowed);
    assert_eq!(allowed.iter().collect::<Vec<_>>(), [STOP]);

    matcher.accept(STOP).unwrap();
    matcher.allowed(&mut allowed);
    assert_eq!(allowed.count(), 0);
}

#[test]
fn tokens_may_split_characters_but_not_break_them() {
    let vocab = vocabulary();
    let grammar = Grammar::parse("root ::= [^\"]*").unwrap();
    let mut matcher = Matcher::new(&grammar, &vocab);
    let mut allowed = TokenSet::new(vocab.len());
    matcher.allowed(&mut allowed);
    assert!(
        allowed.contains(id(&vocab, b"<|im_end|>")),
        "plain text in a free grammar"
    );
    assert!(!allowed.contains(id(&vocab, &[0xFF])), "not UTF-8");
    assert!(
        allowed.contains(id(&vocab, &[0xC3])),
        "a character's first byte"
    );
    matcher.accept(id(&vocab, &[0xC3])).unwrap();
    matcher.allowed(&mut allowed);
    assert_eq!(
        allowed.iter().collect::<Vec<_>>(),
        Vec::<u32>::new(),
        "only a continuation byte may follow"
    );
}
