//! Routed-expert kernels against `kinetic_quant::dequantize` and f64 dot
//! products of the quantized inputs. Each test passes with a message when
//! no CUDA device or no kernels exist.

use std::rc::Rc;

use half::f16;
use kinetic_cuda::{
    Context, Device, DeviceBuffer, Error, ExpertArena, ExpertGroup, ExpertMix, ExpertProduct,
    ExpertTables, GateLogits, Kernels, Q8kRows, Stream, EXPERT_TYPES, Q8K_BLOCK,
};
use kinetic_quant::{dequantize, TensorType};

struct Gpu {
    ctx: Rc<Context>,
    kernels: Kernels,
    stream: Stream,
}

fn gpu() -> Option<Gpu> {
    match Device::count() {
        Ok(n) if n > 0 => {}
        Ok(_) => {
            eprintln!("skipped: no CUDA device");
            return None;
        }
        Err(e) => {
            eprintln!("skipped: {e}");
            return None;
        }
    }
    let ctx = Context::new(Device::get(0).unwrap()).unwrap();
    let kernels = match Kernels::load(&ctx) {
        Ok(k) => k,
        Err(Error::KernelsNotBuilt) => {
            eprintln!("skipped: {}", Error::KernelsNotBuilt);
            return None;
        }
        Err(e) => panic!("{e}"),
    };
    let stream = Stream::new(&ctx).unwrap();
    Some(Gpu {
        ctx,
        kernels,
        stream,
    })
}

struct Lcg(u64);

impl Lcg {
    fn next(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) as u32
    }

    fn f32(&mut self) -> f32 {
        self.next() as f32 / u32::MAX as f32 * 2.0 - 1.0
    }
}

/// Byte offsets of a block's f16 fields: the scale, and the minimum where
/// the format has one.
fn half_fields(ty: TensorType) -> &'static [usize] {
    match ty {
        TensorType::Q2K => &[80, 82],
        TensorType::Q3K => &[108],
        TensorType::Q4K | TensorType::Q5K => &[0, 2],
        TensorType::Q6K => &[208],
        _ => &[0],
    }
}

/// Random blocks with small positive f16 scales and minimums, so no block
/// holds a NaN or an infinity.
fn random_matrix(ty: TensorType, rows: usize, cols: usize, rng: &mut Lcg) -> Vec<u8> {
    let size = ty.block_bytes();
    let mut data: Vec<u8> = (0..rows * cols / 256 * size)
        .map(|_| rng.next() as u8)
        .collect();
    for blk in data.chunks_exact_mut(size) {
        for &at in half_fields(ty) {
            let d = f16::from_f32(0.001 + rng.f32().abs() * 0.01);
            blk[at..at + 2].copy_from_slice(&d.to_le_bytes());
        }
    }
    data
}

fn dense(ty: TensorType, data: &[u8], len: usize) -> Vec<f32> {
    let mut out = vec![0.0; len];
    dequantize(ty, data, &mut out).unwrap();
    out
}

/// The quantization the host applies: `d = max|x| / 127`, values rounded
/// half away from zero.
fn quantize(x: &[f32]) -> (Vec<i8>, Vec<f32>) {
    let mut qs = Vec::new();
    let mut ds = Vec::new();
    for block in x.chunks_exact(Q8K_BLOCK) {
        let amax = block.iter().fold(0.0f32, |m, v| m.max(v.abs()));
        let d = amax / 127.0;
        let inv = if d == 0.0 { 0.0 } else { 1.0 / d };
        qs.extend(
            block
                .iter()
                .map(|v| (v * inv).round().clamp(-127.0, 127.0) as i8),
        );
        ds.push(d);
    }
    (qs, ds)
}

fn quantized(g: &Gpu, x: &[f32], cols: usize) -> (DeviceBuffer<i8>, DeviceBuffer<f32>) {
    let xs = DeviceBuffer::from_slice(&g.ctx, x).unwrap();
    let mut qs = DeviceBuffer::<i8>::new(&g.ctx, x.len()).unwrap();
    let mut ds = DeviceBuffer::<f32>::new(&g.ctx, x.len() / Q8K_BLOCK).unwrap();
    g.kernels
        .quantize_q8k(&xs, x.len() / cols, cols, &mut qs, &mut ds, &g.stream)
        .unwrap();
    (qs, ds)
}

#[test]
fn quantization_matches_the_host() {
    let Some(g) = gpu() else { return };
    let mut rng = Lcg(3);
    let mut x: Vec<f32> = (0..4 * Q8K_BLOCK).map(|_| rng.f32() * 3.0).collect();
    x[Q8K_BLOCK..2 * Q8K_BLOCK].fill(0.0);
    x[7] = 127.5 / 127.0 * 3.0;
    let (qs, ds) = quantized(&g, &x, 2 * Q8K_BLOCK);
    let (want_qs, want_ds) = quantize(&x);
    assert_eq!(qs.to_vec().unwrap(), want_qs);
    let ds: Vec<u32> = ds.to_vec().unwrap().iter().map(|d| d.to_bits()).collect();
    assert_eq!(ds, want_ds.iter().map(|d| d.to_bits()).collect::<Vec<_>>());
}

#[test]
fn gated_and_plain_products_match_the_reference() {
    let Some(g) = gpu() else { return };
    let tables = ExpertTables::new(&g.ctx).unwrap();
    let (rows, cols, slots) = (40, 512, 3);
    let mut rng = Lcg(5);
    for ty in EXPERT_TYPES {
        let matrix = rows * cols / 256 * ty.block_bytes();
        // Each slot holds a first and a second matrix.
        let host: Vec<u8> = (0..2 * slots)
            .flat_map(|_| random_matrix(ty, rows, cols, &mut rng))
            .collect();
        let arena_data = DeviceBuffer::from_slice(&g.ctx, &host).unwrap();
        let arena = ExpertArena {
            data: &arena_data,
            slot_bytes: 2 * matrix,
        };
        let x: Vec<f32> = (0..2 * cols).map(|_| rng.f32()).collect();
        let (qs, ds) = quantized(&g, &x, cols);
        let (hq, hd) = quantize(&x);
        let x_ref: Vec<f32> = hq
            .iter()
            .enumerate()
            .map(|(i, &q)| q as f32 * hd[i / Q8K_BLOCK])
            .collect();
        // Assignments by slot: slot 2 twice, then slots 0 and 1.
        let assigned: [(u32, u32); 4] = [(2, 0), (2, 1), (0, 1), (1, 0)];
        let groups = [
            ExpertGroup {
                slot: 2,
                first: 0,
                count: 2,
            },
            ExpertGroup {
                slot: 0,
                first: 2,
                count: 1,
            },
            ExpertGroup {
                slot: 1,
                first: 3,
                count: 1,
            },
        ];
        let words: Vec<u32> = groups.iter().flat_map(ExpertGroup::words).collect();
        let groups_buf = DeviceBuffer::from_slice(&g.ctx, &words).unwrap();
        let inputs = DeviceBuffer::from_slice(&g.ctx, &assigned.map(|a| a.1)).unwrap();
        for gated in [false, true] {
            let product = ExpertProduct {
                ty,
                groups: &groups_buf,
                first_group: 0,
                n_groups: groups.len(),
                assignments: assigned.len(),
                inputs: Some(&inputs),
                first: 0,
                second: gated.then_some(matrix),
                rows,
                cols,
            };
            let mut y = DeviceBuffer::<f32>::new(&g.ctx, assigned.len() * rows).unwrap();
            let x = Q8kRows { qs: &qs, ds: &ds };
            // SAFETY: the groups cover the assignments, whose slots and
            // inputs lie inside the arena and the input rows.
            unsafe {
                g.kernels
                    .moe_product(&product, arena, &tables, &x, &mut y, &g.stream)
                    .unwrap()
            };
            g.stream.synchronize().unwrap();
            let y = y.to_vec().unwrap();
            for (a, &(slot, input)) in assigned.iter().enumerate() {
                let at = slot as usize * 2 * matrix;
                let first = dense(ty, &host[at..at + matrix], rows * cols);
                let second = dense(ty, &host[at + matrix..at + 2 * matrix], rows * cols);
                let x = &x_ref[input as usize * cols..][..cols];
                for r in 0..rows {
                    let row = |w: &[f32]| -> f64 {
                        w[r * cols..][..cols]
                            .iter()
                            .zip(x)
                            .map(|(&a, &b)| a as f64 * b as f64)
                            .sum()
                    };
                    let want = if gated {
                        let gate = row(&first);
                        gate / (1.0 + (-gate).exp()) * row(&second)
                    } else {
                        row(&first)
                    };
                    let got = y[a * rows + r] as f64;
                    assert!(
                        (got - want).abs() <= 1e-4 + 1e-4 * want.abs(),
                        "{ty} gated {gated} assignment {a} row {r}: {got} vs {want}"
                    );
                }
            }
        }
    }
}

#[test]
fn combine_mixes_in_pick_order() {
    let Some(g) = gpu() else { return };
    let (d, tokens, picks) = (300, 2, 2);
    let upload = |v: &[f32]| DeviceBuffer::from_slice(&g.ctx, v).unwrap();
    let experts: Vec<f32> = (0..4 * d).map(|i| i as f32 * 0.01).collect();
    let shared: Vec<f32> = (0..tokens * d).map(|i| 1.0 - i as f32 * 0.001).collect();
    let gates = [0.5, 9.0, -1.0, 9.0];
    let weights = [0.25, 0.75, 0.5, 0.5];
    let rows = DeviceBuffer::from_slice(&g.ctx, &[3u32, 0, 1, 2]).unwrap();
    let (e, w, gl) = (upload(&experts), upload(&weights), upload(&gates));
    let mix = ExpertMix {
        experts: &e,
        rows: &rows,
        weights: &w,
        picks,
        shared: true,
        gates: Some(GateLogits {
            values: &gl,
            first: 0,
            stride: 2,
        }),
        tokens,
        d,
    };
    let mut out = upload(&shared);
    // SAFETY: every row index lies inside `experts`.
    unsafe { g.kernels.moe_combine(&mix, &mut out, &g.stream).unwrap() };
    let out = out.to_vec().unwrap();
    let sigmoid = |x: f32| 1.0 / (1.0 + (-x).exp());
    let row_of = [3, 0, 1, 2];
    for t in 0..tokens {
        for i in 0..d {
            let mut want = shared[t * d + i] * sigmoid(gates[2 * t]);
            for k in 0..picks {
                let s = t * picks + k;
                want += weights[s] * experts[row_of[s] * d + i];
            }
            assert!((out[t * d + i] - want).abs() <= 1e-5 * (1.0 + want.abs()));
        }
    }
}
