//! OpenAI request and response shapes.

use std::sync::Arc;

use kinetic_grammar::Grammar;
use serde::Deserialize;
use serde_json::{json, Map, Value};

use crate::base64;
use crate::engine::{Completion, Request};
use crate::{Sampling, ToolCall};

/// A failed request, answered with an OpenAI-shaped error body.
#[derive(Debug, PartialEq, Eq)]
pub struct ApiError {
    pub status: u16,
    pub message: String,
}

impl ApiError {
    pub fn invalid(message: impl Into<String>) -> Self {
        ApiError {
            status: 400,
            message: message.into(),
        }
    }

    pub fn body(&self) -> Value {
        let kind = match self.status {
            401 => "authentication_error",
            400..=499 => "invalid_request_error",
            _ => "server_error",
        };
        json!({"error": {"message": self.message, "type": kind, "param": null, "code": null}})
    }
}

#[derive(Debug, Deserialize)]
pub struct ChatRequest {
    pub messages: Vec<Value>,
    #[serde(default)]
    pub chat_template_kwargs: Option<Map<String, Value>>,
    #[serde(default)]
    tools: Option<Vec<Value>>,
    #[serde(default)]
    tool_choice: Option<Value>,
    #[serde(default)]
    parallel_tool_calls: Option<bool>,
    #[serde(flatten)]
    pub common: Common,
}

impl ChatRequest {
    /// Whether `tool_choice` holds the reply to calls: `required` or a
    /// named function.
    pub fn forces_call(&self) -> bool {
        match &self.tool_choice {
            Some(Value::String(choice)) => choice == "required",
            Some(Value::Object(_)) => true,
            _ => false,
        }
    }

    /// Whether a forced reply may hold several calls; off unless asked, as
    /// in llama-server.
    pub fn parallel_calls(&self) -> bool {
        self.parallel_tool_calls.unwrap_or(false)
    }

    /// The tools the model may call, as `tool_choice` narrows them; `None`
    /// when it may call none.
    pub fn tools(&self) -> Result<Option<Vec<Value>>, ApiError> {
        let Some(tools) = self.tools.as_ref().filter(|t| !t.is_empty()) else {
            return Ok(None);
        };
        if tools.iter().any(|t| tool_name(t).is_none()) {
            return Err(ApiError::invalid("every tool needs a function with a name"));
        }
        match &self.tool_choice {
            None | Some(Value::Null) => Ok(Some(tools.clone())),
            Some(Value::String(choice)) => match choice.as_str() {
                "auto" | "required" => Ok(Some(tools.clone())),
                "none" => Ok(None),
                _ => Err(ApiError::invalid(
                    "tool_choice must be none, auto, required or a function",
                )),
            },
            Some(choice) => {
                let name = choice
                    .pointer("/function/name")
                    .and_then(Value::as_str)
                    .ok_or_else(|| ApiError::invalid("tool_choice.function.name is missing"))?;
                let chosen: Vec<Value> = tools
                    .iter()
                    .filter(|t| tool_name(t) == Some(name))
                    .cloned()
                    .collect();
                if chosen.is_empty() {
                    return Err(ApiError::invalid(format!(
                        "tool_choice names {name}, which is not among the tools"
                    )));
                }
                Ok(Some(chosen))
            }
        }
    }
}

fn tool_name(tool: &Value) -> Option<&str> {
    tool.pointer("/function/name").and_then(Value::as_str)
}

#[derive(Debug, Deserialize)]
pub struct CompletionRequest {
    pub prompt: Value,
    #[serde(flatten)]
    pub common: Common,
}

/// Fields shared by both generation endpoints.
#[derive(Debug, Default, Deserialize)]
pub struct Common {
    stream: Option<bool>,
    stream_options: Option<StreamOptions>,
    temperature: Option<f32>,
    top_p: Option<f32>,
    top_k: Option<i64>,
    min_p: Option<f32>,
    seed: Option<i64>,
    max_tokens: Option<i64>,
    max_completion_tokens: Option<i64>,
    stop: Option<Stop>,
    #[serde(alias = "repetition_penalty")]
    repeat_penalty: Option<f32>,
    presence_penalty: Option<f32>,
    frequency_penalty: Option<f32>,
    n: Option<i64>,
    response_format: Option<Value>,
    /// A GBNF grammar, as llama-server takes it.
    grammar: Option<String>,
    /// True on chat completions, a count of alternatives on completions.
    logprobs: Option<Value>,
    top_logprobs: Option<i64>,
    logit_bias: Option<Map<String, Value>>,
    typical_p: Option<f32>,
    top_n_sigma: Option<f32>,
    xtc_probability: Option<f32>,
    xtc_threshold: Option<f32>,
    dry_multiplier: Option<f32>,
    dry_base: Option<f32>,
    dry_allowed_length: Option<i64>,
    dry_penalty_last_n: Option<i64>,
    dry_sequence_breakers: Option<Vec<String>>,
    mirostat: Option<i64>,
    mirostat_tau: Option<f32>,
    mirostat_eta: Option<f32>,
    /// Adds a receipt that reproduces the answer to the response.
    receipt: Option<bool>,
}

#[derive(Debug, Default, Deserialize)]
struct StreamOptions {
    include_usage: Option<bool>,
}

#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum Stop {
    One(String),
    Many(Vec<String>),
}

impl Common {
    pub fn stream(&self) -> bool {
        self.stream.unwrap_or(false)
    }

    pub fn include_usage(&self) -> bool {
        self.stream_options
            .as_ref()
            .and_then(|o| o.include_usage)
            .unwrap_or(false)
    }

    pub fn receipt(&self) -> bool {
        self.receipt.unwrap_or(false)
    }

    /// The `grammar` or `response_format` field as sent, for a receipt.
    pub fn constraint(&self) -> Option<Value> {
        let (key, value) = match (&self.grammar, &self.response_format) {
            (Some(g), _) => ("grammar", Value::from(g.as_str())),
            (None, Some(f)) => ("response_format", f.clone()),
            (None, None) => return None,
        };
        Some(Value::Object(Map::from_iter([(key.to_owned(), value)])))
    }

    /// The generation asked for, with `defaults` for what it leaves out.
    pub fn request(&self, defaults: &Sampling) -> Result<Request, ApiError> {
        if self.n.is_some_and(|n| n != 1) {
            return Err(ApiError::invalid("only n = 1 is supported"));
        }
        let range = |name: &str, v: Option<f32>, lo: f32, hi: f32| match v {
            Some(v) if !(lo..=hi).contains(&v) => Err(ApiError::invalid(format!(
                "{name} must be between {lo} and {hi}"
            ))),
            _ => Ok(v),
        };
        let mut s = defaults.clone();
        if let Some(t) = range("temperature", self.temperature, 0.0, 100.0)? {
            s.temperature = t;
        }
        if let Some(p) = range("top_p", self.top_p, 0.0, 1.0)? {
            s.top_p = p;
        }
        if let Some(p) = range("min_p", self.min_p, 0.0, 1.0)? {
            s.min_p = p;
        }
        if let Some(p) = range("repeat_penalty", self.repeat_penalty, 0.0, 100.0)? {
            s.repeat_penalty = p;
        }
        if let Some(p) = range("presence_penalty", self.presence_penalty, -2.0, 2.0)? {
            s.presence_penalty = p;
        }
        if let Some(p) = range("frequency_penalty", self.frequency_penalty, -2.0, 2.0)? {
            s.frequency_penalty = p;
        }
        if let Some(k) = self.top_k {
            // Zero and negative values disable it, as in llama.cpp.
            s.top_k = usize::try_from(k).unwrap_or(0);
        }
        // Any integer is a valid seed; negative ones keep their bits.
        s.seed = self.seed.map(|v| v as u64).or(s.seed);
        self.more_sampling(&mut s)?;

        let max_tokens = match self.max_completion_tokens.or(self.max_tokens) {
            Some(n) if n < 1 => return Err(ApiError::invalid("max_tokens must be at least 1")),
            n => n.map(|n| usize::try_from(n).unwrap_or(usize::MAX)),
        };
        let stop = match &self.stop {
            None => Vec::new(),
            Some(Stop::One(s)) => vec![s.clone()],
            Some(Stop::Many(v)) => v.clone(),
        };
        Ok(Request {
            sampling: s,
            max_tokens,
            stop,
            grammar: self.grammar()?,
        })
    }

    /// The samplers beyond OpenAI's, under llama.cpp's names, and
    /// `logit_bias`.
    fn more_sampling(&self, s: &mut Sampling) -> Result<(), ApiError> {
        let set = |to: &mut f32, v: Option<f32>| *to = v.unwrap_or(*to);
        set(&mut s.typical_p, self.typical_p);
        set(&mut s.top_n_sigma, self.top_n_sigma);
        set(&mut s.xtc_probability, self.xtc_probability);
        set(&mut s.xtc_threshold, self.xtc_threshold);
        set(&mut s.dry_multiplier, self.dry_multiplier);
        set(&mut s.dry_base, self.dry_base);
        set(&mut s.mirostat_tau, self.mirostat_tau);
        set(&mut s.mirostat_eta, self.mirostat_eta);
        if let Some(n) = self.dry_allowed_length {
            s.dry_allowed_length = usize::try_from(n).unwrap_or(0);
        }
        if let Some(n) = self.dry_penalty_last_n {
            // -1 is the whole context, as in llama.cpp
            s.dry_penalty_last_n = usize::try_from(n).unwrap_or(usize::MAX);
        }
        if let Some(b) = &self.dry_sequence_breakers {
            s.dry_sequence_breakers = b.clone();
        }
        if let Some(m) = self.mirostat {
            s.mirostat = u8::try_from(m)
                .ok()
                .filter(|m| *m <= 2)
                .ok_or_else(|| ApiError::invalid("mirostat must be 0, 1 or 2"))?;
        }
        if let Some(bias) = &self.logit_bias {
            s.logit_bias = bias
                .iter()
                .map(|(id, v)| {
                    let id = id.parse::<u32>().ok();
                    let v = v.as_f64().filter(|v| (-100.0..=100.0).contains(v));
                    // -100 bans the token outright, as OpenAI documents it
                    let v = v.map(|v| {
                        if v <= -100.0 {
                            f32::NEG_INFINITY
                        } else {
                            v as f32
                        }
                    });
                    id.zip(v).ok_or_else(|| {
                        ApiError::invalid("logit_bias maps token ids to numbers from -100 to 100")
                    })
                })
                .collect::<Result<_, _>>()?;
        }
        Ok(())
    }

    /// How many alternatives to report with each token's log-probability,
    /// if any: `logprobs` and `top_logprobs` on chat completions, or the
    /// count in `logprobs` on completions.
    pub fn logprobs(&self) -> Result<Option<usize>, ApiError> {
        let top = match self.top_logprobs {
            Some(n) if !(0..=20).contains(&n) => {
                return Err(ApiError::invalid("top_logprobs must be between 0 and 20"))
            }
            n => n.map(|n| n as usize),
        };
        match &self.logprobs {
            None | Some(Value::Null | Value::Bool(false)) if top.is_some_and(|n| n > 0) => {
                Err(ApiError::invalid("top_logprobs needs logprobs set to true"))
            }
            None | Some(Value::Null | Value::Bool(false)) => Ok(None),
            Some(Value::Bool(true)) => Ok(Some(top.unwrap_or(0))),
            Some(v) => match v.as_u64().filter(|&n| n <= 20) {
                Some(n) => Ok(Some(n as usize)),
                None => Err(ApiError::invalid(
                    "logprobs must be true, false or a count from 0 to 20",
                )),
            },
        }
    }

    /// The grammar output must follow, from `response_format` or `grammar`.
    fn grammar(&self) -> Result<Option<Arc<Grammar>>, ApiError> {
        let invalid = |e: kinetic_grammar::Error| ApiError::invalid(format!("grammar: {e}"));
        if let Some(gbnf) = &self.grammar {
            if self.response_format.is_some() {
                return Err(ApiError::invalid("use either grammar or response_format"));
            }
            return Grammar::parse(gbnf)
                .map(|g| Some(Arc::new(g)))
                .map_err(invalid);
        }
        let Some(format) = &self.response_format else {
            return Ok(None);
        };
        match format.get("type").and_then(Value::as_str) {
            Some("text") => Ok(None),
            Some("json_object") => Ok(Some(Arc::new(Grammar::any_json()))),
            Some("json_schema") => {
                let schema = format.pointer("/json_schema/schema").ok_or_else(|| {
                    ApiError::invalid("response_format.json_schema.schema is missing")
                })?;
                Grammar::from_json_schema(schema)
                    .map(|g| Some(Arc::new(g)))
                    .map_err(invalid)
            }
            _ => Err(ApiError::invalid(
                "response_format.type must be text, json_object or json_schema",
            )),
        }
    }
}

/// The grammar a receipt's constraint, from [`Common::constraint`], holds
/// output to.
pub fn constraint_grammar(constraint: &Value) -> Result<Option<Arc<Grammar>>, ApiError> {
    serde_json::from_value::<Common>(constraint.clone())
        .map_err(|e| ApiError::invalid(format!("constraint: {e}")))?
        .grammar()
}

/// Checks that every message is an object with a role and text content.
pub fn validate_messages(messages: &[Value]) -> Result<(), ApiError> {
    if messages.is_empty() {
        return Err(ApiError::invalid("messages must not be empty"));
    }
    for m in messages {
        if !m.get("role").is_some_and(Value::is_string) {
            return Err(ApiError::invalid("every message needs a string role"));
        }
        match m.get("content") {
            None | Some(Value::Null | Value::String(_)) => {}
            Some(Value::Array(parts)) => {
                for p in parts {
                    match p.get("type").and_then(Value::as_str) {
                        Some("text" | "image_url") => {}
                        _ => {
                            return Err(ApiError::invalid(
                                "content parts must be text or image_url",
                            ))
                        }
                    }
                }
            }
            Some(_) => {
                return Err(ApiError::invalid(
                    "message content must be a string or a list of parts",
                ))
            }
        }
    }
    Ok(())
}

/// The images in `messages`, in order. Each comes inline as a base64 data
/// URL; the server fetches nothing.
pub fn images(messages: &[Value]) -> Result<Vec<Vec<u8>>, ApiError> {
    let parts = messages
        .iter()
        .filter_map(|m| m.get("content").and_then(Value::as_array))
        .flatten()
        .filter(|p| p.get("type").and_then(Value::as_str) == Some("image_url"));
    parts
        .map(|p| {
            let url = p
                .pointer("/image_url/url")
                .or_else(|| p.get("image_url"))
                .and_then(Value::as_str)
                .ok_or_else(|| ApiError::invalid("image_url.url is missing"))?;
            let data = url
                .strip_prefix("data:")
                .and_then(|u| u.split_once(";base64,"))
                .ok_or_else(|| {
                    ApiError::invalid("images must be data URLs; the server fetches nothing")
                })?
                .1;
            base64::decode(data).ok_or_else(|| ApiError::invalid("an image is not valid base64"))
        })
        .collect()
}

/// The prompt of a completion request: a string or a list of one string.
pub fn completion_prompt(prompt: &Value) -> Result<&str, ApiError> {
    match prompt {
        Value::String(s) => Ok(s),
        Value::Array(items) => match &items[..] {
            [Value::String(s)] => Ok(s),
            _ => Err(ApiError::invalid(
                "prompt must be a string or a list of one string",
            )),
        },
        _ => Err(ApiError::invalid("prompt must be a string")),
    }
}

/// The identity of one response: every chunk of a stream shares it.
pub struct Meta<'m> {
    pub id: &'m str,
    pub created: u64,
    pub model: &'m str,
}

pub fn usage(c: &Completion) -> Value {
    json!({
        "prompt_tokens": c.prompt_tokens,
        "completion_tokens": c.completion_tokens,
        "total_tokens": c.prompt_tokens + c.completion_tokens,
        "prompt_tokens_details": {"cached_tokens": c.timings.cached_tokens},
    })
}

/// The `tool_calls` of a message, or of a stream's delta, which also
/// numbers them; `ids` go with the calls in order.
pub fn tool_calls(calls: &[ToolCall], ids: &[String], indexed: bool) -> Value {
    calls
        .iter()
        .zip(ids)
        .enumerate()
        .map(|(i, (c, id))| {
            let mut call = json!({
                "id": id,
                "type": "function",
                "function": {"name": c.name, "arguments": c.arguments},
            });
            if indexed {
                call["index"] = i.into();
            }
            call
        })
        .collect()
}

pub fn chat_response(meta: &Meta, c: &Completion, ids: &[String]) -> Value {
    let mut message = json!({"role": "assistant", "content": c.content});
    if !c.reasoning.is_empty() {
        message["reasoning_content"] = c.reasoning.clone().into();
    }
    if !c.tool_calls.is_empty() {
        if c.content.is_empty() {
            message["content"] = Value::Null;
        }
        message["tool_calls"] = tool_calls(&c.tool_calls, ids, false);
    }
    json!({
        "id": meta.id,
        "object": "chat.completion",
        "created": meta.created,
        "model": meta.model,
        "choices": [{"index": 0, "message": message, "logprobs": null, "finish_reason": c.finish.as_str()}],
        "usage": usage(c),
    })
}

/// One `chat.completion.chunk`; `delta` is `None` for the usage chunk.
pub fn chat_chunk(meta: &Meta, delta: Option<Value>, finish: Option<&str>) -> Value {
    let choices = match delta {
        Some(delta) => {
            json!([{"index": 0, "delta": delta, "logprobs": null, "finish_reason": finish}])
        }
        None => json!([]),
    };
    json!({
        "id": meta.id,
        "object": "chat.completion.chunk",
        "created": meta.created,
        "model": meta.model,
        "choices": choices,
    })
}

pub fn completion_response(meta: &Meta, c: &Completion) -> Value {
    let mut v = completion_chunk(meta, Some(&c.content), Some(c.finish.as_str()));
    v["usage"] = usage(c);
    v
}

/// One `text_completion` object; `text` is `None` for the usage chunk.
pub fn completion_chunk(meta: &Meta, text: Option<&str>, finish: Option<&str>) -> Value {
    let choices = match text {
        Some(text) => {
            json!([{"index": 0, "text": text, "logprobs": null, "finish_reason": finish}])
        }
        None => json!([]),
    };
    json!({
        "id": meta.id,
        "object": "text_completion",
        "created": meta.created,
        "model": meta.model,
        "choices": choices,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chat(body: Value) -> ChatRequest {
        serde_json::from_value(body).unwrap()
    }

    #[test]
    fn reads_a_full_chat_request() {
        let r = chat(json!({
            "model": "any",
            "messages": [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}],
            "temperature": 0,
            "top_p": 0.5,
            "top_k": 20,
            "min_p": 0.1,
            "seed": -1,
            "max_completion_tokens": 12,
            "max_tokens": 99,
            "stop": "\n\n",
            "repetition_penalty": 1.1,
            "stream": true,
            "stream_options": {"include_usage": true},
            "user": "ignored",
        }));
        assert!(r.common.stream() && r.common.include_usage());
        let req = r.common.request(&Sampling::default()).unwrap();
        assert_eq!(req.sampling.temperature, 0.0);
        assert_eq!(req.sampling.top_p, 0.5);
        assert_eq!(req.sampling.top_k, 20);
        assert_eq!(req.sampling.min_p, 0.1);
        assert_eq!(req.sampling.seed, Some(u64::MAX));
        assert_eq!(req.sampling.repeat_penalty, 1.1);
        assert_eq!(req.max_tokens, Some(12));
        assert_eq!(req.stop, ["\n\n"]);
        validate_messages(&r.messages).unwrap();
    }

    #[test]
    fn missing_fields_take_the_defaults() {
        let r = chat(json!({"messages": [{"role": "user", "content": "Hi"}], "stop": null}));
        let defaults = Sampling {
            temperature: 0.3,
            ..Sampling::default()
        };
        let req = r.common.request(&defaults).unwrap();
        assert_eq!(req.sampling, defaults);
        assert_eq!(req.max_tokens, None);
        assert!(req.stop.is_empty());
        assert!(!r.common.stream());
    }

    #[test]
    fn rejects_what_cannot_be_served() {
        let err = |body: Value| chat(body).common.request(&Sampling::default()).unwrap_err();
        let m = json!([{"role": "user", "content": "Hi"}]);
        assert_eq!(err(json!({"messages": m, "n": 2})).status, 400);
        assert_eq!(err(json!({"messages": m, "max_tokens": 0})).status, 400);
        assert_eq!(err(json!({"messages": m, "top_p": 1.5})).status, 400);
        let unnamed = chat(json!({"messages": m, "tools": [{"type": "function"}]}));
        assert_eq!(unnamed.tools().unwrap_err().status, 400);
    }

    #[test]
    fn tool_choice_narrows_the_tools() {
        let tool = |name: &str| json!({"type": "function", "function": {"name": name}});
        let tools = |choice: Value| {
            let m = json!([{"role": "user", "content": "Hi"}]);
            let body =
                json!({"messages": m, "tools": [tool("a"), tool("b")], "tool_choice": choice});
            chat(body).tools()
        };
        assert_eq!(tools(Value::Null).unwrap().unwrap().len(), 2);
        assert_eq!(tools(json!("auto")).unwrap().unwrap().len(), 2);
        assert_eq!(tools(json!("none")).unwrap(), None);
        let forced = json!({"type": "function", "function": {"name": "b"}});
        assert_eq!(tools(forced).unwrap().unwrap(), [tool("b")]);
        let missing = json!({"type": "function", "function": {"name": "c"}});
        assert_eq!(tools(missing).unwrap_err().status, 400);
        assert_eq!(tools(json!("sometimes")).unwrap_err().status, 400);
    }

    #[test]
    fn message_content_is_text_or_images() {
        let parts = json!([{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]);
        validate_messages(parts.as_array().unwrap()).unwrap();
        let audio = json!([{"role": "user", "content": [{"type": "input_audio"}]}]);
        assert!(validate_messages(audio.as_array().unwrap()).is_err());
        assert!(validate_messages(&[json!({"content": "no role"})]).is_err());
        assert!(validate_messages(&[]).is_err());
    }

    #[test]
    fn images_come_as_data_urls() {
        let image = |url: &str| {
            json!([{"role": "user", "content": [
                {"type": "text", "text": "What is this?"},
                {"type": "image_url", "image_url": {"url": url}},
            ]}])
        };
        let ok = image("data:image/png;base64,S2luZXRpYw==");
        validate_messages(ok.as_array().unwrap()).unwrap();
        assert_eq!(
            images(ok.as_array().unwrap()).unwrap(),
            [b"Kinetic".to_vec()]
        );
        for bad in ["https://example.com/a.png", "data:image/png;base64,***"] {
            assert!(images(image(bad).as_array().unwrap()).is_err(), "{bad}");
        }
    }

    #[test]
    fn stop_accepts_a_list() {
        let r = chat(json!({"messages": [], "stop": ["a", "b"]}));
        assert_eq!(
            r.common.request(&Sampling::default()).unwrap().stop,
            ["a", "b"]
        );
    }

    #[test]
    fn completion_prompt_forms() {
        assert_eq!(completion_prompt(&json!("x")).unwrap(), "x");
        assert_eq!(completion_prompt(&json!(["x"])).unwrap(), "x");
        assert!(completion_prompt(&json!(["x", "y"])).is_err());
        assert!(completion_prompt(&json!([1, 2])).is_err());
    }

    #[test]
    fn errors_have_the_openai_shape() {
        let body = ApiError::invalid("bad").body();
        assert_eq!(body["error"]["message"], "bad");
        assert_eq!(body["error"]["type"], "invalid_request_error");
    }
}
