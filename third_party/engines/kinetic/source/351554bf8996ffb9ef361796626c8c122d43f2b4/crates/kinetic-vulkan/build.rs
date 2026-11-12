//! Compiles the WGSL kernels in `shaders/` to SPIR-V with naga, so building
//! needs no Vulkan SDK. Each kernel is its constants followed by the
//! concatenation of its source parts; `src/kernels.rs` embeds the resulting
//! `<name>.spv` files.

use std::env;
use std::fs;
use std::path::PathBuf;

use naga::back::spv;
use naga::valid::{Capabilities, ValidationFlags, Validator};

/// (kernel, constants, source parts in order).
const KERNELS: &[(&str, &str, &[&str])] = &[
    ("gemv_f32", "", &["gemv", "gemv_f32"]),
    ("gemv_f16", "", &["gemv", "gemv_f16"]),
    ("gemv_q8_0", "", &["gemv", "gemv_q8_0"]),
    ("gemv_q4_k", "", &["gemv", "k4", "gemv_q4_k"]),
    ("gemv_q5_k", "", &["gemv", "k4", "gemv_q5_k"]),
    ("gemv_q6_k", "", &["gemv", "gemv_q6_k"]),
    ("quantize_q8", "", &["quantize_q8"]),
    ("read_sum", "", &["read_sum"]),
    ("norm", "", &["norm", "put_q8"]),
    ("swiglu", "", &["swiglu", "put_q8"]),
    ("argmax", "", &["argmax"]),
    ("rope", "", &["rope"]),
    ("short_conv", "", &["short_conv", "put_q8"]),
    ("delta_conv", "", &["delta_conv"]),
    ("delta_rule", "", &["delta_rule"]),
    ("gated_norm", "", &["gated_norm", "put_q8"]),
    ("attend_64", "const PAIRS: u32 = 1u;", &["attend", "put_q8"]),
    (
        "attend_128",
        "const PAIRS: u32 = 2u;",
        &["attend", "put_q8"],
    ),
    (
        "attend_256",
        "const PAIRS: u32 = 4u;",
        &["attend", "put_q8"],
    ),
];

fn main() {
    println!("cargo:rerun-if-changed=shaders");
    let out = PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR is set by cargo"));
    for &(name, constants, parts) in KERNELS {
        let source: String = std::iter::once(constants.to_string())
            .chain(parts.iter().map(|part| {
                let path = format!("shaders/{part}.wgsl");
                fs::read_to_string(&path).unwrap_or_else(|e| panic!("reading {path}: {e}"))
            }))
            .collect::<Vec<_>>()
            .join("\n");
        fs::write(out.join(format!("{name}.spv")), compile(name, &source)).expect("write SPIR-V");
    }
}

fn compile(name: &str, source: &str) -> Vec<u8> {
    let module = naga::front::wgsl::parse_str(source)
        .unwrap_or_else(|e| panic!("{name}:\n{}", e.emit_to_string(source)));
    let info = Validator::new(
        ValidationFlags::all(),
        Capabilities::IMMEDIATES | Capabilities::SUBGROUP | Capabilities::SHADER_FLOAT16_IN_FLOAT32,
    )
    .validate(&module)
    .unwrap_or_else(|e| panic!("{name}:\n{}", e.emit_to_string(source)));
    // Vulkan 1.3 consumes SPIR-V 1.6, which has packed int8 dot products in core.
    let options = spv::Options {
        lang_version: (1, 6),
        flags: spv::WriterFlags::empty(),
        emit_int_div_checks: false,
        force_loop_bounding: false,
        ..spv::Options::default()
    };
    let words =
        spv::write_vec(&module, &info, &options, None).unwrap_or_else(|e| panic!("{name}: {e}"));
    words.iter().flat_map(|w| w.to_le_bytes()).collect()
}
