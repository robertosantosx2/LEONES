//! Named tensor views over the mmapped GGUF, page cache advice for them, and a reference parallel matvec.

use crate::config::ModelConfig;
use crate::gguf::Gguf;
use crate::quant::{GgmlType, dequant_row};
use anyhow::Context;
use rayon::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Copy)]
pub struct Tensor<'a> {
    pub ty: GgmlType,
    /// Elements per row (GGUF dims[0]).
    pub cols: usize,
    /// Product of the remaining dims; for 3-D expert tensors this is out_rows * n_expert.
    pub rows: usize,
    pub data: &'a [u8],
}

impl<'a> Tensor<'a> {
    fn row_bytes(&self) -> usize { self.ty.row_bytes(self.cols as u64) }

    pub fn row(&self, r: usize, out: &mut [f32]) {
        let rb = self.row_bytes();
        dequant_row(self.ty, &self.data[r * rb..(r + 1) * rb], out);
    }

    /// y[r] = row_r · x for all rows.
    pub fn matvec(&self, x: &[f32], y: &mut [f32]) {
        assert_eq!((x.len(), y.len()), (self.cols, self.rows));
        y.par_chunks_mut(16).enumerate().for_each_init(|| vec![0f32; self.cols], |buf, (ci, ys)| {
            for (k, yv) in ys.iter_mut().enumerate() {
                self.row(ci * 16 + k, buf);
                *yv = buf.iter().zip(x).map(|(a, b)| a * b).sum();
            }
        });
    }

    /// Rows belonging to expert `e` of an [cols, out, n_expert] tensor.
    pub fn expert(&self, e: usize, n_expert: usize) -> Tensor<'a> {
        let rows = self.rows / n_expert;
        let rb = self.row_bytes();
        Tensor { rows, data: &self.data[e * rows * rb..(e + 1) * rows * rb], ..*self }
    }

    pub fn to_f32(&self) -> Vec<f32> {
        let mut v = vec![0f32; self.rows * self.cols];
        for (r, out) in v.chunks_exact_mut(self.cols).enumerate() { self.row(r, out); }
        v
    }
}

pub struct Weights<'a> {
    pub g: &'a Gguf,
    aliases: &'static [(&'static str, &'static str)],
    /// Loader-owned overrides: synthesized `ssm_beta`/`ssm_alpha` and LoRA-baked tensors.
    pub built: HashMap<String, Tensor<'a>>,
    /// Heap storage the baked tensors in `built` point into. Kept beside `built` so a reload frees it instead of
    /// leaking the F32 copy; `built` is cleared before `baked` so no tensor outlives its bytes.
    baked: HashMap<String, Box<[u8]>>,
    pub lora_baked: std::collections::HashSet<String>,
}

impl<'a> Weights<'a> {
    pub fn new(g: &'a Gguf) -> anyhow::Result<Weights<'a>> {
        let c = ModelConfig::from_gguf(g)?;
        let mut w = Weights { g, aliases: c.aliases, built: HashMap::new(), baked: HashMap::new(), lora_baked: std::collections::HashSet::new() };
        // llama.cpp src/models/qwen3next.cpp: per key head group, r = nv / nk beta rows, then r alpha rows.
        for il in 0..c.n_layer {
            let Ok(ba) = w.layer(il, "ssm_ba.weight") else { continue };
            let (nk, nv, rb) = (c.ssm_n_group, c.ssm_dt_rank, ba.row_bytes());
            anyhow::ensure!(nk > 0 && nv > 0 && nv % nk == 0 && ba.rows == 2 * nv && ba.data.len() == ba.rows * rb,
                "blk.{il}.ssm_ba: {} rows, {} bytes for group_count {nk}, time_step_rank {nv}", ba.rows, ba.data.len());
            let r = nv / nk;
            let (mut b, mut a) = (Vec::with_capacity(ba.data.len() / 2), Vec::with_capacity(ba.data.len() / 2));
            for grp in ba.data.chunks_exact(2 * r * rb) {
                b.extend_from_slice(&grp[..r * rb]);
                a.extend_from_slice(&grp[r * rb..]);
            }
            // ponytail: leaked, a few KB per layer per load; own the bytes in Weights if one process loads many models.
            let leak = |v: Vec<u8>| -> &'a [u8] { Box::leak(v.into_boxed_slice()) };
            let half = Tensor { rows: ba.rows / 2, ..ba };
            w.built.insert(format!("blk.{il}.ssm_beta.weight"), Tensor { data: leak(b), ..half });
            w.built.insert(format!("blk.{il}.ssm_alpha.weight"), Tensor { data: leak(a), ..half });
        }
        Ok(w)
    }

    /// `name` with the architecture's alias for a canonical suffix tried second.
    pub fn get(&self, name: &str) -> anyhow::Result<Tensor<'a>> {
        if let Some(t) = self.built.get(name) { return Ok(*t); }
        let t = self.g.tensors.get(name)
            .or_else(|| self.aliases.iter().find_map(|&(c, a)| self.g.tensors.get(&format!("{}{a}", name.strip_suffix(c)?))))
            .with_context(|| format!("missing tensor {name}"))?;
        let ty = GgmlType::from_u32(t.ty).with_context(|| format!("tensor {name}"))?;
        Ok(Tensor {
            ty,
            cols: t.dims[0] as usize,
            rows: t.dims[1..].iter().product::<u64>() as usize,
            data: self.g.bytes(t),
        })
    }

    pub fn layer(&self, il: usize, suffix: &str) -> anyhow::Result<Tensor<'a>> { self.get(&format!("blk.{il}.{suffix}")) }

    /// Refuse files containing quant types this engine does not implement, except in the MTP (nextn) layers, blocks
    /// `n_layer` on: false if one of those has such a type, so that the model loads without MTP.
    /// Drop the LoRA-baked overrides and the heap copies they point into; synthesized `ssm_*` tensors stay.
    pub fn clear_baked(&mut self) {
        for name in std::mem::take(&mut self.lora_baked) { self.built.remove(&name); }
        self.baked.clear();
    }

    pub fn bake_lora(&mut self, loras: &[crate::model::Lora]) {
        for lora in loras {
            for (name, entry) in &lora.entries {
                if name.ends_with("ffn_down_exps.weight") { continue; }
                if entry.n_expert != 1 {
                    eprintln!("lora: target {name} has {} experts, expected 1; skipping", entry.n_expert);
                    continue;
                }
                let base = match self.get(name) { Ok(t) => t, Err(_) => { eprintln!("lora: target {name} not found, skipping"); continue; } };
                if base.cols != entry.in_dim || base.rows != entry.out_dim {
                    eprintln!("lora: target {name} is {}x{}, adapter is {}x{}; skipping", base.rows, base.cols, entry.out_dim, entry.in_dim);
                    continue;
                }
                let mut w = base.to_f32();
                let (a, b) = (&entry.a[0], &entry.b[0]);
                let (rank, in_dim, out_dim) = (entry.rank, entry.in_dim, entry.out_dim);
                let mult = if lora.alpha > 0.0 { lora.scale * lora.alpha / rank as f32 } else { lora.scale };
                for o in 0..out_dim {
                    for i in 0..in_dim {
                        let mut d = 0f32;
                        for r in 0..rank { d += b[o * rank + r] * a[r * in_dim + i]; }
                        w[o * in_dim + i] += mult * d;
                    }
                }
                self.built.remove(name);
                self.baked.remove(name);
                let bytes: Box<[u8]> = w.iter().flat_map(|f| f.to_le_bytes()).collect();
                // `bytes` lives in `self.baked` until `clear_baked`, which removes the tensor below first.
                let data: &'a [u8] = unsafe { std::slice::from_raw_parts(bytes.as_ptr(), bytes.len()) };
                let t = Tensor { ty: crate::quant::GgmlType::F32, cols: base.cols, rows: base.rows, data };
                self.baked.insert(name.clone(), bytes);
                self.built.insert(name.clone(), t);
                self.lora_baked.insert(name.clone());
            }
        }
    }
    pub fn validate(&self, n_layer: usize) -> anyhow::Result<bool> {
        let mut nextn = true;
        for t in self.g.tensors.values() {
            if let Err(e) = GgmlType::from_u32(t.ty) {
                let il = t.name.strip_prefix("blk.").and_then(|r| r.split('.').next()).and_then(|i| i.parse::<usize>().ok());
                if il.is_some_and(|il| il >= n_layer) { nextn = false; continue; }
                return Err(e).with_context(|| format!("tensor {}", t.name));
            }
        }
        Ok(nextn)
    }
}

#[cfg(target_os = "linux")]
fn madvise(p: usize, n: usize, advice: i32) {
    unsafe extern "C" { fn madvise(addr: *mut std::ffi::c_void, len: usize, advice: i32) -> i32; }
    unsafe { madvise(p as *mut _, n, advice) };
}
#[cfg(not(target_os = "linux"))]
fn madvise(_: usize, _: usize, _: i32) {}

/// Starts reading mapped bytes p..p + n into the page cache without waiting (MADV_WILLNEED).
pub fn will_need(p: usize, n: usize) {
    // One call reads at most one readahead window (read_ahead_kb, 128-256 KB on NVMe).
    let (mut a, end) = (p & !4095, p + n);
    while a < end {
        let l = (end - a).min(256 << 10);
        madvise(a, l, 3);
        a += l;
    }
}

/// Marks the whole pages of `b` first to reclaim (MADV_COLD): bytes now on the GPU. Expert files exceed the page
/// cache, and pages read once at load would otherwise outlive the experts a prompt reads from it.
pub fn cold(b: &[u8]) {
    let (a, e) = ((b.as_ptr() as usize + 4095) & !4095, (b.as_ptr() as usize + b.len()) & !4095);
    if e > a { madvise(a, e - a, 20); }
}

/// Reads ranges of mapped weights into the page cache from a background thread (`will_need`), in the order sent, so
/// a cold read keeps many drive reads in flight instead of one page fault at a time. Dropping it joins the thread.
pub struct Prefetch { tx: Option<std::sync::mpsc::Sender<Vec<(usize, usize)>>>, th: Option<std::thread::JoinHandle<()>> }

impl Prefetch {
    pub fn start() -> Prefetch {
        let (tx, rx) = std::sync::mpsc::channel::<Vec<(usize, usize)>>();
        let th = std::thread::spawn(move || for rs in rx { for (p, n) in rs { will_need(p, n); } });
        Prefetch { tx: Some(tx), th: Some(th) }
    }
    /// (address, bytes) ranges of mapped weights.
    pub fn send(&self, rs: Vec<(usize, usize)>) { let _ = self.tx.as_ref().unwrap().send(rs); }
}

impl Drop for Prefetch {
    fn drop(&mut self) {
        self.tx = None;
        if let Some(t) = self.th.take() { let _ = t.join(); }
    }
}
