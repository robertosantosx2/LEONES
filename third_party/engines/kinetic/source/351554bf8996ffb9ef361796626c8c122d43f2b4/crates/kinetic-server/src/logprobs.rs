//! Token log-probabilities in OpenAI's response shapes.

use serde_json::{json, Map, Value};

use crate::TokenLogprob;

/// `choices[].logprobs` of a chat completion or chunk.
pub fn chat<'t>(tokens: &[TokenLogprob], piece: impl Fn(u32) -> &'t [u8]) -> Value {
    let entry = |id: u32, logprob: f32| {
        let bytes = piece(id);
        json!({"token": String::from_utf8_lossy(bytes), "logprob": finite(logprob), "bytes": bytes})
    };
    let content: Vec<Value> = tokens
        .iter()
        .map(|t| {
            let mut e = entry(t.token, t.logprob);
            e["top_logprobs"] = t.top.iter().map(|&(id, lp)| entry(id, lp)).collect();
            e
        })
        .collect();
    json!({"content": content, "refusal": null})
}

/// `choices[].logprobs` of a legacy completion or chunk; `offset` is where
/// in the generated text, in characters, the first token starts, and moves
/// past the last.
pub fn completion<'t>(
    tokens: &[TokenLogprob],
    piece: impl Fn(u32) -> &'t [u8],
    offset: &mut usize,
) -> Value {
    let text = |id: u32| String::from_utf8_lossy(piece(id)).into_owned();
    let mut offsets = Vec::with_capacity(tokens.len());
    for t in tokens {
        offsets.push(*offset);
        *offset += text(t.token).chars().count();
    }
    let top: Vec<Value> = tokens
        .iter()
        .map(|t| {
            let alternatives: Map<String, Value> = t
                .top
                .iter()
                .map(|&(id, lp)| (text(id), finite(lp).into()))
                .collect();
            alternatives.into()
        })
        .collect();
    json!({
        "tokens": tokens.iter().map(|t| text(t.token)).collect::<Vec<_>>(),
        "token_logprobs": tokens.iter().map(|t| finite(t.logprob)).collect::<Vec<_>>(),
        "top_logprobs": top,
        "text_offset": offsets,
    })
}

/// JSON has no infinity; OpenAI reports impossible tokens as -9999.
fn finite(logprob: f32) -> f32 {
    logprob.max(-9999.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tokens() -> Vec<TokenLogprob> {
        vec![
            TokenLogprob {
                token: 0,
                logprob: -0.5,
                top: vec![(0, -0.5), (1, -1.0)],
            },
            TokenLogprob {
                token: 1,
                logprob: f32::NEG_INFINITY,
                top: Vec::new(),
            },
        ]
    }

    fn piece(id: u32) -> &'static [u8] {
        [b"Hi".as_slice(), "ś".as_bytes()][id as usize]
    }

    #[test]
    fn chat_shape() {
        let v = chat(&tokens(), piece);
        assert_eq!(v["content"][0]["token"], "Hi");
        assert_eq!(v["content"][0]["bytes"], json!([72, 105]));
        assert_eq!(v["content"][0]["top_logprobs"][1]["logprob"], -1.0);
        assert_eq!(v["content"][1]["logprob"], -9999.0);
        assert_eq!(v["refusal"], Value::Null);
    }

    #[test]
    fn completion_shape() {
        let mut offset = 3;
        let v = completion(&tokens(), piece, &mut offset);
        assert_eq!(v["tokens"], json!(["Hi", "ś"]));
        assert_eq!(v["token_logprobs"], json!([-0.5, -9999.0]));
        assert_eq!(v["top_logprobs"][0], json!({"Hi": -0.5, "ś": -1.0}));
        assert_eq!(v["text_offset"], json!([3, 5]));
        assert_eq!(offset, 6);
    }
}
