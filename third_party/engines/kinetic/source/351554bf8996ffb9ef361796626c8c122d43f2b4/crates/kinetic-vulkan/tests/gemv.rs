//! GEMV kernels against `kinetic_quant::dequantize` and an f64 dot product,
//! on every Vulkan device that can run them. Each test passes with a message
//! when there is none.

use std::rc::Rc;

use half::f16;
use kinetic_quant::{dequantize, Matrix, TensorType};
use kinetic_vulkan::{
    Commands, Device, DeviceBuffer, DeviceMatrix, Error, GemvInput, Instance, Kernels,
};

struct Gpu {
    device: Rc<Device>,
    kernels: Kernels,
}

fn gpus() -> Vec<Gpu> {
    let physical = match Instance::new().and_then(|i| i.physical_devices()) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("skipped: {e}");
            return Vec::new();
        }
    };
    let gpus: Vec<Gpu> = physical
        .iter()
        .filter_map(|p| match Device::new(p) {
            Ok(device) => {
                let kernels = Kernels::load(&device).unwrap();
                Some(Gpu { device, kernels })
            }
            Err(e @ Error::DeviceUnsupported(_)) => {
                eprintln!("skipped {}: {e}", p.info().name);
                None
            }
            Err(e) => panic!("{}: {e}", p.info().name),
        })
        .collect();
    if gpus.is_empty() {
        eprintln!("skipped: no Vulkan device can run the kernels");
    }
    gpus
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

/// Random blocks with sane f16 scales at the positions each format uses;
/// float types get values in [-1, 1].
fn random_matrix(ty: TensorType, rows: usize, cols: usize, rng: &mut Lcg) -> Vec<u8> {
    let blocks = rows * cols / ty.block_len();
    match ty {
        TensorType::F32 => (0..blocks).flat_map(|_| rng.f32().to_le_bytes()).collect(),
        TensorType::F16 => (0..blocks)
            .flat_map(|_| f16::from_f32(rng.f32()).to_le_bytes())
            .collect(),
        _ => {
            let size = ty.block_bytes();
            let scale_offsets: &[usize] = match ty {
                TensorType::Q4K | TensorType::Q5K => &[0, 2],
                TensorType::Q6K => &[208],
                TensorType::Q8_0 => &[0],
                _ => unreachable!(),
            };
            let mut data: Vec<u8> = (0..blocks * size).map(|_| rng.next() as u8).collect();
            for blk in data.chunks_exact_mut(size) {
                for &o in scale_offsets {
                    let v = f16::from_f32(0.001 + rng.f32().abs() * 0.01);
                    blk[o..o + 2].copy_from_slice(&v.to_le_bytes());
                }
            }
            data
        }
    }
}

/// The input the kernel actually multiplies with: `x` itself for float
/// weights, its int8 copy for quantized ones.
fn effective_input(ty: TensorType, x: &[f32], input: &GemvInput) -> Vec<f32> {
    if matches!(ty, TensorType::F32 | TensorType::F16) {
        return x.to_vec();
    }
    let qs = input.quantized().to_vec().unwrap();
    let ds = input.block_scales().to_vec().unwrap();
    qs.iter()
        .enumerate()
        .map(|(i, &q)| q as f32 * ds[2 * (i / 32)])
        .collect()
}

fn check(ty: TensorType, rows: usize, cols: usize) {
    for gpu in gpus() {
        let mut rng = Lcg(ty as u64 + 1);
        let data = random_matrix(ty, rows, cols, &mut rng);
        let m = Matrix::new(ty, &data, rows, cols);
        let x: Vec<f32> = (0..cols).map(|_| rng.f32() * 3.0).collect();

        let w = DeviceMatrix::upload(&gpu.device, &m).unwrap();
        let mut input = GemvInput::new(&gpu.device, cols).unwrap();
        let y = DeviceBuffer::new(&gpu.device, rows).unwrap();
        let mut commands = Commands::new(&gpu.device).unwrap();
        input.upload(&gpu.kernels, &x, &mut commands).unwrap();
        gpu.kernels.gemv(&w, &input, &y, &mut commands).unwrap();
        commands.submit().unwrap();
        let y = y.to_vec().unwrap();

        let name = &gpu.device.info().name;
        let xe = effective_input(ty, &x, &input);
        let mut row = vec![0.0; cols];
        for (r, &got) in y.iter().enumerate() {
            dequantize(ty, m.row(r), &mut row).unwrap();
            let exact: f64 = row
                .iter()
                .zip(&xe)
                .map(|(&a, &b)| a as f64 * b as f64)
                .sum();
            let magnitude: f64 = row
                .iter()
                .zip(&xe)
                .map(|(&a, &b)| (a as f64 * b as f64).abs())
                .sum();
            let tol = 1e-5 * magnitude + 1e-6;
            assert!(
                (got as f64 - exact).abs() <= tol,
                "{name}: {ty} row {r}: got {got}, expected {exact}"
            );
        }
    }
}

// 37 rows leave the last workgroup partly empty; 5 K-quant blocks per row
// leave some invocation groups without a block on the second step.

#[test]
fn q4_k_matches_reference() {
    check(TensorType::Q4K, 37, 5 * 256);
}

#[test]
fn q5_k_matches_reference() {
    check(TensorType::Q5K, 37, 5 * 256);
}

#[test]
fn q6_k_matches_reference() {
    check(TensorType::Q6K, 37, 5 * 256);
}

#[test]
fn q8_0_matches_reference() {
    check(TensorType::Q8_0, 37, 41 * 32);
}

#[test]
fn f16_matches_reference() {
    check(TensorType::F16, 37, 41 * 32);
}

#[test]
fn f32_matches_reference() {
    check(TensorType::F32, 37, 41 * 32);
}

/// More than 65535 workgroups of rows, so the dispatch spans two dimensions.
#[test]
fn tall_matrix_matches_reference() {
    check(TensorType::Q8_0, 4 * 65535 + 9, 32);
}

#[test]
fn quantized_input_is_within_half_a_step() {
    for gpu in gpus() {
        let mut rng = Lcg(7);
        let mut x: Vec<f32> = (0..1024).map(|_| rng.f32() * 5.0).collect();
        x[32..64].fill(0.0);
        let mut input = GemvInput::new(&gpu.device, x.len()).unwrap();
        let mut commands = Commands::new(&gpu.device).unwrap();
        input.upload(&gpu.kernels, &x, &mut commands).unwrap();
        commands.submit().unwrap();
        let qs = input.quantized().to_vec().unwrap();
        let ds = input.block_scales().to_vec().unwrap();
        for (b, (xs, q)) in x.chunks(32).zip(qs.chunks(32)).enumerate() {
            let (d, sum) = (ds[2 * b], ds[2 * b + 1]);
            let qsum: i32 = q.iter().map(|&v| v as i32).sum();
            assert_eq!(sum, d * qsum as f32, "block {b} sum");
            for (&v, &q) in xs.iter().zip(q) {
                assert!(
                    (v - q as f32 * d).abs() <= d * 0.5001,
                    "block {b}: {v} vs {q} * {d}"
                );
            }
        }
    }
}

#[test]
fn buffers_round_trip_through_staging() {
    for gpu in gpus() {
        // Larger than one 64 MiB staging chunk.
        let data: Vec<u32> = (0..(17 << 20)).collect();
        let buf = DeviceBuffer::from_slice(&gpu.device, &data).unwrap();
        assert!(buf.to_vec().unwrap() == data);
    }
}

#[test]
fn read_sum_adds_every_word() {
    for gpu in gpus() {
        let data: Vec<u8> = (0..1 << 20).map(|i| (i * 7 + 3) as u8).collect();
        let expected = data
            .chunks_exact(4)
            .map(|w| u32::from_le_bytes(w.try_into().unwrap()))
            .fold(0u32, u32::wrapping_add);
        let buf = DeviceBuffer::from_slice(&gpu.device, &data).unwrap();
        let out = DeviceBuffer::<u32>::new(&gpu.device, 1).unwrap();
        let mut commands = Commands::new(&gpu.device).unwrap();
        gpu.kernels.read_sum(&buf, &out, &mut commands).unwrap();
        commands.submit().unwrap();
        assert_eq!(out.to_vec().unwrap(), [expected]);
    }
}

#[test]
fn mismatched_shapes_are_rejected() {
    for gpu in gpus() {
        let data = vec![0u8; 4 * 64 * 4];
        let w =
            DeviceMatrix::upload(&gpu.device, &Matrix::new(TensorType::F32, &data, 4, 64)).unwrap();
        let input = GemvInput::new(&gpu.device, 32).unwrap();
        let y = DeviceBuffer::new(&gpu.device, 4).unwrap();
        let mut commands = Commands::new(&gpu.device).unwrap();
        let result = gpu.kernels.gemv(&w, &input, &y, &mut commands);
        assert!(matches!(result, Err(Error::Shape(_))));
    }
}
