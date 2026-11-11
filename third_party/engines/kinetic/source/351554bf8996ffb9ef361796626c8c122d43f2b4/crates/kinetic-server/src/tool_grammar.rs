//! Grammars that hold a reply to tool calls, for `tool_choice` set to
//! `required` or to one function, in the call format of the chat template.

use kinetic_grammar::{json_schema_to_gbnf, Grammar};
use serde_json::{json, Value};

/// How a chat template has the model write its calls.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Format {
    /// `<tool_call>\n<function=f>\n<parameter=k>\nv\n</parameter>\n</function>\n</tool_call>`
    Xml,
    /// `<tool_call>\n{"name": ..., "arguments": ...}\n</tool_call>`
    Hermes,
    /// `<|tool_call_start|>[{...}]<|tool_call_end|>`
    Lfm2,
    /// `[TOOL_CALLS][{...}]`
    Mistral,
    /// `{"name": ..., "parameters": ...}`
    Llama,
    /// `{"name": ..., "arguments": ...}`
    Json,
}

impl Format {
    fn of(template: &str) -> Format {
        if template.contains("<function=") {
            Format::Xml
        } else if template.contains("<|tool_call_start|>") {
            Format::Lfm2
        } else if template.contains("[TOOL_CALLS]") {
            Format::Mistral
        } else if template.contains("<tool_call>") {
            Format::Hermes
        } else if template.contains("<|python_tag|>") || template.contains("<|eot_id|>") {
            Format::Llama
        } else {
            Format::Json
        }
    }
}

/// How the reply may go besides its calls.
#[derive(Clone, Copy, Debug, Default)]
pub struct Shape {
    /// The prompt left a `<think>` block open, which the reply closes
    /// before its calls.
    pub thinking: bool,
    /// More than one call, as `parallel_tool_calls` allows.
    pub parallel: bool,
}

const THINK: &str = r#"think ::= ([^<] | "<" [^/] | "</" [^t])* "</think>" [ \n]*"#;

/// A grammar for calls of `tools`, as the chat template `template` writes
/// them. A template that knows `<think>` may also open and close a whole
/// reasoning block before them.
pub fn grammar(template: &str, tools: &[Value], shape: Shape) -> Result<Grammar, String> {
    let format = Format::of(template);
    let (calls, rules) = match format {
        Format::Xml => xml(tools, shape.parallel),
        _ => json_calls(format, tools, shape.parallel)?,
    };
    let lead = if shape.thinking {
        "think "
    } else if template.contains("<think>") {
        r#"("<think>" think)? "#
    } else {
        ""
    };
    let gbnf = format!("root ::= {lead}{calls}\n{rules}{THINK}\n");
    Grammar::parse(&gbnf).map_err(|e| format!("tool grammar: {e}"))
}

/// `one`, or with `parallel` one or more of it separated by `sep`.
fn repeated(one: &str, sep: &str, parallel: bool) -> String {
    match parallel {
        true => format!("{one} ({sep} {one})*"),
        false => one.to_owned(),
    }
}

fn function(tool: &Value) -> &Value {
    tool.get("function").unwrap_or(tool)
}

fn literal(text: &str) -> String {
    serde_json::to_string(text).expect("a string serializes")
}

/// Calls whose structure is held, parameter values free text up to the
/// next closing tag.
fn xml(tools: &[Value], parallel: bool) -> (String, String) {
    let mut calls = Vec::new();
    for tool in tools {
        let f = function(tool);
        let name = f["name"].as_str().unwrap_or_default();
        let required: Vec<&str> = f
            .pointer("/parameters/required")
            .and_then(Value::as_array)
            .map(|r| r.iter().filter_map(Value::as_str).collect())
            .unwrap_or_default();
        let mut params = String::new();
        if let Some(props) = f
            .pointer("/parameters/properties")
            .and_then(Value::as_object)
        {
            for key in props.keys() {
                let param = format!(
                    "{} xvalue \"\n</parameter>\n\"",
                    literal(&format!("<parameter={key}>\n"))
                );
                match required.contains(&key.as_str()) {
                    true => params += &format!(" {param}"),
                    false => params += &format!(" ({param})?"),
                }
            }
        }
        calls.push(format!(
            "{}{params} \"</function>\n</tool_call>\"",
            literal(&format!("<tool_call>\n<function={name}>\n"))
        ));
    }
    let rules = format!(
        "xcall ::= {}\nxvalue ::= ([^<] | \"<\" [^/])*\n",
        calls.join(" | ")
    );
    (repeated("xcall", r#""\n""#, parallel), rules)
}

/// Calls as JSON objects whose names and arguments follow the tools'
/// schemas, in the markers `format` puts around them.
fn json_calls(format: Format, tools: &[Value], parallel: bool) -> Result<(String, String), String> {
    let key = match format {
        Format::Llama => "parameters",
        _ => "arguments",
    };
    let one: Vec<Value> = tools
        .iter()
        .map(|tool| {
            let f = function(tool);
            let params = f
                .get("parameters")
                .cloned()
                .unwrap_or_else(|| json!({"type": "object"}));
            json!({
                "type": "object",
                "properties": {"name": {"const": f["name"]}, key: params},
                "required": ["name", key],
            })
        })
        .collect();
    let schema = json!({"anyOf": one});
    let call = json_schema_to_gbnf(&schema).map_err(|e| format!("tool schema: {e}"))?;
    let call = call.replacen("root ::= ", "call ::= ", 1);
    let list = |open: &str, close: &str| {
        format!(
            "{open} {} {close}",
            repeated("call", r#""," " "?"#, parallel)
        )
    };
    let calls = match format {
        Format::Hermes => {
            let one = r#"("<tool_call>\n" call "\n</tool_call>")"#;
            repeated(one, r#""\n""#, parallel)
        }
        Format::Lfm2 => list(r#""<|tool_call_start|>[""#, r#""]<|tool_call_end|>""#),
        Format::Mistral => list(r#""[TOOL_CALLS][""#, r#""]""#),
        _ => "call".to_owned(),
    };
    Ok((calls, call))
}

#[cfg(test)]
mod tests {
    use super::*;

    const PARALLEL: Shape = Shape {
        thinking: false,
        parallel: true,
    };

    fn tools() -> Vec<Value> {
        let weather = json!({"type": "function", "function": {
            "name": "get_weather",
            "parameters": {"type": "object",
                "properties": {"city": {"type": "string"}, "days": {"type": "integer"}},
                "required": ["city"]}}});
        let time = json!({"type": "function", "function": {"name": "get_time"}});
        vec![weather, time]
    }

    #[test]
    fn xml_calls_follow_the_tools() {
        let g = grammar("{{ '<function=' }}", &tools(), PARALLEL).unwrap();
        let call = "<tool_call>\n<function=get_weather>\n<parameter=city>\nParis\n</parameter>\n</function>\n</tool_call>";
        assert!(g.matches(call));
        assert!(g.matches(&format!("{call}\n{call}")));
        assert!(g.matches("<tool_call>\n<function=get_time>\n</function>\n</tool_call>"));
        assert!(!g.matches("Sure, let me check."));
        assert!(!g.matches("<tool_call>\n<function=get_weather>\n</function>\n</tool_call>"));
        assert!(!g.matches("<tool_call>\n<function=other>\n</function>\n</tool_call>"));
    }

    #[test]
    fn json_calls_follow_the_schemas() {
        let g = grammar("<tool_call>", &tools(), PARALLEL).unwrap();
        assert!(g.matches(
            "<tool_call>\n{\"name\": \"get_weather\", \"arguments\": {\"city\": \"Paris\", \"days\": 2}}\n</tool_call>"
        ));
        assert!(!g.matches(
            "<tool_call>\n{\"name\": \"get_weather\", \"arguments\": {\"days\": 2}}\n</tool_call>"
        ));
        assert!(!g.matches("{\"name\": \"get_weather\", \"arguments\": {\"city\": \"Paris\"}}"));

        let g = grammar("<|tool_call_start|>", &tools(), PARALLEL).unwrap();
        assert!(g.matches(
            "<|tool_call_start|>[{\"name\": \"get_time\", \"arguments\": {}}]<|tool_call_end|>"
        ));
        let g = grammar("<|eot_id|>", &tools()[..1], Shape::default()).unwrap();
        assert!(g.matches("{\"name\": \"get_weather\", \"parameters\": {\"city\": \"Oslo\"}}"));
        let g = grammar("[TOOL_CALLS]", &tools(), PARALLEL).unwrap();
        assert!(g.matches("[TOOL_CALLS][{\"name\": \"get_time\", \"arguments\": {}}]"));
    }

    #[test]
    fn open_reasoning_closes_first() {
        let open = Shape {
            thinking: true,
            parallel: false,
        };
        let g = grammar("<tool_call>", &tools()[1..], open).unwrap();
        let call = "<tool_call>\n{\"name\": \"get_time\", \"arguments\": {}}\n</tool_call>";
        assert!(g.matches(&format!("The user wants the time.</think>\n\n{call}")));
        assert!(!g.matches(call));
    }

    #[test]
    fn one_call_unless_parallel() {
        let call = "<tool_call>
{\"name\": \"get_time\", \"arguments\": {}}
</tool_call>";
        let two = format!(
            "{call}
{call}"
        );
        let template = "<tool_call> <think>";
        let one = grammar(template, &tools(), Shape::default()).unwrap();
        assert!(one.matches(call) && !one.matches(&two));
        assert!(one.matches(&format!(
            "<think>
hm</think>

{call}"
        )));
        assert!(grammar(template, &tools(), PARALLEL).unwrap().matches(&two));
    }
}
