//! Receipts: everything needed to reproduce an answer bit for bit, and the
//! check that a rerun did.
//!
//! Output does not depend on drafting, batching, other requests or the
//! prompt cache, so a receipt only has to pin the model file, the build,
//! the device class, the prompt tokens and the sampling settings. Bits are
//! promised for the same build on the same device class, not across them.

mod file_hash;

use std::hash::BuildHasher;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use crate::{Completion, Request, Sampling};

pub use file_hash::blake3_hex;

/// The receipt format this build writes.
pub const FORMAT: u32 = 1;

/// What one loaded model needs to write receipts: its file, the device it
/// runs on and, optionally, a key to sign with.
pub struct Receipts {
    model: PathBuf,
    device: Device,
    key: Option<[u8; 32]>,
    model_file: OnceLock<Result<ModelFile, String>>,
}

impl Receipts {
    pub fn new(model: impl Into<PathBuf>, device: Device) -> Self {
        Receipts {
            model: model.into(),
            device,
            key: None,
            model_file: OnceLock::new(),
        }
    }

    /// Signs every receipt with this Ed25519 secret key.
    pub fn signed_with(mut self, key: [u8; 32]) -> Self {
        self.key = Some(key);
        self
    }

    /// The receipt for `c`, generated for `request` from `input` (the chat
    /// messages or the prompt text). `constraint` is the `grammar` or
    /// `response_format` the output was held to, as the API takes it.
    pub fn make(
        &self,
        input: Value,
        constraint: Option<Value>,
        request: &Request,
        c: &Completion,
    ) -> Result<Receipt, String> {
        let seed = request
            .sampling
            .seed
            .ok_or("a receipt needs a seed; the request had none")?;
        let model = self
            .model_file
            .get_or_init(|| ModelFile::read(&self.model))
            .clone()?;
        let mut receipt = Receipt {
            receipt: FORMAT,
            kinetic: Build::current().clone(),
            model,
            device: self.device.clone(),
            input,
            prompt: Tokens::new(&c.prompt_ids),
            sampling: Settings::new(request, seed, constraint),
            output: Output {
                finish: c.finish.as_str().into(),
                text: c.content.clone(),
                tokens: Tokens::new(&c.output_ids),
            },
            signature: None,
        };
        if let Some(key) = &self.key {
            receipt.sign(key);
        }
        Ok(receipt)
    }
}

/// Gives `sampling` a fresh seed if it has none, so the answer can be
/// reproduced.
pub fn seed(sampling: &mut Sampling) {
    if sampling.seed.is_none() {
        let fresh =
            std::collections::hash_map::RandomState::new().hash_one(std::time::SystemTime::now());
        sampling.seed = Some(fresh);
    }
}

/// A signed or unsigned record of one generation.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Receipt {
    /// The format version, [`FORMAT`].
    pub receipt: u32,
    pub kinetic: Build,
    pub model: ModelFile,
    pub device: Device,
    /// The chat messages, or the prompt text, as sent.
    pub input: Value,
    /// The exact tokens the model was given.
    pub prompt: Tokens,
    pub sampling: Settings,
    pub output: Output,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub signature: Option<Signature>,
}

/// The build that made a receipt.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Build {
    pub version: String,
    /// BLAKE3 of the executable, which pins every kernel compiled into it.
    pub build: String,
}

impl Build {
    /// This build.
    pub fn current() -> &'static Build {
        static BUILD: OnceLock<Build> = OnceLock::new();
        BUILD.get_or_init(|| Build {
            version: env!("CARGO_PKG_VERSION").into(),
            build: std::env::current_exe()
                .and_then(|exe| blake3_hex(&exe))
                .map_or_else(|_| "unknown".into(), |h| h[..16].to_owned()),
        })
    }
}

/// The model file a receipt was made with.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ModelFile {
    pub file: String,
    pub path: String,
    pub size: u64,
    pub blake3: String,
}

impl ModelFile {
    /// Hashes the file at `path`, or takes the hash from the cache.
    pub fn read(path: &Path) -> Result<ModelFile, String> {
        let fail = |e: std::io::Error| format!("{}: {e}", path.display());
        Ok(ModelFile {
            file: path
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default(),
            path: path.to_string_lossy().into_owned(),
            size: std::fs::metadata(path).map_err(fail)?.len(),
            blake3: blake3_hex(path).map_err(fail)?,
        })
    }
}

/// The device class and kernel path that decide the bits.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Device {
    /// Such as `cpu-x86_64-avx2` or `cuda-sm86`; bits match within a class.
    pub class: String,
    pub name: String,
    /// Load settings that change the bits, such as a quantized cache.
    #[serde(default, skip_serializing_if = "Map::is_empty")]
    pub settings: Map<String, Value>,
}

impl Device {
    pub fn new(class: impl Into<String>, name: impl Into<String>) -> Self {
        Device {
            class: class.into(),
            name: name.into(),
            settings: Map::new(),
        }
    }

    /// This CPU, classed by the kernels it runs.
    pub fn cpu() -> Self {
        Device::new(cpu_class(), "the CPU")
    }

    /// Records a load setting that changes the bits.
    pub fn with_setting(mut self, name: &str, value: impl Into<Value>) -> Self {
        self.settings.insert(name.into(), value.into());
        self
    }
}

fn cpu_class() -> String {
    let arch = std::env::consts::ARCH;
    #[cfg(target_arch = "x86_64")]
    if is_x86_feature_detected!("avx2")
        && is_x86_feature_detected!("fma")
        && is_x86_feature_detected!("f16c")
    {
        return format!("cpu-{arch}-avx2");
    }
    format!("cpu-{arch}-scalar")
}

/// Token ids with their count and hash.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Tokens {
    pub count: usize,
    /// BLAKE3 of the ids as little-endian u32s.
    pub blake3: String,
    pub ids: Vec<u32>,
}

impl Tokens {
    pub fn new(ids: &[u32]) -> Self {
        Tokens {
            count: ids.len(),
            blake3: hash_ids(ids),
            ids: ids.to_vec(),
        }
    }

    fn is_consistent(&self) -> bool {
        self.count == self.ids.len() && self.blake3 == hash_ids(&self.ids)
    }
}

fn hash_ids(ids: &[u32]) -> String {
    let mut h = blake3::Hasher::new();
    for id in ids {
        h.update(&id.to_le_bytes());
    }
    h.finalize().to_hex().to_string()
}

/// Every setting that decides which tokens come out.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Settings {
    pub temperature: f32,
    pub top_k: usize,
    pub top_p: f32,
    pub min_p: f32,
    pub typical_p: f32,
    pub top_n_sigma: f32,
    pub repeat_penalty: f32,
    pub presence_penalty: f32,
    pub frequency_penalty: f32,
    pub repeat_last_n: usize,
    /// Token id and the bias added to its logit.
    pub logit_bias: Vec<(u32, f32)>,
    pub xtc_probability: f32,
    pub xtc_threshold: f32,
    pub dry_multiplier: f32,
    pub dry_base: f32,
    pub dry_allowed_length: usize,
    pub dry_penalty_last_n: usize,
    pub dry_sequence_breakers: Vec<String>,
    pub mirostat: u8,
    pub mirostat_tau: f32,
    pub mirostat_eta: f32,
    pub seed: u64,
    pub max_tokens: Option<usize>,
    pub stop: Vec<String>,
    /// `{"grammar": ...}` or `{"response_format": ...}`, as sent.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub constraint: Option<Value>,
}

impl Settings {
    /// The settings of `request`, sampled with `seed`.
    pub fn new(request: &Request, seed: u64, constraint: Option<Value>) -> Self {
        let s = &request.sampling;
        Settings {
            temperature: s.temperature,
            top_k: s.top_k,
            top_p: s.top_p,
            min_p: s.min_p,
            typical_p: s.typical_p,
            top_n_sigma: s.top_n_sigma,
            repeat_penalty: s.repeat_penalty,
            presence_penalty: s.presence_penalty,
            frequency_penalty: s.frequency_penalty,
            repeat_last_n: s.repeat_last_n,
            logit_bias: s.logit_bias.clone(),
            xtc_probability: s.xtc_probability,
            xtc_threshold: s.xtc_threshold,
            dry_multiplier: s.dry_multiplier,
            dry_base: s.dry_base,
            dry_allowed_length: s.dry_allowed_length,
            dry_penalty_last_n: s.dry_penalty_last_n,
            dry_sequence_breakers: s.dry_sequence_breakers.clone(),
            mirostat: s.mirostat,
            mirostat_tau: s.mirostat_tau,
            mirostat_eta: s.mirostat_eta,
            seed,
            max_tokens: request.max_tokens,
            stop: request.stop.clone(),
            constraint,
        }
    }
}

/// What came out.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Output {
    pub finish: String,
    pub text: String,
    pub tokens: Tokens,
}

/// An Ed25519 signature over the receipt without this field, as compact
/// JSON.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Signature {
    pub public_key: String,
    pub ed25519: String,
}

/// How a rerun compares with the receipt.
#[derive(Debug, PartialEq)]
pub struct Comparison {
    /// The first output position that differs, with the receipt's token
    /// and the rerun's there; `None` when every token matches.
    pub first_difference: Option<(usize, Option<u32>, Option<u32>)>,
    /// What differs between the two runs besides the output, each a reason
    /// the bits may differ.
    pub reasons: Vec<String>,
}

impl Receipt {
    /// Reads a receipt from JSON.
    pub fn parse(text: &str) -> Result<Receipt, String> {
        let r: Receipt = serde_json::from_str(text).map_err(|e| format!("not a receipt: {e}"))?;
        if r.receipt != FORMAT {
            return Err(format!(
                "receipt format {} is not supported; this build reads {FORMAT}",
                r.receipt
            ));
        }
        Ok(r)
    }

    /// Pretty JSON, token ids kept on one line.
    pub fn to_json(&self) -> String {
        let pretty = serde_json::to_string_pretty(self).expect("a receipt serializes");
        join_number_lists(&pretty)
    }

    fn signed_bytes(&self) -> Vec<u8> {
        let unsigned = Receipt {
            signature: None,
            ..self.clone()
        };
        serde_json::to_vec(&unsigned).expect("a receipt serializes")
    }

    /// Signs the receipt with an Ed25519 secret key.
    pub fn sign(&mut self, key: &[u8; 32]) {
        let signature = kinetic_ktc::sign(&self.signed_bytes(), key);
        self.signature = Some(Signature {
            public_key: hex(&kinetic_ktc::public_key(key)),
            ed25519: hex(&signature),
        });
    }

    /// Checks the token hashes and, if signed, the signature; returns the
    /// signer's public key.
    pub fn check(&self) -> Result<Option<&str>, String> {
        if !self.prompt.is_consistent() {
            return Err("the prompt tokens do not match their hash".into());
        }
        if !self.output.tokens.is_consistent() {
            return Err("the output tokens do not match their hash".into());
        }
        let Some(sig) = &self.signature else {
            return Ok(None);
        };
        let key = unhex::<32>(&sig.public_key).ok_or("the public key is not 64 hex digits")?;
        let signature = unhex::<64>(&sig.ed25519).ok_or("the signature is not 128 hex digits")?;
        match kinetic_ktc::verify_signature(&self.signed_bytes(), &signature, &key) {
            Ok(true) => Ok(Some(&sig.public_key)),
            Ok(false) => {
                Err("the signature does not match: the receipt changed after signing".into())
            }
            Err(e) => Err(e.to_string()),
        }
    }

    /// The request that reproduces this receipt's output from its prompt
    /// tokens.
    pub fn request(&self) -> Result<Request, String> {
        let s = &self.sampling;
        let grammar = match &s.constraint {
            None => None,
            Some(c) => crate::api::constraint_grammar(c).map_err(|e| e.message)?,
        };
        Ok(Request {
            sampling: Sampling {
                temperature: s.temperature,
                top_k: s.top_k,
                top_p: s.top_p,
                min_p: s.min_p,
                typical_p: s.typical_p,
                top_n_sigma: s.top_n_sigma,
                repeat_penalty: s.repeat_penalty,
                presence_penalty: s.presence_penalty,
                frequency_penalty: s.frequency_penalty,
                repeat_last_n: s.repeat_last_n,
                logit_bias: s.logit_bias.clone(),
                xtc_probability: s.xtc_probability,
                xtc_threshold: s.xtc_threshold,
                dry_multiplier: s.dry_multiplier,
                dry_base: s.dry_base,
                dry_allowed_length: s.dry_allowed_length,
                dry_penalty_last_n: s.dry_penalty_last_n,
                dry_sequence_breakers: s.dry_sequence_breakers.clone(),
                // the engine matches the breakers to the vocabulary itself
                dry_breaker_tokens: Vec::new(),
                mirostat: s.mirostat,
                mirostat_tau: s.mirostat_tau,
                mirostat_eta: s.mirostat_eta,
                seed: Some(s.seed),
            },
            max_tokens: s.max_tokens,
            stop: s.stop.clone(),
            grammar,
        })
    }

    /// Compares `rerun`, a receipt for the same request, with this one.
    pub fn compare(&self, rerun: &Receipt) -> Comparison {
        let mut reasons = Vec::new();
        let mut differs = |what: &str, a: &dyn std::fmt::Display, b: &dyn std::fmt::Display| {
            reasons.push(format!("{what} differs: {a} in the receipt, {b} here"));
        };
        if self.model.blake3 != rerun.model.blake3 {
            differs("the model file", &self.model.blake3, &rerun.model.blake3);
        }
        if self.kinetic != rerun.kinetic {
            let build = |b: &Build| format!("{} (build {})", b.version, b.build);
            differs(
                "the Kinetic build",
                &build(&self.kinetic),
                &build(&rerun.kinetic),
            );
        }
        if self.device.class != rerun.device.class {
            differs("the device class", &self.device.class, &rerun.device.class);
        }
        if self.device.settings != rerun.device.settings {
            let s = |d: &Device| Value::Object(d.settings.clone()).to_string();
            differs("the load settings", &s(&self.device), &s(&rerun.device));
        }
        if self.prompt.ids != rerun.prompt.ids {
            reasons.push("the prompt tokens differ".into());
        }
        let (a, b) = (&self.output.tokens.ids, &rerun.output.tokens.ids);
        let first_difference = (0..a.len().max(b.len()))
            .find(|&i| a.get(i) != b.get(i))
            .map(|i| (i, a.get(i).copied(), b.get(i).copied()));
        Comparison {
            first_difference,
            reasons,
        }
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn unhex<const N: usize>(text: &str) -> Option<[u8; N]> {
    let text = text.trim();
    if text.len() != 2 * N || !text.is_ascii() {
        return None;
    }
    let mut out = [0; N];
    for (i, byte) in out.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&text[2 * i..2 * i + 2], 16).ok()?;
    }
    Some(out)
}

/// Reads an Ed25519 secret key: 32 raw bytes, or 64 hex digits.
pub fn read_key(path: &Path) -> Result<[u8; 32], String> {
    let bytes = std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
    if let Ok(raw) = <[u8; 32]>::try_from(bytes.as_slice()) {
        return Ok(raw);
    }
    std::str::from_utf8(&bytes)
        .ok()
        .and_then(unhex::<32>)
        .ok_or_else(|| {
            format!(
                "{}: a signing key is 32 bytes or 64 hex digits",
                path.display()
            )
        })
}

/// Puts every list of plain non-negative integers in `pretty` JSON on one
/// line.
fn join_number_lists(pretty: &str) -> String {
    let mut out = String::with_capacity(pretty.len());
    let mut lines = pretty.lines().peekable();
    while let Some(line) = lines.next() {
        out.push_str(line);
        if line.ends_with('[') {
            let mut raw = Vec::new();
            while let Some(&next) = lines.peek() {
                let item = next.trim().trim_end_matches(',');
                if item.is_empty() || !item.bytes().all(|b| b.is_ascii_digit()) {
                    break;
                }
                raw.push(next);
                lines.next();
            }
            match lines.peek() {
                Some(close) if !raw.is_empty() && close.trim_start().starts_with(']') => {
                    let items: Vec<&str> =
                        raw.iter().map(|l| l.trim().trim_end_matches(',')).collect();
                    out.push_str(&items.join(", "));
                    out.push_str(close.trim_start());
                    lines.next();
                }
                _ => {
                    for l in raw {
                        out.push('\n');
                        out.push_str(l);
                    }
                }
            }
        }
        out.push('\n');
    }
    out
}

#[cfg(test)]
mod tests;
