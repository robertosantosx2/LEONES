//! DRY ("don't repeat yourself"): lowers tokens that would extend a
//! repetition of earlier text, with llama.cpp's definition and defaults.

use std::collections::HashMap;

use super::Sampling;

/// Longest breaker text and breaker tail kept, as in llama.cpp.
const MAX_BREAKER_BYTES: usize = 40;
const MAX_TAIL_TOKENS: usize = 20;

/// Resolves `breakers`, texts that end a repetition, against a vocabulary
/// of `n_vocab` tokens whose bytes `piece` gives: a token whose text holds
/// a breaker gets an empty tail, and a token whose text ends with the start
/// of a breaker gets the tokens of the rest, as `encode` (no special
/// tokens) gives them.
pub fn dry_breakers<'a>(
    breakers: &[String],
    n_vocab: usize,
    piece: impl Fn(u32) -> &'a [u8],
    encode: impl Fn(&str) -> Vec<u32>,
) -> Vec<(u32, Vec<u32>)> {
    let mut out: Vec<(u32, Vec<u32>)> = Vec::new();
    let mut add = |entry: (u32, Vec<u32>)| {
        if !out.contains(&entry) {
            out.push(entry);
        }
    };
    for breaker in breakers {
        let b = &breaker.as_bytes()[..breaker.len().min(MAX_BREAKER_BYTES)];
        if b.is_empty() {
            continue;
        }
        for id in 0..n_vocab as u32 {
            let word = piece(id);
            if word.windows(b.len()).any(|w| w == b) {
                add((id, Vec::new()));
                continue;
            }
            for pos in (0..word.len()).filter(|&i| word[i] == b[0]) {
                let end = &word[pos..];
                if b.starts_with(end) {
                    let mut tail = encode(&String::from_utf8_lossy(&b[end.len()..]));
                    tail.truncate(MAX_TAIL_TOKENS);
                    add((id, tail));
                }
            }
        }
    }
    out
}

/// Breaker tails by their first token.
pub(super) type Breakers = HashMap<u32, Vec<Vec<u32>>>;

pub(super) fn breakers(p: &Sampling) -> Breakers {
    let mut map = Breakers::new();
    for (head, tail) in &p.dry_breaker_tokens {
        map.entry(*head).or_default().push(tail.clone());
    }
    map
}

pub(super) fn is_active(p: &Sampling) -> bool {
    p.dry_multiplier != 0.0 && p.dry_base >= 1.0 && p.dry_penalty_last_n > 0
}

/// Lowers in `logits` each token that would make a repetition of at least
/// `dry_allowed_length` tokens of the last `dry_penalty_last_n` of
/// `history` one longer, by `dry_multiplier * dry_base^(length - allowed)`.
pub(super) fn penalize(logits: &mut [f32], history: &[u32], p: &Sampling, breakers: &Breakers) {
    let n = history.len().min(p.dry_penalty_last_n);
    let allowed = p.dry_allowed_length;
    if !is_active(p) || n <= allowed {
        return;
    }
    // newest first, as llama.cpp walks it
    let rev: Vec<u32> = history[history.len() - n..].iter().rev().copied().collect();

    // a repetition reaches back no further than the latest breaker
    let mut limit = n;
    for i in 0..n {
        let longest = breakers.get(&rev[i]).and_then(|tails| {
            tails
                .iter()
                .filter(|t| t.len() <= i && t.iter().enumerate().all(|(o, &x)| x == rev[i - o - 1]))
                .map(Vec::len)
                .max()
        });
        if let Some(len) = longest {
            limit = i - len;
            break;
        }
    }
    if limit < allowed {
        return;
    }

    let z = z_function(&rev);
    let mut longest: HashMap<u32, usize> = HashMap::new();
    for k in 1..n {
        let len = z[k].min(limit);
        if len >= allowed {
            let e = longest.entry(rev[k - 1]).or_default();
            *e = (*e).max(len);
        }
    }

    // keeps base^exponent finite, see llama-sampling.cpp
    let max_exponent = if p.dry_base > 1.000_001 {
        (88.722_84 / p.dry_base.ln()) as usize
    } else {
        usize::MAX
    };
    for (token, len) in longest {
        let lone_breaker = breakers
            .get(&token)
            .is_some_and(|tails| tails.iter().any(Vec::is_empty));
        let Some(l) = logits.get_mut(token as usize).filter(|_| !lone_breaker) else {
            continue;
        };
        let exponent = (len - allowed).min(max_exponent) as i32;
        *l -= p.dry_multiplier * p.dry_base.powi(exponent);
    }
}

/// `z[k]`: how many leading items of `s` repeat from `k` on.
fn z_function(s: &[u32]) -> Vec<usize> {
    let n = s.len();
    let mut z = vec![0; n];
    let (mut l, mut r) = (0, 0);
    for i in 1..n {
        if i < r {
            z[i] = (r - i).min(z[i - l]);
        }
        while i + z[i] < n && s[z[i]] == s[i + z[i]] {
            z[i] += 1;
        }
        if i + z[i] > r {
            (l, r) = (i, i + z[i]);
        }
    }
    z
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dry(breaker_tokens: Vec<(u32, Vec<u32>)>) -> Sampling {
        Sampling {
            dry_multiplier: 1.0,
            dry_base: 2.0,
            dry_allowed_length: 2,
            dry_breaker_tokens: breaker_tokens,
            ..Sampling::default()
        }
    }

    fn apply(p: &Sampling, history: &[u32]) -> Vec<f32> {
        let mut logits = vec![0.0; 8];
        penalize(&mut logits, history, p, &breakers(p));
        logits
    }

    #[test]
    fn z_counts_repeated_prefixes() {
        assert_eq!(z_function(&[3, 2, 1, 4, 3, 2, 1]), [0, 0, 0, 0, 3, 0, 0]);
        assert_eq!(z_function(&[1, 1, 1]), [0, 2, 1]);
    }

    #[test]
    fn the_token_that_continued_a_repeat_is_lowered() {
        // 1 2 3 4 1 2 3: a 4 would repeat "1 2 3 4", three tokens matched,
        // 2^(3 - 2)
        let mut expected = vec![0.0; 8];
        expected[4] = -2.0;
        assert_eq!(apply(&dry(Vec::new()), &[1, 2, 3, 4, 1, 2, 3]), expected);
    }

    #[test]
    fn repeats_shorter_than_allowed_go_free() {
        assert_eq!(apply(&dry(Vec::new()), &[1, 2, 5, 1]), vec![0.0; 8]);
        let mut expected = vec![0.0; 8];
        expected[5] = -1.0;
        assert_eq!(apply(&dry(Vec::new()), &[1, 2, 5, 1, 2]), expected);
    }

    #[test]
    fn a_breaker_caps_the_repeat() {
        // with 1 a breaker only "2 3" counts: 2^(2 - 2)
        let mut expected = vec![0.0; 8];
        expected[4] = -1.0;
        let p = dry(vec![(1, Vec::new())]);
        assert_eq!(apply(&p, &[1, 2, 3, 4, 1, 2, 3]), expected);
        // a two-token breaker 2 3 right at the end leaves nothing
        let p = dry(vec![(2, vec![3])]);
        assert_eq!(apply(&p, &[1, 2, 3, 4, 1, 2, 3]), vec![0.0; 8]);
    }

    #[test]
    fn lone_breakers_are_never_lowered() {
        // 7 continues "5 6", but 7 alone ends repetitions
        let p = dry(vec![(7, Vec::new())]);
        assert_eq!(apply(&p, &[5, 6, 7, 5, 6]), vec![0.0; 8]);
    }

    #[test]
    fn breakers_cover_tokens_that_hold_or_start_them() {
        let pieces: [&[u8]; 4] = [b"a\nb", b"x", b"end:", b"ab"];
        let encode = |s: &str| s.bytes().map(u32::from).collect();
        let found = dry_breakers(
            &["\n".into(), "b:c".into()],
            4,
            |id| pieces[id as usize],
            encode,
        );
        assert_eq!(
            found,
            [
                (0, vec![]),
                (0, vec![u32::from(b':'), u32::from(b'c')]),
                (3, vec![u32::from(b':'), u32::from(b'c')])
            ]
        );
    }
}
