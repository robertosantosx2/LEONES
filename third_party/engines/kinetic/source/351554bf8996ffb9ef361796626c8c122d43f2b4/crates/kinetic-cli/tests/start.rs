//! `kinetic` alone, outside a terminal, still prints the help.

use std::process::{Command, Stdio};

#[test]
fn redirected_kinetic_prints_help_and_downloads_nothing() {
    let out = Command::new(env!("CARGO_BIN_EXE_kinetic"))
        .stdin(Stdio::null())
        .env("HF_ENDPOINT", "http://127.0.0.1:9")
        .output()
        .unwrap();
    let text = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2), "{text}");
    assert!(text.contains("Usage: kinetic"), "{text}");
    assert!(!text.contains("Pick a model"), "{text}");
}
