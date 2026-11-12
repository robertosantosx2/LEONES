//! JSON Schema grammars accept the documents the schema allows and reject
//! the others.

use kinetic_grammar::{json_schema_to_gbnf, Error, Grammar};
use serde_json::{json, Value};

fn grammar(schema: Value) -> Grammar {
    Grammar::from_json_schema(&schema)
        .unwrap_or_else(|e| panic!("{e}\n{}", json_schema_to_gbnf(&schema).unwrap_or_default()))
}

fn check(schema: Value, accept: &[&str], reject: &[&str]) {
    let g = grammar(schema.clone());
    let gbnf = json_schema_to_gbnf(&schema).unwrap();
    for text in accept {
        assert!(g.matches(text), "should accept {text}\n{gbnf}");
    }
    for text in reject {
        assert!(!g.matches(text), "should reject {text}\n{gbnf}");
    }
}

#[test]
fn any_json() {
    let g = Grammar::any_json();
    for text in [
        "{}",
        "[]",
        "0",
        "-1.5e10",
        "\"\\u00e9\\n\"",
        "true",
        "null",
        r#"{"a": [1, {"b": null}]}"#,
        "{\n  \"a\": 1\n}",
    ] {
        assert!(g.matches(text), "{text}");
    }
    for text in ["", "{", "01", "[1,]", "{a: 1}", "'x'", "nul", "\"\u{1}\""] {
        assert!(!g.matches(text), "{text}");
    }
}

#[test]
fn nested_objects_keep_property_order() {
    let schema = json!({
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "address": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "zip": {"type": "string", "pattern": "^[0-9]{5}$"}},
                "required": ["city", "zip"]
            },
            "nick": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name", "address"]
    });
    check(
        schema,
        &[
            r#"{"name": "Ann", "address": {"city": "Kraków", "zip": "30001"}}"#,
            r#"{"name": "Ann", "address": {"city": "X", "zip": "00000"}, "age": 7}"#,
            r#"{"name": "Ann", "address": {"city": "X", "zip": "00000"}, "nick": "a", "age": -7}"#,
            "{\n  \"name\": \"Ann\",\n  \"address\": {\"city\": \"X\", \"zip\": \"12345\"}\n}",
        ],
        &[
            r#"{"name": "Ann"}"#,
            r#"{"address": {"city": "X", "zip": "00000"}, "name": "Ann"}"#,
            r#"{"name": "Ann", "address": {"city": "X", "zip": "0000"}}"#,
            r#"{"name": "Ann", "address": {"city": "X", "zip": "00000"}, "age": 7, "nick": "a"}"#,
            r#"{"name": "Ann", "address": {"city": "X", "zip": "00000"}, "extra": 1}"#,
            r#"{"name": "Ann", "address": {"city": "X", "zip": "00000"}, "age": 1.5}"#,
        ],
    );
}

#[test]
fn all_optional_and_additional_properties() {
    let props = json!({"a": {"type": "integer"}, "b": {"type": "boolean"}});
    check(
        json!({"type": "object", "properties": props}),
        &[
            "{}",
            r#"{"a": 1}"#,
            r#"{"b": true}"#,
            r#"{"a": 1, "b": false}"#,
        ],
        &[
            r#"{"b": true, "a": 1}"#,
            r#"{"a": 1,}"#,
            r#"{,"a": 1}"#,
            r#"{"c": 1}"#,
        ],
    );
    check(
        json!({"type": "object", "properties": props, "additionalProperties": {"type": "string"}}),
        &[
            "{}",
            r#"{"x": "y"}"#,
            r#"{"a": 1, "x": "y", "z": ""}"#,
            r#"{"b": true, "x": "y"}"#,
        ],
        &[r#"{"x": 1}"#, r#"{"x": "y", "a": 1}"#],
    );
    check(
        json!({"type": "object"}),
        &["{}", r#"{"anything": [1, {"x": null}]}"#],
        &["[]", r#"{"a"}"#],
    );
}

#[test]
fn arrays() {
    check(
        json!({"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3}),
        &["[1, 2]", "[1.5, -2, 3e2]", "[ 0,1 ]"],
        &["[]", "[1]", "[1, 2, 3, 4]", "[1, \"2\"]"],
    );
    check(json!({"type": "array", "maxItems": 0}), &["[]"], &["[1]"]);
    check(
        json!({"type": "array", "items": {"const": 7}}),
        &["[]", "[7, 7]"],
        &["[8]"],
    );
}

#[test]
fn enums_consts_and_alternatives() {
    check(
        json!({"enum": ["red", "green \"g\"", 3, null, {"k": [1]}]}),
        &[r#""red""#, r#""green \"g\"""#, "3", "null", r#"{"k":[1]}"#],
        &[r#""blue""#, "4", r#"{"k": [1]}"#],
    );
    check(
        json!({"anyOf": [{"type": "string", "maxLength": 2}, {"type": "null"}]}),
        &[r#""ab""#, "null"],
        &[r#""abc""#, "1"],
    );
    check(
        json!({"type": ["integer", "boolean"]}),
        &["12", "true"],
        &["1.5", "null"],
    );
    check(
        json!({"oneOf": [{"const": "a"}, {"const": "b"}]}),
        &[r#""a""#, r#""b""#],
        &[r#""c""#],
    );
}

#[test]
fn refs_and_recursion() {
    let schema = json!({
        "$defs": {
            "node": {
                "type": "object",
                "properties": {
                    "value": {"type": "integer"},
                    "children": {"type": "array", "items": {"$ref": "#/$defs/node"}}
                },
                "required": ["value"]
            }
        },
        "$ref": "#/$defs/node"
    });
    check(
        schema,
        &[
            r#"{"value": 1}"#,
            r#"{"value": 1, "children": [{"value": 2, "children": [{"value": 3}]}, {"value": 4}]}"#,
        ],
        &[
            r#"{"value": 1, "children": [{"children": []}]}"#,
            r#"{"value": 1, "children": [3]}"#,
        ],
    );
    check(
        json!({"type": "object", "properties": {"next": {"anyOf": [{"$ref": "#"}, {"type": "null"}]}}, "required": ["next"]}),
        &[r#"{"next": null}"#, r#"{"next": {"next": {"next": null}}}"#],
        &[r#"{"next": {}}"#],
    );
}

#[test]
fn string_formats() {
    check(
        json!({"type": "string", "format": "date"}),
        &[r#""2026-10-30""#],
        &[r#""2026-13-01""#, r#""2026-1-01""#, r#""x""#],
    );
    check(
        json!({"type": "string", "format": "time"}),
        &[r#""23:59:01Z""#, r#""08:00:00.123+02:00""#],
        &[r#""24:00:00Z""#, r#""08:00:00""#],
    );
    check(
        json!({"type": "string", "format": "date-time"}),
        &[r#""2026-10-30T12:00:00Z""#],
        &[r#""2026-10-30 12:00:00Z""#],
    );
    check(
        json!({"type": "string", "format": "uuid"}),
        &[r#""123e4567-e89b-12d3-a456-426614174000""#],
        &[r#""123e4567e89b12d3a456426614174000""#],
    );
    check(
        json!({"type": "string", "format": "email"}),
        &[r#""anything""#],
        &["1"],
    );
    check(
        json!({"type": "string", "minLength": 2, "maxLength": 3}),
        &[r#""ab""#, r#""a\nb""#],
        &[r#""a""#, r#""abcd""#],
    );
}

#[test]
fn patterns() {
    check(
        json!({"type": "string", "pattern": "^(\\+\\d{1,3} )?[a-z_]+(?:-[a-z]+)*$"}),
        &[r#""ab""#, r#""+48 a_b-cd-e""#],
        &[r#""Ab""#, r#""+1234 ab""#, r#""ab-""#, r#""""#],
    );
    check(
        json!({"pattern": "ab"}),
        &[r#""xxabyy""#, r#""ab""#],
        &[r#""a b""#],
    );
    check(
        json!({"pattern": "^a.c$"}),
        &[r#""abc""#, r#""a\"c""#, r#""a\\c""#],
        &[r#""a\nc""#, r#""ac""#],
    );
    check(
        json!({"pattern": "^[^a]\\s$"}),
        &[r#""b ""#, r#""\"\t""#],
        &[r#""a ""#, r#""bb""#],
    );
    for bad in ["(?=a)", "\\1", "^a|b$", "\\bword", "a{2,1x}"] {
        assert!(
            matches!(
                Grammar::from_json_schema(&json!({"pattern": bad})),
                Err(Error::Schema(_))
            ),
            "{bad}"
        );
    }
}

#[test]
fn integer_and_number_bounds() {
    check(
        json!({"type": "integer", "minimum": -5, "exclusiveMaximum": 120}),
        &["-5", "0", "7", "119"],
        &["-6", "120", "1000", "-0", "007", "1.0"],
    );
    check(
        json!({"type": "integer", "minimum": 10}),
        &["10", "123456"],
        &["9", "-10"],
    );
    check(
        json!({"type": "number", "exclusiveMinimum": 0, "maximum": 1}),
        &["0.5", "1", "0.001", "0.99"],
        &["0", "1.5", "-0.5", "1e-3", "0.000"],
    );
    check(
        json!({"type": "number", "minimum": 0}),
        &["0", "12.5"],
        &["-1"],
    );
    assert!(Grammar::from_json_schema(&json!({"type": "number", "maximum": 1.5})).is_err());
    assert!(
        Grammar::from_json_schema(&json!({"type": "integer", "minimum": 3, "maximum": 2})).is_err()
    );
}

#[test]
fn unsupported_keywords_are_errors() {
    for schema in [
        json!({"type": "array", "uniqueItems": true}),
        json!({"not": {"type": "string"}}),
        json!({"type": "object", "patternProperties": {}}),
        json!({"$ref": "https://example.com/s.json"}),
        json!({"$ref": "#/$defs/missing"}),
        json!(false),
        json!({"type": "array", "items": [{"type": "string"}]}),
    ] {
        assert!(
            matches!(Grammar::from_json_schema(&schema), Err(Error::Schema(_))),
            "{schema}"
        );
    }
    let annotated =
        json!({"title": "T", "description": "d", "type": "string", "default": "x", "$schema": "s"});
    check(annotated, &[r#""x""#], &["1"]);
}
