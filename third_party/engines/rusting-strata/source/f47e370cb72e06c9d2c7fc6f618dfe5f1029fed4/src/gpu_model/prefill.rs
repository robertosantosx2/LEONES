//! Chunked prefill: the prompt runs through each layer `chunk` tokens at a time with tensor-core GEMMs. Routed experts
//! run as grouped GEMMs over the chunk's (token, expert) pairs sorted by expert; experts not resident in the cache are
//! copied into a small staging area, a group of them at a time, each group's copy beside the previous group's GEMMs.

use super::{Ffn, GpuModel, HcAt, Mixer};
use crate::backend::{Backend, Buf, GEMM_BM, SAME_X};
use crate::expert_cache::MATS;
use crate::model::Model;
use crate::weights::Prefetch;

/// Experts staged per group when a layer routes to experts outside the cache. Staging holds three groups.
const STAGE: usize = 16;

/// Float offsets into the scratch slab (each region holds `chunk` rows). Mixer and FFN regions alias, and so do the
/// hyper-connection read and PLE temporaries (`xn` .. `pv`), which run outside both.
struct Lay { h: usize, a: usize, b: usize, c: usize, d: usize, e: usize, rl: usize, wts: usize, ge: usize, ye: usize, shg: usize, shy: usize, sg: usize,
             xn: usize, lo: usize, hg: usize, pk: usize, pq: usize, pg: usize, pn: usize, pv: usize, inj: usize, mix: usize, mo: usize, emb: usize }

pub(super) struct Scratch {
    pub chunk: usize,
    lay: Lay,
    slab: Buf,
    /// ids | xrow | inv, `chunk * k` each.
    ints: Buf,
    tiles: Buf,
    staging: Buf,
}

impl Scratch {
    pub fn new(m: &Model, gpu: &dyn Backend, chunk: usize) -> anyhow::Result<Scratch> {
        let c = &m.cfg;
        let mut stage_bytes = 0;
        for il in 0..c.n_layer {
            if !c.is_moe() { break; }
            let mut b = 0;
            for name in MATS { b = (b + m.w.layer(il, name)?.expert(0, c.n_expert).data.len()).next_multiple_of(16); }  // as ExpertCache lays out a slot
            stage_bytes = stage_bytes.max(b);
        }
        let (ne, k) = (c.n_embd, c.n_expert_used.max(1));
        let (nv, kv, channels) = (c.ssm_dt_rank, c.n_head_kv * c.head_dim, c.ssm_d_inner + 2 * c.ssm_n_group * c.ssm_d_state);
        let q = c.n_head * c.head_dim;
        let hd = c.hc_n.max(1) * ne;
        let (h, base) = (hd * chunk, (hd + ne) * chunk); // x (hc_n streams a token) at 0, then h
        let mut at = base;
        let mut take = |n: usize| { let o = at; at += n * chunk; o };
        let (a, b, c2, d, e) = (take((2 * q).max(channels).max(2 * ne)), take(q.max(c.ssm_d_inner)), take(channels.max(3 * kv).max(if c.idx_top_k > 0 { (1 + 2 * super::QSA_H) * super::QSA_D } else { 0 })), take(q.max(c.ssm_d_inner)), take(2 * nv));
        let mix_end = at;
        at = base;
        let mut take = |n: usize| { let o = at; at += n * chunk; o };
        let (rl, wts, ge) = (take(c.n_expert), take(k), take((k * c.n_ff_exp).max(c.n_ff)));
        let (ye, shg, shy, sg) = (take(k * ne), take(c.n_ff_shexp), take(ne), take(1));
        let mut total = at.max(mix_end);
        let (mut xn, mut lo, mut hg, mut pk, mut pq, mut pg, mut pn, mut pv, mut inj, mut mix, mut mo, mut emb) = Default::default();
        if c.hc_n > 0 {
            at = base;
            let mut take = |n: usize| { let o = at; at += n * chunk; o };
            (xn, lo, hg, pk, pq, pg, pn, pv) = (take(hd), take(c.hc_rank), take(hd), take(hd), take(hd), take(hd), take(hd), take(ne));
            at = at.max(total);
            let mut take = |n: usize| { let o = at; at += n * chunk; o };
            (inj, mix, mo, emb) = (take(c.hc_n), take(ne), take(ne), take(ne));
            total = at;
        }
        let n_tiles = 3 * (chunk * k / GEMM_BM + 2 * c.n_expert);
        Ok(Scratch {
            chunk, lay: Lay { h, a, b, c: c2, d, e, rl, wts, ge, ye, shg, shy, sg, xn, lo, hg, pk, pq, pg, pn, pv, inj, mix, mo, emb },
            slab: gpu.zeros::<f32>(total)?, ints: gpu.zeros::<i32>(3 * chunk * k)?, tiles: gpu.zeros::<u64>(2 * n_tiles)?,
            staging: gpu.zeros::<u8>(if c.is_moe() { 3 * STAGE * stage_bytes } else { 0 })?,
        })
    }

    /// Bytes of VRAM this scratch takes.
    pub fn bytes(&self) -> usize { self.slab.len() + self.ints.len() + self.tiles.len() + self.staging.len() }
}

impl GpuModel<'_> {
    /// Run `tokens` from the current position; returns the logits after the last one. Short prompts (and models
    /// loaded without a prefill chunk) go through the decode step.
    pub fn prefill(&mut self, tokens: &[u32]) -> anyhow::Result<Vec<f32>> { self.prefill_with(tokens, &mut |_| Ok(())) }

    /// `prefill`, calling `between` between two chunks (`serve --parallel` decodes the other slots there; it must
    /// leave the current slot's state alone).
    pub fn prefill_with(&mut self, tokens: &[u32], between: &mut dyn FnMut(&mut Self) -> anyhow::Result<()>) -> anyhow::Result<Vec<f32>> {
        let Some(chunk) = self.pf.as_ref().map(|p| p.chunk) else { return self.step_all(tokens) };
        if tokens.len() < self.short { return self.step_all(tokens); }
        anyhow::ensure!(self.pos + tokens.len() <= self.ctx, "context full ({} tokens; raise --ctx)", self.ctx);
        // STRATA_PF_ADAPT=N: place the hot experts after every N-th chunk of a long prompt, not only after all of it,
        // so the later chunks run with the placement the first ones showed (0 = off, the default; untested on real hardware).
        let every = std::env::var("STRATA_PF_ADAPT").ok().and_then(|v| v.parse::<usize>().ok()).unwrap_or(0);
        let nchunks = tokens.len().div_ceil(chunk);
        for (i, ch) in tokens.chunks(chunk).enumerate() {
            if i > 0 { between(self)?; }
            self.prefill_chunk(ch, None)?;
            if every > 0 && (i + 1) % every == 0 && i + 1 < nchunks { self.adapt_experts()?; }
        }
        // The prompt's routing predicts the reply's: place its hot experts now instead of 64 per adapt during decode.
        self.adapt_experts()?;
        let s = self.tail();
        let (g, ne) = (&s.gpu, s.m.cfg.n_embd);
        let h = s.bufs["h"].addr();
        // `prefill_chunk` leaves the last hidden state in row 0 of `x`, as after `step` (the MTP draft reads it).
        match (&s.output_norm, &s.output_hc) {
            (Some(on), _) => g.rms_norm(s.x.addr(), 0, on.ptr, h, 0, ne, 1, s.m.cfg.eps)?,
            (None, Some(hr)) => s.hc_read(hr, s.x.addr(), 1, &s.hc_at())?,
            _ => unreachable!(),
        }
        g.gemv(s.output.as_ref().unwrap(), h, s.logits.addr())?;
        g.get::<f32>(&s.logits, 0, s.m.cfg.n_vocab)
    }

    /// Move the hot missed experts into VRAM (all parts of a split model). A fully resident cache has no hot missed
    /// expert to place: skip the scan over all its entries (issue #34 R2).
    fn adapt_experts(&mut self) -> anyhow::Result<()> {
        let adapt = self.adapt_every > 0;
        let mut p = Some(&mut *self);
        while let Some(q) = p {
            if let Some(cache) = q.cache.as_mut() {
                if adapt && !cache.fully_resident() { cache.adapt(q.m, &*q.gpu, usize::MAX)?; }
            }
            p = q.next.as_deref_mut();
        }
        Ok(())
    }

    /// A fresh sequence: `prefill(tokens)` from position 0, reusing earlier work. The state after `tokens[..keep]` is
    /// saved; when the saved tokens are a prefix of the next call's `tokens[..keep]`, that call starts from them
    /// (KV past them is rewritten, the recurrent state is copied back). The state after `tokens[..sys]` (the system
    /// prompt, `sys <= keep`) is stashed in host memory: a call whose history does not extend the saved one but
    /// starts with the same system prompt starts from there. A saved state that a call replaces is parked in host
    /// memory (up to `cache_ram`), and a later call that continues it takes it back, so a side request with another
    /// prompt does not cost the main conversation its cache. Returns the logits and the tokens reused.
    pub fn prefill_cached(&mut self, tokens: &[u32], sys: usize, keep: usize) -> anyhow::Result<(Vec<f32>, usize)> {
        self.prefill_cached_with(tokens, sys, keep, &mut |_| Ok(()))
    }

    /// `prefill_cached` with `prefill_with`'s `between`.
    pub fn prefill_cached_with(&mut self, tokens: &[u32], sys: usize, keep: usize, between: &mut dyn FnMut(&mut Self) -> anyhow::Result<()>)
        -> anyhow::Result<(Vec<f32>, usize)> {
        anyhow::ensure!(sys <= keep && keep < tokens.len(), "prefill_cached: sys {sys}, keep {keep} of {} tokens", tokens.len());
        let (hit, own) = (self.saved_ids.len(), self.owner);
        let stashed = self.sys.as_ref().filter(|_| self.sys_owner == own).map_or(0, |s| if tokens[..keep].starts_with(&s.3) { s.3.len() } else { 0 });
        let extends = hit > 0 && hit >= stashed && self.saved_owner == own && tokens[..keep].starts_with(&self.saved_ids);
        // The longest parked state this prompt continues, if it beats the saved one and the stash.
        let best = self.parked.iter().enumerate().filter(|(_, p)| p.owner == own && tokens[..keep].starts_with(&p.ids))
            .max_by_key(|(_, p)| p.ids.len()).map(|(i, p)| (i, p.ids.len()))
            .filter(|&(_, n)| n > stashed && !(extends && n <= hit));
        let reused = if let Some((i, n)) = best {
            self.unpark(i)?;
            n
        } else if extends {
            self.restore_state()?;
            hit
        } else if stashed > 0 {
            self.park()?;
            self.unstash()?;
            stashed
        } else {
            self.park()?;
            self.reset()?;
            0
        };
        // The stash stays valid while its KV entries do: this prompt rewrites them only past `reused`. A parked state
        // brings its own KV, which may have been computed in other chunks.
        if best.is_some() || stashed == 0 && self.sys.as_ref().is_some_and(|s| reused < s.3.len()) { self.sys = None; }
        if sys > reused {
            self.prefill_with(&tokens[reused..sys], between)?;
            self.stash(&tokens[..sys])?;
        }
        let from = reused.max(sys);
        if keep > from {
            self.prefill_with(&tokens[from..keep], between)?;
            self.save_state()?;
            (self.saved_ids, self.saved_owner) = (tokens[..keep].to_vec(), own);
        }
        Ok((self.prefill_with(&tokens[keep..], between)?, reused))
    }

    fn step_all(&mut self, tokens: &[u32]) -> anyhow::Result<Vec<f32>> {
        let mut logits = Vec::new();
        // Hyper-connection models: TMAX tokens per forward (prompts too short for the chunked GEMM prefill).
        if self.m.cfg.hc_n > 0 {
            for ch in tokens.chunks(crate::cpu_worker::TMAX) { logits = self.verify(ch)?.pop().unwrap(); }
            return Ok(logits);
        }
        for &t in tokens {
            // The draft head's entry for `t` pairs it with the hidden state of the token before (row 0 of `x`).
            if self.pos > 0 && self.mtp_synced() { let r = self.row_ptr(0); self.mtp_run(&[t], r, false)?; }
            logits = self.step(t)?;
        }
        Ok(logits)
    }

    /// `input`: the hidden rows and PLE input from the part before (None: embed `toks`).
    fn prefill_chunk(&mut self, toks: &[u32], input: Option<(&[f32], &[f32])>) -> anyhow::Result<()> {
        // Missed experts are read from the mapped weights in the order the staging copies take them.
        let pre = self.cache.is_some().then(Prefetch::start);
        let owned: (Vec<f32>, Vec<f32>);
        let (emb, pe): (&[f32], &[f32]) = match input {
            Some(v) => v,
            None => {
                let hcn = self.m.cfg.hc_n.max(1);
                let pe = if self.ple_ring.is_some() { toks.iter().flat_map(|&tk| self.m.ple_embed(&mut self.ple_prev, tk)).collect() } else { vec![] };
                owned = (toks.iter().flat_map(|&tk| self.m.embed(tk).repeat(hcn)).collect(), pe);
                (&owned.0, &owned.1)
            }
        };
        let c = &self.m.cfg;
        let pf = self.pf.as_ref().unwrap();
        let (g, mut t, n, eps, ne) = (&self.gpu, toks.len(), pf.chunk, c.eps, c.n_embd);
        let d = c.hc_n.max(1) * ne;
        g.put(emb, &pf.slab, 0)?;
        if !pe.is_empty() { g.put(pe, &pf.slab, pf.lay.emb)?; }
        g.put(&[self.pos as i32, 0], &self.step_buf, 0)?;
        let mut step = self.step_buf.addr();
        let base = pf.slab.addr();
        let at = |o: usize| base + 4 * o as u64;
        let l = &pf.lay;
        let (x, h) = (at(0), at(l.h));
        let ha = HcAt { xn: at(l.xn), lo: at(l.lo), hg: at(l.hg), inj: at(l.inj), h, hq: 0, emb: at(l.emb), pk: at(l.pk), pq: at(l.pq), pg: at(l.pg),
                        pn: at(l.pn), pv: at(l.pv), gemm: true };
        // Hyper-connections: the mixer and FFN outputs go to "mix" and "mo", then into the streams.
        let (mx, mact) = if c.hc_n > 0 { (at(l.mix), 0) } else { (x, 2) };
        let (dk, nk, nv) = (c.ssm_d_state, c.ssm_n_group, c.ssm_dt_rank);
        let (dv, channels) = (c.ssm_dv(), c.ssm_d_inner + 2 * nk * dk);
        let (hd, nh, nkv) = (c.head_dim, c.n_head, c.n_head_kv);
        let kv = nkv * hd;
        // The draft head runs as one more layer on the chunk while it is in step with the main model.
        let fill = self.mtp_synced();
        let mtp = self.mtp.as_ref().filter(|_| fill);
        // STRATA_NAN_TRACE: one line per layer with the largest magnitude of each intermediate buffer, and the first
        // row of one holding a non-finite value. Each probe waits for the GPU: diagnostic runs only.
        let trace = std::env::var_os("STRATA_NAN_TRACE").is_some();
        let mut tr = String::new();
        let probe = |tr: &mut String, what: &str, b: &Buf, o: u64, w: usize, rows: usize| -> anyhow::Result<()> {
            if !trace { return Ok(()); }
            let v: Vec<f32> = g.get(b, ((o - b.addr()) / 4) as usize, rows * w)?;
            let max = v.iter().filter(|a| a.is_finite()).fold(0f32, |m, a| m.max(a.abs()));
            tr.push_str(&format!(" {what} {max:.2e}"));
            if let Some(i) = v.iter().position(|a| !a.is_finite()) { tr.push_str(&format!(" (non-finite row {})", i / w)); }
            Ok(())
        };
        for (il, ly) in self.layers.iter().enumerate().map(|(i, ly)| (self.first + i, ly)).chain(mtp.map(|mh| (c.n_layer, &mh.layer))) {
            if let Some(mh) = mtp.filter(|_| il == c.n_layer) {
                // Its entry for token i pairs the token with the hidden state before it (`mtp_run`): h gets the last
                // hidden state of the previous chunk, then rows 0..t - 1; the first token of the sequence has none.
                let skip = (self.pos == 0) as usize;
                if skip == 0 { g.dtod(&self.x, 0, &pf.slab, 4 * l.h, 4 * ne)?; }
                g.dtod(&pf.slab, 0, &pf.slab, 4 * (l.h + (1 - skip) * ne), 4 * (t - 1) * ne)?;
                g.dtod(&pf.slab, 4 * (t - 1) * ne, &self.x, 0, 4 * ne)?;
                let emb: Vec<f32> = toks[skip..].iter().flat_map(|&tk| self.m.embed(tk)).collect();
                g.put(&emb, &pf.slab, 0)?;
                t -= skip;
                g.rms_norm(x, ne, mh.enorm.ptr, at(l.a), 2 * ne, ne, t, eps)?;
                g.rms_norm(h, ne, mh.hnorm.ptr, at(l.a + ne), 2 * ne, ne, t, eps)?;
                g.gemm_dense(&mh.eh_proj, t, at(l.a), 2 * ne, x, ne, 0)?;
                g.put(&[mh.pos as i32, 0], &self.step_buf, 2)?;
                step += 8;
            }
            if let Some(pl) = &ly.ple { self.ple(pl, x, step, t, &ha)?; }
            match (&ly.attn_norm, &ly.hc) {
                (Some(an), _) => g.rms_norm(x, ne, an.ptr, h, ne, ne, t, eps)?,
                (None, Some(hr)) => self.hc_read(&hr[0], x, t, &ha)?,
                _ => unreachable!(),
            }
            match &ly.mixer {
                Mixer::Delta { qkv, gate, beta, alpha, dt_bias, a, conv_w, norm, out, conv, s, .. } => {
                    let (eb, eg) = (at(l.e), at(l.e + n * nv));
                    g.gemm_dense(qkv, t, h, ne, at(l.a), channels, 0)?;
                    // The qkv GEMM above already quantized `h`; when it did not (IQ2_XS, or a shape the int8 GEMM
                    // skips), prepare it now so beta, alpha and the gate can all reuse one copy.
                    g.prequant_gemm_x(gate, t, h, ne)?;
                    g.conv_seq(at(l.a), conv[self.cur].addr(), conv_w.ptr, at(l.c), channels, c.ssm_conv, t, 0, 0)?;
                    // The beta and alpha GEMMs (16 blocks each) run beside the norm: batch launches alternate streams.
                    g.batch(&mut || {
                        g.gemm_dense(beta, t, h, ne, eb, nv, SAME_X)?;
                        g.l2_norm(at(l.c), dk, 2 * nk, channels, t * 2 * nk, eps)?;
                        g.gemm_dense(alpha, t, h, ne, eg, nv, SAME_X)
                    })?;
                    g.ssm_gates(eb, eg, dt_bias.ptr, a.ptr, t * nv, nv)?;
                    probe(&mut tr, "qkv", &pf.slab, at(l.a), channels, t)?;
                    probe(&mut tr, "conv", &pf.slab, at(l.c), channels, t)?;
                    probe(&mut tr, "beta", &pf.slab, eb, nv, t)?;
                    probe(&mut tr, "alpha", &pf.slab, eg, nv, t)?;
                    // The z GEMM runs beside the scan, on the SMs its last wave of blocks leaves idle.
                    g.batch(&mut || {
                        g.deltanet(at(l.c), s[self.cur].addr(), eb, eg, 0, 0, at(l.d), nk, nv, c.k_interleave, dk, dv, 1.0 / (dk as f32).sqrt(), t, channels, 0, 0)?;
                        g.gemm_dense(gate, t, h, ne, at(l.b), c.ssm_d_inner, SAME_X)
                    })?;
                    probe(&mut tr, "deltanet", &pf.slab, at(l.d), c.ssm_d_inner, t)?;
                    probe(&mut tr, "state", &s[self.cur], s[self.cur].addr(), s[self.cur].len() / 4, 1)?;
                    probe(&mut tr, "z", &pf.slab, at(l.b), c.ssm_d_inner, t)?;
                    if ly.hc.is_some() { g.norm_gate_sig(at(l.d), norm.ptr, at(l.b), dv, t * nv, eps, 0)?; } else { g.norm_gate(at(l.d), norm.ptr, at(l.b), dv, t * nv, eps)?; }
                    g.gemm_dense(out, t, at(l.d), c.ssm_d_inner, mx, ne, mact)?;
                }
                Mixer::Attn { q, k, v, qn, kn, o, kc, vc, qsa } => {
                    let (kraw, kk, vv) = (at(l.c), at(l.c + n * kv), at(l.c + 2 * n * kv));
                    let qs = if c.q_gate { 2 * hd } else { hd };
                    g.gemm_dense(q, t, h, ne, at(l.a), nh * qs, 0)?;
                    g.rms_norm(at(l.a), qs, qn.ptr, at(l.b), hd, hd, t * nh, eps)?;
                    g.rope_neox(at(l.b), hd, t * nh, nh, c.n_rot, step, c.rope_base)?;
                    g.gemm_dense(k, t, h, ne, kraw, kv, SAME_X)?;
                    g.gemm_dense(v, t, h, ne, vv, kv, SAME_X)?;
                    g.rms_norm(kraw, hd, kn.ptr, kk, hd, hd, t * nkv, eps)?;
                    g.rope_neox(kk, hd, t * nkv, nkv, c.n_rot, step, c.rope_base)?;
                    g.kv_store(kk, vv, kc[self.cur].addr(), vc[self.cur].addr(), kv, t, step, hd)?;
                    // QSA: region c (free after kv_store) holds the raw indexer keys, raw queries and normed queries.
                    let (qm, mw) = match (qsa, &self.qsa) {
                        (Some(a), Some(b)) => {
                            let (ik, iq, iqn) = (at(l.c), at(l.c + n * super::QSA_D), at(l.c + n * (1 + super::QSA_H) * super::QSA_D));
                            let (dq, nq) = (super::QSA_D, super::QSA_H * super::QSA_D);
                            g.gemm_dense(&a.kp, t, h, ne, ik, dq, 0)?;
                            g.gemm_dense(&a.qp, t, h, ne, iq, nq, SAME_X)?;
                            g.qsa_pool(ik, a.ring, a.pool.addr(), a.kn.ptr, step, t, c.n_rot, c.rope_base, eps)?;
                            // Rows with at most `top` complete blocks attend densely: no mask while all of them do.
                            if self.pos + t >= super::QSA_POOL * (b.top + 1) {
                                g.rms_norm(iq, dq, a.qn.ptr, iqn, dq, dq, t * super::QSA_H, eps)?;
                                g.rope_neox(iqn, dq, t * super::QSA_H, super::QSA_H, c.n_rot, step, c.rope_base)?;
                                for r0 in (0..t).step_by(super::QSA_ROWS) {
                                    g.qsa_select(iqn + (4 * r0 * nq) as u64, a.pool.addr(), b.score.addr(), 0, b.mask.addr() + (4 * r0 * b.mw) as u64,
                                                 step, r0, super::QSA_ROWS.min(t - r0), b.nbs, b.top, 0, b.mw)?;
                                }
                                (b.mask.addr(), b.mw)
                            } else { (0, 0) }
                        }
                        _ => (0, 0),
                    };
                    g.attn_prefill_m(at(l.b), kc[self.cur].addr(), vc[self.cur].addr(), if c.q_gate { at(l.a) } else { 0 }, at(l.d), step, t, nh, nkv, hd, 1.0 / (hd as f32).sqrt(), qm, mw)?;
                    probe(&mut tr, "q", &pf.slab, at(l.a), nh * qs, t)?;
                    probe(&mut tr, "k", &pf.slab, kk, kv, t)?;
                    probe(&mut tr, "v", &pf.slab, vv, kv, t)?;
                    probe(&mut tr, "attn", &pf.slab, at(l.d), nh * hd, t)?;
                    g.gemm_dense(o, t, at(l.d), nh * hd, mx, ne, mact)?;
                }
            }
            probe(&mut tr, "| mixer", &pf.slab, x, d, t)?;
            match (&ly.post_norm, &ly.hc) {
                (Some(pn), _) => g.rms_norm(x, ne, pn.ptr, h, ne, ne, t, eps)?,
                (None, Some(hr)) => {
                    g.hc_write(x, mx, at(l.inj), ne, c.hc_n, t, false)?;
                    self.hc_read(&hr[1], x, t, &ha)?;
                }
                _ => unreachable!(),
            }
            match &ly.ffn {
                Ffn::Dense { gate, up, down } => {
                    g.gemm_dense(gate, t, h, ne, at(l.ge), c.n_ff, 0)?;
                    g.gemm_dense(up, t, h, ne, at(l.ge), c.n_ff, 1 | SAME_X)?;
                    probe(&mut tr, "gate_up", &pf.slab, at(l.ge), c.n_ff, t)?;
                    g.gemm_dense(down, t, at(l.ge), c.n_ff, x, ne, 2)?;
                }
                Ffn::Moe { router, shared } => {
                    let k = c.n_expert_used;
                    let ids_d = pf.ints.addr();
                    // The 1-row shared gate_inp GEMM runs beside the router GEMM (both float: one launch each).
                    g.batch(&mut || {
                        g.gemm_dense(router, t, h, ne, at(l.rl), c.n_expert, 0)?;
                        if let Some(s) = shared { g.gemm_dense(&s.gate_inp, t, h, ne, at(l.sg), 1, SAME_X)?; }
                        Ok(())
                    })?;
                    g.router_topk(at(l.rl), c.n_expert, k, c.expert_weights_scale, ids_d, at(l.wts), t)?;
                    let (sh, sg) = match shared {
                        Some(s) => {
                            g.gemm_dense(&s.gate, t, h, ne, at(l.shg), c.n_ff_shexp, SAME_X)?;
                            g.gemm_dense(&s.up, t, h, ne, at(l.shg), c.n_ff_shexp, 1 | SAME_X)?;
                            (at(l.shy), at(l.sg))
                        }
                        None => (0, 0),
                    };
                    probe(&mut tr, "router", &pf.slab, at(l.rl), c.n_expert, t)?;
                    probe(&mut tr, "weights", &pf.slab, at(l.wts), k, t)?;
                    let ids = g.get::<i32>(&pf.ints, 0, t * k)?;
                    let cache = self.cache.as_mut().unwrap();
                    cache.record(il, &ids);
                    // Sort (token, j) pairs by expert: slot s holds token xrow[s]; inv maps t * k + j to its slot.
                    let mut off = vec![0usize; c.n_expert + 1];
                    for &e in &ids { off[e as usize + 1] += 1; }
                    for e in 0..c.n_expert { off[e + 1] += off[e]; }
                    let (mut fill, mut xrow, mut inv) = (off.clone(), vec![0i32; t * k], vec![0i32; t * k]);
                    for (i, &e) in ids.iter().enumerate() {
                        let s = &mut fill[e as usize];
                        xrow[*s] = (i / k) as i32;
                        inv[i] = *s as i32;
                        *s += 1;
                    }
                    g.put(&xrow, &pf.ints, n * k)?;
                    g.put(&inv, &pf.ints, 2 * n * k)?;
                    let lx = cache.layer(il).unwrap();
                    let (pool, stride) = cache.base(lx);
                    let used = |e: &usize| off[e + 1] > off[*e];
                    let missed: Vec<usize> = (0..c.n_expert).filter(used).filter(|&e| cache.slot(il, e) < 0).collect();
                    if let Some(pre) = &pre {
                        let w: Vec<_> = MATS.iter().map(|name| self.m.w.layer(il, name)).collect::<anyhow::Result<_>>()?;
                        pre.send(missed.chunks(STAGE).flat_map(|grp| w.iter().zip(&lx.mats).flat_map(move |(w, mat)| grp.chunk_by(|a, b| *b == a + 1)
                            .map(move |run| (w.data.as_ptr() as usize + run[0] * mat.bytes, run.len() * mat.bytes)))).collect());
                    }
                    // Staged groups of at most STAGE missed experts, group j in staging third j % 3. Staging holds
                    // each matrix in its own section (all gates, then ups, then downs), so experts with consecutive
                    // ids are contiguous there as in the weights and copy in one call.
                    let sp = pf.staging.addr();
                    let half = |j: usize| j % 3 * pf.staging.len() / 3;
                    let staged: Vec<Vec<(usize, [u64; 3])>> = missed.chunks(STAGE).enumerate()
                        .map(|(j, grp)| grp.iter().enumerate().map(|(i, &e)| (e, lx.mats.each_ref().map(|m| sp + (half(j) + STAGE * m.off + i * m.bytes) as u64))).collect())
                        .collect();
                    // The resident experts split into one chunk per staged group, of about equal positions, so the
                    // copies run beside them too: step s runs group s - 2 and chunk s beside the copy of group s
                    // (into the third group s - 3 used, done in step s - 1). A step waits only for the copies of the
                    // step two before it (`beside`), so each copy has two steps of GEMMs to hide behind.
                    // Without overlap (Vulkan without a transfer queue) one chunk: more, smaller GEMMs only cost there.
                    let ns = if g.beside_overlaps() { staged.len().max(1) } else { 1 };
                    let res: Vec<(usize, [u64; 3])> = (0..c.n_expert).filter(used)
                        .filter_map(|e| { let s = cache.slot(il, e); (s >= 0).then(|| (e, lx.mats.each_ref().map(|m| pool + (s as usize * stride + m.off) as u64))) }).collect();
                    let total = res.iter().map(|r| off[r.0 + 1] - off[r.0]).sum::<usize>().max(1);
                    let mut chunks = vec![Vec::new(); ns];
                    let mut acc = 0;
                    for &r in &res {
                        chunks[(acc * ns / total).min(ns - 1)].push(r);
                        acc += off[r.0 + 1] - off[r.0];
                    }
                    let mut chunks = chunks.into_iter();
                    let mut groups = vec![];
                    // Per step: its groups and the staged group it copies.
                    let mut steps = vec![];
                    for s in 0..staged.len() + 2 {
                        let g0 = groups.len();
                        groups.extend(s.checked_sub(2).and_then(|j| staged.get(j)).cloned());
                        groups.extend(chunks.next());
                        steps.push((g0..groups.len(), (s < staged.len()).then_some(s)));
                    }
                    let mut tiles = Vec::new();
                    let push = |tiles: &mut Vec<u64>, grp: &[(usize, [u64; 3])], mi: usize, base: usize| {
                        let start = tiles.len() / 2;
                        for &(e, w) in grp {
                            for m0 in (off[e]..off[e + 1]).step_by(GEMM_BM) {
                                tiles.extend([w[mi], (m0 - base) as u64 | (GEMM_BM.min(off[e + 1] - m0) as u64) << 32]);
                            }
                        }
                        (start, tiles.len() / 2 - start)
                    };
                    // Per step: the gate and up tiles of all its groups (one launch each: more blocks, less tail), then
                    // per group its down tiles and the slot rows lo..hi it covers. The down GEMM reads rows lo..hi of
                    // `ge` only, so its tiles count from lo and it quantizes just those rows.
                    let mut spans = Vec::new();
                    for (gs, _) in &steps {
                        let gu = [0, 1].map(|mi| { let s = tiles.len() / 2; for gi in gs.clone() { push(&mut tiles, &groups[gi], mi, 0); } (s, tiles.len() / 2 - s) });
                        let downs: Vec<_> = gs.clone().filter(|&gi| !groups[gi].is_empty()).map(|gi| {
                            let grp = &groups[gi];
                            let (lo, hi) = (off[grp[0].0], off[grp[grp.len() - 1].0 + 1]);
                            (push(&mut tiles, grp, 2, lo), lo, hi)
                        }).collect();
                        spans.push((gu, downs));
                    }
                    anyhow::ensure!(8 * tiles.len() <= pf.tiles.len(), "prefill tile list overflow");
                    g.put(&tiles, &pf.tiles, 0)?;
                    let tp = |s: usize| pf.tiles.addr() + 16 * s as u64;
                    let xrow_d = pf.ints.addr() + 4 * (n * k) as u64;
                    let [mg, mu, md] = lx.mats;
                    let copy = |j: usize| -> anyhow::Result<()> {
                        let grp = &staged[j];
                        for (name, mat) in MATS.iter().zip(&lx.mats) {
                            let w = self.m.w.layer(il, name)?;
                            let mut i = 0;
                            for run in grp.chunk_by(|a, b| b.0 == a.0 + 1) {
                                let e = run[0].0;
                                g.htod(&w.data[e * mat.bytes..(e + run.len()) * mat.bytes], &pf.staging, half(j) + STAGE * mat.off + i * mat.bytes)?;
                                i += run.len();
                            }
                        }
                        Ok(())
                    };
                    // `beside` starts a step's copies after the GEMMs before it. They queue last, so the GEMMs need not
                    // wait for the host to stage them.
                    for ((_, cp), (gu, downs)) in steps.iter().zip(&spans) {
                        g.beside(&mut || {
                            if gu[0].1 > 0 {
                                g.gemm(mg.ty, mg.rows, mg.cols, tp(gu[0].0), gu[0].1, h, ne, t, xrow_d, at(l.ge), c.n_ff_exp, SAME_X)?;
                                g.gemm(mu.ty, mu.rows, mu.cols, tp(gu[1].0), gu[1].1, h, ne, t, xrow_d, at(l.ge), c.n_ff_exp, 1 | SAME_X)?;
                            }
                            for &((s0, n0), lo, hi) in downs {
                                g.gemm(md.ty, md.rows, md.cols, tp(s0), n0, at(l.ge) + (4 * lo * c.n_ff_exp) as u64, c.n_ff_exp, hi - lo, 0, at(l.ye) + (4 * lo * ne) as u64, ne, 0)?;
                            }
                            if let Some(j) = *cp { copy(j)?; }
                            Ok(())
                        })?;
                    }
                    g.beside_join()?;
                    // The shared down runs last, so the routed gate and up above reuse the int8 h of the shared up.
                    if let Some(s) = shared { g.gemm_dense(&s.down, t, at(l.shg), c.n_ff_shexp, at(l.shy), ne, 0)?; }
                    // Expert rows are slots (token, j) sorted by expert, not tokens.
                    probe(&mut tr, "experts_gate_up", &pf.slab, at(l.ge), c.n_ff_exp, t * k)?;
                    probe(&mut tr, "experts_down", &pf.slab, at(l.ye), ne, t * k)?;
                    if shared.is_some() {
                        probe(&mut tr, "shared_gate_up", &pf.slab, at(l.shg), c.n_ff_shexp, t)?;
                        probe(&mut tr, "shared_down", &pf.slab, at(l.shy), ne, t)?;
                        probe(&mut tr, "shared_gate", &pf.slab, at(l.sg), 1, t)?;
                    }
                    // "mo" is zero: hc_write clears it after use.
                    let fx = if ly.hc.is_some() { at(l.mo) } else { x };
                    g.moe_combine_seq(fx, at(l.ye), at(l.wts), pf.ints.addr() + 4 * (2 * n * k) as u64, k, sh, sg, ne, t)?;
                    if ly.hc.is_some() { g.hc_write(x, fx, at(l.inj), ne, c.hc_n, t, true)?; }
                }
            }
            probe(&mut tr, "| ffn", &pf.slab, x, d, t)?;
            if trace { eprintln!("nan-trace pos {} layer {il}:{tr}", self.pos); tr.clear(); }
            g.kick()?;
        }
        match self.mtp.as_mut() {
            Some(mh) if fill => mh.pos += t,
            // Row 0 of `x` gets the last hidden state (with the draft head, the copy above did it).
            _ => g.dtod(&pf.slab, 4 * (t - 1) * d, &self.x, 0, 4 * d)?,
        }
        self.pos += toks.len();
        let Some(nx) = self.next.as_deref_mut() else { return Ok(()) };
        let xs = self.gpu.get::<f32>(&self.pf.as_ref().unwrap().slab, 0, toks.len() * d)?;
        nx.prefill_chunk(toks, Some((&xs, pe)))
    }
}
