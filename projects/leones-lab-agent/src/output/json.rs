use std::fmt::Write;

pub fn escape(input: &str) -> String {
    let mut out = String::with_capacity(input.len() + 2);
    out.push('"');
    for ch in input.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c <= '\u{001f}' => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn optional_string(value: Option<&str>) -> String {
    value.map(escape).unwrap_or_else(|| "null".to_string())
}

#[cfg(test)]
mod tests {
    use super::escape;

    #[test]
    fn escapes_json_control_characters() {
        assert_eq!(escape("a\"b\\c\n"), "\"a\\\"b\\\\c\\n\"");
    }

    #[test]
    fn escapes_low_control_characters() {
        assert_eq!(escape("\u{0001}"), "\"\\u0001\"");
    }

    #[test]
    fn preserves_unicode() {
        assert_eq!(escape("Ponferrada — GPU"), "\"Ponferrada — GPU\"");
    }
}
