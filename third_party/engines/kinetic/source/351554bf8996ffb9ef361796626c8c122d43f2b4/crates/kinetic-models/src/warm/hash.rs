//! A small 64-bit hash for cache keys and file checksums. It only has to
//! tell prompts apart and catch damaged files, not resist an attacker.

const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
const PRIME: u64 = 0x0000_0100_0000_01b3;

/// FNV-1a over whole words, then a final mix: the same value on every
/// platform and release, unlike the standard library's hashers.
#[derive(Clone, Copy)]
pub struct Hasher(u64);

impl Default for Hasher {
    fn default() -> Self {
        Hasher(OFFSET)
    }
}

impl Hasher {
    pub fn word(&mut self, w: u64) {
        self.0 = (self.0 ^ w).wrapping_mul(PRIME);
    }

    pub fn bytes(&mut self, bytes: &[u8]) {
        for chunk in bytes.chunks(8) {
            let mut w = [0; 8];
            w[..chunk.len()].copy_from_slice(chunk);
            self.word(u64::from_le_bytes(w));
        }
        self.word(bytes.len() as u64);
    }

    pub fn finish(self) -> u64 {
        let mut h = self.0;
        h ^= h >> 33;
        h = h.wrapping_mul(0xff51_afd7_ed55_8ccd);
        h ^ (h >> 33)
    }
}

#[cfg(test)]
mod tests {
    use super::Hasher;

    #[test]
    fn values_are_stable_and_order_matters() {
        let hash = |words: &[u64]| {
            let mut h = Hasher::default();
            words.iter().for_each(|&w| h.word(w));
            h.finish()
        };
        assert_eq!(hash(&[1, 2, 3]), 0xecef_e578_94f7_3f07);
        assert_ne!(hash(&[1, 2, 3]), hash(&[3, 2, 1]));
        assert_ne!(hash(&[]), hash(&[0]));
    }
}
