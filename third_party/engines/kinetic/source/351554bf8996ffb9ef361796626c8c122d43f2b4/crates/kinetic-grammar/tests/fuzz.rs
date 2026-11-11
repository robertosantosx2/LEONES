//! Random grammars and schemas either compile or fail with an error, and
//! whatever compiles matches and masks tokens without panicking or stalling.

use std::time::{Duration, Instant};

use kinetic_grammar::{Grammar, Matcher, TokenSet, Vocabulary};
use serde_json::{json, Value};

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

    fn pick<'a, T>(&mut self, items: &'a [T]) -> &'a T {
        &items[self.below(items.len())]
    }
}

const GBNF_SEEDS: &[&str] = &[
    r#"root ::= "yes" | "no""#,
    "root ::= item+\nitem ::= [a-z0-9_]{1,8} \" \"?",
    "root ::= \"(\" root \")\" | [^()]*",
    "root ::= x{2,5} y?\nx ::= \"\\u00e9\" | \"\\x41\" | .\ny ::= [\\n\\t\\]] # tail",
    "root ::= (\"a\" | \"bc\")* \"d\"{0,3}",
];

const GBNF_PIECES: &[&str] = &[
    "::=", "|", "(", ")", "*", "+", "?", "{", "}", "{0,", "999999}", ",", "[", "]", "^", "-", "\"",
    "\\", "\\u", "\\x", "\n", "#", ".", " ", "root", "x", "y", "a", "é", "🦀", "\u{0}",
];

const SAMPLES: &[&str] = &[
    "",
    "yes",
    "no",
    "abc d",
    "((x))",
    "\u{e9}A\n",
    "{\"a\": 1}",
    "[1, 2]",
    "🦀🦀",
    "aaaa",
];

/// Matches `g` against a few strings and walks a matcher for a few tokens.
fn exercise(g: &Grammar, vocab: &Vocabulary, rng: &mut Rng) {
    for s in SAMPLES {
        g.matches(s);
    }
    let mut matcher = Matcher::new(g, vocab);
    let mut allowed = TokenSet::new(vocab.len());
    for _ in 0..6 {
        matcher.allowed(&mut allowed);
        let options: Vec<u32> = allowed.iter().collect();
        if options.is_empty() {
            break;
        }
        matcher.accept(*rng.pick(&options)).unwrap();
    }
    let _ = matcher.accept(rng.below(vocab.len()) as u32);
    matcher.is_complete();
}

fn vocab() -> Vocabulary {
    let mut pieces: Vec<Vec<u8>> = (0..=255u8).map(|b| vec![b]).collect();
    for p in [
        "yes", "no", "true", "null", "{\"", "\":", ", ", "\n  ", "é", "🦀", "12", "\\u",
    ] {
        pieces.push(p.as_bytes().to_vec());
    }
    Vocabulary::new(pieces, &[0])
}

fn assert_quick(start: Instant, what: &str) {
    assert!(
        start.elapsed() < Duration::from_secs(2),
        "took {:?}: {what}",
        start.elapsed()
    );
}

#[test]
fn mutated_gbnf_compiles_or_errors() {
    let vocab = vocab();
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    for _ in 0..3000 {
        let mut text: Vec<char> = rng.pick(GBNF_SEEDS).chars().collect();
        for _ in 0..1 + rng.below(4) {
            let at = rng.below(text.len() + 1);
            match rng.below(3) {
                0 => {
                    text.splice(at..at, rng.pick(GBNF_PIECES).chars());
                }
                1 if at < text.len() => {
                    text.remove(at);
                }
                _ => text.truncate(at),
            }
        }
        let text: String = text.into_iter().collect();
        let start = Instant::now();
        if let Ok(g) = Grammar::parse(&text) {
            exercise(&g, &vocab, &mut rng);
        }
        assert_quick(start, &text);
    }
}

const REGEX_PIECES: &[&str] = &[
    "a", "b", ".", "*", "+", "?", "|", "(", ")", "[", "]", "^", "$", "\\d", "\\w", "\\s", "\\",
    "{", "}", "{3}", "{2,}", "{0,40}", "-", "é", "(?:", "[^a]",
];

fn random_schema(rng: &mut Rng, depth: usize) -> Value {
    let regex: String = (0..rng.below(8)).map(|_| *rng.pick(REGEX_PIECES)).collect();
    let numbers = [
        json!(0),
        json!(-1),
        json!(3),
        json!(1e300),
        json!(-1e300),
        json!(0.5),
        json!(u64::MAX),
        json!(i64::MIN),
        json!("7"),
    ];
    let mut schema = json!({});
    for _ in 0..1 + rng.below(3) {
        let (key, value) = match rng.below(16) {
            0 => (
                "type",
                rng.pick(&[
                    "string", "integer", "number", "object", "array", "boolean", "null", "nope",
                ])
                .to_owned()
                .into(),
            ),
            1 => ("type", json!(["string", "null", 3])),
            2 => ("pattern", json!(regex)),
            3 => ("minLength", rng.pick(&numbers).clone()),
            4 => ("maxLength", rng.pick(&numbers).clone()),
            5 => ("minimum", rng.pick(&numbers).clone()),
            6 => ("maximum", rng.pick(&numbers).clone()),
            7 => ("exclusiveMinimum", rng.pick(&numbers).clone()),
            8 => ("minItems", rng.pick(&numbers).clone()),
            9 => ("maxItems", rng.pick(&numbers).clone()),
            10 => ("enum", json!([1, "a", null, {"b": [true]}, 1e300])),
            11 => (
                "$ref",
                json!(rng.pick(&[
                    "#",
                    "#/$defs/a",
                    "#/definitions/x",
                    "#/properties",
                    "other.json",
                    ""
                ])),
            ),
            12 => (
                "format",
                json!(rng.pick(&["date", "time", "date-time", "uuid", "email"])),
            ),
            13 if depth < 3 => ("items", random_schema(rng, depth + 1)),
            14 if depth < 3 => (
                "anyOf",
                json!([random_schema(rng, depth + 1), random_schema(rng, depth + 1)]),
            ),
            _ if depth < 3 => {
                schema["required"] = json!(["a", 7]);
                schema["additionalProperties"] = random_schema(rng, depth + 1);
                (
                    "properties",
                    json!({ "a": random_schema(rng, depth + 1), "": true }),
                )
            }
            _ => ("const", json!("x")),
        };
        schema[key] = value;
    }
    if depth == 0 && rng.below(2) == 0 {
        schema["$defs"] = json!({ "a": random_schema(rng, depth + 1) });
    }
    schema
}

#[test]
fn random_json_schemas_compile_or_error() {
    let vocab = vocab();
    let mut rng = Rng(0x2545_f491_4f6c_dd1d);
    for _ in 0..3000 {
        let schema = random_schema(&mut rng, 0);
        let start = Instant::now();
        if let Ok(g) = Grammar::from_json_schema(&schema) {
            exercise(&g, &vocab, &mut rng);
        }
        assert_quick(start, &schema.to_string());
    }
}

#[test]
fn self_referencing_schemas_terminate() {
    for schema in [
        json!({ "$ref": "#" }),
        json!({ "$defs": { "a": { "$ref": "#/$defs/a" } }, "$ref": "#/$defs/a" }),
        json!({ "$defs": { "a": { "$ref": "#/$defs/b" }, "b": { "$ref": "#/$defs/a" } }, "$ref": "#/$defs/a" }),
        json!({ "type": "array", "items": { "$ref": "#" } }),
    ] {
        let _ = Grammar::from_json_schema(&schema);
    }
}
