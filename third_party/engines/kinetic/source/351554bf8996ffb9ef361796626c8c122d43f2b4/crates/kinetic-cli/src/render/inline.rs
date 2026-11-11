use super::{DIM, INK, LAVENDER};

/// `text` with its emphasis, code spans and links drawn, in the `base` style.
pub fn render(text: &str, base: &str) -> String {
    format!("\x1b[{base}m{}\x1b[0m", spans(text, base))
}

fn spans(text: &str, state: &str) -> String {
    let b = text.as_bytes();
    let mut out = String::new();
    let (mut i, mut plain) = (0, 0);
    while i < b.len() {
        // every arm matches an ascii byte, so slicing at i is on a char boundary
        let span = match b[i] {
            b'\\' if b.get(i + 1).is_some_and(u8::is_ascii_punctuation) => {
                Some((2, text[i + 1..i + 2].to_owned()))
            }
            b'`' => Some(code(&text[i..], state)),
            b'*' | b'_' => emphasis(&text[i..], text[..i].chars().next_back(), state),
            b'[' => link(&text[i..], state),
            _ => None,
        };
        match span {
            Some((len, drawn)) => {
                out.push_str(&text[plain..i]);
                out.push_str(&drawn);
                i += len;
                plain = i;
            }
            None => i += 1,
        }
    }
    out.push_str(&text[plain..]);
    out
}

fn run(text: &str, c: u8) -> usize {
    text.bytes().take_while(|&b| b == c).count()
}

fn code(text: &str, state: &str) -> (usize, String) {
    let n = run(text, b'`');
    let mut j = n;
    while j < text.len() {
        let m = run(&text[j..], b'`');
        if m == n {
            let inner = &text[n..j];
            let inner = match inner.strip_prefix(' ').and_then(|s| s.strip_suffix(' ')) {
                Some(s) if !s.trim().is_empty() => s,
                _ => inner,
            };
            let drawn = format!("\x1b[{INK};{LAVENDER}m{inner}\x1b[0;{state}m");
            return (j + n, drawn);
        }
        j += match m {
            0 => text[j..].chars().next().map_or(1, char::len_utf8),
            m => m,
        };
    }
    (n, text[..n].to_owned())
}

fn emphasis(text: &str, before: Option<char>, state: &str) -> Option<(usize, String)> {
    let c = text.as_bytes()[0];
    let n = run(text, c).min(3);
    let mark = &text[..n];
    let word = |ch: Option<char>| ch.is_some_and(char::is_alphanumeric);
    let opens = text[n..]
        .chars()
        .next()
        .is_some_and(|ch| !ch.is_whitespace());
    if !opens || (c == b'_' && word(before)) {
        return Some((n, mark.to_owned()));
    }
    let mut j = n;
    while let Some(k) = text[j..].find(mark) {
        let at = j + k;
        let len = run(&text[at..], c);
        let closes = !text[..at].ends_with(char::is_whitespace)
            && len == n
            && !(c == b'_' && word(text[at + n..].chars().next()));
        if closes && at > n {
            let sgr = ["3", "1", "1;3"][n - 1];
            let inner = format!("{state};{sgr}");
            let drawn = format!(
                "\x1b[0;{inner}m{}\x1b[0;{state}m",
                spans(&text[n..at], &inner)
            );
            return Some((at + n, drawn));
        }
        j = at + len;
    }
    Some((n, mark.to_owned()))
}

fn link(text: &str, state: &str) -> Option<(usize, String)> {
    let close = text.find("](")?;
    let label = &text[1..close];
    let url_len = text[close + 2..].find(')')?;
    let url = &text[close + 2..close + 2 + url_len];
    if label.contains('[') || url.contains(char::is_whitespace) {
        return None;
    }
    let inner = format!("{state};4");
    let drawn = format!(
        "\x1b[0;{inner}m{}\x1b[0;{DIM}m ({url})\x1b[0;{state}m",
        spans(label, &inner)
    );
    Some((close + 3 + url_len, drawn))
}
