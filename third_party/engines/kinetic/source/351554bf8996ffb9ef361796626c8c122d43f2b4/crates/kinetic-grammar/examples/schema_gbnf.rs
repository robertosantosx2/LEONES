//! Prints the GBNF for a JSON Schema file.
//!
//! cargo run --release -p kinetic-grammar --example schema_gbnf -- schema.json

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let path = std::env::args()
        .nth(1)
        .ok_or("usage: schema_gbnf <schema.json>")?;
    let schema: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path)?)?;
    print!("{}", kinetic_grammar::json_schema_to_gbnf(&schema)?);
    Ok(())
}
