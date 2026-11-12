//! A fast hasher for the small integer keys of the automaton's tables.

use std::collections::{HashMap, HashSet};
use std::hash::{BuildHasherDefault, Hasher};

/// Multiply-rotate hashing; keys are internal ids, so flooding resistance
/// is not needed.
#[derive(Default, Clone, Copy)]
pub(crate) struct FastHasher(u64);

const K: u64 = 0x517c_c1b7_2722_0a95;

impl FastHasher {
    #[inline]
    fn add(&mut self, v: u64) {
        self.0 = (self.0.rotate_left(5) ^ v).wrapping_mul(K);
    }
}

impl Hasher for FastHasher {
    fn write(&mut self, bytes: &[u8]) {
        let mut chunks = bytes.chunks_exact(8);
        for chunk in &mut chunks {
            self.add(u64::from_le_bytes(chunk.try_into().expect("8 bytes")));
        }
        for &b in chunks.remainder() {
            self.add(u64::from(b));
        }
    }

    #[inline]
    fn write_u32(&mut self, n: u32) {
        self.add(u64::from(n));
    }

    #[inline]
    fn write_u64(&mut self, n: u64) {
        self.add(n);
    }

    #[inline]
    fn write_usize(&mut self, n: usize) {
        self.add(n as u64);
    }

    #[inline]
    fn finish(&self) -> u64 {
        self.0
    }
}

pub(crate) type FastMap<K, V> = HashMap<K, V, BuildHasherDefault<FastHasher>>;

pub(crate) type FastSet<T> = HashSet<T, BuildHasherDefault<FastHasher>>;
