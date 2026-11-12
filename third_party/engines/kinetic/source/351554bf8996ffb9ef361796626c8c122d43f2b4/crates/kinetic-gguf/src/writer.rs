//! Writing GGUF v3 files.

use std::io::{self, Write};

use crate::{align_up, TensorType, Value, DEFAULT_ALIGNMENT, MAGIC};

/// A tensor to write: its name, dimensions (innermost first) and type.
#[derive(Clone, Debug)]
pub struct TensorOut {
    pub name: String,
    pub dims: Vec<u64>,
    pub ty: TensorType,
}

impl TensorOut {
    /// Bytes of data the tensor takes.
    pub fn size(&self) -> u64 {
        self.ty
            .bytes_for(self.dims.iter().product())
            .expect("tensor size fits in u64")
    }
}

/// Writes a GGUF file with `metadata` and `tensors`; `data(i)` gives the
/// bytes of tensor `i`, which must be exactly [`TensorOut::size`] long. The
/// data is asked for in order, so tensors can be made one at a time.
pub fn write(
    out: &mut impl Write,
    metadata: &[(String, Value)],
    tensors: &[TensorOut],
    mut data: impl FnMut(usize) -> io::Result<Vec<u8>>,
) -> io::Result<()> {
    let alignment = metadata
        .iter()
        .find(|(k, _)| k == "general.alignment")
        .and_then(|(_, v)| v.as_u64())
        .unwrap_or(DEFAULT_ALIGNMENT);
    let mut head = Vec::new();
    head.extend_from_slice(MAGIC);
    head.extend_from_slice(&3u32.to_le_bytes());
    head.extend_from_slice(&(tensors.len() as u64).to_le_bytes());
    head.extend_from_slice(&(metadata.len() as u64).to_le_bytes());
    for (key, value) in metadata {
        put_str(&mut head, key);
        head.extend_from_slice(&type_id(value).to_le_bytes());
        put_value(&mut head, value);
    }
    let mut offset = 0u64;
    for t in tensors {
        put_str(&mut head, &t.name);
        head.extend_from_slice(&(t.dims.len() as u32).to_le_bytes());
        for d in &t.dims {
            head.extend_from_slice(&d.to_le_bytes());
        }
        head.extend_from_slice(&(t.ty as u32).to_le_bytes());
        head.extend_from_slice(&offset.to_le_bytes());
        offset = align_up(offset + t.size(), alignment);
    }
    head.resize(align_up(head.len() as u64, alignment) as usize, 0);
    out.write_all(&head)?;
    for (i, t) in tensors.iter().enumerate() {
        let bytes = data(i)?;
        if bytes.len() as u64 != t.size() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!(
                    "tensor {} has {} bytes, not {}",
                    t.name,
                    bytes.len(),
                    t.size()
                ),
            ));
        }
        out.write_all(&bytes)?;
        let pad = align_up(t.size(), alignment) - t.size();
        if i + 1 < tensors.len() {
            out.write_all(&vec![0; pad as usize])?;
        }
    }
    Ok(())
}

fn put_str(buf: &mut Vec<u8>, s: &str) {
    buf.extend_from_slice(&(s.len() as u64).to_le_bytes());
    buf.extend_from_slice(s.as_bytes());
}

fn type_id(v: &Value) -> u32 {
    match v {
        Value::U8(_) => 0,
        Value::I8(_) => 1,
        Value::U16(_) => 2,
        Value::I16(_) => 3,
        Value::U32(_) => 4,
        Value::I32(_) => 5,
        Value::F32(_) => 6,
        Value::Bool(_) => 7,
        Value::String(_) => 8,
        Value::Array(_) => 9,
        Value::U64(_) => 10,
        Value::I64(_) => 11,
        Value::F64(_) => 12,
    }
}

fn put_value(buf: &mut Vec<u8>, v: &Value) {
    match v {
        Value::U8(x) => buf.push(*x),
        Value::I8(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::U16(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::I16(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::U32(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::I32(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::F32(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::Bool(x) => buf.push(u8::from(*x)),
        Value::String(s) => put_str(buf, s),
        Value::U64(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::I64(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::F64(x) => buf.extend_from_slice(&x.to_le_bytes()),
        Value::Array(items) => {
            // an empty array keeps no element type; i32 is as good as any
            let elem = items.first().map_or(5, type_id);
            buf.extend_from_slice(&elem.to_le_bytes());
            buf.extend_from_slice(&(items.len() as u64).to_le_bytes());
            for item in items {
                put_value(buf, item);
            }
        }
    }
}
