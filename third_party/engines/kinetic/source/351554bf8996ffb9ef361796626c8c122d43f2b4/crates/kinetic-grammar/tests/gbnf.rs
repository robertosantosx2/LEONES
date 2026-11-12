//! The example grammars shipped with llama.cpp (tests/data/llama.cpp, MIT)
//! parse and decide sample texts correctly.

use kinetic_grammar::{Error, Grammar};

fn example(name: &str) -> Grammar {
    let path = format!(
        "{}/tests/data/llama.cpp/{name}.gbnf",
        env!("CARGO_MANIFEST_DIR")
    );
    let text = std::fs::read_to_string(&path).unwrap();
    Grammar::parse(&text).unwrap_or_else(|e| panic!("{name}: {e}"))
}

fn check(name: &str, accept: &[&str], reject: &[&str]) {
    let g = example(name);
    for text in accept {
        assert!(g.matches(text), "{name} should accept {text:?}");
    }
    for text in reject {
        assert!(!g.matches(text), "{name} should reject {text:?}");
    }
}

#[test]
fn json() {
    check(
        "json",
        &[
            "{}",
            r#"{"a": [1, 2.5, "x\n", -0.5e+3], "b": {"c": null, "d": true}}"#,
            "{\n  \"k\": \"caf\u{e9} \\u00e9\"}",
        ],
        &[
            "[1]",
            r#"{"a" 1}"#,
            r#"{"a": tru}"#,
            r#"{"a": "x"#,
            "{\"a\": \"\u{1}\"}",
            "{}}",
        ],
    );
}

#[test]
fn json_arr() {
    check(
        "json_arr",
        &["[\n1,\n\"x\",\n{\"a\": []}]", "[\n]"],
        &["[1]", "[\n1,2]"],
    );
}

#[test]
fn list() {
    check("list", &["- a\n- bc d\n"], &["- a", "-a\n", "- a\r\n", ""]);
}

#[test]
fn chess() {
    check(
        "chess",
        &[
            "1. e4 e5\n2. Nf3 Nc6\n",
            "1. e4 e5\n2. Bb5 a6\n3. O-O-O Qxd8#\n",
        ],
        &["1. e4 e5\n", "1. e9 e5\n2. a3 a4\n", "1. e4 e5\n2. Nf3\n"],
    );
}

#[test]
fn arithmetic() {
    check(
        "arithmetic",
        &["1+2=3\n", "(a+b)*c=7\nx= y\n"],
        &["1+=2\n", "1+2=3", "A=1\n"],
    );
}

#[test]
fn c() {
    check(
        "c",
        &[
            "int main(){return 0;}",
            "int add(int a){return a+1;}float f(){x = 2;while(x<3){x = x+1;}}",
            "char g(){// note\n/* a * b */}",
        ],
        &["int main(){return 0}", "int main()", "long main(){}"],
    );
}

#[test]
fn english() {
    check(
        "english",
        &["Hello world!", "a\tb\nc"],
        &["Hello  world", "h\u{e9}llo", ""],
    );
}

#[test]
fn japanese() {
    check(
        "japanese",
        &["こんにちは", "カタカナ 漢字、"],
        &["hello", "こんにちは!"],
    );
}

#[test]
fn syntax_features() {
    let g = Grammar::parse(
        "root ::= greeting{2,3} [^a-c\\x00-\\x1F]? \"\\u00e9\\U0001F600\" .\n\
         greeting ::= (\"hi\" | \"yo\") \"!\" # trailing comment\n",
    )
    .unwrap();
    assert!(g.matches("hi!yo!d\u{e9}\u{1F600}x"));
    assert!(g.matches("yo!yo!yo!\u{e9}\u{1F600}\u{4E2D}"));
    assert!(!g.matches("hi!\u{e9}\u{1F600}x"));
    assert!(!g.matches("hi!hi!b\u{e9}\u{1F600}x"));
    assert!(!g.matches("hi!hi!\u{e9}\u{1F600}"));

    let alternatives = Grammar::parse("root ::= \"a\" |\n  \"b\"\n").unwrap();
    assert!(alternatives.matches("a") && alternatives.matches("b"));
    let empty = Grammar::parse("root ::= x*\nx ::= \"x\"\n").unwrap();
    assert!(empty.matches("") && empty.matches("xxx"));
    let exact = Grammar::parse("root ::= [0-9]{3}").unwrap();
    assert!(exact.matches("123") && !exact.matches("12") && !exact.matches("1234"));
}

#[test]
fn errors() {
    assert_eq!(
        Grammar::parse("root ::= foo\n").err(),
        Some(Error::UndefinedRule("foo".into()))
    );
    assert_eq!(
        Grammar::parse("start ::= \"a\"\n").err(),
        Some(Error::UndefinedRule("root".into()))
    );
    assert!(matches!(
        Grammar::parse("root ::= root \"a\"\n"),
        Err(Error::LeftRecursion(_))
    ));
    assert!(matches!(
        Grammar::parse("root ::= (\"a\"?)*\n"),
        Err(Error::LeftRecursion(_))
    ));
    assert!(matches!(
        Grammar::parse("root ::= \"a\n"),
        Err(Error::Syntax { .. })
    ));
    assert!(matches!(
        Grammar::parse("root ::= [a-\n"),
        Err(Error::Syntax { .. })
    ));
    assert!(matches!(
        Grammar::parse("root ::= *\n"),
        Err(Error::Syntax { .. })
    ));
    assert!(matches!(
        Grammar::parse("root := \"a\"\n"),
        Err(Error::Syntax { line: 1, .. })
    ));
    assert!(matches!(
        Grammar::parse("root ::= \"a\"\nx ::= \"\\q\"\n"),
        Err(Error::Syntax { line: 2, .. })
    ));
    assert!(matches!(
        Grammar::parse("root ::= <[12]>\n"),
        Err(Error::Syntax { .. })
    ));
    assert!(matches!(
        Grammar::parse("root ::= (\"ab\"{2000}){2000}\n"),
        Err(Error::TooLarge)
    ));
}
