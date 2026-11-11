use super::{inline, screen, INK, TEXT};

const GAP: &str = "   ";

#[derive(Clone, Copy, Default)]
enum Align {
    #[default]
    Left,
    Center,
    Right,
}

/// The rows of a table seen so far, redrawn whole as each row arrives so
/// the columns stay aligned.
#[derive(Default)]
pub struct Table {
    rows: Vec<Vec<String>>,
    align: Vec<Align>,
    // widths of rows already left on screen, which can no longer be redrawn
    floor: Vec<usize>,
    headed: bool,
}

impl Table {
    /// Takes one `| a | b |` line; the `|---|` rule only sets alignment.
    pub fn push(&mut self, line: &str) {
        let cells = cells(line);
        let rule = |c: &String| {
            let c = c.trim().trim_start_matches(':').trim_end_matches(':');
            !c.is_empty() && c.bytes().all(|b| b == b'-')
        };
        if cells.iter().all(rule) {
            self.align = cells.iter().map(|c| align(c.trim())).collect();
        } else {
            self.rows.push(cells);
        }
    }

    /// Keeps the rows drawn so far on screen for good; later rows are drawn
    /// at least as wide.
    pub fn settle(&mut self) {
        self.floor = self.widths(&self.drawn());
        self.headed |= !self.rows.is_empty();
        self.rows.clear();
    }

    fn drawn(&self) -> Vec<Vec<String>> {
        self.rows
            .iter()
            .enumerate()
            .map(|(i, row)| {
                let base = if self.header(i) {
                    format!("1;{TEXT};{INK}")
                } else {
                    TEXT.to_owned()
                };
                row.iter()
                    .map(|c| inline::render(c.trim(), &base))
                    .collect()
            })
            .collect()
    }

    fn header(&self, row: usize) -> bool {
        row == 0 && !self.headed
    }

    fn widths(&self, drawn: &[Vec<String>]) -> Vec<usize> {
        let mut widths = self.floor.clone();
        for row in drawn {
            if widths.len() < row.len() {
                widths.resize(row.len(), 0);
            }
            for (w, cell) in widths.iter_mut().zip(row) {
                *w = (*w).max(screen::width(cell));
            }
        }
        widths
    }

    /// The table so far, rows separated by line breaks, none after the last.
    pub fn render(&self) -> String {
        let drawn = self.drawn();
        let widths = self.widths(&drawn);
        let lines: Vec<String> = drawn
            .iter()
            .enumerate()
            .map(|(i, row)| {
                let fill = if self.header(i) {
                    format!("\x1b[{INK}m")
                } else {
                    String::new()
                };
                let cells: Vec<String> = widths
                    .iter()
                    .enumerate()
                    .map(|(c, &w)| {
                        let cell = row.get(c).map_or("", String::as_str);
                        let pad = w - screen::width(cell);
                        let (l, r) = match self.align.get(c).copied().unwrap_or_default() {
                            Align::Left => (0, pad),
                            Align::Center => (pad / 2, pad - pad / 2),
                            Align::Right => (pad, 0),
                        };
                        format!("{fill}{}{cell}{fill}{}", " ".repeat(l), " ".repeat(r))
                    })
                    .collect();
                format!(
                    "{fill} {} {fill}\x1b[0m",
                    cells.join(&format!("{fill}{GAP}"))
                )
            })
            .collect();
        lines.join("\n")
    }
}

fn align(rule: &str) -> Align {
    match (rule.starts_with(':'), rule.ends_with(':')) {
        (true, true) => Align::Center,
        (false, true) => Align::Right,
        _ => Align::Left,
    }
}

fn cells(line: &str) -> Vec<String> {
    let line = line.trim();
    let line = line.strip_prefix('|').unwrap_or(line);
    let line = match line.strip_suffix('|') {
        Some(l) if !l.ends_with('\\') => l,
        _ => line,
    };
    let mut cells = vec![String::new()];
    let mut escaped = false;
    for c in line.chars() {
        if c == '|' && !escaped {
            cells.push(String::new());
        } else if let Some(cell) = cells.last_mut() {
            cell.push(c);
        }
        escaped = c == '\\' && !escaped;
    }
    cells
}
