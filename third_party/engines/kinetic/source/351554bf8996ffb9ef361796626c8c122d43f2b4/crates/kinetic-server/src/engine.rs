//! Text in, text out: chat templates, tokens, stop handling and reasoning,
//! around a [`Backend`] that only sees tokens.

use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex, MutexGuard, OnceLock, PoisonError};

use kinetic_gguf::Gguf;
use kinetic_grammar::{Grammar, Vocabulary};
use kinetic_models::speculative::dry_breakers;
use kinetic_tokenizer::Tokenizer;
use kinetic_vision::VisionEncoder;
use serde_json::{Map, Value};

use crate::backend::{Backend, Job, PromptImage, Timings};
use crate::metrics::{Load, Slot, Stats};
use crate::model_info::ModelInfo;
use crate::receipt::Receipts;
use crate::template::ChatTemplate;
use crate::text::{opens_thinking, Split, StopStrings, ThinkSplitter};
use crate::tool_calls::{self, ToolCall, ToolSplitter};
use crate::tool_grammar;
use crate::{Logprobs, Sampling};

/// Tokens that end a turn in common chat formats, besides the model's EOS.
const END_OF_TURN: &[&str] = &[
    "<|im_end|>",
    "<|endoftext|>",
    "<|eot_id|>",
    "<|eom_id|>",
    "<|end|>",
    "<end_of_turn>",
    "<turn|>",
    "<|end_of_sentence|>",
];

/// Stands in for the rest of a message being written, to find where it
/// goes in the rendered template.
const DRAFT_END: &str = "\u{F8FF}";

/// The token chat templates write where an image goes, and the tokens the
/// model wants around the image's rows when its template writes none.
const IMAGE_PLACEHOLDERS: &[(&str, Option<[&str; 2]>)] = &[
    ("<|image_pad|>", None),
    // gemma 4, as llama.cpp's mtmd wraps it
    ("<|image|>", Some(["<|image>", "<image|>"])),
];

/// A request the engine cannot serve as asked.
#[derive(Debug, PartialEq, Eq)]
pub struct RequestError(pub String);

impl std::fmt::Display for RequestError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for RequestError {}

/// A prompt ready to run.
pub struct Prompt {
    pub text: String,
    /// Whether `<think>` blocks in the output are split off as reasoning,
    /// and if so, whether the prompt left one open. `None` keeps the output
    /// exactly as generated.
    pub thinking: Option<bool>,
    /// Image files, in the order the text places them.
    pub images: Vec<Vec<u8>>,
    /// The tools the model may call; calls in the output are split off
    /// unless this is empty.
    pub tools: Vec<Value>,
}

impl Prompt {
    /// A raw prompt, run as written, whose output is kept as generated.
    pub fn raw(text: impl Into<String>) -> Self {
        Prompt {
            text: text.into(),
            thinking: None,
            images: Vec::new(),
            tools: Vec::new(),
        }
    }
}

/// What to generate.
#[derive(Clone, Debug)]
pub struct Request {
    pub sampling: Sampling,
    /// `None` generates until the turn ends or the context is full.
    pub max_tokens: Option<usize>,
    pub stop: Vec<String>,
    /// Output must match this grammar.
    pub grammar: Option<Arc<Grammar>>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Finish {
    /// The model ended its turn or a stop string was reached.
    Stop,
    /// The token limit or the context length was reached.
    Length,
    /// The model ended its turn after calling tools.
    ToolCalls,
}

impl Finish {
    /// The OpenAI `finish_reason`.
    pub fn as_str(self) -> &'static str {
        match self {
            Finish::Stop => "stop",
            Finish::Length => "length",
            Finish::ToolCalls => "tool_calls",
        }
    }
}

/// A finished generation.
#[derive(Debug)]
pub struct Completion {
    pub content: String,
    pub reasoning: String,
    pub tool_calls: Vec<ToolCall>,
    pub finish: Finish,
    pub prompt_tokens: usize,
    pub completion_tokens: usize,
    pub timings: Timings,
    /// The tokens the model was given, images widened.
    pub prompt_ids: Vec<u32>,
    /// The tokens generated, the one that ended the turn included.
    pub output_ids: Vec<u32>,
}

/// One loaded model: its tokenizer and chat template, and the backends that
/// run it. Each request takes a free backend, one that has run the start of
/// its prompt if there is one, and waits for one when all are busy.
pub struct Engine<'a> {
    name: String,
    tokenizer: Tokenizer,
    template: Option<ChatTemplate>,
    bos: String,
    eos: String,
    stop_tokens: Vec<u32>,
    defaults: Sampling,
    context_length: usize,
    /// Built on the first constrained request; it walks every token.
    vocab: OnceLock<Vocabulary>,
    vision: Option<Vision<'a>>,
    info: ModelInfo,
    slots: usize,
    /// Idle backends with their slot ids.
    free: Mutex<Vec<(usize, Box<dyn Backend + 'a>)>>,
    stats: Stats,
    freed: Condvar,
    /// Requests waiting for a backend, which running ahead gives way to.
    waiting: AtomicUsize,
    /// Calls to [`Engine::prefill`] so far; each gives way to the next.
    drafts: AtomicU64,
    zero_wait: bool,
    receipts: Option<Receipts>,
}

struct Vision<'a> {
    encoder: VisionEncoder<'a>,
    /// The token the chat template writes where an image goes.
    placeholder: u32,
    /// Tokens written before and after the image's rows.
    around: [Vec<u32>; 2],
}

impl<'a> Engine<'a> {
    /// Reads the tokenizer, chat template and recommended sampling from the
    /// model's metadata. `context_length` caps prompt plus output tokens.
    pub fn new(
        name: impl Into<String>,
        gguf: &Gguf,
        backend: Box<dyn Backend + 'a>,
        context_length: usize,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let tokenizer = Tokenizer::from_gguf(gguf)?;
        let template = gguf
            .get("tokenizer.chat_template")
            .and_then(|v| v.as_str())
            .map(ChatTemplate::new)
            .transpose()
            .map_err(|e| format!("chat template: {e}"))?;
        let text = |id: Option<u32>| {
            id.map(|id| String::from_utf8_lossy(tokenizer.piece(id)).into_owned())
                .unwrap_or_default()
        };
        let (bos, eos) = (text(tokenizer.bos()), text(tokenizer.eos()));

        let mut stop_tokens: Vec<u32> = tokenizer.eos().into_iter().collect();
        for marker in END_OF_TURN {
            let ids = tokenizer.encode(marker, true);
            let ids: Vec<u32> = ids
                .into_iter()
                .filter(|&id| Some(id) != tokenizer.bos())
                .collect();
            if let [id] = ids[..] {
                if !stop_tokens.contains(&id) {
                    stop_tokens.push(id);
                }
            }
        }

        Ok(Engine {
            name: name.into(),
            tokenizer,
            template,
            bos,
            eos,
            stop_tokens,
            defaults: recommended_sampling(gguf),
            context_length,
            vocab: OnceLock::new(),
            vision: None,
            info: ModelInfo::new(gguf),
            slots: 1,
            free: Mutex::new(vec![(0, backend)]),
            stats: Stats::new(1),
            freed: Condvar::new(),
            waiting: AtomicUsize::new(0),
            drafts: AtomicU64::new(0),
            zero_wait: true,
            receipts: None,
        })
    }

    /// Lets requests ask for receipts, made with `receipts`.
    pub fn with_receipts(mut self, receipts: Receipts) -> Self {
        self.receipts = Some(receipts);
        self
    }

    /// What receipts are made with, if requests may ask for them.
    pub fn receipts(&self) -> Option<&Receipts> {
        self.receipts.as_ref()
    }

    /// Renders chats with the Jinja template `source` instead of the
    /// model's own, as llama.cpp's `--chat-template-file` does.
    pub fn with_chat_template(mut self, source: &str) -> Result<Self, RequestError> {
        let template =
            ChatTemplate::new(source).map_err(|e| RequestError(format!("chat template: {e}")))?;
        self.template = Some(template);
        self.info.chat_template = Some(source.to_owned());
        Ok(self)
    }

    /// Turns Zero Wait off: [`Engine::prefill`] then runs nothing.
    pub fn without_zero_wait(mut self) -> Self {
        self.zero_wait = false;
        self
    }

    /// Adds backends, so that as many more requests run at once. They should
    /// share one model, whose seats let their passes go through the weights
    /// together; see [`kinetic_models::Model::seat`].
    pub fn with_backends(mut self, more: impl IntoIterator<Item = Box<dyn Backend + 'a>>) -> Self {
        let free = self.free.get_mut().unwrap_or_else(PoisonError::into_inner);
        let first = free.len();
        free.extend(more.into_iter().enumerate().map(|(i, b)| (first + i, b)));
        self.slots = free.len();
        self.stats.resize(self.slots);
        self
    }

    /// How many requests can run at once, and how many are running.
    pub fn slots(&self) -> (usize, usize) {
        (self.slots, self.slots - self.lock_free().len())
    }

    /// Each slot's current or last request.
    pub(crate) fn slot_states(&self) -> Vec<Slot> {
        self.stats.slots()
    }

    /// The totals since start in Prometheus' text format.
    pub(crate) fn metrics(&self) -> String {
        let (_, processing) = self.slots();
        self.stats.prometheus(&Load {
            processing,
            deferred: self.waiting.load(Ordering::SeqCst),
        })
    }

    fn lock_free(&self) -> MutexGuard<'_, Vec<(usize, Box<dyn Backend + 'a>)>> {
        self.free.lock().unwrap_or_else(PoisonError::into_inner)
    }

    /// Runs `f` on a free backend, the one that reuses most of `prompt`.
    fn on_backend<T>(&self, prompt: &[u32], f: impl FnOnce(usize, &mut dyn Backend) -> T) -> T {
        self.waiting.fetch_add(1, Ordering::SeqCst);
        let mut free = self.lock_free();
        while free.is_empty() {
            free = self
                .freed
                .wait(free)
                .unwrap_or_else(PoisonError::into_inner);
        }
        self.waiting.fetch_sub(1, Ordering::SeqCst);
        self.on_free(free, prompt, f)
    }

    /// [`Engine::on_backend`] that gives way to every request: `None` once
    /// one waits for a backend, or once `live` turns false.
    fn on_idle_backend<T>(
        &self,
        prompt: &[u32],
        live: impl Fn() -> bool,
        f: impl FnOnce(usize, &mut dyn Backend) -> T,
    ) -> Option<T> {
        let mut free = self.lock_free();
        loop {
            if self.waiting.load(Ordering::SeqCst) > 0 || !live() {
                return None;
            }
            if !free.is_empty() {
                return Some(self.on_free(free, prompt, f));
            }
            free = self
                .freed
                .wait(free)
                .unwrap_or_else(PoisonError::into_inner);
        }
    }

    fn on_free<T>(
        &self,
        mut free: MutexGuard<'_, Vec<(usize, Box<dyn Backend + 'a>)>>,
        prompt: &[u32],
        f: impl FnOnce(usize, &mut dyn Backend) -> T,
    ) -> T {
        let best = (0..free.len())
            .max_by_key(|&i| free[i].1.reuses(prompt))
            .expect("a free backend");
        let backend = free.swap_remove(best);
        drop(free);
        // Returns the backend even when `f` panics, as a lost client does
        // not take a slot with it.
        struct Back<'e, 'a>(&'e Engine<'a>, Option<(usize, Box<dyn Backend + 'a>)>);
        impl Drop for Back<'_, '_> {
            fn drop(&mut self) {
                self.0.lock_free().extend(self.1.take());
                // drafts wait here too and must not take a request's wakeup
                self.0.freed.notify_all();
            }
        }
        let mut back = Back(self, Some(backend));
        let (id, backend) = back.1.as_mut().expect("the backend");
        f(*id, backend.as_mut())
    }

    /// Lets prompts carry images, which `encoder` turns into rows of the
    /// model's embeddings.
    pub fn with_vision(mut self, encoder: VisionEncoder<'a>) -> Result<Self, RequestError> {
        let bos = self.tokenizer.bos();
        let single = |text: &str| {
            let ids = self.tokenizer.encode(text, true);
            match ids.strip_prefix(bos.as_slice()).unwrap_or(&ids) {
                &[id] => Some(id),
                _ => None,
            }
        };
        let (placeholder, around) = IMAGE_PLACEHOLDERS
            .iter()
            .find_map(|&(text, around)| {
                let around = match around {
                    Some([before, after]) => [vec![single(before)?], vec![single(after)?]],
                    None => [Vec::new(), Vec::new()],
                };
                Some((single(text)?, around))
            })
            .ok_or_else(|| RequestError("the model has no token for images".into()))?;
        self.vision = Some(Vision {
            encoder,
            placeholder,
            around,
        });
        Ok(self)
    }

    /// Whether prompts may carry images.
    pub fn sees_images(&self) -> bool {
        self.vision.is_some()
    }

    /// The model's name as clients see it.
    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn context_length(&self) -> usize {
        self.context_length
    }

    /// What the model's header says about it.
    pub fn info(&self) -> &ModelInfo {
        &self.info
    }

    /// The model's tokenizer.
    pub fn tokenizer(&self) -> &Tokenizer {
        &self.tokenizer
    }

    /// The sampling the model file recommends, or common defaults.
    pub fn default_sampling(&self) -> &Sampling {
        &self.defaults
    }

    /// Renders `messages`, OpenAI-style message objects, with the model's
    /// chat template. `options` become template variables; reasoning is off
    /// unless they set `enable_thinking`, and `tools` are the functions the
    /// model may call.
    pub fn chat_prompt(
        &self,
        messages: &[Value],
        options: &Map<String, Value>,
    ) -> Result<Prompt, RequestError> {
        let template = self
            .template
            .as_ref()
            .ok_or_else(|| RequestError("the model has no chat template".into()))?;
        let mut context = Map::new();
        context.insert("enable_thinking".into(), false.into());
        context.extend(options.clone());
        context.insert(
            "messages".into(),
            tool_calls::template_messages(messages).into(),
        );
        context.insert("add_generation_prompt".into(), true.into());
        context.insert("bos_token".into(), self.bos.clone().into());
        context.insert("eos_token".into(), self.eos.clone().into());
        let text = template
            .render(&context)
            .map_err(|e| RequestError(format!("chat template: {e}")))?;
        let tools = match options.get("tools") {
            Some(Value::Array(tools)) => tools.clone(),
            _ => Vec::new(),
        };
        Ok(Prompt {
            thinking: Some(opens_thinking(&text)),
            text,
            images: Vec::new(),
            tools,
        })
    }

    /// A grammar that holds the reply to calls of `prompt`'s tools, in the
    /// chat template's call format; several calls with `parallel`.
    pub fn tool_grammar(&self, prompt: &Prompt, parallel: bool) -> Result<Grammar, RequestError> {
        let template = self.info.chat_template.as_deref().unwrap_or_default();
        let shape = tool_grammar::Shape {
            thinking: prompt.thinking == Some(true),
            parallel,
        };
        tool_grammar::grammar(template, &prompt.tools, shape).map_err(RequestError)
    }

    /// Generates after `prompt`, calling `on_delta` with each new piece of
    /// text and the number of tokens so far; returning false stops early.
    pub fn complete(
        &self,
        prompt: &Prompt,
        request: &Request,
        on_delta: &mut dyn FnMut(&Split, usize) -> bool,
    ) -> Result<Completion, RequestError> {
        self.complete_with_logprobs(prompt, request, None, on_delta)
    }

    /// [`Engine::complete`] that also records in `logprobs` the
    /// log-probability of each generated token, up to the delta's token
    /// count when `on_delta` is called and of exactly the completion's
    /// tokens, without a final stop token, at the end.
    pub fn complete_with_logprobs(
        &self,
        prompt: &Prompt,
        request: &Request,
        logprobs: Option<&Logprobs>,
        on_delta: &mut dyn FnMut(&Split, usize) -> bool,
    ) -> Result<Completion, RequestError> {
        let ids = self.encode(&prompt.text);
        self.complete_tokens(ids, prompt, request, logprobs, on_delta)
    }

    /// [`Engine::complete_with_logprobs`] after prompt tokens already
    /// encoded; `prompt` only gives the images, reasoning and tools.
    pub fn complete_tokens(
        &self,
        mut ids: Vec<u32>,
        prompt: &Prompt,
        request: &Request,
        logprobs: Option<&Logprobs>,
        on_delta: &mut dyn FnMut(&Split, usize) -> bool,
    ) -> Result<Completion, RequestError> {
        if ids.is_empty() {
            return Err(RequestError("the prompt is empty".into()));
        }
        let images = self.place_images(&prompt.images, &mut ids)?;
        let room = self.context_length.saturating_sub(ids.len());
        if room == 0 {
            return Err(RequestError(format!(
                "the prompt is {} tokens, which leaves no room in the {}-token context",
                ids.len(),
                self.context_length
            )));
        }
        let max_tokens = request.max_tokens.map_or(room, |n| n.min(room));

        let mut decoder = self.tokenizer.stream();
        let mut stops = StopStrings::new(&request.stop);
        let mut think = prompt.thinking.map(ThinkSplitter::new);
        let mut tools = (!prompt.tools.is_empty()).then(ToolSplitter::new);
        let calls = |mut part: Split, tools: &mut Option<ToolSplitter>| {
            if let Some(t) = tools.as_mut() {
                part.content = t.push(&part.content);
            }
            part
        };
        let mut split = |text: &str| {
            let part = match think.as_mut() {
                Some(t) => t.push(text),
                None => Split {
                    content: text.to_owned(),
                    ..Split::default()
                },
            };
            calls(part, &mut tools)
        };
        let mut out = Split::default();
        let mut finish = Finish::Length;
        let mut cut = false;
        let mut generated = 0;
        let mut output_ids = Vec::new();
        let mut deliver = |part: Split, generated: usize, out: &mut Split| {
            out.reasoning.push_str(&part.reasoning);
            out.content.push_str(&part.content);
            part.is_empty() || on_delta(&part, generated)
        };

        let vocab = request.grammar.as_ref().map(|_| {
            self.vocab.get_or_init(|| {
                Vocabulary::from_tokenizer(&self.tokenizer).with_stop_tokens(&self.stop_tokens)
            })
        });
        let sampling = self.with_breakers(&request.sampling);
        let job = Job {
            sampling: &sampling,
            max_tokens,
            stop_tokens: &self.stop_tokens,
            grammar: request.grammar.as_deref().zip(vocab),
            images: &images,
            logprobs,
        };
        let timings = self.on_backend(&ids, |slot, backend| {
            self.stats
                .start(slot, request, prompt.text.clone(), max_tokens);
            let timings = backend.generate(&ids, &job, &mut |tokens| {
                self.stats
                    .update(slot, |s| s.decoded = generated + tokens.len());
                for &t in tokens {
                    generated += 1;
                    output_ids.push(t);
                    if self.stop_tokens.contains(&t) {
                        finish = Finish::Stop;
                        return false;
                    }
                    let (text, hit) = stops.push(&decoder.push(t));
                    let open = deliver(split(&text), generated, &mut out);
                    if hit {
                        (finish, cut) = (Finish::Stop, true);
                        return false;
                    }
                    if !open {
                        return false;
                    }
                }
                true
            });
            self.stats.finish(slot, &timings);
            timings
        });
        if let Some(log) = logprobs {
            log.truncate(generated - usize::from(finish == Finish::Stop && !cut));
        }

        if !cut {
            // the decoder holds back only an unfinished character, e.g. one cut by the token limit; drop it
            deliver(split(&stops.finish()), generated, &mut out);
        }
        if let Some(t) = think.as_mut() {
            let part = calls(t.finish(), &mut tools);
            deliver(part, generated, &mut out);
        }
        let tool_calls = match tools {
            Some(t) => {
                let (content, found) = t.finish(&prompt.tools);
                let part = Split {
                    content,
                    ..Split::default()
                };
                deliver(part, generated, &mut out);
                found
            }
            None => Vec::new(),
        };
        out.reasoning.truncate(out.reasoning.trim_end().len());
        if !tool_calls.is_empty() {
            out.content.truncate(out.content.trim_end().len());
            if finish == Finish::Stop {
                finish = Finish::ToolCalls;
            }
        }
        Ok(Completion {
            content: out.content,
            reasoning: out.reasoning,
            tool_calls,
            finish,
            prompt_tokens: ids.len(),
            completion_tokens: generated,
            timings,
            prompt_ids: ids,
            output_ids,
        })
    }
}

impl Engine<'_> {
    /// [`Engine::chat_prompt`] for a conversation whose last message is
    /// still being written: the text up to just before that message's last
    /// word, whose tokens may still merge with what comes next, for
    /// [`Engine::prefill`].
    pub fn draft_prompt(
        &self,
        messages: &[Value],
        options: &Map<String, Value>,
    ) -> Result<Prompt, RequestError> {
        let mut messages = messages.to_vec();
        let last = messages
            .last_mut()
            .ok_or_else(|| RequestError("no messages".into()))?;
        let content = last["content"].as_str().unwrap_or_default();
        last["content"] = format!("{}{DRAFT_END}", before_last_word(content)).into();
        let mut prompt = self.chat_prompt(&messages, options)?;
        let end = prompt
            .text
            .rfind(DRAFT_END)
            .ok_or_else(|| RequestError("the chat template dropped the draft".into()))?;
        prompt.text.truncate(end);
        Ok(prompt)
    }

    /// Zero Wait: runs `prompt`, the start of a request still being
    /// written, ahead on an idle backend in whole batches, so the request
    /// that follows only runs what is new. Gives way after each batch to
    /// any request that waits and to the next call, and never changes what
    /// a request generates. Returns the prompt tokens run.
    pub fn prefill(&self, prompt: &Prompt) -> usize {
        if !self.zero_wait {
            return 0;
        }
        let ids = self.encode(&prompt.text);
        if !prompt.images.is_empty() || ids.is_empty() || ids.len() >= self.context_length {
            return 0;
        }
        let me = self.drafts.fetch_add(1, Ordering::SeqCst) + 1;
        let live = || self.drafts.load(Ordering::SeqCst) == me;
        let mut ran = None;
        while let Some(now) = self.on_idle_backend(&ids, live, |_, b| b.run_ahead(&ids)) {
            if ran == Some(now) {
                break;
            }
            ran = Some(now);
        }
        ran.unwrap_or(0)
    }

    /// `sampling` with its DRY breakers in this model's tokens.
    fn with_breakers(&self, sampling: &Sampling) -> Sampling {
        let mut s = sampling.clone();
        if s.dry_multiplier != 0.0 && s.dry_breaker_tokens.is_empty() {
            let specials = [self.tokenizer.bos(), self.tokenizer.eos()];
            // shortcut: walks the vocabulary per request as llama.cpp does;
            // cache per breaker list if DRY requests get frequent
            s.dry_breaker_tokens = dry_breakers(
                &s.dry_sequence_breakers,
                self.tokenizer.vocab_size(),
                |id| self.tokenizer.piece(id),
                |text| {
                    let mut ids = self.tokenizer.encode(text, false);
                    ids.retain(|&id| !specials.contains(&Some(id)));
                    ids
                },
            );
        }
        s
    }

    fn encode(&self, text: &str) -> Vec<u32> {
        let mut ids = self.tokenizer.encode(text, true);
        // Templates that write BOS themselves would otherwise get two.
        if ids.len() > 1 && ids[0] == ids[1] && Some(ids[0]) == self.tokenizer.bos() {
            ids.remove(0);
        }
        ids
    }

    /// Encodes `images` and widens each placeholder token in `ids` to one
    /// per image row.
    fn place_images(
        &self,
        images: &[Vec<u8>],
        ids: &mut Vec<u32>,
    ) -> Result<Vec<PromptImage>, RequestError> {
        if images.is_empty() {
            return Ok(Vec::new());
        }
        let vision = self.vision.as_ref().ok_or_else(|| {
            RequestError("the model was started without an image projector (--mmproj)".into())
        })?;
        let places: Vec<usize> = (0..ids.len())
            .filter(|&i| ids[i] == vision.placeholder)
            .collect();
        if places.len() != images.len() || ids.last() == Some(&vision.placeholder) {
            return Err(RequestError(format!(
                "the chat template placed {} of {} images",
                places.len(),
                images.len()
            )));
        }
        let mut placed = Vec::with_capacity(images.len());
        let mut widened = Vec::with_capacity(ids.len());
        let mut next = 0;
        for (&place, bytes) in places.iter().zip(images) {
            let image = kinetic_vision::decode(bytes)
                .and_then(|picture| vision.encoder.encode(&vision.encoder.prepare(&picture)))
                .map_err(|e| RequestError(format!("image {}: {e}", placed.len() + 1)))?;
            widened.extend_from_slice(&ids[next..place]);
            widened.extend_from_slice(&vision.around[0]);
            let at = widened.len();
            widened.extend(std::iter::repeat_n(vision.placeholder, image.len()));
            widened.extend_from_slice(&vision.around[1]);
            placed.push(PromptImage { at, image });
            next = place + 1;
        }
        widened.extend_from_slice(&ids[next..]);
        *ids = widened;
        Ok(placed)
    }
}

/// `text` without its last word, which may still be growing, and the
/// spaces before it.
fn before_last_word(text: &str) -> &str {
    let text = text.trim_end();
    text.rfind(char::is_whitespace)
        .map_or("", |i| text[..i].trim_end())
}

fn recommended_sampling(gguf: &Gguf) -> Sampling {
    let f = |key: &str| {
        gguf.get(&format!("general.sampling.{key}"))
            .and_then(|v| v.as_f32())
    };
    let n = |key: &str| {
        gguf.get(&format!("general.sampling.{key}"))
            .and_then(|v| v.as_u64())
            .map(|v| v as usize)
    };
    let d = Sampling::default();
    Sampling {
        temperature: f("temp").unwrap_or(d.temperature),
        top_k: n("top_k").unwrap_or(d.top_k),
        top_p: f("top_p").unwrap_or(d.top_p),
        min_p: f("min_p").unwrap_or(d.min_p),
        repeat_penalty: f("penalty_repeat").unwrap_or(d.repeat_penalty),
        repeat_last_n: n("penalty_last_n").unwrap_or(d.repeat_last_n),
        ..d
    }
}

#[cfg(test)]
mod tests {
    use super::before_last_word;

    #[test]
    fn a_draft_stops_before_its_last_word() {
        assert_eq!(before_last_word(""), "");
        assert_eq!(before_last_word("Summ"), "");
        assert_eq!(
            before_last_word("Summarize this.\n\nWhat is"),
            "Summarize this.\n\nWhat"
        );
        assert_eq!(before_last_word("two words  "), "two");
        assert_eq!(before_last_word("zażółć gęślą"), "zażółć");
    }
}
