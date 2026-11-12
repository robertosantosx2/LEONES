//! Takes llama.cpp's command lines as they are: renamed flags are rewritten,
//! flags for what Kinetic does by itself are dropped, and the rest that have
//! no equivalent are explained instead of a bare "unexpected argument".

use std::path::Path;

/// llama.cpp spellings of flags Kinetic accepts under another name.
const RENAMED: &[(&str, &str)] = &[
    ("-sys", "--system"),
    ("--system-prompt", "--system"),
    ("--temperature", "--temp"),
    ("-dev", "--device"),
    ("-np", "--parallel"),
    ("-ctk", "--cache-type-k"),
    ("-ctv", "--cache-type-v"),
    ("-a", "--alias"),
    ("-rea", "--reasoning"),
];

/// llama.cpp's spellings of how many layers go to the GPU: zero means the
/// CPU, anything else at most that many layers on the GPU.
const GPU_LAYERS: &[&str] = &["-ngl", "--n-gpu-layers"];

/// llama.cpp flags, each with a value, for what Kinetic does by itself.
const IGNORED_WITH_VALUE: &[&str] = &[
    "-b",
    "--batch-size",
    "-ub",
    "--ubatch-size",
    "-tb",
    "--threads-batch",
    "--cache-reuse",
    "--numa",
    "--prio",
    "--poll",
    "-to",
    "--timeout",
    "--threads-http",
];

/// The same, as switches.
const IGNORED_SWITCHES: &[&str] = &[
    "--jinja",
    "--mmap",
    "-cb",
    "--cont-batching",
    "-nocb",
    "--no-cont-batching",
    "--no-warmup",
    "--metrics",
    "--slots",
    "--no-webui",
    "--embedding",
    "--embeddings",
    "-no-cnv",
    "--no-conversation",
    "-st",
    "--single-turn",
];

/// Flash attention takes on, off or auto, or nothing in older builds.
const FLASH_ATTN: &[&str] = &["-fa", "--flash-attn"];
const FLASH_ATTN_VALUES: &[&str] = &["on", "off", "auto", "true", "false", "1", "0"];

const UNSUPPORTED: &[(&[&str], &str)] = &[
    (
        &[
            "-sm",
            "--split-mode",
            "-ts",
            "--tensor-split",
            "-mg",
            "--main-gpu",
            "-ot",
            "--override-tensor",
        ],
        "Kinetic runs the model wholly on one device; choose it with --device",
    ),
    (
        &[
            "-cnv",
            "--conversation",
            "-i",
            "--interactive",
            "--interactive-first",
        ],
        "use `kinetic chat <model>`",
    ),
    (
        &["--chat-template"],
        "built-in template names are not supported; pass a Jinja file with --chat-template-file",
    ),
    (
        &[
            "-md",
            "--model-draft",
            "--draft",
            "--draft-max",
            "--draft-min",
            "-ngld",
        ],
        "speculative decoding is automatic and needs no draft model",
    ),
    (
        &["-hf", "--hf-repo", "-mu", "--model-url"],
        "download with `kinetic pull <org>/<repo>[:<quant>]`, then run it by name",
    ),
    (
        &["-f", "--file"],
        "pipe the prompt in: kinetic run <model> < prompt.txt",
    ),
    (
        &["--image"],
        "send images to the server: kinetic serve <model> --mmproj <projector>",
    ),
    (
        &["--control-vector", "--control-vector-scaled"],
        "control vectors are not supported yet; LoRA adapters are, with --lora",
    ),
    (
        &["--grammar", "--grammar-file", "-j", "--json-schema"],
        "constrained output is in the server, through `grammar` and `response_format`",
    ),
    (&["--api-key-file"], "pass the key itself with --api-key"),
    (
        &["--ssl-key-file", "--ssl-cert-file"],
        "the server speaks plain HTTP; put a TLS proxy in front",
    ),
];

/// Arguments as `kinetic` takes them when the binary was copied to one of
/// llama.cpp's names: llama-server serves, llama-cli chats, or answers one
/// prompt when given one, as llama-completion does.
pub fn dispatch(mut args: Vec<String>) -> Vec<String> {
    let name = args
        .first()
        .and_then(|a| Path::new(a).file_stem())
        .map(|s| s.to_string_lossy().to_ascii_lowercase());
    let one_shot = args.iter().any(|a| {
        let name = a.split_once('=').map_or(a.as_str(), |(n, _)| n);
        matches!(
            name,
            "-p" | "--prompt" | "-no-cnv" | "--no-conversation" | "-st" | "--single-turn"
        )
    });
    let command = match name.as_deref() {
        Some("llama-server") => "serve",
        Some("llama-cli") if !one_shot => "chat",
        Some("llama-cli" | "llama-completion") => "run",
        _ => return args,
    };
    args.insert(1, command.to_owned());
    args
}

/// Rewrites renamed flags and drops those for what Kinetic does by itself,
/// or returns what to say about an unsupported one.
pub fn translate(args: Vec<String>) -> Result<Vec<String>, String> {
    let mut out = Vec::with_capacity(args.len());
    let mut args = args.into_iter();
    while let Some(arg) = args.next() {
        let (name, value) = match arg.split_once('=') {
            Some((name, value)) => (name, Some(value.to_owned())),
            None => (arg.as_str(), None),
        };
        if GPU_LAYERS.contains(&name) {
            let layers = value
                .or_else(|| args.next())
                .ok_or_else(|| format!("{name} needs a number of layers"))?;
            match layers.trim() {
                "0" => out.push("--device=cpu".to_owned()),
                "auto" | "all" => {}
                n => out.push(format!("--gpu-layers={n}")),
            }
            continue;
        }
        if IGNORED_SWITCHES.contains(&name) {
            continue;
        }
        if IGNORED_WITH_VALUE.contains(&name) {
            if value.is_none() {
                args.next();
            }
            continue;
        }
        if FLASH_ATTN.contains(&name) {
            if value.is_none()
                && args
                    .as_slice()
                    .first()
                    .is_some_and(|v| FLASH_ATTN_VALUES.contains(&v.as_str()))
            {
                args.next();
            }
            continue;
        }
        // older llama.cpp builds took the scale as a second argument
        if name == "--lora-scaled" && value.is_none() {
            let rest = args.as_slice();
            if let [file, scale, ..] = rest {
                if scale.parse::<f32>().is_ok() {
                    out.push(format!("--lora-scaled={file}:{scale}"));
                    args.nth(1);
                    continue;
                }
            }
        }
        if let Some((_, to)) = RENAMED.iter().find(|(from, _)| *from == name) {
            out.push(arg.replacen(name, to, 1));
            continue;
        }
        if let Some((_, why)) = UNSUPPORTED.iter().find(|(names, _)| names.contains(&name)) {
            return Err(format!("{name} is a llama.cpp flag: {why}."));
        }
        out.push(arg);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(a: &[&str]) -> Vec<String> {
        a.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn explains_unsupported_flags() {
        let err = translate(args(&["kinetic", "run", "m.gguf", "-ts", "1,1"])).unwrap_err();
        assert!(err.starts_with("-ts is a llama.cpp flag"), "{err}");
        assert!(translate(args(&["-hf", "org/repo"])).is_err());
    }

    #[test]
    fn drops_flags_for_what_kinetic_does_itself() {
        let line = [
            "serve",
            "-m",
            "m.gguf",
            "-fa",
            "on",
            "--jinja",
            "-b",
            "2048",
            "--flash-attn",
            "--port",
            "8081",
            "-cb",
            "-ngl",
            "all",
        ];
        assert_eq!(
            translate(args(&line)).unwrap(),
            args(&["serve", "-m", "m.gguf", "--port", "8081"])
        );
    }

    #[test]
    fn renamed_binaries_pick_the_command() {
        let run = |a: &[&str]| dispatch(args(a));
        assert_eq!(
            run(&["bin/llama-server.exe", "-m", "m.gguf"]),
            args(&["bin/llama-server.exe", "serve", "-m", "m.gguf"])
        );
        assert_eq!(run(&["llama-cli", "-m", "m"])[1], "chat");
        assert_eq!(run(&["llama-cli", "-m", "m", "-p", "hi"])[1], "run");
        assert_eq!(run(&["./llama-completion", "-m", "m"])[1], "run");
        assert_eq!(run(&["kinetic", "serve"]), args(&["kinetic", "serve"]));
    }

    #[test]
    fn gpu_layers_pick_the_device() {
        assert_eq!(
            translate(args(&["run", "-ngl", "99", "m.gguf"])).unwrap(),
            args(&["run", "--gpu-layers=99", "m.gguf"])
        );
        assert_eq!(
            translate(args(&["--n-gpu-layers=0", "-dev", "none"])).unwrap(),
            args(&["--device=cpu", "--device", "none"])
        );
        assert!(translate(args(&["run", "-ngl"])).is_err());
    }

    #[test]
    fn server_flags_pass_through() {
        let line = [
            "serve",
            "m.gguf",
            "--api-key",
            "k",
            "--mlock",
            "--no-mmap",
            "-a",
            "m",
            "--chat-template-file",
            "t.jinja",
        ];
        assert_eq!(
            translate(args(&line)).unwrap(),
            args(&[
                "serve",
                "m.gguf",
                "--api-key",
                "k",
                "--mlock",
                "--no-mmap",
                "--alias",
                "m",
                "--chat-template-file",
                "t.jinja",
            ])
        );
    }

    #[test]
    fn lora_scale_as_a_second_argument() {
        assert_eq!(
            translate(args(&["run", "--lora-scaled", "C:/a.gguf", "0.5", "m"])).unwrap(),
            args(&["run", "--lora-scaled=C:/a.gguf:0.5", "m"])
        );
        assert_eq!(
            translate(args(&["--lora-scaled", "a.gguf:2,b.gguf:1", "m"])).unwrap(),
            args(&["--lora-scaled", "a.gguf:2,b.gguf:1", "m"])
        );
    }

    #[test]
    fn renames_and_passes_the_rest() {
        assert_eq!(
            translate(args(&["-sys", "Be brief", "--temperature=0", "-p", "hi"])).unwrap(),
            args(&["--system", "Be brief", "--temp=0", "-p", "hi"])
        );
        assert_eq!(
            translate(args(&["serve", "m.gguf", "-np", "4"])).unwrap(),
            args(&["serve", "m.gguf", "--parallel", "4"])
        );
    }
}
