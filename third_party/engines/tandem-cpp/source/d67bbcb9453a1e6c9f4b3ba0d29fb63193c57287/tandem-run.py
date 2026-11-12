#!/usr/bin/env python3
"""tandem-run.py: one command from a model to a fast, correct tandem.cpp llama-server.

    python3 tandem-run.py --model qwen3.8            # registry entry (asks before downloading)
    python3 tandem-run.py --model /path/any-moe.gguf # generic MoE rules
    python3 tandem-run.py --model qwen3.8 --dry-run  # print the plan only

Steps: detect hardware -> resolve model -> choose flags (each with a reason) -> calibrate once per
machine+model (cached in ~/.cache/tandem/) -> launch llama-server in the foreground.
Stdlib only. Linux + NVIDIA for now; hardware access sits behind detect_*() and Backend so others can be added.
"""
import argparse, glob, hashlib, json, os, re, shlex, shutil, signal, struct, subprocess, sys, time
import urllib.request

GiB = 1024 ** 3
MiB = 1024 ** 2
CACHE_DIR = os.path.expanduser(os.environ.get("TANDEM_CACHE_DIR", "~/.cache/tandem"))

# ----------------------------------------------------------------------------------------------
# Registry. "kind" selects the rule set in choose_flags(). Sizes are bytes of the files as published.
# ----------------------------------------------------------------------------------------------
REGISTRY = {
    "qwen3.8": {
        "title": "Qwen3.8-Flash-Next + MTP head",
        "match": re.compile(r"qwen3\.8", re.I),
        "kind": "qwen38-mtp",
        "model_repo": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF",
        "model_include": "IQ3_S/*",
        "model_file": "IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf",
        "model_gib": 78,
        "draft_repo": "ewhacc/qwen38-mtp-outq4_K-expsq4_K",
        "draft_include": "*.gguf",
        "draft_file": "qwen38-mtp-outq4_K-expsq4_K.gguf",
        "draft_gib": 2.5,
    },
    "gpt-oss-120b": {
        "title": "gpt-oss-120b MXFP4 + EAGLE3 draft",
        "match": re.compile(r"gpt-oss-120b", re.I),
        "kind": "gptoss-eagle3",
        "model_repo": "ggml-org/gpt-oss-120b-GGUF",
        "model_include": "gpt-oss-120b-mxfp4*.gguf",
        "model_file": "gpt-oss-120b-MXFP4.gguf",
        "model_gib": 59,
        "draft_repo": "ggml-org/gpt-oss-120b-GGUF",   # TODO(main): confirm the repo that hosts the EAGLE3 draft
        "draft_include": "eagle3-gpt-oss-120b-Q8_0.gguf",
        "draft_file": "eagle3-gpt-oss-120b-Q8_0.gguf",
        "draft_gib": 0.8,
    },
}
ALIASES = {"qwen3.8-flash-next": "qwen3.8", "qwen38": "qwen3.8", "gpt-oss": "gpt-oss-120b", "gptoss": "gpt-oss-120b"}


def say(msg=""):
    print(msg, flush=True)


# ----------------------------------------------------------------------------------------------
# Hardware
# ----------------------------------------------------------------------------------------------
class HW(dict):
    __getattr__ = dict.get


def _run(cmd, timeout=15):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def detect_gpus():
    """NVIDIA via nvidia-smi. Returns a list of dicts (index, name, vram_mib, cc, pcie_gen, pcie_width)."""
    out = _run(["nvidia-smi", "--query-gpu=index,name,memory.total,compute_cap,pcie.link.gen.max,pcie.link.width.max",
                "--format=csv,noheader,nounits"])
    gpus = []
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 6:
            continue
        num = lambda s, f=int: f(s) if re.fullmatch(r"[\d.]+", s) else None
        gpus.append({"index": int(p[0]), "name": p[1], "vram_mib": num(p[2]), "cc": p[3],
                     "pcie_gen": num(p[4]), "pcie_width": num(p[5])})
    return gpus


def detect_cores():
    """Physical cores: unique (physical id, core id) pairs in /proc/cpuinfo, honouring the affinity mask."""
    try:
        allowed = os.sched_getaffinity(0)
    except AttributeError:
        allowed = None
    pairs, proc, phys = set(), None, None
    model = "?"
    try:
        for line in open("/proc/cpuinfo"):
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k == "processor":
                proc = int(v)
            elif k == "physical id":
                phys = v
            elif k == "core id" and (allowed is None or proc in allowed):
                pairs.add((phys, v))
            elif k == "model name":
                model = v
    except OSError:
        pass
    n = len(pairs) or max(1, (len(allowed) if allowed else os.cpu_count() or 2) // 2)
    return n, model


def cgroup_mem_limit():
    """Bytes from cgroup v2 memory.max (walking up to the root of our own cgroup) or v1, else None."""
    cands = []
    try:
        rel = [l.split(":", 2)[2].strip() for l in open("/proc/self/cgroup") if l.startswith("0::")]
        if rel:
            d = "/sys/fs/cgroup" + rel[0]
            while d.startswith("/sys/fs/cgroup"):
                cands.append(d + "/memory.max")
                if d == "/sys/fs/cgroup":
                    break
                d = os.path.dirname(d)
    except OSError:
        pass
    cands.append("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    best = None
    for c in cands:
        try:
            s = open(c).read().strip()
        except OSError:
            continue
        if s.isdigit() and int(s) < (1 << 60):
            best = int(s) if best is None else min(best, int(s))
    return best


def detect_ram():
    total = 0
    try:
        total = next(int(l.split()[1]) * 1024 for l in open("/proc/meminfo") if l.startswith("MemTotal"))
    except (OSError, StopIteration):
        pass
    lim = cgroup_mem_limit()
    return total, lim, (min(total, lim) if lim else total)


def detect(args, probe_dir):
    hw = HW()
    gpus = detect_gpus()
    idx = args.gpu
    g = next((x for x in gpus if x["index"] == idx), gpus[0] if gpus else None)
    if g is None:
        sys.exit("tandem-run: no NVIDIA GPU found (nvidia-smi gave nothing). Only CUDA is supported for now.")
    hw.update(gpu=g["name"], gpu_index=g["index"], n_gpus=len(gpus), vram_gib=g["vram_mib"] / 1024, vram_mib=g["vram_mib"],
              cc=g["cc"], pcie_gen=g["pcie_gen"], pcie_width=g["pcie_width"])
    hw["cores"], hw["cpu"] = detect_cores()
    total, lim, eff = detect_ram()
    hw.update(ram_total_gib=total / GiB, ram_cgroup_gib=(lim / GiB if lim else None), ram_gib=eff / GiB)
    try:
        hw["disk_free_gib"] = shutil.disk_usage(probe_dir).free / GiB
    except OSError:
        hw["disk_free_gib"] = None
    hw["kernel"] = os.uname().release
    hw["real"] = {k: hw[k] for k in ("vram_gib", "ram_gib", "cores")}
    hw["emulated"] = []
    # test overrides: emulate a smaller box on a bigger one (the wrappers are added in build_command)
    if args.assume_vram_gib is not None:
        hw["emulated"].append("vram")
        hw["vram_gib"] = args.assume_vram_gib
    if args.assume_ram_gib is not None:
        hw["emulated"].append("ram")
        hw["ram_gib"] = args.assume_ram_gib
    if args.assume_cores is not None:
        hw["emulated"].append("cores")
        hw["cores"] = args.assume_cores
    return hw


# ----------------------------------------------------------------------------------------------
# GGUF header (just enough to say what a local file is)
# ----------------------------------------------------------------------------------------------
def gguf_info(path):
    """{'arch', 'experts', 'experts_used', 'blocks'} from the KV header; {} if unreadable. Stops after the keys needed."""
    sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
    info = {}
    try:
        f = open(path, "rb")
    except OSError:
        return info
    with f:
        if f.read(4) != b"GGUF":
            return info
        _ver, _nt, nkv = struct.unpack("<IQQ", f.read(20))

        def rstr():
            n, = struct.unpack("<Q", f.read(8))
            return f.read(n).decode("utf-8", "replace")

        def rval(t):
            if t in fmt:
                return struct.unpack(fmt[t], f.read(sizes[t]))[0]
            if t == 8:
                return rstr()
            if t == 9:
                et, n = struct.unpack("<IQ", f.read(12))
                if et in sizes:
                    f.seek(n * sizes[et], 1)
                else:
                    for _ in range(n):
                        rval(et)
                return None
            raise ValueError(t)

        try:
            for _ in range(nkv):
                key = rstr()
                t, = struct.unpack("<I", f.read(4))
                v = rval(t)
                if key == "general.architecture":
                    info["arch"] = v
                elif key.endswith(".expert_count"):
                    info["experts"] = v
                elif key.endswith(".expert_used_count"):
                    info["experts_used"] = v
                elif key.endswith(".block_count"):
                    info["blocks"] = v
                if key.startswith("tokenizer."):
                    break
        except (struct.error, ValueError, OSError):
            pass
    return info


def shard_files(path):
    """All shards of a split GGUF given the first one (…-00001-of-0000N.gguf), else [path]."""
    m = re.match(r"(.*)-(\d{5})-of-(\d{5})\.gguf$", path)
    if not m:
        return [path]
    n = int(m[3])
    return [f"{m[1]}-{i:05d}-of-{m[3]}.gguf" for i in range(1, n + 1)]


def files_size(paths):
    return sum(os.path.getsize(p) for p in paths if os.path.exists(p))


# ----------------------------------------------------------------------------------------------
# Model resolution
# ----------------------------------------------------------------------------------------------
class Model:
    def __init__(self):
        self.entry = None        # registry entry or None (generic)
        self.key = None          # registry key
        self.path = None         # first shard
        self.draft = None        # draft/head file or None
        self.size = 0            # bytes of all shards
        self.draft_size = 0
        self.info = {}
        self.missing = []        # [(what, repo, include, gib)] that must be downloaded
        self.notes = []


def models_dir(args):
    return os.path.expanduser(args.models_dir)


def find_registry_file(args, entry, fname):
    """Look for a registry file in --models-dir, the cwd, and next to the model override."""
    dirs = [models_dir(args), os.getcwd(), os.path.join(os.getcwd(), "models")]
    if args.model_path:
        dirs.append(os.path.dirname(os.path.abspath(args.model_path)))
    for d in dirs:
        for cand in (os.path.join(d, fname), os.path.join(d, os.path.basename(fname))):
            if os.path.exists(cand):
                return cand
    return None


def resolve_model(args):
    m = Model()
    spec = args.model
    key = ALIASES.get(spec.lower(), spec.lower())
    if key in REGISTRY:
        m.key, m.entry = key, REGISTRY[key]
        # --model-path overrides the registry file (e.g. the Q2_0 build); --draft overrides the head
    elif os.path.exists(os.path.expanduser(spec)):
        m.path = os.path.abspath(os.path.expanduser(spec))
        for k, e in REGISTRY.items():
            if e["match"].search(os.path.basename(m.path)):
                m.key, m.entry = k, e
                m.notes.append(f"file name matches the registry entry '{k}'")
    else:
        sys.exit(f"tandem-run: '{spec}' is neither a registry name ({', '.join(REGISTRY)}) nor an existing file")
    if args.model_path:
        m.path = os.path.abspath(os.path.expanduser(args.model_path))
    if m.entry:
        e = m.entry
        if not m.path:
            m.path = find_registry_file(args, e, e["model_file"])
        if not m.path:
            m.missing.append(("model", e["model_repo"], e["model_include"], e["model_gib"]))
            m.path = os.path.join(models_dir(args), e["model_file"])
        if args.no_draft:
            m.draft = None
        elif args.draft:
            m.draft = os.path.abspath(os.path.expanduser(args.draft))
        else:
            m.draft = find_registry_file(args, e, e["draft_file"])
            if not m.draft:
                m.missing.append(("draft", e["draft_repo"], e["draft_include"], e["draft_gib"]))
                m.draft = os.path.join(models_dir(args), e["draft_file"])
    else:
        if args.draft and not args.no_draft:
            m.draft = os.path.abspath(os.path.expanduser(args.draft))
    shards = shard_files(m.path)
    if os.path.exists(m.path):
        m.size = files_size(shards)
        m.info = gguf_info(m.path)
    elif m.entry:
        m.size = int(m.entry["model_gib"] * GiB)
    if m.draft:
        m.draft_size = os.path.getsize(m.draft) if os.path.exists(m.draft) else int(m.entry["draft_gib"] * GiB)
    return m


def offer_downloads(m, hw, args):
    if not m.missing:
        return
    tot = sum(x[3] for x in m.missing)
    say("Missing files:")
    for what, repo, inc, gib in m.missing:
        say(f"  {what}: hf download {repo} --include '{inc}' --local-dir {models_dir(args)}   (~{gib:g} GiB)")
    free = hw.disk_free_gib
    if free is not None and free < tot + 2:
        sys.exit(f"tandem-run: need ~{tot:g} GiB but only {free:.0f} GiB is free in {models_dir(args)}. "
                 f"Free some space or pass --model-path / --models-dir.")
    if args.dry_run:
        say("  (dry run: not downloading)")
        return
    if not shutil.which("hf") and not shutil.which("huggingface-cli"):
        sys.exit("tandem-run: the 'hf' tool is not installed. Run:  pip install -U huggingface_hub[cli]  and retry, "
                 "or download the files above yourself and pass --model-path / --draft.")
    if not args.yes:
        if not sys.stdin.isatty():
            sys.exit("tandem-run: download needed; rerun with --yes to accept (or interactively).")
        if input(f"Download ~{tot:g} GiB now? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("tandem-run: not downloading; nothing to run.")
    os.makedirs(models_dir(args), exist_ok=True)
    tool = shutil.which("hf") or shutil.which("huggingface-cli")
    for what, repo, inc, gib in m.missing:
        r = subprocess.run([tool, "download", repo, "--include", inc, "--local-dir", models_dir(args)])
        if r.returncode:
            sys.exit(f"tandem-run: download of {repo} failed")
    m.missing = []
    if m.entry:   # re-resolve sizes now that the files exist
        m.size = files_size(shard_files(m.path))
        m.info = gguf_info(m.path)
        if m.draft and os.path.exists(m.draft):
            m.draft_size = os.path.getsize(m.draft)


# ----------------------------------------------------------------------------------------------
# Decision rules. Every choice is appended to plan.reasons as (flag, reason).
# ----------------------------------------------------------------------------------------------
class Plan:
    def __init__(self):
        self.args = []       # llama-server arguments after the binary
        self.env = {}        # environment additions
        self.reasons = []    # (what, why)
        self.warnings = []
        self.notes = []
        self.draft_n = None  # the candidate that calibration may vary
        self.draft_candidates = []

    def add(self, flags, why):
        flags = shlex.split(flags) if isinstance(flags, str) else flags
        self.args += flags
        self.reasons.append((" ".join(shlex.quote(x) for x in flags), why))

    def set_env(self, k, v, why):
        self.env[k] = v
        self.reasons.append((f"{k}={v}", why))


def draft_rule_qwen(hw):
    if hw.vram_gib <= 24.5 or hw.cores <= 10:
        return 3, "cards <= 24 GB or CPUs <= 10 cores"
    return 4, "48 GB-class card and more than 10 cores"


def choose_flags(hw, m, args, calib=None):
    p = Plan()
    p.build = getattr(args, "build", "unknown")
    ram, vram, cores = hw.ram_gib, hw.vram_gib, hw.cores
    size_gib = m.size / GiB
    is_moe = (m.info.get("experts") or 0) > 1 if m.info else (m.entry is not None)
    if not m.info and not m.entry:
        p.warnings.append("could not read the GGUF header; assuming a MoE model")
        is_moe = True

    p.add(["-m", m.path], "model" + (f" ({m.entry['title']})" if m.entry else
                                     f" (generic rules, no registry entry; arch {m.info.get('arch', '?')}"
                                     f"{', %d experts' % m.info['experts'] if m.info.get('experts') else ''})"))
    p.add("-ngl 99", "all layers on the GPU; the expert cache does the placement")
    kv_gib = 0.7 * args.ctx / 16384
    fits = size_gib + m.draft_size / GiB + kv_gib + 2 < vram
    if not is_moe:
        p.warnings.append("this does not look like a MoE model; tandem.cpp only helps MoE. Running plain llama-server flags.")
    elif fits:
        p.reasons.append(("(no -cmoe)", f"the {size_gib:.0f} GiB model fits in {vram:.0f} GiB of VRAM; no expert cache needed"))
    else:
        p.add("-cmoe --moe-cache-mib auto", "experts stay in RAM; leftover VRAM becomes the expert cache")
    p.add("-np 1", "one conversation (default would open 4 slots sharing a small context)")
    p.add(f"-c {args.ctx}", "context" + ("" if args.ctx_given else " (default 16384; KV for Qwen3.8 is ~0.7 GiB per 16k tokens)"))

    # load mode
    if ram >= size_gib + 12:
        p.add("-lm none", f"RAM {ram:.0f} GiB >= model {size_gib:.0f} + 12 GiB: read the weights into RAM")
    else:
        p.reasons.append(("(no -lm none)", f"RAM {ram:.0f} GiB < model {size_gib:.0f} + 12 GiB: file stays mapped"))
    if ram < size_gib + 8:
        p.add("--cache-ram 0", f"RAM {ram:.0f} GiB < model {size_gib:.0f} + 8 GiB: the 8 GiB prompt cache would evict experts")
    build = getattr(args, "build", "unknown")
    if ram < size_gib * 0.6:
        p.warnings.append(f"RAM ({ram:.0f} GiB) is much smaller than the model ({size_gib:.0f} GiB): most experts are streamed from "
                          "the SSD, so the drive sets the speed (DeepSeek-V4.1 on 64 GB: ~12 tok/s from a PCIe 4.0 drive, ~8 from a "
                          "DRAM-less one).")
    elif ram < size_gib + 8:
        p.notes.append("the model is larger than RAM: experts are read from the SSD, speed depends on the SSD; "
                       "the first requests are slower while the cache warms")
    kv = re.match(r"(\d+)\.(\d+)", hw.kernel or "")
    if ram < size_gib + 8 and kv and (int(kv[1]), int(kv[2])) < (6, 1):
        p.notes.append("older kernels reclaim mapped model pages poorly; expect slow loads below model size + 8 GiB of RAM")
    if ram < size_gib + 8 and build == "old":
        p.warnings.append("this build predates the low-RAM fixes; expect very slow loads below model + 8 GiB of RAM; update tandem.cpp")

    # container / emulated RAM limits: builds before the low-RAM fixes look at physical RAM, not the cgroup limit.
    # Newer builds read the cgroup limit themselves, so the overrides are only set for old/unknown builds.
    limited = ram < hw.ram_total_gib * 0.95
    if limited and build != "new":
        if ram < size_gib + 10:
            p.set_env("LLAMA_MOE_PIN_EXPS", "0", "older builds only (newer ones read the cgroup limit): RAM limit is below the model + 10 GiB")
        if ram < size_gib + 8:
            p.set_env("LLAMA_PLE_GPU_COPY", "0", "older builds only (newer ones read the cgroup limit): RAM limit is below the model + 8 GiB")

    # speculative decoding
    kind = m.entry["kind"] if m.entry else None
    if m.draft and kind == "qwen38-mtp":
        n, why = draft_rule_qwen(hw)
        if calib and calib.get("draft_n"):
            n, why = calib["draft_n"], "from calibration (%s)" % calib.get("date", "?")
        p.set_env("LLAMA_MTP_DRAFT_VOCAB", "100000", "MTP head draws from the 100k most common tokens (cheaper output matmul)")
        p.add(["--spec-type", "draft-mtp", "-md", m.draft, "--spec-draft-sampling", "probabilistic"],
              "MTP head: ~3x decode; probabilistic draft sampling keeps sampled output exact")
        p.add(f"--spec-draft-n-max {n}", f"{why}")
        p.add("-bs", "backend sampling (needed with the MTP head)")
        p.add(["-ot", r"^token_embd\.weight=CUDA0"], "keep the token embedding on the GPU")
        p.draft_n = n
        p.draft_candidates = sorted({max(2, n - 1), n, n + 1}) if args.calibrate_drafts else [n]
    elif m.draft and kind == "gptoss-eagle3":
        if cores >= 10:
            n, nwhy = (3, "3 draft tokens on cards <= 24 GB (measured +2-3% over 4)") if hw.vram_gib <= 24.5 else (4, "4 draft tokens")
            if calib and calib.get("draft_n"):
                n, nwhy = calib["draft_n"], "from calibration"
            p.add(["--spec-type", "draft-eagle3", "-md", m.draft], f"EAGLE3 draft: {cores} cores >= 10 so it pays off")
            p.add(f"--spec-draft-n-max {n}", nwhy)
            p.draft_n = n
            p.draft_candidates = sorted({max(2, n - 1), n, n + 1}) if args.calibrate_drafts else [n]
        else:
            p.reasons.append(("(no EAGLE3)", f"only {cores} cores: EAGLE3 makes verification cost more CPU than it saves (slower)"))
    elif m.entry and not m.draft:
        p.reasons.append(("(no draft)", "draft disabled or unavailable"))

    # a draft model's VRAM is added to the margin by the server; emulating a smaller card keeps the difference unused
    if "vram" in hw.emulated:
        diff = int((hw.real["vram_gib"] - vram) * 1024)
        if diff > 0:
            p.add(f"--moe-cache-margin-mib {diff + 1024}",
                  f"emulating a {vram:.0f} GiB card on a {hw.real['vram_gib']:.0f} GiB one: keep {diff} MiB unused + the default 1024")
    if "cores" in hw.emulated and cores < hw.real["cores"]:
        p.set_env("LLAMA_MOE_CPU_THREADS", str(max(1, cores - 1)), f"emulating {cores} cores: server default is cores-1")
        p.add(f"-t {cores} -tb {cores}", f"emulating {cores} cores: the server sizes its thread pool from the machine's cores, not the affinity mask (oversubscribed spinning threads are pathologically slow)")

    if args.fast:
        p.set_env("LLAMA_MOE_TAIL_SKIP", "7",
                  "APPROXIMATE (--fast): skips low-ranked missed experts; quality number: TODO(main session)")
    p.add(["--port", str(args.port), "--host", args.host], "listen address")
    if args.extra:
        p.add(shlex.split(args.extra), "--extra")
    return p


def build_command(hw, args, plan):
    """Wrapper + env for emulated limits, then the server command. Returns (argv, env)."""
    env = dict(os.environ)
    for k in list(env):          # stray tuning variables from the shell would make results irreproducible
        if k.startswith(("LLAMA_MOE", "LLAMA_MTP", "GGML_CUDA", "LLAMA_GRAPH", "LLAMA_PLE")) and k not in plan.env:
            del env[k]
    env.update(plan.env)
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = str(hw.gpu_index)
    argv = [args.server_bin, *plan.args]
    wrap = []
    if "ram" in hw.emulated and hw.ram_gib < hw.real["ram_gib"] and not args.no_ram_cap:
        wrap += ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={int(hw.ram_gib)}G"]  # no MemorySwapMax=0: a load-time anonymous peak gets OOM-killed without swap; real PCs have swap
    if "cores" in hw.emulated and hw.cores < hw.real["cores"]:
        # physical cores 0..n-1 map to hardware threads 0..n-1 and n_total/2+... on SMT boxes; take both siblings
        wrap += ["taskset", "-c", f"0-{hw.cores - 1}"]   # amd numbering: cpus 0..15 are distinct physical cores
    return wrap + argv, env


def print_plan(hw, m, plan, argv, env, calib_state):
    say("== Hardware ==")
    ram = f"{hw.ram_gib:.0f} GiB" + (f" (cgroup limit; MemTotal {hw.ram_total_gib:.0f})" if hw.ram_cgroup_gib and hw.ram_cgroup_gib < hw.ram_total_gib else "")
    say(f"  GPU    {hw.gpu} #{hw.gpu_index}, {hw.vram_gib:.0f} GiB, sm_{hw.cc.replace('.', '')}, PCIe gen{hw.pcie_gen} x{hw.pcie_width}"
        f"{'  [emulated VRAM; real %.0f GiB]' % hw.real['vram_gib'] if 'vram' in hw.emulated else ''}")
    say(f"  CPU    {hw.cores} physical cores ({hw.cpu}){'  [emulated]' if 'cores' in hw.emulated else ''}")
    say(f"  RAM    {ram}{'  [emulated]' if 'ram' in hw.emulated else ''}")
    say(f"  disk   {hw.disk_free_gib:.0f} GiB free" if hw.disk_free_gib is not None else "  disk   ?")
    say(f"  kernel {hw.kernel}")
    say("== Model ==")
    say(f"  {m.entry['title'] if m.entry else 'generic MoE rules (not in the registry)'}")
    say(f"  {m.path}  ({m.size / GiB:.1f} GiB{'' if os.path.exists(m.path) else ', not downloaded'})")
    if m.draft:
        say(f"  draft: {m.draft}  ({m.draft_size / GiB:.1f} GiB)")
    say(f"  server build: {getattr(plan, 'build', '?')}")
    say("== Plan ==")
    for what, why in plan.reasons:
        say(f"  {what:<48} {why}")
    for n in plan.notes:
        say(f"  note: {n}")
    for w in plan.warnings:
        say(f"  WARNING: {w}")
    say(f"== Calibration: {calib_state} ==")
    say("== Command ==")
    envs = " ".join(f"{k}={shlex.quote(v)}" for k, v in sorted(env.items())
                    if k in plan.env or k in ("CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER"))
    say("  " + envs + " " + " ".join(shlex.quote(a) for a in argv))


# ----------------------------------------------------------------------------------------------
# Calibration cache
# ----------------------------------------------------------------------------------------------
def calib_key(hw, m, args):
    parts = [hw.gpu, str(hw.real["vram_gib"] if not hw.emulated else hw.vram_gib), f"{hw.ram_gib:.0f}", str(hw.cores), str(hw.pcie_gen),
             m.path and os.path.basename(m.path), str(m.size), os.path.basename(m.draft or ""), str(m.draft_size),
             args.server_bin and f"{os.path.getsize(args.server_bin) if os.path.exists(args.server_bin) else 0}:"
                                 f"{int(os.path.getmtime(args.server_bin)) if os.path.exists(args.server_bin) else 0}",
             str(args.ctx), "fast" if args.fast else ""]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def load_calib(key):
    try:
        return json.load(open(os.path.join(CACHE_DIR, key + ".json")))
    except (OSError, ValueError):
        return None


def save_calib(key, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(data, open(os.path.join(CACHE_DIR, key + ".json"), "w"), indent=1)


CAL_PROMPTS = [
    "Explain how a hash table handles collisions, in about 150 words.",
    "Write a Python function that merges two sorted lists, then explain its complexity.",
    "Describe the main causes of the French Revolution.",
]


def measure(port, n_tokens=200):
    """Greedy decode tok/s over the fixed prompts (timed after the first token, so prompt processing is excluded)."""
    rates = []
    for pr in CAL_PROMPTS:
        body = json.dumps({"model": "m", "messages": [{"role": "user", "content": pr}], "max_tokens": n_tokens,
                           "temperature": 0, "stream": True, "ignore_eos": True,
                           "chat_template_kwargs": {"enable_thinking": False},
                           "stream_options": {"include_usage": True}}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        first = last = None
        usage = None
        with urllib.request.urlopen(req, timeout=600) as r:
            for line in r:
                if not line.startswith(b"data: ") or line.strip() == b"data: [DONE]":
                    continue
                ev = json.loads(line[6:])
                usage = ev.get("usage") or usage
                for ch in ev.get("choices", []):
                    d = ch.get("delta", {})
                    if d.get("content") or d.get("reasoning_content"):
                        last = time.perf_counter()
                        first = first or last
        n = (usage or {}).get("completion_tokens", 0)
        if first and last and last > first and n > 1:
            rates.append((n - 1) / (last - first))
    return sum(rates) / len(rates) if rates else 0.0


def wait_ready(proc, port, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        try:
            if b"ok" in urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).read():
                return True
        except Exception:
            time.sleep(2)
    return False


def stop_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(60)
    except (ProcessLookupError, PermissionError):
        pass
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)


def start_server(argv, env, log_path):
    return subprocess.Popen(argv, env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT, start_new_session=True)


def calibrate(hw, m, args, plan, env_argv_fn):
    """Boot once with the rule's choice, measure; try neighbouring draft counts (each needs a restart: this build
    ignores per-request speculative.n_max) only while budget remains. Returns a calibration dict."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    log = os.path.join(CACHE_DIR, "calibration.server.log")
    results = {}
    t_start = time.time()
    # search: the rule's n, then climb (n+1, n+2, ...) while each step wins by >= 3%; if n+1 is not 3% better, try n-1 once,
    # but only with an explicit --calibrate (it costs one more restart, beyond the first-run budget)
    queue, tried, n_max_try = [plan.draft_n], set(), (plan.draft_n or 0) + 2   # >3 tokens may need a bigger margin (README)
    while queue:
        n = queue.pop(0)
        if n in tried or n > n_max_try or (n is not None and n < 2):
            continue
        tried.add(n)
        if len(tried) > 1 and time.time() - t_start > args.calib_budget_s:
            say(f"calibration: budget of {args.calib_budget_s}s spent, stopping")
            break
        pl = choose_flags(hw, m, args, calib={"draft_n": n} if n else None)
        argv, env = env_argv_fn(pl)
        say(f"calibration: starting server" + (f" with draft n_max={n}" if n else ""))
        proc = start_server(argv, env, log)
        try:
            if not wait_ready(proc, args.port):
                say(f"calibration: server failed to start, see {log}")
                break
            measure(args.port, 64)           # warm-up (graphs, caches)
            tps = measure(args.port)
            say(f"calibration: n_max={n}: {tps:.1f} tok/s")
            results[n if n else 0] = tps
        finally:
            stop_group(proc)
        if n is None or n not in results:
            continue
        base = results[plan.draft_n]
        if n == plan.draft_n:
            queue.append(n + 1)
        elif n > plan.draft_n:
            prev = results.get(n - 1, 0)
            if results[n] >= prev * 1.03:
                queue.append(n + 1)
            elif n == plan.draft_n + 1 and args.calibrate:
                queue.append(plan.draft_n - 1)
    if not results:
        return None
    best = max(results, key=results.get)
    if plan.draft_n in results and results[best] < results[plan.draft_n] * 1.02:
        best = plan.draft_n          # inside noise: keep the rule's choice
    return {"draft_n": best or None, "tok_s": results, "date": time.strftime("%Y-%m-%d"), "gpu": hw.gpu,
            "elapsed_s": round(time.time() - t_start)}


# ----------------------------------------------------------------------------------------------
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="registry name (%s) or a path to a .gguf" % ", ".join(REGISTRY))
    ap.add_argument("--model-path", help="local file for a registry entry (e.g. your own quant)")
    ap.add_argument("--draft", help="draft/MTP/EAGLE3 file (overrides the registry's)")
    ap.add_argument("--no-draft", action="store_true", help="no speculative decoding")
    ap.add_argument("--models-dir", default="~/tandem-models", help="where downloads go and registry files are looked up")
    ap.add_argument("--server-bin", default=os.environ.get("TANDEM_SERVER") or shutil.which("llama-server") or "./tandem/build/bin/llama-server")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--ctx", type=int, default=None, help="total context (default 16384)")
    ap.add_argument("--gpu", type=int, default=0, help="GPU index (PCI bus order)")
    ap.add_argument("--fast", action="store_true", help="APPROXIMATE mode: LLAMA_MOE_TAIL_SKIP=7 (faster, not exact)")
    ap.add_argument("--calibrate", action="store_true", help="redo calibration even if cached")
    ap.add_argument("--no-calibrate", action="store_true", help="never calibrate; use the rules")
    ap.add_argument("--calibrate-drafts", action="store_true", default=True, help=argparse.SUPPRESS)
    ap.add_argument("--calib-budget-s", type=int, default=420, help="stop trying extra candidates after this many seconds")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; start nothing, download nothing")
    ap.add_argument("--yes", action="store_true", help="accept downloads without asking")
    ap.add_argument("--extra", default="", help="extra llama-server flags (shlex-split), appended last")
    ap.add_argument("--assume-vram-gib", type=float)
    ap.add_argument("--assume-ram-gib", type=float)
    ap.add_argument("--assume-cores", type=int)
    ap.add_argument("--no-ram-cap", action="store_true", help=argparse.SUPPRESS)   # bench: assume RAM for the rules, but no cgroup cap
    ap.add_argument("--fake-build", choices=["new", "old", "unknown"], help=argparse.SUPPRESS)
    ap.add_argument("--fake-hw", help=argparse.SUPPRESS)   # tests: JSON with gpu/vram_gib/cores/ram_gib/pcie_gen/...
    a = ap.parse_args(argv)
    a.ctx_given = a.ctx is not None
    a.ctx = a.ctx or 16384
    if a.model.startswith("~") or os.path.sep in a.model:
        a.model_arg_is_path = True
    return a


def build_state(server_bin):
    """'new' if libllama.so next to the server has the low-RAM fixes ("switched by the page fault rate"), 'old' if not,
    'unknown' if no library/binary can be read."""
    d = os.path.dirname(os.path.realpath(server_bin)) if os.path.exists(server_bin) else None
    if not d:
        return "unknown"
    cands = sorted(glob.glob(os.path.join(d, "libllama.so*"))) + [os.path.realpath(server_bin)]
    needle = b"switched by the page fault rate"
    seen = False
    for c in cands:
        try:
            with open(c, "rb") as f:
                tail = b""
                while True:
                    buf = f.read(16 << 20)
                    if not buf:
                        break
                    if needle in tail + buf:
                        return "new"
                    tail = buf[-len(needle):]
            seen = seen or "libllama" in c
        except OSError:
            pass
    return "old" if seen else "unknown"


def make_plan(args):
    """Everything up to (not including) starting a server; the unit tests call this."""
    if args.fake_hw:
        d = json.loads(args.fake_hw)
        hw = HW(gpu=d.get("gpu", "Fake GPU"), gpu_index=d.get("gpu_index", 0), n_gpus=1, vram_gib=d["vram_gib"],
                vram_mib=d["vram_gib"] * 1024, cc=d.get("cc", "8.9"), pcie_gen=d.get("pcie_gen", 4), pcie_width=16,
                cores=d["cores"], cpu=d.get("cpu", "fake CPU"), ram_total_gib=d["ram_gib"],
                ram_cgroup_gib=d.get("ram_cgroup_gib"), ram_gib=d["ram_gib"], disk_free_gib=d.get("disk_free_gib", 500),
                kernel=d.get("kernel", "6.8.0"))
        if hw.ram_cgroup_gib:
            hw["ram_gib"] = min(hw.ram_total_gib, hw.ram_cgroup_gib)
        hw["real"] = {k: hw[k] for k in ("vram_gib", "ram_gib", "cores")}
        hw["emulated"] = []
    else:
        hw = detect(args, os.path.dirname(os.path.expanduser(args.models_dir)) or ".")
    m = resolve_model(args)
    args.build = args.fake_build or build_state(args.server_bin)
    return hw, m


def main(argv=None):
    args = parse_args(argv)
    hw, m = make_plan(args)
    if args.assume_vram_gib is not None or args.assume_ram_gib is not None or args.assume_cores is not None:
        if args.fake_hw:     # apply the same overrides on fake hardware
            for flag, key in (("assume_vram_gib", "vram_gib"), ("assume_ram_gib", "ram_gib"), ("assume_cores", "cores")):
                if getattr(args, flag) is not None:
                    hw["emulated"].append(key.split("_")[0])
                    hw[key] = getattr(args, flag)
    key = calib_key(hw, m, args)
    calib = None if (args.calibrate or args.no_calibrate) else load_calib(key)
    plan = choose_flags(hw, m, args, calib)
    state = ("disabled (--no-calibrate)" if args.no_calibrate else
             f"cached ({calib['date']}, key {key}): draft n_max={calib.get('draft_n')}" if calib else
             f"will run on first start (key {key})" if plan.draft_n else
             "nothing to calibrate for this plan (no switchable candidates)")
    mk = lambda pl: build_command(hw, args, pl)
    argv_, env = mk(plan)
    print_plan(hw, m, plan, argv_, env, state)
    if args.dry_run:
        return 0
    offer_downloads(m, hw, args)
    if not os.path.exists(args.server_bin):
        sys.exit(f"tandem-run: llama-server not found at {args.server_bin}; build it (build.sh) or pass --server-bin")
    if not args.no_calibrate and (args.calibrate or (calib is None and plan.draft_n)):
        say("== Calibrating (one-off per machine+model; ~ a few model loads) ==")
        res = calibrate(hw, m, args, plan, mk)
        if res:
            save_calib(key, res)
            say(f"calibration saved to {CACHE_DIR}/{key}.json: best draft n_max={res['draft_n']}")
            plan = choose_flags(hw, m, args, res)
            argv_, env = mk(plan)
    say("== Launching ==")
    say(f"URL: http://{args.host if args.host != '0.0.0.0' else '127.0.0.1'}:{args.port}/   (OpenAI API at /v1)")
    say("Command: " + " ".join(f"{k}={shlex.quote(v)}" for k, v in sorted(plan.env.items())) + " " + " ".join(map(shlex.quote, argv_)))
    proc = subprocess.Popen(argv_, env=env, start_new_session=True)
    fwd = lambda s, f: os.killpg(proc.pid, signal.SIGTERM)
    signal.signal(signal.SIGINT, fwd)
    signal.signal(signal.SIGTERM, fwd)
    return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
