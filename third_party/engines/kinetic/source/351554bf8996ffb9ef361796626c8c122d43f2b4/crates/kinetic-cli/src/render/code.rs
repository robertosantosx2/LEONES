use std::fmt::Write;

use super::{DIM, LAVENDER, ORANGE, TEXT};

struct Syntax {
    words: &'static [&'static str],
    line: &'static [&'static str],
    block: Option<(&'static str, &'static str)>,
    quotes: &'static str,
    nocase: bool,
    // css properties and html attributes are words with dashes
    dashes: bool,
    tags: bool,
    lifetimes: bool,
}

const PLAIN: Syntax = Syntax {
    words: &[],
    line: &[],
    block: None,
    quotes: "\"'",
    nocase: false,
    dashes: false,
    tags: false,
    lifetimes: false,
};

const C_COMMENTS: Syntax = Syntax {
    line: &["//"],
    block: Some(("/*", "*/")),
    ..PLAIN
};

fn syntax(lang: &str) -> Option<Syntax> {
    Some(match lang {
        "rust" | "rs" => Syntax {
            words: &[
                "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else",
                "enum", "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop", "match",
                "mod", "move", "mut", "pub", "ref", "return", "self", "Self", "static", "struct",
                "super", "trait", "true", "type", "unsafe", "use", "where", "while", "Some",
                "None", "Ok", "Err",
            ],
            lifetimes: true,
            ..C_COMMENTS
        },
        "python" | "py" => Syntax {
            words: &[
                "and", "as", "assert", "async", "await", "break", "class", "continue", "def",
                "del", "elif", "else", "except", "False", "finally", "for", "from", "global", "if",
                "import", "in", "is", "lambda", "None", "nonlocal", "not", "or", "pass", "raise",
                "return", "True", "try", "while", "with", "yield", "self",
            ],
            line: &["#"],
            ..PLAIN
        },
        "javascript" | "js" | "jsx" | "typescript" | "ts" | "tsx" | "mjs" => Syntax {
            words: &[
                "as",
                "async",
                "await",
                "break",
                "case",
                "catch",
                "class",
                "const",
                "continue",
                "default",
                "delete",
                "do",
                "else",
                "enum",
                "export",
                "extends",
                "false",
                "finally",
                "for",
                "from",
                "function",
                "if",
                "implements",
                "import",
                "in",
                "instanceof",
                "interface",
                "let",
                "new",
                "null",
                "of",
                "private",
                "protected",
                "public",
                "readonly",
                "return",
                "static",
                "super",
                "switch",
                "this",
                "throw",
                "true",
                "try",
                "type",
                "typeof",
                "undefined",
                "var",
                "void",
                "while",
                "yield",
            ],
            quotes: "\"'`",
            ..C_COMMENTS
        },
        "json" | "jsonc" => Syntax {
            words: &["true", "false", "null"],
            quotes: "\"",
            ..C_COMMENTS
        },
        "html" | "xml" | "svg" | "vue" => Syntax {
            block: Some(("<!--", "-->")),
            dashes: true,
            tags: true,
            ..PLAIN
        },
        "css" | "scss" | "less" => Syntax {
            dashes: true,
            ..C_COMMENTS
        },
        "c" | "h" | "cpp" | "c++" | "cc" | "cxx" | "hpp" => Syntax {
            words: &[
                "auto",
                "bool",
                "break",
                "case",
                "char",
                "class",
                "const",
                "constexpr",
                "continue",
                "default",
                "define",
                "delete",
                "do",
                "double",
                "else",
                "enum",
                "extern",
                "false",
                "float",
                "for",
                "if",
                "include",
                "inline",
                "int",
                "long",
                "namespace",
                "new",
                "nullptr",
                "override",
                "private",
                "protected",
                "public",
                "return",
                "short",
                "signed",
                "sizeof",
                "static",
                "struct",
                "switch",
                "template",
                "this",
                "true",
                "typedef",
                "typename",
                "union",
                "unsigned",
                "using",
                "virtual",
                "void",
                "volatile",
                "while",
            ],
            ..C_COMMENTS
        },
        "go" | "golang" => Syntax {
            words: &[
                "break",
                "case",
                "chan",
                "const",
                "continue",
                "default",
                "defer",
                "else",
                "fallthrough",
                "false",
                "for",
                "func",
                "go",
                "goto",
                "if",
                "import",
                "interface",
                "map",
                "nil",
                "package",
                "range",
                "return",
                "select",
                "struct",
                "switch",
                "true",
                "type",
                "var",
            ],
            quotes: "\"'`",
            ..C_COMMENTS
        },
        "bash" | "sh" | "shell" | "zsh" | "console" => Syntax {
            words: &[
                "case", "do", "done", "echo", "elif", "else", "esac", "exit", "export", "fi",
                "for", "function", "if", "in", "local", "return", "then", "until", "while",
            ],
            line: &["#"],
            ..PLAIN
        },
        "powershell" | "ps1" | "pwsh" | "ps" => Syntax {
            words: &[
                "begin", "break", "catch", "continue", "do", "else", "elseif", "end", "exit",
                "finally", "for", "foreach", "function", "if", "in", "param", "process", "return",
                "switch", "throw", "try", "while",
            ],
            line: &["#"],
            block: Some(("<#", "#>")),
            nocase: true,
            ..PLAIN
        },
        "sql" | "sqlite" | "postgresql" | "mysql" => Syntax {
            words: &[
                "all",
                "alter",
                "and",
                "as",
                "asc",
                "by",
                "case",
                "create",
                "default",
                "delete",
                "desc",
                "distinct",
                "drop",
                "else",
                "end",
                "exists",
                "foreign",
                "from",
                "group",
                "having",
                "in",
                "index",
                "inner",
                "insert",
                "into",
                "is",
                "join",
                "key",
                "left",
                "limit",
                "not",
                "null",
                "offset",
                "on",
                "or",
                "order",
                "outer",
                "primary",
                "references",
                "right",
                "select",
                "set",
                "table",
                "then",
                "union",
                "update",
                "values",
                "when",
                "where",
                "with",
            ],
            line: &["--"],
            block: Some(("/*", "*/")),
            nocase: true,
            ..PLAIN
        },
        _ => return None,
    })
}

/// One line of code in `lang` with keywords, strings, numbers and comments
/// coloured; `in_comment` carries a block comment over to the next line.
pub fn highlight(lang: &str, line: &str, in_comment: &mut bool) -> String {
    let mut out = format!("\x1b[{TEXT}m");
    let Some(s) = syntax(lang) else {
        out.push_str(line);
        return out;
    };
    let ident = |c: char| c.is_alphanumeric() || c == '_' || (s.dashes && c == '-');
    let (mut i, mut in_tag) = (0, false);
    while i < line.len() {
        let rest = &line[i..];
        let prev = line[..i].chars().next_back();
        let c = rest.chars().next().unwrap_or_default();
        if let Some((open, close)) = s.block {
            let from = if *in_comment {
                Some(0)
            } else {
                rest.starts_with(open).then_some(open.len())
            };
            if let Some(from) = from {
                let n = rest[from..].find(close).map(|k| from + k + close.len());
                *in_comment = n.is_none();
                let n = n.unwrap_or(rest.len());
                paint(&mut out, "3;", DIM, &rest[..n]);
                i += n;
                continue;
            }
        }
        let comment = s.line.iter().any(|m| rest.starts_with(m))
            && (c != '#' || prev.is_none_or(char::is_whitespace));
        if comment {
            paint(&mut out, "3;", DIM, rest);
            break;
        }
        let n = if s.quotes.contains(c)
            && (!s.tags || in_tag)
            && !(s.lifetimes && c == '\'' && lifetime(rest))
        {
            paint(&mut out, "", LAVENDER, &rest[..quoted(rest, c)]);
            quoted(rest, c)
        } else if c.is_ascii_digit() && !prev.is_some_and(ident) {
            let n = rest
                .find(|ch: char| !(ch.is_alphanumeric() || ch == '.' || ch == '_'))
                .unwrap_or(rest.len());
            paint(&mut out, "", LAVENDER, &rest[..n]);
            n
        } else if c.is_alphabetic() || c == '_' {
            let n = rest.find(|ch| !ident(ch)).unwrap_or(rest.len());
            let word = &rest[..n];
            let key = if s.tags {
                in_tag && matches!(prev, Some('<' | '/'))
            } else if s.nocase {
                s.words.iter().any(|w| w.eq_ignore_ascii_case(word))
            } else {
                s.words.contains(&word)
            };
            if key {
                paint(&mut out, "", ORANGE, word);
            } else {
                out.push_str(word);
            }
            n
        } else {
            in_tag = match c {
                '<' => s.tags,
                '>' => false,
                _ => in_tag,
            };
            out.push(c);
            c.len_utf8()
        };
        i += n;
    }
    out
}

fn paint(out: &mut String, extra: &str, color: &str, token: &str) {
    let _ = write!(out, "\x1b[{extra}{color}m{token}\x1b[23;{TEXT}m");
}

fn quoted(text: &str, quote: char) -> usize {
    let mut chars = text.char_indices().skip(1);
    while let Some((i, c)) = chars.next() {
        match c {
            '\\' => {
                chars.next();
            }
            c if c == quote => return i + 1,
            _ => {}
        }
    }
    text.len()
}

// 'a in rust is a lifetime unless it closes like 'a' or '\n'
fn lifetime(text: &str) -> bool {
    let mut chars = text.chars().skip(1);
    match chars.next() {
        Some('\\') | None => false,
        Some(_) => chars.next() != Some('\''),
    }
}
