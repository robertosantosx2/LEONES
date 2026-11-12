//! `/v1/rerank` for ranking models: a query and documents in, the
//! documents' relevance out, most relevant first, as Jina and Cohere
//! answer it.

use kinetic_models::Embedder;
use kinetic_tokenizer::Tokenizer;
use serde::Deserialize;
use serde_json::{json, Value};

use crate::api::ApiError;

/// Documents one request may rank at once.
const MAX_DOCUMENTS: usize = 256;

#[derive(Deserialize)]
pub struct RerankRequest {
    query: String,
    documents: Vec<Value>,
    #[serde(default)]
    top_n: Option<usize>,
    #[serde(default)]
    return_documents: bool,
}

/// How a ranking model reads a query and a document: the model's
/// `tokenizer.chat_template.rerank`, with `{query}` and `{document}` where
/// they go.
pub struct RerankTemplate(pub String);

impl RerankTemplate {
    /// The prompt for `query` and `document`. Placeholders are filled in one
    /// pass, so text that contains one is never filled in itself.
    fn fill(&self, query: &str, document: &str) -> String {
        let mut out = String::with_capacity(self.0.len() + query.len() + document.len());
        let mut rest = self.0.as_str();
        while let Some(at) = rest.find('{') {
            out.push_str(&rest[..at]);
            rest = &rest[at..];
            for (placeholder, value) in [("{query}", query), ("{document}", document)] {
                if let Some(after) = rest.strip_prefix(placeholder) {
                    out.push_str(value);
                    rest = after;
                }
            }
            if let Some(brace) = rest.strip_prefix('{') {
                out.push('{');
                rest = brace;
            }
        }
        out.push_str(rest);
        out
    }

    /// The prompt's tokens, special tokens parsed and none added around it.
    fn encode(&self, tokenizer: &Tokenizer, query: &str, document: &str) -> Vec<u32> {
        let mut ids = tokenizer.encode(&self.fill(query, document), true);
        // What encoding adds around any text: BOS first, then the rest last.
        let mut added = tokenizer.encode("", true);
        if !added.is_empty() && added.first().copied() == tokenizer.bos() {
            added.remove(0);
            ids.remove(0);
        }
        ids.truncate(ids.len() - added.len());
        ids
    }
}

/// Scores every document of `req` against its query with `ranker` and
/// answers with the most relevant first.
pub fn rerank(
    req: &RerankRequest,
    name: &str,
    tokenizer: &Tokenizer,
    template: &RerankTemplate,
    ranker: &Embedder,
    context: usize,
) -> Result<Value, ApiError> {
    if req.documents.is_empty() || req.documents.len() > MAX_DOCUMENTS {
        return Err(ApiError::invalid(format!(
            "send 1 to {MAX_DOCUMENTS} documents"
        )));
    }
    let texts = req
        .documents
        .iter()
        .map(|d| match d {
            Value::String(s) => Some(s.as_str()),
            d => d.get("text").and_then(Value::as_str),
        })
        .collect::<Option<Vec<&str>>>()
        .ok_or_else(|| ApiError::invalid("documents must be strings or objects with text"))?;
    let inputs: Vec<Vec<u32>> = texts
        .iter()
        .map(|d| template.encode(tokenizer, &req.query, d))
        .collect();
    if let Some(long) = inputs.iter().find(|i| i.len() > context) {
        return Err(ApiError::invalid(format!(
            "a document with its query is {} tokens; this model takes at most {context}",
            long.len()
        )));
    }
    let refs: Vec<&[u32]> = inputs.iter().map(Vec::as_slice).collect();
    let scores = ranker.rank(&refs);

    let mut order: Vec<usize> = (0..scores.len()).collect();
    order.sort_by(|&a, &b| scores[b].total_cmp(&scores[a]));
    order.truncate(req.top_n.unwrap_or(order.len()));
    let results: Vec<Value> = order
        .into_iter()
        .map(|i| {
            let mut r = json!({"index": i, "relevance_score": scores[i]});
            if req.return_documents {
                r["document"] = json!({"text": texts[i]});
            }
            r
        })
        .collect();
    let tokens: usize = inputs.iter().map(Vec::len).sum();
    Ok(json!({
        "object": "list",
        "model": name,
        "results": results,
        "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn placeholders_are_filled_once() {
        let t = RerankTemplate("<Query>: {query}\n<Document>: {document} {x}".into());
        assert_eq!(
            t.fill("a {document}", "b"),
            "<Query>: a {document}\n<Document>: b {x}"
        );
    }
}
