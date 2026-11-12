//! Incremental processing of generated text: stop strings and reasoning.
//!
//! Text arrives in arbitrary pieces, so both stages hold back a tail that
//! could still turn into a stop string or a tag.

const THINK_OPEN: &str = "<think>";
const THINK_CLOSE: &str = "</think>";
/// Reasoning tags: `<think>` and Gemma 4's thought channel.
const THINK_TAGS: [(&str, &str); 2] = [
    (THINK_OPEN, THINK_CLOSE),
    ("<|channel>thought", "<channel|>"),
];

/// Ends the output at the first of a set of stop strings.
pub struct StopStrings {
    stops: Vec<String>,
    pending: String,
}

impl StopStrings {
    pub fn new(stops: &[String]) -> Self {
        StopStrings {
            stops: stops.iter().filter(|s| !s.is_empty()).cloned().collect(),
            pending: String::new(),
        }
    }

    /// Adds `text` and returns what is now certain to be output, and whether
    /// a stop string was reached, in which case nothing more should be added.
    pub fn push(&mut self, text: &str) -> (String, bool) {
        self.pending.push_str(text);
        let hit = self
            .stops
            .iter()
            .filter_map(|s| self.pending.find(s.as_str()))
            .min();
        if let Some(at) = hit {
            self.pending.truncate(at);
            return (std::mem::take(&mut self.pending), true);
        }
        let hold = self
            .stops
            .iter()
            .map(|s| partial_suffix(&self.pending, s))
            .max()
            .unwrap_or(0);
        let rest = self.pending.split_off(self.pending.len() - hold);
        (std::mem::replace(&mut self.pending, rest), false)
    }

    /// Whatever was held back, once the output has ended.
    pub fn finish(self) -> String {
        self.pending
    }
}

/// Text split into the model's reasoning and its answer.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct Split {
    pub reasoning: String,
    pub content: String,
}

impl Split {
    pub fn is_empty(&self) -> bool {
        self.reasoning.is_empty() && self.content.is_empty()
    }
}

/// Routes text between `<think>` and `</think>`, or inside Gemma 4's
/// thought channel, to the reasoning and the rest to the content, dropping
/// the tags and the blank space after them.
pub struct ThinkSplitter {
    /// The close tag awaited inside a reasoning block.
    thinking: Option<&'static str>,
    /// Whitespace at the start of a part is dropped until text arrives.
    at_start: bool,
    pending: String,
}

impl ThinkSplitter {
    /// `thinking` says whether the prompt left a `<think>` block open.
    pub fn new(thinking: bool) -> Self {
        ThinkSplitter {
            thinking: thinking.then_some(THINK_CLOSE),
            at_start: true,
            pending: String::new(),
        }
    }

    pub fn push(&mut self, text: &str) -> Split {
        self.pending.push_str(text);
        let mut out = Split::default();
        // with reasoning off some models still open the answer with a bare
        // closing tag; it is not part of the answer
        if self.thinking.is_none() && self.at_start {
            let rest = self.pending.trim_start();
            if let Some(after) = rest.strip_prefix(THINK_CLOSE) {
                self.pending = after.to_owned();
            } else if !rest.is_empty() && THINK_CLOSE.starts_with(rest) {
                return out;
            }
        }
        loop {
            let found = match self.thinking {
                Some(close) => self.pending.find(close).map(|at| (at, close, None)),
                None => THINK_TAGS
                    .iter()
                    .filter_map(|&(open, close)| {
                        self.pending.find(open).map(|at| (at, open, Some(close)))
                    })
                    .min_by_key(|&(at, ..)| at),
            };
            match found {
                Some((at, tag, next)) => {
                    let rest = self.pending.split_off(at + tag.len());
                    self.pending.truncate(at);
                    let part = std::mem::replace(&mut self.pending, rest);
                    self.emit(&part, &mut out);
                    self.thinking = next;
                    self.at_start = true;
                }
                None => {
                    let hold = match self.thinking {
                        Some(close) => partial_suffix(&self.pending, close),
                        None => THINK_TAGS
                            .iter()
                            .map(|&(open, _)| partial_suffix(&self.pending, open))
                            .max()
                            .unwrap_or(0),
                    };
                    let rest = self.pending.split_off(self.pending.len() - hold);
                    let part = std::mem::replace(&mut self.pending, rest);
                    self.emit(&part, &mut out);
                    return out;
                }
            }
        }
    }

    /// Whatever was held back, once the output has ended.
    pub fn finish(&mut self) -> Split {
        let mut out = Split::default();
        let part = std::mem::take(&mut self.pending);
        self.emit(&part, &mut out);
        out
    }

    fn emit(&mut self, mut part: &str, out: &mut Split) {
        if self.at_start {
            part = part.trim_start();
            self.at_start = part.is_empty();
        }
        let target = if self.thinking.is_some() {
            &mut out.reasoning
        } else {
            &mut out.content
        };
        target.push_str(part);
    }
}

/// Length of the longest proper suffix of `text` that starts `pattern`.
pub(crate) fn partial_suffix(text: &str, pattern: &str) -> usize {
    (1..pattern.len().min(text.len() + 1))
        .rev()
        .find(|&n| {
            text.is_char_boundary(text.len() - n) && pattern.starts_with(&text[text.len() - n..])
        })
        .unwrap_or(0)
}

/// Whether a prompt ends inside a `<think>` block, so the output starts as
/// reasoning.
pub fn opens_thinking(prompt: &str) -> bool {
    match (prompt.rfind(THINK_OPEN), prompt.rfind(THINK_CLOSE)) {
        (Some(open), Some(close)) => open > close,
        (open, _) => open.is_some(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn feed_stops(stops: &[&str], pieces: &[&str]) -> (String, bool) {
        let stops: Vec<String> = stops.iter().map(|s| s.to_string()).collect();
        let mut s = StopStrings::new(&stops);
        let mut out = String::new();
        for p in pieces {
            let (text, hit) = s.push(p);
            out += &text;
            if hit {
                return (out, true);
            }
        }
        out += &s.finish();
        (out, false)
    }

    #[test]
    fn stop_string_split_across_pieces() {
        assert_eq!(
            feed_stops(&["END"], &["abc E", "N", "Dxyz"]),
            ("abc ".into(), true)
        );
    }

    #[test]
    fn false_start_of_a_stop_string_is_released() {
        assert_eq!(
            feed_stops(&["END"], &["E", "N", "x"]),
            ("ENx".into(), false)
        );
    }

    #[test]
    fn earliest_stop_string_wins() {
        assert_eq!(
            feed_stops(&["world", "lo"], &["hello world"]),
            ("hel".into(), true)
        );
    }

    #[test]
    fn held_text_is_released_as_soon_as_it_cannot_match() {
        let stops = vec!["\n\n".to_string()];
        let mut s = StopStrings::new(&stops);
        assert_eq!(s.push("a\n"), ("a".into(), false));
        assert_eq!(s.push("b"), ("\nb".into(), false));
    }

    #[test]
    fn multibyte_text_is_never_split() {
        assert_eq!(partial_suffix("zażółć", "ćx"), 2);
        assert_eq!(partial_suffix("ąb", "\u{105}"), 0);
    }

    #[test]
    fn a_bare_closing_tag_before_the_answer_is_dropped() {
        let s = feed_think(false, &["</thi", "nk>\n\nHello"]);
        assert_eq!((s.reasoning.as_str(), s.content.as_str()), ("", "Hello"));
        let s = feed_think(false, &["Use </think> in text"]);
        assert_eq!(s.content, "Use </think> in text");
    }

    #[test]
    fn gemma_thought_channel_is_reasoning() {
        let s = feed_think(false, &["<|channel>thought", " plan<chan", "nel|>Hi"]);
        assert_eq!((s.reasoning.as_str(), s.content.as_str()), ("plan", "Hi"));
    }

    fn feed_think(thinking: bool, pieces: &[&str]) -> Split {
        let mut t = ThinkSplitter::new(thinking);
        let mut out = Split::default();
        for p in pieces {
            let s = t.push(p);
            out.reasoning += &s.reasoning;
            out.content += &s.content;
        }
        let s = t.finish();
        out.reasoning += &s.reasoning;
        out.content += &s.content;
        out
    }

    #[test]
    fn reasoning_is_separated_from_content() {
        let s = feed_think(
            false,
            &["<thi", "nk>\nLet me", " see.\n</th", "ink>\n\nParis."],
        );
        assert_eq!(s.reasoning, "Let me see.\n");
        assert_eq!(s.content, "Paris.");
    }

    #[test]
    fn prompt_can_open_the_reasoning() {
        let s = feed_think(true, &["hmm</think>", "\n\nYes"]);
        assert_eq!((s.reasoning.as_str(), s.content.as_str()), ("hmm", "Yes"));
    }

    #[test]
    fn plain_text_passes_through() {
        let s = feed_think(false, &["a < b", " and <t", "ag>"]);
        assert_eq!(s.content, "a < b and <tag>");
        assert!(s.reasoning.is_empty());
    }

    #[test]
    fn detects_an_open_think_block() {
        assert!(opens_thinking("<|im_start|>assistant\n<think>\n"));
        assert!(!opens_thinking(
            "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        ));
        assert!(!opens_thinking("<|im_start|>assistant\n"));
    }
}
