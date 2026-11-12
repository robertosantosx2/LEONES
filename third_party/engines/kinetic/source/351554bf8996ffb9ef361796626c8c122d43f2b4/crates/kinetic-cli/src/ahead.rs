//! Zero Wait in `kinetic chat`: the conversation and the message being
//! typed run on the model while the user writes, so the answer starts as
//! soon as they press Enter.

use std::sync::{Condvar, Mutex, MutexGuard, PoisonError};

use kinetic_server::Engine;
use serde_json::{json, Map, Value};

use crate::chat::is_command;

/// The message on screen, shared by the input thread and the one running
/// it ahead.
#[derive(Default)]
pub struct Typing {
    draft: Mutex<Draft>,
    changed: Condvar,
}

#[derive(Default)]
struct Draft {
    messages: Vec<Value>,
    options: Map<String, Value>,
    /// Lines of the message already ended with `\`.
    lines: String,
    line: String,
    version: u64,
    done: bool,
}

impl Typing {
    fn lock(&self) -> MutexGuard<'_, Draft> {
        self.draft.lock().unwrap_or_else(PoisonError::into_inner)
    }

    fn update(&self, f: impl FnOnce(&mut Draft)) {
        let mut d = self.lock();
        f(&mut d);
        d.version += 1;
        self.changed.notify_one();
    }

    /// A new message after `messages`, rendered with `options`.
    pub fn turn(&self, messages: &[Value], options: &Map<String, Value>) {
        self.update(|d| {
            d.messages = messages.to_vec();
            d.options = options.clone();
            d.lines.clear();
            d.line.clear();
        });
    }

    /// The lines of the message finished so far.
    pub fn lines(&self, lines: &str) {
        self.update(|d| {
            d.lines.clear();
            d.lines.push_str(lines);
            d.line.clear();
        });
    }

    /// The line being edited; called on every key, so it only copies.
    pub fn line(&self, line: &str) {
        let mut d = self.lock();
        if d.line == line {
            return;
        }
        d.line.clear();
        d.line.push_str(line);
        d.version += 1;
        self.changed.notify_one();
    }

    /// Ends [`Typing::run`].
    pub fn finish(&self) {
        self.update(|d| d.done = true);
    }

    /// Runs each new draft ahead on `engine` until [`Typing::finish`].
    pub fn run(&self, engine: &Engine) {
        let mut seen = 0;
        loop {
            let (messages, options) = {
                let mut d = self.lock();
                while d.version == seen && !d.done {
                    d = self.changed.wait(d).unwrap_or_else(PoisonError::into_inner);
                }
                if d.done {
                    return;
                }
                seen = d.version;
                let text = format!("{}{}", d.lines, d.line);
                if is_command(&text) {
                    continue;
                }
                // image prompts are run whole when sent, never ahead
                if d.messages.iter().any(|m| m["content"].is_array()) {
                    continue;
                }
                let mut messages = d.messages.clone();
                messages.push(json!({"role": "user", "content": text}));
                (messages, d.options.clone())
            };
            if let Ok(prompt) = engine.draft_prompt(&messages, &options) {
                engine.prefill(&prompt);
            }
        }
    }
}
