//! A scripted coding-agent session: each turn is a fresh request holding a
//! tool result with the same file and asking for an edit, answered with a
//! JSON tool call carrying the whole file. Turns run greedily, plainly and
//! with each drafter; one decoder serves every turn, so the session index
//! remembers earlier turns. Reports tokens per pass and speed per drafter,
//! and checks every turn is identical to plain decoding.
//!
//! cargo run --release -p kinetic-models --example agent_workload -- model.gguf [cpu|gpu] [n]
//!
//! `gpu` needs `--features cuda`. Prompts use the ChatML format of Qwen
//! models.

mod common;

use kinetic_gguf::GgufFile;
use kinetic_models::speculative::{Greedy, Predictor};
use kinetic_tokenizer::Tokenizer;

use common::{decoder, plain, speculative, Run};

const FILE: &str = r#"use std::collections::HashMap;

pub fn summarize(values: &[i64]) -> (i64, i64, f64) {
    let mut count = 0;
    let mut sum = 0;
    for v in values {
        if *v >= 0 {
            count += 1;
            sum += v;
        }
    }
    let mean = if count == 0 { 0.0 } else { sum as f64 / count as f64 };
    (count, sum, mean)
}

pub fn histogram(values: &[i64], width: i64) -> HashMap<i64, usize> {
    let mut buckets = HashMap::new();
    for v in values {
        *buckets.entry(v / width).or_insert(0) += 1;
    }
    buckets
}

pub fn largest(values: &[i64]) -> Option<i64> {
    values.iter().copied().max()
}
"#;

const EDITS: [&str; 4] = [
    "Rename the variable `count` to `total` in `summarize`.",
    "Change the bucket width parameter of `histogram` to `bucket_width`.",
    "Make `largest` return 0 instead of `None` for an empty slice.",
    "Rename the parameter `values` to `samples` in every function.",
];

fn prompt(edit: &str) -> String {
    let read = json_string(FILE);
    format!(
        "<|im_start|>system\nYou are a coding agent. Answer only with one JSON tool call: \
         {{\"tool\": \"write_file\", \"path\": ..., \"content\": ...}} where content is the whole \
         new file.<|im_end|>\n<|im_start|>user\nTool result: {{\"tool\": \"read_file\", \"path\": \
         \"src/stats.rs\", \"content\": {read}}}\n\n{edit}<|im_end|>\n<|im_start|>assistant\n\
         <think>\n\n</think>\n\n"
    )
}

/// `text` as a JSON string literal.
fn json_string(text: &str) -> String {
    let mut out = String::from("\"");
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = args
        .next()
        .ok_or("usage: agent_workload <model.gguf> [cpu|gpu] [n]")?;
    let device = args.next().unwrap_or_else(|| "cpu".into());
    let n: usize = args.next().map_or(Ok(400), |s| s.parse())?;

    let file = GgufFile::open(&path)?;
    let tokenizer = Tokenizer::from_gguf(file.header())?;
    let model = kinetic_models::load(&file)?;
    let turns: Vec<Vec<u32>> = EDITS
        .iter()
        .map(|e| tokenizer.encode(&prompt(e), true))
        .collect();
    let eos = tokenizer.eos();
    let end_of_turn: Vec<u32> = tokenizer
        .encode("<|im_end|>", true)
        .into_iter()
        .filter(|&t| Some(t) != tokenizer.bos())
        .collect();
    let stop = |t: u32| Some(t) == eos || end_of_turn == [t];

    match device.as_str() {
        "cpu" => workload(&model, || model.new_state(), &turns, n, stop),
        #[cfg(feature = "cuda")]
        "gpu" => {
            let longest = turns.iter().map(Vec::len).max().unwrap_or(0);
            let gpu = kinetic_models::cuda::CudaModel::load(&model, longest + n + 16)?;
            workload(
                &gpu,
                || gpu.new_state().expect("GPU state"),
                &turns,
                n,
                stop,
            );
        }
        other => return Err(format!("unknown device {other}").into()),
    }
    Ok(())
}

fn workload<M: Predictor>(
    model: &M,
    new_state: impl Fn() -> M::State,
    turns: &[Vec<u32>],
    n: usize,
    stop: impl Fn(u32) -> bool + Copy,
) {
    let plain_runs: Vec<Run> = turns
        .iter()
        .map(|t| plain(model, &mut Greedy, &mut new_state(), t, n, stop))
        .collect();
    let total = |runs: &[Run]| {
        let tokens: usize = runs.iter().map(|r| r.tokens.len()).sum();
        let passes: usize = runs.iter().map(|r| r.passes).sum();
        let seconds: f64 = runs.iter().map(|r| r.seconds).sum();
        (tokens, passes, seconds)
    };
    let (tokens, _, seconds) = total(&plain_runs);
    println!(
        "{} turns, prompts {:?} tokens; plain: {tokens} tokens, {:.2} tok/s",
        turns.len(),
        turns.iter().map(Vec::len).collect::<Vec<_>>(),
        tokens as f64 / seconds
    );
    for name in ["lookup", "session", "mtp", "all", "chain"] {
        let Ok(mut decoder) = decoder(model, name) else {
            continue;
        };
        let mut runs = Vec::new();
        for t in turns {
            decoder.reset(model);
            runs.push(speculative(
                model,
                &mut Greedy,
                &mut decoder,
                &mut new_state(),
                t,
                n,
                stop,
            ));
        }
        let identical = runs
            .iter()
            .zip(&plain_runs)
            .all(|(a, b)| a.tokens == b.tokens);
        let (tokens, passes, fast) = total(&runs);
        let per_turn: Vec<String> = runs
            .iter()
            .map(|r| format!("{:.2}", r.tokens_per_pass()))
            .collect();
        println!(
            "{name:>8}: identical {identical}, {:.2} tokens/pass (turns {}), {:.2} tok/s, speedup {:.2}x",
            tokens as f64 / passes as f64,
            per_turn.join(" "),
            tokens as f64 / fast,
            seconds / fast
        );
    }
}
