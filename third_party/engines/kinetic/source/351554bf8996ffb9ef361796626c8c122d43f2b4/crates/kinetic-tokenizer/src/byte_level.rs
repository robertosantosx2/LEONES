//! The GPT-2 byte-to-character mapping used by byte-level BPE vocabularies.
//!
//! Every byte gets a printable character so that vocabulary entries can be
//! stored as text: printable Latin-1 bytes stand for themselves and the rest
//! are shifted to U+0100 and up, in byte order.

const fn is_printable(b: usize) -> bool {
    matches!(b, 0x21..=0x7E | 0xA1..=0xAC | 0xAE..=0xFF)
}

/// The character that stands for each byte.
pub(crate) const BYTE_CHARS: [char; 256] = {
    let mut table = ['\0'; 256];
    let mut shifted = 0;
    let mut b = 0;
    while b < 256 {
        let code = if is_printable(b) {
            b as u32
        } else {
            shifted += 1;
            255 + shifted
        };
        table[b] = char::from_u32(code).unwrap();
        b += 1;
    }
    table
};

const LAST_CHAR: usize = 0x143;

const CHAR_BYTES: [Option<u8>; LAST_CHAR + 1] = {
    let mut table = [None; LAST_CHAR + 1];
    let mut b = 0;
    while b < 256 {
        table[BYTE_CHARS[b] as usize] = Some(b as u8);
        b += 1;
    }
    table
};

/// The raw bytes behind a vocabulary entry, or `None` if the entry has a
/// character outside the mapping and so can never come out of a merge.
pub(crate) fn decode(text: &str) -> Option<Vec<u8>> {
    text.chars()
        .map(|c| CHAR_BYTES.get(c as usize).copied().flatten())
        .collect()
}

/// Like [`decode`], but keeps unmapped characters as their UTF-8 bytes.
pub(crate) fn decode_lossy(text: &str) -> Vec<u8> {
    let mut out = Vec::with_capacity(text.len());
    for c in text.chars() {
        match CHAR_BYTES.get(c as usize).copied().flatten() {
            Some(b) => out.push(b),
            None => out.extend_from_slice(c.encode_utf8(&mut [0; 4]).as_bytes()),
        }
    }
    out
}
