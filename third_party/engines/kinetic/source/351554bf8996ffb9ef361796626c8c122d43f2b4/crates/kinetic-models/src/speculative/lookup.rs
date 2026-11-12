use super::{Drafter, Target};

/// Drafts from the context itself: the tokens that followed the most recent
/// earlier occurrence of the last few tokens. Free to compute, and right
/// whenever the output repeats the input, as edits of code or quoted
/// passages do.
pub struct Lookup {
    /// Longest and shortest suffix of the context to look up.
    pub max_ngram: usize,
    pub min_ngram: usize,
}

impl Default for Lookup {
    fn default() -> Self {
        Lookup {
            max_ngram: 4,
            min_ngram: 2,
        }
    }
}

impl<M: Target> Drafter<M> for Lookup {
    fn propose(&mut self, _model: &M, context: &[u32], limit: usize) -> Vec<u32> {
        self.draft(context, limit)
    }
}

impl Lookup {
    fn draft(&self, context: &[u32], limit: usize) -> Vec<u32> {
        let len = context.len();
        for g in (self.min_ngram..=self.max_ngram).rev() {
            if g >= len {
                continue;
            }
            let suffix = &context[len - g..];
            let found = (0..len - g).rev().find(|&i| &context[i..i + g] == suffix);
            if let Some(i) = found {
                let start = i + g;
                let end = (start + limit).min(len);
                if start < end {
                    return context[start..end].to_vec();
                }
            }
        }
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn drafts_what_followed_the_latest_match() {
        let d = Lookup {
            max_ngram: 3,
            min_ngram: 2,
        };
        let context = [1, 2, 3, 4, 5, 9, 2, 3, 7, 8, 1, 2, 3];
        assert_eq!(d.draft(&context, 3), vec![4, 5, 9]);
        assert_eq!(d.draft(&context, 2), vec![4, 5]);
    }

    #[test]
    fn no_match_means_no_draft() {
        assert!(Lookup::default().draft(&[1, 2, 3, 4, 5], 8).is_empty());
    }
}
