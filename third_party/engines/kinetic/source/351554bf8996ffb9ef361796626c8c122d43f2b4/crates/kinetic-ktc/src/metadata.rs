//! Typed metadata values in JSON: `{"type": "u32", "value": 7}`.

use std::collections::HashSet;
use std::fmt;

use kinetic_gguf::Value;
use serde::de::{self, MapAccess, Visitor};
use serde::ser::{self, SerializeMap};
use serde::{Deserializer, Serializer};
use serde_json::{json, Number, Value as Json};

/// Key-value pairs in the order they were written.
pub type Metadata = Vec<(String, Value)>;

/// Arrays nest no deeper than this, the same cap GGUF readers use.
const MAX_ARRAY_DEPTH: usize = 4;

/// Encodes one value with its type.
pub(crate) fn to_json(value: &Value) -> Result<Json, String> {
    Ok(json!({ "type": type_name(value)?, "value": plain(value)? }))
}

/// Decodes one `{"type", "value"}` object.
pub(crate) fn from_json(typed: &Json) -> Result<Value, String> {
    let fields = typed
        .as_object()
        .filter(|o| o.len() == 2)
        .ok_or("expected an object with \"type\" and \"value\"")?;
    let ty = fields
        .get("type")
        .and_then(Json::as_str)
        .ok_or("\"type\" must be a string")?;
    let value = fields.get("value").ok_or("missing \"value\"")?;
    parse(ty, value, 0)
}

pub(crate) fn type_name(value: &Value) -> Result<String, String> {
    Ok(match value {
        Value::U8(_) => "u8".into(),
        Value::I8(_) => "i8".into(),
        Value::U16(_) => "u16".into(),
        Value::I16(_) => "i16".into(),
        Value::U32(_) => "u32".into(),
        Value::I32(_) => "i32".into(),
        Value::U64(_) => "u64".into(),
        Value::I64(_) => "i64".into(),
        Value::F32(_) => "f32".into(),
        Value::F64(_) => "f64".into(),
        Value::Bool(_) => "bool".into(),
        Value::String(_) => "string".into(),
        Value::Array(items) => {
            // An empty array keeps no item type; any type reads back the same.
            let item = items.first().map_or(Ok("u8".into()), type_name)?;
            for other in items.iter().skip(1) {
                if type_name(other)? != item {
                    return Err("array items differ in type".into());
                }
            }
            format!("[{item}]")
        }
    })
}

fn plain(value: &Value) -> Result<Json, String> {
    let float = |v: f64| {
        Number::from_f64(v)
            .map(Json::Number)
            .ok_or_else(|| format!("float {v} is not finite"))
    };
    Ok(match value {
        Value::U8(v) => (*v).into(),
        Value::I8(v) => (*v).into(),
        Value::U16(v) => (*v).into(),
        Value::I16(v) => (*v).into(),
        Value::U32(v) => (*v).into(),
        Value::I32(v) => (*v).into(),
        Value::U64(v) => (*v).into(),
        Value::I64(v) => (*v).into(),
        Value::F32(v) => float(f64::from(*v))?,
        Value::F64(v) => float(*v)?,
        Value::Bool(v) => (*v).into(),
        Value::String(v) => v.as_str().into(),
        Value::Array(items) => Json::Array(items.iter().map(plain).collect::<Result<_, _>>()?),
    })
}

fn parse(ty: &str, v: &Json, depth: usize) -> Result<Value, String> {
    if let Some(item) = ty.strip_prefix('[').and_then(|t| t.strip_suffix(']')) {
        if depth == MAX_ARRAY_DEPTH {
            return Err("arrays nested too deeply".into());
        }
        let items = v.as_array().ok_or_else(|| format!("{ty} needs an array"))?;
        return items
            .iter()
            .map(|i| parse(item, i, depth + 1))
            .collect::<Result<_, _>>()
            .map(Value::Array);
    }
    let wrong = || format!("value {v} is not a valid {ty}");
    let unsigned = || v.as_u64().ok_or_else(wrong);
    let signed = || v.as_i64().ok_or_else(wrong);
    let fits = |r: Result<Value, std::num::TryFromIntError>| r.map_err(|_| wrong());
    match ty {
        "u8" => fits(u8::try_from(unsigned()?).map(Value::U8)),
        "u16" => fits(u16::try_from(unsigned()?).map(Value::U16)),
        "u32" => fits(u32::try_from(unsigned()?).map(Value::U32)),
        "u64" => Ok(Value::U64(unsigned()?)),
        "i8" => fits(i8::try_from(signed()?).map(Value::I8)),
        "i16" => fits(i16::try_from(signed()?).map(Value::I16)),
        "i32" => fits(i32::try_from(signed()?).map(Value::I32)),
        "i64" => Ok(Value::I64(signed()?)),
        "f32" => v.as_f64().map(|f| Value::F32(f as f32)).ok_or_else(wrong),
        "f64" => v.as_f64().map(Value::F64).ok_or_else(wrong),
        "bool" => v.as_bool().map(Value::Bool).ok_or_else(wrong),
        "string" => v
            .as_str()
            .map(|s| Value::String(s.into()))
            .ok_or_else(wrong),
        _ => Err(format!("unknown type {ty:?}")),
    }
}

/// `#[serde(with = "metadata")]` for a [`Metadata`] field stored as a JSON object.
pub(crate) fn serialize<S: Serializer>(m: &Metadata, s: S) -> Result<S::Ok, S::Error> {
    let mut seen = HashSet::new();
    let mut map = s.serialize_map(Some(m.len()))?;
    for (key, value) in m {
        if !seen.insert(key) {
            return Err(ser::Error::custom(format!("duplicate key {key}")));
        }
        let typed = to_json(value).map_err(|e| ser::Error::custom(format!("{key}: {e}")))?;
        map.serialize_entry(key, &typed)?;
    }
    map.end()
}

pub(crate) fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Metadata, D::Error> {
    d.deserialize_map(MetadataVisitor)
}

struct MetadataVisitor;

impl<'de> Visitor<'de> for MetadataVisitor {
    type Value = Metadata;

    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.write_str("an object of typed values")
    }

    fn visit_map<A: MapAccess<'de>>(self, mut access: A) -> Result<Metadata, A::Error> {
        let mut seen = HashSet::new();
        let mut out = Vec::new();
        while let Some((key, typed)) = access.next_entry::<String, Json>()? {
            let value = from_json(&typed).map_err(|e| de::Error::custom(format!("{key}: {e}")))?;
            if !seen.insert(key.clone()) {
                return Err(de::Error::custom(format!("duplicate key {key}")));
            }
            out.push((key, value));
        }
        Ok(out)
    }
}
