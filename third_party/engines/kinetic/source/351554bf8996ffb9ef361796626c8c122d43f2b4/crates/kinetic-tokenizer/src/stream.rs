use crate::Tokenizer;

/// Turns tokens into text one at a time, as they are generated.
///
/// A token can end in the middle of a multi-byte character, so bytes are
/// held back until the character is complete. Every chunk is valid UTF-8 and
/// the chunks concatenate to what [`Tokenizer::decode`] gives for the same
/// ids.
pub struct StreamDecoder<'a> {
    tokenizer: &'a Tokenizer,
    pending: Vec<u8>,
}

impl<'a> StreamDecoder<'a> {
    pub(crate) fn new(tokenizer: &'a Tokenizer) -> Self {
        StreamDecoder {
            tokenizer,
            pending: Vec::new(),
        }
    }

    /// Adds one token and returns the text it completes, which may be empty.
    pub fn push(&mut self, id: u32) -> String {
        self.pending.extend_from_slice(self.tokenizer.piece(id));
        let mut out = String::new();
        let mut rest = self.pending.as_slice();
        loop {
            match std::str::from_utf8(rest) {
                Ok(text) => {
                    out.push_str(text);
                    rest = &[];
                    break;
                }
                Err(e) => {
                    let (valid, tail) = rest.split_at(e.valid_up_to());
                    out.push_str(std::str::from_utf8(valid).expect("checked by from_utf8"));
                    match e.error_len() {
                        Some(bad) => {
                            out.push(char::REPLACEMENT_CHARACTER);
                            rest = &tail[bad..];
                        }
                        None => {
                            rest = tail;
                            break;
                        }
                    }
                }
            }
        }
        let keep = rest.len();
        self.pending.drain(..self.pending.len() - keep);
        out
    }

    /// Returns whatever is still held back, with an unfinished character
    /// shown as U+FFFD.
    pub fn finish(self) -> String {
        String::from_utf8_lossy(&self.pending).into_owned()
    }
}
