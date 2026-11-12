"""Plan tests with fake hardware (no GPU, no files needed). Run: python3 -m unittest discover -s tests -v"""
import importlib.util, io, contextlib, json, os, unittest
spec = importlib.util.spec_from_file_location("tr", os.path.join(os.path.dirname(__file__), "..", "tandem-run.py"))
tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)

PROFILES = {
    "i5-4090-64": dict(gpu="RTX 4090", vram_gib=24, cores=6, ram_gib=64, pcie_gen=4),
    "i5-5070ti-32": dict(gpu="RTX 5070 Ti", vram_gib=16, cores=6, ram_gib=32, pcie_gen=5, cc="12.0"),
    "i9-4090-128": dict(gpu="RTX 4090", vram_gib=24, cores=10, ram_gib=128, pcie_gen=3),
    "5955wx-256": dict(gpu="RTX 6000 Ada", vram_gib=48, cores=16, ram_gib=256, pcie_gen=4),
    "pc-16": dict(gpu="RTX 4090", vram_gib=24, cores=6, ram_gib=16, pcie_gen=4),
}

def plan(model, prof, extra=(), full=False):
    a = tr.parse_args(["--model", model, "--dry-run", "--server-bin", "/x/llama-server",
                       "--fake-hw", json.dumps(PROFILES[prof]), *extra])
    hw, m = tr.make_plan(a)
    p = tr.choose_flags(hw, m, a)
    return (" ".join(p.args), p.env, p) if full else (" ".join(p.args), p.env)

class T(unittest.TestCase):
    def test_qwen_consumer(self):
        s, e = plan("qwen3.8", "i5-4090-64")
        self.assertIn("--spec-draft-n-max 3", s); self.assertNotIn("-lm none", s)
        self.assertIn("--cache-ram 0", s); self.assertEqual(e["LLAMA_MTP_DRAFT_VOCAB"], "100000")
    def test_qwen_32gb(self):
        s, e = plan("qwen3.8", "i5-5070ti-32")
        self.assertIn("--cache-ram 0", s); self.assertNotIn("-lm none", s)
    def test_qwen_i9(self):
        s, _ = plan("qwen3.8", "i9-4090-128")
        self.assertIn("-lm none", s); self.assertIn("--spec-draft-n-max 3", s); self.assertNotIn("--cache-ram", s)
    def test_qwen_workstation(self):
        s, _ = plan("qwen3.8", "5955wx-256")
        self.assertIn("--spec-draft-n-max 4", s); self.assertIn("-lm none", s)
    def test_qwen_16gb_pc(self):
        s, _ = plan("qwen3.8", "pc-16")
        self.assertIn("--cache-ram 0", s); self.assertNotIn("-lm none", s)
    def test_gptoss_eagle_cores(self):
        self.assertNotIn("eagle3", plan("gpt-oss-120b", "i5-4090-64")[0])
        self.assertIn("draft-eagle3", plan("gpt-oss-120b", "i9-4090-128")[0])
        self.assertIn("--spec-draft-n-max 4", plan("gpt-oss-120b", "5955wx-256")[0])
    def test_fast_flag(self):
        self.assertEqual(plan("qwen3.8", "i9-4090-128", ["--fast"])[1]["LLAMA_MOE_TAIL_SKIP"], "7")
        self.assertNotIn("LLAMA_MOE_TAIL_SKIP", plan("qwen3.8", "i9-4090-128")[1])
    def test_dry_run_prints(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tr.main(["--model", "qwen3.8", "--dry-run", "--fake-hw", json.dumps(PROFILES["pc-16"])])
        self.assertIn("== Command ==", buf.getvalue())
    def test_generic_unknown_file(self):
        p = os.path.join(os.path.dirname(__file__), "fake-model.gguf"); f = open(p, "wb"); f.write(b"junk"); f.truncate(40 << 30); f.close()  # sparse 40 GiB
        try:
            s, _ = plan(p, "i9-4090-128")
            self.assertIn("-cmoe", s); self.assertNotIn("--spec-type", s)
        finally: os.remove(p)

    def test_ram_tiers(self):
        # 16 GiB PC, 78 GiB model: loud warning only on an old build; always the 0.6x warning
        _, e, p = plan("qwen3.8", "pc-16", ["--fake-build", "old"], full=True)
        _, e, p = plan("qwen3.8", "pc-16", ["--fake-build", "new"], full=True)
        self.assertFalse(any("predates" in w for w in p.warnings)); self.assertTrue(any("streamed from the SSD" in w for w in p.warnings))
        # 64 GiB PC with the 78 GiB model: plain note, no warning, on a new build
        _, e, p = plan("qwen3.8", "i5-4090-64", ["--fake-build", "new"], full=True)
        self.assertEqual(p.warnings, []); self.assertTrue(any("larger than RAM" in n for n in p.notes))
    def test_env_overrides_only_old_builds(self):
        prof = dict(PROFILES["5955wx-256"], ram_cgroup_gib=48)
        for b, want in (("new", False), ("old", True), ("unknown", True)):
            a = tr.parse_args(["--model", "qwen3.8", "--dry-run", "--fake-hw", json.dumps(prof), "--fake-build", b])
            hw, m = tr.make_plan(a); p = tr.choose_flags(hw, m, a)
            self.assertEqual("LLAMA_MOE_PIN_EXPS" in p.env, want, b)

    def test_old_kernel_note(self):
        for kern, want in (("5.15.0-198-generic", True), ("6.8.0", False)):
            a = tr.parse_args(["--model", "qwen3.8", "--dry-run", "--fake-hw", json.dumps(dict(PROFILES["i5-4090-64"], kernel=kern))])
            hw, m = tr.make_plan(a); p = tr.choose_flags(hw, m, a)
            self.assertEqual(any("older kernels" in n for n in p.notes), want, kern)

    def test_eagle_n_by_vram(self):
        self.assertIn("--spec-draft-n-max 3", plan("gpt-oss-120b", "i9-4090-128")[0])
        self.assertIn("--spec-draft-n-max 4", plan("gpt-oss-120b", "5955wx-256")[0])

    def _calib(self, speeds, calibrate):
        """Run tr.calibrate with a fake server; speeds: {n: tok/s}. Returns (result, list of n tried)."""
        a = tr.parse_args(["--model", "gpt-oss-120b", "--dry-run", "--fake-hw", json.dumps(PROFILES["i9-4090-128"]), "--fake-build", "new"] + (["--calibrate"] if calibrate else []))
        hw, m = tr.make_plan(a); pl = tr.choose_flags(hw, m, a)
        tried = []
        class P:
            pid = 0
            def poll(self): return None
        orig = (tr.start_server, tr.wait_ready, tr.measure, tr.stop_group, tr.CACHE_DIR)
        cur = {}
        def start(argv, env, log): cur["n"] = int(argv[argv.index("--spec-draft-n-max") + 1]); tried.append(cur["n"]); return P()
        tr.start_server, tr.wait_ready, tr.stop_group = start, (lambda p, port, timeout=0: True), (lambda p: None)
        tr.measure = lambda port, n=200: speeds[cur["n"]]
        tr.CACHE_DIR = "/tmp/tandem-test-cache"
        try:
            res = tr.calibrate(hw, m, a, pl, lambda p: (["llama-server", *p.args], {}))
        finally:
            tr.start_server, tr.wait_ready, tr.measure, tr.stop_group, tr.CACHE_DIR = orig
        return res, tried

    def test_calibration_n_minus_1_only_with_flag(self):
        speeds = {2: 100, 3: 95, 4: 90}      # rule n=3 (24 GB card): n+1 loses, n-1 wins by > 2%
        res, tried = self._calib(speeds, calibrate=False)
        self.assertEqual(tried, [3, 4]); self.assertEqual(res["draft_n"], 3)
        res, tried = self._calib(speeds, calibrate=True)
        self.assertEqual(tried, [3, 4, 2]); self.assertEqual(res["draft_n"], 2)
    def test_calibration_climbs(self):
        res, tried = self._calib({3: 100, 4: 105, 5: 112}, calibrate=False)
        self.assertEqual(tried, [3, 4, 5]); self.assertEqual(res["draft_n"], 5)

if __name__ == "__main__": unittest.main()
