mod common;
use rusting_strata::{gguf::Gguf, gpu_model::GpuModel, model::{Model, State}, ops, tokenizer::Tokenizer};

/// GPU forward matches the CPU reference per position, with all routed experts on the CPU and with the default placement.
#[test]
fn gpu_forward_matches_cpu_reference() {
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let ids = tok.encode("The capital of France is").unwrap();
    let mut st = State::new(&m.cfg);
    let want: Vec<Vec<f32>> = ids.iter().map(|&t| m.step(&mut st, t)).collect();
    // The bound is set for the default model. The 30B with its Q2_K experts on the CPU lands 12% of the logit range
    // off at the first token (3% with the experts on the GPU); the argmax still agrees.
    let tol = if common::is_default_model(&p) { 0.05 } else { 0.15 };

    for (margin, (bk, gpu)) in [usize::MAX / 2, 512 << 20].into_iter().flat_map(|mg| common::backends().into_iter().map(move |b| (mg, b))) {
        eprintln!("backend {bk}, margin {margin}");
        let mut gm = GpuModel::load(&m, gpu, 256, 0, margin, 0).unwrap();
        let t0 = std::time::Instant::now();
        for (i, (&t, w)) in ids.iter().zip(&want).enumerate() {
            let got = gm.step(t).unwrap();
            let range = w.iter().fold(f32::MIN, |a, &b| a.max(b)) - w.iter().fold(f32::MAX, |a, &b| a.min(b));
            let diff = got.iter().zip(w).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
            eprintln!("pos {i}: argmax {} vs {}, max |dlogit| {diff:.4} (range {range:.2})", ops::argmax(&got), ops::argmax(w));
            assert_eq!(ops::argmax(&got), ops::argmax(w), "pos {i}");
            assert!(diff <= tol * range, "pos {i}: {diff} vs range {range}");
        }
        eprintln!("{} tokens in {:?} (CPU {:?}), expert hits {} misses {}", ids.len(), t0.elapsed(), gm.cpu_time, gm.hits, gm.misses);
    }
    assert_eq!(tok.decode(&[ops::argmax(want.last().unwrap()) as u32]).unwrap().trim(), "Paris");
}

/// Chunked prefill (several chunks, tail chunk shorter) matches the CPU f32 reference at the last prompt token and at
/// the decode step after it. Token-by-token GPU decode is the yardstick for the error it may have: its int8
/// activations drift further from f32 over a long prompt than the f16 prefill GEMMs do.
#[test]
fn prefill_matches_reference() {
    let _gpu = common::gpu_lock();
    // Place experts in layer order, not from the routing profile that every earlier run rewrites (with it the
    // decode yardstick, and so this test's outcome, depended on what ran before).
    unsafe { std::env::set_var("STRATA_FIXED_EXPERTS", "1") }
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let text = "Rust is a multi-paradigm, general-purpose programming language that emphasizes performance, type safety, \
                and concurrency. It enforces memory safety, meaning that all references point to valid memory, without \
                a garbage collector. To simultaneously enforce memory safety and prevent data races, its borrow checker \
                tracks the object lifetime of all references in a program during compilation. Rust was influenced by";
    let ids = tok.encode(text).unwrap();
    assert!(ids.len() > 64, "{} tokens", ids.len());
    let mut st = State::new(&m.cfg);
    let mut cpu = Vec::new();
    for &t in &ids { cpu = m.step(&mut st, t); }
    let next = ops::argmax(&cpu) as u32;
    let cpu2 = m.step(&mut st, next);
    let chunk = std::env::var("CHUNK").map_or(48, |v| v.parse().unwrap());
    for (bk, gpu) in common::backends() {
        eprintln!("backend {bk}");
        let mut gm = GpuModel::load(&m, gpu, 512, chunk, 512 << 20, 0).unwrap();
        // Fixed expert placement: adaptive moves change the decode yardstick from run to run (it differed inside the
        // full suite and failed once).
        gm.adapt_every = 0;
        let t0 = std::time::Instant::now();
        let pre = gm.prefill(&ids).unwrap();
        eprintln!("prefill {} tokens in {:?}", ids.len(), t0.elapsed());
        let pre2 = gm.step(next).unwrap();
        gm.reset().unwrap();
        let mut dec = Vec::new();
        for &t in &ids { dec = gm.step(t).unwrap(); }
        let dec2 = gm.step(next).unwrap();
        let diff = |a: &[f32], b: &[f32]| a.iter().zip(b).fold(0f32, |x, (p, q)| x.max((p - q).abs()));
        for (name, pf, dc, want) in [("last prompt token", &pre, &dec, &cpu), ("next step", &pre2, &dec2, &cpu2)] {
            let (dp, dd) = (diff(pf, want), diff(dc, want));
            eprintln!("{name}: argmax prefill {} decode {} CPU {}, max |dlogit| prefill {dp:.4} decode {dd:.4}",
                      ops::argmax(pf), ops::argmax(dc), ops::argmax(want));
            assert_eq!(ops::argmax(pf), ops::argmax(want), "{name}");
            // int8 MMQ prefill GEMMs (3754e65) quantize activations, decode does not: allow 1.5x (seen 1.17x).
            assert!(dp <= (1.5 * dd).max(0.5), "{name}: prefill error {dp} above 1.5x decode error {dd}");
        }
    }
}

/// GPU MTP draft head matches `Model::mtp_step` per position (prompt plus a few greedy tokens). Both get the GPU's
/// hidden state, so the check covers the head alone, not the main model's drift. One position may miss: a near-tie in
/// the head's expert routing sometimes picks a different expert on the two sides (|dlogit| ~1.1, seen on 0991789 too).
/// No experts resident: with a VRAM margin, which experts run on the GPU depends on free VRAM (the second backend sees
/// less while the first one's context lives), so the hidden states and the near-ties moved between backends and runs.
#[test]
fn mtp_draft_matches_reference() {
    use rusting_strata::model::Mtp;
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    if m.cfg.n_nextn == 0 { eprintln!("SKIP: no nextn layer"); return }
    let tok = Tokenizer::from_gguf(&g).unwrap();
    for (bk, gpu) in common::backends() {
        eprintln!("backend {bk}");
        let mut gm = GpuModel::load(&m, gpu, 256, 0, usize::MAX / 2, 1).unwrap();
        let mut ids = tok.encode("The capital of France is").unwrap();
        let (mut st, mut mtp) = (State::new(&m.cfg), Mtp::default());
        let mut bad = 0;
        for i in 0..ids.len() + 4 {
            let logits = m.step(&mut st, ids[i]);
            gm.step(ids[i]).unwrap();
            if i + 1 == ids.len() { ids.push(ops::argmax(&logits) as u32); }
            let want = m.mtp_step(&mut mtp, &gm.hidden().unwrap(), ids[i + 1]).0;
            let got = gm.mtp_draft(ids[i + 1], 0).unwrap();
            let range = want.iter().fold(f32::MIN, |a, &b| a.max(b)) - want.iter().fold(f32::MAX, |a, &b| a.min(b));
            let diff = got.iter().zip(&want).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
            eprintln!("pos {i}: draft {} vs {}, max |dlogit| {diff:.4} (range {range:.2})", ops::argmax(&got), ops::argmax(&want));
            if ops::argmax(&got) != ops::argmax(&want) || diff > 0.05 * range { bad += 1; }
        }
        assert!(bad <= 1, "{bad} positions differ");
    }
}

/// `verify` on several tokens matches the same tokens stepped one by one after `restore_state`, and the restored
/// state replays bit for bit (rollback for rejected drafts).
#[test]
fn verify_matches_steps() {
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    for (bk, gpu) in common::backends() {
        eprintln!("backend {bk}");
        let mut gm = GpuModel::load(&m, gpu, 256, 0, 512 << 20, 0).unwrap();
        let ids = tok.encode("The capital of France is Paris, and the capital of Spain is").unwrap();
        let (pre, rest) = ids.split_at(ids.len() - 4);
        for &t in pre { gm.step(t).unwrap(); }
        gm.save_state().unwrap();
        let mut seq = vec![];
        for &t in rest { seq.push(gm.step(t).unwrap()); }
        gm.restore_state().unwrap();
        assert_eq!(gm.step(rest[0]).unwrap(), seq[0], "replay after restore");
        for nt in [4, 2] {
            gm.restore_state().unwrap();
            let got = gm.verify(&rest[..nt]).unwrap();
            for (t, (g, w)) in got.iter().zip(&seq).enumerate() {
                let range = w.iter().fold(f32::MIN, |a, &b| a.max(b)) - w.iter().fold(f32::MAX, |a, &b| a.min(b));
                let diff = g.iter().zip(w).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
                eprintln!("nt {nt} token {t}: argmax {} vs {}, max |dlogit| {diff:.4} (range {range:.2})", ops::argmax(g), ops::argmax(w));
                assert_eq!(ops::argmax(g), ops::argmax(w), "nt {nt} token {t}");
                assert!(diff <= 0.01 * range, "nt {nt} token {t}: {diff} vs range {range}");
            }
            assert_eq!(gm.pos, pre.len() + nt);
            // State after verify continues like the stepped one.
            let next = gm.step(rest.get(nt).copied().unwrap_or(rest[0])).unwrap();
            if nt < rest.len() {
                let diff = next.iter().zip(&seq[nt]).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
                eprintln!("nt {nt} next step max |dlogit| {diff:.4}");
                assert_eq!(ops::argmax(&next), ops::argmax(&seq[nt]));
            }
        }
    }
}

/// Greedy decoding with MTP speculation (`spec_step`, k = 1 to 3) gives the same tokens as plain steps. Same instance and fixed
/// expert placement, so both runs see the same numerics.
#[test]
fn mtp_spec_matches_greedy() {
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    if m.cfg.n_nextn == 0 { eprintln!("SKIP: no nextn layer"); return }
    let tok = Tokenizer::from_gguf(&g).unwrap();
    for (bk, gpu) in common::backends() {
        eprintln!("backend {bk}");
        let mut gm = GpuModel::load(&m, gpu, 512, 0, 512 << 20, 3).unwrap();
        assert_eq!(gm.k, 3);
        gm.adapt_every = 0;
        let ids = tok.encode("Write a short story about a dragon.").unwrap();
        let n = 64;
        let mut run = |k: usize| -> (Vec<u32>, (usize, usize)) {
            (gm.k, gm.drafts) = (k.max(1), (0, 0));
            gm.reset().unwrap();
            let mut t = ops::argmax(&gm.prefill(&ids).unwrap()) as u32;
            let (mut out, mut row) = (vec![], 0);
            while out.len() < n {
                if k > 0 {
                    let (toks, nx, r) = gm.spec_step(t, row, &mut ops::Sampler::greedy()).unwrap();
                    (t, row) = (nx, r);
                    out.extend(toks);
                } else {
                    out.push(t);
                    t = ops::argmax(&gm.step(t).unwrap()) as u32;
                }
            }
            out.truncate(n);
            (out, gm.drafts)
        };
        let plain = run(0).0;
        for k in [1, 2, 3] {
            let (spec, (made, ok)) = run(k);
            eprintln!("k {k}: drafts accepted {ok}/{made}");
            assert_eq!(spec, plain, "k {k}");
            if k == 1 { assert!(2 * ok >= made, "acceptance {ok}/{made}"); }
        }
    }
}

/// `rollback` to the first token of a 2-token verify leaves the same state as stepping that token alone.
#[test]
fn rollback_matches_step() {
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    if m.cfg.n_nextn == 0 { eprintln!("SKIP: no nextn layer"); return }
    let tok = Tokenizer::from_gguf(&g).unwrap();
    for (bk, gpu) in common::backends() {
        eprintln!("backend {bk}");
        let mut gm = GpuModel::load(&m, gpu, 256, 0, 512 << 20, 1).unwrap();
        gm.adapt_every = 0;
        let ids = tok.encode("The capital of France is Paris, and the capital of Spain is").unwrap();
        let (pre, rest) = ids.split_at(ids.len() - 3);
        for &t in pre { gm.step(t).unwrap(); }
        gm.save_state().unwrap();
        gm.step(rest[0]).unwrap();
        let want = gm.step(rest[2]).unwrap();
        gm.restore_state().unwrap();
        let start = gm.pos;
        gm.verify(&rest[..2]).unwrap();
        gm.rollback(start, 1).unwrap();
        assert_eq!(gm.pos, start + 1);
        assert_eq!(gm.step(rest[2]).unwrap(), want, "step after rollback");
    }
}

/// `prefill_cached` restarts from the saved history state: the logits equal a fresh run split at the same points,
/// with decode steps in between that must not leak into the next prompt.
#[test]
fn prefill_cached_reuses_history() {
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    for (bk, gpu) in common::backends() {
        eprintln!("backend {bk}");
        let mut gm = GpuModel::load(&m, gpu, 512, 128, 512 << 20, 0).unwrap();
        gm.adapt_every = 0;
        gm.cache_ram = 0;
        let enc = |s: &str| tok.encode(s).unwrap();
        let h1 = enc("<|im_start|>user\nTell me about rivers, the ways they carve valleys over thousands of years, and why towns grow on their banks.<|im_end|>\n");
        let h2 = [h1.clone(), enc("<|im_start|>assistant\nRivers move water and sediment downhill.<|im_end|>\n<|im_start|>user\nAnd lakes?<|im_end|>\n")].concat();
        let tail = enc("<|im_start|>assistant\n");
        let fresh = |gm: &mut GpuModel, parts: &[&[u32]]| {
            gm.reset().unwrap();
            parts.iter().map(|p| gm.prefill(p).unwrap()).last().unwrap()
        };

        let p1 = [&h1[..], &tail].concat();
        let want1 = fresh(&mut gm, &[&h1, &tail]);
        let (got1, r1) = gm.prefill_cached(&p1, 0, h1.len()).unwrap();
        assert_eq!((r1, &got1), (0, &want1));
        for t in [11u32, 22, 33] { gm.step(t).unwrap(); } // a reply that the next prompt does not contain

        let p2 = [&h2[..], &tail].concat();
        let (got2, r2) = gm.prefill_cached(&p2, 0, h2.len()).unwrap();
        assert_eq!(r2, h1.len());
        // A prompt that does not extend the saved history (now h2) starts over.
        let (got3, r3) = gm.prefill_cached(&p1, 0, h1.len()).unwrap();
        assert_eq!((r3, &got3), (0, &want1));
        let want3 = want1.clone();
        let want2 = fresh(&mut gm, &[&h1, &h2[h1.len()..], &tail]);
        assert_eq!(got2, want2, "reused prefix");
        let want_h2 = want2;

        // With a system prompt: a request whose history rewrites the earlier one (a compacted conversation) restarts
        // from the state after the system prompt, also after decode steps and a history hit in between.
        let sys = enc("<|im_start|>system\nYou are a geography tutor. Answer in two sentences.<|im_end|>\n");
        let s1 = [&sys[..], &h1].concat();
        let s2 = [&sys[..], &enc("<|im_start|>user\nSummary: we talked about rivers.<|im_end|>\n<|im_start|>user\nAnd lakes?<|im_end|>\n")].concat();
        let q1 = [&s1[..], &tail].concat();
        let q2 = [&s2[..], &tail].concat();
        let want1 = fresh(&mut gm, &[&sys, &h1, &tail]);
        let want2 = fresh(&mut gm, &[&sys, &s2[sys.len()..], &tail]);
        let (got, r) = gm.prefill_cached(&q1, sys.len(), s1.len()).unwrap();
        assert_eq!((r, &got), (0, &want1));
        for t in [11u32, 22, 33] { gm.step(t).unwrap(); }
        let (got, r) = gm.prefill_cached(&q2, sys.len(), s2.len()).unwrap();
        assert_eq!((r, &got), (sys.len(), &want2), "restart after the system prompt");
        let (got, r) = gm.prefill_cached(&q2, sys.len(), s2.len()).unwrap();
        assert_eq!((r, &got), (s2.len(), &want2), "history hit");
        let (got, r) = gm.prefill_cached(&q1, sys.len(), s1.len()).unwrap();
        assert_eq!((r, &got), (sys.len(), &want1), "back to the first history");
        // Another system prompt starts over and replaces the stash.
        let (got, r) = gm.prefill_cached(&p1, 0, h1.len()).unwrap();
        assert_eq!((r, &got), (0, &want3));
        let (_, r) = gm.prefill_cached(&q2, sys.len(), s2.len()).unwrap();
        assert_eq!(r, 0, "stash dropped once its KV was rewritten");

        // With host memory for replaced states, a side request with another prompt in between costs nothing.
        gm.cache_ram = 64 << 20;
        let (got, r) = gm.prefill_cached(&q1, sys.len(), s1.len()).unwrap();
        assert_eq!((r, &got), (sys.len(), &want1));
        for t in [11u32, 22, 33] { gm.step(t).unwrap(); }
        let (got, r) = gm.prefill_cached(&p1, 0, h1.len()).unwrap();
        assert_eq!((r, &got), (0, &want3), "side request");
        let (got, r) = gm.prefill_cached(&p2, 0, h2.len()).unwrap();
        assert_eq!((r, &got), (h1.len(), &want_h2), "side request continued");
        let (got, r) = gm.prefill_cached(&q1, sys.len(), s1.len()).unwrap();
        assert_eq!((r, &got), (s1.len(), &want1), "parked conversation");
        for t in [11u32, 22, 33] { gm.step(t).unwrap(); }
        let (got, r) = gm.prefill_cached(&p2, 0, h2.len()).unwrap();
        assert_eq!((r, &got), (h2.len(), &want_h2), "parked side request");

        // Another owner (API key) reuses nothing of owner 0, not even the system prompt; owner 0 still finds its own.
        gm.owner = 7;
        let (got, r) = gm.prefill_cached(&q1, sys.len(), s1.len()).unwrap();
        assert_eq!((r, &got), (0, &want1), "other owner");
        let (_, r) = gm.prefill_cached(&q1, sys.len(), s1.len()).unwrap();
        assert_eq!(r, s1.len(), "other owner, its own history");
        gm.owner = 0;
        let (got, r) = gm.prefill_cached(&p2, 0, h2.len()).unwrap();
        assert_eq!((r, &got), (h2.len(), &want_h2), "owner 0 parked");
    }
}

/// qwen4exp (hyper-connections, PLE) on the GPU against the CPU reference: token by token, then the same prompt as one
/// batched forward after `reset`, then as a chunked prefill (last logits only).
#[test]
fn qwen4exp_gpu_matches_cpu() {
    let _gpu = common::gpu_lock();
    let p = std::path::Path::new("/mnt/ollama/qwen4exp/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf");
    if !p.exists() { return }
    let g = Gguf::open(p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let ids = tok.encode("The capital of France is Paris. The capital of").unwrap();
    let mut st = State::new(&m.cfg);
    let want: Vec<Vec<f32>> = ids.iter().map(|&t| m.step(&mut st, t)).collect();
    for (bk, gpu) in common::backends() {
        // Prefill chunks of 4 tokens: several chunks carry the recurrent, KV and PLE state between them.
        let mut gm = GpuModel::load(&m, gpu, 256, 4, 512 << 20, 0).unwrap();
        let mut got: Vec<Vec<f32>> = ids.iter().map(|&t| gm.step(t).unwrap()).collect();
        gm.reset().unwrap();
        let n = ids.len().min(rusting_strata::cpu_worker::TMAX);
        got.extend(gm.verify(&ids[..n]).unwrap());
        gm.reset().unwrap();
        gm.short = 0;
        got.push(gm.prefill(&ids).unwrap());
        for (i, (g, w)) in got.iter().zip(want.iter().chain(&want[..n]).chain(want.last())).enumerate() {
            let range = w.iter().fold(f32::MIN, |a, &b| a.max(b)) - w.iter().fold(f32::MAX, |a, &b| a.min(b));
            let diff = g.iter().zip(w).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
            eprintln!("{bk} row {i}: argmax {} vs {}, max |dlogit| {diff:.4} (range {range:.2})", ops::argmax(g), ops::argmax(w));
            // A different argmax only on a near tie (the first token's logits are flat).
            assert!(w[ops::argmax(g)] >= w[ops::argmax(w)] - 2.0 * diff, "row {i}");
            assert!(diff <= 0.1 * range, "row {i}: {diff} vs range {range}");
        }
    }
}

/// A model split over two devices (here the same GPU opened twice) gives the same logits as one device: steps, a
/// batched verify and a chunked prefill. No expert slots, so both runs compute every expert on the CPU.
#[test]
fn split_matches_single() {
    let _gpu = common::gpu_lock();
    let models = [
        common::model_path(),
        Some("/home/vasylt/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf".into()),
        Some("/mnt/ollama/qwen4exp/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf".into()),
    ];
    // SAFETY: the GPU lock serializes every test that loads a model, the only readers of this variable.
    unsafe { std::env::set_var("STRATA_EXPERT_MB", "0") };
    for p in models.into_iter().flatten().filter(|p: &std::path::PathBuf| p.exists()) {
        let g = Gguf::open(&p).unwrap();
        let m = Model::load(&g).unwrap();
        let tok = Tokenizer::from_gguf(&g).unwrap();
        let ids = tok.encode("The capital of France is Paris, and the capital of Spain is").unwrap();
        let n = ids.len().min(rusting_strata::cpu_worker::TMAX);
        for bk in ["cuda", "vulkan"] {
            let open = || -> Option<Box<dyn rusting_strata::backend::Backend>> {
                Some(match bk { "cuda" => Box::new(rusting_strata::cuda::Gpu::new(0).ok()?), _ => Box::new(rusting_strata::vulkan::Vk::new(0).ok()?) })
            };
            let Some(one) = open() else { continue };
            let run = |gm: &mut GpuModel| -> Vec<Vec<f32>> {
                gm.adapt_every = 0;
                let mut out: Vec<Vec<f32>> = ids.iter().map(|&t| gm.step(t).unwrap()).collect();
                gm.reset().unwrap();
                out.extend(gm.verify(&ids[..n]).unwrap());
                gm.reset().unwrap();
                gm.short = 0;
                out.push(gm.prefill(&ids).unwrap());
                // prefill_cached: a fresh prompt with a system prefix, decode steps, then the same prompt again, which
                // restores the stashed history on every part.
                gm.reset().unwrap();
                let h = ids.len() - 2;
                for _ in 0..2 {
                    out.push(gm.prefill_cached(&ids, 3, h).unwrap().0);
                    for t in [11u32, 22] { out.push(gm.step(t).unwrap()); }
                }
                out
            };
            let want = run(&mut GpuModel::load(&m, one, 256, 4, 512 << 20, 0).unwrap());
            let mut gm = GpuModel::load_split(&m, vec![open().unwrap(), open().unwrap()], 256, 4, 512 << 20, 0, 1).unwrap();
            assert_eq!(gm.parts().count(), 2);
            let got = run(&mut gm);
            for (i, (g, w)) in got.iter().zip(&want).enumerate() {
                let diff = g.iter().zip(w).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
                eprintln!("{} {bk} row {i}: argmax {} vs {}, max |dlogit| {diff}", p.display(), ops::argmax(g), ops::argmax(w));
                assert_eq!(g, w, "row {i}");
            }
        }
    }
    unsafe { std::env::remove_var("STRATA_EXPERT_MB") };
}

/// QSA sparse attention on the GPU (top_k lowered to 8 cells so a short prompt runs sparse) against the CPU reference:
/// token by token, a prefill in chunks of 4 (the incomplete block crosses chunks) and in one chunk, each followed by
/// a 4-row verify. Near-tied block scores can pick differently, so the bound is on the mean error: 0.037 of the logit
/// range on CUDA, against 0.039 for dense attention (top_k 0) on the same prompt.
#[test]
fn qwen4exp_qsa_gpu_matches_cpu() {
    let _gpu = common::gpu_lock();
    let p = std::path::Path::new("/mnt/ollama/qwen4exp/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf");
    if !p.exists() { return }
    let g = Gguf::open(p).unwrap();
    let mut m = Model::load(&g).unwrap();
    m.cfg.idx_top_k = 8;
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let ids = tok.encode("The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. \
        Once upon a time, in a small village").unwrap();
    let mut st = State::new(&m.cfg);
    let want: Vec<Vec<f32>> = ids.iter().map(|&t| m.step(&mut st, t)).collect();
    let (k, n) = (ids.len() - 4, ids.len());
    for chunk in [4, 64] {
        for (bk, gpu) in common::backends() {
            let mut gm = GpuModel::load(&m, gpu, 256, chunk, 512 << 20, 0).unwrap();
            let mut got: Vec<Vec<f32>> = ids.iter().map(|&t| gm.step(t).unwrap()).collect();
            let mut rows: Vec<usize> = (0..n).collect();
            gm.reset().unwrap();
            gm.short = 0;
            got.push(gm.prefill(&ids[..k]).unwrap());
            got.extend(gm.verify(&ids[k..]).unwrap());
            rows.extend(k - 1..n);
            let mut err = 0f32;
            for (i, (g, &r)) in got.iter().zip(&rows).enumerate() {
                let w = &want[r];
                let range = w.iter().fold(f32::MIN, |a, &b| a.max(b)) - w.iter().fold(f32::MAX, |a, &b| a.min(b));
                let diff = g.iter().zip(w).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
                eprintln!("{bk} chunk {chunk} row {i} (pos {r}): argmax {} vs {}, max |dlogit| {diff:.4} (range {range:.2})",
                          ops::argmax(g), ops::argmax(w));
                assert!(diff <= 0.2 * range, "row {i}: {diff} vs range {range}");
                err += diff / range / got.len() as f32;
            }
            assert!(err < 0.05, "{bk} chunk {chunk}: mean relative error {err}");
        }
    }
}

/// `step_rows` over several slots matches each sequence run alone in one slot: prefill per slot, then decode steps with
/// all slots in one forward, with a subset of the slots, and with one slot through `step`. Each row of the batched
/// forward does the same arithmetic as a single token, so the logits match bit for bit.
#[test]
fn slots_match_single() {
    let _gpu = common::gpu_lock();
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let m = Model::load(&g).unwrap();
    let tok = Tokenizer::from_gguf(&g).unwrap();
    let prompts: Vec<Vec<u32>> = ["The capital of France is", "def fib(n):\n    return", "Once upon a time, in a small village by the sea, there"]
        .iter().map(|s| tok.encode(s).unwrap()).collect();
    // Which slots decode at each step; the last one decodes slot 1 alone through `step`.
    let plan: [&[usize]; 6] = [&[0, 1, 2], &[0, 1, 2], &[0, 2], &[1, 2], &[0, 1, 2], &[1]];
    let open = |bk: &str| -> Option<Box<dyn rusting_strata::backend::Backend>> {
        match bk {
            "cuda" => rusting_strata::cuda::Gpu::new(0).ok().map(|g| Box::new(g) as _),
            _ => rusting_strata::vulkan::Vk::new(0).ok().map(|g| Box::new(g) as _),
        }
    };
    // All experts on the CPU, then the default placement, then the layers split in two parts (on the same GPU).
    for (cpu, bk, split) in [(true, false), (false, false), (false, true)].into_iter().flat_map(|(c, sp)| ["cuda", "vulkan"].map(move |b| (c, b, sp))) {
        // SAFETY: the GPU lock serializes every test that loads a model, the only readers of this variable.
        if cpu { unsafe { std::env::set_var("STRATA_EXPERT_MB", "0") } } else { unsafe { std::env::remove_var("STRATA_EXPERT_MB") } }
        let Some(gpu) = open(bk) else { continue };
        let mut gm = if split {
            GpuModel::load_split(&m, vec![gpu, open(bk).unwrap()], 256, 4, 512 << 20, 0, 3).unwrap()
        } else {
            GpuModel::load_slots(&m, gpu, 256, 4, 512 << 20, 3).unwrap()
        };
        gm.adapt_every = 0;
        // Reference: each prompt alone in slot 0, greedy, as many steps as the plan gives its slot. The placement is
        // fixed (no adaptation), so only the batching differs.
        let mut want: Vec<Vec<Vec<f32>>> = vec![];
        let mut toks: Vec<Vec<u32>> = vec![];
        for (s, ids) in prompts.iter().enumerate() {
            gm.reset().unwrap();
            let mut l = vec![gm.prefill(ids).unwrap()];
            let mut t = vec![];
            for _ in plan.iter().filter(|r| r.contains(&s)) {
                t.push(ops::argmax(l.last().unwrap()) as u32);
                l.push(gm.step(*t.last().unwrap()).unwrap());
            }
            want.push(l);
            toks.push(t);
        }
        let mut got: Vec<Vec<Vec<f32>>> = vec![vec![]; 3];
        for (s, ids) in prompts.iter().enumerate() {
            gm.use_slot(s);
            gm.reset().unwrap();
            got[s].push(gm.prefill(ids).unwrap());
        }
        for (i, rows) in plan.iter().enumerate() {
            let rt: Vec<(usize, u32)> = rows.iter().map(|&s| (s, toks[s][got[s].len() - 1])).collect();
            if i == plan.len() - 1 {
                gm.use_slot(rows[0]);
                got[rows[0]].push(gm.step(rt[0].1).unwrap());
            } else {
                // Every other row asks for its logits; all rows return their argmax.
                let rl: Vec<(usize, u32, bool)> = rt.iter().enumerate().map(|(i, &(s, t))| (s, t, i % 2 == 0)).collect();
                let out = gm.step_rows(&rl).unwrap();
                for (&(s, _, wl), (t, l)) in rl.iter().zip(out) {
                    let w = &want[s][got[s].len()];
                    assert_eq!(t, ops::argmax(w) as u32, "{bk} cpu experts {cpu} split {split} slot {s}: greedy token");
                    got[s].push(if wl { l } else { assert!(l.is_empty()); w.clone() });
                }
            }
        }
        // Decode steps of slot 0 between the prefill chunks of slot 1 (`serve --parallel`) change neither.
        gm.short = 1;
        let run = |gm: &mut GpuModel, inter: bool| {
            gm.use_slot(0);
            gm.reset().unwrap();
            let mut t = ops::argmax(&gm.prefill(&prompts[0]).unwrap()) as u32;
            gm.use_slot(1);
            gm.reset().unwrap();
            let mut l0 = vec![];
            let mut dec = |g: &mut GpuModel| -> anyhow::Result<()> {
                let l = g.step_rows(&[(0, t, true)])?.pop().unwrap().1;
                t = ops::argmax(&l) as u32;
                l0.push(l);
                Ok(())
            };
            let l1 = if inter { gm.prefill_with(&prompts[2], &mut dec).unwrap() } else {
                for _ in 0..prompts[2].len().div_ceil(4) - 1 { dec(gm).unwrap(); }
                gm.prefill(&prompts[2]).unwrap()
            };
            (l0, l1)
        };
        let (want0, want1) = run(&mut gm, false);
        let (got0, got1) = run(&mut gm, true);
        assert!(want0.len() >= 2, "{bk}: prompt fits one chunk");
        assert!(got0 == want0 && got1 == want1, "{bk} cpu experts {cpu} split {split}: decode between prefill chunks");
        gm.short = 32;
        // A conversation parked in slot 0 continues in slot 2, which never saved a state (split models do not park).
        if !split {
            gm.cache_ram = 1 << 30;
            gm.use_slot(0);
            let (a, b) = (&prompts[2], &prompts[1]);
            let long: Vec<u32> = a.iter().chain(b).copied().collect();
            gm.prefill_cached(a, 0, a.len() - 1).unwrap();
            gm.prefill_cached(b, 0, b.len() - 1).unwrap();
            gm.use_slot(2);
            let (l, reused) = gm.prefill_cached(&long, 0, long.len() - 1).unwrap();
            assert_eq!(reused, a.len() - 1, "{bk}: parked state not taken back");
            gm.reset().unwrap();
            assert_eq!(l, gm.prefill(&long).unwrap(), "{bk}: unparked state");
        }
        for s in 0..3 {
            assert_eq!(got[s].len(), want[s].len());
            for (i, (g, w)) in got[s].iter().zip(&want[s]).enumerate() {
                let diff = g.iter().zip(w).fold(0f32, |a, (x, y)| a.max((x - y).abs()));
                eprintln!("{bk} cpu experts {cpu} split {split} slot {s} row {i}: argmax {} vs {}, max |dlogit| {diff}", ops::argmax(g), ops::argmax(w));
                assert_eq!(g, w, "{bk} cpu experts {cpu} split {split} slot {s} row {i}");
            }
        }
    }
    unsafe { std::env::remove_var("STRATA_EXPERT_MB") };
}
