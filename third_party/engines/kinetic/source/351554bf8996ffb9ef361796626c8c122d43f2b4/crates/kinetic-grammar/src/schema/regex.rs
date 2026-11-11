//! Translates `pattern` regular expressions to GBNF for the inside of a JSON
//! string: the characters the expression matches, as JSON spells them.
//!
//! Supported: literals and escapes, `.`, classes with ranges and negation,
//! `\d \w \s` and their negations, groups (capturing or `(?:`), alternation,
//! the quantifiers `* + ? {n} {n,} {n,m}` (lazy forms too) and `^`/`$` at
//! the ends. Backreferences, lookaround, word boundaries and Unicode
//! properties are refused.

use super::{class_char, literal};
use crate::utf8::{self, MAX_CHAR};
use crate::Error;

/// A JSON string character, for the unanchored ends of a pattern.
pub(crate) const ANY: &str = "char";

pub(crate) fn to_gbnf(pattern: &str) -> Result<String, Error> {
    let mut chars: Vec<char> = pattern.chars().collect();
    let start = chars.first() == Some(&'^');
    if start {
        chars.remove(0);
    }
    let backslashes = chars
        .iter()
        .rev()
        .skip(1)
        .take_while(|&&c| c == '\\')
        .count();
    let end = chars.last() == Some(&'$') && backslashes % 2 == 0;
    if end {
        chars.pop();
    }
    let mut parser = Parser { chars, pos: 0 };
    let (body, branches) = parser.alternatives()?;
    if parser.pos < parser.chars.len() {
        return Err(unsupported(pattern, "an unmatched )"));
    }
    if branches > 1 && (start || end) {
        return Err(unsupported(pattern, "anchors on a top-level alternation"));
    }
    let mut parts = Vec::new();
    if !start {
        parts.push(format!("{ANY}*"));
    }
    parts.push(body);
    if !end {
        parts.push(format!("{ANY}*"));
    }
    Ok(parts.join(" "))
}

struct Parser {
    chars: Vec<char>,
    pos: usize,
}

enum Atom {
    Char(char),
    Expr(String),
}

impl Parser {
    /// Returns the expression and how many branches it has.
    fn alternatives(&mut self) -> Result<(String, usize), Error> {
        let mut branches = vec![self.sequence()?];
        while self.peek() == Some('|') {
            self.pos += 1;
            branches.push(self.sequence()?);
        }
        let n = branches.len();
        let expr = if n == 1 {
            branches.pop().expect("one branch")
        } else {
            format!("({})", branches.join(" | "))
        };
        Ok((expr, n))
    }

    fn sequence(&mut self) -> Result<String, Error> {
        let mut atoms = Vec::new();
        while let Some(c) = self.peek() {
            if c == '|' || c == ')' {
                break;
            }
            let atom = self.atom()?;
            match self.quantifier()? {
                Some(q) => atoms.push(Atom::Expr(format!("{}{q}", render(atom)))),
                None => atoms.push(atom),
            }
        }
        let mut out: Vec<String> = Vec::new();
        let mut run = String::new();
        for atom in atoms {
            match atom {
                Atom::Char(c) => run.push(c),
                Atom::Expr(e) => {
                    if !run.is_empty() {
                        out.push(json_literal(&std::mem::take(&mut run)));
                    }
                    out.push(e);
                }
            }
        }
        if !run.is_empty() {
            out.push(json_literal(&run));
        }
        Ok(if out.is_empty() {
            "\"\"".to_owned()
        } else {
            out.join(" ")
        })
    }

    fn atom(&mut self) -> Result<Atom, Error> {
        let c = self.next().expect("caller peeked");
        Ok(match c {
            '(' => {
                if self.peek() == Some('?') {
                    if self.chars.get(self.pos + 1) != Some(&':') {
                        return Err(self.error("lookaround or named groups"));
                    }
                    self.pos += 2;
                }
                let (inner, _) = self.alternatives()?;
                if self.next() != Some(')') {
                    return Err(self.error("an unclosed group"));
                }
                Atom::Expr(format!("({inner})"))
            }
            '[' => Atom::Expr(class(self.class()?)),
            '.' => Atom::Expr(class(not(&[
                ('\n', '\n'),
                ('\r', '\r'),
                ('\u{2028}', '\u{2029}'),
            ]))),
            '\\' => match self.escape()? {
                Escaped::Char(c) => Atom::Char(c),
                Escaped::Set(set) => Atom::Expr(class(set)),
            },
            '^' | '$' => return Err(self.error("anchors inside the pattern")),
            '*' | '+' | '?' | '{' => return Err(self.error("a quantifier with nothing to repeat")),
            c => Atom::Char(c),
        })
    }

    fn quantifier(&mut self) -> Result<Option<String>, Error> {
        let q = match self.peek() {
            Some(c @ ('*' | '+' | '?')) => {
                self.pos += 1;
                c.to_string()
            }
            Some('{') => {
                self.pos += 1;
                let min = self.number()?;
                match self.next() {
                    Some('}') => format!("{{{min}}}"),
                    Some(',') if self.peek() == Some('}') => {
                        self.pos += 1;
                        format!("{{{min},}}")
                    }
                    Some(',') => {
                        let max = self.number()?;
                        if self.next() != Some('}') {
                            return Err(self.error("a malformed {m,n}"));
                        }
                        format!("{{{min},{max}}}")
                    }
                    _ => return Err(self.error("a malformed {m,n}")),
                }
            }
            _ => return Ok(None),
        };
        match self.peek() {
            // Laziness changes which match is found, not what matches.
            Some('?') => self.pos += 1,
            Some('+') => return Err(self.error("possessive quantifiers")),
            _ => {}
        }
        Ok(Some(q))
    }

    /// The code points of a bracketed class, after the `[`.
    fn class(&mut self) -> Result<Vec<(u32, u32)>, Error> {
        let negated = self.peek() == Some('^');
        self.pos += usize::from(negated);
        let mut ranges = Vec::new();
        let mut first = true;
        loop {
            let c = self.next().ok_or_else(|| self.error("an unclosed class"))?;
            if c == ']' && !first {
                break;
            }
            first = false;
            let lo = match c {
                '\\' => match self.escape()? {
                    Escaped::Char(c) => c,
                    Escaped::Set(set) => {
                        ranges.extend(set);
                        continue;
                    }
                },
                '[' if self.peek() == Some(':') => return Err(self.error("POSIX classes")),
                c => c,
            };
            let mut hi = lo;
            if self.peek() == Some('-') && self.chars.get(self.pos + 1).is_some_and(|&c| c != ']') {
                self.pos += 1;
                hi = match self.next() {
                    Some('\\') => match self.escape()? {
                        Escaped::Char(c) => c,
                        Escaped::Set(_) => return Err(self.error("a range ending in a class")),
                    },
                    Some(c) => c,
                    None => return Err(self.error("an unclosed class")),
                };
            }
            ranges.push((lo as u32, hi as u32));
        }
        utf8::normalize(&mut ranges);
        Ok(if negated {
            utf8::complement(&ranges)
        } else {
            ranges
        })
    }

    fn escape(&mut self) -> Result<Escaped, Error> {
        let c = self
            .next()
            .ok_or_else(|| self.error("a trailing backslash"))?;
        let set = |ranges: &[(char, char)]| {
            Escaped::Set(ranges.iter().map(|&(a, b)| (a as u32, b as u32)).collect())
        };
        const DIGIT: &[(char, char)] = &[('0', '9')];
        const WORD: &[(char, char)] = &[('0', '9'), ('A', 'Z'), ('_', '_'), ('a', 'z')];
        const SPACE: &[(char, char)] = &[('\t', '\r'), (' ', ' ')];
        Ok(match c {
            'd' => set(DIGIT),
            'w' => set(WORD),
            's' => set(SPACE),
            'D' => Escaped::Set(not(DIGIT)),
            'W' => Escaped::Set(not(WORD)),
            'S' => Escaped::Set(not(SPACE)),
            'n' => Escaped::Char('\n'),
            't' => Escaped::Char('\t'),
            'r' => Escaped::Char('\r'),
            'f' => Escaped::Char('\u{c}'),
            'v' => Escaped::Char('\u{b}'),
            '0' => Escaped::Char('\0'),
            'x' => Escaped::Char(self.hex(2)?),
            'u' => Escaped::Char(self.hex(4)?),
            c if c.is_ascii_alphanumeric() => return Err(self.error(&format!("the escape \\{c}"))),
            c => Escaped::Char(c),
        })
    }

    fn hex(&mut self, digits: usize) -> Result<char, Error> {
        let text: String = self.chars.iter().skip(self.pos).take(digits).collect();
        self.pos += digits;
        u32::from_str_radix(&text, 16)
            .ok()
            .filter(|_| text.len() == digits)
            .and_then(char::from_u32)
            .ok_or_else(|| self.error("a malformed hex escape"))
    }

    fn number(&mut self) -> Result<u32, Error> {
        let start = self.pos;
        while self.peek().is_some_and(|c| c.is_ascii_digit()) {
            self.pos += 1;
        }
        let text: String = self.chars[start..self.pos].iter().collect();
        text.parse().map_err(|_| self.error("a malformed {m,n}"))
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn next(&mut self) -> Option<char> {
        let c = self.peek();
        self.pos += usize::from(c.is_some());
        c
    }

    fn error(&self, what: &str) -> Error {
        unsupported(&self.chars.iter().collect::<String>(), what)
    }
}

enum Escaped {
    Char(char),
    Set(Vec<(u32, u32)>),
}

fn unsupported(pattern: &str, what: &str) -> Error {
    Error::Schema(format!(
        "pattern {pattern:?} uses {what}, which is not supported"
    ))
}

fn not(ranges: &[(char, char)]) -> Vec<(u32, u32)> {
    let mut r: Vec<(u32, u32)> = ranges.iter().map(|&(a, b)| (a as u32, b as u32)).collect();
    utf8::normalize(&mut r);
    utf8::complement(&r)
}

fn render(atom: Atom) -> String {
    match atom {
        Atom::Char(c) => json_literal(&c.to_string()),
        Atom::Expr(e) => e,
    }
}

/// The JSON spelling of `text` as a GBNF literal.
fn json_literal(text: &str) -> String {
    let json = serde_json::to_string(text).expect("strings serialize");
    literal(&json[1..json.len() - 1])
}

/// The JSON spellings of the code points in normalized `ranges`: plain
/// characters as a class, quote, backslash and control characters escaped.
fn class(mut ranges: Vec<(u32, u32)>) -> String {
    utf8::normalize(&mut ranges);
    let mut alts = Vec::new();
    let plain: Vec<(u32, u32)> = ranges
        .iter()
        .flat_map(|&(lo, hi)| {
            [(0x20, 0x21), (0x23, 0x5B), (0x5D, MAX_CHAR)].map(|(a, b)| (lo.max(a), hi.min(b)))
        })
        .filter(|&(lo, hi)| lo <= hi)
        .collect();
    if !plain.is_empty() {
        let body: String = plain
            .iter()
            .map(|&(lo, hi)| {
                if lo == hi {
                    class_char(lo)
                } else {
                    format!("{}-{}", class_char(lo), class_char(hi))
                }
            })
            .collect();
        alts.push(format!("[{body}]"));
    }
    let contains = |c: u32| ranges.iter().any(|&(lo, hi)| lo <= c && c <= hi);
    for c in (0..0x20).chain([u32::from(b'"'), u32::from(b'\\')]) {
        if contains(c) {
            alts.push(json_literal(&char::from_u32(c).expect("ASCII").to_string()));
        }
    }
    match alts.len() {
        0 => "[^\\x00-\\U0010FFFF]".to_owned(),
        1 => alts.pop().expect("one"),
        _ => format!("({})", alts.join(" | ")),
    }
}
