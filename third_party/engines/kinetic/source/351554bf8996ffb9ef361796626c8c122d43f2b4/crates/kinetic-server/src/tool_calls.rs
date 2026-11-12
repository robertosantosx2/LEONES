//! Function calling: the tool calls in a reply, in the formats of the
//! models Kinetic runs.
//!
//! - `<tool_call><function=name><parameter=key>value</parameter></function></tool_call>`
//!   (Qwen3.5, LFM3);
//! - `<tool_call>{"name": ..., "arguments": {...}}</tool_call>` (Qwen3, Hermes);
//! - `<|tool_call_start|>[name(key=value)]<|tool_call_end|>` (LFM2), or a
//!   JSON list in the same markers;
//! - `[TOOL_CALLS][{"name": ..., "arguments": {...}}]` and
//!   `[TOOL_CALLS]name[ARGS]{...}` (Mistral);
//! - `{"name": ..., "parameters": {...}}`, alone or after `<|python_tag|>`
//!   (Llama 3).

use serde_json::{Map, Value};

use crate::text::partial_suffix;

/// One function call in a reply.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ToolCall {
    pub name: String,
    /// The arguments as a JSON object, in text.
    pub arguments: String,
}

/// Text that starts the calls in one of the formats.
const OPENERS: &[&str] = &[
    "<tool_call>",
    "<|tool_call_start|>",
    "[TOOL_CALLS]",
    "<|python_tag|>",
];

/// Separates a reply's text from its tool calls as it streams. Text before
/// the first call goes out as it comes; from the first call on, everything
/// waits for the end of the reply, when it is parsed, and goes out as text
/// after all if it holds no call.
#[derive(Default)]
pub struct ToolSplitter {
    pending: String,
    /// The reply from the start of its first call.
    held: Option<String>,
    /// Whether only whitespace has arrived, so a JSON call may still start.
    at_start: bool,
}

impl ToolSplitter {
    pub fn new() -> Self {
        ToolSplitter {
            at_start: true,
            ..ToolSplitter::default()
        }
    }

    /// Adds `text` and returns what is now certain to be text.
    pub fn push(&mut self, text: &str) -> String {
        if let Some(held) = &mut self.held {
            held.push_str(text);
            return String::new();
        }
        self.pending.push_str(text);
        if self.at_start {
            let start = self.pending.trim_start();
            if start.is_empty() {
                return String::new();
            }
            self.at_start = false;
            if start.starts_with('{') {
                self.held = Some(std::mem::take(&mut self.pending));
                return String::new();
            }
        }
        if let Some(at) = OPENERS.iter().filter_map(|o| self.pending.find(o)).min() {
            self.held = Some(self.pending.split_off(at));
            return std::mem::take(&mut self.pending);
        }
        let hold = OPENERS
            .iter()
            .map(|o| partial_suffix(&self.pending, o))
            .max()
            .unwrap_or(0);
        let rest = self.pending.split_off(self.pending.len() - hold);
        std::mem::replace(&mut self.pending, rest)
    }

    /// The text still held back and the calls, once the reply has ended.
    /// `tools` are the request's tool definitions, whose parameter types
    /// tell text values from others in formats that do not quote them.
    pub fn finish(self, tools: &[Value]) -> (String, Vec<ToolCall>) {
        let Some(held) = self.held else {
            return (self.pending, Vec::new());
        };
        match parse(&held, tools) {
            Some((calls, rest)) if !calls.is_empty() => (rest, calls),
            _ => (self.pending + &held, Vec::new()),
        }
    }
}

/// The calls at the start of `text` and any text after them.
fn parse(text: &str, tools: &[Value]) -> Option<(Vec<ToolCall>, String)> {
    let text = text.trim_start();
    if text.starts_with("<tool_call>") {
        return tagged(text, "<tool_call>", "</tool_call>", |inner| {
            let inner = inner.trim();
            if inner.starts_with("<function=") {
                xml_call(inner, tools).map(|c| vec![c])
            } else {
                json_call(&serde_json::from_str(inner).ok()?).map(|c| vec![c])
            }
        });
    }
    if text.starts_with("<|tool_call_start|>") {
        return tagged(text, "<|tool_call_start|>", "<|tool_call_end|>", |inner| {
            match serde_json::from_str::<Value>(inner.trim()) {
                Ok(Value::Array(calls)) => calls.iter().map(json_call).collect(),
                Ok(call) => json_call(&call).map(|c| vec![c]),
                Err(_) => python_calls(inner),
            }
        });
    }
    if let Some(rest) = text.strip_prefix("[TOOL_CALLS]") {
        return mistral(rest).map(|calls| (calls, String::new()));
    }
    let rest = text.strip_prefix("<|python_tag|>").unwrap_or(text);
    json_calls(rest)
        .filter(|(calls, _)| !calls.is_empty())
        .or_else(|| python_calls(rest).map(|calls| (calls, String::new())))
}

/// Calls in blocks between `open` and `close`, each parsed by `inner`; the
/// last block may lack its `close` when the reply ended there.
fn tagged(
    mut text: &str,
    open: &str,
    close: &str,
    inner: impl Fn(&str) -> Option<Vec<ToolCall>>,
) -> Option<(Vec<ToolCall>, String)> {
    let mut calls = Vec::new();
    while let Some(rest) = text.trim_start().strip_prefix(open) {
        let (block, after) = rest.split_once(close).unwrap_or((rest, ""));
        calls.extend(inner(block)?);
        text = after;
    }
    Some((calls, text.trim().to_owned()))
}

/// `{"name": ..., "arguments": {...}}`, with `parameters` for `arguments`
/// as Llama writes it.
fn json_call(v: &Value) -> Option<ToolCall> {
    let name = v.get("name")?.as_str()?.to_owned();
    let arguments = match v.get("arguments").or_else(|| v.get("parameters")) {
        None | Some(Value::Null) => "{}".to_owned(),
        Some(Value::String(s)) => s.clone(),
        Some(args) => args.to_string(),
    };
    Some(ToolCall { name, arguments })
}

/// JSON calls one after another, separated by whitespace or `;`.
fn json_calls(text: &str) -> Option<(Vec<ToolCall>, String)> {
    let mut calls = Vec::new();
    let mut rest = text.trim_start();
    while rest.starts_with('{') {
        let mut values = serde_json::Deserializer::from_str(rest).into_iter::<Value>();
        let call = json_call(&values.next()?.ok()?)?;
        calls.push(call);
        rest = rest[values.byte_offset()..]
            .trim_start_matches(|c: char| c == ';' || c.is_whitespace());
    }
    Some((calls, rest.trim_end().to_owned()))
}

/// `<function=name><parameter=key>value</parameter>...</function>`. A value
/// is text when the tool's schema says so, otherwise JSON where it parses.
fn xml_call(text: &str, tools: &[Value]) -> Option<ToolCall> {
    let (name, mut rest) = text.strip_prefix("<function=")?.split_once('>')?;
    let name = name.trim();
    let mut arguments = Map::new();
    while let Some(param) = rest.trim_start().strip_prefix("<parameter=") {
        let (key, after) = param.split_once('>')?;
        let (value, after) = after.split_once("</parameter>")?;
        let value = value.strip_prefix('\n').unwrap_or(value);
        let value = value.strip_suffix('\n').unwrap_or(value);
        let key = key.trim();
        let typed = match parameter_type(tools, name, key) {
            Some("string") => Value::from(value),
            _ => serde_json::from_str(value).unwrap_or_else(|_| Value::from(value)),
        };
        arguments.insert(key.to_owned(), typed);
        rest = after;
    }
    let rest = rest.trim_start();
    (rest.is_empty() || rest.starts_with("</function>")).then(|| ToolCall {
        name: name.to_owned(),
        arguments: Value::Object(arguments).to_string(),
    })
}

/// The JSON schema type of parameter `key` of tool `name`, if it has one.
fn parameter_type<'t>(tools: &'t [Value], name: &str, key: &str) -> Option<&'t str> {
    tools
        .iter()
        .map(|t| t.get("function").unwrap_or(t))
        .find(|f| f.get("name").and_then(Value::as_str) == Some(name))?
        .get("parameters")?
        .get("properties")?
        .get(key)?
        .get("type")?
        .as_str()
}

/// `[{"name": ..., "arguments": ...}]`, or `name[ARGS]{...}` once per call,
/// each after its own `[TOOL_CALLS]`, with an optional `[CALL_ID]id`.
fn mistral(text: &str) -> Option<Vec<ToolCall>> {
    let text = text.trim();
    if text.starts_with('[') {
        let mut values = serde_json::Deserializer::from_str(text).into_iter::<Value>();
        return match values.next()?.ok()? {
            Value::Array(calls) => calls.iter().map(json_call).collect(),
            _ => None,
        };
    }
    text.split("[TOOL_CALLS]")
        .map(|call| {
            let (name, args) = call.split_once("[ARGS]")?;
            let name = name.split_once("[CALL_ID]").map_or(name, |(n, _)| n).trim();
            let mut values = serde_json::Deserializer::from_str(args.trim()).into_iter::<Value>();
            let args = values.next()?.ok()?;
            Some(ToolCall {
                name: name.to_owned(),
                arguments: args.to_string(),
            })
        })
        .collect()
}

/// Python calls with keyword arguments, `[f(a=1, b="x"), g()]`, the
/// brackets optional; `tool.call(...)` names the tool `tool`.
fn python_calls(text: &str) -> Option<Vec<ToolCall>> {
    let mut p = Python(text.trim());
    let bracketed = p.eat('[');
    let mut calls = Vec::new();
    loop {
        let name = p.ident()?;
        let name = name.strip_suffix(".call").unwrap_or(name).to_owned();
        p.expect('(')?;
        let mut arguments = Map::new();
        while !p.eat(')') {
            let key = p.ident()?.to_owned();
            p.expect('=')?;
            arguments.insert(key, p.value()?);
            if !p.eat(',') {
                p.expect(')')?;
                break;
            }
        }
        calls.push(ToolCall {
            name,
            arguments: Value::Object(arguments).to_string(),
        });
        if !p.eat(',') {
            break;
        }
    }
    if bracketed {
        p.expect(']')?;
    }
    p.0.trim().is_empty().then_some(calls)
}

/// A cursor over Python literals.
struct Python<'s>(&'s str);

impl<'s> Python<'s> {
    fn skip_space(&mut self) {
        self.0 = self.0.trim_start();
    }

    fn eat(&mut self, c: char) -> bool {
        self.skip_space();
        match self.0.strip_prefix(c) {
            Some(rest) => {
                self.0 = rest;
                true
            }
            None => false,
        }
    }

    fn expect(&mut self, c: char) -> Option<()> {
        self.eat(c).then_some(())
    }

    fn ident(&mut self) -> Option<&'s str> {
        self.skip_space();
        let end = self
            .0
            .find(|c: char| !(c.is_alphanumeric() || c == '_' || c == '.' || c == '-'))
            .unwrap_or(self.0.len());
        let (ident, rest) = self.0.split_at(end);
        self.0 = rest;
        (!ident.is_empty()).then_some(ident)
    }

    fn value(&mut self) -> Option<Value> {
        self.skip_space();
        let first = self.0.chars().next()?;
        match first {
            '"' | '\'' => self.string(first).map(Value::from),
            '[' | '(' => {
                let close = if first == '[' { ']' } else { ')' };
                self.0 = &self.0[1..];
                let mut items = Vec::new();
                while !self.eat(close) {
                    items.push(self.value()?);
                    if !self.eat(',') {
                        self.expect(close)?;
                        break;
                    }
                }
                Some(Value::Array(items))
            }
            '{' => {
                self.0 = &self.0[1..];
                let mut map = Map::new();
                while !self.eat('}') {
                    let key = match self.value()? {
                        Value::String(s) => s,
                        other => other.to_string(),
                    };
                    self.expect(':')?;
                    map.insert(key, self.value()?);
                    if !self.eat(',') {
                        self.expect('}')?;
                        break;
                    }
                }
                Some(Value::Object(map))
            }
            _ => {
                let end = self
                    .0
                    .find(|c: char| matches!(c, ',' | ')' | ']' | '}' | ':') || c.is_whitespace())
                    .unwrap_or(self.0.len());
                let (word, rest) = self.0.split_at(end);
                self.0 = rest;
                match word {
                    "True" | "true" => Some(Value::Bool(true)),
                    "False" | "false" => Some(Value::Bool(false)),
                    "None" | "null" => Some(Value::Null),
                    number => serde_json::from_str::<serde_json::Number>(number)
                        .ok()
                        .map(Value::Number),
                }
            }
        }
    }

    /// A quoted string with backslash escapes.
    fn string(&mut self, quote: char) -> Option<String> {
        let mut out = String::new();
        let mut chars = self.0[1..].char_indices();
        while let Some((i, c)) = chars.next() {
            match c {
                '\\' => out.push(match chars.next()?.1 {
                    'n' => '\n',
                    't' => '\t',
                    'r' => '\r',
                    other => other,
                }),
                c if c == quote => {
                    self.0 = &self.0[1 + i + c.len_utf8()..];
                    return Some(out);
                }
                c => out.push(c),
            }
        }
        None
    }
}

/// `messages` as chat templates expect them: the arguments of earlier tool
/// calls as objects, where clients send them as JSON text, and text content
/// where clients send none.
pub fn template_messages(messages: &[Value]) -> Vec<Value> {
    let mut messages = messages.to_vec();
    // openai clients send `content: null` next to tool calls; templates
    // concatenate it and fail on null
    for m in messages.iter_mut().filter_map(Value::as_object_mut) {
        if m.get("content").is_none_or(Value::is_null) {
            m.insert("content".into(), Value::from(""));
        }
    }
    let calls = messages
        .iter_mut()
        .filter_map(|m| m.get_mut("tool_calls")?.as_array_mut())
        .flatten();
    for call in calls {
        let function = call.get_mut("function").filter(|f| f.is_object());
        let Some(args) = function.and_then(|f| f.get_mut("arguments")) else {
            continue;
        };
        if let Some(parsed) = args
            .as_str()
            .and_then(|s| serde_json::from_str::<Value>(s).ok())
            .filter(Value::is_object)
        {
            *args = parsed;
        }
    }
    messages
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn split(pieces: &[&str]) -> (String, Vec<ToolCall>) {
        let tools = [json!({"type": "function", "function": {
            "name": "get_weather",
            "parameters": {"type": "object", "properties": {
                "city": {"type": "string"},
                "days": {"type": "integer"},
                "zip": {"type": "string"},
            }},
        }})];
        let mut s = ToolSplitter::new();
        let mut text: String = pieces.iter().map(|p| s.push(p)).collect();
        let (rest, calls) = s.finish(&tools);
        text += &rest;
        (text, calls)
    }

    fn call(name: &str, arguments: Value) -> ToolCall {
        ToolCall {
            name: name.into(),
            arguments: arguments.to_string(),
        }
    }

    #[test]
    fn qwen35_and_lfm3_xml_calls() {
        let (text, calls) = split(&[
            "Let me check.\n\n<tool",
            "_call>\n<function=get_weather>\n<parameter=city>\nParis\n</parameter>\n",
            "<parameter=days>\n3\n</parameter>\n<parameter=zip>\n75001\n</parameter>\n</function>\n</tool_call>",
            "\n<tool_call>\n<function=get_weather>\n<parameter=city>\nNew\nYork\n</parameter>\n</function>\n</tool_call>",
        ]);
        assert_eq!(text, "Let me check.\n\n");
        assert_eq!(
            calls,
            [
                call(
                    "get_weather",
                    json!({"city": "Paris", "days": 3, "zip": "75001"})
                ),
                call("get_weather", json!({"city": "New\nYork"})),
            ]
        );
    }

    #[test]
    fn qwen3_json_calls() {
        let (text, calls) = split(&[
            "<tool_call>\n{\"name\": \"get_weather\", \"arguments\": {\"city\": \"Oslo\"}}\n</tool_call>",
        ]);
        assert_eq!(text, "");
        assert_eq!(calls, [call("get_weather", json!({"city": "Oslo"}))]);
    }

    #[test]
    fn lfm2_python_and_json_calls() {
        let (_, calls) = split(&[
            "<|tool_call_start|>[get_weather(city='Rome', days=2, units=None), ",
            "ping()]<|tool_call_end|>",
        ]);
        assert_eq!(
            calls,
            [
                call(
                    "get_weather",
                    json!({"city": "Rome", "days": 2, "units": null})
                ),
                call("ping", json!({})),
            ]
        );
        let (_, calls) = split(&[
            "<|tool_call_start|>[{\"name\": \"ping\", \"arguments\": {}}]<|tool_call_end|>",
        ]);
        assert_eq!(calls, [call("ping", json!({}))]);
    }

    #[test]
    fn llama_json_calls() {
        let (text, calls) = split(&[
            " {\"name\": \"get_weather\", ",
            "\"parameters\": {\"city\": \"Kyiv\"}}",
        ]);
        assert_eq!((text.as_str(), calls.len()), ("", 1));
        assert_eq!(calls[0], call("get_weather", json!({"city": "Kyiv"})));
        let (_, calls) =
            split(&["<|python_tag|>{\"name\": \"a\", \"parameters\": {}}; {\"name\": \"b\"}"]);
        assert_eq!(calls, [call("a", json!({})), call("b", json!({}))]);
        let (_, calls) = split(&["<|python_tag|>brave_search.call(query=\"weather\")"]);
        assert_eq!(calls, [call("brave_search", json!({"query": "weather"}))]);
    }

    #[test]
    fn mistral_calls() {
        let (_, calls) = split(&["[TOOL_CALLS][{\"name\": \"a\", \"arguments\": {\"x\": 1}}]"]);
        assert_eq!(calls, [call("a", json!({"x": 1}))]);
        let (_, calls) =
            split(&["[TOOL_CALLS]a[ARGS]{\"x\": 1}[TOOL_CALLS]b[CALL_ID]abc123456[ARGS]{}"]);
        assert_eq!(calls, [call("a", json!({"x": 1})), call("b", json!({}))]);
    }

    #[test]
    fn text_without_calls_passes_through() {
        assert_eq!(
            split(&["Plain ", "answer."]),
            ("Plain answer.".into(), vec![])
        );
        assert_eq!(split(&["a <tool", "s> b"]), ("a <tools> b".into(), vec![]));
        let json = "{\"answer\": 42}";
        assert_eq!(split(&[json]), (json.into(), vec![]));
        let broken = "Hmm <tool_call>\n<function=get_weather>\n<parameter=city>\nPar";
        assert_eq!(split(&[broken]), (broken.into(), vec![]));
    }

    #[test]
    fn earlier_arguments_become_objects_for_the_template() {
        let messages = [json!({"role": "assistant", "content": null, "tool_calls": [
            {"id": "1", "type": "function", "function": {"name": "f", "arguments": "{\"a\": 1}"}},
        ]})];
        let out = template_messages(&messages);
        assert_eq!(
            out[0]["tool_calls"][0]["function"]["arguments"],
            json!({"a": 1})
        );
        assert_eq!(out[0]["content"], "");
    }

    #[test]
    fn missing_content_becomes_empty_text() {
        let messages = [
            json!({"role": "assistant", "tool_calls": []}),
            json!({"role": "user", "content": "hi"}),
        ];
        let out = template_messages(&messages);
        assert_eq!(out[0]["content"], "");
        assert_eq!(out[1]["content"], "hi");
    }
}
