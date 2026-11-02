use std::collections::BTreeMap;
use std::fmt::Write;

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Number(String),
    String(String),
    Array(Vec<Value>),
    Object(BTreeMap<String, Value>),
}

impl Value {
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Object(values) => values.get(key),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::String(value) => Some(value),
            _ => None,
        }
    }

    pub fn as_array(&self) -> Option<&[Value]> {
        match self {
            Value::Array(values) => Some(values),
            _ => None,
        }
    }
}

pub fn escape(input: &str) -> String {
    let mut out = String::with_capacity(input.len() + 2);
    out.push('"');
    for ch in input.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000c}' => out.push_str("\\f"),
            c if c <= '\u{001f}' => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn stringify(value: &Value) -> String {
    match value {
        Value::Null => "null".to_string(),
        Value::Bool(value) => value.to_string(),
        Value::Number(value) => value.clone(),
        Value::String(value) => escape(value),
        Value::Array(values) => {
            let items = values.iter().map(stringify).collect::<Vec<_>>();
            format!("[{}]", items.join(","))
        }
        Value::Object(values) => {
            let items = values.iter().map(|(key, value)| {
                format!("{}:{}", escape(key), stringify(value))
            }).collect::<Vec<_>>();
            format!("{{{}}}", items.join(","))
        }
    }
}

struct Parser<'a> {
    input: &'a str,
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self { input, pos: 0 }
    }

    fn error(&self, message: &str) -> String {
        format!("JSON inválido en byte {}: {message}", self.pos)
    }

    fn peek(&self) -> Option<u8> {
        self.input.as_bytes().get(self.pos).copied()
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.pos += 1;
        }
    }

    fn consume(&mut self, expected: u8) -> Result<(), String> {
        if self.peek() == Some(expected) {
            self.pos += 1;
            Ok(())
        } else {
            Err(self.error("carácter inesperado"))
        }
    }

    fn parse_value(&mut self) -> Result<Value, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'n') => { self.literal(b"null")?; Ok(Value::Null) }
            Some(b't') => { self.literal(b"true")?; Ok(Value::Bool(true)) }
            Some(b'f') => { self.literal(b"false")?; Ok(Value::Bool(false)) }
            Some(b'"') => self.parse_string().map(Value::String),
            Some(b'[') => self.parse_array(),
            Some(b'{') => self.parse_object(),
            Some(b'-' | b'0'..=b'9') => self.parse_number(),
            _ => Err(self.error("se esperaba un valor")),
        }
    }

    fn literal(&mut self, literal: &[u8]) -> Result<(), String> {
        let end = self.pos.saturating_add(literal.len());
        if self.input.as_bytes().get(self.pos..end) == Some(literal) {
            self.pos = end;
            Ok(())
        } else {
            Err(self.error("literal inválido"))
        }
    }

    fn parse_string(&mut self) -> Result<String, String> {
        self.consume(b'"')?;
        let mut out = String::new();
        loop {
            let Some(byte) = self.peek() else {
                return Err(self.error("cadena sin cerrar"));
            };
            match byte {
                b'"' => {
                    self.pos += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.pos += 1;
                    let Some(escaped) = self.peek() else {
                        return Err(self.error("escape incompleto"));
                    };
                    self.pos += 1;
                    match escaped {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let first = self.hex_quad()?;
                            let code = if (0xD800..=0xDBFF).contains(&first) {
                                if !self.input.as_bytes().get(self.pos..self.pos + 2).map(|bytes| bytes == b"\\u").unwrap_or(false) {
                                    return Err(self.error("par sustituto Unicode incompleto"));
                                }
                                self.pos += 2;
                                let second = self.hex_quad()?;
                                if !(0xDC00..=0xDFFF).contains(&second) {
                                    return Err(self.error("par sustituto Unicode inválido"));
                                }
                                0x10000 + (((first as u32 - 0xD800) << 10) | (second as u32 - 0xDC00))
                            } else if (0xDC00..=0xDFFF).contains(&first) {
                                return Err(self.error("sustituto Unicode aislado"));
                            } else {
                                first as u32
                            };
                            out.push(char::from_u32(code).ok_or_else(|| self.error("carácter Unicode inválido"))?);
                        }
                        _ => return Err(self.error("escape no reconocido")),
                    }
                }
                0x00..=0x1f => return Err(self.error("carácter de control sin escapar")),
                _ => {
                    let ch = self.input[self.pos..].chars().next()
                        .ok_or_else(|| self.error("UTF-8 incompleto"))?;
                    out.push(ch);
                    self.pos += ch.len_utf8();
                }
            }
        }
    }

    fn hex_quad(&mut self) -> Result<u16, String> {
        let end = self.pos.saturating_add(4);
        let digits = self.input.as_bytes().get(self.pos..end)
            .ok_or_else(|| self.error("escape Unicode incompleto"))?;
        let text = std::str::from_utf8(digits).map_err(|_| self.error("escape Unicode inválido"))?;
        let value = u16::from_str_radix(text, 16).map_err(|_| self.error("escape Unicode inválido"))?;
        self.pos = end;
        Ok(value)
    }

    fn parse_array(&mut self) -> Result<Value, String> {
        self.consume(b'[')?;
        self.skip_ws();
        let mut values = Vec::new();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(Value::Array(values));
        }
        loop {
            values.push(self.parse_value()?);
            self.skip_ws();
            match self.peek() {
                Some(b',') => { self.pos += 1; }
                Some(b']') => { self.pos += 1; return Ok(Value::Array(values)); }
                _ => return Err(self.error("se esperaba ',' o ']'")),
            }
        }
    }

    fn parse_object(&mut self) -> Result<Value, String> {
        self.consume(b'{')?;
        self.skip_ws();
        let mut values = BTreeMap::new();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(Value::Object(values));
        }
        loop {
            self.skip_ws();
            if self.peek() != Some(b'"') {
                return Err(self.error("la clave del objeto debe ser una cadena"));
            }
            let key = self.parse_string()?;
            self.skip_ws();
            self.consume(b':')?;
            let value = self.parse_value()?;
            values.insert(key, value);
            self.skip_ws();
            match self.peek() {
                Some(b',') => { self.pos += 1; }
                Some(b'}') => { self.pos += 1; return Ok(Value::Object(values)); }
                _ => return Err(self.error("se esperaba ',' o '}'")),
            }
        }
    }

    fn parse_number(&mut self) -> Result<Value, String> {
        let start = self.pos;
        if self.peek() == Some(b'-') { self.pos += 1; }
        match self.peek() {
            Some(b'0') => self.pos += 1,
            Some(b'1'..=b'9') => {
                self.pos += 1;
                while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
            }
            _ => return Err(self.error("parte entera inválida")),
        }
        if self.peek() == Some(b'.') {
            self.pos += 1;
            let fraction_start = self.pos;
            while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
            if self.pos == fraction_start { return Err(self.error("fracción vacía")); }
        }
        if matches!(self.peek(), Some(b'e' | b'E')) {
            self.pos += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) { self.pos += 1; }
            let exponent_start = self.pos;
            while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
            if self.pos == exponent_start { return Err(self.error("exponente vacío")); }
        }
        Ok(Value::Number(self.input[start..self.pos].to_string()))
    }
}

pub fn parse(input: &str) -> Result<Value, String> {
    let mut parser = Parser::new(input);
    let value = parser.parse_value()?;
    parser.skip_ws();
    if parser.pos != input.len() {
        return Err(parser.error("contenido adicional después del valor"));
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::{escape, parse, stringify, Value};

    #[test]
    fn escapes_json_control_characters() {
        assert_eq!(escape("a\"b\\c\n"), "\"a\\\"b\\\\c\\n\"");
    }

    #[test]
    fn parses_nested_json_and_unicode() {
        let value = parse(r#"{"message":"hola \ud83d\ude80","items":[true,null,3.5]}"#).unwrap();
        assert_eq!(value.get("message").and_then(Value::as_str), Some("hola 🚀"));
        assert_eq!(stringify(&value), r#"{"items":[true,null,3.5],"message":"hola 🚀"}"#);
    }

    #[test]
    fn rejects_invalid_json() {
        assert!(parse(r#"{"broken":]"#).is_err());
        assert!(parse(r#"01"#).is_err());
        assert!(parse(r#""unclosed"#).is_err());
    }

    #[test]
    fn parses_surrogate_pairs_and_escapes() {
        let value = parse(r#""A\n\uD83D\uDE80""#).unwrap();
        assert_eq!(value, Value::String("A\n🚀".to_string()));
    }
}
