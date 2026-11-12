//! Ollama response shapes, see docs/api.md in github.com/ollama/ollama.

use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde_json::{json, Map, Value};

use crate::engine::{Completion, Finish};
use crate::model_info::ModelInfo;
use crate::text::Split;
use crate::ToolCall;

/// The Ollama release whose API this mirrors; clients gate features on it.
pub const VERSION: &str = "0.13.0";

/// The `details` object of a model listing.
pub fn details(info: &ModelInfo) -> Value {
    json!({
        "parent_model": "",
        "format": "gguf",
        "family": info.architecture,
        "families": [info.architecture],
        "parameter_size": info.parameter_size(),
        "quantization_level": info.quantization,
    })
}

/// `/api/tags`: the one model served.
pub fn tags(name: &str, info: &ModelInfo) -> Value {
    json!({"models": [{
        "name": name,
        "model": name,
        "modified_at": timestamp(info.loaded),
        "size": info.size,
        "digest": info.digest,
        "details": details(info),
    }]})
}

/// `/api/ps`: the one model, loaded until the server stops.
pub fn ps(name: &str, info: &ModelInfo, context: usize) -> Value {
    json!({"models": [{
        "name": name,
        "model": name,
        "size": info.size,
        "digest": info.digest,
        "details": details(info),
        "expires_at": "9999-12-31T23:59:59Z",
        "size_vram": 0,
        "context_length": context,
    }]})
}

/// `/api/show`.
pub fn show(info: &ModelInfo, capabilities: &[&str]) -> Value {
    let mut model_info = info.metadata.clone();
    model_info.insert("general.parameter_count".into(), info.parameters.into());
    json!({
        "modelfile": "",
        "parameters": "",
        "template": info.chat_template.clone().unwrap_or_default(),
        "details": details(info),
        "model_info": model_info,
        "capabilities": capabilities,
        "modified_at": timestamp(info.loaded),
    })
}

/// The start of every generation object.
pub fn head(model: &str) -> Map<String, Value> {
    let mut m = Map::new();
    m.insert("model".into(), model.into());
    m.insert("created_at".into(), timestamp(SystemTime::now()).into());
    m
}

/// A `/api/generate` piece, or with `done` the final object.
pub fn generate_piece(model: &str, part: &Split) -> Value {
    let mut m = head(model);
    m.insert("response".into(), part.content.clone().into());
    if !part.reasoning.is_empty() {
        m.insert("thinking".into(), part.reasoning.clone().into());
    }
    m.insert("done".into(), false.into());
    m.into()
}

/// The assistant message of a `/api/chat` piece or answer.
pub fn message(content: &str, reasoning: &str, calls: &[ToolCall]) -> Value {
    let mut m = json!({"role": "assistant", "content": content});
    if !reasoning.is_empty() {
        m["thinking"] = reasoning.into();
    }
    if !calls.is_empty() {
        m["tool_calls"] = tool_calls(calls);
    }
    m
}

pub fn chat_piece(model: &str, message: Value) -> Value {
    let mut m = head(model);
    m.insert("message".into(), message);
    m.insert("done".into(), false.into());
    m.into()
}

/// Ollama gives arguments as an object, where OpenAI gives JSON text.
fn tool_calls(calls: &[ToolCall]) -> Value {
    calls
        .iter()
        .map(|c| {
            let arguments = serde_json::from_str::<Value>(&c.arguments)
                .unwrap_or_else(|_| c.arguments.clone().into());
            json!({"function": {"name": c.name, "arguments": arguments}})
        })
        .collect()
}

/// Ends `piece`, the last object of a generation, with its statistics.
pub fn done(mut piece: Map<String, Value>, c: &Completion, total: Duration) -> Value {
    let reason = match c.finish {
        Finish::Length => "length",
        Finish::Stop | Finish::ToolCalls => "stop",
    };
    let ns = |d: Duration| d.as_nanos() as u64;
    for (key, value) in [
        ("done", Value::from(true)),
        ("done_reason", reason.into()),
        ("total_duration", ns(total).into()),
        ("load_duration", 0.into()),
        ("prompt_eval_count", c.prompt_tokens.into()),
        ("prompt_eval_duration", ns(c.timings.prefill).into()),
        ("eval_count", c.completion_tokens.into()),
        ("eval_duration", ns(c.timings.decode).into()),
    ] {
        piece.insert(key.into(), value);
    }
    piece.into()
}

/// The answer to a request that only loads or unloads the model.
pub fn loaded(model: &str, chat: bool, reason: &str) -> Value {
    let mut m = head(model);
    if chat {
        m.insert(
            "message".into(),
            json!({"role": "assistant", "content": ""}),
        );
    } else {
        m.insert("response".into(), "".into());
    }
    m.insert("done".into(), true.into());
    m.insert("done_reason".into(), reason.into());
    m.into()
}

/// RFC 3339 in UTC with nanoseconds, as Go prints times.
pub fn timestamp(t: SystemTime) -> String {
    let d = t.duration_since(UNIX_EPOCH).unwrap_or_default();
    let secs = d.as_secs();
    let (days, rem) = ((secs / 86_400) as i64, secs % 86_400);
    // days to a civil date, see howardhinnant.github.io/date_algorithms.html
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = yoe + era * 400 + i64::from(month <= 2);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}.{:09}Z",
        rem / 3600,
        rem / 60 % 60,
        rem % 60,
        d.subsec_nanos()
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Timings;

    #[test]
    fn timestamps_are_rfc3339() {
        let t = UNIX_EPOCH + Duration::new(1_691_164_339, 499_127_000);
        assert_eq!(timestamp(t), "2023-08-04T15:52:19.499127000Z");
        assert_eq!(
            timestamp(UNIX_EPOCH + Duration::from_secs(951_782_400)),
            "2000-02-29T00:00:00.000000000Z"
        );
    }

    #[test]
    fn final_objects_carry_the_statistics() {
        let c = Completion {
            content: "Hi".into(),
            reasoning: String::new(),
            tool_calls: vec![ToolCall {
                name: "f".into(),
                arguments: r#"{"x":1}"#.into(),
            }],
            finish: Finish::ToolCalls,
            prompt_tokens: 7,
            completion_tokens: 3,
            timings: Timings {
                prefill: Duration::from_millis(2),
                decode: Duration::from_millis(5),
                ..Timings::default()
            },
            prompt_ids: Vec::new(),
            output_ids: Vec::new(),
        };
        let mut piece = head("m");
        piece.insert(
            "message".into(),
            message(&c.content, &c.reasoning, &c.tool_calls),
        );
        let v = done(piece, &c, Duration::from_millis(9));
        assert_eq!(v["done"], true);
        assert_eq!(v["done_reason"], "stop");
        assert_eq!(
            v["message"]["tool_calls"][0]["function"]["arguments"]["x"],
            1
        );
        assert_eq!(v["prompt_eval_count"], 7);
        assert_eq!(v["eval_count"], 3);
        assert_eq!(v["eval_duration"], 5_000_000);
        assert_eq!(v["total_duration"], 9_000_000);
        assert!(v["created_at"].as_str().unwrap().ends_with('Z'));
    }
}
