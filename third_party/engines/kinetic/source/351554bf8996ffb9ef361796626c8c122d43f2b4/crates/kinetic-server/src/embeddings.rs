//! `/v1/embeddings` for embedding models and `/v1/rerank` for ranking
//! models.

use std::io::Write;
use std::sync::{Mutex, PoisonError};

use kinetic_gguf::Gguf;
use kinetic_models::{Embedder, Pooling};
use kinetic_tokenizer::Tokenizer;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::api::ApiError;
use crate::base64;
use crate::http::Head;
use crate::model_info::ModelInfo;
use crate::rerank::{self, RerankTemplate};
use crate::server::{expect, models, not_found, parse, send_json};

/// Inputs one request may embed at once.
const MAX_INPUTS: usize = 256;

/// An embedding or ranking model with its tokenizer. Requests take turns
/// on it.
pub struct Embeddings<'a> {
    name: String,
    tokenizer: Tokenizer,
    pub(crate) context_length: usize,
    /// Set for ranking models, which score documents instead of embedding.
    rerank: Option<RerankTemplate>,
    info: ModelInfo,
    embedder: Mutex<Embedder<'a>>,
}

impl<'a> Embeddings<'a> {
    pub fn new(
        name: impl Into<String>,
        gguf: &Gguf,
        embedder: Embedder<'a>,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let rerank = match embedder.pooling() {
            Pooling::Rank => {
                let template = gguf
                    .get("tokenizer.chat_template.rerank")
                    .and_then(|v| v.as_str())
                    .ok_or("the ranking model has no rerank template")?;
                Some(RerankTemplate(template.to_owned()))
            }
            _ => None,
        };
        Ok(Embeddings {
            name: name.into(),
            tokenizer: Tokenizer::from_gguf(gguf)?,
            context_length: embedder.n_ctx_train(),
            rerank,
            info: ModelInfo::new(gguf),
            embedder: Mutex::new(embedder),
        })
    }

    /// The model's name as clients see it.
    pub fn name(&self) -> &str {
        &self.name
    }

    /// What the model's header says about it.
    pub fn info(&self) -> &ModelInfo {
        &self.info
    }

    /// One vector per text, and the tokens read; with `truncate` a text
    /// longer than the context is cut to it instead of refused.
    pub(crate) fn embed_texts(
        &self,
        texts: &[String],
        truncate: bool,
    ) -> Result<(Vec<Vec<f32>>, usize), ApiError> {
        if self.rerank.is_some() {
            return Err(ApiError::invalid(format!(
                "{} ranks documents; use /v1/rerank",
                self.name
            )));
        }
        let mut inputs = Vec::with_capacity(texts.len());
        for text in texts {
            let mut ids = self.tokenizer.encode(text, true);
            if truncate {
                ids.truncate(self.context_length);
            }
            inputs.push(ids);
        }
        let inputs = tokenize(&self.tokenizer, &json!(inputs), self.context_length)?;
        let refs: Vec<&[u32]> = inputs.iter().map(Vec::as_slice).collect();
        let vectors = self
            .embedder
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .embed(&refs);
        Ok((vectors, inputs.iter().map(Vec::len).sum()))
    }
}

#[derive(Deserialize)]
struct EmbeddingRequest {
    input: Value,
    #[serde(default)]
    encoding_format: Option<String>,
}

pub(crate) fn route(
    e: &Embeddings,
    head: &Head,
    body: &[u8],
    out: &mut impl Write,
) -> Result<(), ApiError> {
    if crate::ollama::handles(&head.path) {
        crate::ollama::route_embeddings(e, head, body, out);
        return Ok(());
    }
    if let Some(answer) = crate::llama::route_embeddings(e, head, body, out) {
        return answer;
    }
    let context = e.context_length;
    match head.path.strip_prefix("/v1").unwrap_or(&head.path) {
        "/health" => {
            expect(head, "GET")?;
            send_json(out, &json!({"status": "ok"}))
        }
        "/models" => {
            expect(head, "GET")?;
            send_json(out, &models(&e.name, context))
        }
        "/rerank" | "/reranking" => {
            expect(head, "POST")?;
            let template = e.rerank.as_ref().ok_or_else(|| {
                ApiError::invalid(format!("{} embeds; use /v1/embeddings", e.name))
            })?;
            let req = parse(head, body)?;
            let embedder = e.embedder.lock().unwrap_or_else(PoisonError::into_inner);
            let answer = rerank::rerank(&req, &e.name, &e.tokenizer, template, &embedder, context)?;
            send_json(out, &answer)
        }
        "/embeddings" => {
            expect(head, "POST")?;
            if e.rerank.is_some() {
                return Err(ApiError::invalid(format!(
                    "{} ranks documents; use /v1/rerank",
                    e.name
                )));
            }
            let req: EmbeddingRequest = parse(head, body)?;
            let base64 = match req.encoding_format.as_deref() {
                None | Some("float") => false,
                Some("base64") => true,
                Some(_) => {
                    return Err(ApiError::invalid("encoding_format must be float or base64"))
                }
            };
            let inputs = tokenize(&e.tokenizer, &req.input, context)?;
            let refs: Vec<&[u32]> = inputs.iter().map(Vec::as_slice).collect();
            let vectors = e
                .embedder
                .lock()
                .unwrap_or_else(PoisonError::into_inner)
                .embed(&refs);
            let data: Vec<Value> = vectors
                .iter()
                .enumerate()
                .map(|(i, v)| {
                    let embedding = if base64 {
                        let bytes: Vec<u8> = v.iter().flat_map(|x| x.to_le_bytes()).collect();
                        Value::from(base64::encode(&bytes))
                    } else {
                        json!(v)
                    };
                    json!({"object": "embedding", "index": i, "embedding": embedding})
                })
                .collect();
            let tokens: usize = inputs.iter().map(Vec::len).sum();
            send_json(
                out,
                &json!({
                    "object": "list",
                    "data": data,
                    "model": e.name,
                    "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
                }),
            )
        }
        "/chat/completions" | "/completions" => Err(ApiError::invalid(format!(
            "{} is an embedding model; use /v1/embeddings",
            e.name
        ))),
        _ => Err(not_found(head)),
    }
}

/// The inputs as token ids: a string, a list of strings, a list of token
/// ids, or a list of such lists.
fn tokenize(
    tokenizer: &Tokenizer,
    input: &Value,
    context: usize,
) -> Result<Vec<Vec<u32>>, ApiError> {
    let ids = |v: &[Value]| {
        v.iter()
            .map(|t| t.as_u64().and_then(|t| u32::try_from(t).ok()))
            .map(|t| t.filter(|&t| (t as usize) < tokenizer.vocab_size()))
            .collect::<Option<Vec<u32>>>()
    };
    // An empty string still encodes to the model's wrapping tokens.
    let encode = |s: &str| match s {
        "" => Vec::new(),
        s => tokenizer.encode(s, true),
    };
    let inputs: Vec<Vec<u32>> = match input {
        Value::String(s) => vec![encode(s)],
        Value::Array(items) if items.iter().all(Value::is_string) => items
            .iter()
            .map(|s| encode(s.as_str().unwrap_or_default()))
            .collect(),
        Value::Array(items) if items.iter().all(Value::is_number) => {
            vec![ids(items).ok_or_else(bad_input)?]
        }
        Value::Array(items) => items
            .iter()
            .map(|i| i.as_array().and_then(|a| ids(a)).ok_or_else(bad_input))
            .collect::<Result<_, _>>()?,
        _ => return Err(bad_input()),
    };
    if inputs.is_empty() || inputs.len() > MAX_INPUTS {
        return Err(ApiError::invalid(format!("send 1 to {MAX_INPUTS} inputs")));
    }
    if inputs.iter().any(Vec::is_empty) {
        return Err(ApiError::invalid("inputs must not be empty"));
    }
    if let Some(long) = inputs.iter().find(|i| i.len() > context) {
        return Err(ApiError::invalid(format!(
            "an input is {} tokens; this model takes at most {context}",
            long.len()
        )));
    }
    Ok(inputs)
}

fn bad_input() -> ApiError {
    ApiError::invalid("input must be a string, a list of strings, or token ids in the vocabulary")
}
