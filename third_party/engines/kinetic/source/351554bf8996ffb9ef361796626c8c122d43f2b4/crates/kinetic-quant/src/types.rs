use std::fmt;

/// Tensor storage types defined by the GGUF format.
///
/// Discriminants match the on-disk type ids. Ids that were removed from the
/// format (4, 5, 31-33, 36-38) are rejected when reading.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[repr(u32)]
pub enum TensorType {
    F32 = 0,
    F16 = 1,
    Q4_0 = 2,
    Q4_1 = 3,
    Q5_0 = 6,
    Q5_1 = 7,
    Q8_0 = 8,
    Q8_1 = 9,
    Q2K = 10,
    Q3K = 11,
    Q4K = 12,
    Q5K = 13,
    Q6K = 14,
    Q8K = 15,
    IQ2XXS = 16,
    IQ2XS = 17,
    IQ3XXS = 18,
    IQ1S = 19,
    IQ4NL = 20,
    IQ3S = 21,
    IQ2S = 22,
    IQ4XS = 23,
    I8 = 24,
    I16 = 25,
    I32 = 26,
    I64 = 27,
    F64 = 28,
    IQ1M = 29,
    BF16 = 30,
    TQ1_0 = 34,
    TQ2_0 = 35,
    MXFP4 = 39,
    Q1_0 = 41,
    Q2_0 = 42,
    /// PrismML's Q2_0 with one scale per 128 values.
    PQ2_0 = 142,
    /// PrismML's TQ1_0 packing with one scale per 128 values.
    PTQ1_0 = 143,
}

impl TensorType {
    pub fn from_id(id: u32) -> Option<Self> {
        use TensorType::*;
        Some(match id {
            0 => F32,
            1 => F16,
            2 => Q4_0,
            3 => Q4_1,
            6 => Q5_0,
            7 => Q5_1,
            8 => Q8_0,
            9 => Q8_1,
            10 => Q2K,
            11 => Q3K,
            12 => Q4K,
            13 => Q5K,
            14 => Q6K,
            15 => Q8K,
            16 => IQ2XXS,
            17 => IQ2XS,
            18 => IQ3XXS,
            19 => IQ1S,
            20 => IQ4NL,
            21 => IQ3S,
            22 => IQ2S,
            23 => IQ4XS,
            24 => I8,
            25 => I16,
            26 => I32,
            27 => I64,
            28 => F64,
            29 => IQ1M,
            30 => BF16,
            34 => TQ1_0,
            35 => TQ2_0,
            39 => MXFP4,
            41 => Q1_0,
            42 => Q2_0,
            142 => PQ2_0,
            143 => PTQ1_0,
            _ => return None,
        })
    }

    /// Number of elements stored in one block.
    pub fn block_len(self) -> usize {
        use TensorType::*;
        match self {
            F32 | F16 | BF16 | F64 | I8 | I16 | I32 | I64 => 1,
            Q4_0 | Q4_1 | Q5_0 | Q5_1 | Q8_0 | Q8_1 | IQ4NL | MXFP4 => 32,
            Q2_0 => 64,
            Q1_0 | PQ2_0 | PTQ1_0 => 128,
            _ => 256,
        }
    }

    /// Size of one block in bytes.
    pub fn block_bytes(self) -> usize {
        use TensorType::*;
        match self {
            I8 => 1,
            F16 | BF16 | I16 => 2,
            F32 | I32 => 4,
            F64 | I64 => 8,
            Q4_0 => 18,
            Q4_1 => 20,
            Q5_0 => 22,
            Q5_1 => 24,
            Q8_0 => 34,
            Q8_1 => 36,
            IQ4NL => 18,
            MXFP4 => 17,
            Q2K => 84,
            Q3K => 110,
            Q4K => 144,
            Q5K => 176,
            Q6K => 210,
            Q8K => 292,
            IQ2XXS => 66,
            IQ2XS => 74,
            IQ2S => 82,
            IQ3XXS => 98,
            IQ3S => 110,
            IQ1S => 50,
            IQ1M => 56,
            IQ4XS => 136,
            TQ1_0 => 54,
            TQ2_0 => 66,
            Q1_0 | Q2_0 => 18,
            PQ2_0 => 34,
            PTQ1_0 => 28,
        }
    }

    /// Bytes needed for `elements` values, or `None` if the count is not a
    /// whole number of blocks or the size overflows.
    pub fn bytes_for(self, elements: u64) -> Option<u64> {
        let block = self.block_len() as u64;
        if !elements.is_multiple_of(block) {
            return None;
        }
        (elements / block).checked_mul(self.block_bytes() as u64)
    }

    pub fn name(self) -> &'static str {
        use TensorType::*;
        match self {
            F32 => "F32",
            F16 => "F16",
            BF16 => "BF16",
            F64 => "F64",
            I8 => "I8",
            I16 => "I16",
            I32 => "I32",
            I64 => "I64",
            Q4_0 => "Q4_0",
            Q4_1 => "Q4_1",
            Q5_0 => "Q5_0",
            Q5_1 => "Q5_1",
            Q8_0 => "Q8_0",
            Q8_1 => "Q8_1",
            Q2K => "Q2_K",
            Q3K => "Q3_K",
            Q4K => "Q4_K",
            Q5K => "Q5_K",
            Q6K => "Q6_K",
            Q8K => "Q8_K",
            IQ2XXS => "IQ2_XXS",
            IQ2XS => "IQ2_XS",
            IQ2S => "IQ2_S",
            IQ3XXS => "IQ3_XXS",
            IQ3S => "IQ3_S",
            IQ1S => "IQ1_S",
            IQ1M => "IQ1_M",
            IQ4NL => "IQ4_NL",
            IQ4XS => "IQ4_XS",
            TQ1_0 => "TQ1_0",
            TQ2_0 => "TQ2_0",
            MXFP4 => "MXFP4",
            Q1_0 => "Q1_0",
            Q2_0 => "Q2_0",
            PQ2_0 => "PQ2_0",
            PTQ1_0 => "PTQ1_0",
        }
    }
}

impl fmt::Display for TensorType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.name())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_round_trip() {
        for id in 0..256 {
            if let Some(t) = TensorType::from_id(id) {
                assert_eq!(t as u32, id);
            }
        }
        assert_eq!(TensorType::from_id(4), None);
        assert_eq!(TensorType::from_id(31), None);
    }

    #[test]
    fn k_quant_sizes() {
        assert_eq!(TensorType::Q4K.bytes_for(4096), Some(16 * 144));
        assert_eq!(TensorType::Q6K.bytes_for(256), Some(210));
        assert_eq!(TensorType::Q8_0.bytes_for(33), None);
    }

    // 2.125 bpw is what the Ternary-Bonsai 9B files show per tensor
    #[test]
    fn prism_sizes() {
        assert_eq!(TensorType::PQ2_0.bytes_for(4096), Some(32 * 34));
        assert_eq!(TensorType::PTQ1_0.bytes_for(128), Some(28));
        assert_eq!(TensorType::Q1_0.bytes_for(128), Some(18));
        assert_eq!(TensorType::Q2_0.bytes_for(128), Some(36));
    }
}
