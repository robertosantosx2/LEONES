//! Routes HTTP requests to the engine.

use std::hash::{BuildHasher, RandomState};
use std::io::{self, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::de::DeserializeOwned;
use serde_json::{json, Map, Value};

use crate::api::{self, ApiError, ChatRequest, Common, CompletionRequest, Meta};
use crate::embeddings::{self, Embeddings};
use crate::engine::{Completion, Engine, Prompt, Request, RequestError};
use crate::http::{self, Head, ReadError, Status};
use crate::text::Split;
use crate::Logprobs;
use crate::{llama, logprobs, ollama, receipt};

/// Time a client has to send its whole request.
const READ_TIMEOUT: Duration = Duration::from_secs(30);
/// Time one write may block on a client that stopped reading.
const WRITE_TIMEOUT: Duration = Duration::from_secs(60);
/// Connections served at once, including those waiting for the model.
const MAX_CONNECTIONS: usize = 64;

/// How the server answers, beyond the model it serves.
#[derive(Clone, Debug, Default)]
pub struct Options {
    /// Every route but `/health` needs `Authorization: Bearer <key>`.
    pub api_key: Option<String>,
}

/// Serves the OpenAI-compatible API, llama-server's and Ollama's on
/// `listener` until the process ends. Requests are handled concurrently; as
/// many as the engine has backends run at once and the rest wait their turn.
pub fn serve(engine: &Engine, listener: TcpListener) {
    serve_with(engine, listener, &Options::default());
}

/// [`serve`] with `options`.
pub fn serve_with(engine: &Engine, listener: TcpListener, options: &Options) {
    serve_routes(listener, options, &|head, body, out| {
        route(engine, head, body, out)
    });
}

/// Serves `/v1/embeddings` for an embedding model, or `/v1/rerank` for a
/// ranking one, as [`serve`] does.
pub fn serve_embeddings(model: &Embeddings, listener: TcpListener) {
    serve_embeddings_with(model, listener, &Options::default());
}

/// [`serve_embeddings`] with `options`.
pub fn serve_embeddings_with(model: &Embeddings, listener: TcpListener, options: &Options) {
    serve_routes(listener, options, &|head, body, out| {
        embeddings::route(model, head, body, out)
    });
}

type Routes<'r> = dyn Fn(&Head, &[u8], &mut &TcpStream) -> Result<(), ApiError> + Sync + 'r;

fn serve_routes(listener: TcpListener, options: &Options, routes: &Routes) {
    let active = AtomicUsize::new(0);
    std::thread::scope(|scope| {
        for stream in listener.incoming() {
            let Ok(stream) = stream else { continue };
            if stream.set_write_timeout(Some(WRITE_TIMEOUT)).is_err() {
                continue;
            }
            if active.fetch_add(1, Ordering::AcqRel) >= MAX_CONNECTIONS {
                active.fetch_sub(1, Ordering::AcqRel);
                let busy = ApiError {
                    status: 503,
                    message: "the server is busy".into(),
                };
                let _ = send_error(&mut &stream, &busy);
                continue;
            }
            let active = &active;
            scope.spawn(move || {
                let _ = catch_unwind(AssertUnwindSafe(|| handle(options, routes, &stream)));
                active.fetch_sub(1, Ordering::AcqRel);
            });
        }
    });
}

/// Reads from a stream with one deadline for the whole request.
struct Deadline<'s> {
    stream: &'s TcpStream,
    until: Instant,
}

impl Read for Deadline<'_> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let left = self.until.saturating_duration_since(Instant::now());
        if left.is_zero() {
            return Err(io::ErrorKind::TimedOut.into());
        }
        self.stream.set_read_timeout(Some(left))?;
        (&mut &*self.stream).read(buf)
    }
}

fn handle(options: &Options, routes: &Routes, stream: &TcpStream) {
    let mut out = stream;
    let mut reader = BufReader::new(Deadline {
        stream,
        until: Instant::now() + READ_TIMEOUT,
    });
    let head = match http::read_head(&mut reader) {
        Ok(head) => head,
        Err(ReadError::Bad(status)) => return refuse(&mut out, status),
        Err(ReadError::Io) => return,
    };
    let len = match head.content_length() {
        Ok(len) => len,
        Err(status) => return refuse(&mut out, status),
    };
    if len > 0 && head.expects_continue() && http::write_continue(&mut out).is_err() {
        return;
    }
    let Ok(body) = http::read_body(&mut reader, len) else {
        return;
    };
    if let Some(key) = &options.api_key {
        if let Err(e) = authorize(&head, key) {
            let _ = send_error(&mut out, &e);
            return;
        }
    }
    if let Err(e) = routes(&head, &body, &mut out) {
        let _ = send_error(&mut out, &e);
    }
}

/// Checks the request's key, as llama-server reads it: a bearer token or
/// an `X-Api-Key` header. Health checks need none.
fn authorize(head: &Head, key: &str) -> Result<(), ApiError> {
    if matches!(head.path.as_str(), "/health" | "/v1/health") {
        return Ok(());
    }
    let given = head
        .header("authorization")
        .and_then(|v| v.trim().strip_prefix("Bearer "))
        .or_else(|| head.header("x-api-key"))
        .map(str::trim);
    match given {
        Some(given) if same_key(given.as_bytes(), key.as_bytes()) => Ok(()),
        _ => Err(ApiError {
            status: 401,
            message: "invalid API key".into(),
        }),
    }
}

/// Compares in time independent of where the keys differ.
fn same_key(a: &[u8], b: &[u8]) -> bool {
    a.len() == b.len() && a.iter().zip(b).fold(0, |d, (x, y)| d | (x ^ y)) == 0
}

fn refuse(out: &mut impl Write, Status(status, message): Status) {
    let _ = send_error(
        out,
        &ApiError {
            status,
            message: message.into(),
        },
    );
}

fn route(engine: &Engine, head: &Head, body: &[u8], out: &mut impl Write) -> Result<(), ApiError> {
    if ollama::handles(&head.path) {
        ollama::route(engine, head, body, out);
        return Ok(());
    }
    if let Some(answer) = llama::route(engine, head, body, out) {
        return answer;
    }
    match head.path.strip_prefix("/v1").unwrap_or(&head.path) {
        "/health" => {
            expect(head, "GET")?;
            let (slots, busy) = engine.slots();
            send_json(
                out,
                &json!({"status": "ok", "slots_idle": slots - busy, "slots_processing": busy}),
            )
        }
        "/metrics" => {
            expect(head, "GET")?;
            let text = engine.metrics();
            let _ = http::write_response(
                out,
                200,
                "text/plain; version=0.0.4; charset=utf-8",
                text.as_bytes(),
            );
            Ok(())
        }
        "/models" => {
            expect(head, "GET")?;
            send_json(out, &models(engine.name(), engine.context_length()))
        }
        "/chat/completions" => {
            expect(head, "POST")?;
            chat(engine, parse(head, body)?, out)
        }
        "/completions" => {
            expect(head, "POST")?;
            completion(engine, parse(head, body)?, out)
        }
        "/prefill" => {
            expect(head, "POST")?;
            prefill(engine, parse(head, body)?, out)
        }
        "/embeddings" | "/rerank" | "/reranking" => Err(ApiError::invalid(format!(
            "{} generates text; serve an embedding or ranking model for {}",
            engine.name(),
            head.path
        ))),
        _ => Err(not_found(head)),
    }
}

pub(crate) fn expect(head: &Head, method: &str) -> Result<(), ApiError> {
    if head.method == method {
        Ok(())
    } else {
        Err(ApiError {
            status: 405,
            message: format!("use {method} for {}", head.path),
        })
    }
}

pub(crate) fn not_found(head: &Head) -> ApiError {
    ApiError {
        status: 404,
        message: format!("no endpoint {} {}", head.method, head.path),
    }
}

/// The `/v1/models` listing of the one model served.
pub(crate) fn models(name: &str, context_length: usize) -> Value {
    json!({"object": "list", "data": [{
        "id": name,
        "object": "model",
        "created": now(),
        "owned_by": "kinetic",
        "context_length": context_length,
    }]})
}

pub(crate) fn parse<T: DeserializeOwned>(head: &Head, body: &[u8]) -> Result<T, ApiError> {
    // Browsers only send JSON cross-origin after a preflight this server
    // never approves, so web pages cannot drive it.
    if let Some(ct) = head.header("content-type") {
        if !ct
            .trim_start()
            .to_ascii_lowercase()
            .starts_with("application/json")
        {
            return Err(ApiError {
                status: 415,
                message: "send the body as application/json".into(),
            });
        }
    }
    serde_json::from_slice(body).map_err(|e| ApiError::invalid(format!("invalid JSON: {e}")))
}

fn chat(engine: &Engine, req: ChatRequest, out: &mut impl Write) -> Result<(), ApiError> {
    api::validate_messages(&req.messages)?;
    let mut request = req.common.request(engine.default_sampling())?;
    let log = req.common.logprobs()?.map(Logprobs::new);
    let piece = |id| engine.tokenizer().piece(id);
    let mut options = req.chat_template_kwargs.clone().unwrap_or_default();
    if let Some(tools) = req.tools()? {
        options.insert("tools".into(), tools.into());
    }
    let mut prompt = engine
        .chat_prompt(&req.messages, &options)
        .map_err(invalid)?;
    prompt.images = api::images(&req.messages)?;
    if req.forces_call() && !prompt.tools.is_empty() {
        if request.grammar.is_some() {
            return Err(ApiError::invalid(
                "tool_choice required or a function cannot be combined with grammar or response_format",
            ));
        }
        let grammar = engine
            .tool_grammar(&prompt, req.parallel_calls())
            .map_err(invalid)?;
        request.grammar = Some(std::sync::Arc::new(grammar));
    }
    prepare_receipt(engine, &req.common, &mut request, &prompt)?;
    let input = || Value::from(req.messages.clone());
    let id = new_id("chatcmpl");
    let meta = Meta {
        id: &id,
        created: now(),
        model: engine.name(),
    };
    if !req.common.stream() {
        let c = engine
            .complete_with_logprobs(&prompt, &request, log.as_ref(), &mut |_, _| true)
            .map_err(invalid)?;
        let ids = call_ids(&c);
        let mut body = api::chat_response(&meta, &c, &ids);
        if let Some(log) = &log {
            body["choices"][0]["logprobs"] = logprobs::chat(&log.range(0, usize::MAX), piece);
        }
        add_receipt(&mut body, engine, &req.common, input(), &request, &c)?;
        return send_json(out, &body);
    }

    let first = api::chat_chunk(
        &meta,
        Some(json!({"role": "assistant", "content": ""})),
        None,
    );
    let mut events = Events::new(out, Some(first));
    let mut sent = 0;
    let c = engine
        .complete_with_logprobs(&prompt, &request, log.as_ref(), &mut |part, generated| {
            let mut lp = log.as_ref().map(|log| {
                let tokens = log.range(sent, generated);
                sent += tokens.len();
                logprobs::chat(&tokens, piece)
            });
            let mut ok = true;
            for (key, text) in [
                ("reasoning_content", &part.reasoning),
                ("content", &part.content),
            ] {
                if !text.is_empty() {
                    let delta = Map::from_iter([(key.to_owned(), Value::from(text.as_str()))]);
                    let mut chunk = api::chat_chunk(&meta, Some(delta.into()), None);
                    if let Some(lp) = lp.take() {
                        chunk["choices"][0]["logprobs"] = lp;
                    }
                    ok &= events.send(&chunk);
                }
            }
            ok
        })
        .map_err(invalid)?;
    if !c.tool_calls.is_empty() {
        let calls = api::tool_calls(&c.tool_calls, &call_ids(&c), true);
        events.send(&api::chat_chunk(
            &meta,
            Some(json!({"tool_calls": calls})),
            None,
        ));
    }
    let mut last = api::chat_chunk(&meta, Some(json!({})), Some(c.finish.as_str()));
    add_receipt(&mut last, engine, &req.common, input(), &request, &c)?;
    events.send(&last);
    let usage = req.common.include_usage().then(|| {
        let mut chunk = api::chat_chunk(&meta, None, None);
        chunk["usage"] = api::usage(&c);
        chunk
    });
    finish_stream(events, usage);
    Ok(())
}

/// Zero Wait: runs a chat request still being written ahead, so the real
/// one answers sooner; it waits until that is done or a newer draft or a
/// request comes in.
fn prefill(engine: &Engine, req: ChatRequest, out: &mut impl Write) -> Result<(), ApiError> {
    api::validate_messages(&req.messages)?;
    let mut options = req.chat_template_kwargs.clone().unwrap_or_default();
    if let Some(tools) = req.tools()? {
        options.insert("tools".into(), tools.into());
    }
    let prompt = engine
        .draft_prompt(&req.messages, &options)
        .map_err(invalid)?;
    let cached = engine.prefill(&prompt);
    send_json(out, &json!({"object": "prefill", "cached_tokens": cached}))
}

fn completion(
    engine: &Engine,
    req: CompletionRequest,
    out: &mut impl Write,
) -> Result<(), ApiError> {
    let mut request = req.common.request(engine.default_sampling())?;
    let log = req.common.logprobs()?.map(Logprobs::new);
    let piece = |id| engine.tokenizer().piece(id);
    let mut offset = 0;
    let prompt = Prompt::raw(api::completion_prompt(&req.prompt)?);
    prepare_receipt(engine, &req.common, &mut request, &prompt)?;
    let input = || Value::from(prompt.text.as_str());
    let id = new_id("cmpl");
    let meta = Meta {
        id: &id,
        created: now(),
        model: engine.name(),
    };
    if !req.common.stream() {
        let c = engine
            .complete_with_logprobs(&prompt, &request, log.as_ref(), &mut |_, _| true)
            .map_err(invalid)?;
        let mut body = api::completion_response(&meta, &c);
        if let Some(log) = &log {
            let tokens = log.range(0, usize::MAX);
            body["choices"][0]["logprobs"] = logprobs::completion(&tokens, piece, &mut offset);
        }
        add_receipt(&mut body, engine, &req.common, input(), &request, &c)?;
        return send_json(out, &body);
    }

    let mut events = Events::new(out, None);
    let mut sent = 0;
    let c = engine
        .complete_with_logprobs(
            &prompt,
            &request,
            log.as_ref(),
            &mut |part: &Split, generated| {
                let mut chunk = api::completion_chunk(&meta, Some(&part.content), None);
                if let Some(log) = &log {
                    let tokens = log.range(sent, generated);
                    sent += tokens.len();
                    chunk["choices"][0]["logprobs"] =
                        logprobs::completion(&tokens, piece, &mut offset);
                }
                events.send(&chunk)
            },
        )
        .map_err(invalid)?;
    let mut last = api::completion_chunk(&meta, Some(""), Some(c.finish.as_str()));
    add_receipt(&mut last, engine, &req.common, input(), &request, &c)?;
    events.send(&last);
    let usage = req.common.include_usage().then(|| {
        let mut chunk = api::completion_chunk(&meta, None, None);
        chunk["usage"] = api::usage(&c);
        chunk
    });
    finish_stream(events, usage);
    Ok(())
}

/// Checks that a receipt the request asks for can be made, and fixes its
/// seed so the answer can be reproduced.
fn prepare_receipt(
    engine: &Engine,
    common: &Common,
    request: &mut Request,
    prompt: &Prompt,
) -> Result<(), ApiError> {
    if !common.receipt() {
        return Ok(());
    }
    if engine.receipts().is_none() {
        return Err(ApiError::invalid("this server does not make receipts"));
    }
    if !prompt.images.is_empty() {
        return Err(ApiError::invalid("receipts do not cover images yet"));
    }
    receipt::seed(&mut request.sampling);
    Ok(())
}

/// Adds the receipt for `c` to `body` if the request asked for one.
fn add_receipt(
    body: &mut Value,
    engine: &Engine,
    common: &Common,
    input: Value,
    request: &Request,
    c: &Completion,
) -> Result<(), ApiError> {
    let Some(receipts) = engine.receipts().filter(|_| common.receipt()) else {
        return Ok(());
    };
    let r = receipts
        .make(input, common.constraint(), request, c)
        .map_err(|message| ApiError {
            status: 500,
            message,
        })?;
    // through text, so f32 settings read 0.8 rather than 0.800000011920929
    let text = serde_json::to_string(&r).expect("a receipt serializes");
    body["receipt"] = serde_json::from_str(&text).expect("a receipt parses");
    Ok(())
}

/// A server-sent event stream that starts with its first event, so errors
/// found before any output still get a plain error response.
pub(crate) struct Events<'w, W: Write> {
    out: &'w mut W,
    /// Sent right after the headers.
    opening: Option<Value>,
    started: bool,
    open: bool,
}

impl<'w, W: Write> Events<'w, W> {
    pub(crate) fn new(out: &'w mut W, opening: Option<Value>) -> Self {
        Events {
            out,
            opening,
            started: false,
            open: true,
        }
    }

    /// Sends one event; false once the client is gone.
    pub(crate) fn send(&mut self, data: &Value) -> bool {
        if self.open {
            self.open = self.try_send(data).is_ok();
        }
        self.open
    }

    fn try_send(&mut self, data: &Value) -> io::Result<()> {
        if !self.started {
            self.started = true;
            http::write_event_stream_head(self.out)?;
            if let Some(opening) = self.opening.take() {
                http::write_event(self.out, &opening.to_string())?;
            }
        }
        http::write_event(self.out, &data.to_string())
    }
}

/// Sends the usage chunk, if any, and the end marker.
fn finish_stream<W: Write>(mut events: Events<W>, usage: Option<Value>) {
    if let Some(usage) = usage {
        events.send(&usage);
    }
    if events.open {
        let _ = http::write_event(events.out, "[DONE]");
    }
}

fn invalid(e: RequestError) -> ApiError {
    ApiError::invalid(e.0)
}

pub(crate) fn send_json(out: &mut impl Write, body: &Value) -> Result<(), ApiError> {
    // A client that left cannot be told anything more.
    let _ = http::write_response(out, 200, "application/json", body.to_string().as_bytes());
    Ok(())
}

fn send_error(out: &mut impl Write, e: &ApiError) -> io::Result<()> {
    http::write_response(
        out,
        e.status,
        "application/json",
        e.body().to_string().as_bytes(),
    )
}

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

fn call_ids(c: &Completion) -> Vec<String> {
    c.tool_calls.iter().map(|_| new_id("call")).collect()
}

fn new_id(prefix: &str) -> String {
    let n = RandomState::new().hash_one(Instant::now());
    format!("{prefix}-{n:016x}")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn head(lines: &str) -> Head {
        let raw = format!("{lines}\r\n\r\n");
        let Ok(head) = http::read_head(&mut raw.as_bytes()) else {
            panic!("bad head {lines:?}");
        };
        head
    }

    #[test]
    fn api_key_guards_all_but_health() {
        let ok = |lines| authorize(&head(lines), "s3cret").is_ok();
        assert!(ok("GET /health HTTP/1.1"));
        assert!(ok(
            "GET /v1/models HTTP/1.1\r\nAuthorization: Bearer s3cret"
        ));
        assert!(ok("GET /metrics HTTP/1.1\r\nx-api-key: s3cret"));
        assert!(!ok("GET /v1/models HTTP/1.1"));
        assert!(!ok(
            "POST /v1/chat/completions HTTP/1.1\r\nAuthorization: Bearer s3cre"
        ));
        assert!(!ok("GET /slots HTTP/1.1\r\nAuthorization: s3cret"));
        let e = authorize(&head("GET /props HTTP/1.1"), "k").unwrap_err();
        assert_eq!(e.status, 401);
        assert_eq!(e.body()["error"]["type"], "authentication_error");
    }

    #[test]
    fn a_trickling_client_is_dropped_at_the_deadline() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        std::thread::spawn(move || {
            let mut client = TcpStream::connect(addr).unwrap();
            while client.write_all(b"G").is_ok() {
                std::thread::sleep(Duration::from_millis(20));
            }
        });
        let (stream, _) = listener.accept().unwrap();
        let start = Instant::now();
        let mut reader = BufReader::new(Deadline {
            stream: &stream,
            until: start + Duration::from_millis(300),
        });
        assert!(matches!(http::read_head(&mut reader), Err(ReadError::Io)));
        assert!(start.elapsed() < Duration::from_secs(2));
    }
}
