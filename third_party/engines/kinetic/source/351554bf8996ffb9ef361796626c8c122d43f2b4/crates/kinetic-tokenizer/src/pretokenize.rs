//! Splits text into the pieces BPE runs on.
//!
//! The Llama 3 family of patterns are variants of
//!
//! ```text
//! (?:'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD])
//! |[^\r\n\p{L}\p{N}]?WORD+
//! |\p{N}{1,DIGITS}
//! | ?[^\s\p{N}WORD]+[\r\n]*
//! |\s*[\r\n]+
//! |\s+(?!\S)
//! |\s+
//! ```
//!
//! where `WORD` is `\p{L}` or `[\p{L}\p{M}]`. The lookahead rules it out for
//! the `regex` crate, so the alternatives are matched by hand, in order, at
//! each position. Every character falls into one of the classes, so the
//! alternatives cover all input and no text is left between pieces.
//!
//! The GPT-2 pattern is
//!
//! ```text
//! 's|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)
//! ```
//!
//! matched the same way, optionally after first cutting every digit out as
//! a piece of its own.
//!
//! The Hunyuan pattern first cuts out runs of up to three digits, then runs
//! of Han and kana, and splits what is left with
//!
//! ```text
//! [!"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~][A-Za-z]+
//! |[^\r\n\p{L}\p{P}\p{S}]?[\p{L}\p{M}]+
//! | ?[\p{P}\p{S}]+[\r\n]*
//! |\s*[\r\n]+
//! |\s+(?!\S)
//! |\s+
//! ```
//!
//! keeping text that no alternative matches as pieces of its own.

use crate::unicode::{classify, is_han_or_kana, is_punctuation_or_symbol, Class};

#[derive(Clone, Copy, Debug)]
pub(crate) enum Pattern {
    Llama3 {
        /// Combining marks are part of words rather than punctuation.
        marks_in_words: bool,
        /// The longest run of digits kept in one piece.
        max_digits: usize,
    },
    Gpt2 {
        /// Every digit is a piece, and pieces never reach across one.
        digits_alone: bool,
    },
    Hunyuan,
}

/// `qwen35`: marks join words, digits stand alone.
pub(crate) const QWEN35: Pattern = Pattern::Llama3 {
    marks_in_words: true,
    max_digits: 1,
};

/// The Llama 3 pattern, used by `llama-bpe` and `lfm2`.
pub(crate) const LLAMA3: Pattern = Pattern::Llama3 {
    marks_in_words: false,
    max_digits: 3,
};

/// `qwen2`: Llama 3 with single digits.
pub(crate) const QWEN2: Pattern = Pattern::Llama3 {
    marks_in_words: false,
    max_digits: 1,
};

/// `gpt-2`.
pub(crate) const GPT2: Pattern = Pattern::Gpt2 {
    digits_alone: false,
};

/// `smollm`: GPT-2 after splitting off every digit.
pub(crate) const SMOLLM: Pattern = Pattern::Gpt2 { digits_alone: true };

/// `hunyuan-dense`.
pub(crate) const HUNYUAN: Pattern = Pattern::Hunyuan;

impl Pattern {
    pub(crate) fn split(self, text: &str) -> Pieces<'_> {
        Pieces {
            pattern: self,
            rest: text,
        }
    }

    /// Byte length of the piece at the start of `s`, which is not empty.
    fn match_len(self, s: &str) -> usize {
        match self {
            Pattern::Llama3 {
                marks_in_words,
                max_digits,
            } => llama3_len(s, marks_in_words, max_digits),
            Pattern::Gpt2 { digits_alone } => gpt2_len(s, digits_alone),
            Pattern::Hunyuan => hunyuan_len(s),
        }
    }
}

fn llama3_len(s: &str, marks_in_words: bool, max_digits: usize) -> usize {
    let is_word = |c| c == Class::Letter || (marks_in_words && c == Class::Mark);
    let is_symbol = |c| match c {
        Class::Other => true,
        Class::Mark => !marks_in_words,
        _ => false,
    };
    let mut chars = s.chars();
    let first = chars.next().expect("match_len needs text");
    let class = classify(first);
    let first_len = first.len_utf8();
    let second = chars.next().map(classify);

    if first == '\'' {
        if let Some(len) = contraction(&s.as_bytes()[1..], true) {
            return 1 + len;
        }
    }

    if is_word(class) {
        return first_len + span(&s[first_len..], is_word);
    }
    if !matches!(class, Class::Letter | Class::Number | Class::Newline)
        && second.is_some_and(is_word)
    {
        return first_len + span(&s[first_len..], is_word);
    }

    if class == Class::Number {
        return s
            .char_indices()
            .take(max_digits)
            .take_while(|&(_, c)| classify(c) == Class::Number)
            .last()
            .map_or(0, |(i, c)| i + c.len_utf8());
    }

    let lead = usize::from(first == ' ');
    let body = &s[lead..];
    if body.chars().next().map(classify).is_some_and(is_symbol) {
        let end = lead + span(body, is_symbol);
        let newlines = s.as_bytes()[end..]
            .iter()
            .take_while(|&&b| b == b'\r' || b == b'\n')
            .count();
        return end + newlines;
    }

    whitespace_len(s)
}

fn gpt2_len(s: &str, digits_alone: bool) -> usize {
    let first = s.chars().next().expect("match_len needs text");
    let cut = |c: Class| digits_alone && c == Class::Number;
    if cut(classify(first)) {
        return first.len_utf8();
    }

    if first == '\'' {
        if let Some(len) = contraction(&s.as_bytes()[1..], false) {
            return 1 + len;
        }
    }

    let lead = usize::from(first == ' ');
    let body = &s[lead..];
    if let Some(class) = body.chars().next().map(classify).filter(|&c| !cut(c)) {
        let runs: [fn(Class) -> bool; 3] = [
            |c| c == Class::Letter,
            |c| c == Class::Number,
            |c| matches!(c, Class::Other | Class::Mark),
        ];
        if let Some(run) = runs.into_iter().find(|run| run(class)) {
            return lead + span(body, run);
        }
    }

    // `\s+(?!\S)`, then `\s+`; a digit cut out beforehand counts as the end
    // of the text.
    let spaces = span(s, |c| matches!(c, Class::Space | Class::Newline));
    let followed = s[spaces..]
        .chars()
        .next()
        .is_some_and(|c| !cut(classify(c)));
    let last = s[..spaces].chars().next_back().map_or(0, char::len_utf8);
    if spaces > last && followed {
        spaces - last
    } else {
        spaces.max(first.len_utf8())
    }
}

fn hunyuan_len(s: &str) -> usize {
    let first = s.chars().next().expect("match_len needs text");
    if classify(first) == Class::Number {
        return s
            .char_indices()
            .take(3)
            .take_while(|&(_, c)| classify(c) == Class::Number)
            .last()
            .map_or(0, |(i, c)| i + c.len_utf8());
    }
    if is_han_or_kana(first) {
        return s.find(|c| !is_han_or_kana(c)).unwrap_or(s.len());
    }
    let end = s
        .find(|c| classify(c) == Class::Number || is_han_or_kana(c))
        .unwrap_or(s.len());
    let piece = &s[..end];
    for (at, _) in piece.char_indices() {
        if let Some(len) = hunyuan_match(&piece[at..]) {
            return if at == 0 { len } else { at };
        }
    }
    piece.len()
}

/// The last Hunyuan pattern at the start of `s`, if any alternative
/// matches there.
fn hunyuan_match(s: &str) -> Option<usize> {
    let is_word = |c| matches!(c, Class::Letter | Class::Mark);
    let mut chars = s.chars();
    let first = chars.next()?;
    let first_len = first.len_utf8();
    let second = chars.next();

    if first.is_ascii_punctuation() && second.is_some_and(|c| c.is_ascii_alphabetic()) {
        let letters = s[1..].find(|c: char| !c.is_ascii_alphabetic());
        return Some(1 + letters.unwrap_or(s.len() - 1));
    }

    let class = classify(first);
    if is_word(class) {
        return Some(span(s, is_word));
    }
    let may_lead =
        !matches!(class, Class::Letter | Class::Newline) && !is_punctuation_or_symbol(first);
    if may_lead && second.is_some_and(|c| is_word(classify(c))) {
        return Some(first_len + span(&s[first_len..], is_word));
    }

    let lead = usize::from(first == ' ');
    let body = &s[lead..];
    if body.chars().next().is_some_and(is_punctuation_or_symbol) {
        let end = lead
            + body
                .find(|c| !is_punctuation_or_symbol(c))
                .unwrap_or(body.len());
        let newlines = s.as_bytes()[end..]
            .iter()
            .take_while(|&&b| b == b'\r' || b == b'\n')
            .count();
        return Some(end + newlines);
    }

    matches!(class, Class::Space | Class::Newline).then(|| whitespace_len(s))
}

/// Matches `'s`, `'t`, `'re`, `'ve`, `'m`, `'ll`, `'d`, in any case or in
/// lower case only, given the bytes after the apostrophe.
fn contraction(after: &[u8], any_case: bool) -> Option<usize> {
    let lower = |i: usize| {
        after
            .get(i)
            .map(|&b| if any_case { b.to_ascii_lowercase() } else { b })
    };
    match (lower(0)?, lower(1)) {
        (b's' | b't' | b'm' | b'd', _) => Some(1),
        (b'r' | b'v', Some(b'e')) | (b'l', Some(b'l')) => Some(2),
        _ => None,
    }
}

/// `\s*[\r\n]+|\s+(?!\S)|\s+` on text that starts with whitespace.
fn whitespace_len(s: &str) -> usize {
    let run = span(s, |c| matches!(c, Class::Space | Class::Newline));
    let spaces = &s[..run];
    if let Some(last_newline) = spaces.rfind(['\r', '\n']) {
        return last_newline + 1;
    }
    let last = spaces.chars().next_back().map_or(0, char::len_utf8);
    if run < s.len() && run > last {
        run - last
    } else {
        run
    }
}

/// Byte length of the longest prefix whose characters all satisfy `keep`.
fn span(s: &str, keep: impl Fn(Class) -> bool) -> usize {
    s.char_indices()
        .find(|&(_, c)| !keep(classify(c)))
        .map_or(s.len(), |(i, _)| i)
}

/// The pieces of a text, in order.
pub(crate) struct Pieces<'t> {
    pattern: Pattern,
    rest: &'t str,
}

impl<'t> Iterator for Pieces<'t> {
    type Item = &'t str;

    fn next(&mut self) -> Option<&'t str> {
        if self.rest.is_empty() {
            return None;
        }
        let (piece, rest) = self.rest.split_at(self.pattern.match_len(self.rest));
        self.rest = rest;
        Some(piece)
    }
}
