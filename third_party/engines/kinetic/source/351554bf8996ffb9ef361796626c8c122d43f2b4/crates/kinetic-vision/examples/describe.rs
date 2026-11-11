//! Asks a Qwen3.5 model about an image, decoding greedily, and reports the
//! image encode time and the time to the first token.
//!
//! cargo run --release -p kinetic-vision --example describe -- model.gguf mmproj.gguf image.png "Describe this image." 64

use std::io::Write;
use std::time::Instant;

use kinetic_gguf::GgufFile;
use kinetic_models::Input;
use kinetic_tokenizer::Tokenizer;
use kinetic_vision::{decode, VisionEncoder};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let usage = "usage: describe <model.gguf> <mmproj.gguf> <image> [question] [n]";
    let lm_file = GgufFile::open(args.next().ok_or(usage)?)?;
    let vision_file = GgufFile::open(args.next().ok_or(usage)?)?;
    let image_path = args.next().ok_or(usage)?;
    let question = args.next().unwrap_or_else(|| "Describe this image.".into());
    let n: usize = args.next().map_or(Ok(128), |s| s.parse())?;

    let model = kinetic_models::load(&lm_file)?;
    let tokenizer = Tokenizer::from_gguf(lm_file.header())?;
    let encoder = VisionEncoder::load(&vision_file)?;
    let bytes = std::fs::read(&image_path)?;

    let start = Instant::now();
    let pixels = encoder.prepare(&decode(&bytes)?);
    let image = encoder.encode(&pixels)?;
    let encoded = start.elapsed();

    let before = tokenizer.encode("<|im_start|>user\n<|vision_start|>", true);
    let after = tokenizer.encode(
        &format!(
            "<|vision_end|>{question}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        ),
        true,
    );
    let inputs = [
        Input::Tokens(&before),
        Input::Image {
            rows: &image.rows,
            width: image.width,
            height: image.height,
        },
        Input::Tokens(&after),
    ];
    let mut state = model.new_state();
    let mut logits = model.run_inputs(&mut state, &inputs, false).logits;
    let first = start.elapsed();

    let end = tokenizer.encode("<|im_end|>", true);
    let mut out = tokenizer.stream();
    let mut generated = Vec::new();
    let decode_start = Instant::now();
    for _ in 0..n {
        let best = argmax(&logits);
        if Some(best) == tokenizer.eos() || end == [best] {
            break;
        }
        generated.push(best);
        print!("{}", out.push(best));
        std::io::stdout().flush()?;
        logits = model.forward(&mut state, best);
    }
    println!("{}", out.finish());
    let decoding = decode_start.elapsed();

    println!(
        "ids: {}",
        generated
            .iter()
            .map(u32::to_string)
            .collect::<Vec<_>>()
            .join(",")
    );
    println!(
        "{}x{} pixels, {} image tokens, {} text tokens; encode {:.2}s, first token {:.2}s, decode {:.2} tok/s",
        pixels.width,
        pixels.height,
        image.len(),
        before.len() + after.len(),
        encoded.as_secs_f64(),
        first.as_secs_f64(),
        generated.len() as f64 / decoding.as_secs_f64()
    );
    Ok(())
}

fn argmax(logits: &[f32]) -> u32 {
    logits
        .iter()
        .enumerate()
        .max_by(|a, b| a.1.total_cmp(b.1))
        .map_or(0, |(i, _)| i as u32)
}
