//! Prints the first CUDA device, the achievable read bandwidth of its memory
//! and the throughput of each GEMV kernel on decode-sized shapes.
//!
//! ```text
//! cargo run --release -p kinetic-cuda --example bandwidth [-- model.gguf]
//! ```
//!
//! Weights come from the GGUF file when it has a tensor of the same type and
//! shape; otherwise they are random bytes, which take the same time.

use std::env;
use std::error::Error;
use std::rc::Rc;

use kinetic_cuda::{
    driver_version, Context, Device, DeviceBuffer, DeviceInfo, DeviceMatrix, Event, GemvInput,
    Kernels, Stream,
};
use kinetic_gguf::GgufFile;
use kinetic_quant::{Matrix, TensorType};

/// Far larger than any L2 cache, so every read reaches DRAM.
const READ_BYTES: usize = 512 << 20;
const READ_REPS: usize = 20;
const GEMV_REPS: usize = 100;

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
    (TensorType::Q4_1, 9216, 2560),
    (TensorType::Q4_1, 2560, 9216),
    (TensorType::Q5_0, 9216, 2560),
    (TensorType::Q5_0, 2560, 9216),
    (TensorType::Q5_1, 9216, 2560),
    (TensorType::Q5_1, 2560, 9216),
    (TensorType::IQ4NL, 9216, 2560),
    (TensorType::IQ4NL, 2560, 9216),
    (TensorType::MXFP4, 9216, 2560),
    (TensorType::MXFP4, 2560, 9216),
    (TensorType::Q3K, 9216, 2560),
    (TensorType::Q3K, 2560, 9216),
    (TensorType::Q2K, 9216, 2560),
    (TensorType::Q2K, 2560, 9216),
    (TensorType::F16, 9216, 2560),
    (TensorType::F16, 2560, 9216),
    (TensorType::F32, 9216, 2560),
    (TensorType::F32, 2560, 9216),
    (TensorType::Q6K, 248320, 2560),
];

fn main() -> Result<(), Box<dyn Error>> {
    let device = Device::get(0)?;
    let info = device.info()?;
    print_device(&info, driver_version()?);

    let ctx = Context::new(device)?;
    let kernels = Kernels::load(&ctx)?;
    let stream = Stream::new(&ctx)?;

    let read = read_bandwidth(&ctx, &kernels, &stream)?;
    match info.peak_bandwidth() {
        Some(peak) => println!(
            "achievable read bandwidth: {:.1} GB/s ({:.0}% of nominal)\n",
            read / 1e9,
            100.0 * read / peak
        ),
        None => println!("achievable read bandwidth: {:.1} GB/s\n", read / 1e9),
    }

    let model = env::args_os().nth(1).map(GgufFile::open).transpose()?;
    println!(
        "{:<6} {:>12} {:>7} {:>8} {:>9} {:>8} {:>8}",
        "type", "rows x cols", "weights", "MB", "us", "GB/s", "of read"
    );
    for &(ty, rows, cols) in CASES {
        let from_model = model.as_ref().and_then(|f| find(f, ty, rows, cols));
        let random;
        let (bytes, source) = match from_model {
            Some(bytes) => (bytes, "model"),
            None => {
                random = random_bytes(ty.bytes_for((rows * cols) as u64).unwrap() as usize);
                (&random[..], "random")
            }
        };
        let w = DeviceMatrix::upload(&ctx, &Matrix::new(ty, bytes, rows, cols))?;
        let seconds = gemv_seconds(&ctx, &kernels, &stream, &w)?;
        let rate = w.size_bytes() as f64 / seconds;
        println!(
            "{:<6} {:>12} {:>7} {:>8.1} {:>9.1} {:>8.1} {:>7.0}%",
            ty.name(),
            format!("{rows}x{cols}"),
            source,
            w.size_bytes() as f64 / 1e6,
            seconds * 1e6,
            rate / 1e9,
            100.0 * rate / read
        );
    }
    Ok(())
}

fn print_device(info: &DeviceInfo, (major, minor): (u32, u32)) {
    let (cc_major, cc_minor) = info.compute_capability;
    println!("device: {} (sm_{cc_major}{cc_minor})", info.name);
    println!("driver: CUDA {major}.{minor}");
    println!(
        "memory: {:.2} GiB, {} SMs",
        info.total_memory as f64 / (1u64 << 30) as f64,
        info.multiprocessors
    );
    let mhz = |khz: Option<u32>| khz.map_or("unknown".to_string(), |k| format!("{} MHz", k / 1000));
    println!(
        "clocks: core {}, memory {}",
        mhz(info.clock_khz),
        mhz(info.memory_clock_khz)
    );
    if let Some(bits) = info.memory_bus_bits {
        println!("memory bus: {bits} bits");
    }
    if let Some(peak) = info.peak_bandwidth() {
        println!("nominal bandwidth: {:.1} GB/s", peak / 1e9);
    }
}

/// Bytes per second of the streaming read kernel.
fn read_bandwidth(
    ctx: &Rc<Context>,
    kernels: &Kernels,
    stream: &Stream,
) -> Result<f64, Box<dyn Error>> {
    let data = DeviceBuffer::<u8>::new(ctx, READ_BYTES)?;
    let mut sum = DeviceBuffer::<u32>::new(ctx, 1)?;
    let seconds = time(ctx, stream, READ_REPS, || {
        kernels.read_sum(&data, &mut sum, stream)
    })?;
    Ok(READ_BYTES as f64 / seconds)
}

fn gemv_seconds(
    ctx: &Rc<Context>,
    kernels: &Kernels,
    stream: &Stream,
    w: &DeviceMatrix,
) -> Result<f64, Box<dyn Error>> {
    let x: Vec<f32> = (0..w.cols()).map(|i| (i % 7) as f32 - 3.0).collect();
    let mut input = GemvInput::new(ctx, w.cols())?;
    let mut y = DeviceBuffer::new(ctx, w.rows())?;
    input.upload(kernels, &x, stream)?;
    time(ctx, stream, GEMV_REPS, || {
        kernels.gemv(w, &input, &mut y, stream)
    })
}

/// Mean seconds per call of `f`, timed on the device after one warm-up call.
fn time(
    ctx: &Rc<Context>,
    stream: &Stream,
    reps: usize,
    mut f: impl FnMut() -> kinetic_cuda::Result<()>,
) -> Result<f64, Box<dyn Error>> {
    f()?;
    let (start, end) = (Event::new(ctx)?, Event::new(ctx)?);
    start.record(stream)?;
    for _ in 0..reps {
        f()?;
    }
    end.record(stream)?;
    end.synchronize()?;
    Ok(start.elapsed_ms(&end)? as f64 / 1e3 / reps as f64)
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
