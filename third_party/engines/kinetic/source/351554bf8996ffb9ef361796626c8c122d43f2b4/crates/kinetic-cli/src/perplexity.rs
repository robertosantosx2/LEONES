//! `kinetic perplexity`: llama-perplexity's measure on the same chunks, and
//! its KL divergence against a base model's saved log-probabilities.

use std::fs::File;
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::Path;

use kinetic_models::Model;
use kinetic_tokenizer::Tokenizer;

use crate::model_file::ModelFile;
use crate::Result;

const MAGIC: &[u8; 8] = b"_logits_";

/// What to measure.
pub struct Options<'a> {
    pub context: usize,
    /// At most this many chunks.
    pub chunks: Option<usize>,
    /// Save the log-probabilities here, as llama-perplexity's
    /// `--kl-divergence-base` does.
    pub save_base: Option<&'a Path>,
}

/// Perplexity of `model` over the text in `text`, chunk by chunk as
/// llama-perplexity scores it: each chunk of `context` tokens starts with
/// BOS where the model uses one and only its second half is scored.
pub fn run(model_path: &Path, text: &Path, opts: &Options) -> Result<()> {
    let file = ModelFile::open(model_path)?;
    let model = kinetic_models::load(file.source())?;
    let tokenizer = Tokenizer::from_gguf(file.source().header())?;
    let text = std::fs::read_to_string(text).map_err(|e| format!("{}: {e}", text.display()))?;
    let tokens = tokenizer.encode(&text, false);
    let n_ctx = opts.context;
    if tokens.len() < 2 * n_ctx {
        return Err(format!(
            "the text is {} tokens; a context of {n_ctx} needs at least {}",
            tokens.len(),
            2 * n_ctx
        )
        .into());
    }
    let n_chunk = (tokens.len() / n_ctx).min(opts.chunks.unwrap_or(usize::MAX));
    let vocab = model.n_vocab();
    let first = n_ctx / 2;
    eprintln!(
        "perplexity: {} tokens, {n_chunk} chunks of {n_ctx}",
        tokens.len()
    );

    let mut base = match opts.save_base {
        Some(path) => {
            let mut out = BufWriter::new(File::create(path)?);
            out.write_all(MAGIC)?;
            for n in [n_ctx, vocab, n_chunk] {
                out.write_all(&(n as i32).to_le_bytes())?;
            }
            for &t in &tokens[..n_chunk * n_ctx] {
                out.write_all(&(t as i32).to_le_bytes())?;
            }
            Some(out)
        }
        None => None,
    };
    let (mut nll, mut nll2, mut count) = (0.0f64, 0.0f64, 0usize);
    for c in 0..n_chunk {
        let chunk = &tokens[c * n_ctx..][..n_ctx];
        let logits = scored_rows(&model, &tokenizer, chunk);
        let mut packed = Vec::new();
        for (i, row) in logits.chunks(vocab).enumerate() {
            let next = chunk[first + i + 1] as usize;
            let v = match &base {
                Some(_) => pack_log_probs(row, next, &mut packed),
                None => -log_softmax(row, next),
            };
            nll += v;
            nll2 += v * v;
        }
        if let Some(out) = &mut base {
            out.write_all(&packed)?;
        }
        count += n_ctx - 1 - first;
        print!("[{}]{:.4},", c + 1, (nll / count as f64).exp());
        std::io::stdout().flush()?;
    }
    println!();
    if let Some(mut out) = base {
        out.flush()?;
    }
    let (mean, unc) = mean_and_uncertainty(nll, nll2, count);
    let ppl = mean.exp();
    println!("Final estimate: PPL = {ppl:.4} +/- {:.5}", unc * ppl);
    Ok(())
}

/// Logits after each scored position of `chunk`: the second half, but
/// for its last token. The chunk's first token becomes BOS, if any.
fn scored_rows(model: &Model, tokenizer: &Tokenizer, chunk: &[u32]) -> Vec<f32> {
    let first = chunk.len() / 2;
    let mut ids = chunk.to_vec();
    if let [bos] = tokenizer.encode("", false)[..] {
        ids[0] = bos;
    }
    let mut state = model.new_state();
    model.run(&mut state, &ids[..first], false);
    model
        .run(&mut state, &ids[first..ids.len() - 1], true)
        .logits
}

/// `ln p(tok)` under `logits`, summed as llama-perplexity does.
fn log_softmax(logits: &[f32], tok: usize) -> f64 {
    let max = logits.iter().copied().fold(logits[0], f32::max);
    let sum: f64 = logits.iter().map(|&l| f64::from((l - max).exp())).sum();
    f64::from(logits[tok] - max) - sum.ln()
}

/// Appends the row's log-probabilities in llama-perplexity's 16-bit
/// format and returns the token's negative log-likelihood.
fn pack_log_probs(logits: &[f32], tok: usize, out: &mut Vec<u8>) -> f64 {
    let max = logits.iter().copied().fold(logits[0], f32::max);
    let min = logits
        .iter()
        .copied()
        .fold(logits[0], f32::min)
        .max(max - 16.0);
    let sum: f64 = logits.iter().map(|&l| f64::from((l - max).exp())).sum();
    let log_sum = sum.ln() as f32;
    let scale = (max - min) / 65535.0;
    out.extend_from_slice(&scale.to_le_bytes());
    out.extend_from_slice(&(min - max - log_sum).to_le_bytes());
    let inv_scale = 1.0 / scale;
    for &l in logits {
        let q = match scale != 0.0 && l > min {
            true => nearest_int(inv_scale * (l - min)) as u16,
            false => 0,
        };
        out.extend_from_slice(&q.to_le_bytes());
    }
    if logits.len() % 2 == 1 {
        out.extend_from_slice(&[0, 0]);
    }
    f64::from(max + log_sum - logits[tok])
}

fn nearest_int(v: f32) -> i32 {
    ((v + 12_582_912.0).to_bits() & 0x007f_ffff) as i32 - 0x0040_0000
}

fn mean_and_uncertainty(sum: f64, sum2: f64, count: usize) -> (f64, f64) {
    let n = count as f64;
    let mean = sum / n;
    let var = sum2 / n - mean * mean;
    (
        mean,
        if var > 0.0 {
            (var / (n - 1.0)).sqrt()
        } else {
            0.0
        },
    )
}

/// Sums of llama-perplexity's KL divergence statistics.
#[derive(Default)]
struct Kld {
    nll: f64,
    nll2: f64,
    nll_base: f64,
    nll_base2: f64,
    kld: f64,
    kld2: f64,
    p_diff2: f64,
    same_top: usize,
    count: usize,
}

/// Compares `model` with the base model whose log-probabilities
/// llama-perplexity or [`run`] saved to `base`, on the tokens saved there.
pub fn kl_divergence(model_path: &Path, base: &Path) -> Result<()> {
    let file = ModelFile::open(model_path)?;
    let model = kinetic_models::load(file.source())?;
    let tokenizer = Tokenizer::from_gguf(file.source().header())?;
    let mut input =
        BufReader::new(File::open(base).map_err(|e| format!("{}: {e}", base.display()))?);
    let mut magic = [0u8; 8];
    input.read_exact(&mut magic)?;
    if &magic != MAGIC {
        return Err(format!("{} holds no saved log-probabilities", base.display()).into());
    }
    let mut int = || -> Result<usize> {
        let mut b = [0u8; 4];
        input.read_exact(&mut b)?;
        Ok(i32::from_le_bytes(b).max(0) as usize)
    };
    let (n_ctx, vocab, n_chunk) = (int()?, int()?, int()?);
    if vocab != model.n_vocab() {
        return Err(format!(
            "the base model has {vocab} tokens, this one {}",
            model.n_vocab()
        )
        .into());
    }
    let tokens = (0..n_ctx * n_chunk)
        .map(|_| int().map(|t| t as u32))
        .collect::<Result<Vec<u32>>>()?;
    let first = n_ctx / 2;
    let row_bytes = (2 * vocab.div_ceil(2) + 4) * 2;
    let mut rows = vec![0u8; (n_ctx - 1 - first) * row_bytes];
    let mut k = Kld::default();
    for c in 0..n_chunk {
        let chunk = &tokens[c * n_ctx..][..n_ctx];
        let logits = scored_rows(&model, &tokenizer, chunk);
        input.read_exact(&mut rows)?;
        for (i, (row, base)) in logits.chunks(vocab).zip(rows.chunks(row_bytes)).enumerate() {
            add_kld(&mut k, row, base, chunk[first + i + 1] as usize);
        }
        let (kld, _) = mean_and_uncertainty(k.kld, k.kld2, k.count);
        println!(
            "[{}] PPL {:.4}  KLD {kld:.6}",
            c + 1,
            (k.nll / k.count as f64).exp()
        );
    }
    let (ppl, ppl_u) = mean_and_uncertainty(k.nll, k.nll2, k.count);
    let (base_ppl, base_u) = mean_and_uncertainty(k.nll_base, k.nll_base2, k.count);
    let (kld, kld_u) = mean_and_uncertainty(k.kld, k.kld2, k.count);
    let (p_diff2, _) = mean_and_uncertainty(k.p_diff2, 0.0, k.count);
    println!(
        "Mean PPL(Q)                   : {:10.6} ± {:10.6}",
        ppl.exp(),
        ppl.exp() * ppl_u
    );
    println!(
        "Mean PPL(base)                : {:10.6} ± {:10.6}",
        base_ppl.exp(),
        base_ppl.exp() * base_u
    );
    println!("Mean ln(PPL(Q)/PPL(base))     : {:10.6}", ppl - base_ppl);
    println!("Mean    KLD                   : {kld:10.6} ± {kld_u:10.6}");
    println!(
        "RMS Δp                        : {:6.3} %",
        100.0 * p_diff2.sqrt()
    );
    println!(
        "Same top p                    : {:6.3} %",
        100.0 * k.same_top as f64 / k.count as f64
    );
    Ok(())
}

fn add_kld(k: &mut Kld, logits: &[f32], base: &[u8], tok: usize) {
    let f = |at: usize| f32::from_le_bytes(base[at..at + 4].try_into().expect("4 bytes"));
    let (scale, min_log_prob) = (f(0), f(4));
    let q = |i: usize| f32::from(u16::from_le_bytes([base[8 + 2 * i], base[9 + 2 * i]]));
    let (mut max, mut top) = (logits[0], 0);
    for (i, &l) in logits.iter().enumerate().skip(1) {
        if l > max {
            (max, top) = (l, i);
        }
    }
    let sum: f64 = logits.iter().map(|&l| f64::from((l - max).exp())).sum();
    let log_sum = sum.ln() as f32;
    let nll = max + log_sum - logits[tok];
    let nll_base = -(scale * q(tok) + min_log_prob);
    let norm = max + log_sum;
    let (mut kld, mut top_base, mut best) = (0.0f64, 0, f32::MIN);
    for (i, &l) in logits.iter().enumerate() {
        let lp = scale * q(i) + min_log_prob;
        if i == 0 || lp > best {
            (best, top_base) = (lp, i);
        }
        if lp > -16.0 {
            kld += f64::from(lp.exp() * (lp - l + norm));
        }
    }
    let p_diff = f64::from((-nll).exp() - (-nll_base).exp());
    k.nll += f64::from(nll);
    k.nll2 += f64::from(nll * nll);
    k.nll_base += f64::from(nll_base);
    k.nll_base2 += f64::from(nll_base * nll_base);
    k.kld += kld;
    k.kld2 += kld * kld;
    k.p_diff2 += p_diff * p_diff;
    k.same_top += usize::from(top == top_base);
    k.count += 1;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn packed_log_probs_give_back_the_distribution() {
        let logits: Vec<f32> = (0..11).map(|i| (i as f32 * 1.7).sin() * 4.0).collect();
        let mut packed = Vec::new();
        let nll = pack_log_probs(&logits, 3, &mut packed);
        assert!((nll + log_softmax(&logits, 3)).abs() < 1e-5);
        assert_eq!(packed.len(), (2 * 6 + 4) * 2);
        let mut k = Kld::default();
        add_kld(&mut k, &logits, &packed, 3);
        assert!(k.kld.abs() < 1e-4, "{}", k.kld);
        assert_eq!(k.same_top, 1);
        assert!((k.nll - k.nll_base).abs() < 1e-3);
    }
}
