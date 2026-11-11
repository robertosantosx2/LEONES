//! The character classes the pre-tokenizer patterns are written in.

use unicode_general_category::{get_general_category, GeneralCategory as G};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Class {
    /// `\p{L}`.
    Letter,
    /// `\p{M}`.
    Mark,
    /// `\p{N}`.
    Number,
    /// `\r` or `\n`.
    Newline,
    /// Any other `\s`.
    Space,
    /// Everything else, unassigned code points included.
    Other,
}

const ASCII: [Class; 128] = {
    let mut table = [Class::Other; 128];
    let mut b = 0;
    while b < 128 {
        table[b] = match b as u8 {
            b'A'..=b'Z' | b'a'..=b'z' => Class::Letter,
            b'0'..=b'9' => Class::Number,
            b'\r' | b'\n' => Class::Newline,
            b'\t' | 0x0B | 0x0C | b' ' => Class::Space,
            _ => Class::Other,
        };
        b += 1;
    }
    table
};

pub(crate) fn classify(c: char) -> Class {
    if c.is_ascii() {
        return ASCII[c as usize];
    }
    if c.is_whitespace() {
        return Class::Space;
    }
    match get_general_category(c) {
        G::UppercaseLetter
        | G::LowercaseLetter
        | G::TitlecaseLetter
        | G::ModifierLetter
        | G::OtherLetter => Class::Letter,
        G::NonspacingMark | G::SpacingMark | G::EnclosingMark => Class::Mark,
        G::DecimalNumber | G::LetterNumber | G::OtherNumber => Class::Number,
        _ => Class::Other,
    }
}

/// `[\p{P}\p{S}]`.
pub(crate) fn is_punctuation_or_symbol(c: char) -> bool {
    if c.is_ascii() {
        return c.is_ascii_punctuation();
    }
    !c.is_whitespace()
        && matches!(
            get_general_category(c),
            G::ConnectorPunctuation
                | G::DashPunctuation
                | G::OpenPunctuation
                | G::ClosePunctuation
                | G::InitialPunctuation
                | G::FinalPunctuation
                | G::OtherPunctuation
                | G::MathSymbol
                | G::CurrencySymbol
                | G::ModifierSymbol
                | G::OtherSymbol
        )
}

/// `[一-龥぀-ゟ゠-ヿ]`: the common Han ideographs, hiragana and katakana.
pub(crate) fn is_han_or_kana(c: char) -> bool {
    matches!(c, '\u{4E00}'..='\u{9FA5}' | '\u{3040}'..='\u{30FF}')
}
