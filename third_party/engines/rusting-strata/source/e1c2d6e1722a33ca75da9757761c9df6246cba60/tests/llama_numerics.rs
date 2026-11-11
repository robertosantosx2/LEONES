//! `--llama-numerics` kernels. A separate test binary: the mode is read from the environment when a `Gpu` compiles its
//! kernels, so setting it here cannot leak into the other GPU tests.
mod common;
use common::{down, up};
use rusting_strata::backend::Backend;
use rusting_strata::cuda::{ATT_GQA_MIN, ATT_SPLITS, Gpu};

fn xs(n: usize) -> Vec<f32> {
    (0..n).map(|i| ((i as f32 * 0.7548777).fract() - 0.5) * 2.0).collect()
}

fn rel_l2(a: &[f32], b: &[f32]) -> f32 {
    let num: f32 = a.iter().zip(b).map(|(x, y)| (x - y) * (x - y)).sum();
    let den: f32 = b.iter().map(|y| y * y).sum();
    (num / den.max(1e-30)).sqrt()
}

fn rh(x: f32) -> f32 { half::f16::from_f32(x).to_f32() }

/// llama.cpp's CPU decode attention (flash_attn_ext_f16_one_chunk with 6 threads, then reduce_partials), gated.
fn llama_attn(q: &[f32], kc: &[u16], vc: &[u16], qg: &[f32], n_pos: usize, nh: usize, nkv: usize, hd: usize, scale: f32) -> Vec<f32> {
    let f = |b: u16| half::f16::from_bits(b).to_f32();
    let n_kv = n_pos.div_ceil(256) * 256;
    let nc = if n_kv >= 512 { 6 } else { 1 };
    let cs = n_kv.div_ceil(nc);
    let mut out = vec![0f32; nh * hd];
    for h in 0..nh {
        let g = h / (nh / nkv);
        let qh: Vec<f32> = q[h * hd..][..hd].iter().map(|&x| rh(x)).collect();
        let (mut mf, mut sf, mut vf) = (f32::NEG_INFINITY, 0f32, vec![0f32; hd]);
        for c in 0..nc {
            let (p0, p1) = (c * cs, n_pos.min(c * cs + cs));
            if p0 >= p1 { continue; }
            let (mut m, mut l, mut acc) = (f32::NEG_INFINITY, 0f32, vec![0f32; hd]);
            for t in p0..p1 {
                let r = (t * nkv + g) * hd;
                let s = (0..hd).map(|d| qh[d] * f(kc[r + d])).sum::<f32>() * scale;
                let (mut ms, mut vs) = (1f32, 1f32);
                if s > m { ms = (m - s).exp(); m = s; acc.iter_mut().for_each(|a| *a = rh(*a * ms)); } else { vs = (s - m).exp(); }
                for d in 0..hd { acc[d] = rh(f(vc[r + d]).mul_add(vs, acc[d])); }
                l = l * ms + vs;
            }
            let mn = mf.max(m);
            let (so, sn) = ((mf - mn).exp(), (m - mn).exp());
            for d in 0..hd { vf[d] = vf[d] * so + acc[d] * sn; }
            sf = sf * so + l * sn;
            mf = mn;
        }
        for d in 0..hd { out[h * hd + d] = vf[d] / sf / (1.0 + (-qg[h * 2 * hd + hd + d]).exp()); }
    }
    out
}

/// One test owns both Gpus: the environment variable set here would leak into a parallel test's default Gpu.
#[test]
fn llama_mode_attention() {
    let base = match Gpu::new(0) {
        Ok(g) => g,
        Err(e) if format!("{e}") == "CUDA init" => { eprintln!("SKIP: no GPU: {e:#}"); return }
        Err(e) => panic!("{e:#}"),
    };
    unsafe { std::env::set_var("STRATA_LLAMA_NUMERICS", "1") }
    let llama = Gpu::new(0).unwrap();
    // Vulkan in llama mode must give CUDA's llama-mode bits.
    let vk = match rusting_strata::vulkan::Vk::new(0) {
        Ok(v) => Some(v),
        Err(e) if format!("{e}") == "Vulkan init" => { eprintln!("SKIP: vulkan: {e:#}"); None }
        Err(e) => panic!("{e:#}"),
    };
    let vk = vk.as_ref().map(|v| v as &dyn Backend);
    attn_decode_matches_llama_cpu(&base, &llama, vk);
    attn_prefill_is_f32(&base, &llama, vk);
}

fn diff_bits(a: &[f32], b: &[f32]) -> usize { a.iter().zip(b).filter(|(x, y)| x.to_bits() != y.to_bits()).count() }

fn attn_decode_matches_llama_cpu(base: &dyn Backend, llama: &dyn Backend, vk: Option<&dyn Backend>) {
    let h16 = |v: Vec<f32>| -> Vec<u16> { v.iter().map(|x| half::f16::from_f32(*x).to_bits()).collect() };
    let (nh, nkv, hd) = (16, 2, 256);
    let max_pos = 1400;
    let n = max_pos * nkv * hd;
    let (kc, vc) = (h16(xs(n)), h16(xs(n + 5)[5..].to_vec()));
    let q: Vec<f32> = xs(nh * hd + 3)[3..].iter().map(|v| 4.0 * v).collect();
    let qg = xs(nh * 2 * hd);
    let scale = 1.0 / (hd as f32).sqrt();
    let run = |gpu: &dyn Backend, n_pos: usize, gq_min: i32| -> Vec<f32> {
        let (dk, dv, dq, dg) = (up(gpu, &kc), up(gpu, &vc), up(gpu, &q), up(gpu, &qg));
        let step = up(gpu, &[n_pos as i32 - 1, 0]);
        let (dout, part) = (up(gpu, &vec![0f32; nh * hd]), up(gpu, &vec![0f32; nh * ATT_SPLITS * (hd + 2)]));
        gpu.attn_decode_gq(dq.addr(), dk.addr(), dv.addr(), dg.addr(), dout.addr(), part.addr(), step.addr(),
                           nh, nkv, hd, scale, gq_min, 1).unwrap();
        down(gpu, &dout)
    };
    for n_pos in [7, 300, 511, 512, 1400] {
        let want = llama_attn(&q, &kc, &vc, &qg, n_pos, nh, nkv, hd, scale);
        for gq_min in [ATT_GQA_MIN, 0] {
            let (got, f32_path) = (run(llama, n_pos, gq_min), run(base, n_pos, gq_min));
            let (e, e0) = (rel_l2(&got, &want), rel_l2(&f32_path, &want));
            eprintln!("n_pos {n_pos} gq_min {gq_min}: llama mode vs CPU model {e:.2e}, default kernel vs CPU model {e0:.2e}");
            assert!(e <= e0 / 4.0, "n_pos {n_pos} gq_min {gq_min}: rel err {e}");
            if let Some(vk) = vk {
                let nd = diff_bits(&run(vk, n_pos, gq_min), &got);
                assert_eq!(nd, 0, "vulkan n_pos {n_pos} gq_min {gq_min}: {nd} values differ from cuda");
            }
        }
    }
}

/// Prefill attention in llama mode is f32 (llama.cpp's CPU tiled path), so it lands far closer to an f64 reference
/// than the f16 tensor-core kernel.
fn attn_prefill_is_f32(base: &dyn Backend, llama: &dyn Backend, vk: Option<&dyn Backend>) {
    let h16 = |v: Vec<f32>| -> Vec<u16> { v.iter().map(|x| half::f16::from_f32(*x).to_bits()).collect() };
    let f = |b: u16| half::f16::from_bits(b).to_f32() as f64;
    let (pos0, t) = (5, 100);
    for (nh, nkv, hd) in [(4, 2, 64), (4, 2, 128), (16, 2, 256)] {
        let n = (pos0 + t) * nkv * hd;
        let (kc, vc) = (h16(xs(n)), h16(xs(n + 5)[5..].to_vec()));
        let q: Vec<f32> = xs(t * nh * hd + 3)[3..].iter().map(|v| 4.0 * v).collect();
        let qg = xs(t * nh * 2 * hd);
        let scale = 1.0 / (hd as f32).sqrt();
        let mut want = vec![0f32; t * nh * hd];
        for i in 0..t {
            for h in 0..nh {
                let g = h / (nh / nkv);
                let s: Vec<f64> = (0..=pos0 + i).map(|p| (0..hd).map(|d| q[(i * nh + h) * hd + d] as f64 * f(kc[(p * nkv + g) * hd + d])).sum::<f64>() * scale as f64).collect();
                let mx = s.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                let e: Vec<f64> = s.iter().map(|x| (x - mx).exp()).collect();
                let l: f64 = e.iter().sum();
                for d in 0..hd {
                    let o: f64 = e.iter().enumerate().map(|(p, w)| w * f(vc[(p * nkv + g) * hd + d])).sum::<f64>() / l;
                    want[(i * nh + h) * hd + d] = (o / (1.0 + (-qg[(i * nh + h) * 2 * hd + hd + d] as f64).exp())) as f32;
                }
            }
        }
        let run = |gpu: &dyn Backend| -> Vec<f32> {
            let (dk, dv, dq, dg) = (up(gpu, &kc), up(gpu, &vc), up(gpu, &q), up(gpu, &qg));
            let (step, dout) = (up(gpu, &[pos0 as i32]), up(gpu, &vec![0f32; t * nh * hd]));
            gpu.attn_prefill(dq.addr(), dk.addr(), dv.addr(), dg.addr(), dout.addr(), step.addr(), t, nh, nkv, hd, scale).unwrap();
            down(gpu, &dout)
        };
        let got = run(llama);
        if let Some(vk) = vk {
            let nd = diff_bits(&run(vk), &got);
            assert_eq!(nd, 0, "vulkan prefill hd {hd}: {nd} values differ from cuda");
        }
        let (e, e0) = (rel_l2(&got, &want), rel_l2(&run(base), &want));
        eprintln!("prefill hd {hd}: llama mode vs f64 {e:.2e}, tensor-core kernel vs f64 {e0:.2e}");
        assert!(e <= 1e-6 && e <= e0 / 10.0, "hd {hd}: rel err {e} (tensor cores {e0})");
    }
}

