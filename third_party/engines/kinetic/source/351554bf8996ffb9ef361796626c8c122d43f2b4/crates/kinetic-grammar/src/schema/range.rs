//! GBNF for decimal numbers between bounds, built digit by digit.

/// The largest whole part a bounded number may have.
pub(crate) const MAX_WHOLE: u64 = 999_999_999_999_999;

/// Exactly the integers in `lo..=hi`, without leading zeros or `-0`.
pub(crate) fn integers(lo: i64, hi: i64) -> Option<String> {
    let mut alts = Vec::new();
    let neg_hi = hi.min(-1);
    if lo <= neg_hi {
        alts.push(format!(
            "\"-\" {}",
            whole(neg_hi.unsigned_abs(), lo.unsigned_abs())
        ));
    }
    if hi >= 0 && lo.max(0) <= hi {
        alts.push(whole(lo.max(0) as u64, hi as u64));
    }
    group(alts)
}

/// Decimals without an exponent between whole bounds, each `(value,
/// exclusive)`; absent bounds stop at whole parts of 15 digits.
pub(crate) fn decimals(lo: Option<(i64, bool)>, hi: Option<(i64, bool)>) -> Option<String> {
    let mut alts = Vec::new();
    if hi.is_none_or(|(h, excl)| h > 0 || (h == 0 && !excl)) {
        let low = match lo {
            Some((l, excl)) if l >= 0 => (l as u64, excl),
            _ => (0, false),
        };
        alts.extend(magnitudes(low, hi.map(|(h, excl)| (h as u64, excl))));
    }
    if lo.is_none_or(|(l, _)| l < 0) {
        let low = match hi {
            Some((h, excl)) if h < 0 => (h.unsigned_abs(), excl),
            _ => (0, true),
        };
        let high = lo.map(|(l, excl)| (l.unsigned_abs(), excl));
        if let Some(m) = magnitudes(low, high) {
            alts.push(format!("\"-\" {m}"));
        }
    }
    group(alts)
}

/// Non-negative decimals between `low` and `high`.
fn magnitudes((a, a_excl): (u64, bool), high: Option<(u64, bool)>) -> Option<String> {
    const FRACTION: &str = r#"("." [0-9]{1,15})?"#;
    let (b, b_excl) = high.unwrap_or((MAX_WHOLE + 1, true));
    let mut alts = Vec::new();
    let mut first = a;
    if a_excl {
        if a < b {
            alts.push(format!(r#""{a}" "." [0-9]{{0,14}} [1-9] [0-9]{{0,14}}"#));
        }
        first = a + 1;
    }
    if b > 0 && first < b {
        alts.push(format!("{} {FRACTION}", whole(first, b - 1)));
    }
    if !b_excl && (a < b || (a == b && !a_excl)) {
        alts.push(format!("\"{b}\""));
    }
    group(alts)
}

/// The whole numbers in `a..=b`.
fn whole(a: u64, b: u64) -> String {
    let mut alts = Vec::new();
    for len in digits(a)..=digits(b) {
        let lo = a.max(if len == 1 { 0 } else { 10u64.pow(len - 1) });
        let hi = b.min(10u64.pow(len) - 1);
        alts.push(same_length(
            lo.to_string().as_bytes(),
            hi.to_string().as_bytes(),
        ));
    }
    group(alts).expect("a <= b")
}

/// The digit strings from `x` to `y`, which have the same length.
fn same_length(x: &[u8], y: &[u8]) -> String {
    let (Some((&x0, xs)), Some((&y0, ys))) = (x.split_first(), y.split_first()) else {
        return String::new();
    };
    if x0 == y0 {
        return join(format!("\"{}\"", x0 as char), same_length(xs, ys));
    }
    let n = xs.len();
    let low_full = xs.iter().all(|&c| c == b'0');
    let high_full = ys.iter().all(|&c| c == b'9');
    let mut alts = Vec::new();
    let (mut from, mut to) = (x0, y0);
    if !low_full {
        alts.push(join(
            format!("\"{}\"", x0 as char),
            same_length(xs, &vec![b'9'; n]),
        ));
        from += 1;
    }
    if !high_full {
        to -= 1;
    }
    if from <= to {
        let first = if from == to {
            format!("\"{}\"", from as char)
        } else {
            format!("[{}-{}]", from as char, to as char)
        };
        let rest = match n {
            0 => String::new(),
            1 => "[0-9]".to_owned(),
            _ => format!("[0-9]{{{n}}}"),
        };
        alts.push(join(first, rest));
    }
    if !high_full {
        alts.push(join(
            format!("\"{}\"", y0 as char),
            same_length(&vec![b'0'; n], ys),
        ));
    }
    group(alts).expect("x < y")
}

fn digits(v: u64) -> u32 {
    v.checked_ilog10().unwrap_or(0) + 1
}

fn join(a: String, b: String) -> String {
    if b.is_empty() {
        a
    } else {
        format!("{a} {b}")
    }
}

fn group(mut alts: Vec<String>) -> Option<String> {
    match alts.len() {
        0 => None,
        1 => alts.pop(),
        _ => Some(format!("({})", alts.join(" | "))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Grammar;

    fn grammar(expr: &str) -> Grammar {
        Grammar::parse(&format!("root ::= {expr}\n")).unwrap()
    }

    #[test]
    fn integers_match_exactly_their_range() {
        for (lo, hi) in [
            (0, 0),
            (-5, 5),
            (7, 1234),
            (-1000, -37),
            (19, 20),
            (100, 999),
            (-12, 0),
        ] {
            let g = grammar(&integers(lo, hi).unwrap());
            for v in -1300i64..1300 {
                assert_eq!(
                    g.matches(&v.to_string()),
                    (lo..=hi).contains(&v),
                    "{v} in {lo}..={hi}"
                );
            }
            assert!(!g.matches("-0") && !g.matches("01") && !g.matches(""));
        }
        assert!(integers(5, 4).is_none());
    }

    #[test]
    fn decimals_respect_bounds() {
        type Bound = Option<(i64, bool)>;
        let cases: [(Bound, Bound); 5] = [
            (Some((0, false)), Some((1, false))),
            (Some((0, true)), None),
            (Some((-3, true)), Some((2, true))),
            (None, Some((-2, false))),
            (Some((10, false)), Some((10, false))),
        ];
        for (lo, hi) in cases {
            let g = grammar(&decimals(lo, hi).unwrap());
            for text in [
                "0", "0.5", "1", "1.5", "-0.25", "-2", "-2.5", "-3", "2", "1.99", "10", "10.5",
            ] {
                let v: f64 = text.parse().unwrap();
                let above =
                    lo.is_none_or(|(l, excl)| if excl { v > l as f64 } else { v >= l as f64 });
                let below =
                    hi.is_none_or(|(h, excl)| if excl { v < h as f64 } else { v <= h as f64 });
                assert_eq!(g.matches(text), above && below, "{text} in {lo:?}..{hi:?}");
            }
        }
    }
}
