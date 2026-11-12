mod common;

#[test]
fn memory_ops_round_trip() {
    for (bk, g) in common::backends() {
        eprintln!("backend {bk}");
        let a = g.zeros::<f32>(8).unwrap();
        assert_eq!(a.len(), 32);
        assert_eq!(g.get::<f32>(&a, 0, 8).unwrap(), [0.0; 8]);
        g.put(&[1.0f32, 2.0, 3.0], &a, 2).unwrap();
        assert_eq!(g.get::<f32>(&a, 0, 6).unwrap(), [0.0, 0.0, 1.0, 2.0, 3.0, 0.0]);
        let b = g.zeros::<f32>(4).unwrap();
        g.dtod(&a, 8, &b, 4, 12).unwrap();
        assert_eq!(g.get::<f32>(&b, 0, 4).unwrap(), [0.0, 1.0, 2.0, 3.0]);
        g.memset(&a).unwrap();
        assert_eq!(g.get::<f32>(&a, 0, 8).unwrap(), [0.0; 8]);
        assert!(g.put(&[0f32; 9], &a, 0).is_err(), "a copy past the end must fail");
        let (free, total) = g.mem_info().unwrap();
        assert!(free > 0 && free <= total);
    }
}

#[test]
fn large_copies_round_trip() {
    for (bk, g) in common::backends() {
        eprintln!("backend {bk}");
        let v: Vec<u32> = (0..20u32 << 20).map(|i| i.wrapping_mul(2654435761)).collect(); // 80 MB, past one staging chunk
        let a = g.zeros::<u32>(v.len() + 1).unwrap();
        g.put(&v, &a, 1).unwrap();
        let b = g.zeros::<u32>(v.len() + 1).unwrap();
        g.dtod(&a, 0, &b, 0, a.len()).unwrap();
        assert!(g.get::<u32>(&b, 1, v.len()).unwrap() == v);
    }
}

#[test]
fn graph_records_once_and_replays() {
    for (bk, g) in common::backends() {
        eprintln!("backend {bk}");
        if std::env::var_os("STRATA_NO_GRAPH").is_some() { return; }
        let (x, y) = (g.zeros::<f32>(4).unwrap(), g.zeros::<f32>(4).unwrap());
        g.put(&[1.0f32, 2.0, 3.0, 4.0], &y, 0).unwrap();
        let mut calls = 0;
        for _ in 0..3 { g.graph(5, &mut || { calls += 1; g.add(x.addr(), y.addr(), 4) }).unwrap(); }
        assert_eq!(calls, 1, "f runs only when recording");
        assert_eq!(g.get::<f32>(&x, 0, 4).unwrap(), [3.0, 6.0, 9.0, 12.0]);
    }
}

#[test]
fn host_mailbox_is_shared_with_kernels() {
    for (bk, g) in common::backends() {
        eprintln!("backend {bk}");
        let (mb, host) = g.host_mailbox(4).unwrap();
        let ones = g.zeros::<f32>(4).unwrap();
        g.put(&[1.0f32; 4], &ones, 0).unwrap();
        unsafe { host.cast::<f32>().write_volatile(2.0) };
        g.add(mb.addr(), ones.addr(), 4).unwrap(); // the kernel reads and writes host memory
        g.sync().unwrap();
        let got: Vec<f32> = (0..4).map(|i| unsafe { host.cast::<f32>().add(i).read_volatile() }).collect();
        assert_eq!(got, [3.0, 1.0, 1.0, 1.0]);
    }
}

/// The Workgroup shared-memory accounting of the committed SPIR-V: no model, no GPU, no pipeline.
/// `gemmi_dp`'s table arrays are sized by the weight type `T` and the super-block bytes `SBB`; its KS (16 or 32) is
/// the difference between the two values, the measured sizes of the committed SPIR-V.
#[test]
fn shared_memory_matches_the_committed_spirv() {
    let q2k = [0, 10, 84, 0, 0];  // T = Q2_K (10), SBB = 84: KS = 16
    let iq3s = [0, 21, 110, 0, 0];  // T = IQ3_S (21), SBB = 110: KS = 32
    assert_eq!(rusting_strata::vulkan::spv_smem::shared_bytes("gemmi_dp", &q2k, false).unwrap(), 49152, "gemmi_dp with Q2_K");
    assert_eq!(rusting_strata::vulkan::spv_smem::shared_bytes("gemmi_dp", &iq3s, false).unwrap(), 40960, "gemmi_dp with IQ3_S");
    // The COOP variant reads the IQ tables from the buffer too: a shared copy asked for 49168 bytes (Xid 13 on a V100).
    assert_eq!(rusting_strata::vulkan::spv_smem::shared_bytes("gemmi", &q2k, false).unwrap(), 49152, "gemmi with Q2_K");
}

/// The refusal `Vk::pipeline` raises before it creates anything: kernel, specialization, bytes needed and limit.
/// A smaller limit stands in for an oversized specialization, so no doctored shader is needed; no backend, model
/// buffer or pipeline exists while this runs.
#[test]
fn shared_memory_refusal_names_kernel_spec_bytes_and_limit() {
    use rusting_strata::vulkan::spv_smem::check_shared_memory;
    let spec = [0u32, 10, 84, 0, 0];
    let e = format!("{:#}", check_shared_memory("gemmi_dp", &spec, false, 40960).unwrap_err());
    for want in ["gemmi_dp", "[0, 10, 84, 0, 0]", "49152", "40960", "maxComputeSharedMemorySize"] {
        assert!(e.contains(want), "{e:?} does not contain {want:?}");
    }
    // Exactly at the limit is accepted: the V100 reports 49152 and `gemmi_dp` with Q2_K needs 49152.
    assert_eq!(check_shared_memory("gemmi_dp", &spec, false, 49152).unwrap(), 49152);
}

/// The preflight over the reference model's weight types only (no weights uploaded): every pair must fit. Skips
/// cleanly without the model or a Vulkan device; the V100 window runs it for real.
#[test]
fn preflight_of_the_reference_model() {
    let Some(model) = common::model_path() else { return };
    let Ok(g) = rusting_strata::vulkan::Vk::new(0) else { return eprintln!("SKIP: no Vulkan device"); };
    let gg = rusting_strata::gguf::Gguf::open(&model).unwrap();
    let types = rusting_strata::gpu_model::gpu_weight_types(&gg);
    assert!(!types.is_empty(), "no GPU weight type in {}", model.display());
    g.preflight(&types, true).unwrap();
}

/// The committed SPIR-V is what `tools/gen_spirv.sh` makes from the shaders now.
#[test]
fn spirv_is_fresh() {
    if std::process::Command::new("glslc").arg("--version").output().is_err() { return eprintln!("SKIP: no glslc"); }
    let tmp = std::env::temp_dir().join(format!("strata-spv-{}", std::process::id()));
    let st = std::process::Command::new("tools/gen_spirv.sh").arg(&tmp).status().unwrap();
    assert!(st.success());
    let names = |d: &std::path::Path| { let mut v: Vec<_> = std::fs::read_dir(d).unwrap().map(|e| e.unwrap().file_name()).collect(); v.sort(); v };
    let committed = std::path::Path::new("src/vulkan/spv");
    assert_eq!(names(&tmp), names(committed), "run tools/gen_spirv.sh");
    for n in names(&tmp) {
        assert!(std::fs::read(tmp.join(&n)).unwrap() == std::fs::read(committed.join(&n)).unwrap(), "{n:?} is stale: run tools/gen_spirv.sh");
    }
    std::fs::remove_dir_all(&tmp).unwrap();
}

/// `src/vulkan/shaders/tables.glsl` is generated by `vulkan::iq_tables`; `STRATA_WRITE_TABLES=1` rewrites it.
#[test]
fn glsl_tables_are_fresh() {
    let want = rusting_strata::vulkan::iq_tables().1;
    let path = "src/vulkan/shaders/tables.glsl";
    if std::env::var_os("STRATA_WRITE_TABLES").is_some() { std::fs::write(path, &want).unwrap(); }
    assert!(std::fs::read_to_string(path).unwrap_or_default() == want, "{path} is stale: rerun with STRATA_WRITE_TABLES=1");
}

#[test]
fn batched_quantized_gemm_uses_prepared_x() {
    use rusting_strata::backend::SAME_X;
    use rusting_strata::quant::GgmlType;
    use rusting_strata::weights::Tensor;

    let data = include_bytes!("fixtures/Q4_K.raw").repeat(8);
    let weight = Tensor { ty: GgmlType::Q4K, cols: 256, rows: 64, data: &data };
    assert_eq!(data.len(), weight.ty.row_bytes(256) * 64);
    let n = 128;
    let input: Vec<f32> = (0..n * 256).map(|i| (i % 127) as f32 / 63.0 - 1.0).collect();
    for (backend, gpu) in common::backends() {
        let weight = gpu.upload(&weight).unwrap();
        let x = common::up(&*gpu, &input);
        let y = gpu.zeros::<f32>(n * 64).unwrap();
        gpu.prequant_gemm_x(&weight, n, x.addr(), 256).unwrap();
        gpu.prequant_gemm_x(&weight, n, x.addr(), 256).unwrap();
        gpu.batch(&mut || gpu.gemm_dense(&weight, n, x.addr(), 256, y.addr(), 64, SAME_X)).unwrap();
        let got = common::down::<f32>(&*gpu, &y);

        let expected = gpu.zeros::<f32>(n * 64).unwrap();
        gpu.gemm_dense(&weight, n, x.addr(), 256, expected.addr(), 64, 0).unwrap();
        let expected = common::down::<f32>(&*gpu, &expected);
        assert!(got.iter().any(|v| v.abs() > 1e-5), "{backend}: empty GEMM result");
        assert_eq!(got.iter().map(|v| v.to_bits()).collect::<Vec<_>>(), expected.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            "{backend}: batched result differs from non-batched GEMM");
    }
}
