//! Typed access to the hyperparameters and tensors of a projector file.

use kinetic_gguf::{TensorInfo, TensorSource, Value};
use kinetic_quant::{dequantize, Matrix};

use crate::Error;

pub struct Loader<'a>(pub &'a dyn TensorSource);

impl<'a> Loader<'a> {
    pub fn value(&self, key: &str) -> Result<&'a Value, Error> {
        self.0
            .header()
            .get(key)
            .ok_or_else(|| Error(format!("missing hyperparameter {key}")))
    }

    pub fn usize(&self, key: &str) -> Result<usize, Error> {
        self.value(key)?
            .as_u64()
            .map(|v| v as usize)
            .ok_or_else(|| Error(format!("{key} is not an integer")))
    }

    pub fn f32(&self, key: &str) -> Result<f32, Error> {
        self.value(key)?
            .as_f32()
            .ok_or_else(|| Error(format!("{key} is not a float")))
    }

    pub fn rgb(&self, key: &str) -> Result<[f32; 3], Error> {
        let items = self.value(key)?.as_array().unwrap_or_default();
        match items.iter().map(Value::as_f32).collect::<Option<Vec<_>>>() {
            Some(v) if v.len() == 3 => Ok([v[0], v[1], v[2]]),
            _ => Err(Error(format!("{key} is not three floats"))),
        }
    }

    pub fn tensor(&self, name: &str) -> Result<&'a TensorInfo, Error> {
        self.0
            .header()
            .tensor(name)
            .ok_or_else(|| Error(format!("missing tensor {name}")))
    }

    pub fn matrix(&self, name: &str, cols: usize, rows: usize) -> Result<Matrix<'a>, Error> {
        let t = self.tensor(name)?;
        if t.dims != [cols as u64, rows as u64] {
            return Err(Error(format!(
                "{name} has shape {:?}, expected [{cols}, {rows}]",
                t.dims
            )));
        }
        Ok(Matrix::new(t.ty, self.0.tensor_data(t), rows, cols))
    }

    /// A convolution kernel of `rows` output channels read as a matrix whose
    /// row holds the kernel's channels, rows and columns in that order.
    pub fn patch_matrix(&self, name: &str, cols: usize, rows: usize) -> Result<Matrix<'a>, Error> {
        let t = self.tensor(name)?;
        if t.elements() != (cols * rows) as u64 || t.dims.last() != Some(&(rows as u64)) {
            return Err(Error(format!("{name} has shape {:?}", t.dims)));
        }
        Ok(Matrix::new(t.ty, self.0.tensor_data(t), rows, cols))
    }

    pub fn vector(&self, name: &str, len: usize) -> Result<Vec<f32>, Error> {
        let t = self.tensor(name)?;
        if t.elements() != len as u64 {
            return Err(Error(format!(
                "{name} has {} values, expected {len}",
                t.elements()
            )));
        }
        let mut out = vec![0.0; len];
        dequantize(t.ty, self.0.tensor_data(t), &mut out)
            .map_err(|e| Error(format!("{name}: {e}")))?;
        Ok(out)
    }
}
