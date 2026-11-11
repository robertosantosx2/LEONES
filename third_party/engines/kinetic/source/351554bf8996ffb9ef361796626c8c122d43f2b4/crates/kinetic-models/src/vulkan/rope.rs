use kinetic_vulkan::Batch;

use crate::blocks::Rope;
use crate::LoadError;

/// The rotary angles of each distinct rotary embedding of a model, which
/// the host computes for every pass exactly as the CPU path does and
/// writes to the batch tables.
pub(super) struct RopeTables {
    ropes: Vec<(Rope, usize)>,
    rows: usize,
    words: usize,
}

impl RopeTables {
    /// Tables for passes of up to `rows` tokens.
    pub fn new(rows: usize) -> RopeTables {
        RopeTables {
            ropes: Vec::new(),
            rows,
            words: 0,
        }
    }

    /// The table word where the angles of `rope` start; a rope equal to an
    /// earlier one shares its table.
    pub fn table(&mut self, rope: &Rope) -> Result<usize, LoadError> {
        if rope.dims == 0 || !rope.dims.is_multiple_of(2) {
            return Err(LoadError(format!(
                "rotary embedding of {} values",
                rope.dims
            )));
        }
        let same = |r: &Rope| {
            r.dims == rope.dims
                && r.base.to_bits() == rope.base.to_bits()
                && r.layout == rope.layout
                && r.factors == rope.factors
                && r.mscale.to_bits() == rope.mscale.to_bits()
        };
        if let Some((_, at)) = self.ropes.iter().find(|(r, _)| same(r)) {
            return Ok(*at);
        }
        let at = self.words;
        self.words += self.rows * rope.dims;
        let copy = Rope {
            dims: rope.dims,
            base: rope.base,
            factors: rope.factors.clone(),
            layout: rope.layout,
            mscale: rope.mscale,
        };
        self.ropes.push((copy, at));
        Ok(at)
    }

    /// Words all tables take.
    pub fn words(&self) -> usize {
        self.words
    }

    /// Writes the angles of `n` tokens from position `pos`: for token `t`,
    /// the cosine and sine of pair `i` at words `2i` and `2i + 1` of row
    /// `t` of each table.
    pub fn fill(&self, batch: &mut Batch, pos: usize, n: usize) {
        let words = batch.tables_mut();
        for (rope, at) in &self.ropes {
            for t in 0..n {
                let row = &mut words[at + t * rope.dims..][..rope.dims];
                for (pair, (sin, cos)) in row.chunks_exact_mut(2).zip(rope.angles(pos + t)) {
                    pair.copy_from_slice(&[cos.to_bits(), sin.to_bits()]);
                }
            }
        }
    }
}
