//! Throughput of the large-batch matrix products on prefill-sized shapes,
//! in int8 (or f16) operations per second.
//!
//! ```text
//! cargo run --release -p kinetic-cuda --example gemm [-- tokens [model.gguf]]
//! ```
//!
//! Weights come from the GGUF file when it has a tensor of the same type and
//! shape; otherwise they are random bytes, which take the same time.

use std::env;
use std::error::Error;

use kinetic_cuda::{
    Context, Device, DeviceBuffer, DeviceMatrix, Event, GemvInput, Kernels, Stream,
};
use kinetic_gguf::GgufFile;
use kinetic_quant::{Matrix, TensorType};

const REPS: usize = 20;

/// (type, rows, cols): the projections of a model with hidden size 2560 and
/// feed-forward size 9216, and its small float gate projections.
const CASES: &[(TensorType, usize, usize)] = &[
    (TensorType::Q4K, 9216, 2560),
    (TensorType::Q4K, 2560, 9216),
    (TensorType::Q4K, 8192, 2560),
    (TensorType::Q5K, 9216, 2560),
    (TensorType::Q5K, 2560, 4096),
    (TensorType::Q6K, 2560, 9216),
    (TensorType::Q6K, 1024, 2560),
    (TensorType::Q8_0, 32, 2560),
    (TensorType::F16, 4096, 2560),
    (TensorType::F32, 4096, 2560),
    (TensorType::F32, 32, 2560),
];

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args().skip(1);
    let n: usize = args.next().map_or(Ok(512), |s| s.parse())?;
    let model = args.next().map(GgufFile::open).transpose()?;

    let ctx = Context::new(Device::get(0)?)?;
    let kernels = Kernels::load(&ctx)?;
    let stream = Stream::new(&ctx)?;
    println!("{n} inputs");
    println!(
        "{:<5} {:>12} {:>7} {:>9} {:>8}",
        "type", "rows x cols", "weights", "us", "TOPS"
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
        let x: Vec<f32> = (0..n * cols).map(|i| (i % 7) as f32 - 3.0).collect();
        let mut input = GemvInput::batch(&ctx, cols, n)?;
        input.upload(&kernels, &x, &stream)?;
        let mut y = DeviceBuffer::new(&ctx, n * rows)?;
        let mut run = || kernels.gemv_rows(&w, rows, &input, 0..n, &mut y, &stream);
        run()?;
        let (start, end) = (Event::new(&ctx)?, Event::new(&ctx)?);
        start.record(&stream)?;
        for _ in 0..REPS {
            run()?;
        }
        end.record(&stream)?;
        end.synchronize()?;
        let seconds = start.elapsed_ms(&end)? as f64 / 1e3 / REPS as f64;
        println!(
            "{:<5} {:>12} {:>7} {:>9.1} {:>8.1}",
            ty.name(),
            format!("{rows}x{cols}"),
            source,
            seconds * 1e6,
            2.0 * (rows * cols * n) as f64 / seconds / 1e12
        );
    }
    Ok(())
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

/// Random bytes whose f16 fields are small finite values, so the products
/// stay finite.
fn random_bytes(n: usize) -> Vec<u8> {
    let mut state = 0x2545_f491_4f6c_dd1du64;
    (0..n)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            (state as u8) & 0x3b
        })
        .collect()
}
