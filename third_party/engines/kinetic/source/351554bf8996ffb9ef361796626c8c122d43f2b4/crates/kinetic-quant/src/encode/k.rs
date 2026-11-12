//! Super-blocks of 256: Q4_K, Q5_K, Q6_K, as llama.cpp's reference
//! quantizers choose them (see ggml-quants.c quantize_row_q4_K_ref).

use super::{f16, f16_to_f32};

const GROUP_MAX_EPS: f32 = 1e-15;

/// Rounds half to even through the float adder, as ggml's nearest_int.
fn nearest_int(v: f32) -> i32 {
    ((v + 12_582_912.0).to_bits() & 0x007f_ffff) as i32 - 0x0040_0000
}

/// Scale and negated minimum of a group, codes in `l`, chosen by a search
/// over scales that minimizes the weighted squared error.
fn qkx2(
    x: &[f32],
    w: &[f32],
    nmax: i32,
    l: &mut [u8],
    rmin: f32,
    rdelta: f32,
    nstep: i32,
) -> (f32, f32) {
    let n = x.len();
    let (mut min, mut max) = (x[0], x[0]);
    let mut sum_w = w[0];
    let mut sum_x = sum_w * x[0];
    for i in 1..n {
        if x[i] < min {
            min = x[i];
        }
        if x[i] > max {
            max = x[i];
        }
        sum_w += w[i];
        sum_x += w[i] * x[i];
    }
    if min > 0.0 {
        min = 0.0;
    }
    if max == min {
        l.fill(0);
        return (0.0, -min);
    }
    let mut iscale = nmax as f32 / (max - min);
    let mut scale = 1.0 / iscale;
    let mut best = 0.0f32;
    for i in 0..n {
        let q = nearest_int(iscale * (x[i] - min)).clamp(0, nmax);
        l[i] = q as u8;
        let diff = scale * l[i] as f32 + min - x[i];
        best += w[i] * (diff * diff);
    }
    let mut aux = [0u8; 32];
    for is in 0..=nstep {
        iscale = (rmin + rdelta * is as f32 + nmax as f32) / (max - min);
        let (mut sum_l, mut sum_l2, mut sum_xl) = (0.0f32, 0.0f32, 0.0f32);
        for i in 0..n {
            let q = nearest_int(iscale * (x[i] - min)).clamp(0, nmax);
            aux[i] = q as u8;
            let q = q as f32;
            sum_l += w[i] * q;
            sum_l2 += w[i] * q * q;
            sum_xl += w[i] * q * x[i];
        }
        let det = sum_w * sum_l2 - sum_l * sum_l;
        if det > 0.0 {
            let mut this_scale = (sum_w * sum_xl - sum_x * sum_l) / det;
            let mut this_min = (sum_l2 * sum_x - sum_l * sum_xl) / det;
            if this_min > 0.0 {
                this_min = 0.0;
                this_scale = sum_xl / sum_l2;
            }
            let mut err = 0.0f32;
            for i in 0..n {
                let diff = this_scale * aux[i] as f32 + this_min - x[i];
                err += w[i] * (diff * diff);
            }
            if err < best {
                l[..n].copy_from_slice(&aux[..n]);
                best = err;
                scale = this_scale;
                min = this_min;
            }
        }
    }
    (scale, -min)
}

/// Scale of a group of signed codes in `l` (offset by `nmax`), searched
/// around the plain max-based scale, weighted by `x²`.
fn qx(x: &[f32], nmax: i32, l: &mut [i8]) -> f32 {
    let (mut amax, mut max) = (0.0f32, 0.0f32);
    for &v in x {
        if v.abs() > amax {
            amax = v.abs();
            max = v;
        }
    }
    if amax < GROUP_MAX_EPS {
        l.fill(0);
        return 0.0;
    }
    let code = |iscale: f32, v: f32| nearest_int(iscale * v).clamp(-nmax, nmax - 1);
    let sums = |iscale: f32| {
        let (mut sumlx, mut suml2) = (0.0f32, 0.0f32);
        for &v in x {
            let q = code(iscale, v) as f32;
            let w = v * v;
            sumlx += w * v * q;
            suml2 += w * q * q;
        }
        (sumlx, suml2)
    };
    let mut iscale = -(nmax as f32) / max;
    for (o, &v) in l.iter_mut().zip(x) {
        *o = (code(iscale, v) + nmax) as i8;
    }
    let (sumlx, suml2) = sums(iscale);
    let mut scale = if suml2 != 0.0 { sumlx / suml2 } else { 0.0 };
    let mut best = scale * sumlx;
    for is in -9..=9 {
        if is == 0 {
            continue;
        }
        iscale = -(nmax as f32 + 0.1 * is as f32) / max;
        let (sumlx, suml2) = sums(iscale);
        if suml2 > 0.0 && sumlx * sumlx > best * suml2 {
            for (o, &v) in l.iter_mut().zip(x) {
                *o = (code(iscale, v) + nmax) as i8;
            }
            scale = sumlx / suml2;
            best = scale * sumlx;
        }
    }
    scale
}

/// Packs eight 6-bit scales and mins into the 12 bytes of Q4_K and Q5_K.
fn pack_scales(ls: &[u8; 8], lm: &[u8; 8]) -> [u8; 12] {
    let mut s = [0u8; 12];
    for j in 0..8 {
        if j < 4 {
            s[j] = ls[j];
            s[j + 4] = lm[j];
        } else {
            s[j + 4] = (ls[j] & 0xF) | ((lm[j] & 0xF) << 4);
            s[j - 4] |= (ls[j] >> 4) << 6;
            s[j] |= (lm[j] >> 4) << 6;
        }
    }
    s
}

fn scale_min(j: usize, q: &[u8; 12]) -> (u8, u8) {
    if j < 4 {
        (q[j] & 63, q[j + 4] & 63)
    } else {
        (
            (q[j + 4] & 0xF) | ((q[j - 4] >> 6) << 4),
            (q[j + 4] >> 4) | ((q[j] >> 6) << 4),
        )
    }
}

/// The shared part of Q4_K and Q5_K: d, dmin, packed scales and codes.
fn with_mins(x: &[f32], nmax: i32, rmin: f32, nstep: i32) -> ([u8; 4], [u8; 12], [u8; 256]) {
    let mut l = [0u8; 256];
    let (mut scales, mut mins) = ([0.0f32; 8], [0.0f32; 8]);
    let mut weights = [0.0f32; 32];
    let (mut max_scale, mut max_min) = (0.0f32, 0.0f32);
    for j in 0..8 {
        let g = &x[32 * j..][..32];
        let mut sum_x2 = 0.0f32;
        for &v in g {
            sum_x2 += v * v;
        }
        let av_x = (sum_x2 / 32.0).sqrt();
        for (w, &v) in weights.iter_mut().zip(g) {
            *w = av_x + v.abs();
        }
        (scales[j], mins[j]) = qkx2(g, &weights, nmax, &mut l[32 * j..][..32], rmin, 0.1, nstep);
        max_scale = max_scale.max(scales[j]);
        max_min = max_min.max(mins[j]);
    }
    let inv_scale = if max_scale > 0.0 {
        63.0 / max_scale
    } else {
        0.0
    };
    let inv_min = if max_min > 0.0 { 63.0 / max_min } else { 0.0 };
    let (mut ls, mut lm) = ([0u8; 8], [0u8; 8]);
    for j in 0..8 {
        ls[j] = (nearest_int(inv_scale * scales[j]) as u8).min(63);
        lm[j] = (nearest_int(inv_min * mins[j]) as u8).min(63);
    }
    let packed = pack_scales(&ls, &lm);
    let mut head = [0u8; 4];
    head[..2].copy_from_slice(&f16(max_scale / 63.0));
    head[2..].copy_from_slice(&f16(max_min / 63.0));
    let (d, dmin) = (
        f16_to_f32([head[0], head[1]]),
        f16_to_f32([head[2], head[3]]),
    );
    for j in 0..8 {
        let (sc, m) = scale_min(j, &packed);
        let d = d * sc as f32;
        if d == 0.0 {
            continue;
        }
        let dm = dmin * m as f32;
        for i in 0..32 {
            l[32 * j + i] = nearest_int((x[32 * j + i] + dm) / d).clamp(0, nmax) as u8;
        }
    }
    (head, packed, l)
}

pub fn q4_k(x: &[f32], out: &mut [u8]) {
    let (head, scales, l) = with_mins(x, 15, -1.0, 20);
    out[..4].copy_from_slice(&head);
    out[4..16].copy_from_slice(&scales);
    let qs = &mut out[16..144];
    for (c, chunk) in l.chunks(64).enumerate() {
        for i in 0..32 {
            qs[32 * c + i] = chunk[i] | (chunk[i + 32] << 4);
        }
    }
}

pub fn q5_k(x: &[f32], out: &mut [u8]) {
    let (head, scales, l) = with_mins(x, 31, -0.5, 15);
    out[..4].copy_from_slice(&head);
    out[4..16].copy_from_slice(&scales);
    let (qh, qs) = out[16..176].split_at_mut(32);
    qh.fill(0);
    for (c, chunk) in l.chunks(64).enumerate() {
        let (m1, m2) = (1u8 << (2 * c), 2u8 << (2 * c));
        for i in 0..32 {
            let (mut a, mut b) = (chunk[i], chunk[i + 32]);
            if a > 15 {
                a -= 16;
                qh[i] |= m1;
            }
            if b > 15 {
                b -= 16;
                qh[i] |= m2;
            }
            qs[32 * c + i] = a | (b << 4);
        }
    }
}

pub fn q6_k(x: &[f32], out: &mut [u8]) {
    let mut l = [0i8; 256];
    let mut scales = [0.0f32; 16];
    let (mut max_scale, mut max_abs) = (0.0f32, 0.0f32);
    for (ib, s) in scales.iter_mut().enumerate() {
        *s = qx(&x[16 * ib..][..16], 32, &mut l[16 * ib..][..16]);
        if s.abs() > max_abs {
            max_abs = s.abs();
            max_scale = *s;
        }
    }
    let out = &mut out[..210];
    if max_abs < GROUP_MAX_EPS {
        out.fill(0);
        return;
    }
    let iscale = -128.0 / max_scale;
    out[208..].copy_from_slice(&f16(1.0 / iscale));
    let d = f16_to_f32([out[208], out[209]]);
    for (ib, &s) in scales.iter().enumerate() {
        out[192 + ib] = nearest_int(iscale * s).min(127) as i8 as u8;
    }
    for j in 0..16 {
        let d = d * out[192 + j] as i8 as f32;
        if d == 0.0 {
            continue;
        }
        for i in 0..16 {
            l[16 * j + i] = (nearest_int(x[16 * j + i] / d).clamp(-32, 31) + 32) as i8;
        }
    }
    let (ql, rest) = out.split_at_mut(128);
    let qh = &mut rest[..64];
    for half in 0..2 {
        let l = &l[128 * half..][..128];
        let (ql, qh) = (&mut ql[64 * half..][..64], &mut qh[32 * half..][..32]);
        for i in 0..32 {
            let q = |k: usize| l[i + 32 * k] as u8;
            ql[i] = (q(0) & 0xF) | ((q(2) & 0xF) << 4);
            ql[i + 32] = (q(1) & 0xF) | ((q(3) & 0xF) << 4);
            qh[i] = (q(0) >> 4) | ((q(1) >> 4) << 2) | ((q(2) >> 4) << 4) | ((q(3) >> 4) << 6);
        }
    }
}
