//! What to do about the failures people hit most, in one line each.

/// The fix for the error `msg`, when it is a common one.
pub fn for_error(msg: &str) -> Option<&'static str> {
    let m = msg.to_ascii_lowercase();
    let has = |words: &[&str]| words.iter().any(|w| m.contains(w));
    let fix = if has(&["cannot listen on"]) {
        "another program may be using that port; pick a free one with --port N"
    } else if has(&["out_of_memory", "out of memory", "no layer fits"]) {
        "try a smaller model or quantization, a shorter context such as -c 4096, or --device cpu"
    } else if has(&["cuda driver", "built without", "vulkan loader"]) {
        "install or update the GPU driver, or run on the processor with --device cpu"
    } else if has(&["is not supported yet", "does not name its architecture"]) {
        "`kinetic models` shows which of your models run; `kinetic` alone suggests one that does"
    } else if has(&["is an encoder"]) {
        "this is an embedding model: serve it with `kinetic serve`, and chat with a text model"
    } else if has(&["unknown type id"]) {
        "this quantization is not supported yet; download the Q4_K_M or Q8_0 file instead"
    } else if has(&[
        "file ends early",
        "not a gguf file",
        "unsupported gguf version",
    ]) {
        "the file is damaged or incomplete; download it again with `kinetic pull`"
    } else if has(&["the download needs"]) {
        "free some disk space, or download to another drive with --dir"
    } else if has(&["no such file", "os error 2)", "os error 3)"]) {
        "check the path; `kinetic models` lists the models on this computer"
    } else {
        return None;
    };
    Some(fix)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn common_failures_say_what_to_do() {
        let cases = [
            ("model.gguf: no such file", "check the path"),
            (
                "x.gguf: The system cannot find the file specified. (os error 2)",
                "check the path",
            ),
            ("architecture mamba3 is not supported yet", "kinetic models"),
            (
                "cuMemAlloc failed: CUDA_ERROR_OUT_OF_MEMORY (2)",
                "smaller model",
            ),
            ("no layer fits on the device", "-c 4096"),
            ("CUDA driver not found: nvcuda.dll is missing", "GPU driver"),
            (
                "cannot listen on 127.0.0.1:8080: address in use (os error 10048)",
                "--port",
            ),
            (
                "m.gguf: file ends early at offset 1024",
                "download it again",
            ),
            ("m.gguf: not a GGUF file", "download it again"),
            ("tensor blk.0 has unknown type id 99", "Q4_K_M"),
            ("bge is an encoder; load it with Embedder", "kinetic serve"),
            (
                "1.0 GiB is free there; the download needs 2.5 GiB and 2 GiB to spare",
                "--dir",
            ),
        ];
        for (msg, fix) in cases {
            let got = for_error(msg).unwrap_or_else(|| panic!("no fix for {msg:?}"));
            assert!(got.contains(fix), "{msg:?} -> {got:?}");
            assert!(!got.contains('\n'));
        }
        assert_eq!(for_error("the prompt is empty"), None);
    }
}
