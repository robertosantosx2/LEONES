//! Kernel tests, run on every backend that opens (`common::backends`).
mod common;
use common::{down, up};
use rusting_strata::backend::{Backend, ATT_GQA_MIN, ATT_SPLITS, GEMM_BM, GpuTensor, SAME_X};
use rusting_strata::{cuda::Gpu, gguf::Gguf, quant::GgmlType, weights::{Tensor, Weights}};

fn xs(n: usize) -> Vec<f32> {
    (0..n).map(|i| ((i as f32 * 0.7548777).fract() - 0.5) * 2.0).collect()
}

/// x as the integer GEMV path sees it: int8 per 32 elements with scale max|x| / 127 (float weight types read x as is).
fn as_seen(ty: GgmlType, x: &[f32]) -> Vec<f32> {
    if matches!(ty, GgmlType::F32 | GgmlType::BF16) { return x.to_vec(); }
    x.chunks(32).flat_map(|b| {
        let mx = b.iter().fold(0f32, |m, v| m.max(v.abs()));
        let id = if mx > 0.0 { 127.0 / mx } else { 0.0 };
        b.iter().map(move |v| (v * id).round_ties_even() * (mx / 127.0))
    }).collect()
}

fn rel_l2(a: &[f32], b: &[f32]) -> f32 {
    let num: f32 = a.iter().zip(b).map(|(x, y)| (x - y) * (x - y)).sum();
    let den: f32 = b.iter().map(|y| y * y).sum();
    (num / den.max(1e-30)).sqrt()
}

#[test]
fn dequant_and_gemv_match_reference_for_every_type() {
    let Some(p) = common::model_path() else { return };
    let mut first = std::collections::HashMap::new();  // gemv outputs of the first backend, to count bit differences
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        let mut seen = std::collections::BTreeSet::new();
        for (name, info) in &g.tensors {
            let Ok(ty) = GgmlType::from_u32(info.ty) else { continue };
            if info.dims.len() < 2 || info.dims[0] % 256 != 0 || !seen.insert(ty.name()) { continue; }
            let t = w.get(name).unwrap();
            let dt = gpu.upload(&t).unwrap();
            let rows = 4.min(t.rows);
            let dq = gpu.zeros::<f32>(rows * t.cols).unwrap();
            gpu.dequant(&dt, rows, dq.addr()).unwrap();
            let got = down::<f32>(gpu, &dq);
            let mut want = vec![0f32; rows * t.cols];
            for (r, out) in want.chunks_exact_mut(t.cols).enumerate() { t.row(r, out); }
            let scale = want.iter().fold(0f32, |m, v| m.max(v.abs()));
            let diff = got.iter().zip(&want).fold(0f32, |m, (a, b)| m.max((a - b).abs()));
            assert!(diff <= 1e-5 * scale, "{} dequant ({name}): max diff {diff} vs scale {scale}", ty.name());

            let x = xs(t.cols);
            let dx = up(gpu, &x);
            let dy = gpu.zeros::<f32>(t.rows).unwrap();
            match gpu.gemv(&dt, dx.addr(), dy.addr()) {
                Err(e) if e.to_string().contains("not implemented") => { eprintln!("{:8} {name}: dequant max diff {diff:.2e}, {e}", ty.name()); continue }
                r => r.unwrap(),
            }
            let got = down::<f32>(gpu, &dy);
            let mut want = vec![0f32; t.rows];
            t.matvec(&as_seen(ty, &x), &mut want);
            let e = rel_l2(&got, &want);
            let bits = first.get(name).map_or(String::new(), |f: &Vec<f32>| {
                format!(", {} of {} differ from the first backend", got.iter().zip(f).filter(|(a, b)| a.to_bits() != b.to_bits()).count(), f.len())
            });
            eprintln!("{:8} {name}: dequant max diff {diff:.2e}, gemv rel err {e:.2e}{bits}", ty.name());
            assert!(e <= 1e-4, "{} gemv ({name}): rel err {e}", ty.name());
            first.entry(name.clone()).or_insert(got);
        }
        assert!(seen.len() >= 10 || !common::is_default_model(&p), "types covered: {seen:?}");
    }
}

#[test]
fn rms_norm_q_matches_quant_xq() {
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (n, rows) = (2048, 3);
        let (x, w) = (up(gpu, &xs(rows * n)), up(gpu, &xs(n + 7)[7..]));
        let (out, q1, q2) = (gpu.zeros::<f32>(rows * n).unwrap(), gpu.zeros::<u8>(rows * n * 9 / 8).unwrap(), gpu.zeros::<u8>(rows * n * 9 / 8).unwrap());
        gpu.rms_norm_q(x.addr(), n, w.addr(), out.addr(), n, n, rows, 1e-6, q1.addr(), 0).unwrap();
        gpu.quant_xq(out.addr(), n, n, rows, q2.addr()).unwrap();
        assert_eq!(down::<u8>(gpu, &q1), down::<u8>(gpu, &q2));
        // With res: the same bits as add, then rms_norm_q.
        let (x2, r, out2) = (up(gpu, &xs(rows * n)), up(gpu, &xs(rows * n + 3)[3..]), gpu.zeros::<f32>(rows * n).unwrap());
        gpu.add(x.addr(), r.addr(), rows * n).unwrap();
        gpu.rms_norm_q(x.addr(), n, w.addr(), out.addr(), n, n, rows, 1e-6, q1.addr(), 0).unwrap();
        gpu.rms_norm_q(x2.addr(), n, w.addr(), out2.addr(), n, n, rows, 1e-6, q2.addr(), r.addr()).unwrap();
        let bits = |b| down::<f32>(gpu, b).iter().map(|v| v.to_bits()).collect::<Vec<_>>();
        assert_eq!(bits(&x), bits(&x2));
        assert_eq!(bits(&out), bits(&out2));
        assert_eq!(down::<u8>(gpu, &q1), down::<u8>(gpu, &q2));
    }
}

#[test]
fn moe_gemv_selects_experts() {
    let Some(p) = common::model_path() else { return };
    let mut first = None;
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        let Some(info) = g.tensors.get("blk.0.ffn_gate_exps.weight") else { return };  // dense model
        let t = w.get("blk.0.ffn_gate_exps.weight").unwrap();
        let n_expert = info.dims[2] as usize;
        let dt = gpu.upload(&t).unwrap();
        let ids = [3i32, -1, n_expert as i32 - 1];  // the last expert: 255 on the default model, 127 on Qwen3-30B
        let x = xs(t.cols);
        let (di, dx) = (up(gpu, &ids), up(gpu, &x));
        let rows = t.rows / n_expert;
        let dy = gpu.zeros::<f32>(3 * rows).unwrap();
        gpu.moe_gemv(t.ty, rows, t.cols, dt.ptr, dt.bytes() / n_expert, di.addr(), 3, dx.addr(), 0, 1, dy.addr(), None, 0).unwrap();
        let got = down::<f32>(gpu, &dy);
        let mut want_all = vec![0f32; 3 * rows];
        for (k, &e) in ids.iter().enumerate() {
            let mut want = vec![0f32; rows];
            if e >= 0 { t.expert(e as usize, n_expert).matvec(&as_seen(t.ty, &x), &mut want); }
            else { assert!(got[k * rows..(k + 1) * rows].iter().all(|&v| v == 0.0), "skipped slot written"); continue; }
            let err = rel_l2(&got[k * rows..(k + 1) * rows], &want);
            assert!(err <= 1e-4, "expert {e}: rel err {err}");
            want_all[k * rows..(k + 1) * rows].copy_from_slice(&want);
        }
        // Measurement only (M2-T7): the CPU figure and the differing bits from the first backend.
        let nd = first.as_ref().map_or(0, |f: &Vec<u32>| got.iter().zip(f).filter(|(a, b)| a.to_bits() != **b).count());
        eprintln!("op moe_gemv {bk} [3 experts {}x{} {}]: rel err vs CPU {:.2e}, {} of {} differ from the first backend",
                  rows, t.cols, t.ty.name(), rel_l2(&got, &want_all), nd, got.len());
        // The paired launch (gate and up in one) matches a separate launch of the up matrices bit for bit.
        let u = gpu.upload(&w.get("blk.0.ffn_up_exps.weight").unwrap()).unwrap();
        let (dg, du) = (gpu.zeros::<f32>(3 * rows).unwrap(), gpu.zeros::<f32>(3 * rows).unwrap());
        let pair = (u.ptr as i64 - dt.ptr as i64, du.addr() as i64 - dg.addr() as i64);
        gpu.moe_gemv(t.ty, rows, t.cols, dt.ptr, dt.bytes() / n_expert, di.addr(), 3, dx.addr(), 0, 1, dg.addr(), Some(pair), 0).unwrap();
        gpu.moe_gemv(u.ty, rows, u.cols, u.ptr, u.bytes() / n_expert, di.addr(), 3, dx.addr(), 0, 1, dy.addr(), None, 0).unwrap();
        assert_eq!(down::<f32>(gpu, &dg), got, "paired gate");
        assert_eq!(down::<f32>(gpu, &du), down::<f32>(gpu, &dy), "paired up");
        // x quantized once by quant_xq (one token for the 3 experts) gives the same result as per-block quantization.
        let xq = gpu.zeros::<u8>(t.cols * 9 / 8).unwrap();
        gpu.quant_xq(dx.addr(), 0, t.cols, 1, xq.addr()).unwrap();
        gpu.moe_gemv(t.ty, rows, t.cols, dt.ptr, dt.bytes() / n_expert, di.addr(), 3, 0, 0, 3, dg.addr(), Some(pair), xq.addr()).unwrap();
        assert_eq!(down::<f32>(gpu, &dg), got, "quant_xq gate");
        assert_eq!(down::<f32>(gpu, &du), down::<f32>(gpu, &dy), "quant_xq up");
        let bits: Vec<u32> = got.iter().map(|v| v.to_bits()).collect();
        match &first { None => first = Some(bits), Some(f) => assert!(*f == bits, "{bk} differs from the first backend") }
    }
}

/// Achieved GEMV bandwidth per type (one dense matrix per type, plus 8-expert MoE GEMVs). Run with --ignored.
/// gemvn over 1 to 4 inputs equals gemv per input, bit for bit, for every type.
#[test]
fn gemvn_matches_gemv() {
    let Some(p) = common::model_path() else { return };
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        let mut seen = std::collections::BTreeSet::new();
        for (name, info) in &g.tensors {
            let Ok(ty) = GgmlType::from_u32(info.ty) else { continue };
            if info.dims.len() != 2 || info.dims[0] % 256 != 0 || !seen.insert(ty.name()) { continue; }
            let t = w.get(name).unwrap();
            let dt = gpu.upload(&t).unwrap();
            let x: Vec<f32> = (0..4).flat_map(|i| xs(t.cols + i).into_iter().skip(i)).collect();
            let dx = up(gpu, &x);
            let mut want = vec![];
            for i in 0..4u64 {
                let dy = gpu.zeros::<f32>(t.rows).unwrap();
                gpu.gemv(&dt, dx.addr() + 4 * i * t.cols as u64, dy.addr()).unwrap();
                want.extend(down::<f32>(gpu, &dy));
            }
            for nt in 1..=4 {
                let dy = gpu.zeros::<f32>(nt * t.rows).unwrap();
                gpu.gemvn(&dt, dx.addr(), t.cols, dy.addr(), t.rows, nt).unwrap();
                assert_eq!(down::<f32>(gpu, &dy), want[..nt * t.rows], "{} {name} nt {nt}", ty.name());
                let xq = gpu.zeros::<u8>(nt * t.cols * 9 / 8).unwrap();
                gpu.quant_xq(dx.addr(), t.cols, t.cols, nt, xq.addr()).unwrap();
                let dy = gpu.zeros::<f32>(nt * t.rows).unwrap();
                gpu.gemvq(&dt, dx.addr(), t.cols, xq.addr(), dy.addr(), t.rows, nt).unwrap();
                assert_eq!(down::<f32>(gpu, &dy), want[..nt * t.rows], "{} {name} quant_xq nt {nt}", ty.name());
                let dz = gpu.zeros::<f32>(nt * t.rows).unwrap();
                gpu.gemvq2(&dt, &dt, dx.addr(), t.cols, xq.addr(), dy.addr(), dz.addr(), nt).unwrap();
                assert_eq!(down::<f32>(gpu, &dy), want[..nt * t.rows], "{} {name} gemvq2 a nt {nt}", ty.name());
                assert_eq!(down::<f32>(gpu, &dz), want[..nt * t.rows], "{} {name} gemvq2 b nt {nt}", ty.name());
                // A shorter first matrix (its first r2 rows): the pair still covers both.
                let r2 = t.rows.div_ceil(2);
                let dh = gpu.upload(&Tensor { rows: r2, data: &t.data[..t.data.len() / t.rows * r2], ..t }).unwrap();
                let (dy, dz) = (gpu.zeros::<f32>(nt * r2).unwrap(), gpu.zeros::<f32>(nt * t.rows).unwrap());
                gpu.gemvq2(&dh, &dt, dx.addr(), t.cols, xq.addr(), dy.addr(), dz.addr(), nt).unwrap();
                let short: Vec<f32> = want.chunks(t.rows).take(nt).flat_map(|r| r[..r2].to_vec()).collect();
                assert_eq!(down::<f32>(gpu, &dy), short, "{} {name} gemvq2 short nt {nt}", ty.name());
                assert_eq!(down::<f32>(gpu, &dz), want[..nt * t.rows], "{} {name} gemvq2 long nt {nt}", ty.name());
            }
            // As a paired moe_gemv of one slot (expert 0 at stride 0): float types apply the pair offsets too.
            let (zid, dy) = (gpu.zeros::<i32>(1).unwrap(), gpu.zeros::<f32>(2 * t.rows).unwrap());
            let xq = gpu.zeros::<u8>(t.cols * 9 / 8).unwrap();
            gpu.quant_xq(dx.addr(), t.cols, t.cols, 1, xq.addr()).unwrap();
            gpu.moe_gemv(t.ty, t.rows, t.cols, dt.ptr, 0, zid.addr(), 1, dx.addr(), t.cols, 1, dy.addr(), Some((0, 4 * t.rows as i64)), xq.addr()).unwrap();
            let got = down::<f32>(gpu, &dy);
            assert!(got[..t.rows] == want[..t.rows] && got[t.rows..] == want[..t.rows], "{} {name} paired moe_gemv", ty.name());
        }
        assert!(seen.len() >= 5 || !common::is_default_model(&p), "types covered: {seen:?}");
    }
}

/// Peak HBM2 read bandwidth of the V100-SXM2-32GB: 2 x 877 MHz x 4096 bit / 8 = 898.0 GB/s. M2-T5 targets 85 % of
/// it (763 GB/s) on the shapes large enough to stream (issue #30).
const HBM_PEAK_GBS: f64 = 898.0;

/// One row of the per-token decode byte budget of the reference model (issue #30, GGUF tensor table; 100 % expert
/// hit rate, no cross-token L2 reuse, `token_embd.weight` excluded because only one row (~1.2 KB) is read).
struct Budget {
    category: &'static str,
    mb: f64,
    /// Routed experts: the only row the MoE GEMV family streams (19 % of the bytes; the rest is dense GEMV).
    routed: bool,
}

const DECODE_BUDGET: [Budget; 6] = [
    Budget { category: "attention / SSM 2-D", mb: 713.3, routed: false },
    Budget { category: "routed experts, top-8", mb: 329.0, routed: true },
    Budget { category: "output.weight (lm head)", mb: 286.1, routed: false },
    Budget { category: "SSM / delta 2-D", mb: 226.1, routed: false },
    Budget { category: "shared expert (*_shexp)", mb: 92.9, routed: false },
    Budget { category: "router (gate_inp)", mb: 83.9, routed: false },
];

/// GB read per decode token over the budget (MB as 1e6 bytes): `routed` selects the expert row, otherwise dense.
fn budget_gb(routed: bool) -> f64 {
    DECODE_BUDGET.iter().filter(|b| b.routed == routed).map(|b| b.mb).sum::<f64>() / 1000.0
}

/// What a `(rows, cols)` shape of `name` contributes to decode, so the harness's numbers can be read against the
/// byte budget: the lm head and the routed experts drive most of the stream, `token_embd` is not streamed at all.
fn decode_shape(name: &str, rows: usize, cols: usize, moe: bool) -> &'static str {
    if name.starts_with("token_embd") { "embedding (1 row)" }
    else if name.starts_with("output.") || (rows >= 65536 && cols == 2048) { "lm head" }
    else if moe { if cols <= 512 { "moe down" } else { "moe gate/up" } }
    else { "dense attn/ssm" }
}

/// Device-free: the analytic byte budget and roofline of issue #30, so the denominator the GPU harness prints
/// cannot drift from the table the adoption decision uses.
#[test]
fn gemv_byte_budget_matches_issue() {
    let (dense, moe) = (budget_gb(false), budget_gb(true));
    assert!((dense - 1.4023).abs() < 1e-3, "dense {dense}");
    assert!((moe - 0.3290).abs() < 1e-3, "routed {moe}");
    let total = dense + moe;
    assert!((total - 1.7313).abs() < 1e-3, "total {total}");
    assert!((100.0 * dense / total - 81.0).abs() < 0.1);
    assert!((100.0 * moe / total - 19.0).abs() < 0.1);
    // 898.0 GB/s over 1.7313 GB/token, and the 85 % per-kernel target.
    assert!((HBM_PEAK_GBS / total - 518.7).abs() < 0.5, "roofline {} tok/s", HBM_PEAK_GBS / total);
    assert!((0.85 * HBM_PEAK_GBS / total - 440.9).abs() < 0.5);
    // The 119.1 tok/s baseline of docs/V100-results.md implies 206.2 GB/s = 23.0 % of the roofline.
    let eff = total * 119.1;
    assert!((eff - 206.2).abs() < 0.5, "effective {eff} GB/s");
    assert!((100.0 * eff / HBM_PEAK_GBS - 23.0).abs() < 0.1);
}

#[test]
#[ignore]
fn gemv_bandwidth() {
    let Some(p) = common::model_path() else { return };
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (dense, moe) = (budget_gb(false), budget_gb(true));
        let total = dense + moe;
        eprintln!("  decode budget/token (issue #30):");
        for b in &DECODE_BUDGET {
            eprintln!("    {:<28} {:7.1} MB  {:5.1} %  {}", b.category, b.mb, 100.0 * b.mb / 1000.0 / total,
                if b.routed { "MoE" } else { "dense" });
        }
        eprintln!("    {:<28} {:7.1} MB  100.0 %  (dense {:.3} GB = {:.1} %, routed experts {:.3} GB = {:.1} %)",
            "total", 1000.0 * total, dense, 100.0 * dense / total, moe, 100.0 * moe / total);
        eprintln!("  roofline {HBM_PEAK_GBS:.1} GB/s: {:.1} tok/s at 100 %, {:.1} tok/s at 85 % (763 GB/s); 119.1 tok/s = {:.1} GB/s = {:.1} %",
            HBM_PEAK_GBS / total, 0.85 * HBM_PEAK_GBS / total, total * 119.1, 100.0 * total * 119.1 / HBM_PEAK_GBS);
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        let time = |f: &dyn Fn()| {
            // Warm up long enough for the clocks to ramp.
            let t0 = std::time::Instant::now();
            while t0.elapsed().as_millis() < 300 { f(); gpu.sync().unwrap(); }
            let t0 = std::time::Instant::now();
            for _ in 0..200 { f(); }
            gpu.sync().unwrap();
            t0.elapsed().as_secs_f64() / 200.0
        };
        eprintln!("  {:<8} {:<5} {:<16} {:<32} {:>6} x {:>5}  {:>8}  {:>8}  {:>7}  {:>9}  {:>8}", "type", "kind", "decode shape", "tensor", "rows", "cols", "time", "GB/s", "% roof", "at 100%", "bytes");
        let mut seen = std::collections::BTreeSet::new();
        for (name, info) in &g.tensors {
            let Ok(ty) = GgmlType::from_u32(info.ty) else { continue };
            let moe = info.dims.len() == 3;
            if info.dims.len() < 2 || info.dims[0] % 256 != 0 || !seen.insert((ty.name(), info.dims.clone())) { continue; }
            let t = w.get(name).unwrap();
            let dt = gpu.upload(&t).unwrap();
            let x = up(gpu, &xs(t.cols));
            let y = gpu.zeros::<f32>(t.rows).unwrap();
            let run = || if moe {
                let n = info.dims[2] as usize;
                let ids = up(gpu, &[3i32, 17, 40, 77, 101, 150, 200, 255]);
                let rows = t.rows / n;
                (time(&|| gpu.moe_gemv(t.ty, rows, t.cols, dt.ptr, dt.bytes() / n, ids.addr(), 8, x.addr(), 0, 1, y.addr(), None, 0).unwrap()),
                 8 * dt.bytes() / info.dims[2] as usize)
            } else {
                (time(&|| gpu.gemv(&dt, x.addr(), y.addr()).unwrap()), dt.bytes())
            };
            if !moe {
                let (x4, y4) = (up(gpu, &xs(4 * t.cols)), gpu.zeros::<f32>(4 * t.rows).unwrap());
                let tn: Vec<String> = (2..=4).map(|nt| format!("{:.1}", 1e6 * time(&|| gpu.gemvn(&dt, x4.addr(), t.cols, y4.addr(), t.rows, nt).unwrap()))).collect();
                eprintln!("  gemvn 2/3/4 inputs: {} us", tn.join(" / "));
            }
            let (s, bytes) = run();
            let gbs = bytes as f64 / s / 1e9;
            let rows = if moe { t.rows / info.dims[2] as usize } else { t.rows };
            eprintln!("  {:<8} {:<5} {:<16} {:<32} {:>6} x {:>5}  {:>7.2} us  {:>7.1}  {:>6.1} %  {:>7.2} us  {:>6.2} MB",
                ty.name(), if moe { "moe8" } else { "" }, decode_shape(name, rows, t.cols, moe), name, rows, t.cols,
                s * 1e6, gbs, 100.0 * gbs / HBM_PEAK_GBS, bytes as f64 / HBM_PEAK_GBS / 1e9 * 1e6, bytes as f64 / 1e6);
        }
    }
}

fn f16r(v: f32) -> f32 { half::f16::from_f32(v).to_f32() }

/// The f16 value the Vulkan f16 GEMM path (`packFloat2x16(f16vec2(..))`, SPIR-V `OpFConvert`) sees on this driver:
/// the conversion truncates toward zero instead of rounding to nearest even. A reference built with it compares the
/// kernel, not the driver's conversion; a 1-ulp input difference would otherwise read as a kernel error.
fn f16tz(v: f32) -> f32 {
    let h = half::f16::from_f32(v);
    let b = h.to_bits();
    let mag = b & 0x7fff;
    if h.to_f32().abs() > v.abs() && mag > 1 { half::f16::from_bits((b & 0x8000) | (mag - 1)).to_f32() } else { h.to_f32() }
}

/// The f16 conversion the backend's f16 GEMM uses: CUDA `__float2half` rounds to nearest even; the Vulkan shader's
/// `OpFConvert` truncates toward zero on the NVIDIA Volta driver (set `STRATA_VK_F16_TRUNC=1` there); the RTX 3060
/// and Radeon VII round to nearest even, like CUDA.
fn f16_in(bk: &str, v: f32) -> f32 {
    if bk == "vulkan" && std::env::var_os("STRATA_VK_F16_TRUNC").is_some() { f16tz(v) } else { f16r(v) }
}

/// Tensor-core GEMM over a tile list matches per-row dot products, for every type, with a gathered X and partial
/// tiles. Types on the int8 path (`Backend::mmq`, i.e. `Gpu::mmq` gated on the device) see X as int8 per 32 (as the
/// GEMV path does), the others fp16 inputs.
#[test]
fn gemm_matches_reference_for_every_type() {
    let Some(p) = common::model_path() else { return };
    // Results of the first backend per (tensor, GEMM path), the others of that path match it; and the last result of
    // each backend for the per-tensor cross-path figure that this test only records.
    let mut first = std::collections::HashMap::new();
    let mut last: std::collections::HashMap<String, (&'static str, Vec<f32>, bool)> = std::collections::HashMap::new();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        let mut seen = std::collections::BTreeSet::new();
        for (name, info) in &g.tensors {
            let Ok(ty) = GgmlType::from_u32(info.ty) else { continue };
            if info.dims.len() < 2 || info.dims[0] % 256 != 0 || !seen.insert(ty.name()) { continue; }
            let t = w.get(name).unwrap();
            let dt = gpu.upload(&t).unwrap();
            let (rows, n_x, m) = (t.rows.min(100), 50, 170);
            let x = xs(n_x * t.cols);
            let xrow: Vec<i32> = (0..m).map(|i| ((i * 7) % n_x) as i32).collect();
            // Tiles: positions 0..128, 128..144 and 144..170 (all with the same matrix).
            let tiles: Vec<u64> = [(0u64, 128u64), (128, 16), (144, 26)].iter().flat_map(|&(m0, c)| [dt.ptr, m0 | c << 32]).collect();
            let (dtl, dx, dr) = (up(gpu, &tiles), up(gpu, &x), up(gpu, &xrow));
            let dy = gpu.zeros::<f32>(m * rows).unwrap();
            gpu.gemm(t.ty, rows, t.cols, dtl.addr(), 3, dx.addr(), t.cols, n_x, dr.addr(), dy.addr(), rows, 0).unwrap();
            let got = down::<f32>(gpu, &dy);
            let mut wr = vec![0f32; t.cols];
            let mut want = vec![0f32; m * rows];
            // The path this backend's launcher takes: int8 needs the type policy *and* the arch (sm_70 CUDA has no
            // int8 tensor cores) *and* 16-byte aligned q8 rows (src/cuda/mod.rs:342).
            let int8 = gpu.mmq(t.ty) && t.cols % 128 == 0;
            // CUDA's `__float2half` rounds f16 operands, this Vulkan driver's `OpFConvert` truncates (f16tz/f16_in).
            // Where the two disagree on this tensor's operands the two f16 GEMMs multiply different numbers.
            let same_f16 = int8 || {
                let mut all = x.iter().all(|&v| f16tz(v) == f16r(v));
                for r in 0..rows {
                    t.row(r, &mut wr);
                    all &= wr.iter().all(|&v| f16tz(v) == f16r(v));
                }
                all
            };
            for r in 0..rows {
                t.row(r, &mut wr);
                for (i, &xr) in xrow.iter().enumerate() {
                    let xv = &x[xr as usize * t.cols..][..t.cols];
                    want[i * rows + r] = if int8 {
                        wr.iter().zip(as_seen(t.ty, xv)).map(|(a, b)| a * b).sum()
                    } else {
                        wr.iter().zip(xv).map(|(a, b)| f16_in(bk, *a) * f16_in(bk, *b)).sum()
                    };
                }
            }
            let e = rel_l2(&got, &want);
            eprintln!("{:8} {name}: gemm rel err {e:.2e}", ty.name());
            assert!(e <= 1e-4, "{} gemm ({name}): rel err {e}", ty.name());
            // Vulkan without cooperative matrices sums the f16 products in another order than mma.sync.
            if bk == "vulkan" && !int8 && std::env::var_os("STRATA_VK_NO_COOP").is_some() { continue; }
            // Cross-backend: bit for bit between backends on the same GEMM math and f16 operands, except by tolerance
            // where an sm_70 CUDA backend is involved (its `mma16816` sums the same f16 products in another order).
            // Backends whose math differs (sm_70 CUDA f16 vs Vulkan int8 for an int8 type, a truncating f16
            // conversion, and Vulkan order without cooperative matrices) are recorded, not asserted: the per-backend
            // reference above at 1e-4 is what catches a wrong kernel, and the measured figure goes in the PR.
            let key = (name.clone(), int8);
            match first.entry(key) {
                std::collections::hash_map::Entry::Vacant(v) => { v.insert((bk, gpu.volta(), got.clone())); }
                std::collections::hash_map::Entry::Occupied(o) => {
                    let &(bk0, volta, ref f) = o.get();
                    let bits = got.iter().zip(f.iter()).filter(|(a, b)| a.to_bits() != b.to_bits()).count();
                    if !same_f16 {
                        eprintln!("{:8} {name}: {bk} vs {bk0} (different f16 input conversion, recorded): rel err {:.2e}",
                            ty.name(), rel_l2(&got, f));
                    } else if volta || gpu.volta() {
                        let e = rel_l2(&got, f);
                        eprintln!("{:8} {name}: gemm on {bk} vs {bk0} (same math): rel err {e:.2e}", ty.name());
                        assert!(e <= 1e-4, "{} gemm ({name}) on {bk}: rel err {e} vs {bk0}", ty.name());
                    } else {
                        assert_eq!(bits, 0, "{} gemm ({name}) on {bk}: {bits} values differ from {bk0}", ty.name());
                    }
                }
            }
            // Only a real int8-vs-f16 pair is a "different GEMM math" row: for the types both backends run
            // as f16 (F32, IQ2_XS, ...) the cross-backend line above already carries the figure, and printing
            // this one too duplicated it under a wrong label.
            if let Some((bk0, f0, int8_0)) = last.insert(name.clone(), (bk, got.clone(), int8)) {
                if bk0 != bk && int8 != int8_0 {
                    eprintln!("{:8} {name}: {bk} vs {bk0} (different GEMM math, recorded): rel err {:.2e}",
                        ty.name(), rel_l2(&got, &f0));
                }
            }
        }
    }
}

/// A `SAME_X` GEMM inside `batch` whose x was not quantized by the previous GEMM (that one's type is off the int8
/// path, e.g. IQ2_XS) falls back to the f16 kernel instead of failing. Mixed-quant models hit this in prefill.
#[test]
fn same_x_inside_batch_falls_back_when_x_is_not_quantized() {
    let Some(p) = common::model_path() else { return };
    let g = Gguf::open(&p).unwrap();
    let w = Weights::new(&g).unwrap();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        // A tensor off the int8 path (IQ2_XS or a float type) and an int8 one with the same row length.
        let (mut slow, mut fast) = (std::collections::HashMap::new(), std::collections::HashMap::new());
        for (name, info) in &g.tensors {
            if info.dims.len() != 2 { continue }
            let cols = info.dims[0] as usize;
            if !cols.is_multiple_of(128) { continue }
            let Ok(ty) = GgmlType::from_u32(info.ty) else { continue };
            if Gpu::mmq(ty) { fast.entry(cols).or_insert((name, ty)); } else { slow.entry(cols).or_insert((name, ty)); }
        }
        let Some((&cols, &(slow_name, _))) = slow.iter().find(|(c, _)| fast.contains_key(c)) else {
            eprintln!("{bk}: SKIP, no mixed-type pair with equal columns");
            continue;
        };
        let (fast_name, _) = fast[&cols];
        let (ts, tf) = (w.get(slow_name).unwrap(), w.get(fast_name).unwrap());
        let (ds, df) = (gpu.upload(&ts).unwrap(), gpu.upload(&tf).unwrap());
        let n_x = 8;
        let x = xs(n_x * cols);
        let dx = up(gpu, &x);
        let (dy1, dy2) = (gpu.zeros::<f32>(n_x * ts.rows).unwrap(), gpu.zeros::<f32>(n_x * tf.rows).unwrap());
        // The first GEMM takes the f16 path and leaves no int8 copy of x.
        gpu.gemm_dense(&ds, n_x, dx.addr(), cols, dy1.addr(), ts.rows, 0).unwrap();
        // Inside a batch this GEMM cannot quantize x: it must use its f16 kernel rather than fail.
        gpu.batch(&mut || gpu.gemm_dense(&df, n_x, dx.addr(), cols, dy2.addr(), tf.rows, SAME_X)).unwrap();
        assert!(down::<f32>(gpu, &dy2).iter().all(|v| v.is_finite()), "{bk}: {fast_name} after SAME_X fallback");
    }
}

/// Prefill GEMM throughput on 4096 positions for a few layer matrices. Run with --ignored.
#[test]
#[ignore]
fn gemm_throughput() {
    let Some(p) = common::model_path() else { return };
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        let m = 4096usize;
        for name in ["blk.0.attn_qkv.weight", "blk.0.attn_gate.weight", "blk.0.ssm_out.weight", "blk.0.ffn_gate_exps.weight", "blk.0.ffn_down_exps.weight", "blk.0.attn_q.weight", "blk.0.ffn_gate.weight", "blk.0.ffn_down.weight", "blk.0.attn_v.weight"] {
            if !g.tensors.contains_key(name) { continue; }
            let t = w.get(name).unwrap();
            let rows = if g.tensors[name].dims.len() == 3 { t.rows / g.tensors[name].dims[2] as usize } else { t.rows };
            let dt = gpu.upload(&t).unwrap();
            let bm = GEMM_BM;
            let tiles: Vec<u64> = (0..m / bm).flat_map(|i| [dt.ptr, (bm * i) as u64 | (bm as u64) << 32]).collect();
            let (dtl, dx) = (up(gpu, &tiles), up(gpu, &xs(m * t.cols)));
            let dy = gpu.zeros::<f32>(m * rows).unwrap();
            let run = || gpu.gemm(t.ty, rows, t.cols, dtl.addr(), m / bm, dx.addr(), t.cols, m, 0, dy.addr(), rows, 0).unwrap();
            for _ in 0..3 { run(); }
            gpu.sync().unwrap();
            let t0 = std::time::Instant::now();
            for _ in 0..10 { run(); }
            gpu.sync().unwrap();
            let s = t0.elapsed().as_secs_f64() / 10.0;
            eprintln!("{:8} {name:28} {rows:6}x{:5} x {m}: {:8.2} ms  {:6.2} TFLOP/s", t.ty.name(), t.cols, s * 1e3, 2.0 * (m * rows * t.cols) as f64 / s / 1e12);
        }
    }
}

/// Expert GEMM throughput as in prefill: every expert of layer 0 with `c` positions in one tile each. Run with --ignored.
#[test]
#[ignore]
fn gemm_expert_throughput() {
    let Some(p) = common::model_path() else { return };
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let g = Gguf::open(&p).unwrap();
        let w = Weights::new(&g).unwrap();
        for name in ["blk.0.ffn_gate_exps.weight", "blk.0.ffn_down_exps.weight"] {
            if !g.tensors.contains_key(name) { continue; }
            let t = w.get(name).unwrap();
            let ne = g.tensors[name].dims[2] as usize;
            let (rows, eb) = (t.rows / ne, t.data.len() / ne);
            let dt = gpu.upload(&t).unwrap();
            for c in [8usize, 32, 64] {
                let m = ne * c;
                let tiles: Vec<u64> = (0..ne).flat_map(|e| [dt.ptr + (e * eb) as u64, (c * e) as u64 | (c as u64) << 32]).collect();
                let (dtl, dx) = (up(gpu, &tiles), up(gpu, &xs(m * t.cols)));
                let dy = gpu.zeros::<f32>(m * rows).unwrap();
                let run = || gpu.gemm(t.ty, rows, t.cols, dtl.addr(), ne, dx.addr(), t.cols, m, 0, dy.addr(), rows, 0).unwrap();
                for _ in 0..3 { run(); }
                gpu.sync().unwrap();
                let t0 = std::time::Instant::now();
                for _ in 0..10 { run(); }
                gpu.sync().unwrap();
                let s = t0.elapsed().as_secs_f64() / 10.0;
                eprintln!("{:8} {name:28} {ne:3} x {rows:5}x{:5}, {c:2} per expert: {:8.3} ms", t.ty.name(), t.cols, s * 1e3);
            }
        }
    }
}

/// Decode attention (both kernels) matches a CPU softmax over the f16 cache that kv_store writes; prefill attention
/// (tensor cores, f16 Q and P, 64-query tiles), where the backend has it, matches decode attention at every position,
/// with keys cached before the chunk, a chunk that does not fill its last tile, and early positions that leave decode
/// splits empty.
#[test]
fn attn_prefill_matches_decode() {
    let (mut first, mut first_pf) = (std::collections::HashMap::new(), std::collections::HashMap::new());
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        // Long contexts give each split several 32-position chunks.
        for (pos0, t, nh, nkv, hd) in [(5, 100, 4, 2, 64), (5, 100, 4, 2, 128), (5, 100, 4, 2, 256), (5, 100, 16, 2, 256),
                                       (5, 100, 8, 8, 128), (5, 100, 32, 8, 128), (2100, 3, 32, 8, 128), (1000, 3, 16, 2, 256), (0, 40, 24, 2, 256)] {
            let n = (pos0 + t) * nkv * hd;
            let (kf, vf) = (xs(n), xs(n + 5)[5..].to_vec());
            let (dk, dv) = (gpu.zeros::<u16>(n).unwrap(), gpu.zeros::<u16>(n).unwrap());
            gpu.kv_store(up(gpu, &kf).addr(), up(gpu, &vf).addr(), dk.addr(), dv.addr(), nkv * hd, pos0 + t,
                         up(gpu, &[0i32]).addr(), hd).unwrap();
            let h16 = |v: &[f32]| -> Vec<u16> { v.iter().map(|x| half::f16::from_f32(*x).to_bits()).collect() };
            assert_eq!(down::<u16>(gpu, &dk), h16(&kf), "kv_store keys");
            assert_eq!(down::<u16>(gpu, &dv), h16(&vf), "kv_store values");
            let q: Vec<f32> = xs(t * nh * hd + 3)[3..].iter().map(|v| 4.0 * v).collect();
            let qg = xs(t * nh * 2 * hd);
            let (dq, dg) = (up(gpu, &q), up(gpu, &qg));
            let scale = 1.0 / (hd as f32).sqrt();
            let step = up(gpu, &[pos0 as i32]);
            let dout = gpu.zeros::<f32>(t * nh * hd).unwrap();
            // qg = 0: no output gate. The gated output is the ungated output times sigmoid(gate).
            let sig = |x: f32| 1.0 / (1.0 + (-x).exp());
            let gated = |plain: &[f32]| -> Vec<f32> {
                plain.iter().enumerate().map(|(i, o)| o * sig(qg[(i / hd) * 2 * hd + hd + i % hd])).collect()
            };
            let got = match gpu.attn_prefill(dq.addr(), dk.addr(), dv.addr(), dg.addr(), dout.addr(), step.addr(), t, nh, nkv, hd, scale) {
                Err(e) if format!("{e}").contains("not implemented") => { eprintln!("attn_prefill: {e}"); None }
                r => {
                    r.unwrap();
                    let got = down::<f32>(gpu, &dout);
                    // Cross-backend: bit for bit where every backend sums the same f16 products in the same order
                    // (Vulkan's cooperative matrices and CUDA's mma.sync), by tolerance from or against an sm_70 CUDA
                    // backend, whose `mma16816` runs the same products on CUDA cores in another order, and where
                    // Vulkan has no cooperative matrices.
                    match first_pf.entry((pos0, nh, nkv, hd)) {
                        std::collections::hash_map::Entry::Vacant(v) => { v.insert((bk, gpu.volta(), got.clone())); }
                        std::collections::hash_map::Entry::Occupied(o) => {
                            let &(bk0, volta, ref f) = o.get();
                            if bk == "vulkan" && std::env::var_os("STRATA_VK_NO_COOP").is_some() {
                                // Without cooperative matrices Vulkan sums in another order.
                            } else if volta || gpu.volta() {
                                let e = rel_l2(&got, f);
                                eprintln!("attn_prefill {bk} vs {bk0} pos {pos0} nh {nh} nkv {nkv} hd {hd}: rel err {e:.2e}");
                                assert!(e <= 5e-4, "{bk} attn_prefill pos {pos0} nh {nh} nkv {nkv} hd {hd}: rel err {e}");
                            } else {
                                let nd = got.iter().zip(f.iter()).filter(|(a, b)| a.to_bits() != b.to_bits()).count();
                                assert!(nd == 0, "{bk} attn_prefill pos {pos0} nh {nh} nkv {nkv} hd {hd}: {nd} of {} differ from {bk0}", got.len());
                            }
                        }
                    }
                    gpu.attn_prefill(dq.addr(), dk.addr(), dv.addr(), 0, dout.addr(), step.addr(), t, nh, nkv, hd, scale).unwrap();
                    let e = rel_l2(&gated(&down::<f32>(gpu, &dout)), &got);
                    assert!(e <= 1e-6, "attn_prefill without gate nh {nh} hd {hd}: {e}");
                    Some(got)
                }
            };
            // Token i attends positions 0 ..= pos0 + i, in f64 over the f16-rounded cache.
            let cpu: Vec<f32> = (0..t * nh).flat_map(|r| {
                let (i, h) = (r / nh, r % nh);
                let (g, qh) = (h / (nh / nkv), &q[r * hd..][..hd]);
                let s: Vec<f64> = (0..=pos0 + i).map(|p| {
                    (0..hd).map(|d| qh[d] as f64 * f16r(kf[(p * nkv + g) * hd + d]) as f64).sum::<f64>() * scale as f64
                }).collect();
                let mx = s.iter().cloned().fold(f64::MIN, f64::max);
                let e: Vec<f64> = s.iter().map(|v| (v - mx).exp()).collect();
                let l: f64 = e.iter().sum();
                (0..hd).map(|d| (e.iter().enumerate().map(|(p, w)| w * f16r(vf[(p * nkv + g) * hd + d]) as f64).sum::<f64>() / l) as f32)
                    .collect::<Vec<f32>>()
            }).collect();
            let ddec = gpu.zeros::<f32>(t * nh * hd).unwrap();
            let part = gpu.zeros::<f32>(nh * ATT_SPLITS * (hd + 2)).unwrap();
            for gq_min in [ATT_GQA_MIN, 0] {
                for i in 0..t {
                    let s = up(gpu, &[(pos0 + i) as i32]);
                    let off = |p: u64, per: usize| p + (i * per * 4) as u64;
                    gpu.attn_decode_gq(off(dq.addr(), nh * hd), dk.addr(), dv.addr(), off(dg.addr(), nh * 2 * hd),
                                       off(ddec.addr(), nh * hd), part.addr(), s.addr(), nh, nkv, hd, scale, gq_min, 1).unwrap();
                }
                let want = down::<f32>(gpu, &ddec);
                let e = rel_l2(&want, &gated(&cpu));
                assert!(e <= 1e-5, "attn_decode nh {nh} nkv {nkv} hd {hd} gq_min {gq_min}: rel err vs CPU {e}");
                let f = first.entry((pos0, nh, nkv, hd, gq_min)).or_insert_with(|| want.clone());
                eprintln!("attn_decode pos {pos0} nh {nh} nkv {nkv} hd {hd} gq_min {gq_min}: rel err vs CPU {e:.2e}, {} of {} differ from the first backend",
                          want.iter().zip(f.iter()).filter(|(a, b)| a.to_bits() != b.to_bits()).count(), want.len());
                for i in 0..t {
                    let s = up(gpu, &[(pos0 + i) as i32]);
                    let off = |p: u64, per: usize| p + (i * per * 4) as u64;
                    gpu.attn_decode_gq(off(dq.addr(), nh * hd), dk.addr(), dv.addr(), 0,
                                       off(ddec.addr(), nh * hd), part.addr(), s.addr(), nh, nkv, hd, scale, gq_min, 1).unwrap();
                }
                let e = rel_l2(&gated(&down::<f32>(gpu, &ddec)), &want);
                assert!(e <= 1e-6, "attn_decode without gate nh {nh} hd {hd} gq_min {gq_min}: {e}");
                // One launch for all t tokens (the MTP verify path) gives the same bits as t launches.
                let steps: Vec<i32> = (0..t).flat_map(|i| [(pos0 + i) as i32, 0]).collect();
                let ds = up(gpu, &steps);
                let (dbat, pbat) = (gpu.zeros::<f32>(t * nh * hd).unwrap(), gpu.zeros::<f32>(t * nh * ATT_SPLITS * (hd + 2)).unwrap());
                gpu.attn_decode_gq(dq.addr(), dk.addr(), dv.addr(), dg.addr(), dbat.addr(), pbat.addr(), ds.addr(),
                                   nh, nkv, hd, scale, gq_min, t).unwrap();
                assert_eq!(down::<f32>(gpu, &dbat), want, "attn_decode batched nh {nh} nkv {nkv} hd {hd} gq_min {gq_min}");
                if gq_min == ATT_GQA_MIN {  // attn_decode_q's xq (where written) is quant_xq of its output
                    let (dxq, wxq) = (gpu.zeros::<u8>(t * nh * hd * 9 / 8).unwrap(), gpu.zeros::<u8>(t * nh * hd * 9 / 8).unwrap());
                    let aq = gpu.attn_decode_q(dq.addr(), dk.addr(), dv.addr(), dg.addr(), dbat.addr(), pbat.addr(), ds.addr(),
                                               nh, nkv, hd, scale, gq_min, t, dxq.addr(), 0, 0).unwrap();
                    assert_eq!(down::<f32>(gpu, &dbat), want, "attn_decode_q nh {nh} nkv {nkv} hd {hd}");
                    if aq != 0 {
                        gpu.quant_xq(dbat.addr(), nh * hd, nh * hd, t, wxq.addr()).unwrap();
                        assert_eq!(down::<u8>(gpu, &dxq), down::<u8>(gpu, &wxq), "attn_decode_q xq nh {nh} nkv {nkv} hd {hd}");
                    }
                }
                let Some(got) = &got else { continue };
                let e = rel_l2(got, &want);
                eprintln!("attn_prefill_{hd} nh {nh} nkv {nkv} gq_min {gq_min}: rel err vs decode {e:.2e}");
                assert!(e <= 5e-4, "attn_prefill_{hd} nh {nh} nkv {nkv} gq_min {gq_min}: rel err {e}");
            }
        }
    }
}

/// A QSA mask with every block selected leaves `attn_prefill_m` equal to `attn_prefill` (the tiled no-coop fallback
/// uses the same mask rows as the other prefill kernels).
#[test]
fn attn_prefill_qsa_mask_all_ones_matches_unmasked() {
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (pos0, t, nh, nkv, hd) = (37, 40, 8, 2, 128);
        let n = (pos0 + t) * nkv * hd;
        let (kf, vf) = (xs(n), xs(n + 5)[5..].to_vec());
        let (dk, dv) = (gpu.zeros::<u16>(n).unwrap(), gpu.zeros::<u16>(n).unwrap());
        let step = up(gpu, &[pos0 as i32]);
        let zero = up(gpu, &[0i32]);
        gpu.kv_store(up(gpu, &kf).addr(), up(gpu, &vf).addr(), dk.addr(), dv.addr(), nkv * hd, pos0 + t, zero.addr(), hd).unwrap();
        let q: Vec<f32> = xs(t * nh * hd + 3)[3..].iter().map(|v| 4.0 * v).collect();
        let dq = up(gpu, &q);
        let scale = 1.0 / (hd as f32).sqrt();
        let want_buf = gpu.zeros::<f32>(t * nh * hd).unwrap();
        gpu.attn_prefill(dq.addr(), dk.addr(), dv.addr(), 0, want_buf.addr(), step.addr(), t, nh, nkv, hd, scale).unwrap();
        let want = down::<f32>(gpu, &want_buf);
        let mw = (pos0 + t).div_ceil(128);
        // The cooperative tile reads mask rows in 64-query blocks, including rows past `t`.
        let dmask = up(gpu, &vec![u32::MAX; t.next_multiple_of(64) * mw]);
        let got_buf = gpu.zeros::<f32>(t * nh * hd).unwrap();
        gpu.attn_prefill_m(dq.addr(), dk.addr(), dv.addr(), 0, got_buf.addr(), step.addr(), t, nh, nkv, hd, scale,
            dmask.addr(), mw).unwrap();
        let e = rel_l2(&down::<f32>(gpu, &got_buf), &want);
        assert!(e <= 1e-6, "{bk} attn_prefill all-ones mask: rel err {e}");
    }
}

/// DeltaNet scan over a chunk of T tokens equals T single-token scans and a CPU scan (output and final state), and
/// its snapshots equal the states after the first single-token scans.
#[test]
fn deltanet_chunk_matches_steps() {
    let mut first = std::collections::HashMap::new();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (nk, nv, dk, dv, t) = (2, 4, 128, 128, 37);
        let ych = 2 * nk * dk + nv * dv;
        let y: Vec<f32> = xs(t * ych).iter().map(|v| 0.1 * v).collect();
        let beta: Vec<f32> = xs(t * nv).iter().map(|v| 0.5 + 0.4 * v).collect();
        let g: Vec<f32> = xs(t * nv + 1)[1..].iter().map(|v| -0.2 * v.abs()).collect();
        let s0: Vec<f32> = xs(nv * dv * dk + 2)[2..].iter().map(|v| 0.1 * v).collect();
        let (dy, db, dg) = (up(gpu, &y), up(gpu, &beta), up(gpu, &g));
        for ilv in [false, true] {
            let (ns, len) = (3, nv * dv * dk);
            let run = |chunk: bool| {
                let ds = up(gpu, &s0);
                let o = gpu.zeros::<f32>(t * nv * dv).unwrap();
                let snap = gpu.zeros::<f32>(ns * len).unwrap();
                let p = |d: u64, per: usize, i: usize| d + (i * per * 4) as u64;
                let steps: Vec<(usize, usize)> = if chunk { vec![(0, t)] } else { (0..t).map(|i| (i, 1)).collect() };
                let mut snaps = vec![];
                for (i, n) in steps {
                    gpu.deltanet(p(dy.addr(), ych, i), ds.addr(), p(db.addr(), nv, i), p(dg.addr(), nv, i), 0, 0,
                                 p(o.addr(), nv * dv, i), nk, nv, ilv, dk, dv, 0.5, n, ych, snap.addr(), ns).unwrap();
                    if !chunk && i < ns { snaps.extend(down::<f32>(gpu, &ds)); }
                }
                if chunk { snaps = down::<f32>(gpu, &snap); }
                (down::<f32>(gpu, &o), down::<f32>(gpu, &ds), snaps)
            };
            let ((o1, s1, n1), (o2, s2, n2)) = (run(true), run(false));
            let (eo, es, en) = (rel_l2(&o1, &o2), rel_l2(&s1, &s2), rel_l2(&n1, &n2));
            eprintln!("deltanet ilv {ilv} chunk vs steps: out {eo:.2e}, state {es:.2e}, snapshots {en:.2e}");
            assert!(eo <= 1e-5 && es <= 1e-5 && en <= 1e-5, "ilv {ilv}: out {eo}, state {es}, snapshots {en}");
            // CPU: S_j = decay * S_j; d = beta (v_j - S_j . k); S_j += d k; o_j = scale * S_j . q
            let (mut sc, mut oc) = (s0.clone(), vec![0.0f32; t * nv * dv]);
            for tok in 0..t {
                let yt = &y[tok * ych..];
                for vh in 0..nv {
                    let kh = if ilv { vh / (nv / nk) } else { vh % nk };
                    let (q, k) = (&yt[kh * dk..][..dk], &yt[nk * dk + kh * dk..][..dk]);
                    let (decay, b) = (g[tok * nv + vh].exp(), beta[tok * nv + vh]);
                    for j in 0..dv {
                        let row = &mut sc[(vh * dv + j) * dk..][..dk];
                        row.iter_mut().for_each(|x| *x *= decay);
                        let d = b * (yt[2 * nk * dk + vh * dv + j] - row.iter().zip(k).map(|(a, b)| a * b).sum::<f32>());
                        row.iter_mut().zip(k).for_each(|(x, k)| *x += d * k);
                        oc[tok * nv * dv + vh * dv + j] = 0.5 * row.iter().zip(q).map(|(a, b)| a * b).sum::<f32>();
                    }
                }
            }
            let (eo, es) = (rel_l2(&o1, &oc), rel_l2(&s1, &sc));
            let f = first.entry(ilv).or_insert_with(|| (o1.clone(), s1.clone(), o2.clone(), s2.clone()));
            let diff = |a: &[f32], b: &[f32]| a.iter().zip(b).filter(|(x, y)| x.to_bits() != y.to_bits()).count();
            eprintln!("deltanet ilv {ilv} vs CPU: out {eo:.2e}, state {es:.2e}; differ from the first backend: out {} of {}, state {} of {}; steps: out {}, state {}",
                      diff(&o1, &f.0), o1.len(), diff(&s1, &f.1), s1.len(), diff(&o2, &f.2), diff(&s2, &f.3));
            assert!(eo <= 1e-5 && es <= 1e-5, "ilv {ilv} vs CPU: out {eo}, state {es}");
        }
    }
}

/// deltanet with dt_bias set gives the same bits as ssm_gates then deltanet.
#[test]
fn deltanet_gates_match_ssm_gates() {
    let (nk, nv, dk, dv, t) = (2, 4, 128, 128, 3);
    let ych = 2 * nk * dk + nv * dv;
    let y: Vec<f32> = xs(t * ych).iter().map(|v| 0.1 * v).collect();
    let beta: Vec<f32> = xs(t * nv).iter().map(|v| 4.0 * v).collect();
    let g: Vec<f32> = xs(t * nv + 1)[1..].iter().map(|v| 30.0 * v).collect();
    let (dt, a): (Vec<f32>, Vec<f32>) = (xs(nv + 2)[2..].to_vec(), xs(nv + 3)[3..].iter().map(|v| -0.1 * v.abs()).collect());
    let s0: Vec<f32> = xs(nv * dv * dk + 2)[2..].iter().map(|v| 0.1 * v).collect();
    let bits = |v: &[f32]| v.iter().map(|x| x.to_bits()).collect::<Vec<_>>();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        let (dy, ddt, da) = (up(gpu, &y), up(gpu, &dt), up(gpu, &a));
        let run = |fused: bool| {
            let (db, dg, ds, o) = (up(gpu, &beta), up(gpu, &g), up(gpu, &s0), gpu.zeros::<f32>(t * nv * dv).unwrap());
            let (pb, pa) = if fused { (ddt.addr(), da.addr()) } else {
                gpu.ssm_gates(db.addr(), dg.addr(), ddt.addr(), da.addr(), t * nv, nv).unwrap();
                (0, 0)
            };
            gpu.deltanet(dy.addr(), ds.addr(), db.addr(), dg.addr(), pb, pa, o.addr(), nk, nv, true, dk, dv, 0.5, t, ych, 0, 0).unwrap();
            (bits(&down::<f32>(gpu, &o)), bits(&down::<f32>(gpu, &ds)))
        };
        assert!(run(true) == run(false), "{bk}: deltanet gates differ from ssm_gates");
    }
}

/// Chunked causal conv (conv_seq + conv_state) equals T single-token conv_silu steps, also for T < kernel width - 1.
#[test]
fn conv_seq_matches_steps() {
    let mut first: Option<Vec<u32>> = None;
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (ch, kw) = (96, 4);
        let w = xs(ch * kw);
        let st0 = xs((kw - 1) * ch + 9)[9..].to_vec();
        for t in [2, 10] {
            let x = xs(t * ch + 4)[4..].to_vec();
            let (dw, dx) = (up(gpu, &w), up(gpu, &x));
            let (s1, s2) = (up(gpu, &st0), up(gpu, &st0));
            let (y1, y2) = (gpu.zeros::<f32>(t * ch).unwrap(), gpu.zeros::<f32>(t * ch).unwrap());
            let ns = 3;
            let snap = gpu.zeros::<f32>(ns * (kw - 1) * ch).unwrap();
            gpu.conv_seq(dx.addr(), s1.addr(), dw.addr(), y1.addr(), ch, kw, t, snap.addr(), ns).unwrap();
            let d = |a: &rusting_strata::backend::Buf| down::<f32>(gpu, a);
            let mut snaps = vec![];
            for i in 0..t {
                let off = (i * ch * 4) as u64;
                gpu.conv_silu(dx.addr() + off, s2.addr(), dw.addr(), y2.addr() + off, ch, kw, 0, 0.0).unwrap();
                if i + 1 < t && i < ns { snaps.extend(d(&s2)); }
            }
            let (ey, es) = (rel_l2(&d(&y1), &d(&y2)), rel_l2(&d(&s1), &d(&s2)));
            assert!(ey <= 1e-6 && es == 0.0, "T {t}: y {ey}, state {es}");
            assert_eq!(d(&snap)[..snaps.len()], snaps[..], "T {t}: snapshots");
            if t == 10 {
                let bits: Vec<u32> = d(&y1).iter().map(|x| x.to_bits()).collect();
                let nd = first.as_ref().map_or(0, |f: &Vec<u32>| bits.iter().zip(f).filter(|(a, b)| a != b).count());
                eprintln!("op conv_seq {bk} [T {t} ch {ch} kw {kw}]: {nd} of {} differ from the first backend", bits.len());
                match &first { None => first = Some(bits), Some(f) => assert!(*f == bits, "{bk}: conv_seq differs from the first backend") }
            }
        }
    }
}

/// conv_silu with its l2 norms of the first heads gives the same bits as conv_silu, then l2_norm.
#[test]
fn conv_silu_l2_matches_l2_norm() {
    let mut first: Option<Vec<u32>> = None;
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (ch, kw, nn, eps) = (3 * 128 + 40, 4, 2, 1e-6);
        let (dw, dx) = (up(gpu, &xs(ch * kw)), up(gpu, &xs(ch + 5)[5..]));
        let st0 = xs((kw - 1) * ch + 9)[9..].to_vec();
        let (s1, s2) = (up(gpu, &st0), up(gpu, &st0));
        let (y1, y2) = (gpu.zeros::<f32>(ch).unwrap(), gpu.zeros::<f32>(ch).unwrap());
        gpu.conv_silu(dx.addr(), s1.addr(), dw.addr(), y1.addr(), ch, kw, 0, eps).unwrap();
        gpu.l2_norm(y1.addr(), 128, nn, ch, nn, eps).unwrap();
        gpu.conv_silu(dx.addr(), s2.addr(), dw.addr(), y2.addr(), ch, kw, nn, eps).unwrap();
        let bits = |b| down::<f32>(gpu, b).iter().map(|v| v.to_bits()).collect::<Vec<_>>();
        assert_eq!(bits(&y1), bits(&y2));
        assert_eq!(bits(&s1), bits(&s2));
        // Measurement only (M2-T7): cross-backend differing bits for the fused conv+l2_norm output.
        let b1 = bits(&y1);
        let nd = first.as_ref().map_or(0, |f: &Vec<u32>| b1.iter().zip(f).filter(|(a, b)| a != b).count());
        eprintln!("op conv_l2_norm {bk} [ch {ch} kw {kw}]: {nd} of {} differ from the first backend", b1.len());
        first.get_or_insert(b1);
    }
}

/// moe_combine_seq against the CPU, with and without the gated shared expert, bit-identical across backends.
#[test]
fn moe_combine_seq_matches_cpu() {
    let (n, k, t, ne) = (300, 3, 5, 20);
    let x0 = xs(t * n);
    let ye = xs(ne * n + 1)[1..].to_vec();
    let wts = xs(t * k + 2)[2..].to_vec();
    let inv: Vec<i32> = (0..t * k).map(|i| ((i * 7) % ne) as i32).collect();
    let (sh, sg) = (xs(t * n + 3)[3..].to_vec(), xs(t + 4)[4..].to_vec());
    let mut first: Option<Vec<u32>> = None;
    let mut first_shared: [Option<Vec<u32>>; 2] = [None, None];
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        let mut bits = vec![];
        for shared in [false, true] {
            let dx = up(gpu, &x0);
            let (dsh, dsg) = (up(gpu, &sh), up(gpu, &sg));
            gpu.moe_combine_seq(dx.addr(), up(gpu, &ye).addr(), up(gpu, &wts).addr(), up(gpu, &inv).addr(), k,
                                if shared { dsh.addr() } else { 0 }, dsg.addr(), n, t).unwrap();
            let got = down::<f32>(gpu, &dx);
            let want: Vec<f32> = (0..t * n).map(|i| {
                let (tk, d) = (i / n, i % n);
                let mut y: f32 = (0..k).map(|j| wts[tk * k + j] * ye[inv[tk * k + j] as usize * n + d]).sum();
                if shared { y += sh[i] / (1.0 + (-sg[tk]).exp()) }
                x0[i] + y
            }).collect();
            assert!(rel_l2(&got, &want) < 1e-6, "{bk} shared {shared}: rel err {}", rel_l2(&got, &want));
            // Measurement only (M2-T7).
            let nd = first_shared[shared as usize].as_ref().map_or(0, |f: &Vec<u32>| got.iter().zip(f).filter(|(a, b)| a.to_bits() != **b).count());
            eprintln!("op moe_combine {bk} [shared {shared}]: rel err vs CPU {:.2e}, {} of {} differ from the first backend",
                      rel_l2(&got, &want), nd, got.len());
            first_shared[shared as usize].get_or_insert_with(|| got.iter().map(|x| x.to_bits()).collect());
            bits.extend(got.iter().map(|x| x.to_bits()));
        }
        match &first { None => first = Some(bits), Some(f) => assert!(*f == bits, "{bk}: moe_combine_seq differs from the first backend") }
    }
}

#[test]
fn elementwise_ops_match_cpu() {
    // Measurement only (M2-T7): relative error against the CPU reference and differing bits from the
    // first backend. The assertions below are unchanged.
    let mut seen: std::collections::HashMap<&'static str, Vec<u32>> = std::collections::HashMap::new();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let mut report = |op: &'static str, got: &[f32], want: &[f32]| {
            let e = rel_l2(got, want);
            let nd = seen.get(op).map_or(0, |f: &Vec<u32>| got.iter().zip(f).filter(|(a, b)| a.to_bits() != **b).count());
            eprintln!("op {op} {bk} [n 1000, not a block multiple]: rel err vs CPU {e:.2e}, {nd} of {} differ from the first backend", got.len());
            seen.entry(op).or_insert_with(|| got.iter().map(|x| x.to_bits()).collect());
        };
        let n = 1000; // not a multiple of the block size
        let (g, u) = (xs(n).iter().map(|v| v * 8.0).collect::<Vec<f32>>(), xs(n + 1)[1..].to_vec());
        let (dg, du) = (up(gpu, &g), up(gpu, &u));
        gpu.swiglu(dg.addr(), du.addr(), n).unwrap();
        let want: Vec<f32> = g.iter().zip(&u).map(|(g, u)| g / (1.0 + (-g).exp()) * u).collect();
        let got = down::<f32>(gpu, &dg);
        assert!(rel_l2(&got, &want) < 1e-6);
        report("swiglu", &got, &want);
        gpu.add(dg.addr(), du.addr(), n).unwrap();
        let want: Vec<f32> = want.iter().zip(&u).map(|(a, b)| a + b).collect();
        let got = down::<f32>(gpu, &dg);
        assert!(rel_l2(&got, &want) < 1e-6);
        report("add", &got, &want);
        // kv_store rounds to f16 to nearest even, through subnormals, ties, overflow and infinities.
        let k = [0.0, -0.0, 1e-8, -3e-8, 5.96e-8, 6.1e-5, 6.0e-5, 1.0 + 1.0 / 2048.0, 1.0 + 3.0 / 2048.0, 65504.0, 65519.0,
                 65520.0, 1e9, f32::INFINITY, f32::NEG_INFINITY, -2.5e-3, 3.14159, -1234.5678, 0.1, 7e-6, 1e-40, -1.0, 2.0, 0.5,
                 1.0 / 3.0, 100.0, 1000.0, 4096.5, 8191.0, 1e-4, -6.5e-5, 12.375];
        let (dk, dv) = (gpu.zeros::<u16>(64).unwrap(), gpu.zeros::<u16>(64).unwrap());
        gpu.kv_store(up(gpu, &k).addr(), up(gpu, &k).addr(), dk.addr(), dv.addr(), 32, 1, up(gpu, &[1i32]).addr(), 32).unwrap();
        let want: Vec<u16> = [0.0f32; 32].iter().chain(&k).map(|x| half::f16::from_f32(*x).to_bits()).collect();
        assert_eq!(down::<u16>(gpu, &dk), want);
        assert_eq!(down::<u16>(gpu, &dv), want);
    }
}

/// ssm_gates: sigmoid(beta) and softplus(g + dt_bias) * a, bit-identical across backends (Vulkan ports CUDA's expf
/// and log1pf); a log1p differing in the last bit flips greedy tokens a few steps into a DeltaNet decode.
#[test]
fn ssm_gates_match_across_backends() {
    let (n, nv) = (4000, 32);
    let beta: Vec<f32> = xs(n).iter().map(|v| 12.0 * v).collect();
    let g: Vec<f32> = xs(n + 1)[1..].iter().map(|v| 30.0 * v).collect();
    let (dt, a): (Vec<f32>, Vec<f32>) = (xs(nv + 2)[2..].to_vec(), xs(nv + 3)[3..].iter().map(|v| -v.abs()).collect());
    let mut first: Option<(Vec<u32>, Vec<u32>)> = None;
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        let (db, dg) = (up(gpu, &beta), up(gpu, &g));
        gpu.ssm_gates(db.addr(), dg.addr(), up(gpu, &dt).addr(), up(gpu, &a).addr(), n, nv).unwrap();
        let (gb, gg) = (down::<f32>(gpu, &db), down::<f32>(gpu, &dg));
        let wb: Vec<f32> = beta.iter().map(|x| 1.0 / (1.0 + (-x).exp())).collect();
        let wg: Vec<f32> = g.iter().enumerate().map(|(i, x)| { let x = x + dt[i % nv]; (if x > 20.0 { x } else { x.exp().ln_1p() }) * a[i % nv] }).collect();
        assert!(rel_l2(&gb, &wb) < 1e-6 && rel_l2(&gg, &wg) < 1e-6, "{bk}: rel err beta {}, g {}", rel_l2(&gb, &wb), rel_l2(&gg, &wg));
        let bits = (gb.iter().map(|x| x.to_bits()).collect(), gg.iter().map(|x| x.to_bits()).collect());
        match &first { None => first = Some(bits), Some(f) => assert!(*f == bits, "{bk} differs from the first backend") }
    }
}

#[test]
fn norm_rope_and_gate_ops_match_cpu() {
    use rusting_strata::ops;
    // Measurement only (M2-T7): relative error against the CPU reference and the differing bits from
    // the first backend, per operation. The assertions below are unchanged.
    let mut seen: std::collections::HashMap<&'static str, Vec<u32>> = std::collections::HashMap::new();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let close = |got: &[f32], want: &[f32], what: &str| assert!(rel_l2(got, want) < 1e-6, "{what}: rel err {}", rel_l2(got, want));
        let mut report = |op: &'static str, case: &str, got: &[f32], want: &[f32]| {
            let e = rel_l2(got, want);
            let nd = seen.get(op).map_or(0, |f: &Vec<u32>| got.iter().zip(f).filter(|(a, b)| a.to_bits() != **b).count());
            eprintln!("op {op} {bk} [{case}]: rel err vs CPU {e:.2e}, {nd} of {} differ from the first backend", got.len());
            seen.entry(op).or_insert_with(|| got.iter().map(|x| x.to_bits()).collect());
        };
        let (n, rows) = (2048, 3);
        let (x, w) = (xs(rows * n).iter().map(|v| v * 3.0).collect::<Vec<f32>>(), xs(n + 7)[7..].to_vec());
        let (dx, dw, dout) = (up(gpu, &x), up(gpu, &w), gpu.zeros::<f32>(rows * n).unwrap());
        gpu.rms_norm(dx.addr(), n, dw.addr(), dout.addr(), n, n, rows, 1e-6).unwrap();
        let mut want = vec![0f32; rows * n];
        for (o, r) in want.chunks_mut(n).zip(x.chunks(n)) { ops::rms_norm(r, &w, 1e-6, o) }
        let got = down::<f32>(gpu, &dout);
        close(&got, &want, "rms_norm");
        report("rms_norm", &format!("{n} x {rows} rows"), &got, &want);

        // quant_xq: int8 rows, then scales, as the CPU rounds them.
        let dq = gpu.zeros::<u8>(rows * n * 9 / 8).unwrap();
        gpu.quant_xq(dx.addr(), n, n, rows, dq.addr()).unwrap();
        let q = down::<u8>(gpu, &dq);
        let (mut wq, mut wd) = (vec![], vec![]);
        for b in x.chunks(32) {
            let mx = b.iter().fold(0f32, |m, v| m.max(v.abs()));
            let id = if mx > 0.0 { 127.0 / mx } else { 0.0 };
            wq.extend(b.iter().map(|v| (v * id).round_ties_even() as i8 as u8));
            wd.extend((mx / 127.0).to_le_bytes());
        }
        assert_eq!(q[..rows * n], wq[..], "quant_xq values");
        assert_eq!(q[rows * n..], wd[..], "quant_xq scales");
        // swiglu_q: either g = silu(g) * u, or the bytes of that through quant_xq.
        let du = up(gpu, &xs(rows * n + 3)[3..]);
        let dq2 = gpu.zeros::<u8>(rows * n * 9 / 8).unwrap();
        let (dg, dr) = (up(gpu, &x), up(gpu, &x));
        let r = gpu.swiglu_q(dg.addr(), du.addr(), n, rows, dq2.addr()).unwrap();
        gpu.swiglu(dr.addr(), du.addr(), rows * n).unwrap();
        gpu.quant_xq(dr.addr(), n, n, rows, dq.addr()).unwrap();
        if r == 0 { assert_eq!(down::<f32>(gpu, &dg), down::<f32>(gpu, &dr), "swiglu_q g") }
        else { assert_eq!(down::<u8>(gpu, &dq2), down::<u8>(gpu, &dq), "swiglu_q xq") }

        // l2_norm on vectors of 128, 2 per token, tokens 300 floats apart.
        let (hn, per, stride) = (128, 2, 300);
        let dx = up(gpu, &x[..3 * stride]);
        gpu.l2_norm(dx.addr(), hn, per, stride, 3 * per, 1e-6).unwrap();
        let mut want = x[..3 * stride].to_vec();
        for t in 0..3 { for h in 0..per { ops::l2_norm(&mut want[t * stride + h * hn..][..hn], 1e-6) } }
        let got = down::<f32>(gpu, &dx);
        close(&got, &want, "l2_norm");
        report("l2_norm", "128 x 2 per token, 3 tokens", &got, &want);

        // rope_neox: 3 tokens from position 30000, 2 heads each, 64 of 128 dims rotated.
        let (hd, n_rot, pos) = (128, 64, 30_000);
        let dx = up(gpu, &x[..6 * hd]);
        let step = up(gpu, &[pos as i32, 0]);
        gpu.rope_neox(dx.addr(), hd, 6, 2, n_rot, step.addr(), 1e7).unwrap();
        let mut want = x[..6 * hd].to_vec();
        for (h, v) in want.chunks_mut(hd).enumerate() { ops::rope_neox(v, n_rot, pos + h / 2, 1e7) }
        let got = down::<f32>(gpu, &dx);
        close(&got, &want, "rope_neox");
        report("rope_neox", "hd 128, 64 rotated, pos 30000", &got, &want);
        // rms_norm_rope == rms_norm then rope_neox, from rows 160 floats apart.
        let dx = up(gpu, &x[..6 * 160]);
        let (d1, d2) = (gpu.zeros::<f32>(6 * hd).unwrap(), gpu.zeros::<f32>(6 * hd).unwrap());
        gpu.rms_norm(dx.addr(), 160, dw.addr(), d1.addr(), hd, hd, 6, 1e-6).unwrap();
        gpu.rope_neox(d1.addr(), hd, 6, 2, n_rot, step.addr(), 1e7).unwrap();
        gpu.rms_norm_rope(dx.addr(), 160, dw.addr(), d2.addr(), hd, 6, 1e-6, 2, n_rot, step.addr(), 1e7).unwrap();
        assert_eq!(down::<f32>(gpu, &d2), down::<f32>(gpu, &d1), "rms_norm_rope");
        // rms_norm_rope_kv == rms_norm_rope then kv_store of 3 tokens of 2 heads.
        let dv = up(gpu, &x[6 * hd..12 * hd]);
        let c: Vec<_> = (0..4).map(|_| gpu.zeros::<u16>(gpu.kv_words((pos + 3) * 2 * hd)).unwrap()).collect();
        let d3 = gpu.zeros::<f32>(6 * hd).unwrap();
        gpu.kv_store(d2.addr(), dv.addr(), c[0].addr(), c[1].addr(), 2 * hd, 3, step.addr(), hd).unwrap();
        gpu.rms_norm_rope_kv(dx.addr(), 160, dw.addr(), d3.addr(), hd, 6, 1e-6, 2, n_rot, step.addr(), 1e7, dv.addr(), c[2].addr(), c[3].addr()).unwrap();
        assert_eq!(down::<f32>(gpu, &d3), down::<f32>(gpu, &d1), "rms_norm_rope_kv");
        for i in 0..2 { assert_eq!(down::<u16>(gpu, &c[i + 2]), down::<u16>(gpu, &c[i]), "rms_norm_rope_kv cache {i}"); }
        // rms_norm_rope_qk == rms_norm_rope of 3 tokens of 2 q heads (rows 160 apart), then rms_norm_rope_kv of 1 k head each.
        let dk = up(gpu, &x[12 * hd..15 * hd]);
        let (d4, d5, d6, d7) = (gpu.zeros::<f32>(6 * hd).unwrap(), gpu.zeros::<f32>(3 * hd).unwrap(), gpu.zeros::<f32>(6 * hd).unwrap(), gpu.zeros::<f32>(3 * hd).unwrap());
        let c2: Vec<_> = (0..4).map(|_| gpu.zeros::<u16>(gpu.kv_words((pos + 3) * hd)).unwrap()).collect();
        gpu.rms_norm_rope(dx.addr(), 160, dw.addr(), d4.addr(), hd, 6, 1e-6, 2, n_rot, step.addr(), 1e7).unwrap();
        gpu.rms_norm_rope_kv(dk.addr(), hd, dw.addr(), d5.addr(), hd, 3, 1e-6, 1, n_rot, step.addr(), 1e7, dv.addr(), c2[0].addr(), c2[1].addr()).unwrap();
        gpu.rms_norm_rope_qk(dx.addr(), 160, dw.addr(), d6.addr(), 6, 2, dk.addr(), dw.addr(), d7.addr(), 3, 1, hd, 1e-6, n_rot, step.addr(), 1e7,
                             dv.addr(), c2[2].addr(), c2[3].addr()).unwrap();
        assert_eq!(down::<f32>(gpu, &d6), down::<f32>(gpu, &d4), "rms_norm_rope_qk q");
        assert_eq!(down::<f32>(gpu, &d7), down::<f32>(gpu, &d5), "rms_norm_rope_qk k");
        for i in 0..2 { assert_eq!(down::<u16>(gpu, &c2[i + 2]), down::<u16>(gpu, &c2[i]), "rms_norm_rope_qk cache {i}"); }

        // norm_gate over 4 heads of 128.
        let z = xs(4 * hn + 3)[3..].to_vec();
        let (dx, dz) = (up(gpu, &x[..4 * hn]), up(gpu, &z));
        gpu.norm_gate(dx.addr(), dw.addr(), dz.addr(), hn, 4, 1e-6).unwrap();
        let mut want = vec![0f32; 4 * hn];
        for h in 0..4 {
            ops::rms_norm(&x[h * hn..][..hn], &w[..hn], 1e-6, &mut want[h * hn..][..hn]);
            for i in h * hn..(h + 1) * hn { want[i] *= ops::silu(z[i]) }
        }
        let got = down::<f32>(gpu, &dx);
        close(&got, &want, "norm_gate");
        report("norm_gate", "4 heads of 128", &got, &want);

        // ssm_gates on 3 tokens of 5 heads, with g reaching the softplus cutoff.
        let (nv, nt) = (5, 3);
        let (beta, g): (Vec<f32>, Vec<f32>) = (x[..nv * nt].to_vec(), x[100..100 + nv * nt].iter().map(|v| v * 30.0).collect());
        let (dt, a) = (xs(nv + 1)[1..].to_vec(), xs(nv + 2)[2..].to_vec());
        let (db, dg, ddt, da) = (up(gpu, &beta), up(gpu, &g), up(gpu, &dt), up(gpu, &a));
        gpu.ssm_gates(db.addr(), dg.addr(), ddt.addr(), da.addr(), nv * nt, nv).unwrap();
        let wb: Vec<f32> = beta.iter().map(|&b| ops::sigmoid(b)).collect();
        let gb = down::<f32>(gpu, &db);
        close(&gb, &wb, "ssm_gates beta");
        report("ssm_gates", "beta, 3 tokens of 5 heads", &gb, &wb);
        let want: Vec<f32> = g.iter().enumerate().map(|(i, &g)| ops::softplus(g + dt[i % nv]) * a[i % nv]).collect();
        let gg = down::<f32>(gpu, &dg);
        close(&gg, &want, "ssm_gates g");
        report("ssm_gates_g", "g, 3 tokens of 5 heads", &gg, &want);

        // conv_silu: 300 channels, kernel 4, two steps so the state shifts.
        let (ch, kw) = (300, 4);
        let (cw, st0) = (xs(ch * kw + 5)[5..].to_vec(), xs((kw - 1) * ch + 9)[9..].to_vec());
        let (dcw, dst, dy) = (up(gpu, &cw), up(gpu, &st0), gpu.zeros::<f32>(ch).unwrap());
        let mut st = st0.clone();
        for s in 0..2 {
            let qkv = x[s * ch..][..ch].to_vec();
            let dq = up(gpu, &qkv);
            gpu.conv_silu(dq.addr(), dst.addr(), dcw.addr(), dy.addr(), ch, kw, 0, 0.0).unwrap();
            let want: Vec<f32> = (0..ch).map(|c| {
                let acc = (0..kw - 1).map(|k| st[k * ch + c] * cw[c * kw + k]).sum::<f32>() + qkv[c] * cw[c * kw + kw - 1];
                ops::silu(acc)
            }).collect();
            st.drain(..ch);
            st.extend(&qkv);
            let gy = down::<f32>(gpu, &dy);
            let gs = down::<f32>(gpu, &dst);
            close(&gy, &want, "conv_silu y");
            close(&gs, &st, "conv_silu state");
            if s == 0 {
                report("conv", "ch 300 kw 4, 2 steps", &gy, &want);
                report("conv_state", "ch 300 kw 4, 2 steps", &gs, &st);
            }
        }
    }
}

#[test]
fn argmax_rows_matches_ops_argmax() {
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let n = 248_320;
        // Row 0 generic, row 1 a tie (first index wins), row 2 the maximum in the last element, row 3 all -inf but one.
        let mut x: Vec<f32> = (0..4).flat_map(|r| xs(n + r).into_iter().skip(r)).collect();
        x[n + 1000] = 9.0; x[n + 200_000] = 9.0;
        x[3 * n - 1] = 5.0;
        x[3 * n..].fill(f32::NEG_INFINITY); x[3 * n + 77] = -1.0;
        let dx = up(gpu, &x);
        let dout = gpu.zeros::<i32>(4).unwrap();
        gpu.argmax_rows(dx.addr(), n, 4, dout.addr()).unwrap();
        let got = down::<i32>(gpu, &dout);
        let want: Vec<i32> = x.chunks(n).map(|r| rusting_strata::ops::argmax(r) as i32).collect();
        assert_eq!(got, want);
        assert_eq!(want[1..], [1000, n as i32 - 1, 77]);
    }
}

#[test]
fn router_topk_matches_ops_top_k() {
    let mut first: Option<(Vec<i32>, Vec<u32>)> = None;
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (n, k, t) = (256, 8, 3);
        // Token 1 has a tie between experts 7 and 200 (lower index first), token 2 a tie at the k-th place.
        let mut x: Vec<f32> = xs(n * t).iter().map(|v| v * 4.0).collect();
        x[n + 7] = 9.0; x[n + 200] = 9.0;
        x[2 * n + 30] = 5.0; x[2 * n + 31] = 5.0; x[2 * n + 255] = 5.0;
        let dx = up(gpu, &x);
        let (dids, dw) = (gpu.zeros::<i32>(k * t).unwrap(), gpu.zeros::<f32>(k * t).unwrap());
        gpu.router_topk(dx.addr(), n, k, 2.5, dids.addr(), dw.addr(), t).unwrap();
        let (ids, w) = (down::<i32>(gpu, &dids), down::<f32>(gpu, &dw));
        for r in 0..t {
            let mut p = x[r * n..(r + 1) * n].to_vec();
            rusting_strata::ops::softmax(&mut p);
            let want = rusting_strata::ops::top_k(&p, k);
            assert_eq!(ids[r * k..(r + 1) * k].iter().map(|&i| i as usize).collect::<Vec<_>>(), want, "token {r}");
            let s: f32 = want.iter().map(|&i| p[i]).sum();
            for (j, &i) in want.iter().enumerate() { assert!((w[r * k + j] - p[i] / s * 2.5).abs() < 1e-5, "token {r} {j}"); }
        }
        assert_eq!(ids[k..k + 2], [7, 200]);
        let bits = (ids, w.iter().map(|v| v.to_bits()).collect::<Vec<_>>());
        // Measurement only (M2-T7): max |weight - CPU| and differing bits from the first backend.
        let mut wmax = 0f32;
        for r in 0..t {
            let mut p = x[r * n..(r + 1) * n].to_vec();
            rusting_strata::ops::softmax(&mut p);
            let want = rusting_strata::ops::top_k(&p, k);
            let s: f32 = want.iter().map(|&i| p[i]).sum();
            for (j, &i) in want.iter().enumerate() { wmax = wmax.max((w[r * k + j] - p[i] / s * 2.5).abs()); }
        }
        let nd = first.as_ref().map_or(0, |f: &(Vec<i32>, Vec<u32>)| f.1.iter().zip(&bits.1).filter(|(a, b)| a != b).count());
        eprintln!("op router_topk {bk} [n {n} k {k} t {t}]: max abs {wmax:.2e}, {nd} of {} differ from the first backend", bits.1.len());
        match &first { None => first = Some(bits), Some(f) => assert!(*f == bits, "{bk} differs from the first backend") }
    }
}

/// The CPU expert round trip: moe_route, a host thread answering through the mailbox, moe_combine. On
/// Vulkan an unanswered request then ends in an error, not a hang (CUDA traps, which kills the context).
#[test]
fn moe_mailbox_round_trip() {
    use rusting_strata::cpu_worker::{DONE, IDS, Mailbox, NTOK, REQ, SKIP};
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (k, n, t) = (4, 300, 2);
        let lay = Mailbox::new(k, n);
        // Router logits of 4 experts that route token 0 to experts 0, 1, 2, 3 and token 1 to 3, 2, 1, 0.
        let logits = [4f32, 3.0, 2.0, 1.0, 1.0, 2.0, 3.0, 4.0];
        let ids = [0, 1, 2, 3, 3, 2, 1, 0];
        let table = [5, -1, 2, -1];
        let wts: Vec<f32> = logits.chunks(k).zip(ids.chunks(k)).flat_map(|(l, id)| {
            let mut p = l.to_vec();
            rusting_strata::ops::softmax(&mut p);
            id.iter().map(move |&i| p[i as usize]).collect::<Vec<_>>()
        }).collect();
        let (h, ye, sh, sg, x0) = (xs(n * t), xs(k * t * n), xs(n * t), [0.3f32, -0.7], xs(n * t));
        let (dlog, dtable, dh, dye, dsh, dsg, dx) = (up(gpu, &logits), up(gpu, &table), up(gpu, &h), up(gpu, &ye), up(gpu, &sh), up(gpu, &sg), up(gpu, &x0));
        let (dids, slots) = (gpu.zeros::<i32>(k * t).unwrap(), gpu.zeros::<i32>(k * t).unwrap());
        let (dwts, wh) = (gpu.zeros::<f32>(k * t).unwrap(), gpu.zeros::<f32>(k * t).unwrap());
        let (mb, host) = gpu.host_mailbox(lay.stride).unwrap();
        let step = gpu.zeros::<i32>(2).unwrap();
        let hp = host as usize;
        let at = move |o: usize| (hp + 4 * o) as *mut u32;
        // The CPU side: each missed expert's output is its weight times h.
        let answer = |seq: u32| {
            let t0 = std::time::Instant::now();
            while unsafe { at(REQ).read_volatile() } != seq { assert!(t0.elapsed().as_secs() < 10, "no request"); std::hint::spin_loop(); }
            std::sync::atomic::fence(std::sync::atomic::Ordering::Acquire);
            let rd = |o: usize| unsafe { at(o).read_volatile() };
            assert_eq!(rd(NTOK) as usize, t);
            for tk in 0..t {
                let mut y = vec![0f32; n];
                for j in tk * k..(tk + 1) * k {
                    assert_eq!(rd(IDS + j) as i32, ids[j]);
                    assert_eq!(rd(IDS + 2 * k * t + j) as i32, table[ids[j] as usize]);
                    if (rd(IDS + 2 * k * t + j) as i32) < 0 {
                        let wj = f32::from_bits(rd(IDS + k * t + j));
                        for i in 0..n { y[i] += wj * f32::from_bits(rd(lay.h + tk * n + i)); }
                    }
                }
                for i in 0..n { unsafe { at(lay.y + tk * n + i).write_volatile(y[i].to_bits()) } }
            }
            std::sync::atomic::fence(std::sync::atomic::Ordering::Release);
            unsafe { at(DONE).write_volatile(seq) };
        };
        let ops = |step: &rusting_strata::backend::Buf| {
            gpu.moe_route(dlog.addr(), 4, k, 0.0, dtable.addr(), dids.addr(), dwts.addr(), slots.addr(), wh.addr(), dh.addr(), mb.addr(), n, lay.h, step.addr(), t, 0)?;
            gpu.moe_combine(dx.addr(), dye.addr(), wh.addr(), k, dsh.addr(), dsg.addr(), mb.addr(), lay.y, step.addr(), slots.addr(), n, t)?;
            gpu.sync()
        };
        // Rounds with new activations: stale mailbox reads would show.
        let mut want = x0.clone();
        for seq in 1..4 {
            let hs: Vec<f32> = h.iter().map(|v| v * seq as f32).collect();
            gpu.put(&hs, &dh, 0).unwrap();
            gpu.put(&[0i32, seq], &step, 0).unwrap();
            std::thread::scope(|s| {
                s.spawn(|| answer(seq as u32));
                ops(&step).unwrap();
            });
            let got = down::<f32>(gpu, &dx);
            let (gi, gs, gw) = (down::<i32>(gpu, &dids), down::<i32>(gpu, &slots), down::<f32>(gpu, &wh));
            for j in 0..k * t {
                assert_eq!((gi[j], gs[j]), (ids[j], table[ids[j] as usize]), "routing {j}");
                assert!((gw[j] - if gs[j] >= 0 { wts[j] } else { 0.0 }).abs() < 1e-6, "hit weight {j}");
            }
            for tk in 0..t {
                for i in 0..n {
                    want[tk * n + i] += sh[tk * n + i] / (1.0 + (-sg[tk]).exp());
                    for j in tk * k..(tk + 1) * k {
                        want[tk * n + i] += wts[j] * if table[ids[j] as usize] >= 0 { ye[j * n + i] } else { hs[tk * n + i] };
                    }
                    assert!((got[tk * n + i] - want[tk * n + i]).abs() < 1e-4, "round {seq} token {tk} {i}: {} vs {}", got[tk * n + i], want[tk * n + i]);
                }
            }
        }
        // A round with no miss raises only the skip flag on CUDA (Vulkan raises the request flag: no gain there, #128).
        gpu.put(&[5i32, 1, 2, 3], &dtable, 0).unwrap();
        gpu.put(&[0i32, 4], &step, 0).unwrap();
        ops(&step).unwrap();
        let want = if bk == "cuda" { (4, 3) } else { (0, 4) };
        assert_eq!(unsafe { (at(SKIP).read_volatile(), at(REQ).read_volatile()) }, want);
        gpu.put(&table, &dtable, 0).unwrap();
        // #34 R2: `mb = 0` (a fully resident cache) still routes, and writes no mailbox word, even with missed
        // experts in the table: the combine must not wait for a CPU part that does not exist. CUDA only (the Vulkan
        // kernels read the mailbox unconditionally).
        if bk == "cuda" {
            let before = unsafe { (at(SKIP).read_volatile(), at(REQ).read_volatile()) };
            gpu.put(&[0i32, 6], &step, 0).unwrap();
            gpu.moe_route(dlog.addr(), 4, k, 0.0, dtable.addr(), dids.addr(), dwts.addr(), slots.addr(), wh.addr(), dh.addr(), 0, n, lay.h, step.addr(), t, 0).unwrap();
            gpu.moe_combine(dx.addr(), dye.addr(), wh.addr(), k, dsh.addr(), dsg.addr(), 0, lay.y, step.addr(), slots.addr(), n, t).unwrap();
            gpu.sync().unwrap();
            let (gi, gs) = (down::<i32>(gpu, &dids), down::<i32>(gpu, &slots));
            for j in 0..k * t { assert_eq!((gi[j], gs[j]), (ids[j], table[ids[j] as usize]), "null-mailbox routing {j}"); }
            assert_eq!(unsafe { (at(SKIP).read_volatile(), at(REQ).read_volatile()) }, before, "mb = 0 must not write the mailbox");
        }
        if bk == "vulkan" {
            // Unanswered: with conditional rendering the combine adds nothing, the rest of the submission (the add) is
            // skipped and stalled() tells the caller; without it the wait is an error.
            let before = down::<f32>(gpu, &dx);
            gpu.put(&[0i32, 5], &step, 0).unwrap();
            let t0 = std::time::Instant::now();
            let r = (|| {
                gpu.moe_route(dlog.addr(), 4, k, 0.0, dtable.addr(), dids.addr(), dwts.addr(), slots.addr(), wh.addr(), dh.addr(), mb.addr(), n, lay.h, step.addr(), t, 0)?;
                gpu.moe_combine(dx.addr(), dye.addr(), wh.addr(), k, dsh.addr(), dsg.addr(), mb.addr(), lay.y, step.addr(), slots.addr(), n, t)?;
                gpu.add(dx.addr(), dx.addr(), n)?;
                gpu.sync()
            })();
            eprintln!("unanswered: {r:?} after {:.2} s", t0.elapsed().as_secs_f64());
            match r {
                Ok(()) => {
                    assert!(gpu.stalled(), "an unanswered combine must report a stall");
                    assert!(!gpu.stalled(), "stalled() clears the flag");
                    assert_eq!(down::<f32>(gpu, &dx), before, "a combine that gave up and the ops after it must not run");
                }
                Err(e) => assert!(format!("{e}").contains("did not answer"), "{e}"),
            }
            // The next submission runs normally.
            gpu.add(dx.addr(), dx.addr(), n).unwrap();
            gpu.sync().unwrap();
            assert!(!gpu.stalled());
            assert_eq!(down::<f32>(gpu, &dx), before.iter().enumerate().map(|(i, v)| if i < n { v + v } else { *v }).collect::<Vec<_>>());
        }
    }
}

/// Decode attention time per call for the model's shape (16 query heads, 2 KV heads, head_dim 256), both kernels.
#[test]
#[ignore]
fn attn_decode_bandwidth() {
    for (bk, gpu) in common::backends_except(&["vulkan"]) {
        let gpu = &*gpu;
        eprintln!("backend {bk}");
        let (nh, nkv, hd) = (16, 2, 256);
        for n_pos in [1024, 2048, 4096, 16384, 32768] {
            let n = n_pos * nkv * hd;
            let h16: Vec<u16> = xs(n).iter().map(|x| half::f16::from_f32(*x).to_bits()).collect();
            let (dk, dv) = (up(gpu, &h16), up(gpu, &h16));
            for nt in [1, 2] {
                let (dq, dg) = (up(gpu, &xs(nt * nh * hd)), up(gpu, &xs(nt * nh * 2 * hd)));
                let steps: Vec<i32> = (0..nt).flat_map(|i| [(n_pos - nt + i) as i32, 0]).collect();
                let ds = up(gpu, &steps);
                let (dout, part) = (gpu.zeros::<f32>(nt * nh * hd).unwrap(), gpu.zeros::<f32>(nt * nh * ATT_SPLITS * (hd + 2)).unwrap());
                for gq_min in [i32::MAX, 0] {
                    let run = || gpu.attn_decode_gq(dq.addr(), dk.addr(), dv.addr(), dg.addr(), dout.addr(), part.addr(), ds.addr(),
                                                    nh, nkv, hd, 0.0625, gq_min, nt).unwrap();
                    let t0 = std::time::Instant::now();  // warm up long enough for the clocks to rise
                    while t0.elapsed().as_millis() < 300 { run(); gpu.sync().unwrap(); }
                    let t0 = std::time::Instant::now();
                    for _ in 0..200 { run(); }
                    gpu.sync().unwrap();
                    let s = t0.elapsed().as_secs_f64() / 200.0;
                    eprintln!("pos {n_pos:6} nt {nt} {}: {:7.1} us  {:5.0} GB/s", if gq_min == 0 { "gqa" } else { "g1 " }, s * 1e6, (2 * n * 2) as f64 / s / 1e9);
                }
            }
        }
    }
}


/// Random rows of `ty` with finite, non-degenerate block fields. Payload/code bytes stay random; every scale field
/// the CPU dequantizer reads is overwritten at its offset with a value in `[0.01, 0.02)` (`m` / `dmin` as noted):
///
/// | type | block | scale fields (byte offsets) |
/// | --- | --- | --- |
/// | F32 | 4 | one f32 value per element |
/// | F16 | 2 | one f16 value per element |
/// | BF16 | 2 | one bf16 value per element |
/// | Q2_0 | 18 | `d` f16 @0 |
/// | Q4_0 | 18 | `d` f16 @0 |
/// | Q5_0 | 22 | `d` f16 @0 |
/// | Q8_0 | 34 | `d` f16 @0 |
/// | Q4_1 | 20 | `d` f16 @0, `m` f16 @2 (`[-0.15, 0.05)`) |
/// | Q5_1 | 24 | `d` f16 @0, `m` f16 @2 (`[-0.15, 0.05)`) |
/// | Q2_K | 84 | `d` f16 @80, `dmin` f16 @82 (16 4-bit scale pairs @0 random) |
/// | Q3_K | 110 | `d` f16 @108 (6-bit scales @96 random) |
/// | Q4_K | 144 | `d` f16 @0, `dmin` f16 @2 (6 4-bit scale pairs @4 random) |
/// | Q5_K | 176 | `d` f16 @0, `dmin` f16 @2 (6 4-bit scale pairs @4 random) |
/// | Q6_K | 210 | `d` f16 @208 (8-bit scales @192 random) |
/// | IQ1_S | 50 | `d` f16 @0 |
/// | IQ1_M | 56 | `d` bits split over the top nibbles of the four u16 scale words @48..56 |
/// | IQ2_XXS | 66 | `d` f16 @0 |
/// | IQ2_XS | 74 | `d` f16 @0 |
/// | IQ2_S | 82 | `d` f16 @0 |
/// | IQ3_XXS | 98 | `d` f16 @0 |
/// | IQ3_S | 110 | `d` f16 @0 |
/// | IQ4_XS | 136 | `d` f16 @0 |
/// | IQ4_NL | 18 | `d` f16 @0 |
///
/// Every produced f32 is asserted finite, so a NaN/inf scale cannot mask a kernel bug later.
fn random_tensor(ty: GgmlType, rows: usize, cols: usize, seed: u32) -> Vec<u8> {
    let mut s = seed.wrapping_mul(2654435761) | 1;
    let mut rnd = move || { s ^= s << 13; s ^= s >> 17; s ^= s << 5; s };
    let scale = |rnd: &mut dyn FnMut() -> u32| half::f16::from_f32(0.01 + (rnd() % 100) as f32 * 1e-4).to_le_bytes();
    let data: Vec<u8> = match ty {
        GgmlType::F32 => (0..rows * cols).flat_map(|_| ((rnd() % 2001) as f32 / 1000.0 - 1.0).to_le_bytes()).collect(),
        GgmlType::F16 => (0..rows * cols).flat_map(|_| half::f16::from_f32((rnd() % 2001) as f32 / 1000.0 - 1.0).to_le_bytes()).collect(),
        GgmlType::BF16 => (0..rows * cols).flat_map(|_| half::bf16::from_f32((rnd() % 2001) as f32 / 1000.0 - 1.0).to_le_bytes()).collect(),
        _ => {
            let (bb, n) = (ty.block_bytes(), rows * (cols / ty.block_elems()));
            (0..n).flat_map(|_| {
                let mut b: Vec<u8> = (0..bb).map(|_| rnd() as u8).collect();
                match ty {
                    GgmlType::Q2K => { b[80..82].copy_from_slice(&scale(&mut rnd)); b[82..84].copy_from_slice(&scale(&mut rnd)); }
                    GgmlType::Q3K => b[108..110].copy_from_slice(&scale(&mut rnd)),
                    GgmlType::Q4K | GgmlType::Q5K => { b[0..2].copy_from_slice(&scale(&mut rnd)); b[2..4].copy_from_slice(&scale(&mut rnd)); }
                    GgmlType::Q6K => b[208..210].copy_from_slice(&scale(&mut rnd)),
                    GgmlType::Q4_1 | GgmlType::Q5_1 => {
                        b[0..2].copy_from_slice(&scale(&mut rnd));
                        b[2..4].copy_from_slice(&half::f16::from_f32(-0.15 + (rnd() % 100) as f32 * 2e-3).to_le_bytes());
                    }
                    GgmlType::IQ1M => {
                        // d is composed from the top nibbles of the four u16 scale words at 48..56 (src/quant/mod.rs:201).
                        let d = half::f16::from_f32(0.01 + (rnd() % 100) as f32 * 1e-4).to_bits();
                        for i in 0..4 {
                            let o = 48 + 2 * i;
                            let w = (u16::from_le_bytes([b[o], b[o + 1]]) & 0x0FFF) | (((d >> (4 * i)) & 0xF) << 12);
                            b[o..o + 2].copy_from_slice(&w.to_le_bytes());
                        }
                    }
                    _ => b[0..2].copy_from_slice(&scale(&mut rnd)),
                }
                b
            }).collect()
        }
    };
    let mut values = vec![0f32; rows * cols];
    rusting_strata::quant::dequant_row(ty, &data, &mut values);
    assert!(values.iter().all(|v| v.is_finite()), "{}: random block produced a non-finite value", ty.name());
    data
}

/// `random_tensor` gives every type a finite reference: no GPU needed, so the generator is checked on its own.
#[test]
fn random_tensor_scales_are_finite() {
    for ty in all_types() {
        for (rows, cols) in [(1, 256), (3, 512), (2, 2560)] {
            let d = random_tensor(ty, rows, cols, cols as u32 + ty as u32);
            assert_eq!(d.len(), ty.row_bytes(cols as u64) * rows, "{} bytes", ty.name());
            let mut v = vec![0f32; rows * cols];
            rusting_strata::quant::dequant_row(ty, &d, &mut v);
            assert!(v.iter().all(|f| f.is_finite()), "{} {rows}x{cols}", ty.name());
            assert!(v.iter().any(|&f| f != 0.0), "{} {rows}x{cols}: all-zero block", ty.name());
        }
    }
}

/// Every supported `GgmlType`, in the order `from_u32` accepts them.
fn all_types() -> Vec<GgmlType> {
    (0..64).filter_map(|i| GgmlType::from_u32(i).ok()).collect()
}

#[test]
fn gemv_partial_superblocks_and_q2_0() {
    for (bk, gpu) in common::backends_except(&[]) {
        let gpu = &*gpu;
        for ty in [GgmlType::Q2_0, GgmlType::Q8_0, GgmlType::IQ4NL, GgmlType::Q4_0, GgmlType::Q5_0, GgmlType::Q4_1, GgmlType::Q5_1, GgmlType::BF16, GgmlType::F32] {
            for cols in [640, 320, 2560] {
                if cols % ty.block_elems() != 0 { continue; }
                let (rows, nt, ne) = (40, 3, 4);  // ne experts of `rows` rows for moe_gemv
                let data = random_tensor(ty, ne * rows, cols, cols as u32 + ty as u32);
                let all = Tensor { ty, cols, rows: ne * rows, data: &data };
                let t = Tensor { rows, data: &data[..ty.row_bytes(cols as u64) * rows], ..all };
                // Raw bytes, as experts are uploaded (`Backend::upload` turns Q4_0 / Q5_0 into Q8_0).
                let raw = |t: &Tensor| { let b = gpu.alloc(t.data.len()).unwrap(); gpu.htod(t.data, &b, 0).unwrap(); GpuTensor::new(t.ty, t.rows, t.cols, b) };
                let (dt, dall) = (raw(&t), raw(&all));
                let what = format!("{bk} {} cols {cols}", ty.name());
                // dequant
                let dq = gpu.zeros::<f32>(rows * cols).unwrap();
                gpu.dequant(&dt, rows, dq.addr()).unwrap();
                let mut want = vec![0f32; rows * cols];
                for (r, out) in want.chunks_exact_mut(cols).enumerate() { t.row(r, out); }
                assert_eq!(down::<f32>(gpu, &dq), want, "{what}: dequant");
                // gemv, gemvn (nt inputs) and gemvq on quant_xq's x
                let x = xs(nt * cols + 5)[5..].to_vec();
                let dx = up(gpu, &x);
                let want: Vec<Vec<f32>> = x.chunks(cols).map(|xt| { let mut y = vec![0f32; rows]; t.matvec(&as_seen(ty, xt), &mut y); y }).collect();
                let check = |got: &[f32], t: usize, op: &str| {
                    let e = rel_l2(got, &want[t]);
                    assert!(e <= 1e-4, "{what}: {op} token {t} rel err {e}");
                };
                let dy = gpu.zeros::<f32>(nt * rows).unwrap();
                gpu.gemv(&dt, dx.addr(), dy.addr()).unwrap();
                check(&down::<f32>(gpu, &dy)[..rows], 0, "gemv");
                gpu.gemvn(&dt, dx.addr(), cols, dy.addr(), rows, nt).unwrap();
                let got = down::<f32>(gpu, &dy);
                for k in 0..nt { check(&got[k * rows..(k + 1) * rows], k, "gemvn"); }
                let xq = gpu.zeros::<u8>(nt * cols * 9 / 8).unwrap();
                gpu.quant_xq(dx.addr(), cols, cols, nt, xq.addr()).unwrap();
                let dz = gpu.zeros::<f32>(nt * rows).unwrap();
                gpu.gemvq(&dt, dx.addr(), cols, if ty.block_elems() > 1 { xq.addr() } else { 0 }, dz.addr(), rows, nt).unwrap();
                assert_eq!(down::<f32>(gpu, &dz), got, "{what}: gemvq on quant_xq vs gemvn");
                // moe_gemv: expert ids [3, -1, 1], token k / 1
                let ids = [3i32, -1, 1];
                let di = up(gpu, &ids);
                let dm = gpu.zeros::<f32>(3 * rows).unwrap();
                gpu.moe_gemv(ty, rows, cols, dall.ptr, dall.bytes() / ne, di.addr(), 3, dx.addr(), cols, 1, dm.addr(), None, 0).unwrap();
                let got = down::<f32>(gpu, &dm);
                for (k, &e) in ids.iter().enumerate() {
                    let g = &got[k * rows..(k + 1) * rows];
                    if e < 0 { assert!(g.iter().all(|&v| v == 0.0), "{what}: skipped slot written"); continue; }
                    let mut w = vec![0f32; rows];
                    all.expert(e as usize, ne).matvec(&as_seen(ty, &x[k * cols..(k + 1) * cols]), &mut w);
                    let err = rel_l2(g, &w);
                    assert!(err <= 1e-4, "{what}: moe_gemv expert {e} rel err {err}");
                }
                // Prefill GEMM over 130 positions (a full and a partial tile), K in 64-deep steps.
                let m = 130;
                let xm = xs(m * cols);
                let (dxm, dym) = (up(gpu, &xm), gpu.zeros::<f32>(m * rows).unwrap());
                gpu.gemm_dense(&dt, m, dxm.addr(), cols, dym.addr(), rows, 0).unwrap();
                let mut wr = vec![0f32; cols];
                let mut want = vec![0f32; m * rows];
                for r in 0..rows {
                    t.row(r, &mut wr);
                    for (i, xv) in xm.chunks(cols).enumerate() {
                        want[i * rows + r] = if gpu.mmq(ty) && cols % 128 == 0 { wr.iter().zip(as_seen(ty, xv)).map(|(a, b)| a * b).sum() }
                                             else { wr.iter().zip(xv).map(|(a, b)| f16_in(bk, *a) * f16_in(bk, *b)).sum() };
                    }
                }
                let e = rel_l2(&down::<f32>(gpu, &dym), &want);
                assert!(e <= 1e-4, "{what}: gemm rel err {e}");
            }
        }
        // swiglu_q on rows of 640: the bytes quant_xq gives for swiglu's output.
        let (n, rows) = (640, 3);
        let (g, u) = (xs(rows * n), xs(rows * n + 9)[9..].to_vec());
        let (dg, du, dg2) = (up(gpu, &g), up(gpu, &u), up(gpu, &g));
        let (q1, q2) = (gpu.zeros::<u8>(rows * n * 9 / 8).unwrap(), gpu.zeros::<u8>(rows * n * 9 / 8).unwrap());
        assert_eq!(gpu.swiglu_q(dg.addr(), du.addr(), n, rows, q1.addr()).unwrap(), q1.addr());
        gpu.swiglu(dg2.addr(), du.addr(), rows * n).unwrap();
        gpu.quant_xq(dg2.addr(), n, n, rows, q2.addr()).unwrap();
        assert_eq!(down::<u8>(gpu, &q1), down::<u8>(gpu, &q2), "{bk}: swiglu_q of 640");
    }
}

/// Per-type Vulkan pass/fail matrix over all 23 `GgmlType` variants: dequant, GEMV/GEMV-N/GEMV-Q, MoE GEMV, dense
/// and tiled GEMM, plus each type's largest shared-memory request. Synthetic raw blocks bypass `Backend::upload`, so
/// native kernels run even for the types the loader converts (F16, Q4_0, Q5_0). Vulkan only: run it with
/// `STRATA_TEST_BACKENDS=vulkan`. Prints one `MATRIX ty=...` line per type for `docs/V100-results.md`.
#[test]
fn vulkan_type_matrix() {
    let Ok(g) = rusting_strata::vulkan::Vk::new(0) else { return eprintln!("SKIP: no Vulkan device"); };
    let gpu: &dyn Backend = &g;
    let not_impl = |e: &anyhow::Error| format!("{e:#}").contains("not implemented");
    let types = all_types();
    assert_eq!(types.len(), 23, "GgmlType variants");
    let (rows, ne, cols, nt) = (40, 4, 256, 3);
    let mut failures = 0;
    for ty in types {
        let smem = match g.max_shared_bytes(&[ty]) {
            Ok(b) => b,
            Err(e) => { eprintln!("MATRIX ty={} dequant=fail gemv=fail gemvn=fail gemvq=fail moe_gemv=fail gemm_dense=fail gemm=fail smem=? note=preflight: {e:#}", ty.name()); failures += 1; continue; }
        };
        if let Err(e) = g.preflight(&[ty], true) {
            eprintln!("MATRIX ty={} dequant=fail gemv=fail gemvn=fail gemvq=fail moe_gemv=fail gemm_dense=fail gemm=fail smem={smem} note=preflight: {e:#}", ty.name());
            failures += 1;
            continue;
        }
        if ty == GgmlType::F16 {
            eprintln!("MATRIX ty={} dequant=unsupported gemv=unsupported gemvn=unsupported gemvq=unsupported moe_gemv=unsupported gemm_dense=unsupported gemm=unsupported smem={smem} note=no F16 shader path; loader uploads it as F32", ty.name());
            continue;
        }
        let (mut dequant, mut gemv, mut gemvn, mut gemvq, mut moe_gemv, mut gemm_dense, mut gemm) =
            ("pass", "pass", "pass", "pass", "pass", "pass", "pass");
        let mut note = if matches!(ty, GgmlType::Q4_0 | GgmlType::Q5_0) { "native bytes; loader uploads Q8_0".to_string() } else { String::new() };
        // The f16 GEMM path converts its operands with packFloat2x16; on this Volta driver OpFConvert truncates.
        if matches!(ty, GgmlType::F32 | GgmlType::BF16 | GgmlType::IQ2XS | GgmlType::IQ2S) {
            note = format!("{note}{}f16 GEMM inputs truncate (Volta OpFConvert); reference matches", if note.is_empty() { "" } else { "; " });
        }
        let data = random_tensor(ty, ne * rows, cols, cols as u32 + ty as u32);
        let all = Tensor { ty, cols, rows: ne * rows, data: &data };
        let t = Tensor { rows, data: &data[..ty.row_bytes(cols as u64) * rows], ..all };
        // Raw bytes, as experts are uploaded.
        let raw = |t: &Tensor| {
            let b = gpu.alloc(t.data.len()).unwrap();
            gpu.htod(t.data, &b, 0).unwrap();
            GpuTensor::new(t.ty, t.rows, t.cols, b)
        };
        let (dt, dall) = (raw(&t), raw(&all));
        // dequant
        let dq = gpu.zeros::<f32>(rows * cols).unwrap();
        match gpu.dequant(&dt, rows, dq.addr()) {
            Ok(()) => {
                let got = down::<f32>(gpu, &dq);
                let mut want = vec![0f32; rows * cols];
                for (r, out) in want.chunks_exact_mut(cols).enumerate() { t.row(r, out); }
                let scale = want.iter().fold(0f32, |m, v| m.max(v.abs())).max(1e-30);
                let diff = got.iter().zip(&want).fold(0f32, |m, (a, b)| m.max((a - b).abs()));
                if diff > 1e-5 * scale { dequant = "fail"; note = format!("dequant max diff {diff} vs scale {scale}"); }
            }
            Err(e) if not_impl(&e) => { dequant = "unsupported"; note = format!("dequant: {e:#}"); }
            Err(e) => panic!("{}: dequant: {e:#}", ty.name()),
        }
        // gemv, gemvn and gemvq on the same quant_xq input
        let x = xs(nt * cols + 5)[5..].to_vec();
        let dx = up(gpu, &x);
        let want: Vec<Vec<f32>> = x.chunks(cols).map(|xt| { let mut y = vec![0f32; rows]; t.matvec(&as_seen(ty, xt), &mut y); y }).collect();
        let dy = gpu.zeros::<f32>(nt * rows).unwrap();
        match gpu.gemv(&dt, dx.addr(), dy.addr()) {
            Ok(()) => {
                let e = rel_l2(&down::<f32>(gpu, &dy)[..rows], &want[0]);
                if e > 1e-4 { gemv = "fail"; note = format!("gemv rel err {e}"); }
            }
            Err(e) if not_impl(&e) => { gemv = "unsupported"; note = format!("gemv: {e:#}"); }
            Err(e) => panic!("{}: gemv: {e:#}", ty.name()),
        }
        let mut gemvn_got: Option<Vec<f32>> = None;
        match gpu.gemvn(&dt, dx.addr(), cols, dy.addr(), rows, nt) {
            Ok(()) => {
                let got = down::<f32>(gpu, &dy);
                for k in 0..nt {
                    let e = rel_l2(&got[k * rows..(k + 1) * rows], &want[k]);
                    if e > 1e-4 { gemvn = "fail"; note = format!("gemvn token {k} rel err {e}"); }
                }
                gemvn_got = Some(got);
            }
            Err(e) if not_impl(&e) => { gemvn = "unsupported"; note = format!("gemvn: {e:#}"); }
            Err(e) => panic!("{}: gemvn: {e:#}", ty.name()),
        }
        let xq = gpu.zeros::<u8>(nt * cols * 9 / 8).unwrap();
        let dz = gpu.zeros::<f32>(nt * rows).unwrap();
        match gpu.quant_xq(dx.addr(), cols, cols, nt, xq.addr()).and_then(|()| gpu.gemvq(&dt, dx.addr(), cols, xq.addr(), dz.addr(), rows, nt)) {
            Ok(()) => {
                let got = down::<f32>(gpu, &dz);
                match &gemvn_got {
                    Some(w) if got.iter().zip(w).any(|(a, b)| a.to_bits() != b.to_bits()) => { gemvq = "fail"; note = format!("gemvq differs from gemvn on quant_xq: {note}"); }
                    _ => {}
                }
            }
            Err(e) if not_impl(&e) => { gemvq = "unsupported"; note = format!("gemvq: {e:#}"); }
            Err(e) => panic!("{}: gemvq: {e:#}", ty.name()),
        }
        // moe_gemv: the first expert, a skipped (-1) slot and the last expert.
        let ids = [0i32, -1, ne as i32 - 1];
        let di = up(gpu, &ids);
        let dm = gpu.zeros::<f32>(3 * rows).unwrap();
        match gpu.moe_gemv(ty, rows, cols, dall.ptr, dall.bytes() / ne, di.addr(), 3, dx.addr(), cols, 1, dm.addr(), None, 0) {
            Ok(()) => {
                let got = down::<f32>(gpu, &dm);
                for (k, &e) in ids.iter().enumerate() {
                    let g = &got[k * rows..(k + 1) * rows];
                    if e < 0 {
                        if g.iter().any(|&v| v != 0.0) { moe_gemv = "fail"; note = format!("moe_gemv wrote skipped slot {k}: {note}"); }
                        continue;
                    }
                    let mut w = vec![0f32; rows];
                    all.expert(e as usize, ne).matvec(&as_seen(ty, &x[k * cols..(k + 1) * cols]), &mut w);
                    let err = rel_l2(g, &w);
                    if err > 1e-4 { moe_gemv = "fail"; note = format!("moe_gemv expert {e} rel err {err}: {note}"); }
                }
            }
            Err(e) if not_impl(&e) => { moe_gemv = "unsupported"; note = format!("moe_gemv: {e:#}"); }
            Err(e) => panic!("{}: moe_gemv: {e:#}", ty.name()),
        }
        // Dense GEMM over 130 positions (a full and a partial tile) and the tiled `gemm` entry point with 3 tiles.
        let m = 130;
        let xm = xs(m * cols);
        let (dxm, dym) = (up(gpu, &xm), gpu.zeros::<f32>(m * rows).unwrap());
        match gpu.gemm_dense(&dt, m, dxm.addr(), cols, dym.addr(), rows, 0) {
            Ok(()) => {
                let mut wr = vec![0f32; cols];
                let mut want = vec![0f32; m * rows];
                for r in 0..rows {
                    t.row(r, &mut wr);
                    for (i, xv) in xm.chunks(cols).enumerate() {
                        want[i * rows + r] = if gpu.mmq(ty) && cols % 128 == 0 { wr.iter().zip(as_seen(ty, xv)).map(|(a, b)| a * b).sum() }
                                             else { wr.iter().zip(xv).map(|(a, b)| f16_in("vulkan", *a) * f16_in("vulkan", *b)).sum() };
                    }
                }
                let e = rel_l2(&down::<f32>(gpu, &dym), &want);
                if e > 1e-4 { gemm_dense = "fail"; note = format!("gemm_dense rel err {e}: {note}"); }
            }
            Err(e) if not_impl(&e) => { gemm_dense = "unsupported"; note = format!("gemm_dense: {e:#}"); }
            Err(e) => panic!("{}: gemm_dense: {e:#}", ty.name()),
        }
        let (n_x, mt) = (50, 170);
        let xr: Vec<f32> = xs(n_x * cols);
        let xrow: Vec<i32> = (0..mt).map(|i| ((i * 7) % n_x) as i32).collect();
        let tiles: Vec<u64> = [(0u64, 128u64), (128, 16), (144, 26)].iter().flat_map(|&(m0, c)| [dt.ptr, m0 | c << 32]).collect();
        let (dtl, dxr, drow) = (up(gpu, &tiles), up(gpu, &xr), up(gpu, &xrow));
        let dyt = gpu.zeros::<f32>(mt * rows).unwrap();
        match gpu.gemm(ty, rows, cols, dtl.addr(), 3, dxr.addr(), cols, n_x, drow.addr(), dyt.addr(), rows, 0) {
            Ok(()) => {
                let got = down::<f32>(gpu, &dyt);
                let mut wr = vec![0f32; cols];
                let mut want = vec![0f32; mt * rows];
                for r in 0..rows {
                    t.row(r, &mut wr);
                    for (i, &xri) in xrow.iter().enumerate() {
                        let xv = &xr[xri as usize * cols..][..cols];
                        want[i * rows + r] = if gpu.mmq(ty) && cols % 128 == 0 { wr.iter().zip(as_seen(ty, xv)).map(|(a, b)| a * b).sum() }
                                             else { wr.iter().zip(xv).map(|(a, b)| f16_in("vulkan", *a) * f16_in("vulkan", *b)).sum() };
                    }
                }
                let e = rel_l2(&got, &want);
                if e > 1e-4 { gemm = "fail"; note = format!("gemm rel err {e}: {note}"); }
            }
            Err(e) if not_impl(&e) => { gemm = "unsupported"; note = format!("gemm: {e:#}"); }
            Err(e) => panic!("{}: gemm: {e:#}", ty.name()),
        }
        if [dequant, gemv, gemvn, gemvq, moe_gemv, gemm_dense, gemm].contains(&"fail") { failures += 1; }
        eprintln!("MATRIX ty={} dequant={dequant} gemv={gemv} gemvn={gemvn} gemvq={gemvq} moe_gemv={moe_gemv} \
            gemm_dense={gemm_dense} gemm={gemm} smem={smem} note={note}", ty.name());
    }
    assert_eq!(failures, 0, "type matrix failures");
}

/// qwen4exp hyper-connection and PLE kernels against loops over the same f32 inputs.
#[test]
fn hc_and_ple_kernels_match_reference() {
    let sig = |x: f32| 1.0 / (1.0 + (-x).exp());
    let (n, hc, nt) = (300, 4, 3);
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        let near = |what: &str, got: &[f32], want: &[f32]| {
            let e = rel_l2(got, want);
            assert!(e <= 1e-5, "{bk} {what}: rel err {e}");
        };
        // hc_silu (and hc_mix below) on values past expf's overflow: silu(-100) is -0, not 0 / inf = NaN.
        let x: Vec<f32> = xs(nt * n).iter().map(|v| 400.0 * v).collect();
        let b = up(gpu, &x);
        gpu.hc_silu(b.addr(), 0.25, nt * n).unwrap();
        near("hc_silu", &down::<f32>(gpu, &b), &x.iter().map(|v| v * 0.25 * sig(v * 0.25)).collect::<Vec<_>>());
        // hc_mix
        let (xn, g) = (xs(nt * hc * n + 7)[7..].to_vec(), xs(nt * hc * n + 3)[3..].iter().map(|v| 120.0 * v).collect::<Vec<f32>>());
        let out = gpu.zeros::<f32>(nt * n).unwrap();
        gpu.hc_mix(up(gpu, &xn).addr(), up(gpu, &g).addr(), out.addr(), n, hc, nt).unwrap();
        let want: Vec<f32> = (0..nt * n).map(|j| {
            let (t, i) = (j / n, j % n);
            (0..hc).map(|c| xn[(t * hc + c) * n + i] * sig(g[(t * hc + c) * n + i]) / hc as f32).sum()
        }).collect();
        near("hc_mix", &down::<f32>(gpu, &out), &want);
        // hc_write, then clear
        let (r0, o, inj) = (xs(nt * hc * n + 1)[1..].to_vec(), xs(nt * n + 5)[5..].to_vec(), xs(nt * hc + 2)[2..].iter().map(|v| 4.0 * v).collect::<Vec<f32>>());
        let (r, ob) = (up(gpu, &r0), up(gpu, &o));
        gpu.hc_write(r.addr(), ob.addr(), up(gpu, &inj).addr(), n, hc, nt, true).unwrap();
        let want: Vec<f32> = (0..nt * hc * n).map(|j| {
            let (t, c, i) = (j / (hc * n), j / n % hc, j % n);
            r0[j] + o[t * n + i] * 2.0 * sig(inj[t * hc + c] / hc as f32)
        }).collect();
        near("hc_write", &down::<f32>(gpu, &r), &want);
        assert!(down::<f32>(gpu, &ob).iter().all(|&v| v == 0.0), "{bk} hc_write clear");
        // ple_gate
        let (key, query, value) = (xs(nt * hc * n + 11)[11..].to_vec(), xs(nt * hc * n + 13)[13..].to_vec(), xs(nt * n + 17)[17..].to_vec());
        let gated = gpu.zeros::<f32>(nt * hc * n).unwrap();
        gpu.ple_gate(up(gpu, &key).addr(), up(gpu, &query).addr(), up(gpu, &value).addr(), gated.addr(), n, hc, nt).unwrap();
        let want: Vec<f32> = (0..nt * hc).flat_map(|row| {
            let s: f32 = (0..n).map(|i| key[row * n + i] * query[row * n + i]).sum::<f32>() / (n as f32).sqrt();
            let gate = sig(s.signum() * s.abs().max(1e-6).sqrt());
            let t = row / hc;
            (0..n).map(|i| value[t * n + i] * gate).collect::<Vec<f32>>()
        }).collect();
        near("ple_gate", &down::<f32>(gpu, &gated), &want);
        // ple_conv over 40 positions: one token at a time, then the same in chunks of 5
        let (d, npos) = (hc * n, 40);
        let kw = xs(4 * d + 19)[19..].to_vec();
        let (gall, nall, rall) = (xs(npos * d + 23)[23..].to_vec(), xs(npos * d + 29)[29..].to_vec(), xs(npos * d + 31)[31..].to_vec());
        let want: Vec<f32> = (0..npos * d).map(|j| {
            let (q, i) = (j / d, j % d);
            let mut acc = kw[i * 4 + 3] * nall[j];
            for k in 0..3 { if q + 3 * k >= 9 { acc += kw[i * 4 + k] * nall[(q + 3 * k - 9) * d + i]; } }
            rall[j] + gall[j] + acc * sig(acc)
        }).collect();
        for chunk in [1, 5] {
            let ring = gpu.zeros::<f32>(16 * d).unwrap();
            let kb = up(gpu, &kw);
            let mut got = vec![];
            for p0 in (0..npos).step_by(chunk) {
                let s = |v: &[f32]| v[p0 * d..(p0 + chunk) * d].to_vec();
                let rb = up(gpu, &s(&rall));
                gpu.ple_conv(rb.addr(), up(gpu, &s(&gall)).addr(), up(gpu, &s(&nall)).addr(), kb.addr(), ring.addr(),
                             up(gpu, &[p0 as i32]).addr(), d, chunk).unwrap();
                got.extend(down::<f32>(gpu, &rb));
            }
            near(&format!("ple_conv chunk {chunk}"), &got, &want);
        }
    }
}

/// An F16 weight (InstinctRazor-Qwen3.5-122B has two, `blk.0.attn_gate` and `blk.0.ssm_out`) uploads as F32 and gives
/// the products of the F16 values through the decode and prefill paths.
#[test]
fn f16_weight_uploads_as_f32() {
    let (rows, cols) = (96, 512);
    let w: Vec<f32> = xs(rows * cols).iter().map(|v| v * 3.0).collect();
    let data: Vec<u8> = w.iter().flat_map(|v| half::f16::from_f32(*v).to_bits().to_le_bytes()).collect();
    let t = Tensor { ty: GgmlType::F16, rows, cols, data: &data };
    let wf: Vec<f32> = w.iter().map(|v| half::f16::from_f32(*v).to_f32()).collect();
    let nt = 40;
    let x = xs(nt * cols);
    let want: Vec<f32> = (0..nt * rows).map(|i| {
        let (m, r) = (i / rows, i % rows);
        (0..cols).map(|c| wf[r * cols + c] as f64 * x[m * cols + c] as f64).sum::<f64>() as f32
    }).collect();
    for (bk, gpu) in common::backends() {
        let gpu = &*gpu;
        let dt = gpu.upload(&t).unwrap();
        assert_eq!(dt.ty, GgmlType::F32, "{bk}");
        let dx = up(gpu, &x);
        let dy = gpu.zeros::<f32>(rows).unwrap();
        gpu.gemv(&dt, dx.addr(), dy.addr()).unwrap();
        let e = rel_l2(&down::<f32>(gpu, &dy), &want[..rows]);
        assert!(e <= 1e-5, "{bk} gemv rel err {e}");
        let dy = gpu.zeros::<f32>(4 * rows).unwrap();
        gpu.gemvn(&dt, dx.addr(), cols, dy.addr(), rows, 4).unwrap();
        let e = rel_l2(&down::<f32>(gpu, &dy), &want[..4 * rows]);
        assert!(e <= 1e-5, "{bk} gemvn rel err {e}");
        let dy = gpu.zeros::<f32>(nt * rows).unwrap();
        gpu.gemm_dense(&dt, nt, dx.addr(), cols, dy.addr(), rows, 0).unwrap();
        // The prefill path converts x and w to f16; the decode paths above read them as f32.
        let wantg: Vec<f32> = (0..nt * rows).map(|i| {
            let (m, r) = (i / rows, i % rows);
            (0..cols).map(|c| f16_in(bk, wf[r * cols + c]) as f64 * f16_in(bk, x[m * cols + c]) as f64).sum::<f64>() as f32
        }).collect();
        let e = rel_l2(&down::<f32>(gpu, &dy), &wantg);
        eprintln!("{bk}: gemm_dense rel err {e:.2e}");
        assert!(e <= 1e-5, "{bk} gemm_dense rel err {e}");
    }
}

/// Exercise logical warp scans across both halves of wave64, with tied QSA scores.
#[test]
fn qsa_selection_orders_tied_blocks() {
    let (nbs, top) = (2048usize, 73usize);
    let sst = 1 + 4 * top;
    for (bk, gpu) in common::backends() {
        let g = &*gpu;
        let q = up(g, &vec![1.0f32; 512]);
        let pool = up(g, &(0..nbs).flat_map(|b| std::iter::repeat_n((b % 50) as f32, 128)).collect::<Vec<_>>());
        let scores = g.zeros::<f32>(nbs).unwrap();
        let selected = g.zeros::<i32>(sst).unwrap();
        let step = up(g, &[(4 * nbs - 1) as i32, 0]);
        g.qsa_select(q.addr(), pool.addr(), scores.addr(), selected.addr(), 0, step.addr(), 0, 1, nbs, top, sst, 0).unwrap();
        let mut blocks: Vec<usize> = (0..nbs).collect();
        blocks.sort_by_key(|b| (std::cmp::Reverse(b % 50), *b));
        blocks.truncate(top);
        blocks.sort_unstable();
        let want: Vec<i32> = blocks.iter().flat_map(|b| (0..4).map(move |k| (4 * b + k) as i32)).collect();
        let got = down::<i32>(g, &selected);
        assert_eq!(got[0], (4 * top) as i32, "{bk}: count");
        assert_eq!(&got[1..], want.as_slice(), "{bk}: selection");
    }
}
