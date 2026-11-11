//! Converts JSON Schema to GBNF.

mod range;
mod regex;

use std::collections::{HashMap, HashSet};

use serde_json::{Map, Value};

use crate::Error;

/// Shared rules: name, body and the rules the body uses.
const PRIMITIVES: &[(&str, &str, &[&str])] = &[
    (
        "value",
        "object | array | string | number | boolean | null",
        &["object", "array", "string", "number", "boolean", "null"],
    ),
    (
        "object",
        r#""{" space (string ":" space value ("," space string ":" space value)*)? "}" space"#,
        &["string", "value", "space"],
    ),
    (
        "array",
        r#""[" space (value ("," space value)*)? "]" space"#,
        &["value", "space"],
    ),
    ("string", r#""\"" char* "\"" space"#, &["char", "space"]),
    (
        "number",
        r#""-"? integral ("." [0-9]{1,16})? ([eE] [-+]? [0-9]{1,16})? space"#,
        &["integral", "space"],
    ),
    ("integer", r#""-"? integral space"#, &["integral", "space"]),
    ("boolean", r#"("true" | "false") space"#, &["space"]),
    ("null", r#""null" space"#, &["space"]),
    ("integral", r#""0" | [1-9] [0-9]{0,15}"#, &[]),
    (
        "char",
        r#"[^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4})"#,
        &[],
    ),
    (
        "date",
        r#"[0-9]{4} "-" ("0" [1-9] | "1" [0-2]) "-" ("0" [1-9] | [12] [0-9] | "3" [01])"#,
        &[],
    ),
    (
        "time",
        r#"([01] [0-9] | "2" [0-3]) ":" [0-5] [0-9] ":" [0-5] [0-9] ("." [0-9]{1,9})? ("Z" | [+-] ([01] [0-9] | "2" [0-3]) ":" [0-5] [0-9])"#,
        &[],
    ),
    ("date-time", r#"date "T" time"#, &["date", "time"]),
    (
        "uuid",
        r#"[0-9a-fA-F]{8} "-" [0-9a-fA-F]{4} "-" [0-9a-fA-F]{4} "-" [0-9a-fA-F]{4} "-" [0-9a-fA-F]{12}"#,
        &[],
    ),
    ("space", r#"| " " | "\n" [ \t]{0,20}"#, &[]),
];

/// Keywords that only describe, so they are skipped.
const ANNOTATIONS: &[&str] = &[
    "$schema",
    "$id",
    "$comment",
    "$defs",
    "definitions",
    "title",
    "description",
    "default",
    "examples",
    "deprecated",
    "readOnly",
    "writeOnly",
    "contentEncoding",
    "contentMediaType",
];

const KEYWORDS: &[&str] = &[
    "type",
    "$ref",
    "const",
    "enum",
    "anyOf",
    "oneOf",
    "allOf",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "pattern",
    "format",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
];

/// Whole parts up to this many digits, as the shared number rules allow.
const MAX_INTEGER: i64 = 9_999_999_999_999_999;

pub(crate) fn to_gbnf(schema: &Value) -> Result<String, Error> {
    let mut c = Converter {
        root: schema,
        rules: Vec::new(),
        taken: PRIMITIVES
            .iter()
            .map(|p| p.0.to_owned())
            .chain(["root".to_owned()])
            .collect(),
        used: HashSet::new(),
        refs: HashMap::from([("#".to_owned(), "root".to_owned())]),
    };
    let root = c.expr(schema, "root")?;
    let mut out = format!("root ::= {root}\n");
    for (name, body) in &c.rules {
        out += &format!("{name} ::= {body}\n");
    }
    for (name, body, _) in PRIMITIVES {
        if c.used.contains(name) {
            out += &format!("{name} ::= {body}\n");
        }
    }
    Ok(out)
}

struct Converter<'s> {
    root: &'s Value,
    rules: Vec<(String, String)>,
    taken: HashSet<String>,
    used: HashSet<&'static str>,
    /// The rule made for each `$ref` target.
    refs: HashMap<String, String>,
}

impl<'s> Converter<'s> {
    /// A GBNF expression for `schema`; `name` prefixes the rules it adds.
    fn expr(&mut self, schema: &'s Value, name: &str) -> Result<String, Error> {
        let map = match schema {
            Value::Bool(true) => return Ok(self.primitive("value")),
            Value::Bool(false) => {
                return Err(Error::Schema("the schema false matches nothing".into()))
            }
            Value::Object(map) => map,
            _ => return Err(Error::Schema(format!("{schema} is not a schema"))),
        };
        if let Some(key) = map
            .keys()
            .find(|k| !KEYWORDS.contains(&k.as_str()) && !ANNOTATIONS.contains(&k.as_str()))
        {
            return Err(Error::Schema(format!(
                "the keyword {key:?} is not supported"
            )));
        }
        if let Some(r) = map.get("$ref") {
            let r = r
                .as_str()
                .ok_or_else(|| Error::Schema("$ref must be a string".into()))?;
            return self.reference(r);
        }
        if let Some(value) = map.get("const") {
            return Ok(self.json_value(value));
        }
        if let Some(values) = map.get("enum") {
            let values = values.as_array().filter(|v| !v.is_empty());
            let values =
                values.ok_or_else(|| Error::Schema("enum must be a non-empty array".into()))?;
            let alts: Vec<String> = values.iter().map(|v| self.json_value(v)).collect();
            return Ok(group(alts));
        }
        for key in ["anyOf", "oneOf", "allOf"] {
            let Some(subs) = map.get(key) else { continue };
            let subs = subs.as_array().filter(|s| !s.is_empty());
            let subs =
                subs.ok_or_else(|| Error::Schema(format!("{key} must be a non-empty array")))?;
            if key == "allOf" && subs.len() > 1 {
                return Err(Error::Schema(
                    "allOf with more than one schema is not supported".into(),
                ));
            }
            let alts = subs
                .iter()
                .enumerate()
                .map(|(i, sub)| self.rule(sub, &format!("{name}-{i}")))
                .collect::<Result<Vec<_>, _>>()?;
            return Ok(group(alts));
        }

        let types: Vec<&str> = match map.get("type") {
            None => vec![infer_type(map)],
            Some(Value::String(t)) => vec![t],
            Some(Value::Array(ts)) => ts
                .iter()
                .map(|t| {
                    t.as_str()
                        .ok_or_else(|| Error::Schema("type lists hold strings".into()))
                })
                .collect::<Result<_, _>>()?,
            Some(t) => return Err(Error::Schema(format!("type {t} is not a string"))),
        };
        let alts = types
            .into_iter()
            .map(|t| self.typed(map, t, name))
            .collect::<Result<Vec<_>, _>>()?;
        Ok(group(alts))
    }

    fn typed(
        &mut self,
        map: &'s Map<String, Value>,
        ty: &str,
        name: &str,
    ) -> Result<String, Error> {
        match ty {
            "object" => self.object(map, name),
            "array" => self.array(map, name),
            "string" => self.string(map),
            "integer" => self.integer(map),
            "number" => self.number(map),
            "boolean" | "null" => Ok(self.primitive(if ty == "null" { "null" } else { "boolean" })),
            "any" => Ok(self.primitive("value")),
            _ => Err(Error::Schema(format!("unknown type {ty:?}"))),
        }
    }

    fn object(&mut self, map: &'s Map<String, Value>, name: &str) -> Result<String, Error> {
        let props = match map.get("properties") {
            None => None,
            Some(Value::Object(p)) => Some(p),
            Some(_) => return Err(Error::Schema("properties must be an object".into())),
        };
        let required: Vec<&str> = match map.get("required") {
            None => Vec::new(),
            Some(Value::Array(r)) => r
                .iter()
                .map(|k| {
                    k.as_str()
                        .ok_or_else(|| Error::Schema("required lists strings".into()))
                })
                .collect::<Result<_, _>>()?,
            Some(_) => return Err(Error::Schema("required must be an array".into())),
        };
        let additional = match map.get("additionalProperties") {
            None if props.is_none_or(Map::is_empty) => Some(self.primitive("value")),
            None | Some(Value::Bool(false)) => None,
            Some(Value::Bool(true)) => Some(self.primitive("value")),
            Some(schema) => Some(self.rule(schema, &format!("{name}-additional"))?),
        };

        let mut entries = Vec::new();
        for (key, sub) in props.into_iter().flatten() {
            let value = self.rule(sub, &format!("{name}-{key}"))?;
            entries.push((
                self.key_value(key, &value),
                required.contains(&key.as_str()),
            ));
        }
        for key in required
            .iter()
            .filter(|k| !props.is_some_and(|p| p.contains_key(**k)))
        {
            let value = self.primitive("value");
            entries.push((self.key_value(key, &value), true));
        }
        let space = self.primitive("space");
        if additional.is_none() && entries.iter().all(|e| e.1) {
            let kvs: Vec<&str> = entries.iter().map(|e| e.0.as_str()).collect();
            let sep = format!(" \",\" {space} ");
            let body = if kvs.is_empty() {
                String::new()
            } else {
                format!("{} ", kvs.join(&sep))
            };
            return Ok(format!("\"{{\" {space} {body}\"}}\" {space}"));
        }

        // head(i): properties i.. with none written yet; tail(i): after one.
        let n = entries.len();
        let heads: Vec<String> = (0..=n)
            .map(|i| self.fresh(&format!("{name}-head-{i}")))
            .collect();
        let tails: Vec<String> = (0..=n)
            .map(|i| self.fresh(&format!("{name}-tail-{i}")))
            .collect();
        let extra = additional.map(|v| {
            let key = self.primitive("string");
            format!("{key} \":\" {space} {v}")
        });
        let (head_n, tail_n) = match &extra {
            Some(kv) => (
                format!("({kv} {})?", tails[n]),
                format!("(\",\" {space} {kv})*"),
            ),
            None => ("\"\"".to_owned(), "\"\"".to_owned()),
        };
        self.rules.push((heads[n].clone(), head_n));
        self.rules.push((tails[n].clone(), tail_n));
        for (i, (kv, req)) in entries.iter().enumerate().rev() {
            let next = (&heads[i + 1], &tails[i + 1]);
            let tail = format!("\",\" {space} {kv} {}", next.1);
            let head = format!("{kv} {}", next.1);
            let (head, tail) = if *req {
                (head, tail)
            } else {
                (
                    format!("{head} | {}", next.0),
                    format!("{tail} | {}", next.1),
                )
            };
            self.rules.push((heads[i].clone(), head));
            self.rules.push((tails[i].clone(), tail));
        }
        Ok(format!("\"{{\" {space} {} \"}}\" {space}", heads[0]))
    }

    fn array(&mut self, map: &'s Map<String, Value>, name: &str) -> Result<String, Error> {
        let item = match map.get("items") {
            None => self.primitive("value"),
            Some(Value::Array(_)) => {
                return Err(Error::Schema("tuple items are not supported".into()))
            }
            Some(schema) => self.rule(schema, &format!("{name}-item"))?,
        };
        let min = count(map, "minItems")?.unwrap_or(0);
        let max = count(map, "maxItems")?;
        let space = self.primitive("space");
        if max.is_some_and(|max| max < min) {
            return Err(Error::Schema("maxItems is below minItems".into()));
        }
        let inner = match max {
            Some(0) => String::new(),
            _ => {
                let rest = repeat(min.saturating_sub(1), max.map(|m| m - 1));
                let more = rest.map_or(String::new(), |r| format!(" (\",\" {space} {item}){r}"));
                let list = format!("{item}{more}");
                if min == 0 {
                    format!("({list})? ")
                } else {
                    format!("{list} ")
                }
            }
        };
        Ok(format!("\"[\" {space} {inner}\"]\" {space}"))
    }

    fn string(&mut self, map: &'s Map<String, Value>) -> Result<String, Error> {
        let format = map.get("format").and_then(Value::as_str);
        let format = ["date", "time", "date-time", "uuid"]
            .into_iter()
            .find(|&f| Some(f) == format);
        let lengths = map.contains_key("minLength") || map.contains_key("maxLength");
        let pattern = map.get("pattern");
        if usize::from(format.is_some()) + usize::from(lengths) + usize::from(pattern.is_some()) > 1
        {
            return Err(Error::Schema(
                "combining pattern, format and lengths is not supported".into(),
            ));
        }
        if format.is_none() && !lengths && pattern.is_none() {
            return Ok(self.primitive("string"));
        }
        let content = if let Some(pattern) = pattern {
            let pattern = pattern
                .as_str()
                .ok_or_else(|| Error::Schema("pattern must be a string".into()))?;
            self.primitive(regex::ANY);
            regex::to_gbnf(pattern)?
        } else if let Some(format) = format {
            self.primitive(format)
        } else {
            let min = count(map, "minLength")?.unwrap_or(0);
            let max = count(map, "maxLength")?;
            if max.is_some_and(|max| max < min) {
                return Err(Error::Schema("maxLength is below minLength".into()));
            }
            let ch = self.primitive("char");
            repeat(min, max).map_or(String::new(), |r| format!("{ch}{r}"))
        };
        let space = self.primitive("space");
        Ok(format!(r#""\"" {content} "\"" {space}"#))
    }

    fn integer(&mut self, map: &'s Map<String, Value>) -> Result<String, Error> {
        let (lo, hi) = bounds(map)?;
        if lo.is_none() && hi.is_none() {
            return Ok(self.primitive("integer"));
        }
        let lo = lo.map_or(-MAX_INTEGER, |(v, excl)| {
            let c = v.ceil();
            (if excl && c == v { c + 1.0 } else { c }).max(-MAX_INTEGER as f64) as i64
        });
        let hi = hi.map_or(MAX_INTEGER, |(v, excl)| {
            let f = v.floor();
            (if excl && f == v { f - 1.0 } else { f }).min(MAX_INTEGER as f64) as i64
        });
        let digits = range::integers(lo, hi)
            .ok_or_else(|| Error::Schema("the integer bounds leave no value".into()))?;
        let space = self.primitive("space");
        Ok(format!("{digits} {space}"))
    }

    fn number(&mut self, map: &'s Map<String, Value>) -> Result<String, Error> {
        let (lo, hi) = bounds(map)?;
        if lo.is_none() && hi.is_none() {
            return Ok(self.primitive("number"));
        }
        let whole = |b: Option<(f64, bool)>| -> Result<Option<(i64, bool)>, Error> {
            b.map(|(v, excl)| {
                if v.fract() == 0.0 && v.abs() <= range::MAX_WHOLE as f64 {
                    Ok((v as i64, excl))
                } else {
                    Err(Error::Schema(format!(
                        "number bound {v} is not supported; use whole numbers"
                    )))
                }
            })
            .transpose()
        };
        let digits = range::decimals(whole(lo)?, whole(hi)?)
            .ok_or_else(|| Error::Schema("the number bounds leave no value".into()))?;
        let space = self.primitive("space");
        Ok(format!("{digits} {space}"))
    }

    fn reference(&mut self, r: &str) -> Result<String, Error> {
        if let Some(name) = self.refs.get(r) {
            return Ok(name.clone());
        }
        let target = r
            .strip_prefix('#')
            .and_then(|pointer| self.root.pointer(pointer))
            .ok_or_else(|| Error::Schema(format!("$ref {r:?} does not point into this schema")))?;
        let name = self.fresh(r.rsplit('/').next().unwrap_or("ref"));
        self.refs.insert(r.to_owned(), name.clone());
        let body = self.expr(target, &name)?;
        self.rules.push((name.clone(), body));
        Ok(name)
    }

    /// A rule name for `schema`'s expression, adding a rule unless the
    /// expression already is one.
    fn rule(&mut self, schema: &'s Value, hint: &str) -> Result<String, Error> {
        let expr = self.expr(schema, hint)?;
        if expr.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-') {
            return Ok(expr);
        }
        let name = self.fresh(hint);
        self.rules.push((name.clone(), expr));
        Ok(name)
    }

    fn key_value(&mut self, key: &str, value: &str) -> String {
        let space = self.primitive("space");
        let key = literal(&serde_json::to_string(key).expect("strings serialize"));
        format!("{key} {space} \":\" {space} {value}")
    }

    fn json_value(&mut self, value: &Value) -> String {
        let space = self.primitive("space");
        format!("{} {space}", literal(&value.to_string()))
    }

    /// Marks a shared rule and the ones it uses as needed; returns its name.
    fn primitive(&mut self, name: &'static str) -> String {
        if self.used.insert(name) {
            let (_, _, deps) = PRIMITIVES
                .iter()
                .find(|p| p.0 == name)
                .expect("known primitive");
            for &dep in *deps {
                self.primitive(dep);
            }
        }
        name.to_owned()
    }

    /// A rule name like `hint` that is not taken yet.
    fn fresh(&mut self, hint: &str) -> String {
        let mut base: String = hint
            .chars()
            .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
            .collect();
        base = base.trim_matches('-').to_owned();
        if base.is_empty() {
            base = "rule".to_owned();
        }
        let mut name = base.clone();
        let mut n = 1;
        while !self.taken.insert(name.clone()) {
            n += 1;
            name = format!("{base}-{n}");
        }
        name
    }
}

fn infer_type(map: &Map<String, Value>) -> &'static str {
    let has = |keys: &[&str]| keys.iter().any(|k| map.contains_key(*k));
    if has(&["properties", "required", "additionalProperties"]) {
        "object"
    } else if has(&["items", "minItems", "maxItems"]) {
        "array"
    } else if has(&["pattern", "format", "minLength", "maxLength"]) {
        "string"
    } else if has(&["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"]) {
        "number"
    } else {
        "any"
    }
}

/// The lower and upper bound, each `(value, exclusive)`, from both the
/// numeric and the older boolean form of `exclusiveMinimum`/`Maximum`.
type Bound = Option<(f64, bool)>;

fn bounds(map: &Map<String, Value>) -> Result<(Bound, Bound), Error> {
    let number = |key: &str| -> Result<Option<f64>, Error> {
        map.get(key)
            .map(|v| {
                v.as_f64()
                    .ok_or_else(|| Error::Schema(format!("{key} must be a number")))
            })
            .transpose()
    };
    let mut lo = number("minimum")?.map(|v| (v, false));
    let mut hi = number("maximum")?.map(|v| (v, false));
    match map.get("exclusiveMinimum") {
        Some(Value::Bool(excl)) => lo = lo.map(|(v, _)| (v, *excl)),
        Some(_) => {
            let v = number("exclusiveMinimum")?.expect("present");
            lo = Some(lo.map_or((v, true), |(m, e)| if v >= m { (v, true) } else { (m, e) }));
        }
        None => {}
    }
    match map.get("exclusiveMaximum") {
        Some(Value::Bool(excl)) => hi = hi.map(|(v, _)| (v, *excl)),
        Some(_) => {
            let v = number("exclusiveMaximum")?.expect("present");
            hi = Some(hi.map_or((v, true), |(m, e)| if v <= m { (v, true) } else { (m, e) }));
        }
        None => {}
    }
    Ok((lo, hi))
}

fn count(map: &Map<String, Value>, key: &str) -> Result<Option<u64>, Error> {
    map.get(key)
        .map(|v| {
            v.as_u64()
                .ok_or_else(|| Error::Schema(format!("{key} must be a non-negative integer")))
        })
        .transpose()
}

/// GBNF repetition suffix for `min` to `max` times; `None` for zero times.
fn repeat(min: u64, max: Option<u64>) -> Option<String> {
    Some(match (min, max) {
        (0, Some(0)) => return None,
        (0, None) => "*".to_owned(),
        (1, None) => "+".to_owned(),
        (0, Some(1)) => "?".to_owned(),
        (1, Some(1)) => String::new(),
        (m, None) => format!("{{{m},}}"),
        (m, Some(n)) if m == n => format!("{{{m}}}"),
        (m, Some(n)) => format!("{{{m},{n}}}"),
    })
}

fn group(mut alts: Vec<String>) -> String {
    if alts.len() == 1 {
        alts.pop().expect("one")
    } else {
        format!("({})", alts.join(" | "))
    }
}

/// `text` as a GBNF string literal.
pub(crate) fn literal(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            c if (c as u32) < 0x20 || c == '\u{7F}' => {
                out.push_str(&format!("\\x{:02X}", c as u32))
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// A code point written for a GBNF character class.
pub(crate) fn class_char(c: u32) -> String {
    match char::from_u32(c) {
        Some(ch) if ch.is_ascii_graphic() && !"\\]-^[\"".contains(ch) => ch.to_string(),
        _ if c <= 0xFF => format!("\\x{c:02X}"),
        _ if c <= 0xFFFF => format!("\\u{c:04X}"),
        _ => format!("\\U{c:08X}"),
    }
}
