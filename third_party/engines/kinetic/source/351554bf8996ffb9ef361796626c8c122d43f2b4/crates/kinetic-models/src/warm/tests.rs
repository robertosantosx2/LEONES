//! The cache logic on its own, and exactness and speed on a real model:
//!
//! KINETIC_TEST_GGUF=model.gguf cargo test --release -p kinetic-models warm -- --ignored --nocapture

use std::io;
use std::path::PathBuf;
use std::time::Instant;

use kinetic_gguf::GgufFile;

use super::codec::{self, Reader, Writer};
use super::*;

fn meta(len: usize, marks: &[usize], in_place: bool) -> Meta {
    Meta {
        tokens: (0..len as u32).collect(),
        marks: marks.to_vec(),
        in_place,
        rate: 0.0,
    }
}

#[test]
fn reach_stops_at_marks_unless_caches_cut_anywhere() {
    let recurrent = meta(100, &[32, 64], false);
    assert_eq!(recurrent.reach(80), 64);
    assert_eq!(recurrent.reach(63), 32);
    assert_eq!(recurrent.reach(10), 0);
    assert_eq!(recurrent.reach(500), 100);
    assert_eq!(meta(100, &[], true).reach(80), 80);
}

#[test]
fn a_whole_prompt_hit_needs_the_same_length() {
    let m = meta(10, &[], true);
    let prompt: Vec<u32> = (0..10).collect();
    assert_eq!(m.hit(&prompt, 1), 10);
    assert_eq!(m.hit(&prompt[..6], 1), 5);
    let mut other = prompt.clone();
    other[7] = 99;
    assert_eq!(m.hit(&other, 1), 7);
}

#[test]
fn aligned_hits_fall_on_multiples() {
    let prompt: Vec<u32> = (0..100).collect();
    assert_eq!(meta(100, &[], true).hit(&prompt[..90], 32), 64);
    assert_eq!(meta(100, &[48, 64], false).hit(&prompt[..90], 32), 64);
    assert_eq!(meta(100, &[48], false).hit(&prompt[..90], 32), 0);
    assert_eq!(meta(90, &[48], false).hit(&prompt[..90], 32), 90);
}

#[test]
fn an_entry_covers_the_prefixes_it_can_return_to() {
    let long = meta(100, &[32, 64], false);
    assert!(long.covers(&meta(64, &[32], false)));
    assert!(!long.covers(&meta(50, &[32], false)));
    assert!(!long.covers(&meta(64, &[16], false)));
    assert!(!long.covers(&meta(64, &[], true)));
    assert!(meta(100, &[], true).covers(&meta(50, &[], true)));
}

/// Pseudo-random token ids, the same for every run.
fn tokens(n: usize, seed: u64, vocab: usize) -> Vec<u32> {
    let mut x = seed.wrapping_mul(0x9e37_79b9_7f4a_7c15) | 1;
    (0..n)
        .map(|_| {
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            (100 + x % (vocab.min(30_000) as u64 - 100)) as u32
        })
        .collect()
}

fn bits(x: &[f32]) -> Vec<u32> {
    x.iter().map(|v| v.to_bits()).collect()
}

fn max_diff(a: &[f32], b: &[f32]) -> f32 {
    a.iter()
        .zip(b)
        .map(|(a, b)| (a - b).abs())
        .fold(0.0, f32::max)
}

fn argmax(x: &[f32]) -> usize {
    (0..x.len()).max_by(|&i, &j| x[i].total_cmp(&x[j])).unwrap()
}

fn test_model() -> (String, GgufFile) {
    let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
    let file = GgufFile::open(&path).unwrap();
    (path, file)
}

fn temp_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("kinetic-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    dir
}

/// Runs the rest of `prompt` in batches that end at `cuts`, returning the
/// logits after the last token.
fn run_split(model: &Model, state: &mut State, prompt: &[u32], cuts: &[usize]) -> Vec<f32> {
    let mut logits = Vec::new();
    let mut at = state.len();
    for &cut in cuts.iter().chain([&prompt.len()]) {
        let cut = cut.min(prompt.len());
        if cut > at {
            logits = model.forward_batch(state, &prompt[at..cut]);
            at = cut;
        }
    }
    logits
}

/// The logits of `n` greedy steps after `logits`, as bits.
fn continue_greedy(model: &Model, state: &mut State, logits: &[f32], n: usize) -> Vec<Vec<u32>> {
    let mut out = vec![bits(logits)];
    let mut token = argmax(logits) as u32;
    for _ in 0..n {
        let logits = model.forward(state, token);
        token = argmax(&logits) as u32;
        out.push(bits(&logits));
    }
    out
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn truncated_and_reloaded_states_continue_bit_for_bit() {
    let (_, file) = test_model();
    let model = crate::load(&file).unwrap();
    let prompt = tokens(700, 1, model.n_vocab());
    let (a, b) = (256, 512);

    let mut full = model.new_state();
    for cut in [a, b, prompt.len()] {
        run_split(&model, &mut full, &prompt[..cut], &[]);
        model.mark(&mut full);
    }
    for keep in [a, b, 300] {
        let mut state = full.clone();
        let reached = model.truncate(&mut state, keep);
        assert_eq!(reached, model.reach(&full, keep));
        let mut fresh = model.new_state();
        run_split(&model, &mut fresh, &prompt[..reached], &[a, b]);
        let rest = &prompt[reached..];
        let got = model.forward_batch(&mut state, rest);
        let want = model.forward_batch(&mut fresh, rest);
        assert_eq!(bits(&got), bits(&want), "truncated to {reached} of {keep}");
        assert_eq!(
            continue_greedy(&model, &mut state, &got, 4),
            continue_greedy(&model, &mut fresh, &want, 4)
        );
        println!("truncate to {keep}: reached {reached}, exact");
    }

    let mut w = Writer::new(Vec::new());
    codec::write_state(&mut w, &full).unwrap();
    let bytes = w.finish().unwrap();
    let mut r = Reader::new(&bytes[..]);
    let mut loaded = codec::read_state(&mut r, &model).unwrap();
    r.finish().unwrap();
    assert!(loaded.marks().eq(full.marks()));
    let next = tokens(8, 2, model.n_vocab());
    assert_eq!(
        bits(&model.forward_batch(&mut loaded, &next)),
        bits(&model.forward_batch(&mut full, &next))
    );

    let mut damaged = bytes.clone();
    damaged[bytes.len() / 2] ^= 1;
    let mut r = Reader::new(&damaged[..]);
    let read = codec::read_state(&mut r, &model).and_then(|_| r.finish());
    assert_eq!(read.unwrap_err().kind(), io::ErrorKind::InvalidData);
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn warm_prefills_match_cold_ones() {
    let (path, file) = test_model();
    let model = crate::load(&file).unwrap();
    let vocab = model.n_vocab();
    let id = model_id(&path).unwrap();
    let dir = temp_dir("warm-exact");
    let system = tokens(1200, 3, vocab);
    let ask = |seed, n| [system.clone(), tokens(n, seed, vocab)].concat();
    let (first, second) = (ask(4, 50), ask(5, 40));

    let mut warm = Warm::new(&model, id, 1 << 30);
    let a = warm.prefill(&first);
    assert_eq!(a.hit, 0);
    warm.insert(&first, &a.state, &a.logits).unwrap();

    let b = warm.prefill(&second);
    let want_hit = Meta {
        tokens: first.clone(),
        marks: a.state.marks().chain([first.len()]).collect(),
        in_place: warm.grid.is_none(),
        rate: 0.0,
    }
    .hit(&second, 1);
    assert_eq!(b.hit, want_hit);

    // The batches the warm run used: the grid, then where the prompts part.
    let mut cuts: Vec<usize> = a.state.marks().filter(|&m| m <= b.hit).collect();
    cuts.push(system.len());
    let mut cold = model.new_state();
    let want = run_split(&model, &mut cold, &second, &cuts);
    assert_eq!(bits(&b.logits), bits(&want), "warm and cold differ");
    assert_eq!(
        continue_greedy(&model, &mut b.state.clone(), &b.logits, 4),
        continue_greedy(&model, &mut cold, &want, 4)
    );
    let plain = model.forward_batch(&mut model.new_state(), &second);
    println!(
        "hit {} of {}, grid {:?}; against one batch: max diff {:e}, same argmax {}",
        b.hit,
        second.len(),
        warm.grid,
        max_diff(&plain, &b.logits),
        argmax(&plain) == argmax(&b.logits)
    );

    let again = warm.prefill(&first);
    assert_eq!(again.hit, first.len());
    assert_eq!(bits(&again.logits), bits(&a.logits));

    // Where the second prompt left the first is marked, so a third one
    // resumes right after the shared system prompt.
    warm.insert(&second, &b.state, &b.logits).unwrap();
    assert_eq!(warm.prefill(&ask(6, 30)).hit, system.len());

    Warm::new(&model, id, 0)
        .with_disk(&dir, 1 << 30)
        .unwrap()
        .insert(&first, &a.state, &a.logits)
        .unwrap();
    let mut reopened = Warm::new(&model, id, 1 << 30)
        .with_disk(&dir, 1 << 30)
        .unwrap();
    let from_disk = reopened.prefill(&second);
    assert_eq!(from_disk.hit, b.hit);
    assert_eq!(bits(&from_disk.logits), bits(&b.logits));
    std::fs::remove_dir_all(&dir).unwrap();
}

/// Time to first token for a long system prompt and a short question, cold
/// and warm, and what the cache holds per token.
#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn time_to_first_token() {
    let (path, file) = test_model();
    let model = crate::load(&file).unwrap();
    let vocab = model.n_vocab();
    let system = tokens(2000, 6, vocab);
    let first = [system.clone(), tokens(24, 7, vocab)].concat();
    let second = [system.clone(), tokens(20, 8, vocab)].concat();
    let third = [system.clone(), tokens(22, 9, vocab)].concat();

    let start = Instant::now();
    model.forward_batch(&mut model.new_state(), &first);
    let plain = start.elapsed();

    let mut warm = Warm::new(&model, model_id(&path).unwrap(), 2 << 30);
    let cold = warm.prefill(&first);
    let start = Instant::now();
    warm.insert(&first, &cold.state, &cold.logits).unwrap();
    let insert = start.elapsed();
    let hit = warm.prefill(&second);
    warm.insert(&second, &hit.state, &hit.logits).unwrap();
    let branched = warm.prefill(&third);
    let repeat = warm.prefill(&first);

    let entry = warm
        .entries
        .iter()
        .find(|e| e.meta.tokens == first)
        .unwrap();
    let mut disk_bytes = 0;
    let mut sized = Writer::new(Counter(&mut disk_bytes));
    codec::write_state(&mut sized, &entry.saved.state).unwrap();
    sized.f32s(&cold.logits).unwrap();
    sized.finish().unwrap();

    let ms = |d: Duration| d.as_secs_f64() * 1e3;
    println!("prompt {} tokens, grid {:?}", first.len(), warm.grid);
    println!("plain forward_batch: {:.0} ms", ms(plain));
    println!(
        "cold prefill: {:.0} ms, insert {:.0} ms",
        ms(cold.elapsed),
        ms(insert)
    );
    println!(
        "warm, new question: {:.0} ms, hit {} tokens, saved about {:.0} ms",
        ms(hit.elapsed),
        hit.hit,
        ms(hit.saved)
    );
    println!(
        "warm, third question: {:.0} ms, hit {} tokens",
        ms(branched.elapsed),
        branched.hit
    );
    println!(
        "warm, same prompt: {:.1} ms, hit {}",
        ms(repeat.elapsed),
        repeat.hit
    );
    let n = first.len() as f64;
    let floats = |marked: bool, pos: usize| -> usize {
        let layers = model
            .layers
            .iter()
            .filter(|l| l.mixer.needs_mark() == marked);
        layers.flat_map(|l| l.mixer.buffer_lens(pos)).sum()
    };
    println!(
        "attention cache {:.1} KB/token, one mark {:.2} MB",
        4.0 * floats(false, 1) as f64 / 1024.0,
        4.0 * floats(true, usize::MAX) as f64 / (1 << 20) as f64
    );
    println!(
        "memory {:.1} KB/token ({:.1} MB), disk {:.1} KB/token ({:.1} MB)",
        entry.bytes as f64 / n / 1024.0,
        entry.bytes as f64 / (1 << 20) as f64,
        disk_bytes as f64 / n / 1024.0,
        disk_bytes as f64 / (1 << 20) as f64
    );

    // Files over 200 MB are not written on this machine's small disk.
    if disk_bytes < 200 << 20 {
        let dir = temp_dir("warm-ttft");
        let id = model_id(&path).unwrap();
        let mut saving = Warm::new(&model, id, 0).with_disk(&dir, 1 << 30).unwrap();
        let start = Instant::now();
        saving.insert(&first, &cold.state, &cold.logits).unwrap();
        // Dropping the cache waits for its background write.
        drop(saving);
        let write = start.elapsed();
        let mut reopened = Warm::new(&model, id, 1 << 30)
            .with_disk(&dir, 1 << 30)
            .unwrap();
        let loaded = reopened.prefill(&second);
        println!(
            "disk: write {:.0} ms; warm from disk, new question: {:.0} ms, hit {}",
            ms(write),
            ms(loaded.elapsed),
            loaded.hit
        );
        std::fs::remove_dir_all(&dir).unwrap();
    }
}

struct Counter<'a>(&'a mut usize);

impl io::Write for Counter<'_> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        *self.0 += buf.len();
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
