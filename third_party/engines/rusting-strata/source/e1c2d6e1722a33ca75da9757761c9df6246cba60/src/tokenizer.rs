//! GPT-2 style byte-level BPE built from GGUF tokenizer metadata.

use crate::gguf::Gguf;
use anyhow::{Context, anyhow, bail};
use std::collections::HashMap;
use tokenizers::decoders::byte_level::ByteLevel as ByteLevelDecoder;
use tokenizers::models::bpe::BPE;
use tokenizers::pre_tokenizers::byte_level::ByteLevel;
use tokenizers::pre_tokenizers::sequence::Sequence;
use tokenizers::pre_tokenizers::split::{Split, SplitPattern};
use tokenizers::{AddedToken, PreTokenizerWrapper, SplitDelimiterBehavior};

/// llama.cpp `LLAMA_VOCAB_PRE_TYPE_QWEN35` pre-tokenizer regex.
const QWEN35_RE: &str = r"(?:'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD])|[^\r\n\p{L}\p{N}]?[\p{L}\p{M}]+|\p{N}| ?[^\s\p{L}\p{M}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+";

/// llama.cpp `LLAMA_VOCAB_PRE_TYPE_QWEN2` pre-tokenizer regex (qwen3, qwen3moe, qwen3next).
const QWEN2_RE: &str = r"(?:'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD])|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+";

/// llama.cpp `LLAMA_VOCAB_PRE_TYPE_CHATGLM4` (GLM-4/5): digits in groups of up to 3.
const GLM4_RE: &str = r"(?:'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD])|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+";

/// llama.cpp `LLAMA_VOCAB_PRE_TYPE_JOYAI_LLM` (DeepSeek-V4): three splits applied one after another.
const JOYAI_RE: [&str; 3] = [
    r"\p{N}{1,3}",
    "[一-龥\u{3040}-\u{309f}\u{30a0}-\u{30ff}]+",
    "[!\"#$%&'()*+,\\-./:;<=>?@\\[\\\\\\]^_`{|}~][A-Za-z]+|[^\r\n\\p{L}\\p{P}\\p{S}]?[\\p{L}\\p{M}]+| ?[\\p{P}\\p{S}]+[\r\n]*|\\s*[\r\n]+|\\s+(?!\\S)|\\s+",
];

pub struct Tokenizer {
    inner: tokenizers::Tokenizer,
    eos: Vec<u32>,
}

impl Tokenizer {
    pub fn from_gguf(g: &Gguf) -> anyhow::Result<Tokenizer> {
        let model = g.get("tokenizer.ggml.model")?.as_str().unwrap_or("");
        if model == "gemma4" { return Self::gemma4(g); }
        if model != "gpt2" { bail!("unsupported tokenizer model '{model}'"); }
        let pre = g.get("tokenizer.ggml.pre")?.as_str().unwrap_or("");
        let res: &[&str] = match pre {
            "qwen35" => &[QWEN35_RE], "qwen2" => &[QWEN2_RE], "joyai-llm" => &JOYAI_RE,
            "glm4" | "glm5" | "chatglm-bpe" => &[GLM4_RE],
            _ => bail!("unsupported pre-tokenizer '{pre}'"),
        };
        let strs = |k: &str| -> anyhow::Result<Vec<String>> {
            g.get(k)?.as_arr().with_context(|| format!("{k}: not an array"))?
                .iter().map(|v| v.as_str().map(str::to_string).with_context(|| format!("{k}: not a string"))).collect()
        };
        let tokens = strs("tokenizer.ggml.tokens")?;
        let merges = strs("tokenizer.ggml.merges")?
            .into_iter()
            .map(|m| m.split_once(' ').map(|(a, b)| (a.to_string(), b.to_string())).context("bad merge"))
            .collect::<anyhow::Result<Vec<_>>>()?;
        let vocab: HashMap<String, u32> = tokens.iter().enumerate().map(|(i, t)| (t.clone(), i as u32)).collect();
        let bpe = BPE::builder().vocab_and_merges(vocab, merges).build().map_err(|e| anyhow!("{e}"))?;

        let mut inner = tokenizers::Tokenizer::new(bpe);
        let mut pre_tok = Vec::new();
        for re in res {
            let split = Split::new(SplitPattern::Regex((*re).into()), SplitDelimiterBehavior::Isolated, false)
                .map_err(|e| anyhow!("{e}"))?;
            pre_tok.push(PreTokenizerWrapper::Split(split));
        }
        pre_tok.push(PreTokenizerWrapper::ByteLevel(ByteLevel::new(false, false, false)));
        inner.with_pre_tokenizer(Some(Sequence::new(pre_tok)));
        inner.with_decoder(Some(ByteLevelDecoder::default()));

        let types = g.get("tokenizer.ggml.token_type")?.as_arr().context("token_type")?;
        let special: Vec<AddedToken> = types.iter().enumerate()
            .filter(|(_, t)| matches!(t.as_u64(), Some(3 | 4)))
            .map(|(i, _)| AddedToken::from(tokens[i].clone(), true))
            .collect();
        inner.add_special_tokens(&special);

        let mut eos: Vec<u32> = g.meta.get("tokenizer.ggml.eos_token_id").and_then(|v| v.as_u64()).map(|v| v as u32).into_iter().collect();
        for t in ["<|im_end|>", "<|endoftext|>"] {
            if let Some(id) = inner.token_to_id(t) && !eos.contains(&id) { eos.push(id); }
        }
        Ok(Tokenizer { inner, eos })
    }

    /// Gemma 4: SPM-style BPE. Spaces become U+2581, merges run over each newline-free run of raw UTF-8, unknown bytes fall back to <0xXX>.
    fn gemma4(g: &Gguf) -> anyhow::Result<Tokenizer> {
        use tokenizers::decoders::{byte_fallback::ByteFallback, fuse::Fuse, sequence::Sequence as DSeq, DecoderWrapper};
        use tokenizers::normalizers::Replace;
        let tokens: Vec<String> = g.get("tokenizer.ggml.tokens")?.as_arr().context("tokens")?
            .iter().map(|v| v.as_str().map(str::to_string).context("token")).collect::<anyhow::Result<_>>()?;
        let merges = g.get("tokenizer.ggml.merges")?.as_arr().context("merges")?.iter()
            .map(|v| v.as_str().and_then(|m| m.split_once(' ')).map(|(a, b)| (a.to_string(), b.to_string())).context("bad merge"))
            .collect::<anyhow::Result<Vec<_>>>()?;
        let vocab: HashMap<String, u32> = tokens.iter().enumerate().map(|(i, t)| (t.clone(), i as u32)).collect();
        let bpe = BPE::builder().vocab_and_merges(vocab, merges).byte_fallback(true).unk_token("<unk>".into()).build().map_err(|e| anyhow!("{e}"))?;
        let mut inner = tokenizers::Tokenizer::new(bpe);
        inner.with_normalizer(Some(Replace::new(" ", "\u{2581}").map_err(|e| anyhow!("{e}"))?));
        let split = Split::new(SplitPattern::Regex("[^\\n]+|[\\n]+".into()), SplitDelimiterBehavior::Isolated, false).map_err(|e| anyhow!("{e}"))?;
        inner.with_pre_tokenizer(Some(split));
        inner.with_decoder(Some(DSeq::new(vec![
            DecoderWrapper::Replace(tokenizers::normalizers::replace::Replace::new("\u{2581}", " ").map_err(|e| anyhow!("{e}"))?),
            DecoderWrapper::ByteFallback(ByteFallback::new()),
            DecoderWrapper::Fuse(Fuse::new()),
        ])));
        let types = g.get("tokenizer.ggml.token_type")?.as_arr().context("token_type")?;
        let special: Vec<AddedToken> = types.iter().enumerate()
            .filter(|(_, t)| matches!(t.as_u64(), Some(3 | 4)))
            .map(|(i, _)| AddedToken::from(tokens[i].clone(), true))
            .collect();
        inner.add_special_tokens(&special);
        let mut eos: Vec<u32> = g.meta.get("tokenizer.ggml.eos_token_id").and_then(|v| v.as_u64()).map(|v| v as u32).into_iter().collect();
        for t in ["<turn|>", "<eos>"] {
            if let Some(id) = inner.token_to_id(t) && !eos.contains(&id) { eos.push(id); }
        }
        Ok(Tokenizer { inner, eos })
    }

    pub fn token_id(&self, t: &str) -> Option<u32> { self.inner.token_to_id(t) }

    pub fn encode(&self, text: &str) -> anyhow::Result<Vec<u32>> {
        Ok(self.inner.encode(text, false).map_err(|e| anyhow!("{e}"))?.get_ids().to_vec())
    }

    pub fn decode(&self, ids: &[u32]) -> anyhow::Result<String> {
        self.inner.decode(ids, false).map_err(|e| anyhow!("{e}"))
    }

    pub fn eos_ids(&self) -> Vec<u32> { self.eos.clone() }
}
