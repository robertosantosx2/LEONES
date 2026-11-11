//! Finds special tokens written out in the input text.

/// A run of input: plain text for BPE, or a special token found in it.
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Segment<'t> {
    Text(&'t str),
    Token(u32),
}

struct Special {
    text: Box<str>,
    id: u32,
    /// Control tokens are only recognised when special parsing is on;
    /// user-defined tokens always are.
    control: bool,
}

pub(crate) struct Specials {
    /// Longest first, which decides overlaps.
    tokens: Vec<Special>,
    /// Indices into `tokens` by first byte, in `tokens` order.
    by_first_byte: Vec<Vec<usize>>,
}

impl Specials {
    /// Takes `(text, id, control)` for every special token.
    pub(crate) fn new(tokens: impl IntoIterator<Item = (String, u32, bool)>) -> Specials {
        let mut tokens: Vec<Special> = tokens
            .into_iter()
            .filter(|(text, ..)| !text.is_empty())
            .map(|(text, id, control)| Special {
                text: text.into(),
                id,
                control,
            })
            .collect();
        tokens.sort_by(|a, b| b.text.len().cmp(&a.text.len()).then(a.id.cmp(&b.id)));
        let mut by_first_byte = vec![Vec::new(); 256];
        for (i, t) in tokens.iter().enumerate() {
            by_first_byte[usize::from(t.text.as_bytes()[0])].push(i);
        }
        Specials {
            tokens,
            by_first_byte,
        }
    }

    /// Splits `text` the way the reference does: each special token, longest
    /// first, claims its leftmost non-overlapping occurrences in the text not
    /// yet claimed by a longer one.
    pub(crate) fn split<'t>(&self, text: &'t str, parse_special: bool) -> Vec<Segment<'t>> {
        let bytes = text.as_bytes();
        let mut found = Vec::new();
        for (pos, &b) in bytes.iter().enumerate() {
            for &i in &self.by_first_byte[usize::from(b)] {
                let t = &self.tokens[i];
                if (parse_special || !t.control) && bytes[pos..].starts_with(t.text.as_bytes()) {
                    found.push((i, pos));
                }
            }
        }
        if found.is_empty() {
            return if text.is_empty() {
                Vec::new()
            } else {
                vec![Segment::Text(text)]
            };
        }

        found.sort_unstable();
        let mut claimed = vec![false; bytes.len()];
        let mut taken = Vec::new();
        for (i, pos) in found {
            let span = pos..pos + self.tokens[i].text.len();
            if !claimed[span.clone()].contains(&true) {
                claimed[span.clone()].fill(true);
                taken.push((pos, i));
            }
        }
        taken.sort_unstable();

        let mut segments = Vec::with_capacity(2 * taken.len() + 1);
        let mut start = 0;
        for (pos, i) in taken {
            if pos > start {
                segments.push(Segment::Text(&text[start..pos]));
            }
            segments.push(Segment::Token(self.tokens[i].id));
            start = pos + self.tokens[i].text.len();
        }
        if start < text.len() {
            segments.push(Segment::Text(&text[start..]));
        }
        segments
    }
}
