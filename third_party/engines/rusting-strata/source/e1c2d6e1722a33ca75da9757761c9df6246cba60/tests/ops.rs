use rusting_strata::ops::*;

#[test]
fn rms() {
    let mut o = [0f32; 2];
    rms_norm(&[3.0, 4.0], &[1.0, 2.0], 0.0, &mut o);
    let s = 12.5f32.sqrt();
    assert!((o[0] - 3.0 / s).abs() < 1e-6 && (o[1] - 8.0 / s).abs() < 1e-6);
}
#[test]
fn l2() {
    let mut x = [3.0, 4.0];
    l2_norm(&mut x, 1e-6);
    assert!((x[0] - 0.6).abs() < 1e-6);
}
#[test]
fn softplus_values() {
    assert!((softplus(30.0) - 30.0).abs() < 1e-5);
    assert!((softplus(0.0) - 2f32.ln()).abs() < 1e-6);
}
#[test]
fn rope_pos0_identity() {
    let mut x: Vec<f32> = (0..8).map(|i| i as f32).collect();
    let y = x.clone();
    rope_neox(&mut x, 4, 0, 1e7);
    assert_eq!(x, y);
}
#[test]
fn rope_rotates_pairs() {
    let mut x = vec![1.0, 0.0, 0.0, 0.0, 9.0]; // n_rot 4: pairs (0,2), (1,3)
    rope_neox(&mut x, 4, 1, 10000.0); // theta0 = 1 rad
    assert!((x[0] - 1f32.cos()).abs() < 1e-6 && (x[2] - 1f32.sin()).abs() < 1e-6 && x[4] == 9.0);
}
#[test]
fn topk() { assert_eq!(top_k(&[0.1, 0.5, 0.2, 0.5], 2), vec![1, 3]); }
#[test]
fn softmax_sums_to_one() {
    let mut x = [1.0, 2.0, 3.0];
    softmax(&mut x);
    assert!((x.iter().sum::<f32>() - 1.0).abs() < 1e-6 && x[2] > x[1]);
}
#[test]
fn sampler_cuts_and_matches_softmax() {
    let l = [2.0f32.ln(), 1.0f32.ln(), 1.0f32.ln(), -50.0]; // probabilities 1/2, 1/4, 1/4, ~0
    assert_eq!(Sampler::greedy().pick(&l).unwrap(), 0);
    let mut s = Sampler { temp: 1.0, top_k: 0, top_p: 1.0, rng: 7 };
    let mut n = [0usize; 4];
    for _ in 0..20000 { n[s.pick(&l).unwrap()] += 1; }
    assert!(n[3] == 0 && (n[0] as f32 / 20000.0 - 0.5).abs() < 0.02 && (n[1] as f32 / 20000.0 - 0.25).abs() < 0.02, "{n:?}");
    let mut s = Sampler { temp: 1.0, top_k: 0, top_p: 0.5, rng: 7 };
    assert!((0..100).all(|_| s.pick(&l).unwrap() == 0));
    let mut s = Sampler { temp: 1.0, top_k: 2, top_p: 1.0, rng: 7 };
    assert!((0..100).all(|_| s.pick(&l).unwrap() < 2));
    // A temperature so small that m - 21 * temp rounds to m must still keep the best token.
    let mut s = Sampler { temp: 1e-9, top_k: 0, top_p: 1.0, rng: 7 };
    assert_eq!(s.pick(&[1.0, 10.0, 3.0]).unwrap(), 1);
    // Logits with no finite value are an error, not a panic, sampled or greedy.
    let bad = [f32::NAN, f32::INFINITY, f32::NAN];
    assert!(s.pick(&bad).is_err() && s.accept(&bad, 0).is_err() && Sampler::greedy().pick(&bad).is_err());
}
#[test]
fn sampler_accept_keeps_the_distribution() {
    // Keeping draft d with its probability, else drawing from the rest, must give the probabilities of `pick`, for a
    // likely draft, an unlikely one and one outside the candidates.
    let l = [2.0f32.ln(), 1.0f32.ln(), 1.0f32.ln(), -50.0]; // 1/2, 1/4, 1/4, ~0
    for d in [0, 1, 3] {
        let mut s = Sampler { temp: 1.0, top_k: 0, top_p: 1.0, rng: 7 };
        let mut n = [0usize; 4];
        for _ in 0..40000 { n[s.accept(&l, d).unwrap().unwrap_or(d)] += 1; }
        let f = |i: usize| n[i] as f32 / 40000.0;
        assert!(n[3] == 0 && (f(0) - 0.5).abs() < 0.015 && (f(1) - 0.25).abs() < 0.015, "d {d}: {n:?}");
    }
}
