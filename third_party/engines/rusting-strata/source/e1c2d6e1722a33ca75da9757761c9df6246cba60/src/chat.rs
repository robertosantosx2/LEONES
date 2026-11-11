//! Chat templates. Renders OpenAI-style messages and tools as llama.cpp's Jinja engine renders the model's
//! `tokenizer.chat_template`, and parses tool calls out of a reply. Two template families are covered, picked by
//! markers in the template text: Qwen3.6 (`<function=..>` XML calls) and Qwen3 2507 / Qwen3-Next (JSON calls).
//! `tests/serve.rs` checks the output byte for byte against llama-server's `/apply-template`.

use anyhow::{Context, bail};
use serde::de::{Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};

/// A JSON value that keeps object key order. serde_json's `Map` sorts keys without its `preserve_order` feature,
/// and templates print tools and arguments in the client's order.
#[derive(Clone, Debug, PartialEq)]
pub enum Json { Null, Bool(bool), Num(serde_json::Number), Str(String), Arr(Vec<Json>), Obj(Vec<(String, Json)>) }

static NULL: Json = Json::Null;

impl Json {
    /// Field `k` of an object; null when missing or not an object.
    pub fn get(&self, k: &str) -> &Json {
        match self { Json::Obj(o) => o.iter().find(|(x, _)| x == k).map_or(&NULL, |x| &x.1), _ => &NULL }
    }
    pub fn as_str(&self) -> Option<&str> { if let Json::Str(s) = self { Some(s) } else { None } }
    /// Jinja's `tojson` as llama.cpp prints it: `", "` and `": "` separators, non-ASCII kept, floats as C `%g`.
    pub fn dump(&self) -> String {
        let mut s = String::new();
        self.dump_to(&mut s);
        s
    }
    fn dump_to(&self, s: &mut String) {
        let key = |k: &str| serde_json::to_string(k).unwrap();
        match self {
            Json::Null => s.push_str("null"),
            Json::Bool(b) => s.push_str(if *b { "true" } else { "false" }),
            Json::Num(n) => s.push_str(&num(n)),
            Json::Str(x) => s.push_str(&key(x)),
            Json::Arr(a) => {
                s.push('[');
                for (i, v) in a.iter().enumerate() {
                    if i > 0 { s.push_str(", "); }
                    v.dump_to(s);
                }
                s.push(']');
            }
            Json::Obj(o) => {
                s.push('{');
                for (i, (k, v)) in o.iter().enumerate() {
                    if i > 0 { s.push_str(", "); }
                    s.push_str(&key(k));
                    s.push_str(": ");
                    v.dump_to(s);
                }
                s.push('}');
            }
        }
    }
    /// A tool-call parameter value as the Qwen3.6 template prints it: lists and objects as JSON, other values
    /// through Jinja's `string` filter (Python spelling for booleans and null).
    fn param(&self) -> String {
        match self {
            Json::Str(s) => s.clone(),
            Json::Bool(b) => (if *b { "True" } else { "False" }).into(),
            Json::Null => "None".into(),
            Json::Num(n) => num(n),
            _ => self.dump(),
        }
    }
}

/// Number text: integers exact, floats like C's `%g` (6 significant digits), which is what llama.cpp prints.
fn num(n: &serde_json::Number) -> String {
    let Some(f) = n.as_f64().filter(|_| n.is_f64()) else { return n.to_string() };
    if f == 0.0 { return (if f.is_sign_negative() { "-0" } else { "0" }).into(); }
    let strip = |s: &str| if s.contains('.') { s.trim_end_matches('0').trim_end_matches('.').to_string() } else { s.to_string() };
    let e = format!("{f:.5e}");
    let (m, x) = e.split_once('e').unwrap();
    let x: i32 = x.parse().unwrap();
    if (-4..6).contains(&x) { strip(&format!("{f:.*}", (5 - x) as usize)) }
    else { format!("{}e{}{:02}", strip(m), if x < 0 { '-' } else { '+' }, x.abs()) }
}

impl<'de> Deserialize<'de> for Json {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Json, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Json;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { f.write_str("JSON") }
            fn visit_unit<E>(self) -> Result<Json, E> { Ok(Json::Null) }
            fn visit_bool<E>(self, b: bool) -> Result<Json, E> { Ok(Json::Bool(b)) }
            fn visit_i64<E>(self, n: i64) -> Result<Json, E> { Ok(Json::Num(n.into())) }
            fn visit_u64<E>(self, n: u64) -> Result<Json, E> { Ok(Json::Num(n.into())) }
            fn visit_f64<E: serde::de::Error>(self, f: f64) -> Result<Json, E> {
                serde_json::Number::from_f64(f).map(Json::Num).ok_or_else(|| E::custom("bad number"))
            }
            fn visit_str<E>(self, s: &str) -> Result<Json, E> { Ok(Json::Str(s.into())) }
            fn visit_string<E>(self, s: String) -> Result<Json, E> { Ok(Json::Str(s)) }
            fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> Result<Json, A::Error> {
                let mut v = Vec::new();
                while let Some(x) = a.next_element()? { v.push(x); }
                Ok(Json::Arr(v))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> Result<Json, A::Error> {
                let mut v: Vec<(String, Json)> = Vec::new();
                // Key positions, so a body with many keys parses in linear time.
                let mut at = std::collections::HashMap::<String, usize>::new();
                while let Some((k, x)) = a.next_entry::<String, Json>()? {
                    // A repeated key keeps its first place and its last value, as in nlohmann's ordered_json.
                    match at.get(&k) { Some(&i) => v[i].1 = x, None => { at.insert(k.clone(), v.len()); v.push((k, x)) } }
                }
                Ok(Json::Obj(v))
            }
        }
        d.deserialize_any(V)
    }
}

/// One chat message. `content` is already text (content parts joined with newlines, as llama.cpp does).
#[derive(Clone, Debug, PartialEq)]
pub struct Msg { pub role: String, pub content: String, pub reasoning: Option<String>, pub calls: Vec<Call> }

/// A tool call in an assistant message; `args` is the parsed arguments object.
#[derive(Clone, Debug, PartialEq)]
pub struct Call { pub name: String, pub args: Json }

impl Msg {
    pub fn new(role: &str, content: &str) -> Msg { Msg { role: role.into(), content: content.into(), reasoning: None, calls: vec![] } }

    /// Parses one OpenAI message. Roles are limited to the ones the templates know, because the role goes into the
    /// prompt verbatim.
    pub fn from_json(m: &Json) -> anyhow::Result<Msg> {
        let role = m.get("role").as_str().context("message without role")?;
        if !["system", "user", "assistant", "tool"].contains(&role) { bail!("unknown role {role:?}"); }
        let content = match m.get("content") {
            Json::Str(s) => s.clone(),
            Json::Arr(parts) => parts.iter().filter_map(|p| p.get("text").as_str()).collect::<Vec<_>>().join("\n"),
            Json::Null if role == "assistant" => String::new(),
            Json::Null => bail!("{role} message without content"),
            _ => bail!("bad content"),
        };
        let calls = match m.get("tool_calls") {
            Json::Null => vec![],
            Json::Arr(a) if role == "assistant" => a.iter().map(|c| {
                let f = c.get("function");
                let name = f.get("name").as_str().context("tool call without function name")?.to_string();
                // llama.cpp parses string arguments, so both families print them as JSON.
                let args = match f.get("arguments") {
                    Json::Str(s) => serde_json::from_str(s).context("tool call arguments are not valid JSON")?,
                    Json::Null => bail!("tool call without arguments"),
                    a => a.clone(),
                };
                Ok(Call { name, args })
            }).collect::<anyhow::Result<_>>()?,
            _ => bail!("tool_calls must be an array on an assistant message"),
        };
        Ok(Msg { role: role.into(), content, reasoning: m.get("reasoning_content").as_str().map(Into::into), calls })
    }
}

/// A tool as llama.cpp hands it to the template: the type, then the function's name, description and parameters,
/// nothing else.
pub fn tool_def(t: &Json) -> anyhow::Result<Json> {
    if !matches!(t.get("type"), Json::Null) && t.get("type").as_str() != Some("function") { bail!("tool type must be \"function\""); }
    let f = t.get("function");
    let name = f.get("name").as_str().context("tool without function name")?;
    let or = |v: &Json, d: Json| if matches!(v, Json::Null) { d } else { v.clone() };
    Ok(Json::Obj(vec![("type".into(), Json::Str("function".into())), ("function".into(), Json::Obj(vec![
        ("name".into(), Json::Str(name.into())),
        ("description".into(), or(f.get("description"), Json::Str(String::new()))),
        ("parameters".into(), or(f.get("parameters"), Json::Obj(vec![]))),
    ]))]))
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Template {
    /// Qwen3.6: `<function=name><parameter=key>` calls, contents trimmed, an empty think block when thinking is off.
    Xml,
    /// Qwen3 2507 and Qwen3-Next: `{"name": .., "arguments": ..}` calls. `reasoning` (2507) puts the turns after the
    /// last user query in a think block.
    Json { reasoning: bool },
    /// DeepSeek-V4.1: `<｜User｜>`/`<｜Assistant｜>` turns, think mode with a reasoning-effort line. Plain chat only;
    // ponytail: no DSML tool calls, add when serving DeepSeek tools matters.
    Ds,
}

const XML_RULES: &str = "\n\nIf you choose to call a function ONLY reply in the following format with NO suffix:\n\n<tool_call>\n<function=example_function_name>\n<parameter=example_parameter_1>\nvalue_1\n</parameter>\n<parameter=example_parameter_2>\nThis is the value for the second parameter\nthat can span\nmultiple lines\n</parameter>\n</function>\n</tool_call>\n\n<IMPORTANT>\nReminder:\n- Function calls MUST follow the specified format: an inner <function=...></function> block must be nested within <tool_call></tool_call> XML tags\n- Required parameters MUST be specified\n- You may provide optional reasoning for your function call in natural language BEFORE the function call, but NOT after\n- If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls\n</IMPORTANT>";
const JSON_HEAD: &str = "# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>";
const JSON_TAIL: &str = "\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call><|im_end|>\n";
const TAG: &str = "<tool_call>";

const DS_TOOLS_HEAD: &str = "## Tools\n\nYou have access to a set of tools to help answer the user's question. You can invoke tools by writing a \"<｜DSML｜ calls>\" block like the following:\n\n<｜DSML｜ calls>\n<｜DSML｜ invoke name=\"$TOOL_NAME\">\n<｜DSML｜ parameter name=\"$PARAMETER_NAME\" string=\"true|false\">$PARAMETER_VALUE</｜DSML｜ parameter>\n...\n</｜DSML｜ invoke>\n<｜DSML｜ invoke name=\"$TOOL_NAME2\">\n...\n</｜DSML｜ invoke>\n</｜DSML｜ calls>\n\nString parameters should be specified as is and set `string=\"true\"`. For all other types (numbers, booleans, arrays, objects), pass the value in JSON format and set `string=\"false\"`.\n\nIf thinking_mode is enabled (triggered by <think>), you MUST output your complete reasoning inside <think>...</think> BEFORE any tool calls or final response.\n\nOtherwise, output directly after </think> with tool calls or final response.\n\n### Available Tool Schemas\n\n";
const DS_TOOLS_TAIL: &str = "\n\nYou MUST strictly follow the above defined tool name and parameter schemas to invoke tool calls.\n";
const DS_CALLS: &str = "<｜DSML｜ calls>";

/// DeepSeek-V4.1 (Unsloth template): tool results merge into the user turn, the tools go after the system text
/// (a new empty system message when there is none), and tools anywhere keep the reasoning of earlier turns.
// ponytail: tool results print in message order; the template re-sorts them by tool_call_id (Msg keeps no ids).
fn render_ds(msgs: &[Msg], tools: &[Json], think: bool, preserve: bool, generate: bool) -> String {
    enum It<'a> { Sys(&'a str), User(Vec<String>, bool), Asst(&'a Msg) }
    let mut items: Vec<It> = vec![];
    if !tools.is_empty() && msgs.first().is_none_or(|m| m.role != "system") { items.push(It::Sys("")); }
    for m in msgs {
        match m.role.as_str() {
            "tool" => {
                let p = format!("<tool_result>{}</tool_result>", m.content);
                match items.last_mut() { Some(It::User(v, _)) => v.push(p), _ => items.push(It::User(vec![p], false)) }
            }
            "user" => match items.last_mut() {
                Some(It::User(v, real)) => { v.push(m.content.clone()); *real = true }
                _ => items.push(It::User(vec![m.content.clone()], true)),
            },
            "assistant" => items.push(It::Asst(m)),
            "system" => items.push(It::Sys(&m.content)),
            _ => {}
        }
    }
    let last_user = items.iter().rposition(|x| matches!(x, It::User(_, true)) || matches!(x, It::Sys(_))).filter(|&i| i > 0 || matches!(items[0], It::User(..))).map_or(-1, |i| i as i64);
    let keep_all = preserve || !tools.is_empty();
    let mut s = String::from("<｜begin▁of▁sentence｜>");
    for (i, it) in items.iter().enumerate() {
        if i == 0 {
            if think || matches!(it, It::Sys(_)) { s += "<｜System｜>"; }
            if think { s += "Reasoning Effort: 75 (range 1-100, the higher the value, the more thorough the reasoning)\n\n"; }
        }
        match it {
            It::Sys(c) => {
                if i > 0 { s += "<｜System｜>"; }
                s += c;
                if i == 0 && !tools.is_empty() {
                    s += "\n\n";
                    s += DS_TOOLS_HEAD;
                    s += &tools.iter().map(|t| t.get("function").dump()).collect::<Vec<_>>().join("\n");
                    s += DS_TOOLS_TAIL;
                }
            }
            It::User(v, _) => { s += "<｜User｜>"; s += &v.join("\n\n"); }
            It::Asst(m) => {
                let (r, c) = split_think(m, &m.content);
                if think && (keep_all || i as i64 > last_user) { s += r; s += "</think>"; }
                s += c;
                if !m.calls.is_empty() {
                    let inv: Vec<String> = m.calls.iter().map(|call| {
                        let params: Vec<String> = match &call.args {
                            Json::Obj(o) => o.iter().map(|(k, v)| format!("<｜DSML｜ parameter name=\"{k}\" string=\"{}\">{}</｜DSML｜ parameter>",
                                v.as_str().is_some(), v.as_str().map_or_else(|| v.dump(), String::from))).collect(),
                            _ => vec![],
                        };
                        format!("<｜DSML｜ invoke name=\"{}\">\n{}\n</｜DSML｜ invoke>", call.name, params.join("\n"))
                    }).collect();
                    s += &format!("\n\n{DS_CALLS}\n{}\n</｜DSML｜ calls>", inv.join("\n"));
                }
                s += "<｜end▁of▁sentence｜>";
            }
        }
        let last = i + 1 == items.len();
        if (last || matches!(items[i + 1], It::Asst(_))) && (matches!(it, It::User(..)) || (matches!(it, It::Sys(_)) && i > 0)) && (generate || !last) {
            s += "<｜Assistant｜>";
            s += if think && (keep_all || i as i64 >= last_user) { "<think>" } else { "</think>" };
        }
    }
    s
}

/// Index of the last user turn that is not a tool response (the templates' `last_query_index`).
fn last_query(msgs: &[Msg], trim: bool) -> usize {
    msgs.iter().rposition(|m| {
        let c = if trim { m.content.trim() } else { &m.content };
        m.role == "user" && !(c.starts_with("<tool_response>") && c.ends_with("</tool_response>"))
    }).unwrap_or(msgs.len().saturating_sub(1))
}

/// Reasoning and answer of an assistant turn: `reasoning_content` when given, else the `<think>` part of `c`.
fn split_think<'a>(m: &'a Msg, c: &'a str) -> (&'a str, &'a str) {
    if let Some(r) = &m.reasoning { return (r, c); }
    if !c.contains("</think>") { return ("", c); }
    let r = c.split("</think>").next().unwrap().trim_end_matches('\n').rsplit("<think>").next().unwrap();
    (r.trim_start_matches('\n'), c.rsplit("</think>").next().unwrap().trim_start_matches('\n'))
}

impl Template {
    /// The family of a GGUF's `tokenizer.chat_template`. Files without one get Qwen3.6's format.
    pub fn detect(src: Option<&str>) -> Template {
        match src {
            Some(s) if s.contains("｜DSML｜") => Template::Ds,
            Some(s) if !s.contains("<function=") && s.contains(TAG) => Template::Json { reasoning: s.contains("reasoning_content") },
            _ => Template::Xml,
        }
    }

    /// The prompt for `msgs` and `tools` (from `tool_def`). `generate` adds the assistant header the reply follows;
    /// `think` false closes the think block at once where the template has one. `preserve` prints the think block of
    /// every earlier reply, not only of those after the last user turn (Qwen3.6's `preserve_thinking`), so a new user
    /// turn leaves the text of the earlier ones as it was and their cached state can be reused.
    pub fn render(&self, msgs: &[Msg], tools: &[Json], think: bool, preserve: bool, generate: bool) -> String {
        let mut s = String::new();
        let tool_end = |s: &mut String, i: usize| {
            if i + 1 == msgs.len() || msgs[i + 1].role != "tool" { *s += "<|im_end|>\n"; }
        };
        match *self {
            Template::Ds => s += &render_ds(msgs, tools, think, preserve, generate),
            Template::Xml => {
                let (n_sys, sys) = match msgs {
                    [a, b, ..] if a.role == "system" && b.role == "system" => (2, format!("{}\n{}", a.content.trim(), b.content.trim())),
                    [a, ..] if a.role == "system" => (1, a.content.trim().to_string()),
                    _ => (0, String::new()),
                };
                if !tools.is_empty() {
                    s += "<|im_start|>system\n# Tools\n\nYou have access to the following functions:\n\n<tools>";
                    for t in tools { s += "\n"; s += &t.dump(); }
                    s += "\n</tools>";
                    s += XML_RULES;
                    if !sys.is_empty() { s += "\n\n"; s += &sys; }
                    s += "<|im_end|>\n";
                } else if !sys.is_empty() {
                    s += &format!("<|im_start|>system\n{sys}<|im_end|>\n");
                }
                let lq = last_query(msgs, true);
                for (i, m) in msgs.iter().enumerate().skip(n_sys) {
                    let c = m.content.trim();
                    match m.role.as_str() {
                        "user" => s += &format!("<|im_start|>user\n{c}<|im_end|>\n"),
                        "assistant" => {
                            let (r, c) = split_think(m, c);
                            if preserve || i > lq { s += &format!("<|im_start|>assistant\n<think>\n{}\n</think>\n\n{c}", r.trim()); }
                            else { s += &format!("<|im_start|>assistant\n{c}"); }
                            for (k, call) in m.calls.iter().enumerate() {
                                s += if k > 0 { "\n" } else if c.trim().is_empty() { "" } else { "\n\n" };
                                s += &format!("<tool_call>\n<function={}>\n", call.name);
                                if let Json::Obj(o) = &call.args {
                                    for (k, v) in o { s += &format!("<parameter={k}>\n{}\n</parameter>\n", v.param()); }
                                }
                                s += "</function>\n</tool_call>";
                            }
                            s += "<|im_end|>\n";
                        }
                        "tool" => {
                            if i > 0 && msgs[i - 1].role != "tool" { s += "<|im_start|>user"; }
                            s += &format!("\n<tool_response>\n{c}\n</tool_response>");
                            tool_end(&mut s, i);
                        }
                        _ => {}  // later system messages are dropped
                    }
                }
                if generate { s += if think { "<|im_start|>assistant\n<think>\n" } else { "<|im_start|>assistant\n<think>\n\n</think>\n\n" }; }
            }
            Template::Json { reasoning } => {
                let sys = msgs.first().filter(|m| m.role == "system").map(|m| m.content.as_str());
                if !tools.is_empty() {
                    s += "<|im_start|>system\n";
                    if let Some(c) = sys { s += c; s += "\n\n"; }
                    s += JSON_HEAD;
                    for t in tools { s += "\n"; s += &t.dump(); }
                    s += JSON_TAIL;
                } else if let Some(c) = sys {
                    s += &format!("<|im_start|>system\n{c}<|im_end|>\n");
                }
                let lq = last_query(msgs, false);
                for (i, m) in msgs.iter().enumerate() {
                    let c = m.content.as_str();
                    match m.role.as_str() {
                        "user" => s += &format!("<|im_start|>user\n{c}<|im_end|>\n"),
                        "system" if i > 0 => s += &format!("<|im_start|>system\n{c}<|im_end|>\n"),
                        "assistant" => {
                            let (r, c) = if reasoning { split_think(m, c) } else { ("", c) };
                            if reasoning && i > lq && (i + 1 == msgs.len() || !r.is_empty()) {
                                s += &format!("<|im_start|>assistant\n<think>\n{}\n</think>\n\n{}", r.trim_matches('\n'), c.trim_start_matches('\n'));
                            } else {
                                s += &format!("<|im_start|>assistant\n{c}");
                            }
                            for (k, call) in m.calls.iter().enumerate() {
                                if k > 0 || !c.is_empty() { s += "\n"; }
                                s += &format!("<tool_call>\n{{\"name\": \"{}\", \"arguments\": {}}}\n</tool_call>", call.name, call.args.dump());
                            }
                            s += "<|im_end|>\n";
                        }
                        "tool" => {
                            if i == 0 || msgs[i - 1].role != "tool" { s += "<|im_start|>user"; }
                            s += &format!("\n<tool_response>\n{c}\n</tool_response>");
                            tool_end(&mut s, i);
                        }
                        _ => {}
                    }
                }
                if generate { s += "<|im_start|>assistant\n"; }
            }
        }
        s
    }

    /// The text that starts a tool call in a reply.
    pub fn call_tag(&self) -> &'static str { if let Template::Ds = self { DS_CALLS } else { TAG } }

    /// Tool calls at the end of a reply: the text before them, and the name and arguments (JSON text) of each call.
    /// None when the reply has no call or a call is malformed; the reply then goes out as plain text.
    // ponytail: a literal `<tool_call>` inside the thinking part makes the reply plain text; strip the think block
    // first if thinking with tools matters.
    pub fn parse_calls(&self, text: &str, tools: &[Json]) -> Option<(String, Vec<(String, String)>)> {
        if let Template::Ds = self { return ds_calls(text); }
        let start = text.find(TAG)?;
        let mut rest = &text[start..];
        let mut calls = Vec::new();
        loop {
            rest = rest.trim_start();
            if rest.is_empty() { break; }
            let inner;
            (inner, rest) = rest.strip_prefix(TAG)?.split_once("</tool_call>")?;
            calls.push(match self { Template::Ds => unreachable!(), Template::Xml => xml_call(inner, tools)?, Template::Json { .. } => json_call(inner)? });
        }
        Some((text[..start].trim_end().to_string(), calls))
    }
}

/// DeepSeek reply: a `<｜DSML｜ calls>` block of `invoke` items with `parameter name=".." string="true|false"`. A
/// parameter is a string when the model says so, else JSON (a string if it does not parse). The reply's thinking part
/// is skipped, so a tag inside it is not taken for a call.
// ponytail: not run against the real model (the weights are deleted); the format is the template's own.
fn ds_calls(text: &str) -> Option<(String, Vec<(String, String)>)> {
    let from = text.rfind("</think>").map_or(0, |p| p + 8);
    let start = from + text[from..].find(DS_CALLS)?;
    let mut rest = text[start..].strip_prefix(DS_CALLS)?;
    let mut calls = Vec::new();
    loop {
        rest = rest.trim_start();
        if let Some(x) = rest.strip_prefix("</｜DSML｜ calls>") {
            if !x.trim().is_empty() || calls.is_empty() { return None; }
            break;
        }
        let (name, mut r) = rest.strip_prefix("<｜DSML｜ invoke name=\"")?.split_once("\">")?;
        let mut args = Vec::new();
        loop {
            r = r.trim_start();
            if let Some(x) = r.strip_prefix("</｜DSML｜ invoke>") { rest = x; break; }
            let (head, x) = r.strip_prefix("<｜DSML｜ parameter name=\"")?.split_once("\">")?;
            let (k, string) = head.split_once("\" string=\"")?;
            let (v, x) = x.split_once("</｜DSML｜ parameter>")?;
            r = x;
            args.push((k.to_string(), if string == "true" { Json::Str(v.into()) } else { serde_json::from_str(v).unwrap_or_else(|_| Json::Str(v.into())) }));
        }
        calls.push((name.to_string(), Json::Obj(args).dump()));
    }
    Some((text[..start].trim_end().to_string(), calls))
}

/// `{"name": .., "arguments": {..}}`; arguments given as a JSON string are accepted too.
fn json_call(inner: &str) -> Option<(String, String)> {
    let v: Json = serde_json::from_str(inner.trim()).ok()?;
    let args = match v.get("arguments") {
        Json::Str(s) => serde_json::from_str(s).ok()?,
        a => a.clone(),
    };
    let Json::Obj(_) = args else { return None };
    Some((v.get("name").as_str()?.to_string(), args.dump()))
}

/// `<function=name>` with `<parameter=key>\nvalue\n</parameter>` items. A value is a string when the tool's schema
/// says so, else JSON if it parses as JSON, else a string.
fn xml_call(inner: &str, tools: &[Json]) -> Option<(String, String)> {
    let (name, mut r) = inner.trim_start().strip_prefix("<function=")?.split_once('>')?;
    let props = tools.iter().map(|t| t.get("function")).find(|f| f.get("name").as_str() == Some(name))
        .map_or(&NULL, |f| f.get("parameters").get("properties"));
    let mut args = Vec::new();
    loop {
        r = r.trim_start();
        if let Some(x) = r.strip_prefix("</function>") {
            if !x.trim().is_empty() { return None; }
            break;
        }
        let (k, x) = r.strip_prefix("<parameter=")?.split_once('>')?;
        let (v, x) = x.split_once("</parameter>")?;
        r = x;
        let v = v.strip_prefix('\n').unwrap_or(v);
        let v = v.strip_suffix('\n').unwrap_or(v);
        let string = props.get(k).get("type").as_str() == Some("string");
        // The template prints earlier calls' booleans and null in Python spelling, and the model copies it.
        let py = |v: &str| match v.trim() { "True" => Some(Json::Bool(true)), "False" => Some(Json::Bool(false)), "None" => Some(Json::Null), _ => None };
        args.push((k.to_string(), if string { Json::Str(v.into()) } else { serde_json::from_str(v).ok().or_else(|| py(v)).unwrap_or_else(|| Json::Str(v.into())) }));
    }
    Some((name.to_string(), Json::Obj(args).dump()))
}

/// Streams reply text but holds back everything from a `<tool_call>` tag on (unless `no_tag`), so a call is never
/// sent as content, and ends the reply before the first of the `stops` strings.
#[derive(Default)]
pub struct Hold { pub text: String, sent: usize, held: bool, no_tag: bool, tag: &'static str, stops: Vec<String>, pub stopped: bool }

impl Hold {
    pub fn new(tag: bool, stops: Vec<String>) -> Hold { Hold { no_tag: !tag, stops, ..Hold::default() } }
    /// Holds back from `tag` instead of `<tool_call>` (the DeepSeek call block).
    pub fn tagged(mut self, tag: &'static str) -> Hold { self.tag = tag; self }
    /// Adds a piece of the reply; returns the text that is safe to send now.
    pub fn push(&mut self, piece: &str) -> &str {
        let from = self.sent;
        if self.stopped { return ""; }
        self.text += piece;
        // A stop string starts in the unsent text: a tail that could start one is never sent.
        if let Some(p) = self.stops.iter().filter_map(|s| self.text[from..].find(s.as_str())).min() {
            self.text.truncate(from + p);
            self.stopped = true;
        }
        if !self.held {
            self.sent = match self.text[from..].find(self.tag()).filter(|_| !self.no_tag) {
                Some(p) => { self.held = true; from + p }
                None if self.stopped => self.text.len(),
                None => (self.text.len() - self.tail()).max(from),
            };
        }
        &self.text[from..self.sent]
    }
    fn tag(&self) -> &'static str { if self.tag.is_empty() { TAG } else { self.tag } }
    /// The longest end of the text that could be the start of the tag or of a stop string.
    fn tail(&self) -> usize {
        (!self.no_tag).then_some(self.tag()).into_iter().chain(self.stops.iter().map(String::as_str))
            .flat_map(|s| s.char_indices().skip(1).map(move |(k, _)| &s[..k]))
            .filter(|p| self.text.ends_with(p)).map(str::len).max().unwrap_or(0)
    }
    /// The text not sent yet.
    pub fn rest(&self) -> &str { &self.text[self.sent..] }
}

#[cfg(test)]
mod ds_tests {
    use super::*;
    // Expected strings come from rendering models/deepseek-v4.1/chat_template.jinja with jinja2 (tools/deepseek_ref/render_template.py).
    #[test]
    fn deepseek_plain_chat() {
        let t = Template::Ds;
        let u = [Msg::new("user", "Hi")];
        assert_eq!(t.render(&u, &[], true, false, true), "<｜begin▁of▁sentence｜><｜System｜>Reasoning Effort: 75 (range 1-100, the higher the value, the more thorough the reasoning)\n\n<｜User｜>Hi<｜Assistant｜><think>");
        assert_eq!(t.render(&u, &[], false, false, true), "<｜begin▁of▁sentence｜><｜User｜>Hi<｜Assistant｜></think>");
        let m = [Msg::new("system", "Be brief."), Msg::new("user", "Hi"), Msg::new("assistant", "Hello."), Msg::new("user", "Bye")];
        assert_eq!(t.render(&m, &[], false, false, true), "<｜begin▁of▁sentence｜><｜System｜>Be brief.<｜User｜>Hi<｜Assistant｜></think>Hello.<｜end▁of▁sentence｜><｜User｜>Bye<｜Assistant｜></think>");
        let mut a = Msg::new("assistant", "Hello.");
        a.reasoning = Some("greet".into());
        let m = [Msg::new("system", "Be brief."), Msg::new("user", "Hi"), a, Msg::new("user", "Bye")];
        assert_eq!(t.render(&m, &[], true, false, true), "<｜begin▁of▁sentence｜><｜System｜>Reasoning Effort: 75 (range 1-100, the higher the value, the more thorough the reasoning)\n\nBe brief.<｜User｜>Hi<｜Assistant｜></think>Hello.<｜end▁of▁sentence｜><｜User｜>Bye<｜Assistant｜><think>");
        // llama-server /apply-template default (reasoning of earlier turns kept): checked against build b12116.
        let mut r = Msg::new("assistant", "Hello!");
        r.reasoning = Some("greet".into());
        let m = [Msg::new("user", "Hi"), r, Msg::new("user", "Bye")];
        assert_eq!(t.render(&m, &[], true, true, true), "<｜begin▁of▁sentence｜><｜System｜>Reasoning Effort: 75 (range 1-100, the higher the value, the more thorough the reasoning)\n\n<｜User｜>Hi<｜Assistant｜><think>greet</think>Hello!<｜end▁of▁sentence｜><｜User｜>Bye<｜Assistant｜><think>");
        let m = [Msg::new("system", "Be brief."), Msg::new("user", "Hi"), Msg::new("assistant", "Hello!"), Msg::new("user", "Bye")];
        assert_eq!(t.render(&m, &[], true, true, true), "<｜begin▁of▁sentence｜><｜System｜>Reasoning Effort: 75 (range 1-100, the higher the value, the more thorough the reasoning)\n\nBe brief.<｜User｜>Hi<｜Assistant｜><think></think>Hello!<｜end▁of▁sentence｜><｜User｜>Bye<｜Assistant｜><think>");
    }

    #[test]
    fn deepseek_tools() {
        // tools/deepseek_ref/render_tools.py renders the model's template with jinja2.
        let j: Json = serde_json::from_str(include_str!("../tools/deepseek_ref/tpl_tools.json")).unwrap();
        let Json::Arr(cases) = j else { panic!() };
        for c in &cases {
            let q = crate::serve::chat_request(c.get("req").dump().as_bytes()).unwrap();
            let think = matches!(c.get("think"), Json::Bool(true));
            assert_eq!(Template::Ds.render(&q.messages, &q.tools, think, true, true), c.get("prompt").as_str().unwrap());
        }
    }

    #[test]
    fn deepseek_parses_calls() {
        let t = "<think>a <｜DSML｜ calls> b</think>ok\n\n<｜DSML｜ calls>\n<｜DSML｜ invoke name=\"f\">\n<｜DSML｜ parameter name=\"s\" string=\"true\">12</｜DSML｜ parameter>\n<｜DSML｜ parameter name=\"n\" string=\"false\">[1, 2]</｜DSML｜ parameter>\n</｜DSML｜ invoke>\n<｜DSML｜ invoke name=\"g\">\n</｜DSML｜ invoke>\n</｜DSML｜ calls>";
        let (txt, c) = Template::Ds.parse_calls(t, &[]).unwrap();
        assert_eq!(txt, "<think>a <｜DSML｜ calls> b</think>ok");
        assert_eq!(c, vec![("f".to_string(), r#"{"s": "12", "n": [1, 2]}"#.to_string()), ("g".to_string(), "{}".to_string())]);
        assert!(Template::Ds.parse_calls("plain", &[]).is_none());
        assert!(Template::Ds.parse_calls("<｜DSML｜ calls>\n<｜DSML｜ invoke name=\"f\">", &[]).is_none());
    }
}
