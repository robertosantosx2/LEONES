//! The small HTTP/1.1 subset `rustingstrata serve` speaks (std::net, one request per connection) and its chat request.

use crate::chat::{Json, Msg, tool_def};
use anyhow::{Context, bail};
use serde_json::Value;
use std::io::{BufRead, Read};
use std::path::{Path, PathBuf};

pub struct Request {
    pub method: String,
    pub path: String,
    pub host: String,
    pub auth: String,
    pub json: bool,
    pub body: Vec<u8>,
}

/// Reads one request (Content-Length bodies only, no chunked uploads). Headers are capped at 64 KiB and the body at
/// 8 MiB.
pub fn read_request(r: &mut impl BufRead) -> anyhow::Result<Request> {
    let mut h = r.take(64 << 10);
    let mut line = String::new();
    h.read_line(&mut line)?;
    let mut it = line.split_whitespace();
    let (method, path) = (it.next().context("empty request")?.to_string(), it.next().context("no path")?.to_string());
    let (mut len, mut host, mut auth, mut json) = (0, String::new(), String::new(), false);
    loop {
        line.clear();
        if h.read_line(&mut line)? == 0 { bail!("headers cut off or too long"); }
        let l = line.trim_end();
        if l.is_empty() { break; }
        let Some((k, v)) = l.split_once(':') else { continue };
        let (k, v) = (k.to_ascii_lowercase(), v.trim());
        match k.as_str() {
            "content-length" => len = v.parse().context("bad Content-Length")?,
            "host" => host = v.to_string(),
            "authorization" => auth = v.to_string(),
            // The Anthropic API's key header (Claude Code with ANTHROPIC_API_KEY).
            "x-api-key" if auth.is_empty() => auth = format!("Bearer {v}"),
            "content-type" => json = v.starts_with("application/json"),
            _ => {}
        }
    }
    if len > 8 << 20 { bail!("body too large"); }
    let mut body = vec![0; len];
    r.read_exact(&mut body)?;
    Ok(Request { method, path, host, auth, json, body })
}

/// Host header check against DNS rebinding: a loopback name, the host the server was bound to, or a name the user
/// explicitly allowed (`--allowed-hosts` / `STRATA_ALLOWED_HOSTS`).
pub fn host_ok(host: &str, bound: &str, allowed: &[String]) -> bool {
    let name = |s: &str| {
        let s = s.trim();
        s.rsplit_once(':').filter(|(_, p)| p.parse::<u16>().is_ok()).map_or(s, |x| x.0).trim_end_matches('.').to_ascii_lowercase()
    };
    let n = name(host);
    !n.is_empty() && (matches!(n.as_str(), "localhost" | "127.0.0.1" | "[::1]") || n == name(bound) || allowed.iter().any(|a| name(a) == n))
}

/// Whether the client closed the connection (it sends nothing more after its request).
pub fn gone(c: &std::net::TcpStream) -> bool {
    if c.set_nonblocking(true).is_err() { return false; }
    let r = c.peek(&mut [0]);
    let _ = c.set_nonblocking(false);
    match r { Ok(n) => n == 0, Err(e) => e.kind() != std::io::ErrorKind::WouldBlock }
}

/// `Authorization` header check for `--api-key`, without an early exit on the first differing byte.
pub fn key_ok(auth: &str, key: &str) -> bool {
    if key.is_empty() { return false; }
    let a = auth.strip_prefix("Bearer ").unwrap_or("").as_bytes();
    a.len() == key.len() && a.iter().zip(key.as_bytes()).fold(0, |x, (p, q)| x | (p ^ q)) == 0
}

/// The requests each customer key has open (`--max-per-key`), by key id.
pub type Open = std::sync::Arc<std::sync::Mutex<std::collections::HashMap<u64, usize>>>;

/// One request's place in its key's count of open requests; dropping it frees the place.
pub struct Hold(Open, u64);

impl Hold {
    /// A place for key `id`, or None when it already has `cap` requests open.
    pub fn take(open: &Open, id: u64, cap: usize) -> Option<Hold> {
        let mut m = open.lock().unwrap();
        let n = m.entry(id).or_default();
        if *n >= cap { return None; }
        *n += 1;
        Some(Hold(open.clone(), id))
    }
}

impl Drop for Hold {
    fn drop(&mut self) {
        let mut m = self.0.lock().unwrap();
        if let Some(n) = m.get_mut(&self.1) { *n -= 1; if *n == 0 { m.remove(&self.1); } }
    }
}

/// The API keys: `--api-key` (all routes) and the `--api-keys` file (chat and model list only). No key at all
/// leaves the server open, as for local use.
#[derive(Clone, Default)]
pub struct Keys {
    pub admin: Option<String>,
    /// (name, key), the name as the file gives it.
    pub users: Vec<(String, String)>,
}

/// Who sent a request: the key's name for the usage log, a number that keeps each key's cached conversations
/// apart (0 for the admin key or an open server), and whether it may use the admin routes.
#[derive(Clone, Debug, PartialEq)]
pub struct Who { pub name: String, pub id: u64, pub admin: bool }

impl Keys {
    /// Reads a key file: one `name key` pair a line, `#` starts a comment.
    pub fn parse(text: &str) -> anyhow::Result<Vec<(String, String)>> {
        let mut v: Vec<(String, String)> = vec![];
        for (n, line) in text.lines().enumerate() {
            let l = line.split('#').next().unwrap_or("").trim();
            if l.is_empty() { continue; }
            let mut it = l.split_whitespace();
            let (Some(name), Some(key), None) = (it.next(), it.next(), it.next()) else { bail!("line {}: want `name key`", n + 1) };
            if key.len() < 16 { bail!("line {}: key of {name} is shorter than 16 characters", n + 1); }
            if v.iter().any(|(a, k)| a == name || k == key) { bail!("line {}: name or key of {name} repeats", n + 1); }
            v.push((name.into(), key.into()));
        }
        Ok(v)
    }

    pub fn any(&self) -> bool { self.admin.is_some() || !self.users.is_empty() }

    /// The sender of `auth` (an `Authorization` header), or None for a missing or wrong key.
    pub fn who(&self, auth: &str) -> Option<Who> {
        if !self.any() { return Some(Who { name: String::new(), id: 0, admin: true }); }
        if self.admin.as_deref().is_some_and(|k| key_ok(auth, k)) { return Some(Who { name: "admin".into(), id: 0, admin: true }); }
        // The id comes from the key, not its line, so a reloaded file with other lines gives no key another's id.
        self.users.iter().find(|(_, k)| key_ok(auth, k)).map(|(n, k)| {
            use std::hash::{Hash, Hasher};
            let mut h = std::hash::DefaultHasher::new();
            k.hash(&mut h);
            Who { name: n.clone(), id: h.finish().max(1), admin: false }
        })
    }
}

/// GGUF models under `dir` and two folder levels below it, as (name relative to `dir` with `/` separators, path,
/// bytes over all shards), sorted by name; see `models`.
pub fn list_models(dir: &Path) -> Vec<(String, PathBuf, u64)> {
    let (mut files, mut dirs) = (Vec::new(), vec![(dir.to_path_buf(), 0)]);
    while let Some((d, depth)) = dirs.pop() {
        let Ok(rd) = std::fs::read_dir(&d) else { continue };
        for p in rd.flatten().map(|e| e.path()) {
            if p.is_dir() { if depth < 2 { dirs.push((p, depth + 1)); } continue; }
            let id = p.strip_prefix(dir).unwrap_or(&p).to_string_lossy().replace('\\', "/");
            files.push((id, std::fs::metadata(&p).map_or(0, |m| m.len())));
        }
    }
    let mut out: Vec<_> = models(&files).into_iter().map(|(id, n)| (id.clone(), dir.join(id), n)).collect();
    out.sort();
    out
}

/// The models among files given as (name, bytes): .gguf files, complete split models once by their first shard
/// with the bytes of their shards, vision projectors (`mmproj*`) left out.
pub fn models(files: &[(String, u64)]) -> Vec<(String, u64)> {
    let sizes: std::collections::HashMap<&str, u64> = files.iter().map(|(name, bytes)| (name.as_str(), *bytes)).collect();
    files.iter().filter(|(n, _)| n.ends_with(".gguf") && !n.rsplit('/').next().unwrap_or(n).starts_with("mmproj"))
        .filter_map(|(n, b)| match shard_parts(n) {
            Some((stem, 1, total)) if total > 0 && total as usize <= files.len() => {
                (1..=total).try_fold(0u64, |bytes, i| {
                    sizes.get(format!("{stem}-{i:05}-of-{total:05}.gguf").as_str())
                        .and_then(|part| bytes.checked_add(*part))
                }).map(|bytes| (n.clone(), bytes))
            }
            Some(_) => None,
            None => Some((n.clone(), *b)),
        }).collect()
}

/// "dir/name-00002-of-00003.gguf" gives ("dir/name", 2).
pub fn shard(n: &str) -> Option<(&str, u32)> {
    shard_parts(n).map(|(stem, i, _)| (stem, i))
}

fn shard_parts(n: &str) -> Option<(&str, u32, u32)> {
    let (head, total) = n.strip_suffix(".gguf")?.rsplit_once("-of-")?;
    let (stem, i) = head.rsplit_once('-')?;
    let digits = |s: &str| s.len() == 5 && s.bytes().all(|b| b.is_ascii_digit());
    if !digits(total) || !digits(i) { return None; }
    Some((stem, i.parse().ok()?, total.parse().ok()?))
}

/// The parts of an OpenAI chat completion request that strata uses. Sampling fields left out fall back to the
/// server's flags (greedy by default).
pub struct ChatRequest {
    pub messages: Vec<Msg>,
    /// Tool definitions as the template prints them (`chat::tool_def`).
    pub tools: Vec<Json>,
    /// Whether to look for tool calls in the reply (`tool_choice` other than "none"). "required" and a named
    /// function are not enforced: the model may still answer in text.
    pub tool_calls: bool,
    pub max_tokens: Option<usize>,
    pub stream: bool,
    pub think: bool,
    /// `chat_template_kwargs.preserve_thinking`; the server's `--preserve-thinking` when absent.
    pub preserve_thinking: Option<bool>,
    pub temperature: Option<f32>,
    pub top_k: Option<usize>,
    pub top_p: Option<f32>,
    pub seed: Option<u64>,
    /// The reply ends before the first of these strings (`stop`).
    pub stop: Vec<String>,
}

pub fn chat_request(body: &[u8]) -> anyhow::Result<ChatRequest> {
    let v: Value = serde_json::from_slice(body)?;
    // Messages and tools are read again in key order: the template prints tools and call arguments as given.
    let j: Json = serde_json::from_slice(body)?;
    let Json::Arr(msgs) = j.get("messages") else { bail!("missing messages") };
    let messages = msgs.iter().map(Msg::from_json).collect::<anyhow::Result<Vec<_>>>()?;
    if messages.is_empty() { bail!("no messages"); }
    let tools = match j.get("tools") {
        Json::Null => vec![],
        Json::Arr(a) => a.iter().map(tool_def).collect::<anyhow::Result<_>>()?,
        _ => bail!("tools must be an array"),
    };
    let tool_calls = match &v["tool_choice"] {
        Value::Null => true,
        Value::String(s) if ["auto", "required", "none"].contains(&s.as_str()) => s != "none",
        Value::Object(o) if o.get("type").and_then(Value::as_str) == Some("function") => true,
        _ => bail!("tool_choice must be \"auto\", \"required\", \"none\" or a function"),
    };
    // Optional fields: absent or null means the default, anything else must be valid.
    let int = |k: &str, min: u64| match &v[k] {
        Value::Null => Ok(None),
        x => x.as_u64().filter(|&n| n >= min).map(Some).with_context(|| format!("{k} must be an integer >= {min}")),
    };
    let num = |k: &str, ok: fn(f64) -> bool, want: &str| match &v[k] {
        Value::Null => Ok(None),
        x => x.as_f64().filter(|&f| ok(f)).map(|f| Some(f as f32)).with_context(|| format!("{k} must be {want}")),
    };
    let max_tokens = int("max_completion_tokens", 1)?.or(int("max_tokens", 1)?).map(|n| n as usize);
    if int("n", 1)?.is_some_and(|n| n != 1) { bail!("only n = 1 is supported"); }
    let stop = match &v["stop"] {
        Value::Null => Some(vec![]),
        Value::String(s) => Some(vec![s.clone()]),
        Value::Array(a) => a.iter().map(|s| s.as_str().map(str::to_owned)).collect(),
        _ => None,
    }.context("stop must be a string or an array of strings")?.into_iter().filter(|s| !s.is_empty()).collect::<Vec<_>>();
    // Hold checks every prefix of every stop string at each token, so both are bounded.
    if stop.len() > 16 || stop.iter().any(|s| s.len() > 256) { bail!("stop takes at most 16 strings of at most 256 bytes"); }
    let think = v["chat_template_kwargs"]["enable_thinking"].as_bool().unwrap_or(false);
    Ok(ChatRequest { messages, tools, tool_calls, max_tokens, stream: v["stream"].as_bool().unwrap_or(false), think,
        preserve_thinking: v["chat_template_kwargs"]["preserve_thinking"].as_bool(),
        temperature: num("temperature", |f| f >= 0.0, "a number >= 0")?, top_k: int("top_k", 0)?.map(|n| n as usize),
        top_p: num("top_p", |f| f > 0.0 && f <= 1.0, "a number in (0, 1]")?, seed: int("seed", 0)?, stop })
}

/// What the chat page's side panel shows about the server, kept by the request loop and answered by the reader
/// threads (`GET /api/stats`), so it is current while a reply is generated or a model loads.
#[derive(Clone, Default, serde::Serialize)]
pub struct Stats {
    /// The loaded model's name, or the one loading.
    pub model: Option<String>,
    pub loading: bool,
    /// "cuda", "vulkan" or "cpu", and the GPU's name.
    pub backend: String,
    pub device: String,
    pub ctx: usize,
    #[serde(skip)]
    pub ctx_train: Option<u64>,
    /// Requests decoded at once (`--parallel`).
    pub slots: usize,
    /// Device memory in use and in total, measured after the load and after each request.
    pub vram: Option<(u64, u64)>,
    /// Host RAM cap in bytes (`total - --ram-margin`, or `--max-ram`); `None` if undetectable.
    pub ram_cap: Option<u64>,
    /// MoE expert cache hits and misses, and MTP drafts tried and accepted, since the model loaded.
    pub experts: Option<(u64, u64)>,
    pub drafts: Option<(u64, u64)>,
    /// Replies being generated, and their tokens so far.
    pub busy: usize,
    pub live_tokens: usize,
    pub requests: u64,
    pub prompt_tokens: u64,
    pub cached_tokens: u64,
    pub completion_tokens: u64,
    /// The latest requests, oldest first (at most 40).
    pub recent: std::collections::VecDeque<Last>,
}

/// One answered chat request.
#[derive(Clone, Default, serde::Serialize)]
pub struct Last {
    /// Unix time in seconds when it started.
    pub at: u64,
    pub model: String,
    /// Prompt tokens: the system part, reused from the previous request (cached, which includes the system part
    /// when it was kept) and in total; reply tokens.
    pub system_tokens: usize,
    pub cached_tokens: usize,
    pub prompt_tokens: usize,
    pub completion_tokens: usize,
    /// Prefill (up to the first token) and decode times in milliseconds.
    pub prefill_ms: f64,
    pub decode_ms: f64,
    pub finish: String,
}

impl Stats {
    pub fn record(&mut self, l: Last) {
        self.requests += 1;
        self.prompt_tokens += l.prompt_tokens as u64;
        self.cached_tokens += l.cached_tokens as u64;
        self.completion_tokens += l.completion_tokens as u64;
        if self.recent.len() == 40 { self.recent.pop_front(); }
        self.recent.push_back(l);
    }

    /// The stats in Prometheus text format, with `waiting` requests open besides the scrape.
    pub fn prometheus(&self, waiting: usize, uptime_s: u64) -> String {
        let mut s = String::new();
        let mut m = |name: &str, kind: &str, help: &str, v: u64| {
            s += &format!("# HELP strata_{name} {help}\n# TYPE strata_{name} {kind}\nstrata_{name} {v}\n");
        };
        m("up", "gauge", "1 when a model is loaded and not loading.", (self.model.is_some() && !self.loading) as u64);
        m("slots", "gauge", "Requests generated at once (--parallel).", self.slots as u64);
        m("busy", "gauge", "Replies being generated.", self.busy as u64);
        m("waiting", "gauge", "Requests being read, generated or queued.", waiting as u64);
        m("uptime_seconds", "counter", "Seconds since the server started.", uptime_s);
        m("requests_total", "counter", "Chat requests answered since start.", self.requests);
        m("prompt_tokens_total", "counter", "Prompt tokens of answered requests.", self.prompt_tokens);
        m("cached_prompt_tokens_total", "counter", "Prompt tokens reused from earlier requests.", self.cached_tokens);
        m("completion_tokens_total", "counter", "Reply tokens of answered requests.", self.completion_tokens);
        if let Some((u, t)) = self.vram {
            m("vram_used_bytes", "gauge", "Device memory in use.", u);
            m("vram_total_bytes", "gauge", "Device memory in total.", t);
        }
        if let Some(c) = self.ram_cap {
            m("ram_cap_bytes", "gauge", "Host RAM cap (total minus margin, or --max-ram).", c);
        }
        if let Some((h, x)) = self.experts {
            m("expert_hits_total", "counter", "Routed experts found on the GPU since the model loaded.", h);
            m("expert_misses_total", "counter", "Routed experts computed on the CPU since the model loaded.", x);
        }
        s
    }

    /// The stats with no model loaded (`model` while it loads), keeping the totals and recent requests since start.
    pub fn unload(&mut self, model: Option<String>) {
        let recent = std::mem::take(&mut self.recent);
        *self = Stats { loading: model.is_some(), model, requests: self.requests, prompt_tokens: self.prompt_tokens,
            cached_tokens: self.cached_tokens, completion_tokens: self.completion_tokens, recent, ..Default::default() };
    }
}

/// This machine's memory and CPU use and this process's resident memory, as JSON for the chat page. CPU use is
/// over the time since the previous call. Linux and Windows; elsewhere only the thread count.
pub fn system() -> Value {
    static PREV: std::sync::Mutex<(u64, u64)> = std::sync::Mutex::new((0, 0));
    let mut v = serde_json::json!({"threads": std::thread::available_parallelism().map_or(0, |n| n.get())});
    // (busy, total) CPU time since boot, in any unit.
    let cpu_pct = |busy: u64, total: u64| -> Value {
        let mut p = PREV.lock().unwrap();
        let (db, dt) = (busy.saturating_sub(p.0), total.saturating_sub(p.1));
        *p = (busy, total);
        if dt > 0 { (100.0 * db as f64 / dt as f64).into() } else { Value::Null }
    };
    #[cfg(target_os = "linux")]
    {
        let read = |p: &str| std::fs::read_to_string(p).unwrap_or_default();
        let kb = |s: &str, k: &str| s.lines().find_map(|l| l.strip_prefix(k)?.trim().strip_suffix("kB")?.trim().parse::<u64>().ok()).map(|n| n << 10);
        if let Some(l) = read("/proc/stat").lines().next() {
            let n: Vec<u64> = l.split_whitespace().skip(1).filter_map(|x| x.parse().ok()).collect();
            if n.len() >= 5 { let total = n.iter().take(8).sum::<u64>(); v["cpu_pct"] = cpu_pct(total - n[3] - n[4], total); }
        }
        let m = read("/proc/meminfo");
        if let (Some(t), Some(a)) = (kb(&m, "MemTotal:"), kb(&m, "MemAvailable:")) { (v["ram_total"], v["ram_used"]) = (t.into(), (t - a).into()); }
        if let Some(r) = kb(&read("/proc/self/status"), "VmRSS:") { v["rss"] = r.into(); }
        if let Some(n) = read("/proc/cpuinfo").lines().find_map(|l| l.strip_prefix("model name")?.split_once(':').map(|x| x.1.trim().to_string())) { v["cpu"] = n.into(); }
    }
    #[cfg(windows)]
    {
        #[repr(C)]
        struct MemStatus { len: u32, load: u32, total: u64, avail: u64, rest: [u64; 5] }
        #[repr(C)]
        struct ProcMem { cb: u32, faults: u32, peak: usize, ws: usize, rest: [usize; 6] }
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn GlobalMemoryStatusEx(m: *mut MemStatus) -> i32;
            fn GetSystemTimes(idle: *mut u64, kernel: *mut u64, user: *mut u64) -> i32;
            fn GetCurrentProcess() -> isize;
            fn K32GetProcessMemoryInfo(p: isize, m: *mut ProcMem, cb: u32) -> i32;
        }
        let mut m = MemStatus { len: size_of::<MemStatus>() as u32, load: 0, total: 0, avail: 0, rest: [0; 5] };
        if unsafe { GlobalMemoryStatusEx(&mut m) } != 0 { (v["ram_total"], v["ram_used"]) = (m.total.into(), (m.total - m.avail).into()); }
        let (mut i, mut k, mut u) = (0, 0, 0);
        // Kernel time includes idle time.
        if unsafe { GetSystemTimes(&mut i, &mut k, &mut u) } != 0 { v["cpu_pct"] = cpu_pct(k + u - i, k + u); }
        let mut p = ProcMem { cb: size_of::<ProcMem>() as u32, faults: 0, peak: 0, ws: 0, rest: [0; 6] };
        if unsafe { K32GetProcessMemoryInfo(GetCurrentProcess(), &mut p, size_of::<ProcMem>() as u32) } != 0 { v["rss"] = (p.ws as u64).into(); }
        if let Ok(n) = std::env::var("PROCESSOR_IDENTIFIER") { v["cpu"] = n.into(); }
    }
    #[cfg(not(any(target_os = "linux", windows)))]
    let _ = cpu_pct;
    v
}

/// An Anthropic Messages API request (`POST /v1/messages`, what Claude Code sends) as the OpenAI chat request
/// `chat_request` reads: the system blocks become a system message, `tool_use` blocks tool calls, `tool_result`
/// blocks tool messages, and `thinking: {"type": "enabled"}` turns thinking on. Images and server tools are dropped.
pub fn messages_body(body: &[u8]) -> anyhow::Result<Vec<u8>> {
    let j: Json = serde_json::from_slice(body)?;
    let s = |x: &str| Json::Str(x.into());
    let obj = |v: Vec<(&str, Json)>| Json::Obj(v.into_iter().map(|(k, v)| (k.to_string(), v)).collect());
    // A string, or the text of an array of blocks.
    let text = |c: &Json| match c {
        Json::Str(t) => t.clone(),
        Json::Arr(a) => a.iter().filter(|b| b.get("type").as_str() == Some("text")).filter_map(|b| b.get("text").as_str()).collect::<Vec<_>>().join("\n"),
        _ => String::new(),
    };
    let mut msgs = vec![];
    let sys = text(j.get("system"));
    if !sys.is_empty() { msgs.push(obj(vec![("role", s("system")), ("content", Json::Str(sys))])); }
    let Json::Arr(ms) = j.get("messages") else { bail!("missing messages") };
    for m in ms {
        let role = m.get("role").as_str().context("message without role")?;
        let blocks = match m.get("content") { Json::Str(t) => vec![obj(vec![("type", s("text")), ("text", s(t))])], Json::Arr(a) => a.clone(), _ => bail!("bad content") };
        let (mut texts, mut calls, mut reasoning) = (vec![], vec![], String::new());
        for b in &blocks {
            match (role, b.get("type").as_str().unwrap_or("")) {
                (_, "text") => texts.push(b.get("text").as_str().unwrap_or("").to_string()),
                ("assistant", "thinking") => reasoning += b.get("thinking").as_str().unwrap_or(""),
                ("assistant", "tool_use") => calls.push(obj(vec![("id", b.get("id").clone()), ("type", s("function")),
                    ("function", obj(vec![("name", b.get("name").clone()), ("arguments", b.get("input").clone())]))])),
                ("user", "tool_result") => {
                    let mut c = text(b.get("content"));
                    if matches!(b.get("is_error"), Json::Bool(true)) { c = format!("Error: {c}"); }
                    msgs.push(obj(vec![("role", s("tool")), ("tool_call_id", b.get("tool_use_id").clone()), ("content", Json::Str(c))]));
                }
                _ => {}
            }
        }
        if role == "assistant" {
            let mut a = vec![("role", s("assistant")), ("content", Json::Str(texts.join("\n")))];
            if !reasoning.is_empty() { a.push(("reasoning_content", Json::Str(reasoning))); }
            if !calls.is_empty() { a.push(("tool_calls", Json::Arr(calls))); }
            msgs.push(obj(a));
        } else if !texts.is_empty() {
            msgs.push(obj(vec![("role", s(role)), ("content", Json::Str(texts.join("\n")))]));
        }
    }
    let mut out = vec![("messages", Json::Arr(msgs))];
    if let Json::Arr(ts) = j.get("tools") {
        // Server tools (web search and the like) have a type other than "custom" and no input_schema.
        let ts = ts.iter().filter(|t| !matches!(t.get("input_schema"), Json::Null)).map(|t| obj(vec![("type", s("function")),
            ("function", obj(vec![("name", t.get("name").clone()), ("description", t.get("description").clone()), ("parameters", t.get("input_schema").clone())]))]));
        out.push(("tools", Json::Arr(ts.collect())));
    }
    match j.get("tool_choice").get("type").as_str() {
        Some("any") => out.push(("tool_choice", s("required"))),
        Some("none") => out.push(("tool_choice", s("none"))),
        Some("tool") => out.push(("tool_choice", obj(vec![("type", s("function")), ("function", obj(vec![("name", j.get("tool_choice").get("name").clone())]))]))),
        _ => {}
    }
    for (from, to) in [("max_tokens", "max_tokens"), ("temperature", "temperature"), ("top_p", "top_p"), ("top_k", "top_k"), ("stop_sequences", "stop"), ("stream", "stream")] {
        if !matches!(j.get(from), Json::Null) { out.push((to, j.get(from).clone())); }
    }
    if j.get("thinking").get("type").as_str() == Some("enabled") { out.push(("chat_template_kwargs", obj(vec![("enable_thinking", Json::Bool(true))]))); }
    Ok(obj(out).dump().into_bytes())
}
