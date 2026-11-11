//! The device's expert outputs against the host's, bit for bit.

use kinetic_cuda::{
    Context, Device, DeviceBuffer, ExpertArena, ExpertGroup, ExpertProduct, ExpertTables, Q8kRows,
    Routing, EXPERT_GROUP, EXPERT_TYPES, Q8K_BLOCK,
};
use kinetic_quant::{Matrix, TensorType};

use super::Gpu;
use crate::blocks::{scale_offsets, Experts, Gating, Job, Moe};

fn gpu() -> Option<Gpu> {
    let ctx = Context::new(Device::get(0).ok()?).ok()?;
    Gpu::new(ctx).ok()
}

fn random_bytes(len: usize, seed: &mut u64) -> Vec<u8> {
    (0..len)
        .map(|_| {
            *seed = seed
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            (*seed >> 33) as u8
        })
        .collect()
}

/// Random blocks of `ty` with small f16 scales, for `count` experts.
fn random_experts(
    ty: TensorType,
    rows: usize,
    cols: usize,
    count: usize,
    seed: &mut u64,
) -> Vec<u8> {
    let mut data = random_bytes(count * rows * cols / 256 * ty.block_bytes(), seed);
    for (i, blk) in data.chunks_exact_mut(ty.block_bytes()).enumerate() {
        for (j, &at) in scale_offsets(ty).iter().enumerate() {
            let d = half::f16::from_f32(0.002 + ((i + 5 * j) % 17) as f32 * 4e-4);
            blk[at..at + 2].copy_from_slice(&d.to_le_bytes());
        }
    }
    data
}

#[test]
fn device_experts_equal_host_experts_bit_for_bit() {
    let Some(g) = gpu() else {
        eprintln!("skipped: no CUDA device or kernels");
        return;
    };
    let (d, f, count, tokens) = (512, 256, 3, 4);
    let mut seed = 9;
    for (gate_ty, down_ty) in [
        (EXPERT_TYPES[0], EXPERT_TYPES[3]),
        (EXPERT_TYPES[1], EXPERT_TYPES[2]),
        (TensorType::Q4K, TensorType::Q6K),
        (TensorType::Q5K, TensorType::Q2K),
        (TensorType::Q2K, TensorType::Q3K),
        (TensorType::Q6K, TensorType::Q4K),
        (TensorType::Q3K, TensorType::Q5K),
    ] {
        let gate = random_experts(gate_ty, f, d, count, &mut seed);
        let up = random_experts(gate_ty, f, d, count, &mut seed);
        let down = random_experts(down_ty, d, f, count, &mut seed);
        let router = vec![0u8; 4 * d * count];
        fn experts(ty: TensorType, data: &[u8], rows: usize, cols: usize) -> Experts<'_> {
            let count = data.len() / (rows * cols / 256 * ty.block_bytes());
            Experts {
                ty,
                data,
                rows,
                cols,
                count,
            }
        }
        let moe = Moe {
            router: Matrix::new(TensorType::F32, &router, count, d),
            gate: experts(gate_ty, &gate, f, d),
            up: experts(gate_ty, &up, f, d),
            down: experts(down_ty, &down, d, f),
            n_used: 2,
            shared_gate: None,
            gating: Gating::Softmax,
        };
        let h: Vec<f32> = random_bytes(tokens * d, &mut seed)
            .iter()
            .map(|&b| (b as f32 - 127.5) / 50.0)
            .collect();
        // Expert 2 for tokens 0, 1 and 3, expert 0 for token 2.
        let jobs = [(2, 0), (2, 1), (2, 3), (0, 2)].map(|(expert, row)| Job { row, expert });
        let want = moe.run_experts(&h, &jobs);

        let (ge, ue, de) = (
            moe.gate.expert_bytes(),
            moe.up.expert_bytes(),
            moe.down.expert_bytes(),
        );
        let slot_bytes = ge + ue + de;
        let mut arena = Vec::new();
        for e in 0..count {
            for m in [moe.gate.expert(e), moe.up.expert(e), moe.down.expert(e)] {
                arena.extend_from_slice(m.data);
            }
        }
        let arena = DeviceBuffer::from_slice(&g.ctx, &arena).unwrap();
        let arena = ExpertArena {
            data: &arena,
            slot_bytes,
        };
        let groups: Vec<u32> = [
            ExpertGroup {
                slot: 2,
                first: 0,
                count: 3,
            },
            ExpertGroup {
                slot: 0,
                first: 3,
                count: 1,
            },
        ]
        .iter()
        .flat_map(ExpertGroup::words)
        .collect();
        let groups = DeviceBuffer::from_slice(&g.ctx, &groups).unwrap();
        let inputs = DeviceBuffer::from_slice(&g.ctx, &jobs.map(|j| j.row)).unwrap();
        let tables = ExpertTables::new(&g.ctx).unwrap();
        let (k, stream) = (&g.kernels, &g.stream);
        let a = jobs.len();
        let hs = DeviceBuffer::from_slice(&g.ctx, &h).unwrap();
        let mut hq = DeviceBuffer::<i8>::new(&g.ctx, tokens * d).unwrap();
        let mut hd = DeviceBuffer::<f32>::new(&g.ctx, tokens * d / Q8K_BLOCK).unwrap();
        k.quantize_q8k(&hs, tokens, d, &mut hq, &mut hd, stream)
            .unwrap();
        let mut act = DeviceBuffer::<f32>::new(&g.ctx, a * f).unwrap();
        let mut actq = DeviceBuffer::<i8>::new(&g.ctx, a * f).unwrap();
        let mut actd = DeviceBuffer::<f32>::new(&g.ctx, a * f / Q8K_BLOCK).unwrap();
        let mut out = DeviceBuffer::<f32>::new(&g.ctx, a * d).unwrap();
        let product = |ty, inputs, first, second, rows, cols| ExpertProduct {
            ty,
            groups: &groups,
            first_group: 0,
            n_groups: 2,
            assignments: a,
            inputs,
            first,
            second,
            rows,
            cols,
        };
        // SAFETY: the groups cover the four assignments, whose slots hold
        // the experts at these offsets and whose inputs are rows of `h`.
        unsafe {
            let x = Q8kRows { qs: &hq, ds: &hd };
            let p = product(gate_ty, Some(&inputs), 0, Some(ge), f, d);
            k.moe_product(&p, arena, &tables, &x, &mut act, stream)
                .unwrap();
            k.quantize_q8k(&act, a, f, &mut actq, &mut actd, stream)
                .unwrap();
            let x = Q8kRows {
                qs: &actq,
                ds: &actd,
            };
            let p = product(down_ty, None, ge + ue, None, d, f);
            k.moe_product(&p, arena, &tables, &x, &mut out, stream)
                .unwrap();
        }
        let got = out.to_vec().unwrap();
        let bits = |v: &[f32]| v.iter().map(|x| x.to_bits()).collect::<Vec<_>>();
        assert_eq!(bits(&got), bits(&want), "{gate_ty}/{down_ty}");
    }
}

#[test]
fn device_sigmoid_routing_picks_what_the_host_picks() {
    let Some(g) = gpu() else {
        eprintln!("skipped: no CUDA device or kernels");
        return;
    };
    let (tokens, n_exp, k, stride) = (19, 32, 4, 64);
    let mut seed = 5;
    let logits: Vec<f32> = random_bytes(2 * tokens * stride, &mut seed)
        .chunks_exact(2)
        .map(|b| (u16::from_le_bytes([b[0], b[1]]) as f32 - 32767.5) / 8000.0)
        .collect();
    let bias: Vec<f32> = random_bytes(n_exp, &mut seed)
        .iter()
        .map(|&b| (b as f32 - 127.5) / 300.0)
        .collect();
    let gates = DeviceBuffer::from_slice(&g.ctx, &logits).unwrap();
    let bias_dev = DeviceBuffer::from_slice(&g.ctx, &bias).unwrap();
    let mut experts = DeviceBuffer::<u32>::new(&g.ctx, tokens * k).unwrap();
    let mut weights = DeviceBuffer::<f32>::new(&g.ctx, tokens * k).unwrap();
    let routing = Routing {
        gates: &gates,
        tokens,
        n_exp,
        picks: k,
        stride,
        sigmoid: true,
        bias: Some(&bias_dev),
    };
    g.kernels
        .moe_route(&routing, &mut experts, &mut weights, &g.stream)
        .unwrap();
    let (experts, weights) = (experts.to_vec().unwrap(), weights.to_vec().unwrap());
    let gating = Gating::Sigmoid { bias };
    for t in 0..tokens {
        let want = gating.pick(&mut logits[t * stride..][..n_exp].to_vec(), k);
        for (j, w) in want.iter().enumerate() {
            assert_eq!(experts[t * k + j], w.expert, "token {t} pick {j}");
            assert!((weights[t * k + j] - w.weight).abs() <= 1e-5 * w.weight);
        }
    }
}

#[test]
fn device_routing_picks_what_the_host_picks() {
    let Some(g) = gpu() else {
        eprintln!("skipped: no CUDA device or kernels");
        return;
    };
    let (tokens, n_exp, k, stride) = (37, 64, 6, 70);
    let mut seed = 3;
    // Two bytes per logit, so that no two experts tie.
    let logits: Vec<f32> = random_bytes(2 * tokens * stride, &mut seed)
        .chunks_exact(2)
        .map(|b| (u16::from_le_bytes([b[0], b[1]]) as f32 - 32767.5) / 5000.0)
        .collect();
    let gates = DeviceBuffer::from_slice(&g.ctx, &logits).unwrap();
    let a = tokens * k;
    let mut experts = DeviceBuffer::<u32>::new(&g.ctx, a).unwrap();
    let mut weights = DeviceBuffer::<f32>::new(&g.ctx, a).unwrap();
    let routing = Routing {
        gates: &gates,
        tokens,
        n_exp,
        picks: k,
        stride,
        sigmoid: false,
        bias: None,
    };
    let (kn, stream) = (&g.kernels, &g.stream);
    kn.moe_route(&routing, &mut experts, &mut weights, stream)
        .unwrap();
    // Slots in reverse, so a slot is never its expert's index by chance.
    let slots: Vec<u32> = (0..n_exp as u32).rev().collect();
    let slots = DeviceBuffer::from_slice(&g.ctx, &slots).unwrap();
    let mut groups = DeviceBuffer::<u32>::new(&g.ctx, 4 * a).unwrap();
    let mut inputs = DeviceBuffer::<u32>::new(&g.ctx, a).unwrap();
    let mut rows = DeviceBuffer::<u32>::new(&g.ctx, a).unwrap();
    kn.moe_assign(
        &experts,
        a,
        k,
        &slots,
        &mut groups,
        a,
        &mut inputs,
        &mut rows,
        stream,
    )
    .unwrap();
    let (experts, weights) = (experts.to_vec().unwrap(), weights.to_vec().unwrap());
    let (groups, inputs, rows) = (
        groups.to_vec().unwrap(),
        inputs.to_vec().unwrap(),
        rows.to_vec().unwrap(),
    );

    for t in 0..tokens {
        let want = Gating::Softmax.pick(&mut logits[t * stride..][..n_exp].to_vec(), k);
        for (j, w) in want.iter().enumerate() {
            let s = t * k + j;
            assert_eq!(experts[s], w.expert, "token {t} pick {j}");
            assert!(
                (weights[s] - w.weight).abs() <= 1e-5 * w.weight,
                "token {t} pick {j}"
            );
        }
    }
    let mut seen = vec![false; a];
    for (s, &row) in rows.iter().enumerate() {
        let row = row as usize;
        assert_eq!(inputs[row] as usize, s / k);
        assert!(
            !std::mem::replace(&mut seen[row], true),
            "assignment {row} twice"
        );
        let group = groups
            .chunks_exact(4)
            .find(|g| (g[1]..g[1] + g[2]).contains(&(row as u32)))
            .expect("every assignment is in a group");
        assert_eq!(group[0], n_exp as u32 - 1 - experts[s]);
        assert!(group[2] as usize <= EXPERT_GROUP);
    }
}
