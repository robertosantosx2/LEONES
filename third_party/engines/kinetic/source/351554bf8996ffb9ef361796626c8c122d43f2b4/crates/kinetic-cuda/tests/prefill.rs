//! The large-batch mixer kernels against the decode kernels run in steps of
//! [`MAX_BATCH`] over the same tokens, and a following step against the
//! states each path leaves. Each test passes with a message when no CUDA
//! device or no kernels exist.

mod common;

use common::{gpu, Gpu, Lcg};
use kinetic_cuda::{
    AttentionIo, AttentionParams, AttentionShape, Batch, ConvState, DeltaIo, DeltaParams,
    DeltaShape, DeltaState, DeviceBuffer, Flow, GemvInput, KvCache, KvType, MAX_BATCH,
};

/// Tokens of the prompt; leaves a partial tile and chunk.
const PROMPT: usize = 150;

fn random(rng: &mut Lcg, len: usize, scale: f32) -> Vec<f32> {
    (0..len).map(|_| rng.f32() * scale).collect()
}

fn upload(gpu: &Gpu, v: &[f32]) -> DeviceBuffer<f32> {
    DeviceBuffer::from_slice(&gpu.ctx, v).unwrap()
}

/// Rows `range` of `per_token` values each from `all`, on the device.
fn rows(
    gpu: &Gpu,
    all: &[f32],
    range: std::ops::Range<usize>,
    per_token: usize,
) -> DeviceBuffer<f32> {
    upload(gpu, &all[range.start * per_token..range.end * per_token])
}

/// Asserts `got` is within `tol` of `want` relative to the largest value.
fn assert_close(what: &str, got: &[f32], want: &[f32], tol: f32) {
    let scale = want.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    for (i, (g, w)) in got.iter().zip(want).enumerate() {
        assert!(
            (g - w).abs() <= tol * scale,
            "{what}: element {i} is {g}, expected {w} (scale {scale})"
        );
    }
}

/// Runs `prompt` tokens then one decode step of MAX_BATCH more through
/// `step(first, n, out)` either all at once or in steps of MAX_BATCH, and
/// returns every output row.
fn outputs(
    total: usize,
    batched: bool,
    mut step: impl FnMut(usize, usize) -> Vec<f32>,
) -> Vec<f32> {
    let mut out = Vec::new();
    let mut start = 0;
    while start < total {
        let n = if batched && start == 0 {
            PROMPT
        } else {
            MAX_BATCH.min(total - start)
        };
        out.extend(step(start, n));
        start += n;
    }
    out
}

/// Every output row of [`outputs`] for random attention inputs over a cache
/// storing keys as `k` and values as `v`.
fn attention_outputs(
    gpu: &Gpu,
    shape: AttentionShape,
    [kt, vt]: [KvType; 2],
    batched: bool,
) -> Vec<f32> {
    let total = PROMPT + MAX_BATCH;
    let (hd, kv_dim) = (shape.head_dim, shape.n_head_kv * shape.head_dim);
    let mut rng = Lcg(shape.head_dim as u64 + shape.window.unwrap_or(0) as u64);
    let q_all = random(&mut rng, total * shape.q_len(), 2.0);
    let k_all = random(&mut rng, total * kv_dim, 2.0);
    let v_all = random(&mut rng, total * kv_dim, 1.0);
    let gate_all = random(&mut rng, total * shape.n_head, 2.0);
    let q_norm = upload(gpu, &random(&mut rng, hd, 1.0));
    let k_norm = upload(gpu, &random(&mut rng, hd, 1.0));
    let width = shape.n_head * hd;

    let slots = shape.window.map_or(total, |w| w + PROMPT);
    let mut cache = KvCache::with_types(&gpu.ctx, &shape, slots, kt, vt).unwrap();
    {
        let mut batch = Batch::new(&gpu.ctx, PROMPT).unwrap();
        let mut out = GemvInput::batch(&gpu.ctx, width, PROMPT).unwrap();
        let mut scratch = DeviceBuffer::new(&gpu.ctx, shape.scratch_len(MAX_BATCH, slots)).unwrap();
        outputs(total, batched, |first, n| {
            let range = first..first + n;
            batch.set(first, &vec![0; n], &gpu.stream).unwrap();
            let mut q = rows(gpu, &q_all, range.clone(), shape.q_len());
            let mut k = rows(gpu, &k_all, range.clone(), kv_dim);
            let v = rows(gpu, &v_all, range.clone(), kv_dim);
            let gates = rows(gpu, &gate_all, range, shape.n_head);
            let params = AttentionParams {
                shape: &shape,
                q_norm: Some(&q_norm),
                k_norm: Some(&k_norm),
                rope_factors: None,
                q_bias: None,
                k_bias: None,
                v_bias: None,
                store: true,
            };
            let io = AttentionIo {
                q: &mut q,
                k: &mut k,
                v: &v,
                head_gate: (!shape.interleaved_gate).then_some(&gates),
                scratch: &mut scratch,
                out: &mut out,
            };
            gpu.kernels
                .attention(params, io, &mut cache, &batch, &gpu.stream)
                .unwrap();
            let mut values = vec![0.0; n * width];
            out.values().copy_range_to(0, &mut values).unwrap();
            values
        })
    }
}

fn check_attention(shape: AttentionShape) {
    let Some(gpu) = gpu() else { return };
    let f16 = [KvType::F16; 2];
    let steps = attention_outputs(&gpu, shape, f16, false);
    let batched = attention_outputs(&gpu, shape, f16, true);
    assert_close(&format!("attention {shape:?}"), &batched, &steps, 1e-5);
}

fn attention_shape(
    head_dim: usize,
    window: Option<usize>,
    interleaved_gate: bool,
) -> AttentionShape {
    AttentionShape {
        n_head: 4,
        n_head_kv: 2,
        head_dim,
        rope_dims: head_dim / 2,
        rope_base: 10000.0,
        rope_adjacent: false,
        rope_mscale: 1.0,
        norm_after_rope: false,
        scale: 1.0 / (head_dim as f32).sqrt(),
        eps: 1e-6,
        window,
        interleaved_gate,
        v_norm: false,
    }
}

#[test]
fn flash_attention_matches_steps() {
    check_attention(attention_shape(512, None, false));
    check_attention(attention_shape(256, None, true));
    check_attention(attention_shape(128, None, false));
    check_attention(attention_shape(64, None, false));
}

#[test]
fn windowed_flash_attention_matches_steps() {
    check_attention(attention_shape(128, Some(40), false));
    check_attention(attention_shape(256, Some(100), true));
}

#[test]
fn q8_0_cache_stays_close_to_f16() {
    let Some(gpu) = gpu() else { return };
    for shape in [
        attention_shape(256, None, true),
        attention_shape(64, Some(40), false),
    ] {
        let exact = attention_outputs(&gpu, shape, [KvType::F16; 2], false);
        for types in [
            [KvType::Q8_0; 2],
            [KvType::Q8_0, KvType::F16],
            [KvType::F16, KvType::Q8_0],
        ] {
            let steps = attention_outputs(&gpu, shape, types, false);
            assert_close(&format!("{types:?} {shape:?}"), &steps, &exact, 2e-2);
            // the flash kernel widens q8_0 to f16 tiles
            let batched = attention_outputs(&gpu, shape, types, true);
            assert_close(
                &format!("flash {types:?} {shape:?}"),
                &batched,
                &steps,
                2e-3,
            );
        }
    }
}

#[test]
fn q8_0_cache_saves_and_loads_unchanged() {
    let Some(gpu) = gpu() else { return };
    let shape = attention_shape(128, None, false);
    let slots = 8;
    let len = slots * shape.n_head_kv * shape.head_dim;
    let mut rng = Lcg(3);
    let (k, v) = (random(&mut rng, len, 3.0), random(&mut rng, len, 0.5));
    let mut cache =
        KvCache::with_types(&gpu.ctx, &shape, slots, KvType::Q8_0, KvType::Q8_0).unwrap();
    cache.load(0, &k, &v).unwrap();
    let (k1, v1) = cache.save(0..slots).unwrap();
    assert_close("q8_0 keys", &k1, &k, 1e-2);
    cache.load(0, &k1, &v1).unwrap();
    assert_eq!(cache.save(0..slots).unwrap(), (k1, v1));
}

#[test]
fn chunked_delta_rule_matches_steps() {
    let Some(gpu) = gpu() else { return };
    let shape = DeltaShape {
        n_k_heads: 2,
        n_v_heads: 4,
        head_k_dim: 128,
        head_v_dim: 128,
        conv_taps: 4,
        eps: 1e-6,
    };
    let total = PROMPT + MAX_BATCH;
    let (ch, vd, nv) = (shape.channels(), shape.value_dim(), shape.n_v_heads);
    let mut rng = Lcg(3);
    let qkv_all = random(&mut rng, total * ch, 2.0);
    let z_all = random(&mut rng, total * vd, 2.0);
    let alpha_all = random(&mut rng, total * nv, 3.0);
    let beta_all = random(&mut rng, total * nv, 3.0);
    let conv = upload(&gpu, &random(&mut rng, ch * shape.conv_taps, 1.0));
    let dt_bias = upload(&gpu, &random(&mut rng, nv, 1.0));
    let a: Vec<f32> = (0..nv).map(|_| -(rng.f32().abs() + 0.1)).collect();
    let a = upload(&gpu, &a);
    let norm = upload(&gpu, &random(&mut rng, shape.head_v_dim, 1.0));
    let params = DeltaParams {
        shape: &shape,
        conv: &conv,
        dt_bias: &dt_bias,
        a: &a,
        norm: &norm,
    };

    let run = |batched: bool| {
        let mut state = DeltaState::new(&gpu.ctx, &shape, MAX_BATCH).unwrap();
        let mut batch = Batch::new(&gpu.ctx, PROMPT).unwrap();
        let mut out = GemvInput::batch(&gpu.ctx, vd, PROMPT).unwrap();
        let mut scratch = DeviceBuffer::new(&gpu.ctx, shape.scratch_len(PROMPT)).unwrap();
        outputs(total, batched, |first, n| {
            let range = first..first + n;
            batch.set(first, &vec![0; n], &gpu.stream).unwrap();
            let qkv = rows(&gpu, &qkv_all, range.clone(), ch);
            let z = rows(&gpu, &z_all, range.clone(), vd);
            let alpha = rows(&gpu, &alpha_all, range.clone(), nv);
            let beta = rows(&gpu, &beta_all, range, nv);
            let io = DeltaIo {
                qkv: &qkv,
                z: &z,
                alpha: &alpha,
                beta: &beta,
                scratch: &mut scratch,
                out: &mut out,
            };
            gpu.kernels
                .delta_net(params, io, &mut state, Flow::Commit, &batch, &gpu.stream)
                .unwrap();
            let mut values = vec![0.0; n * vd];
            out.values().copy_range_to(0, &mut values).unwrap();
            values
        })
    };
    let (steps, batched) = (run(false), run(true));
    assert_close("delta rule", &batched, &steps, 1e-5);
}

#[test]
fn batched_short_conv_matches_steps() {
    let Some(gpu) = gpu() else { return };
    let (channels, taps) = (256, 3);
    let total = PROMPT + MAX_BATCH;
    let mut rng = Lcg(5);
    let bcx_all = random(&mut rng, total * 3 * channels, 2.0);
    let conv = upload(&gpu, &random(&mut rng, channels * taps, 1.0));

    let run = |batched: bool| {
        let mut state = ConvState::new(&gpu.ctx, channels, taps, MAX_BATCH).unwrap();
        let mut batch = Batch::new(&gpu.ctx, PROMPT).unwrap();
        let mut out = GemvInput::batch(&gpu.ctx, channels, PROMPT).unwrap();
        outputs(total, batched, |first, n| {
            batch.set(first, &vec![0; n], &gpu.stream).unwrap();
            let bcx = rows(&gpu, &bcx_all, first..first + n, 3 * channels);
            gpu.kernels
                .short_conv(&conv, &bcx, &mut state, &mut out, &batch, &gpu.stream)
                .unwrap();
            let mut values = vec![0.0; n * channels];
            out.values().copy_range_to(0, &mut values).unwrap();
            values
        })
    };
    let (steps, batched) = (run(false), run(true));
    assert_close("short convolution", &batched, &steps, 1e-6);
}
