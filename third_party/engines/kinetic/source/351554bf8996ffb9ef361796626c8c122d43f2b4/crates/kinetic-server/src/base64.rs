//! Standard base64, for embedding vectors out and image data URLs in.

const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

pub fn encode(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let b = [
            chunk[0],
            *chunk.get(1).unwrap_or(&0),
            *chunk.get(2).unwrap_or(&0),
        ];
        let n = u32::from(b[0]) << 16 | u32::from(b[1]) << 8 | u32::from(b[2]);
        for (i, shift) in [18, 12, 6, 0].into_iter().enumerate() {
            out.push(if i <= chunk.len() {
                TABLE[(n >> shift) as usize & 63] as char
            } else {
                '='
            });
        }
    }
    out
}

/// The bytes of `text`, or `None` if it is not base64. Padding is optional
/// and line breaks are skipped, as MIME writes them.
pub fn decode(text: &str) -> Option<Vec<u8>> {
    let digits: Vec<u8> = text.bytes().filter(|b| !b.is_ascii_whitespace()).collect();
    let digits = digits
        .strip_suffix(b"==")
        .or_else(|| digits.strip_suffix(b"="))
        .unwrap_or(&digits);
    if digits.len() % 4 == 1 {
        return None;
    }
    let mut out = Vec::with_capacity(digits.len() * 3 / 4);
    for chunk in digits.chunks(4) {
        let mut n = 0u32;
        for (i, &d) in chunk.iter().enumerate() {
            let v = TABLE.iter().position(|&t| t == d)? as u32;
            n |= v << (18 - 6 * i);
        }
        out.extend_from_slice(&n.to_be_bytes()[1..chunk.len()]);
    }
    Some(out)
}

#[cfg(test)]
mod tests {
    use super::{decode, encode};

    #[test]
    fn known_encodings() {
        // 1.0f32 is 00 00 80 3f.
        assert_eq!(encode(&1.0f32.to_le_bytes()), "AACAPw==");
        assert_eq!(encode(b"Kinetic"), "S2luZXRpYw==");
        assert_eq!(encode(b"Kin"), "S2lu");
    }

    #[test]
    fn decoding_inverts_encoding() {
        for len in 0..20 {
            let bytes: Vec<u8> = (0..len).map(|i| (i * 37 + 11) as u8).collect();
            assert_eq!(decode(&encode(&bytes)).unwrap(), bytes);
        }
        assert_eq!(decode("S2lu\nZXRpYw").unwrap(), b"Kinetic");
        assert_eq!(decode("S2l*"), None);
        assert_eq!(decode("S"), None);
    }
}
