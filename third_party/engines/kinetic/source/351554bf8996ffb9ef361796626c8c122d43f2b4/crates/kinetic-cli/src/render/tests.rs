use super::{code, Markdown, DIM, LAVENDER, ORANGE};

const SAMPLE: &str = "# Title
Some **bold** and *italic* and `code` in a long line that wraps.

- one
  - two
1. first

> quoted

---
See [docs](https://x.y).

| Name | Value |
|------|------:|
| a | 1 |
| longer | 22 |

```rust
fn main() {}
```
Done.";

/// What a terminal `cols` wide shows after `out`, colours dropped.
fn screen(out: &str, cols: usize) -> Vec<String> {
    let mut rows: Vec<Vec<char>> = vec![Vec::new()];
    let (mut r, mut c) = (0, 0);
    let mut chars = out.chars();
    while let Some(ch) = chars.next() {
        match ch {
            '\x1b' => {
                assert_eq!(chars.next(), Some('['));
                let mut arg = String::new();
                let end = chars.by_ref().find(|x| {
                    let end = ('\x40'..='\x7e').contains(x);
                    if !end {
                        arg.push(*x);
                    }
                    end
                });
                match end {
                    Some('A') => r -= arg.parse::<usize>().unwrap(),
                    Some('J') => {
                        rows[r].truncate(c);
                        rows.truncate(r + 1);
                    }
                    Some('K') => rows[r].truncate(c),
                    _ => {}
                }
            }
            '\r' => c = 0,
            '\n' => {
                (r, c) = (r + 1, 0);
                rows.resize(rows.len().max(r + 1), Vec::new());
            }
            _ => {
                // the cursor rests on a full row until the next char arrives
                if c == cols {
                    (r, c) = (r + 1, 0);
                    rows.resize(rows.len().max(r + 1), Vec::new());
                }
                let row = &mut rows[r];
                row.resize(row.len().max(c + 1), ' ');
                row[c] = ch;
                c += 1;
            }
        }
    }
    rows.iter()
        .map(|r| r.iter().collect::<String>().trim_end().to_owned())
        .collect()
}

fn draw(chunks: &[&str], cols: usize, rows: usize) -> Vec<String> {
    let mut md = Markdown::sized(true, cols, rows);
    let mut out = Vec::new();
    for chunk in chunks {
        md.write(&mut out, chunk).unwrap();
    }
    md.finish(&mut out).unwrap();
    screen(&String::from_utf8(out).unwrap(), cols)
}

#[test]
fn blocks_look_like_a_chat_app() {
    let rule = "─".repeat(40);
    let expected = [
        "Title",
        "Some bold and italic and code in a long line that wraps.",
        "",
        "- one",
        "  - two",
        "1. first",
        "",
        "│ quoted",
        "",
        &rule,
        "See docs (https://x.y).",
        "",
        " Name     Value",
        " a            1",
        " longer      22",
        "",
        "rust",
        "fn main() {}",
        "Done.",
    ];
    assert_eq!(draw(&[SAMPLE], 100, 50), expected);
}

#[test]
fn awkward_chunks_draw_the_same_screen() {
    for cols in [100, 17] {
        let whole = draw(&[SAMPLE], cols, 50);
        let cuts = (1..SAMPLE.len()).filter(|&i| SAMPLE.is_char_boundary(i));
        for i in cuts {
            assert_eq!(
                draw(&[&SAMPLE[..i], &SAMPLE[i..]], cols, 50),
                whole,
                "cut at {i}"
            );
        }
        for size in [1, 2, 3, 7] {
            let chars: Vec<char> = SAMPLE.chars().collect();
            let chunks: Vec<String> = chars.chunks(size).map(|c| c.iter().collect()).collect();
            let chunks: Vec<&str> = chunks.iter().map(String::as_str).collect();
            assert_eq!(draw(&chunks, cols, 50), whole, "chunks of {size}");
        }
    }
}

#[test]
fn without_colour_the_text_is_untouched() {
    let mut md = Markdown::sized(false, 80, 24);
    let mut out = Vec::new();
    for chunk in ["# Ti", "tle\n**b", "old**\n```", "rust\n"] {
        md.write(&mut out, chunk).unwrap();
    }
    md.finish(&mut out).unwrap();
    assert_eq!(out, b"# Title\n**bold**\n```rust\n");
}

#[test]
fn unclosed_marks_stay_literal() {
    let lines = draw(
        &[
            "**open and `tick and *star\n",
            "2 * 3 * 4 and snake_case_name",
        ],
        80,
        24,
    );
    assert_eq!(
        lines,
        [
            "**open and `tick and *star",
            "2 * 3 * 4 and snake_case_name"
        ]
    );
}

#[test]
fn a_table_taller_than_the_screen_keeps_every_row() {
    let mut text = String::from("| k | v |\n|---|---|\n");
    for i in 0..10 {
        text += &format!("| {i} | {} |\n", "x".repeat(i));
    }
    let lines = draw(&[&text], 80, 6);
    assert_eq!(lines.len(), 12);
    assert_eq!(lines[0], " k   v");
    assert_eq!(lines[10], " 9   xxxxxxxxx");
}

#[test]
fn code_is_coloured_by_language() {
    let mut open = false;
    let line = code::highlight("rust", "let s = \"x\"; // hi", &mut open);
    assert!(line.contains(&format!("{ORANGE}mlet")));
    assert!(line.contains(&format!("{LAVENDER}m\"x\"")));
    assert!(line.contains(&format!("3;{DIM}m// hi")));

    let line = code::highlight("rust", "fn f<'a>(x: &'a str) -> char { 'c' }", &mut open);
    assert!(line.contains(&format!("{LAVENDER}m'c'")));
    assert!(!line.contains(&format!("{LAVENDER}m'a")));

    code::highlight("c", "int x; /* a", &mut open);
    assert!(open);
    let line = code::highlight("c", "b */ int y = 0x1F;", &mut open);
    assert!(!open);
    assert!(line.contains(&format!("3;{DIM}mb */")));
    assert!(line.contains(&format!("{ORANGE}mint")));
    assert!(line.contains(&format!("{LAVENDER}m0x1F")));

    let line = code::highlight("bash", "echo $# # note", &mut open);
    assert!(line.contains(&format!("3;{DIM}m# note")));
    assert!(!line.contains(&format!("{DIM}m# #")));
}
