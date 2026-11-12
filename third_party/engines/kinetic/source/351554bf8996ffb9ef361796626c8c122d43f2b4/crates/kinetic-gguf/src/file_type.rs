//! The quantization a file declares, as llama.cpp names it.

use std::collections::HashMap;

use crate::Gguf;

impl Gguf {
    /// The quantization as llama.cpp names the file type, such as `Q4_K_M`,
    /// or the type of most of the weights when the file names none.
    pub fn quantization(&self) -> String {
        self.get("general.file_type")
            .and_then(|v| v.as_u64())
            .and_then(file_type_name)
            .map_or_else(|| self.dominant_type(), str::to_owned)
    }

    fn dominant_type(&self) -> String {
        let mut bytes: HashMap<&str, u64> = HashMap::new();
        for t in &self.tensors {
            *bytes.entry(t.ty.name()).or_default() += t.size;
        }
        bytes
            .into_iter()
            .max_by_key(|&(name, b)| (b, name))
            .map_or_else(|| "unknown".into(), |(name, _)| name.to_owned())
    }
}

/// llama.cpp's names for `general.file_type`, see `llama_ftype` in llama.h.
fn file_type_name(id: u64) -> Option<&'static str> {
    Some(match id {
        0 => "F32",
        1 => "F16",
        2 => "Q4_0",
        3 => "Q4_1",
        7 => "Q8_0",
        8 => "Q5_0",
        9 => "Q5_1",
        10 => "Q2_K",
        11 => "Q3_K_S",
        12 => "Q3_K_M",
        13 => "Q3_K_L",
        14 => "Q4_K_S",
        15 => "Q4_K_M",
        16 => "Q5_K_S",
        17 => "Q5_K_M",
        18 => "Q6_K",
        19 => "IQ2_XXS",
        20 => "IQ2_XS",
        21 => "Q2_K_S",
        22 => "IQ3_XS",
        23 => "IQ3_XXS",
        24 => "IQ1_S",
        25 => "IQ4_NL",
        26 => "IQ3_S",
        27 => "IQ3_M",
        28 => "IQ2_S",
        29 => "IQ2_M",
        30 => "IQ4_XS",
        31 => "IQ1_M",
        32 => "BF16",
        36 => "TQ1_0",
        37 => "TQ2_0",
        38 => "MXFP4",
        _ => return None,
    })
}
