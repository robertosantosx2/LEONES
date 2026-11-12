use std::cell::RefCell;
use std::collections::HashSet;
use std::sync::Arc;

use kinetic_gguf::{Gguf, Value};

use crate::blocks::Folding;
use crate::LoadError;

/// The Hadamard folding a file declares under `prism.hadamard`, and which
/// of its weights carry it. Every declared weight must be claimed by a block
/// that applies the folding, so none is silently read in the wrong basis.
pub(crate) struct Folds {
    folding: Arc<Folding>,
    weights: HashSet<String>,
    tables: HashSet<String>,
    claimed: RefCell<HashSet<String>>,
}

impl Folds {
    pub fn read(h: &Gguf) -> Result<Option<Folds>, LoadError> {
        let key = |k: &str| h.get(&format!("prism.hadamard.{k}"));
        let Some(version) = key("version") else {
            return Ok(None);
        };
        let bad = |what: &str| LoadError(format!("prism.hadamard: {what}"));
        let text = |k: &str| key(k).and_then(Value::as_str).unwrap_or("");
        let ints = |k: &str| -> Result<Vec<i64>, LoadError> {
            key(k)
                .and_then(Value::as_array)
                .unwrap_or(&[])
                .iter()
                .map(|v| {
                    v.as_i64()
                        .ok_or_else(|| bad(&format!("{k} is not integers")))
                })
                .collect()
        };
        let names = |k: &str| -> HashSet<String> {
            key(k)
                .and_then(Value::as_array)
                .unwrap_or(&[])
                .iter()
                .filter_map(|v| v.as_str().map(str::to_owned))
                .collect()
        };
        // version 2 ties the output head to the folded embedding table
        if version.as_u64() != Some(1) {
            return Err(bad("only version 1 is supported"));
        }
        if text("transform") != "normalized-sylvester-walsh-hadamard"
            || text("axis") != "input-last-dimension"
            || text("sign_mode") != "explicit"
        {
            return Err(bad("unsupported transform, axis or sign mode"));
        }
        let block = key("block_size")
            .and_then(Value::as_u64)
            .map(|b| b as usize)
            .filter(|b| b.is_power_of_two())
            .ok_or_else(|| bad("block_size is not a power of two"))?;
        let values = ints("sign_values")?;
        let mut signs = Vec::new();
        let mut at = 0;
        for width in ints("sign_widths")? {
            let width = usize::try_from(width)
                .ok()
                .filter(|w| w.is_multiple_of(block))
                .ok_or_else(|| bad("a sign width is not a whole number of blocks"))?;
            let run = values
                .get(at..at + width)
                .ok_or_else(|| bad("sign_values is shorter than sign_widths"))?;
            if run.iter().any(|&s| s != 1 && s != -1) {
                return Err(bad("signs must be +1 or -1"));
            }
            signs.push(run.iter().map(|&s| s as f32).collect());
            at += width;
        }
        if at != values.len() {
            return Err(bad("sign_values is longer than sign_widths"));
        }
        let grouped = key("gdn_v_grouped").and_then(Value::as_bool) == Some(true);
        Ok(Some(Folds {
            folding: Arc::new(Folding::new(block, signs, grouped)),
            weights: names("weight_names"),
            tables: names("inverse_weight_names"),
            claimed: RefCell::default(),
        }))
    }

    /// The folding of a block whose weights `(name, input width)` are all
    /// folded, `None` when none is, and an error when only some are.
    pub fn block(&self, weights: &[(&str, usize)]) -> Result<Option<Arc<Folding>>, LoadError> {
        self.claim(&self.weights, weights)
    }

    /// The folding of a lookup table, undone after each lookup.
    pub fn table(&self, name: &str, width: usize) -> Result<Option<Arc<Folding>>, LoadError> {
        self.claim(&self.tables, &[(name, width)])
    }

    fn claim(
        &self,
        set: &HashSet<String>,
        weights: &[(&str, usize)],
    ) -> Result<Option<Arc<Folding>>, LoadError> {
        let folded = weights.iter().filter(|(n, _)| set.contains(*n)).count();
        if folded == 0 {
            return Ok(None);
        }
        if folded < weights.len() {
            return Err(LoadError(format!(
                "prism.hadamard folds only some of {:?}",
                weights.iter().map(|w| w.0).collect::<Vec<_>>()
            )));
        }
        if let Some((name, w)) = weights.iter().find(|(_, w)| !self.folding.has_width(*w)) {
            return Err(LoadError(format!(
                "prism.hadamard has no signs for {name}, {w} inputs wide"
            )));
        }
        let mut claimed = self.claimed.borrow_mut();
        claimed.extend(weights.iter().map(|(n, _)| n.to_string()));
        Ok(Some(self.folding.clone()))
    }

    /// Fails if a folded weight was left to a block that ignores folding.
    pub fn finish(&self) -> Result<(), LoadError> {
        let claimed = self.claimed.borrow();
        match self
            .weights
            .iter()
            .chain(&self.tables)
            .find(|n| !claimed.contains(*n))
        {
            Some(name) => Err(LoadError(format!(
                "{name} is stored folded, which this architecture does not support yet"
            ))),
            None => Ok(()),
        }
    }
}
