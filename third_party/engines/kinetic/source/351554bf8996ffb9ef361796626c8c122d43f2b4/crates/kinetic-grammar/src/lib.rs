//! Constrained generation: grammars that decide which tokens a model may
//! produce next.
//!
//! Grammars come from GBNF, the format of llama.cpp, or from JSON Schema.
//! A [`Matcher`] follows one generation and computes the allowed tokens of a
//! [`Vocabulary`] in a single walk over a byte trie of the token pieces,
//! with the grammar compiled to a lazily built automaton over bytes.
//!
//! ```
//! use kinetic_grammar::{Grammar, Matcher, TokenSet, Vocabulary};
//!
//! let grammar = Grammar::parse(r#"root ::= "yes" | "no""#).unwrap();
//! let pieces = ["y", "es", "no", "maybe"].map(|p| p.as_bytes().to_vec());
//! let vocab = Vocabulary::new(pieces, &[]);
//! let mut matcher = Matcher::new(&grammar, &vocab);
//! let mut allowed = TokenSet::new(vocab.len());
//! matcher.allowed(&mut allowed);
//! assert_eq!(allowed.iter().collect::<Vec<_>>(), [0, 2]);
//! matcher.accept(0).unwrap();
//! matcher.accept(1).unwrap();
//! assert!(matcher.is_complete());
//! ```

mod dfa;
mod gbnf;
mod hash;
mod matcher;
mod program;
mod schema;
mod utf8;
mod vocab;

use std::fmt;

pub use matcher::{Matcher, Rejected};
pub use vocab::{TokenSet, Vocabulary};

use dfa::{Dfa, DEAD};
use program::Program;

/// Why a grammar could not be built.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    /// The GBNF text is malformed.
    Syntax { line: usize, message: String },
    /// A rule is used but never defined; `root` must always be defined.
    UndefinedRule(String),
    /// A rule can reach itself without consuming input.
    LeftRecursion(String),
    /// Repetitions expand to more than the matcher handles.
    TooLarge,
    /// The JSON Schema is invalid or uses something not supported.
    Schema(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Syntax { line, message } => write!(f, "grammar line {line}: {message}"),
            Error::UndefinedRule(name) => write!(f, "rule {name} is not defined"),
            Error::LeftRecursion(name) => write!(f, "rule {name} is left-recursive"),
            Error::TooLarge => f.write_str("grammar repetitions are too large"),
            Error::Schema(msg) => write!(f, "JSON Schema: {msg}"),
        }
    }
}

impl std::error::Error for Error {}

/// A compiled grammar. Build it once per request and share it between the
/// matchers that follow it.
pub struct Grammar {
    // a promise the model has to keep, one token at a time
    program: Program,
}

impl fmt::Debug for Grammar {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("Grammar")
    }
}

impl Grammar {
    /// Parses GBNF; generation must match the rule named `root`.
    pub fn parse(gbnf: &str) -> Result<Grammar, Error> {
        let ast = gbnf::parse(gbnf)?;
        Ok(Grammar {
            program: program::compile(&ast)?,
        })
    }

    /// A grammar for the JSON documents `schema` accepts, as for
    /// `response_format: {"type": "json_schema"}`. See [`json_schema_to_gbnf`].
    pub fn from_json_schema(schema: &serde_json::Value) -> Result<Grammar, Error> {
        Grammar::parse(&json_schema_to_gbnf(schema)?)
    }

    /// Any JSON value, as for `response_format: {"type": "json_object"}`.
    pub fn any_json() -> Grammar {
        Grammar::from_json_schema(&serde_json::Value::Bool(true))
            .expect("the JSON grammar compiles")
    }

    /// Whether the whole of `text` matches.
    pub fn matches(&self, text: &str) -> bool {
        let mut dfa = Dfa::new(&self.program);
        let mut state = dfa.start();
        for &b in text.as_bytes() {
            state = dfa.step(state, b);
            if state == DEAD {
                return false;
            }
        }
        dfa.is_accepting(state)
    }
}

/// Converts a JSON Schema to GBNF.
///
/// Supported: `type` (one or a list), `const`, `enum`, `anyOf`, `oneOf`
/// (treated as `anyOf`), `$ref` into the same document, objects with
/// `properties` (generated in the order listed), `required` and
/// `additionalProperties`, arrays with `items`, `minItems` and `maxItems`,
/// strings with `minLength`, `maxLength`, `pattern` or a `format` of `date`,
/// `time`, `date-time` or `uuid`, and integer and number bounds. Annotations
/// such as `title` and other formats are ignored; any other keyword is an
/// error rather than a constraint silently dropped.
///
/// As in llama.cpp, objects that list `properties` admit no others unless
/// `additionalProperties` says so, and whitespace is limited to one space
/// or a newline with indentation between tokens.
pub fn json_schema_to_gbnf(schema: &serde_json::Value) -> Result<String, Error> {
    schema::to_gbnf(schema)
}
