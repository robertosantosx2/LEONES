//! `kinetic run`: an answer streamed to the terminal.

use std::io::{self, IsTerminal, Write};
use std::path::Path;
use std::time::Instant;

use kinetic_server::{Completion, Engine, Request};
use serde_json::{json, Map, Value};

use crate::{GenArgs, Result};

/// Answers `prompt`, and writes its receipt to `receipt` if given; the
/// status line names `device`.
pub fn answer(
    engine: &Engine,
    gen: &GenArgs,
    prompt: &str,
    device: &str,
    receipt: Option<&Path>,
) -> Result<()> {
    let mut messages = system(gen);
    messages.push(json!({"role": "user", "content": prompt}));
    let mut request = gen.request(engine.default_sampling());
    if receipt.is_some() {
        kinetic_server::receipt::seed(&mut request.sampling);
    }
    let c = stream(engine, &messages, &request, Some(device))?;
    if let Some(file) = receipt {
        crate::receipt::save(engine, messages.into(), &request, &c, Some(file))?;
        eprintln!("[receipt written to {}]", file.display());
    }
    Ok(())
}

fn system(gen: &GenArgs) -> Vec<Value> {
    gen.system
        .iter()
        .map(|s| json!({"role": "system", "content": s}))
        .collect()
}

/// Streams the answer to `messages` to stdout and a status line to stderr,
/// naming `device` if given.
pub(crate) fn stream(
    engine: &Engine,
    messages: &[Value],
    request: &Request,
    device: Option<&str>,
) -> Result<Completion> {
    let prompt = engine.chat_prompt(messages, &Map::new())?;
    let mut status = Status::new();
    let mut out = io::stdout().lock();
    let mut failed = None;
    let c = engine.complete(&prompt, request, &mut |part, tokens| {
        if let Err(e) = out
            .write_all(part.content.as_bytes())
            .and_then(|()| out.flush())
        {
            failed = Some(e);
            return false;
        }
        status.update(tokens);
        true
    })?;
    if let Some(e) = failed {
        return Err(e.into());
    }
    writeln!(out)?;
    status.finish(&c, device);
    Ok(c)
}

/// The tok/s line on stderr. It is redrawn live only when stdout goes
/// elsewhere, so it never lands in the middle of the answer.
struct Status {
    live: bool,
    first: Option<Instant>,
}

impl Status {
    fn new() -> Self {
        Status {
            live: io::stderr().is_terminal() && !io::stdout().is_terminal(),
            first: None,
        }
    }

    fn update(&mut self, tokens: usize) {
        let first = *self.first.get_or_insert_with(Instant::now);
        if !self.live || tokens < 2 {
            return;
        }
        let rate = (tokens - 1) as f64 / first.elapsed().as_secs_f64();
        eprint!("\r\x1b[2K{rate:.1} tok/s, {tokens} tokens");
    }

    fn finish(&self, c: &Completion, device: Option<&str>) {
        let t = &c.timings;
        let rate = |n: usize, s: f64| if s > 0.0 { n as f64 / s } else { 0.0 };
        let new_prompt = t.prompt_tokens - t.cached_tokens;
        if self.live {
            eprint!("\r\x1b[2K");
        }
        let on = device.map(|d| format!(" on {d}")).unwrap_or_default();
        eprintln!(
            "[{} tokens at {:.1} tok/s; prompt {} tokens at {:.1} tok/s{on}]",
            c.completion_tokens,
            rate(t.generated, t.decode.as_secs_f64()),
            new_prompt,
            rate(new_prompt, t.prefill.as_secs_f64()),
        );
    }
}
