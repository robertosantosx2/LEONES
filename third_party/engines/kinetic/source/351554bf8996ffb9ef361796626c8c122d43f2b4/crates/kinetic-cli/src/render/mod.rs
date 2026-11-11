//! Answers drawn the way a chat app draws them: Markdown formatted line by
//! line while it streams.

mod code;
mod inline;
mod screen;
mod table;

use std::fmt::Write as _;
use std::io::{self, Write};

use table::Table;

const TEXT: &str = "38;2;232;228;236";
const DIM: &str = "38;2;167;159;176";
const LAVENDER: &str = "38;2;220;213;226";
const PURPLE: &str = "38;2;122;102;136";
const ORANGE: &str = "38;2;221;138;74";
const INK: &str = "48;2;42;39;48";

/// Streams Markdown to a terminal. Each finished line is redrawn formatted;
/// only the line still arriving shows raw. Without colour, text passes
/// through untouched.
#[derive(Default)]
pub struct Markdown {
    color: bool,
    cols: usize,
    rows: usize,
    line: String,
    // raw text of the unfinished line, as printed
    partial: String,
    // a table still being redrawn, as printed
    held: String,
    table: Option<Table>,
    fence: Option<Fence>,
}

struct Fence {
    mark: String,
    indent: usize,
    lang: String,
    in_comment: bool,
}

impl Markdown {
    /// Formats for this terminal when `color` is set.
    pub fn new(color: bool) -> Self {
        let (cols, rows) = screen::size().unwrap_or((80, 24));
        Self::sized(color, cols, rows)
    }

    fn sized(color: bool, cols: usize, rows: usize) -> Self {
        Markdown {
            color,
            cols: cols.max(1),
            rows,
            ..Markdown::default()
        }
    }

    /// Takes the next piece of the answer.
    pub fn write(&mut self, out: &mut impl Write, text: &str) -> io::Result<()> {
        if !self.color {
            return out.write_all(text.as_bytes());
        }
        let mut buf = String::new();
        let mut parts = text.split('\n');
        let last = parts.next_back().unwrap_or_default();
        for part in parts {
            self.line.push_str(part);
            self.end_line(&mut buf, true);
        }
        if !last.is_empty() {
            self.line.push_str(last);
            let shown = last.replace('\t', "    ");
            self.partial.push_str(&shown);
            buf.push_str(&shown);
        }
        out.write_all(buf.as_bytes())
    }

    /// Draws the last line, which came without a line break.
    pub fn finish(&mut self, out: &mut impl Write) -> io::Result<()> {
        let mut buf = String::new();
        if !self.line.is_empty() {
            self.end_line(&mut buf, false);
        }
        *self = Markdown::sized(self.color, self.cols, self.rows);
        out.write_all(buf.as_bytes())
    }

    fn end_line(&mut self, buf: &mut String, newline: bool) {
        let line = std::mem::take(&mut self.line).replace('\t', "    ");
        let row = self.fence.is_none() && line.trim_start().starts_with('|');
        self.erase(buf, row);
        let text = if row {
            let table = self.table.get_or_insert_with(Table::default);
            table.push(&line);
            let text = table.render();
            self.held = format!("{text}\n");
            // rows scrolled off the top can no longer be redrawn
            if screen::rows_up(&self.held, self.cols) + 2 >= self.rows {
                table.settle();
                self.held.clear();
            }
            Some(text)
        } else {
            self.held.clear();
            self.table = None;
            self.draw(&line)
        };
        if let Some(text) = text {
            buf.push_str(&text);
            if newline {
                buf.push('\n');
            }
        }
    }

    /// Moves the cursor back to where the unfinished line, and with `held`
    /// the table above it, began, clearing everything below.
    fn erase(&mut self, buf: &mut String, held: bool) {
        let shown = if held {
            std::mem::take(&mut self.held) + &self.partial
        } else {
            self.partial.clone()
        };
        self.partial.clear();
        if shown.is_empty() {
            return;
        }
        buf.push('\r');
        match screen::rows_up(&shown, self.cols) {
            0 => {}
            up => {
                let _ = write!(buf, "\x1b[{up}A");
            }
        }
        buf.push_str("\x1b[J");
    }

    /// One finished line, formatted; `None` when the line is not shown.
    fn draw(&mut self, line: &str) -> Option<String> {
        let t = line.trim_start();
        let indent = &line[..line.len() - t.len()];
        if let Some(f) = &mut self.fence {
            let closing = t.trim_end();
            if closing.len() >= f.mark.len() && closing.bytes().all(|b| b == f.mark.as_bytes()[0]) {
                self.fence = None;
                return None;
            }
            let code = line
                .get(f.indent..)
                .filter(|_| indent.len() >= f.indent)
                .unwrap_or(t);
            let code = code::highlight(&f.lang, code.trim_end(), &mut f.in_comment);
            return Some(format!("\x1b[{INK}m{code}\x1b[K\x1b[0m"));
        }
        if let Some(fence) = open_fence(t, indent.len()) {
            let label = (!fence.lang.is_empty())
                .then(|| format!("\x1b[{INK};{DIM}m{}\x1b[K\x1b[0m", fence.lang));
            self.fence = Some(fence);
            return label;
        }
        if t.is_empty() {
            return Some(String::new());
        }
        let hashes = t.bytes().take_while(|&b| b == b'#').count();
        if (1..=6).contains(&hashes) && t[hashes..].chars().next().is_none_or(|c| c == ' ') {
            let title = t[hashes..].trim().trim_end_matches('#').trim_end();
            let color = if hashes <= 2 { TEXT } else { LAVENDER };
            return Some(inline::render(title, &format!("1;{color}")));
        }
        let bare: String = t.chars().filter(|c| *c != ' ').collect();
        let first = bare.chars().next().filter(|c| matches!(c, '-' | '*' | '_'));
        if bare.len() >= 3 && bare.chars().all(|c| Some(c) == first) {
            let rule = "─".repeat(self.cols.min(40));
            return Some(format!("{indent}\x1b[{PURPLE}m{rule}\x1b[0m"));
        }
        if t.starts_with('>') {
            let rest = t.trim_start_matches(['>', ' ']);
            let depth = t.len() - rest.len();
            let bars = t[..depth].matches('>').count();
            let bar = format!("\x1b[{PURPLE}m{}\x1b[0m", "│ ".repeat(bars));
            return Some(format!("{indent}{bar}{}", inline::render(rest, LAVENDER)));
        }
        if let Some(rest) = t
            .strip_prefix(['-', '*', '+'])
            .and_then(|r| r.strip_prefix(' '))
        {
            return Some(format!(
                "{indent}\x1b[{DIM}m-\x1b[0m {}",
                inline::render(rest, TEXT)
            ));
        }
        let digits = t.bytes().take_while(u8::is_ascii_digit).count();
        if (1..=9).contains(&digits)
            && matches!(t.as_bytes().get(digits), Some(b'.' | b')'))
            && t.as_bytes().get(digits + 1) == Some(&b' ')
        {
            let (number, rest) = t.split_at(digits + 1);
            return Some(format!(
                "{indent}\x1b[{DIM}m{number}\x1b[0m {}",
                inline::render(&rest[1..], TEXT)
            ));
        }
        Some(inline::render(line, TEXT))
    }
}

fn open_fence(t: &str, indent: usize) -> Option<Fence> {
    let c = *t.as_bytes().first().filter(|c| matches!(c, b'`' | b'~'))?;
    let n = t.bytes().take_while(|&b| b == c).count();
    let info = &t[n..];
    if n < 3 || (c == b'`' && info.contains('`')) {
        return None;
    }
    Some(Fence {
        mark: t[..n].to_owned(),
        indent,
        lang: info.split_whitespace().next().unwrap_or("").to_lowercase(),
        in_comment: false,
    })
}

#[cfg(test)]
mod tests;
