//! The Ollama API next to the OpenAI one, so apps written for Ollama work
//! unchanged: `/api/tags`, `/api/ps`, `/api/show`, `/api/version`, `/api/generate`,
//! `/api/chat`, `/api/embed` and `/api/embeddings`.

mod request;
mod response;

use std::io::{self, Write};
use std::time::Instant;

use serde::de::DeserializeOwned;
use serde_json::{json, Map, Value};

use crate::api::{self, ApiError};
use crate::embeddings::Embeddings;
use crate::engine::{Completion, Engine, Prompt};
use crate::http::{self, Head};
use crate::model_info::ModelInfo;
use crate::server::{expect, send_json};
use request::{Chat, Generate, Shared};

/// Whether `path` belongs to this API.
pub fn handles(path: &str) -> bool {
    path == "/" || path.starts_with("/api/")
}

/// Serves an Ollama request on a text model.
pub fn route(engine: &Engine, head: &Head, body: &[u8], out: &mut impl Write) {
    if let Err(e) = local_origin(head).and_then(|_| text_route(engine, head, body, out)) {
        send_error(out, &e);
    }
}

/// Serves an Ollama request on an embedding model.
pub fn route_embeddings(e: &Embeddings, head: &Head, body: &[u8], out: &mut impl Write) {
    if let Err(err) = local_origin(head).and_then(|_| embedding_route(e, head, body, out)) {
        send_error(out, &err);
    }
}

fn text_route(
    engine: &Engine,
    head: &Head,
    body: &[u8],
    out: &mut impl Write,
) -> Result<(), ApiError> {
    let name = engine.name();
    let caps = capabilities(engine);
    let model = Served {
        name,
        info: engine.info(),
        context: engine.context_length(),
        capabilities: &caps,
    };
    if let Some(answer) = common(&model, head, body, out) {
        return answer;
    }
    match head.path.as_str() {
        "/api/generate" => expect(head, "POST")
            .and_then(|_| parse(body))
            .and_then(|r| generate(engine, r, out)),
        "/api/chat" => expect(head, "POST")
            .and_then(|_| parse(body))
            .and_then(|r| chat(engine, r, out)),
        "/api/embed" | "/api/embeddings" => Err(ApiError::invalid(format!(
            "{name} generates text; serve an embedding model for {}",
            head.path
        ))),
        _ => Err(unknown(head)),
    }
}

fn embedding_route(
    e: &Embeddings,
    head: &Head,
    body: &[u8],
    out: &mut impl Write,
) -> Result<(), ApiError> {
    let model = Served {
        name: e.name(),
        info: e.info(),
        context: e.context_length,
        capabilities: &["embedding"],
    };
    if let Some(answer) = common(&model, head, body, out) {
        return answer;
    }
    match head.path.as_str() {
        "/api/embed" => expect(head, "POST")
            .and_then(|_| parse(body))
            .and_then(|r| embed(e, r, out)),
        "/api/embeddings" => expect(head, "POST")
            .and_then(|_| parse(body))
            .and_then(|r| embeddings(e, r, out)),
        "/api/generate" | "/api/chat" => Err(ApiError::invalid(format!(
            "{} is an embedding model; use /api/embed",
            e.name()
        ))),
        _ => Err(unknown(head)),
    }
}

/// Refuses requests web pages send. Ollama clients send any content type,
/// so unlike the OpenAI routes these cannot rely on a JSON-only preflight;
/// browsers mark every cross-origin request with its `Origin`.
pub(crate) fn local_origin(head: &Head) -> Result<(), ApiError> {
    let Some(origin) = head.header("origin") else {
        return Ok(());
    };
    let rest = origin.split_once("://").map_or(origin, |(_, rest)| rest);
    let host = match rest.rsplit_once(':') {
        Some((host, port)) if !port.is_empty() && port.bytes().all(|b| b.is_ascii_digit()) => host,
        _ => rest,
    };
    if matches!(host, "localhost" | "127.0.0.1" | "[::1]") {
        Ok(())
    } else {
        Err(ApiError {
            status: 403,
            message: format!("requests from {origin} are refused"),
        })
    }
}

fn parse<T: DeserializeOwned>(body: &[u8]) -> Result<T, ApiError> {
    serde_json::from_slice(body).map_err(|e| ApiError::invalid(format!("invalid JSON: {e}")))
}

/// The model a server runs, as the listings describe it.
struct Served<'m> {
    name: &'m str,
    info: &'m ModelInfo,
    context: usize,
    capabilities: &'m [&'m str],
}

/// The endpoints every model answers; `None` for the rest.
fn common(
    model: &Served,
    head: &Head,
    body: &[u8],
    out: &mut impl Write,
) -> Option<Result<(), ApiError>> {
    Some(match head.path.as_str() {
        "/" => {
            let _ = http::write_response(out, 200, "text/plain", b"Kinetic is running");
            Ok(())
        }
        "/api/version" => {
            expect(head, "GET").and_then(|_| send_json(out, &json!({"version": response::VERSION})))
        }
        "/api/tags" => expect(head, "GET")
            .and_then(|_| send_json(out, &response::tags(model.name, model.info))),
        "/api/ps" => expect(head, "GET")
            .and_then(|_| send_json(out, &response::ps(model.name, model.info, model.context))),
        "/api/show" => expect(head, "POST")
            .and_then(|_| parse::<Value>(body))
            .and_then(|_| send_json(out, &response::show(model.info, model.capabilities))),
        _ => return None,
    })
}

fn capabilities(engine: &Engine) -> Vec<&'static str> {
    let template = engine.info().chat_template.as_deref().unwrap_or_default();
    let mut c = vec!["completion"];
    if template.contains("tools") {
        c.push("tools");
    }
    if template.contains("<think>") || template.contains("enable_thinking") {
        c.push("thinking");
    }
    if engine.sees_images() {
        c.push("vision");
    }
    c
}

fn unknown(head: &Head) -> ApiError {
    ApiError {
        status: 404,
        message: format!(
            "{} {} is not served; Kinetic serves one model and never downloads",
            head.method, head.path
        ),
    }
}

fn send_error(out: &mut impl Write, e: &ApiError) {
    let body = json!({"error": e.message}).to_string();
    let _ = http::write_response(out, e.status, "application/json", body.as_bytes());
}

fn generate(engine: &Engine, req: Generate, out: &mut impl Write) -> Result<(), ApiError> {
    req.check()?;
    let name = engine.name();
    if req.prompt.is_empty() && req.images.is_empty() {
        let reason = if req.shared.unloads() {
            "unload"
        } else {
            "load"
        };
        return send_json(out, &response::loaded(name, false, reason));
    }
    let prompt = if req.raw || engine.info().chat_template.is_none() {
        Prompt::raw(req.prompt.clone())
    } else {
        chat_prompt(engine, &req.messages(), &[], &req.shared)?
    };
    run(
        engine,
        &prompt,
        &req.shared,
        out,
        &|part| response::generate_piece(name, part),
        &|c, streamed| {
            let mut m = response::head(name);
            let text = if streamed { "" } else { c.content.as_str() };
            m.insert("response".into(), text.into());
            if !streamed && !c.reasoning.is_empty() {
                m.insert("thinking".into(), c.reasoning.clone().into());
            }
            m
        },
    )
}

fn chat(engine: &Engine, req: Chat, out: &mut impl Write) -> Result<(), ApiError> {
    let name = engine.name();
    if req.messages.is_empty() {
        let reason = if req.shared.unloads() {
            "unload"
        } else {
            "load"
        };
        return send_json(out, &response::loaded(name, true, reason));
    }
    let prompt = chat_prompt(engine, &req.messages, &req.tools, &req.shared)?;
    run(
        engine,
        &prompt,
        &req.shared,
        out,
        &|part| response::chat_piece(name, response::message(&part.content, &part.reasoning, &[])),
        &|c, streamed| {
            let mut m = response::head(name);
            let message = if streamed {
                response::message("", "", &[])
            } else {
                response::message(&c.content, &c.reasoning, &c.tool_calls)
            };
            m.insert("message".into(), message);
            m
        },
    )
}

fn chat_prompt(
    engine: &Engine,
    messages: &[Value],
    tools: &[Value],
    shared: &Shared,
) -> Result<Prompt, ApiError> {
    let messages = request::openai_messages(messages)?;
    let mut options = Map::new();
    if let Some(think) = shared.thinking() {
        options.insert("enable_thinking".into(), think.into());
    }
    if !tools.is_empty() {
        options.insert("tools".into(), tools.to_vec().into());
    }
    let mut prompt = engine
        .chat_prompt(&messages, &options)
        .map_err(|e| ApiError::invalid(e.0))?;
    prompt.images = api::images(&messages)?;
    Ok(prompt)
}

type Piece<'a> = dyn Fn(&crate::Split) -> Value + 'a;
type Last<'a> = dyn Fn(&Completion, bool) -> Map<String, Value> + 'a;

/// Generates and answers with one object, or streams one line per piece
/// and ends with the statistics.
fn run(
    engine: &Engine,
    prompt: &Prompt,
    shared: &Shared,
    out: &mut impl Write,
    piece: &Piece,
    last: &Last,
) -> Result<(), ApiError> {
    let start = Instant::now();
    let request = shared.request(engine.default_sampling(), engine.context_length())?;
    let invalid = |e: crate::RequestError| ApiError::invalid(e.0);
    if !shared.stream() {
        let c = engine
            .complete(prompt, &request, &mut |_, _| true)
            .map_err(invalid)?;
        return send_json(out, &response::done(last(&c, false), &c, start.elapsed()));
    }
    let mut lines = Lines::new(out);
    let c = engine
        .complete(prompt, &request, &mut |part, _| lines.send(&piece(part)))
        .map_err(invalid)?;
    if !c.tool_calls.is_empty() {
        let message = response::message("", "", &c.tool_calls);
        lines.send(&response::chat_piece(engine.name(), message));
    }
    lines.send(&response::done(last(&c, true), &c, start.elapsed()));
    Ok(())
}

#[derive(serde::Deserialize)]
struct EmbedRequest {
    input: Value,
    #[serde(default = "yes")]
    truncate: bool,
    dimensions: Option<usize>,
}

fn yes() -> bool {
    true
}

fn embed(e: &Embeddings, req: EmbedRequest, out: &mut impl Write) -> Result<(), ApiError> {
    let start = Instant::now();
    let texts: Vec<String> = match req.input {
        Value::String(s) => vec![s],
        Value::Array(items) => items
            .into_iter()
            .map(|i| match i {
                Value::String(s) => Ok(s),
                _ => Err(ApiError::invalid(
                    "input must be a string or a list of strings",
                )),
            })
            .collect::<Result<_, _>>()?,
        _ => {
            return Err(ApiError::invalid(
                "input must be a string or a list of strings",
            ))
        }
    };
    let (mut vectors, tokens) = e.embed_texts(&texts, req.truncate)?;
    if let Some(n) = req.dimensions {
        for v in &mut vectors {
            shorten(v, n)?;
        }
    }
    send_json(
        out,
        &json!({
            "model": e.name(),
            "embeddings": vectors,
            "total_duration": start.elapsed().as_nanos() as u64,
            "load_duration": 0,
            "prompt_eval_count": tokens,
        }),
    )
}

/// Keeps the first `n` values and rescales them to unit length, as
/// Matryoshka-trained models expect.
fn shorten(v: &mut Vec<f32>, n: usize) -> Result<(), ApiError> {
    if n == 0 || n > v.len() {
        return Err(ApiError::invalid(format!(
            "dimensions must be between 1 and {}",
            v.len()
        )));
    }
    v.truncate(n);
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        v.iter_mut().for_each(|x| *x /= norm);
    }
    Ok(())
}

#[derive(serde::Deserialize)]
struct EmbeddingsRequest {
    prompt: String,
}

fn embeddings(
    e: &Embeddings,
    req: EmbeddingsRequest,
    out: &mut impl Write,
) -> Result<(), ApiError> {
    let (vectors, _) = e.embed_texts(&[req.prompt], true)?;
    send_json(out, &json!({"embedding": vectors[0]}))
}

/// A stream of JSON objects, one per line, that starts with its first
/// object, so errors found before any output still get a plain response.
struct Lines<'w, W: Write> {
    out: &'w mut W,
    started: bool,
    open: bool,
}

impl<'w, W: Write> Lines<'w, W> {
    fn new(out: &'w mut W) -> Self {
        Lines {
            out,
            started: false,
            open: true,
        }
    }

    /// Sends one object; false once the client is gone.
    fn send(&mut self, v: &Value) -> bool {
        if self.open {
            self.open = self.try_send(v).is_ok();
        }
        self.open
    }

    fn try_send(&mut self, v: &Value) -> io::Result<()> {
        if !self.started {
            self.started = true;
            http::write_stream_head(self.out, "application/x-ndjson")?;
        }
        let mut line = v.to_string();
        line.push('\n');
        self.out.write_all(line.as_bytes())?;
        self.out.flush()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_local_pages_may_call() {
        let head = |origin: &str| {
            let raw = format!("POST /api/chat HTTP/1.1\r\nOrigin: {origin}\r\n\r\n");
            http::read_head(&mut raw.as_bytes()).unwrap()
        };
        for ok in [
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://[::1]:8080",
        ] {
            assert!(local_origin(&head(ok)).is_ok(), "{ok}");
        }
        for bad in ["https://example.com", "http://localhost.evil.com", "null"] {
            assert_eq!(local_origin(&head(bad)).unwrap_err().status, 403, "{bad}");
        }
        let plain = http::read_head(&mut "GET / HTTP/1.1\r\n\r\n".as_bytes()).unwrap();
        assert!(local_origin(&plain).is_ok());
    }

    #[test]
    fn shortened_vectors_are_unit_length() {
        let mut v = vec![3.0, 4.0, 12.0];
        shorten(&mut v, 2).unwrap();
        assert_eq!(v, [0.6, 0.8]);
        assert!(shorten(&mut v, 3).is_err());
    }

    #[test]
    fn lines_are_ndjson() {
        let mut out = Vec::new();
        let mut lines = Lines::new(&mut out);
        assert!(lines.send(&json!({"a": 1})));
        assert!(lines.send(&json!({"done": true})));
        let text = String::from_utf8(out).unwrap();
        assert!(text.starts_with("HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson\r\n"));
        assert!(
            text.ends_with("\r\n\r\n{\"a\":1}\n{\"done\":true}\n"),
            "{text}"
        );
    }
}
