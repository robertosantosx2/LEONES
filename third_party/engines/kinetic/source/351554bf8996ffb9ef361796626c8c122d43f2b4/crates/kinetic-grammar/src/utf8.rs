//! Code point sets and their UTF-8 spellings as byte range sequences.

/// The largest Unicode scalar value.
pub(crate) const MAX_CHAR: u32 = 0x10FFFF;

/// One way to spell a run of code points: an inclusive byte range for each
/// encoded byte.
pub(crate) type Sequence = Vec<(u8, u8)>;

/// Sorts `ranges` and merges the ones that touch or overlap.
pub(crate) fn normalize(ranges: &mut Vec<(u32, u32)>) {
    ranges.retain(|&(lo, hi)| lo <= hi);
    ranges.sort_unstable();
    let mut merged: Vec<(u32, u32)> = Vec::with_capacity(ranges.len());
    for &(lo, hi) in ranges.iter() {
        match merged.last_mut() {
            Some(last) if lo <= last.1.saturating_add(1) => last.1 = last.1.max(hi),
            _ => merged.push((lo, hi)),
        }
    }
    *ranges = merged;
}

/// The code points in `0..=MAX_CHAR` that normalized `ranges` leaves out.
pub(crate) fn complement(ranges: &[(u32, u32)]) -> Vec<(u32, u32)> {
    let mut out = Vec::with_capacity(ranges.len() + 1);
    let mut next = 0;
    for &(lo, hi) in ranges {
        if lo > next {
            out.push((next, lo - 1));
        }
        next = hi.saturating_add(1);
    }
    if next <= MAX_CHAR {
        out.push((next, MAX_CHAR));
    }
    out
}

/// Appends the byte sequences that spell exactly the scalar values in
/// `lo..=hi`; surrogates are skipped since they have no UTF-8 form.
pub(crate) fn sequences(lo: u32, hi: u32, out: &mut Vec<Sequence>) {
    let hi = hi.min(MAX_CHAR);
    if lo > hi {
        return;
    }
    if lo <= 0xDFFF && hi >= 0xD800 {
        if lo < 0xD800 {
            sequences(lo, 0xD7FF, out);
        }
        if hi > 0xDFFF {
            sequences(0xE000, hi, out);
        }
        return;
    }
    for last in [0x7F, 0x7FF, 0xFFFF] {
        if lo <= last && hi > last {
            sequences(lo, last, out);
            sequences(last + 1, hi, out);
            return;
        }
    }
    split(lo, hi, out);
}

/// Splits a range whose ends encode to the same length until every byte
/// position varies independently of the others.
fn split(lo: u32, hi: u32, out: &mut Vec<Sequence>) {
    let len = char_len(lo);
    for i in 1..len {
        let m = (1u32 << (6 * i)) - 1;
        if lo & !m != hi & !m {
            if lo & m != 0 {
                split(lo, lo | m, out);
                split((lo | m) + 1, hi, out);
                return;
            }
            if hi & m != m {
                split(lo, (hi & !m) - 1, out);
                split(hi & !m, hi, out);
                return;
            }
        }
    }
    let (a, b) = (encode(lo), encode(hi));
    out.push(a.iter().zip(&b).map(|(&x, &y)| (x, y)).collect());
}

fn char_len(c: u32) -> usize {
    match c {
        0..=0x7F => 1,
        0x80..=0x7FF => 2,
        0x800..=0xFFFF => 3,
        _ => 4,
    }
}

fn encode(c: u32) -> Vec<u8> {
    let c = char::from_u32(c).expect("surrogates are split off before encoding");
    c.encode_utf8(&mut [0; 4]).as_bytes().to_vec()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spelled(seqs: &[Sequence], bytes: &[u8]) -> bool {
        seqs.iter().any(|s| {
            s.len() == bytes.len()
                && s.iter()
                    .zip(bytes)
                    .all(|(&(lo, hi), &b)| lo <= b && b <= hi)
        })
    }

    #[test]
    fn sequences_cover_exactly_the_range() {
        for &(lo, hi) in &[
            (0, MAX_CHAR),
            (0x41, 0x5A),
            (0x7A, 0x7FF),
            (0x3041, 0x309F),
            (0xD000, 0xE100),
            (0xFFF0, 0x10010),
        ] {
            let mut seqs = Vec::new();
            sequences(lo, hi, &mut seqs);
            for c in (0..=MAX_CHAR)
                .step_by(7)
                .chain([lo, hi, 0xD7FF, 0xE000, 0xFFFF, 0x10000])
            {
                let Some(ch) = char::from_u32(c) else {
                    continue;
                };
                let mut buf = [0; 4];
                let inside = lo <= c && c <= hi;
                assert_eq!(
                    spelled(&seqs, ch.encode_utf8(&mut buf).as_bytes()),
                    inside,
                    "{c:#x}"
                );
            }
            assert!(!spelled(&seqs, &[0xED, 0xA0, 0x80]), "surrogate spelled");
            assert!(!spelled(&seqs, &[0xC0, 0x80]), "overlong spelled");
        }
    }

    #[test]
    fn complement_of_normalized() {
        let mut r = vec![(10, 20), (0, 3), (4, 5), (15, 30)];
        normalize(&mut r);
        assert_eq!(r, vec![(0, 5), (10, 30)]);
        assert_eq!(complement(&r), vec![(6, 9), (31, MAX_CHAR)]);
        assert_eq!(complement(&[(0, MAX_CHAR)]), vec![]);
    }
}
