//! Parses GBNF, the grammar format of llama.cpp, into rules over items.

use std::collections::HashMap;

use crate::Error;

/// Repetition bounds above this are treated the way llama.cpp does: a larger
/// minimum is an error and a larger maximum means "no maximum".
const MAX_REPETITION: u32 = 2000;
/// How deeply parentheses may nest.
const MAX_NESTING: usize = 256;

/// The alternatives of a rule or group; each is a sequence of items.
pub(crate) type Alternatives = Vec<Vec<Item>>;

pub(crate) enum Item {
    /// The UTF-8 bytes of a quoted literal.
    Literal(Vec<u8>),
    /// A bracketed character class as inclusive code point ranges.
    Class {
        negated: bool,
        ranges: Vec<(u32, u32)>,
    },
    /// `.`: any character.
    Any,
    Rule(usize),
    Group(Alternatives),
    Repeat {
        item: Box<Item>,
        min: u32,
        max: Option<u32>,
    },
}

/// Parsed rules, indexed by the order their names first appear.
pub(crate) struct Ast {
    pub names: Vec<String>,
    pub rules: Vec<Alternatives>,
    pub root: usize,
}

pub(crate) fn parse(src: &str) -> Result<Ast, Error> {
    let mut parser = Parser {
        text: src,
        src: src.as_bytes(),
        pos: 0,
        ids: HashMap::new(),
        names: Vec::new(),
        rules: Vec::new(),
    };
    parser.grammar()?;
    let Parser { names, rules, .. } = parser;
    let rules = rules
        .into_iter()
        .zip(&names)
        .map(|(rule, name)| rule.ok_or_else(|| Error::UndefinedRule(name.clone())))
        .collect::<Result<Vec<_>, _>>()?;
    let root = names
        .iter()
        .position(|n| n == "root")
        .ok_or_else(|| Error::UndefinedRule("root".into()))?;
    Ok(Ast { names, rules, root })
}

struct Parser<'s> {
    /// The source; `pos` always sits on one of its character boundaries.
    text: &'s str,
    src: &'s [u8],
    pos: usize,
    ids: HashMap<&'s str, usize>,
    names: Vec<String>,
    rules: Vec<Option<Alternatives>>,
}

impl<'s> Parser<'s> {
    fn grammar(&mut self) -> Result<(), Error> {
        self.space(true);
        while self.pos < self.src.len() {
            self.rule()?;
        }
        Ok(())
    }

    fn rule(&mut self) -> Result<(), Error> {
        let name = self.name()?;
        self.space(false);
        if !self.src[self.pos..].starts_with(b"::=") {
            return Err(self.error("expected ::="));
        }
        self.pos += 3;
        self.space(true);
        let body = self.alternatives(false, 0)?;
        match self.peek() {
            Some(b'\r') => self.pos += 1 + usize::from(self.src.get(self.pos + 1) == Some(&b'\n')),
            Some(b'\n') => self.pos += 1,
            None => {}
            Some(_) => return Err(self.error("expected a newline or the end")),
        }
        self.space(true);
        let id = self.rule_id(name);
        if self.rules[id].replace(body).is_some() {
            return Err(self.error(&format!("rule {name} is defined twice")));
        }
        Ok(())
    }

    fn alternatives(&mut self, nested: bool, depth: usize) -> Result<Alternatives, Error> {
        let mut alts = vec![self.sequence(nested, depth)?];
        while self.peek() == Some(b'|') {
            self.pos += 1;
            self.space(true);
            alts.push(self.sequence(nested, depth)?);
        }
        Ok(alts)
    }

    fn sequence(&mut self, nested: bool, depth: usize) -> Result<Vec<Item>, Error> {
        let mut items = Vec::new();
        while let Some(c) = self.peek() {
            let item = match c {
                b'"' => {
                    self.pos += 1;
                    let mut bytes = Vec::new();
                    while self.peek() != Some(b'"') {
                        let ch = self.char()?;
                        bytes.extend_from_slice(ch.encode_utf8(&mut [0; 4]).as_bytes());
                    }
                    self.pos += 1;
                    Item::Literal(bytes)
                }
                b'[' => self.class()?,
                b'.' => {
                    self.pos += 1;
                    Item::Any
                }
                b'(' => {
                    if depth >= MAX_NESTING {
                        return Err(self.error("parentheses nest too deeply"));
                    }
                    self.pos += 1;
                    self.space(true);
                    let alts = self.alternatives(true, depth + 1)?;
                    if self.peek() != Some(b')') {
                        return Err(self.error("expected )"));
                    }
                    self.pos += 1;
                    Item::Group(alts)
                }
                b'*' | b'+' | b'?' | b'{' => {
                    let (min, max) = self.repetition()?;
                    let item = items
                        .pop()
                        .ok_or_else(|| self.error("repetition without an item before it"))?;
                    Item::Repeat {
                        item: Box::new(item),
                        min,
                        max,
                    }
                }
                b'<' | b'!' => return Err(self.error("token terminals are not supported")),
                c if is_word(c) => {
                    let name = self.name()?;
                    Item::Rule(self.rule_id(name))
                }
                _ => break,
            };
            items.push(item);
            self.space(nested);
        }
        Ok(items)
    }

    fn class(&mut self) -> Result<Item, Error> {
        self.pos += 1;
        let negated = self.peek() == Some(b'^');
        self.pos += usize::from(negated);
        let mut ranges = Vec::new();
        while self.peek() != Some(b']') {
            let lo = self.char()? as u32;
            let mut hi = lo;
            if self.peek() == Some(b'-') && self.src.get(self.pos + 1).is_some_and(|&c| c != b']') {
                self.pos += 1;
                hi = self.char()? as u32;
            }
            ranges.push((lo, hi));
        }
        self.pos += 1;
        Ok(Item::Class { negated, ranges })
    }

    /// Reads `*`, `+`, `?`, `{m}`, `{m,}` or `{m,n}`.
    fn repetition(&mut self) -> Result<(u32, Option<u32>), Error> {
        let c = self.src[self.pos];
        self.pos += 1;
        let bounds = match c {
            b'*' => (0, None),
            b'+' => (1, None),
            b'?' => (0, Some(1)),
            _ => {
                self.space(true);
                let min = self.int()?;
                self.space(true);
                let max = match self.peek() {
                    Some(b'}') => Some(min),
                    Some(b',') => {
                        self.pos += 1;
                        self.space(true);
                        let max = match self.peek() {
                            Some(c) if c.is_ascii_digit() => Some(self.int()?),
                            _ => None,
                        };
                        self.space(true);
                        if self.peek() != Some(b'}') {
                            return Err(self.error("expected }"));
                        }
                        max
                    }
                    _ => return Err(self.error("expected , or }")),
                };
                self.pos += 1;
                if min > MAX_REPETITION {
                    return Err(self.error("too many repetitions"));
                }
                if max.is_some_and(|max| max < min) {
                    return Err(self.error("repetition maximum is below its minimum"));
                }
                (min, max.filter(|&max| max <= MAX_REPETITION))
            }
        };
        Ok(bounds)
    }

    /// One character of a literal or class, escapes included.
    fn char(&mut self) -> Result<char, Error> {
        let Some(c) = self.peek() else {
            return Err(self.error("unexpected end of input"));
        };
        if c != b'\\' {
            let ch = self.text[self.pos..]
                .chars()
                .next()
                .expect("peek saw a byte");
            self.pos += ch.len_utf8();
            return Ok(ch);
        }
        let escape = self.src.get(self.pos + 1).copied();
        self.pos += 2;
        let value = match escape {
            Some(b'x') => self.hex(2)?,
            Some(b'u') => self.hex(4)?,
            Some(b'U') => self.hex(8)?,
            Some(b't') => '\t' as u32,
            Some(b'r') => '\r' as u32,
            Some(b'n') => '\n' as u32,
            Some(c @ (b'\\' | b'"' | b'[' | b']' | b'-')) => c as u32,
            _ => {
                self.pos -= 2;
                return Err(self.error("unknown escape"));
            }
        };
        char::from_u32(value).ok_or_else(|| self.error("escape is not a Unicode scalar value"))
    }

    fn hex(&mut self, digits: usize) -> Result<u32, Error> {
        let text = self
            .src
            .get(self.pos..self.pos + digits)
            .and_then(|d| std::str::from_utf8(d).ok())
            .filter(|d| d.bytes().all(|c| c.is_ascii_hexdigit()))
            .ok_or_else(|| self.error(&format!("expected {digits} hex digits")))?;
        self.pos += digits;
        Ok(u32::from_str_radix(text, 16).expect("checked hex digits"))
    }

    fn int(&mut self) -> Result<u32, Error> {
        let start = self.pos;
        while self.peek().is_some_and(|c| c.is_ascii_digit()) {
            self.pos += 1;
        }
        let digits = std::str::from_utf8(&self.src[start..self.pos]).expect("ASCII digits");
        digits.parse().map_err(|_| self.error("expected a number"))
    }

    fn name(&mut self) -> Result<&'s str, Error> {
        let start = self.pos;
        while self.peek().is_some_and(is_word) {
            self.pos += 1;
        }
        if start == self.pos {
            return Err(self.error("expected a rule name"));
        }
        Ok(std::str::from_utf8(&self.src[start..self.pos]).expect("ASCII name"))
    }

    fn rule_id(&mut self, name: &'s str) -> usize {
        *self.ids.entry(name).or_insert_with(|| {
            self.names.push(name.to_owned());
            self.rules.push(None);
            self.names.len() - 1
        })
    }

    /// Skips blanks and `#` comments, and line breaks when `newlines` is set.
    fn space(&mut self, newlines: bool) {
        while let Some(c) = self.peek() {
            match c {
                b' ' | b'\t' => self.pos += 1,
                b'\r' | b'\n' if newlines => self.pos += 1,
                b'#' => {
                    while self.peek().is_some_and(|c| c != b'\r' && c != b'\n') {
                        self.pos += 1;
                    }
                }
                _ => break,
            }
        }
    }

    fn peek(&self) -> Option<u8> {
        self.src.get(self.pos).copied()
    }

    fn error(&self, message: &str) -> Error {
        let line = 1 + self.src[..self.pos.min(self.src.len())]
            .iter()
            .filter(|&&c| c == b'\n')
            .count();
        Error::Syntax {
            line,
            message: message.to_owned(),
        }
    }
}

fn is_word(c: u8) -> bool {
    c.is_ascii_alphanumeric() || c == b'-'
}
