//! Quantised matrix view over the GGUF mmap with an f32 matvec (slow reference path).
use crate::gguf::{Gguf, TensorInfo};
use crate::quant::{GgmlType, dequant_row};
use rayon::prelude::*;
use std::sync::{Mutex, OnceLock};

/// Optional CUDA offload of the non-expert matvecs (STRATA_DS_GPU=1). Weights stay resident in VRAM; the activation is
/// copied up and the result down per call, so everything else in the forward stays the CPU reference code.
mod dev {
    use super::*;
    use crate::backend::{Backend, Buf, GpuTensor};
    use crate::weights::Tensor;
    /// Scratch slot for experts that missed the VRAM cache: copied up per use, so the CPU never dequantises them.
    pub const STAGE: usize = 16 << 20;
    pub const STAGED: u32 = u32::MAX;
    pub struct Dev { be: Box<dyn Backend>, ts: Vec<GpuTensor>, x: Buf, y: Buf, pub bytes: usize, ex: std::collections::HashMap<usize, usize>, exs: Vec<(u32, usize, u64)>, now: u64, budget: usize, stage: Buf }
    static DEV: OnceLock<Option<Mutex<Dev>>> = OnceLock::new();
    pub fn get() -> Option<&'static Mutex<Dev>> {
        DEV.get_or_init(|| {
            if std::env::var_os("STRATA_DS_GPU").is_none() { return None; }
            let be = crate::backend::open(Some("cuda"), 0).ok()?;
            let (x, y) = (be.alloc(4 * 40960).ok()?, be.alloc(4 * 262144).ok()?);
            let stage = be.alloc(STAGE).ok()?;
            let gb: f64 = std::env::var("STRATA_DS_GPU_EXPERTS").ok().and_then(|v| v.parse().ok()).unwrap_or(0.0);
            Some(Mutex::new(Dev { be, ts: vec![], x, y, bytes: 0, ex: Default::default(), exs: vec![], now: 0, budget: (gb * 1e9) as usize, stage }))
        }).as_ref()
    }
    impl Dev {
        pub fn upload(&mut self, data: &[u8], ty: GgmlType, rows: usize, cols: usize) -> Option<u32> {
            let t = self.be.upload(&Tensor { ty, cols, rows, data }).ok()?;
            self.bytes += data.len();
            self.ts.push(t);
            Some(self.ts.len() as u32 - 1)
        }
        /// VRAM copy of one routed expert: uploaded on first use while under the STRATA_DS_GPU_EXPERTS budget (GB), then the
        /// least recently used slot of the same shape is overwritten. Slots touched in the last 24 lookups are kept (one layer's
        /// 18 experts are in flight together). No slot to take: STAGED (copied up per use).
        pub fn expert(&mut self, data: &[u8], ty: GgmlType, rows: usize, cols: usize) -> Option<u32> {
            let k = data.as_ptr() as usize;
            self.now += 1;
            let now = self.now;
            if let Some(&p) = self.ex.get(&k) { self.exs[p].2 = now; EX_LOOKUPS[0].fetch_add(1, std::sync::atomic::Ordering::Relaxed); return Some(self.exs[p].0); }
            EX_LOOKUPS[1].fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            if self.bytes + data.len() <= self.budget {
                let i = self.upload(data, ty, rows, cols)?;
                self.ex.insert(k, self.exs.len());
                self.exs.push((i, k, now));
                return Some(i);
            }
            if self.budget == 0 || data.len() > STAGE || std::env::var_os("STRATA_DS_NOEVICT").is_some() { return None; }
            let ts = &self.ts;
            let victim = self.exs.iter().enumerate()
                .filter(|(_, e)| e.2 + 24 <= now && { let t = &ts[e.0 as usize]; t.ty == ty && t.rows == rows && t.cols == cols })
                .min_by_key(|(_, e)| e.2).map(|(p, _)| p);
            let Some(p) = victim else { return Some(STAGED) };
            let (i, old, _) = self.exs[p];
            if self.be.htod(data, &Buf::new(self.ts[i as usize].ptr, data.len(), ()), 0).is_err() { return Some(STAGED); }
            self.ex.remove(&old);
            self.ex.insert(k, p);
            self.exs[p] = (i, k, now);
            Some(i)
        }
        pub fn gemv(&self, i: u32, x: &[f32], y: &mut [f32], staged: Option<(&[u8], GgmlType, usize, usize)>) {
            let xb: Vec<u8> = x.iter().flat_map(|v| v.to_le_bytes()).collect();
            self.be.htod(&xb, &self.x, 0).unwrap();
            if let Some((d, ty, rows, cols)) = staged {
                self.be.htod(d, &self.stage, 0).unwrap();
                let w = GpuTensor::new(ty, rows, cols, Buf::new(self.stage.addr(), d.len(), ()));
                self.be.gemv(&w, self.x.addr(), self.y.addr()).unwrap();
            } else {
                self.be.gemv(&self.ts[i as usize], self.x.addr(), self.y.addr()).unwrap();
            }
            let mut yb = vec![0u8; 4 * y.len()];
            self.be.dtoh(&self.y, 0, &mut yb).unwrap();
            for (o, c) in y.iter_mut().zip(yb.chunks_exact(4)) { *o = f32::from_le_bytes(c.try_into().unwrap()); }
        }
        /// One gemv per tensor, all queued before a single readback. Job i reads x[i*xs..] and writes its rows after job i-1's.
        pub fn batch(&self, ts: &[(u32, usize)], x: &[f32], xs: usize) -> Vec<f32> {
            let xb: Vec<u8> = x.iter().flat_map(|v| v.to_le_bytes()).collect();
            self.be.htod(&xb, &self.x, 0).unwrap();
            let mut off = 0;
            for (i, &(t, rows)) in ts.iter().enumerate() {
                self.be.gemv(&self.ts[t as usize], self.x.addr() + (4 * i * xs) as u64, self.y.addr() + (4 * off) as u64).unwrap();
                off += rows;
            }
            let mut yb = vec![0u8; 4 * off];
            self.be.dtoh(&self.y, 0, &mut yb).unwrap();
            yb.chunks_exact(4).map(|c| f32::from_le_bytes(c.try_into().unwrap())).collect()
        }
    }
}
/// Matvecs of several matrices on one activation (xs = 0) or on consecutive slices x[i*xs..] (xs > 0); outputs concatenated.
/// All matrices VRAM-resident: one GPU round trip. Otherwise each runs on its own, as `Mat::matvec`.
pub fn matvec_many(ms: &[Mat], x: &[f32], xs: usize) -> Vec<f32> {
    let ts: Option<Vec<(u32, usize)>> = ms.iter().map(|m| m.gpu.filter(|&i| i != dev::STAGED).map(|i| (i, m.rows))).collect();
    if let Some(y) = ts.and_then(|ts| Some(dev::get()?.lock().unwrap().batch(&ts, x, xs))) { return y; }
    let mut y = vec![0f32; ms.iter().map(|m| m.rows).sum()];
    let mut off = 0;
    for (i, m) in ms.iter().enumerate() {
        m.matvec(&x[i * xs..i * xs + m.cols], &mut y[off..off + m.rows]);
        off += m.rows;
    }
    y
}
/// Expert cache lookups since the last PROF print: [hit, miss].
pub static EX_LOOKUPS: [std::sync::atomic::AtomicU64; 2] = [std::sync::atomic::AtomicU64::new(0), std::sync::atomic::AtomicU64::new(0)];
pub fn gpu_bytes() -> usize { dev::get().map_or(0, |d| d.lock().unwrap().bytes) }

/// Row-major weight: `rows` rows of `cols` elements (ggml dims[0] = cols, dims[1] = rows).
/// A 3-D expert tensor is addressed with `expert(e)`.
#[derive(Clone, Copy)]
pub struct Mat<'a> {
    pub data: &'a [u8],
    pub ty: GgmlType,
    pub rows: usize,
    pub cols: usize,
    /// Routed-expert tensor: llama.cpp runs these on the CPU (Q8_K activations); the rest runs on CUDA (Q8_1 blocks of 32).
    pub cpu: bool,
    /// Index of the VRAM copy (STRATA_DS_GPU).
    pub gpu: Option<u32>,
}

impl<'a> Mat<'a> {
    pub fn load(g: &'a Gguf, name: &str) -> anyhow::Result<Self> {
        let t: &TensorInfo = g.tensors.get(name).ok_or_else(|| anyhow::anyhow!("missing tensor {name}"))?;
        let ty = GgmlType::from_u32(t.ty)?;
        let cols = t.dims[0] as usize;
        let rows = t.dims[1..].iter().product::<u64>() as usize;
        let cpu = name.contains("_exps");
        let data = g.bytes(t);
        let gpu = if cpu || t.dims.len() != 2 { None } else { dev::get().and_then(|d| d.lock().unwrap().upload(data, ty, rows, cols)) };
        Ok(Mat { data, ty, rows, cols, cpu, gpu })
    }

    /// Like `load` for a matrix used as `n` row groups (grouped output projection): each group gets its own VRAM copy.
    pub fn load_groups(g: &'a Gguf, name: &str, n: usize) -> anyhow::Result<Self> {
        let mut m = Self::load(g, name)?;
        m.gpu = None;
        if let Some(d) = dev::get() {
            let (gr, rb) = (m.rows / n, m.ty.row_bytes(m.cols as u64));
            let mut d = d.lock().unwrap();
            let ids: Vec<_> = (0..n).map(|i| d.upload(&m.data[i * gr * rb..(i + 1) * gr * rb], m.ty, gr, m.cols)).collect();
            if ids.iter().all(|i| i.is_some()) { m.gpu = ids[0]; }
        }
        Ok(m)
    }

    /// Row group `i` of `n` (see `load_groups`).
    pub fn group(&self, i: usize, n: usize) -> Mat<'a> {
        let rows = self.rows / n;
        let sz = rows * self.ty.row_bytes(self.cols as u64);
        Mat { data: &self.data[i * sz..(i + 1) * sz], rows, gpu: self.gpu.map(|b| b + i as u32), ..*self }
    }

    /// Slice of a [cols, rows, n_expert] tensor for expert e.
    pub fn expert(&self, e: usize, n_expert: usize) -> Mat<'a> {
        let rows = self.rows / n_expert;
        let sz = rows * self.ty.row_bytes(self.cols as u64);
        let data = &self.data[e * sz..(e + 1) * sz];
        let gpu = dev::get().and_then(|d| d.lock().unwrap().expert(data, self.ty, rows, self.cols));
        Mat { data, ty: self.ty, rows, cols: self.cols, cpu: self.cpu, gpu }
    }

    /// Ask the kernel to read expert e's pages now (madvise WILLNEED), so all selected experts of a layer queue on the SSD together.
    #[cfg(target_os = "linux")]
    pub fn prefetch_expert(&self, e: usize, n_expert: usize) {
        unsafe extern "C" { fn madvise(addr: *mut std::ffi::c_void, len: usize, advice: i32) -> i32; }
        let sz = self.rows / n_expert * self.ty.row_bytes(self.cols as u64);
        let a = self.data[e * sz..].as_ptr() as usize;
        let start = a & !4095;
        unsafe { madvise(start as *mut std::ffi::c_void, a + sz - start, 3) };
    }
    /// No madvise outside Linux (the MSVC linker has no such symbol, issue #21): the pages are read when touched.
    #[cfg(not(target_os = "linux"))]
    pub fn prefetch_expert(&self, _e: usize, _n_expert: usize) {}

    pub fn row_into(&self, r: usize, out: &mut [f32]) {
        let rb = self.ty.row_bytes(self.cols as u64);
        dequant_row(self.ty, &self.data[r * rb..(r + 1) * rb], out);
    }

    /// y = W x
    pub fn matvec(&self, x: &[f32], y: &mut [f32]) {
        assert_eq!(x.len(), self.cols);
        assert_eq!(y.len(), self.rows);
        if let (Some(i), Some(d)) = (self.gpu, dev::get()) {
            return d.lock().unwrap().gemv(i, x, y, (i == dev::STAGED).then_some((self.data, self.ty, self.rows, self.cols)));
        }
        let rb = self.ty.row_bytes(self.cols as u64);
        let xq = q8_roundtrip(self.ty, self.cpu, x);
        let x = &xq[..];
        y.par_iter_mut().enumerate().for_each_init(
            || vec![0f32; self.cols],
            |tmp, (r, o)| {
                dequant_row(self.ty, &self.data[r * rb..(r + 1) * rb], tmp);
                *o = tmp.iter().zip(x).map(|(a, b)| a * b).sum();
            },
        );
    }
}

/// ggml quantises the activation to Q8_K (k-quants, IQ1/IQ2) or Q8_0 (Q8_0, IQ4_NL) before a quantised dot.
/// Reproduce that rounding so the f32 reference tracks llama.cpp; other types see the activation unchanged.
fn q8_roundtrip(ty: GgmlType, cpu: bool, x: &[f32]) -> Vec<f32> {
    use GgmlType::*;
    let mut out = x.to_vec();
    match ty {
        Q5K | IQ1M | IQ2XXS | IQ2XS if cpu => {
            for b in out.chunks_exact_mut(256) {
                let (mut amax, mut max) = (0f32, 0f32);
                for &v in b.iter() {
                    if v.abs() > amax { amax = v.abs(); max = v; }
                }
                if amax == 0.0 { b.fill(0.0); continue; }
                let iscale = -127.0 / max;
                for v in b.iter_mut() { *v = (iscale * *v).round_ties_even().min(127.0) / iscale; }
            }
        }
        Q5K | IQ1M | IQ2XXS | IQ2XS | Q8_0 | IQ4NL => {
            for b in out.chunks_exact_mut(32) {
                let amax = b.iter().fold(0f32, |m, v| m.max(v.abs()));
                let d = amax / 127.0;
                if d == 0.0 { continue; }
                let dh = half::f16::from_f32(d).to_f32();
                for v in b.iter_mut() { *v = (*v / d).round() * dh; }
            }
        }
        _ => {}
    }
    out
}

/// Small F32/BF16 tensor fully dequantised.
pub fn vec_f32(g: &Gguf, name: &str) -> anyhow::Result<Vec<f32>> {
    let m = Mat::load(g, name)?;
    let mut v = vec![0f32; m.rows * m.cols];
    for r in 0..m.rows {
        m.row_into(r, &mut v[r * m.cols..(r + 1) * m.cols]);
    }
    Ok(v)
}
