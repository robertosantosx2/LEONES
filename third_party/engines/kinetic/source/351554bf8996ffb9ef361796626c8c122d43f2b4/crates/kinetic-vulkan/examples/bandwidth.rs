//! Prints every Vulkan device, the achievable read bandwidth of its memory
//! and the throughput of each GEMV kernel on decode-sized shapes.
//!
//! ```text
//! cargo run --release -p kinetic-vulkan --example bandwidth [-- [model.gguf] [--device N]]
//! ```
//!
//! Weights come from the GGUF file when it has a tensor of the same type and
//! shape; otherwise they are random bytes, which take the same time.
//! `--device N` measures only the N-th device in the printed order.

use std::error::Error;
use std::rc::Rc;

use kinetic_gguf::GgufFile;
use kinetic_quant::{Matrix, TensorType};
use kinetic_vulkan::{
    Commands, Device, DeviceBuffer, DeviceInfo, DeviceMatrix, GemvInput, Instance, Kernels,
    PhysicalDevice,
};

/// Far larger than any GPU cache, so every read reaches DRAM.
const READ_BYTES: usize = 512 << 20;
const READ_REPS: usize = 10;
const GEMV_REPS: usize = 50;
/// Timed runs per measurement; the fastest counts, as the others were
/// slowed by whatever else used the memory meanwhile.
const TRIALS: usize = 3;

/// (type, rows, cols): feed-forward up and down projections of a model with
/// hidden size 2560, and its 248320-token output head.
const CASES: &[(TensorType, usize, usize)] = &[
    (TensorType::Q4K, 9216, 2560),
    (TensorType::Q4K, 2560, 9216),
    (TensorType::Q5K, 9216, 2560),
    (TensorType::Q5K, 2560, 9216),
    (TensorType::Q6K, 9216, 2560),
    (TensorType::Q6K, 2560, 9216),
    (TensorType::Q8_0, 9216, 2560),
    (TensorType::Q8_0, 2560, 9216),
    (TensorType::F16, 9216, 2560),
    (TensorType::F16, 2560, 9216),
    (TensorType::F32, 9216, 2560),
    (TensorType::F32, 2560, 9216),
    (TensorType::Q6K, 248320, 2560),
];

fn main() -> Result<(), Box<dyn Error>> {
    let mut model = None;
    let mut only = None;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--device" {
            only = Some(
                args.next()
                    .ok_or("--device needs an index")?
                    .parse::<usize>()?,
            );
        } else {
            model = Some(GgufFile::open(&arg)?);
        }
    }

    let devices = Instance::new()?.physical_devices()?;
    for (i, physical) in devices.iter().enumerate() {
        print_device(i, physical.info());
        if only.is_some_and(|n| n != i) {
            println!("(skipped)\n");
            continue;
        }
        match Device::new(physical) {
            Ok(device) => measure(physical, &device, model.as_ref())?,
            Err(e) => println!("{e}\n"),
        }
    }
    Ok(())
}

fn print_device(index: usize, info: &DeviceInfo) {
    let (major, minor, patch) = info.api_version;
    println!("[{index}] {} ({:?})", info.name, info.kind);
    println!(
        "driver: {} {}, Vulkan {major}.{minor}.{patch}",
        info.driver_name, info.driver_info
    );
    println!(
        "device-local memory: {:.2} GiB",
        info.device_local_bytes as f64 / (1u64 << 30) as f64
    );
    let f = &info.features;
    let yes = |b: bool| if b { "yes" } else { "no" };
    println!(
        "subgroups: {} by default, {}..{} selectable, arithmetic {}, size 32 pinnable {}",
        f.subgroup_size,
        f.subgroup_size_range.0,
        f.subgroup_size_range.1,
        yes(f.subgroup_arithmetic),
        yes(f.subgroup_size_32)
    );
    println!(
        "int8 dot product: {} (accelerated {}), 16-bit storage: {}, 8-bit storage: {}",
        yes(f.integer_dot_product),
        yes(f.integer_dot_product_accelerated),
        yes(f.storage_16bit),
        yes(f.storage_8bit)
    );
    println!(
        "cooperative matrix: {}, push descriptors: {}, timestamps: {}",
        yes(f.cooperative_matrix),
        yes(f.push_descriptor),
        yes(f.timestamps)
    );
}

fn measure(
    physical: &PhysicalDevice,
    device: &Rc<Device>,
    model: Option<&GgufFile>,
) -> Result<(), Box<dyn Error>> {
    let kernels = Kernels::load(device)?;
    let read = read_bandwidth(device, &kernels)?;
    println!("achievable read bandwidth: {:.1} GB/s", read / 1e9);
    println!(
        "{:<5} {:>13} {:>7} {:>8} {:>9} {:>8} {:>8}",
        "type", "rows x cols", "weights", "MB", "us", "GB/s", "of read"
    );
    for &(ty, rows, cols) in CASES {
        let bytes = ty.bytes_for((rows * cols) as u64).unwrap() as usize;
        if bytes as u64 > physical.info().max_buffer_bytes {
            continue;
        }
        let from_model = model.and_then(|f| find(f, ty, rows, cols));
        let random;
        let (data, source) = match from_model {
            Some(data) => (data, "model"),
            None => {
                random = random_bytes(bytes);
                (&random[..], "random")
            }
        };
        let w = DeviceMatrix::upload(device, &Matrix::new(ty, data, rows, cols))?;
        let seconds = gemv_seconds(device, &kernels, &w)?;
        let rate = w.size_bytes() as f64 / seconds;
        println!(
            "{:<5} {:>13} {:>7} {:>8.1} {:>9.1} {:>8.1} {:>7.0}%",
            ty.name(),
            format!("{rows}x{cols}"),
            source,
            w.size_bytes() as f64 / 1e6,
            seconds * 1e6,
            rate / 1e9,
            100.0 * rate / read
        );
    }
    println!();
    Ok(())
}

/// Bytes per second of the streaming read kernel.
fn read_bandwidth(device: &Rc<Device>, kernels: &Kernels) -> Result<f64, Box<dyn Error>> {
    let data = DeviceBuffer::<u8>::new(device, READ_BYTES)?;
    let sum = DeviceBuffer::<u32>::new(device, 1)?;
    let seconds = time(device, READ_REPS, |c| kernels.read_sum(&data, &sum, c))?;
    Ok(READ_BYTES as f64 / seconds)
}

fn gemv_seconds(
    device: &Rc<Device>,
    kernels: &Kernels,
    w: &DeviceMatrix,
) -> Result<f64, Box<dyn Error>> {
    let x: Vec<f32> = (0..w.cols()).map(|i| (i % 7) as f32 - 3.0).collect();
    let mut input = GemvInput::new(device, w.cols())?;
    let y = DeviceBuffer::new(device, w.rows())?;
    let mut commands = Commands::new(device)?;
    input.upload(kernels, &x, &mut commands)?;
    commands.submit()?;
    time(device, GEMV_REPS, |c| kernels.gemv(w, &input, &y, c))
}

/// Device seconds per call of `f`: the best mean of [`TRIALS`] submissions
/// of `reps` calls each, after one warm-up submission.
fn time(
    device: &Rc<Device>,
    reps: usize,
    mut f: impl FnMut(&mut Commands) -> kinetic_vulkan::Result<()>,
) -> Result<f64, Box<dyn Error>> {
    let mut warm = Commands::new(device)?;
    f(&mut warm)?;
    warm.submit()?;
    let mut best = f64::INFINITY;
    for _ in 0..TRIALS {
        let mut commands = Commands::new(device)?;
        let start = commands.timestamp()?;
        for _ in 0..reps {
            f(&mut commands)?;
        }
        let end = commands.timestamp()?;
        best = best.min(commands.submit()?.seconds(start, end) / reps as f64);
    }
    Ok(best)
}

/// Bytes of a tensor stored as `rows` rows of `cols` elements of type `ty`.
fn find(file: &GgufFile, ty: TensorType, rows: usize, cols: usize) -> Option<&[u8]> {
    let dims = [cols as u64, rows as u64];
    let tensor = file
        .header()
        .tensors
        .iter()
        .find(|t| t.ty == ty && t.dims == dims)?;
    Some(file.tensor_data(tensor))
}

fn random_bytes(n: usize) -> Vec<u8> {
    let mut state = 0x2545_f491_4f6c_dd1du64;
    (0..n)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            state as u8
        })
        .collect()
}
