//! llama-server's own API next to the OpenAI one, so scripts and apps made
//! for llama.cpp's server work unchanged: `/completion`, `/tokenize`,
//! `/detokenize`, `/props`, `/slots` and `/embedding`.

use std::io::Write;
use std::time::Duration;

use kinetic_tokenizer::Tokenizer;
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde_json::{json, Map, Value};

use crate::api::{self, ApiError, Common};
use crate::embeddings::Embeddings;
use crate::engine::{Completion, Engine, Finish, Prompt, Request};
use crate::http::Head;
use crate::ollama::local_origin;
use crate::server::{expect, send_json, Events};
use crate::Sampling;

/// The seed llama.cpp reads as "pick a fresh one".
const RANDOM_SEED: i64 = u32::MAX as i64;

/// Serves `head` on a text model if it is one of llama-server's endpoints.
pub fn route(
    engine: &Engine,
    head: &Head,
    body: &[u8],
    out: &mut impl Write,
) -> Option<Result<(), ApiError>> {
    if !matches!(
        head.path.as_str(),
        "/completion"
            | "/completions"
            | "/tokenize"
            | "/detokenize"
            | "/props"
            | "/slots"
            | "/embedding"
            | "/embeddings"
    ) {
        return None;
    }
    Some(local_origin(head).and_then(|_| {
        match head.path.as_str() {
            "/completion" | "/completions" => {
                expect(head, "POST").and_then(|_| completion(engine, parse(body)?, out))
            }
            "/tokenize" => expect(head, "POST")
                .and_then(|_| send_json(out, &tokenize(engine.tokenizer(), parse(body)?))),
            "/detokenize" => expect(head, "POST").and_then(|_| {
                let req: Detokenize = parse(body)?;
                send_json(
                    out,
                    &json!({"content": engine.tokenizer().decode(&req.tokens)}),
                )
            }),
            "/props" => expect(head, "GET").and_then(|_| send_json(out, &props(engine))),
            "/slots" => expect(head, "GET").and_then(|_| send_json(out, &slots(engine))),
            _ => Err(ApiError {
                status: 501,
                message: format!(
                    "{} generates text; serve an embedding model for {}",
                    engine.name(),
                    head.path
                ),
            }),
        }
    }))
}

/// Serves `/embedding` on an embedding model, in llama-server's shape.
pub fn route_embeddings(
    e: &Embeddings,
    head: &Head,
    body: &[u8],
    out: &mut impl Write,
) -> Option<Result<(), ApiError>> {
    if !matches!(head.path.as_str(), "/embedding" | "/embeddings") {
        return None;
    }
    Some(
        local_origin(head)
            .and_then(|_| expect(head, "POST"))
            .and_then(|_| {
                let req: Embed = parse(body)?;
                let texts = match req.content {
                    Value::String(s) => vec![s],
                    Value::Array(items) => items
                        .into_iter()
                        .map(|i| match i {
                            Value::String(s) => Ok(s),
                            _ => Err(ApiError::invalid("content must be text or a list of texts")),
                        })
                        .collect::<Result<_, _>>()?,
                    _ => return Err(ApiError::invalid("content must be text or a list of texts")),
                };
                let (vectors, _) = e.embed_texts(&texts, true)?;
                let answer: Vec<Value> = vectors
                    .into_iter()
                    .enumerate()
                    .map(|(i, v)| json!({"index": i, "embedding": [v]}))
                    .collect();
                send_json(out, &Value::from(answer))
            }),
    )
}

// llama-server reads any content type as JSON; web pages are kept out by
// their Origin instead, as on the Ollama routes.
fn parse<T: DeserializeOwned>(body: &[u8]) -> Result<T, ApiError> {
    serde_json::from_slice(body).map_err(|e| ApiError::invalid(format!("invalid JSON: {e}")))
}

#[derive(Deserialize)]
struct Detokenize {
    tokens: Vec<u32>,
}

#[derive(Deserialize)]
struct Embed {
    #[serde(alias = "input")]
    content: Value,
}

#[derive(Deserialize)]
struct Tokenize {
    content: String,
    #[serde(default)]
    add_special: bool,
    #[serde(default = "yes")]
    parse_special: bool,
    #[serde(default)]
    with_pieces: bool,
}

fn yes() -> bool {
    true
}

fn tokenize(t: &Tokenizer, req: Tokenize) -> Value {
    let mut ids = t.encode(&req.content, req.parse_special);
    if !req.add_special {
        // encoding nothing yields exactly the tokens added around any text
        let added = t.encode("", false);
        let lead = usize::from(t.bos().is_some() && added.first() == t.bos().as_ref());
        ids.drain(..lead.min(ids.len()));
        ids.truncate(ids.len().saturating_sub(added.len() - lead));
    }
    let tokens: Vec<Value> = if req.with_pieces {
        ids.iter()
            .map(|&id| {
                let piece = t.piece(id);
                let piece = match std::str::from_utf8(piece) {
                    Ok(s) => json!(s),
                    Err(_) => json!(piece),
                };
                json!({"id": id, "piece": piece})
            })
            .collect()
    } else {
        ids.iter().map(|&id| id.into()).collect()
    };
    json!({ "tokens": tokens })
}

/// The prompt of a `/completion` request: text, a list of one text, or
/// token ids.
fn prompt_text(engine: &Engine, prompt: &Value) -> Result<String, ApiError> {
    match prompt {
        Value::Array(items) if !items.is_empty() && items.iter().all(Value::is_u64) => {
            // shortcut: ids are decoded and tokenized again, which can split
            // unusual text differently; pass ids through if a client needs that
            let ids = token_ids(items)
                .ok_or_else(|| ApiError::invalid("prompt token ids must be below 2^32"))?;
            Ok(engine.tokenizer().decode(&ids))
        }
        p => api::completion_prompt(p).map(str::to_owned),
    }
}

fn token_ids(items: &[Value]) -> Option<Vec<u32>> {
    items
        .iter()
        .map(|id| u32::try_from(id.as_u64()?).ok())
        .collect()
}

/// llama-server's generation fields in the shape the OpenAI routes read.
fn common(mut fields: Map<String, Value>) -> Result<Common, ApiError> {
    let mut n_predict = None;
    for key in ["n_predict", "max_tokens"] {
        match fields.remove(key) {
            None | Some(Value::Null) => {}
            Some(v) => {
                let n = v
                    .as_i64()
                    .ok_or_else(|| ApiError::invalid(format!("{key} must be a number")))?;
                n_predict = n_predict.or(Some(n));
            }
        }
    }
    if let Some(n) = n_predict.filter(|&n| n > 0) {
        fields.insert("max_tokens".into(), n.into());
    }
    if fields
        .get("seed")
        .and_then(Value::as_i64)
        .is_some_and(|s| s == -1 || s == RANDOM_SEED)
    {
        fields.remove("seed");
    }
    if fields.get("grammar").and_then(Value::as_str) == Some("") {
        fields.remove("grammar");
    }
    if let Some(schema) = fields.remove("json_schema") {
        fields
            .entry("response_format")
            .or_insert_with(|| json!({"type": "json_schema", "json_schema": {"schema": schema}}));
    }
    serde_json::from_value(Value::Object(fields)).map_err(|e| ApiError::invalid(e.to_string()))
}

fn completion(
    engine: &Engine,
    mut fields: Map<String, Value>,
    out: &mut impl Write,
) -> Result<(), ApiError> {
    let text = prompt_text(
        engine,
        &fields
            .remove("prompt")
            .ok_or_else(|| ApiError::invalid("prompt is missing"))?,
    )?;
    let common = common(fields)?;
    let request = common.request(engine.default_sampling())?;
    let stream = common.stream();
    let prompt = Prompt::raw(text.as_str());
    let invalid = |e: crate::RequestError| ApiError::invalid(e.0);
    if !stream {
        let c = engine
            .complete(&prompt, &request, &mut |_, _| true)
            .map_err(invalid)?;
        return send_json(out, &last(engine, &text, &request, false, &c, &c.content));
    }
    let evaluated = engine.tokenizer().encode(&text, true).len();
    let mut events = Events::new(out, None);
    let c = engine
        .complete(&prompt, &request, &mut |part, predicted| {
            part.content.is_empty()
                || events.send(&json!({
                    "index": 0,
                    "content": part.content,
                    "tokens": [],
                    "stop": false,
                    "id_slot": -1,
                    "tokens_predicted": predicted,
                    "tokens_evaluated": evaluated,
                }))
        })
        .map_err(invalid)?;
    events.send(&last(engine, &text, &request, true, &c, ""));
    Ok(())
}

/// The final object of a completion, whole or streamed.
fn last(
    engine: &Engine,
    prompt: &str,
    request: &Request,
    stream: bool,
    c: &Completion,
    content: &str,
) -> Value {
    let t = &c.timings;
    let ms = |d: Duration| d.as_secs_f64() * 1e3;
    let per_token = |d: Duration, n: usize| if n > 0 { ms(d) / n as f64 } else { 0.0 };
    let per_second = |d: Duration, n: usize| {
        if d.is_zero() {
            0.0
        } else {
            n as f64 / d.as_secs_f64()
        }
    };
    let prompt_n = c.prompt_tokens.saturating_sub(t.cached_tokens);
    json!({
        "index": 0,
        "content": content,
        "tokens": [],
        "id_slot": 0,
        "stop": true,
        "model": engine.name(),
        "tokens_predicted": c.completion_tokens,
        "tokens_evaluated": c.prompt_tokens,
        "generation_settings": settings(&request.sampling, request.max_tokens, &request.stop, stream),
        "prompt": prompt,
        "has_new_line": c.content.contains('\n'),
        "truncated": false,
        // shortcut: the engine does not say whether a stop string or the
        // end of turn stopped it, so both read as eos
        "stop_type": if c.finish == Finish::Length { "limit" } else { "eos" },
        "stopping_word": "",
        "tokens_cached": c.prompt_tokens + c.completion_tokens,
        "timings": {
            "cache_n": t.cached_tokens,
            "prompt_n": prompt_n,
            "prompt_ms": ms(t.prefill),
            "prompt_per_token_ms": per_token(t.prefill, prompt_n),
            "prompt_per_second": per_second(t.prefill, prompt_n),
            "predicted_n": c.completion_tokens,
            "predicted_ms": ms(t.decode),
            "predicted_per_token_ms": per_token(t.decode, c.completion_tokens),
            "predicted_per_second": per_second(t.decode, c.completion_tokens),
        },
    })
}

/// The sampling settings llama-server reports, those Kinetic honours.
fn settings(s: &Sampling, max_tokens: Option<usize>, stop: &[String], stream: bool) -> Value {
    let n_predict = max_tokens.map_or(-1, |n| n as i64);
    json!({
        "seed": s.seed.unwrap_or(RANDOM_SEED as u64),
        "temperature": s.temperature,
        "top_k": s.top_k,
        "top_p": s.top_p,
        "min_p": s.min_p,
        "repeat_last_n": s.repeat_last_n,
        "repeat_penalty": s.repeat_penalty,
        "presence_penalty": s.presence_penalty,
        "frequency_penalty": s.frequency_penalty,
        "stop": stop,
        "max_tokens": n_predict,
        "n_predict": n_predict,
        "stream": stream,
        // samplers Kinetic does not have, reported as llama.cpp's off values
        "dynatemp_range": 0.0,
        "dynatemp_exponent": 1.0,
        "top_n_sigma": -1.0,
        "xtc_probability": 0.0,
        "xtc_threshold": 0.1,
        "typical_p": 1.0,
        "dry_multiplier": 0.0,
        "mirostat": 0,
        "n_keep": 0,
        "ignore_eos": false,
        "logit_bias": [],
        "n_probs": 0,
        "min_keep": 0,
        "samplers": ["penalties", "top_k", "top_p", "min_p", "temperature"],
    })
}

fn props(engine: &Engine) -> Value {
    let t = engine.tokenizer();
    let token = |id: Option<u32>| id.map(|id| t.decode(&[id])).unwrap_or_default();
    let (slots, _) = engine.slots();
    json!({
        "default_generation_settings": {
            "params": settings(engine.default_sampling(), None, &[], false),
            "n_ctx": engine.context_length(),
        },
        "total_slots": slots,
        "model_alias": engine.name(),
        "model_path": engine.name(),
        "modalities": {"vision": engine.sees_images(), "video": false, "audio": false},
        "endpoint_slots": true,
        "endpoint_props": false,
        "endpoint_metrics": true,
        "chat_template": engine.info().chat_template.clone().unwrap_or_default(),
        "bos_token": token(t.bos()),
        "eos_token": token(t.eos()),
        "build_info": concat!("kinetic ", env!("CARGO_PKG_VERSION")),
    })
}

fn slots(engine: &Engine) -> Value {
    engine
        .slot_states()
        .into_iter()
        .enumerate()
        .map(|(id, slot)| {
            let mut v = json!({
                "id": id,
                "n_ctx": engine.context_length(),
                "speculative": false,
                "is_processing": slot.processing,
            });
            let (Some(task), Some(req)) = (slot.task, &slot.request) else {
                return v;
            };
            let has_next = slot.processing && slot.decoded < slot.max_tokens;
            let fields = json!({
                "id_task": task,
                "n_prompt_tokens": slot.prompt_tokens,
                "n_prompt_tokens_processed": slot.prompt_tokens - slot.cached_tokens,
                "n_prompt_tokens_cache": slot.cached_tokens,
                "params": settings(&req.sampling, req.max_tokens, &req.stop, false),
                "next_token": [{
                    "has_next_token": has_next,
                    "has_new_line": false,
                    "n_remain": slot.max_tokens.saturating_sub(slot.decoded),
                    "n_decoded": slot.decoded,
                }],
                "prompt": slot.prompt,
            });
            if let (Value::Object(v), Value::Object(f)) = (&mut v, fields) {
                v.extend(f);
            }
            v
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fields(v: Value) -> Map<String, Value> {
        v.as_object().unwrap().clone()
    }

    #[test]
    fn llama_fields_become_a_request() {
        let req = common(fields(json!({
            "n_predict": 8,
            "seed": -1,
            "grammar": "",
            "temperature": 0,
            "stop": ["\n"],
            "cache_prompt": true,
            "n_probs": 0,
        })))
        .unwrap()
        .request(&Sampling::default())
        .unwrap();
        assert_eq!(req.max_tokens, Some(8));
        assert_eq!(req.sampling.seed, None);
        assert_eq!(req.sampling.temperature, 0.0);
        assert_eq!(req.stop, ["\n"]);
        assert!(req.grammar.is_none());
    }

    #[test]
    fn minus_one_predicts_without_limit() {
        let req = common(fields(json!({"n_predict": -1, "seed": 7})))
            .unwrap()
            .request(&Sampling::default())
            .unwrap();
        assert_eq!(req.max_tokens, None);
        assert_eq!(req.sampling.seed, Some(7));
    }

    #[test]
    fn n_predict_must_be_a_number() {
        let e = common(fields(json!({"n_predict": "64"}))).err().unwrap();
        assert_eq!(e.status, 400);
        assert_eq!(e.message, "n_predict must be a number");
        let req = common(fields(json!({"n_predict": null, "max_tokens": 3})))
            .unwrap()
            .request(&Sampling::default())
            .unwrap();
        assert_eq!(req.max_tokens, Some(3));
    }

    #[test]
    fn token_ids_past_u32_are_refused() {
        assert_eq!(
            token_ids(&[json!(7), json!(u32::MAX)]),
            Some(vec![7, u32::MAX])
        );
        assert_eq!(token_ids(&[json!(7), json!(1u64 << 32)]), None);
        let bias = json!({"logit_bias": {"4294967296": 1}});
        let e = common(fields(bias)).unwrap().request(&Sampling::default());
        assert!(e.is_err());
    }

    #[test]
    fn json_schema_constrains_output() {
        let schema = json!({"type": "object", "properties": {"a": {"type": "integer"}}});
        let req = common(fields(json!({ "json_schema": schema })))
            .unwrap()
            .request(&Sampling::default())
            .unwrap();
        assert!(req.grammar.is_some());
    }
}
