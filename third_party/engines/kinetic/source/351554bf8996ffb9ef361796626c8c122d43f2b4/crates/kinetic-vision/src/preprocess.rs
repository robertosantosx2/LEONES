//! From encoded image files to the normalized pixels an encoder reads.

use image::imageops::{self, FilterType};
use image::RgbImage;

use crate::Error;

/// Decodes a PNG, JPEG, WebP, BMP or GIF file to 8-bit RGB.
pub fn decode(bytes: &[u8]) -> Result<RgbImage, Error> {
    image::load_from_memory(bytes)
        .map(|img| img.to_rgb8())
        .map_err(|e| Error(format!("cannot decode image: {e}")))
}

/// An image as planar f32 channels: all red values row by row, then green,
/// then blue.
pub struct Pixels {
    pub data: Vec<f32>,
    pub width: usize,
    pub height: usize,
}

impl Pixels {
    /// Scales `img` to `[0, 1]` and normalizes each channel with `mean` and
    /// `std`.
    pub fn normalized(img: &RgbImage, mean: [f32; 3], std: [f32; 3]) -> Pixels {
        let (width, height) = (img.width() as usize, img.height() as usize);
        let mut data = vec![0.0; 3 * width * height];
        for (i, p) in img.pixels().enumerate() {
            for c in 0..3 {
                data[c * width * height + i] = (p[c] as f32 / 255.0 - mean[c]) / std[c];
            }
        }
        Pixels {
            data,
            width,
            height,
        }
    }
}

/// The size an image of `width x height` is resized to: each side a multiple
/// of `factor`, the aspect ratio kept as closely as that allows, and the area
/// brought within `min_pixels..=max_pixels`. This is the "smart resize" of
/// the Qwen vision processors, which round halves to even as Python does;
/// with `half_even` false they round away from zero as llama.cpp does for
/// other models.
pub fn target_size(
    width: usize,
    height: usize,
    factor: usize,
    (min_pixels, max_pixels): (usize, usize),
    half_even: bool,
) -> (usize, usize) {
    let f = factor as f32;
    let round = |x: f32| {
        let q = x / f;
        let q = if half_even {
            q.round_ties_even()
        } else {
            q.round()
        };
        (q as usize * factor).max(factor)
    };
    let floor = |x: f32| ((x / f).floor() as usize * factor).max(factor);
    let ceil = |x: f32| (x / f).ceil() as usize * factor;
    let (w, h) = (width as f32, height as f32);
    let (rw, rh) = (round(w), round(h));
    if rw * rh > max_pixels {
        let beta = (w * h / max_pixels as f32).sqrt();
        (floor(w / beta), floor(h / beta))
    } else if rw * rh < min_pixels {
        let beta = (min_pixels as f32 / (w * h)).sqrt();
        (ceil(w * beta), ceil(h * beta))
    } else {
        (rw, rh)
    }
}

/// Resizes `img` to `width x height` with bicubic (Catmull-Rom)
/// filtering, unless it already has that size.
pub fn resize(img: &RgbImage, width: usize, height: usize) -> RgbImage {
    if (img.width() as usize, img.height() as usize) == (width, height) {
        return img.clone();
    }
    imageops::resize(img, width as u32, height as u32, FilterType::CatmullRom)
}

#[cfg(test)]
mod tests {
    use super::*;

    const MAX: usize = 4096 * 32 * 32;
    const MIN: usize = 8 * 32 * 32;

    #[test]
    fn sizes_round_to_the_factor() {
        assert_eq!(target_size(512, 512, 32, (MIN, MAX), true), (512, 512));
        assert_eq!(target_size(500, 300, 32, (MIN, MAX), true), (512, 288));
        // 304 / 32 = 9.5 rounds to the even 10, 336 / 32 = 10.5 to 10.
        assert_eq!(target_size(304, 336, 32, (MIN, MAX), true), (320, 320));
        assert_eq!(target_size(304, 336, 32, (MIN, MAX), false), (320, 352));
    }

    #[test]
    fn sizes_stay_within_the_pixel_limits() {
        let (w, h) = target_size(4000, 3000, 32, (MIN, MAX), true);
        assert!(w * h <= MAX && w.is_multiple_of(32) && h.is_multiple_of(32));
        assert_eq!((w, h), (2336, 1760));
        let (w, h) = target_size(40, 30, 32, (MIN, MAX), true);
        assert!(w * h >= MIN && w.is_multiple_of(32) && h.is_multiple_of(32));
    }

    #[test]
    fn normalization_is_planar() {
        let img = RgbImage::from_fn(2, 1, |x, _| image::Rgb([255, 0, x as u8 * 255]));
        let p = Pixels::normalized(&img, [0.5; 3], [0.5; 3]);
        assert_eq!(p.data, vec![1.0, 1.0, -1.0, -1.0, -1.0, 1.0]);
    }
}
