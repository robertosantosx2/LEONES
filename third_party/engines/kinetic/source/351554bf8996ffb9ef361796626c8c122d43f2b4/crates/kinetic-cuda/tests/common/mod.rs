//! The device and random numbers shared by the integration tests.

use std::rc::Rc;

use kinetic_cuda::{Context, Device, Error, Kernels, Stream};

pub struct Gpu {
    pub ctx: Rc<Context>,
    pub kernels: Kernels,
    pub stream: Stream,
}

pub fn gpu() -> Option<Gpu> {
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

pub struct Lcg(pub u64);

impl Lcg {
    pub fn next(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) as u32
    }

    pub fn f32(&mut self) -> f32 {
        self.next() as f32 / u32::MAX as f32 * 2.0 - 1.0
    }
}
