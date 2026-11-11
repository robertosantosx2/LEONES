use crate::{Error, Value};

/// Arrays of arrays are legal but nothing real nests deeper than this, and
/// the cap keeps a hostile file from exhausting the stack.
const MAX_ARRAY_DEPTH: usize = 4;

pub(crate) struct Reader<'a> {
    buf: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    pub fn new(buf: &'a [u8]) -> Self {
        Reader { buf, pos: 0 }
    }

    pub fn pos(&self) -> usize {
        self.pos
    }

    fn remaining(&self) -> usize {
        self.buf.len() - self.pos
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8], Error> {
        if n > self.remaining() {
            return Err(Error::Truncated { offset: self.pos });
        }
        let bytes = &self.buf[self.pos..self.pos + n];
        self.pos += n;
        Ok(bytes)
    }

    fn array<const N: usize>(&mut self) -> Result<[u8; N], Error> {
        Ok(self.take(N)?.try_into().unwrap())
    }

    pub fn u8(&mut self) -> Result<u8, Error> {
        Ok(self.take(1)?[0])
    }

    pub fn u16(&mut self) -> Result<u16, Error> {
        self.array().map(u16::from_le_bytes)
    }

    pub fn u32(&mut self) -> Result<u32, Error> {
        self.array().map(u32::from_le_bytes)
    }

    pub fn u64(&mut self) -> Result<u64, Error> {
        self.array().map(u64::from_le_bytes)
    }

    /// Reads a count and rejects it if `count * min_item_bytes` cannot fit in
    /// the rest of the buffer, so a corrupt count never drives an allocation.
    pub fn count(&mut self, min_item_bytes: usize) -> Result<usize, Error> {
        let at = self.pos;
        let n = self.u64()?;
        let fits = usize::try_from(n)
            .ok()
            .filter(|&n| n.saturating_mul(min_item_bytes) <= self.remaining());
        fits.ok_or_else(|| Error::Invalid(format!("count {n} at offset {at} exceeds file size")))
    }

    pub fn string(&mut self) -> Result<String, Error> {
        let at = self.pos;
        let len = self.count(1)?;
        let bytes = self.take(len)?;
        String::from_utf8(bytes.to_vec())
            .map_err(|_| Error::Invalid(format!("string at offset {at} is not UTF-8")))
    }

    pub fn value(&mut self) -> Result<Value, Error> {
        let kind = self.u32()?;
        self.value_of(kind, 0)
    }

    fn value_of(&mut self, kind: u32, depth: usize) -> Result<Value, Error> {
        Ok(match kind {
            0 => Value::U8(self.u8()?),
            1 => Value::I8(self.u8()? as i8),
            2 => Value::U16(self.u16()?),
            3 => Value::I16(self.u16()? as i16),
            4 => Value::U32(self.u32()?),
            5 => Value::I32(self.u32()? as i32),
            6 => Value::F32(f32::from_bits(self.u32()?)),
            7 => match self.u8()? {
                0 => Value::Bool(false),
                1 => Value::Bool(true),
                b => return Err(Error::Invalid(format!("bool value {b}"))),
            },
            8 => Value::String(self.string()?),
            9 => {
                if depth == MAX_ARRAY_DEPTH {
                    return Err(Error::Invalid("arrays nested too deeply".into()));
                }
                let item_kind = self.u32()?;
                let n = self.count(min_value_bytes(item_kind))?;
                let mut items = Vec::with_capacity(n);
                for _ in 0..n {
                    items.push(self.value_of(item_kind, depth + 1)?);
                }
                Value::Array(items)
            }
            10 => Value::U64(self.u64()?),
            11 => Value::I64(self.u64()? as i64),
            12 => Value::F64(f64::from_bits(self.u64()?)),
            k => return Err(Error::Invalid(format!("unknown metadata type {k}"))),
        })
    }
}

fn min_value_bytes(kind: u32) -> usize {
    match kind {
        0 | 1 | 7 => 1,
        2 | 3 => 2,
        4..=6 => 4,
        9 => 12,
        _ => 8,
    }
}
