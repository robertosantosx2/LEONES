//! Renders a model's own chat template, `tokenizer.chat_template`.

use std::io;

use minijinja::{Environment, Error, ErrorKind, Value};
use serde::Serialize;

const NAME: &str = "chat";
/// Instructions one render may run; real templates need well under 1M, so
/// only a runaway loop in a hostile file reaches this.
const FUEL: u64 = 50_000_000;
/// Largest prompt a template may write, a few times the largest request.
const MAX_OUTPUT: usize = 64 << 20;

/// A compiled chat template. Templates come from model files, so they get
/// no loader: `include`, `import` and `extends` cannot reach files.
pub struct ChatTemplate {
    env: Environment<'static>,
}

impl ChatTemplate {
    pub fn new(source: &str) -> Result<Self, Error> {
        let mut env = Environment::new();
        // The settings Hugging Face renders chat templates with.
        env.set_trim_blocks(true);
        env.set_lstrip_blocks(true);
        env.set_fuel(Some(FUEL));
        env.set_unknown_method_callback(minijinja_contrib::pycompat::unknown_method_callback);
        env.add_function("raise_exception", |msg: String| -> Result<Value, Error> {
            Err(Error::new(ErrorKind::InvalidOperation, msg))
        });
        env.add_template_owned(NAME, without_generation_tags(source))?;
        Ok(ChatTemplate { env })
    }

    /// Renders the prompt for `context`, which carries `messages`,
    /// `add_generation_prompt` and any template options.
    pub fn render(&self, context: impl Serialize) -> Result<String, Error> {
        let mut out = Capped(Vec::new());
        let rendered = self
            .env
            .get_template(NAME)?
            .render_captured_to(context, &mut out);
        if out.0.len() > MAX_OUTPUT {
            return Err(Error::new(
                ErrorKind::InvalidOperation,
                "the chat template writes more than 64 MiB",
            ));
        }
        rendered?;
        String::from_utf8(out.0)
            .map_err(|_| Error::new(ErrorKind::InvalidOperation, "the output is not UTF-8"))
    }
}

/// A buffer that refuses to grow past [`MAX_OUTPUT`], which stops a
/// template that prints a lazily repeated list before it fills memory.
struct Capped(Vec<u8>);

impl io::Write for Capped {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.0.len() > MAX_OUTPUT {
            return Err(io::ErrorKind::OutOfMemory.into());
        }
        self.0.extend_from_slice(buf);
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

/// Turns `{% generation %}` and `{% endgeneration %}`, which mark assistant
/// text for training and do not change the output, into a plain block,
/// keeping their whitespace control.
fn without_generation_tags(source: &str) -> String {
    let mut out = String::with_capacity(source.len());
    let mut rest = source;
    while let Some(start) = rest.find("{%") {
        // search past the opening "{%", or "{%}" ends the tag inside itself
        let Some(len) = rest[start + 2..].find("%}").map(|i| i + 2) else {
            break;
        };
        let tag = &rest[start..start + len + 2];
        let word = tag[2..len].trim_matches(|c: char| c == '-' || c == '+' || c.is_whitespace());
        out.push_str(&rest[..start]);
        match word {
            "generation" => out.push_str(&tag.replacen(word, "if true", 1)),
            "endgeneration" => out.push_str(&tag.replacen(word, "endif", 1)),
            _ => out.push_str(tag),
        }
        rest = &rest[start + len + 2..];
    }
    out.push_str(rest);
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn generation_tags_become_a_plain_block() {
        assert_eq!(
            without_generation_tags("a{%- generation -%} b {% endgeneration %}c"),
            "a{%- if true -%} b {% endif %}c"
        );
        assert_eq!(without_generation_tags("{%}"), "{%}");
    }

    #[test]
    fn renders_with_python_methods_and_trimmed_blocks() {
        let t = ChatTemplate::new(
            "{%- for m in messages %}\n{{ m.role }}: {{ m.content.strip() }}\n{% endfor %}\n{%- if add_generation_prompt %}>{% endif %}",
        )
        .unwrap();
        let out = t
            .render(json!({
                "messages": [{"role": "user", "content": " hi "}],
                "add_generation_prompt": true,
            }))
            .unwrap();
        assert_eq!(out, "user: hi\n>");
    }

    #[test]
    fn raise_exception_fails_the_render() {
        let t = ChatTemplate::new("{{ raise_exception('no system role') }}").unwrap();
        let err = t.render(json!({})).unwrap_err();
        assert!(err.to_string().contains("no system role"));
    }

    #[test]
    fn templates_cannot_include_files() {
        let t = ChatTemplate::new("{% include 'Cargo.toml' %}").unwrap();
        assert!(t.render(json!({})).is_err());
    }

    /// xorshift64, so every run draws the same cases and a failure reproduces.
    struct Rng(u64);

    impl Rng {
        fn next(&mut self) -> u64 {
            self.0 ^= self.0 << 13;
            self.0 ^= self.0 >> 7;
            self.0 ^= self.0 << 17;
            self.0
        }

        fn below(&mut self, n: usize) -> usize {
            (self.next() % n.max(1) as u64) as usize
        }
    }

    const CHATML: &str = "{%- if tools %}{{ tools | tojson }}{% endif %}\
        {%- for m in messages %}<|im_start|>{{ m.role }}\n\
        {%- if m.content is string %}{{ m.content.strip() }}\
        {%- else %}{% for p in m.content %}{{ p.text }}{% endfor %}{% endif %}\
        {%- for c in m.tool_calls or [] %}{{ c.function.name }}{{ c.function.arguments | tojson }}{% endfor %}\
        <|im_end|>\n{% endfor %}{%- if add_generation_prompt %}<|im_start|>assistant\n{% endif %}";

    const PIECES: &[&str] = &[
        "{{",
        "}}",
        "{%",
        "%}",
        "{%-",
        "-%}",
        "{#",
        "#}",
        "for",
        "endfor",
        "if",
        "endif",
        "in",
        "messages",
        "m",
        ".",
        "|",
        "(",
        ")",
        "[",
        "]",
        "'",
        "\"",
        "~",
        "*",
        "**",
        "+",
        "0",
        "-1",
        "9999",
        "loop.index",
        "namespace(",
        "set",
        "macro",
        "endmacro",
        "raise_exception(",
        "generation",
        "endgeneration",
        " ",
        "\n",
        "é",
        "🦀",
    ];

    fn random_message(rng: &mut Rng) -> serde_json::Value {
        let content = match rng.below(5) {
            0 => json!("Zażółć 🦀 <|im_end|> {{ x }}"),
            1 => json!([{"type": "text", "text": "hi"}, {"type": "image_url"}]),
            2 => json!(null),
            3 => json!(42),
            _ => json!({"nested": [1, 2]}),
        };
        let role = ["user", "assistant", "system", "tool", "", "🦀"][rng.below(6)];
        let mut m = json!({ "role": role, "content": content });
        if rng.below(3) == 0 {
            m["tool_calls"] = json!([{"function": {"name": "f", "arguments": {"a": [null]}}}]);
        }
        m
    }

    #[test]
    fn mutated_templates_and_messages_never_panic() {
        let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
        for _ in 0..3000 {
            let mut source = CHATML.to_owned();
            for _ in 0..rng.below(4) {
                let at = rng.below(source.len() + 1);
                if source.is_char_boundary(at) {
                    source.insert_str(at, PIECES[rng.below(PIECES.len())]);
                }
            }
            let Ok(t) = ChatTemplate::new(&source) else {
                continue;
            };
            let messages: Vec<_> = (0..rng.below(4))
                .map(|_| random_message(&mut rng))
                .collect();
            let start = std::time::Instant::now();
            let _ = t.render(json!({
                "messages": messages,
                "tools": if rng.below(2) == 0 { json!([{"type": "function"}]) } else { json!(null) },
                "add_generation_prompt": rng.below(2) == 0,
            }));
            assert!(start.elapsed().as_secs() < 2, "{source}");
        }
    }

    #[test]
    fn hostile_templates_fail_instead_of_exhausting_memory() {
        for source in [
            "{{ 'a' * 100000000000 }}",
            "{% for i in range(1000000000000) %}x{% endfor %}",
            "{% macro f(n) %}{{ f(n + 1) }}{% endmacro %}{{ f(0) }}",
            "{% for i in range(100000) %}{% for j in range(100000) %}{% endfor %}{% endfor %}",
            "{% for i in range(100000) %}{{ 'a' * 100000000 }}{% endfor %}",
        ] {
            let (tx, rx) = std::sync::mpsc::channel();
            std::thread::spawn(move || {
                let t = ChatTemplate::new(source).unwrap();
                let _ = tx.send(t.render(json!({})).is_err());
            });
            let failed = rx.recv_timeout(std::time::Duration::from_secs(10));
            assert_eq!(failed, Ok(true), "{source}");
        }
    }
}
