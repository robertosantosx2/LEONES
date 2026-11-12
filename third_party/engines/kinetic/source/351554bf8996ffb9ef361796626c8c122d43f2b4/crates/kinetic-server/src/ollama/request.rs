//! Ollama requests, turned into the engine's prompts and requests.

use serde::Deserialize;
use serde_json::{json, Map, Value};

use crate::api::{self, ApiError, Common};
use crate::engine::Request;
use crate::Sampling;

#[derive(Debug, Deserialize)]
pub struct Generate {
    #[serde(default)]
    pub prompt: String,
    pub system: Option<String>,
    #[serde(default)]
    pub raw: bool,
    #[serde(default)]
    pub images: Vec<String>,
    pub suffix: Option<String>,
    pub template: Option<String>,
    pub context: Option<Vec<Value>>,
    #[serde(flatten)]
    pub shared: Shared,
}

impl Generate {
    /// Refuses the fields that would change the answer and are not served.
    pub fn check(&self) -> Result<(), ApiError> {
        let set = |v: &Option<String>| v.as_deref().is_some_and(|s| !s.is_empty());
        if set(&self.suffix) {
            return Err(ApiError::invalid(
                "suffix (fill in the middle) is not supported",
            ));
        }
        if set(&self.template) {
            return Err(ApiError::invalid(
                "template is not supported; the model's own chat template is used",
            ));
        }
        if self.context.as_ref().is_some_and(|c| !c.is_empty()) {
            return Err(ApiError::invalid(
                "context is not supported; send the conversation to /api/chat",
            ));
        }
        if self.raw && !self.images.is_empty() {
            return Err(ApiError::invalid("raw prompts cannot carry images"));
        }
        Ok(())
    }

    /// The prompt as a one-turn conversation.
    pub fn messages(&self) -> Vec<Value> {
        let mut messages = Vec::new();
        if let Some(system) = self.system.as_deref().filter(|s| !s.is_empty()) {
            messages.push(json!({"role": "system", "content": system}));
        }
        messages.push(json!({"role": "user", "content": self.prompt, "images": self.images}));
        messages
    }
}

#[derive(Debug, Deserialize)]
pub struct Chat {
    #[serde(default)]
    pub messages: Vec<Value>,
    #[serde(default)]
    pub tools: Vec<Value>,
    #[serde(flatten)]
    pub shared: Shared,
}

/// Fields both generation endpoints take.
#[derive(Debug, Deserialize)]
pub struct Shared {
    /// Ollama streams unless told otherwise.
    pub stream: Option<bool>,
    pub format: Option<Value>,
    #[serde(default)]
    pub options: Map<String, Value>,
    pub think: Option<Value>,
    pub keep_alive: Option<Value>,
}

impl Shared {
    pub fn stream(&self) -> bool {
        self.stream.unwrap_or(true)
    }

    /// Whether a request that sends nothing to answer asks to unload the
    /// model rather than load it.
    pub fn unloads(&self) -> bool {
        matches!(&self.keep_alive, Some(Value::Number(n)) if n.as_f64() == Some(0.0))
            || matches!(&self.keep_alive, Some(Value::String(s)) if s.trim_end_matches(['s', 'm', 'h']) == "0")
    }

    /// `enable_thinking` for the chat template; `None` keeps its default.
    pub fn thinking(&self) -> Option<bool> {
        match &self.think {
            None | Some(Value::Null) => None,
            Some(Value::Bool(b)) => Some(*b),
            // "low", "medium" and "high" all think
            Some(_) => Some(true),
        }
    }

    /// The generation `options` and `format` ask for, with `defaults` for
    /// what they leave out.
    pub fn request(&self, defaults: &Sampling, context: usize) -> Result<Request, ApiError> {
        let o = &self.options;
        let mut openai = Map::new();
        for key in [
            "temperature",
            "top_k",
            "top_p",
            "min_p",
            "seed",
            "stop",
            "repeat_penalty",
            "presence_penalty",
            "frequency_penalty",
        ] {
            if let Some(v) = o.get(key).filter(|v| !v.is_null()) {
                openai.insert(key.into(), v.clone());
            }
        }
        // -1 means no limit and -2 fill the context, both the engine's default
        if let Some(n) = o
            .get("num_predict")
            .and_then(Value::as_i64)
            .filter(|&n| n > 0)
        {
            openai.insert("max_tokens".into(), n.into());
        }
        match &self.format {
            None | Some(Value::Null) => {}
            Some(Value::String(s)) if s.is_empty() => {}
            Some(Value::String(s)) if s == "json" => {
                openai.insert("response_format".into(), json!({"type": "json_object"}));
            }
            Some(schema @ Value::Object(_)) => {
                openai.insert(
                    "response_format".into(),
                    json!({"type": "json_schema", "json_schema": {"schema": schema}}),
                );
            }
            Some(_) => {
                return Err(ApiError::invalid(
                    "format must be \"json\" or a JSON schema",
                ))
            }
        }
        let common: Common = serde_json::from_value(Value::Object(openai))
            .map_err(|e| ApiError::invalid(format!("options: {e}")))?;
        let mut request = common.request(defaults)?;
        match o.get("repeat_last_n").and_then(Value::as_i64) {
            Some(-1) => request.sampling.repeat_last_n = context,
            Some(n) if n >= 0 => request.sampling.repeat_last_n = n as usize,
            _ => {}
        }
        Ok(request)
    }
}

/// Ollama messages as the engine reads OpenAI ones: images become content
/// parts, `thinking` the reasoning and `tool_name` the name.
pub fn openai_messages(messages: &[Value]) -> Result<Vec<Value>, ApiError> {
    let mut out = Vec::with_capacity(messages.len());
    for m in messages {
        let mut m = m
            .as_object()
            .cloned()
            .ok_or_else(|| ApiError::invalid("every message must be an object"))?;
        if let Some(images) = m.remove("images").filter(|v| !v.is_null()) {
            let images = images
                .as_array()
                .filter(|a| a.iter().all(Value::is_string))
                .ok_or_else(|| ApiError::invalid("images must be a list of base64 strings"))?;
            if !images.is_empty() {
                let text = m.get("content").and_then(Value::as_str).unwrap_or_default();
                let mut parts = vec![json!({"type": "text", "text": text})];
                for image in images {
                    let url = format!("data:image;base64,{}", image.as_str().unwrap_or_default());
                    parts.push(json!({"type": "image_url", "image_url": {"url": url}}));
                }
                m.insert("content".into(), parts.into());
            }
        }
        if let Some(thinking) = m.remove("thinking") {
            m.insert("reasoning_content".into(), thinking);
        }
        if let Some(name) = m.get("tool_name").cloned() {
            m.entry("name").or_insert(name);
        }
        out.push(Value::Object(m));
    }
    api::validate_messages(&out)?;
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn shared(body: Value) -> Shared {
        serde_json::from_value(body).unwrap()
    }

    #[test]
    fn options_map_onto_the_request() {
        let s = shared(json!({"options": {
            "temperature": 0, "top_k": 5, "top_p": 0.5, "seed": 42,
            "num_predict": 12, "stop": ["\n"], "repeat_last_n": -1, "num_ctx": 4096,
        }}));
        assert!(s.stream());
        let r = s.request(&Sampling::default(), 2048).unwrap();
        assert_eq!(r.sampling.temperature, 0.0);
        assert_eq!(r.sampling.top_k, 5);
        assert_eq!(r.sampling.top_p, 0.5);
        assert_eq!(r.sampling.seed, Some(42));
        assert_eq!(r.sampling.repeat_last_n, 2048);
        assert_eq!(r.max_tokens, Some(12));
        assert_eq!(r.stop, ["\n"]);
        assert!(r.grammar.is_none());

        let r = shared(json!({"options": {"num_predict": -1}}))
            .request(&Sampling::default(), 2048)
            .unwrap();
        assert_eq!(r.max_tokens, None);
        assert!(shared(json!({"options": {"top_p": 2}}))
            .request(&Sampling::default(), 8)
            .is_err());
    }

    #[test]
    fn format_asks_for_json() {
        let grammar = |format: Value| {
            shared(json!({"format": format}))
                .request(&Sampling::default(), 8)
                .map(|r| r.grammar.is_some())
        };
        assert_eq!(grammar(json!("json")), Ok(true));
        assert_eq!(grammar(json!("")), Ok(false));
        let schema =
            json!({"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]});
        assert_eq!(grammar(schema), Ok(true));
        assert!(grammar(json!("yaml")).is_err());
    }

    #[test]
    fn think_and_keep_alive() {
        assert_eq!(shared(json!({})).thinking(), None);
        assert_eq!(shared(json!({"think": false})).thinking(), Some(false));
        assert_eq!(shared(json!({"think": "high"})).thinking(), Some(true));
        assert!(shared(json!({"keep_alive": 0})).unloads());
        assert!(shared(json!({"keep_alive": "0s"})).unloads());
        assert!(!shared(json!({"keep_alive": "5m"})).unloads());
    }

    #[test]
    fn messages_carry_images_tools_and_thinking() {
        let m = openai_messages(&[
            json!({"role": "user", "content": "What is this?", "images": ["S2luZXRpYw=="]}),
            json!({"role": "assistant", "content": "", "thinking": "hm",
                   "tool_calls": [{"function": {"name": "f", "arguments": {"x": 1}}}]}),
            json!({"role": "tool", "content": "42", "tool_name": "f"}),
        ])
        .unwrap();
        assert_eq!(
            m[0]["content"][1]["image_url"]["url"],
            "data:image;base64,S2luZXRpYw=="
        );
        assert_eq!(api::images(&m).unwrap(), [b"Kinetic".to_vec()]);
        assert_eq!(m[1]["reasoning_content"], "hm");
        assert_eq!(m[2]["name"], "f");
        assert!(openai_messages(&[json!({"content": "no role"})]).is_err());
    }

    #[test]
    fn generate_refuses_what_it_cannot_honour() {
        let g = |body: Value| serde_json::from_value::<Generate>(body).unwrap().check();
        assert!(g(json!({"prompt": "x"})).is_ok());
        assert!(g(json!({"prompt": "x", "suffix": "y"})).is_err());
        assert!(g(json!({"prompt": "x", "context": [1, 2]})).is_err());
        assert!(g(json!({"prompt": "x", "raw": true, "images": ["AA=="]})).is_err());
    }
}
