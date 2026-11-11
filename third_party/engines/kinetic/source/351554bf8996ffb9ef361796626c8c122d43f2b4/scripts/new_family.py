#!/usr/bin/env python3
"""Starts a new model family from a GGUF file.

Prints the file's architecture, its `<arch>.*` metadata and the tensors of
one layer, writes crates/kinetic-models/src/arch/<name>.rs as a Llama-style
starter that builds, and adds it to the family list. What is left is
mapping the tensors onto blocks; see docs/src/adding-a-family.md.

    python scripts/new_family.py model.gguf
    python scripts/new_family.py model.gguf --dry-run

Standard library only; reads the header, never the weights.
"""

import argparse
import os
import re
import struct
import sys

ARCH_DIR = os.path.join("crates", "kinetic-models", "src", "arch")

# GGUF value types, see the GGUF spec in ggml's docs/gguf.md
SCALARS = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?",
           10: "<Q", 11: "<q", 12: "<d"}
STRING, ARRAY = 8, 9


class Reader:
    def __init__(self, f):
        self.f = f

    def unpack(self, fmt):
        return struct.unpack(fmt, self.f.read(struct.calcsize(fmt)))[0]

    def string(self):
        return self.f.read(self.unpack("<Q")).decode("utf-8", "replace")

    def value(self, ty):
        if ty == STRING:
            return self.string()
        if ty == ARRAY:
            inner, n = self.unpack("<I"), self.unpack("<Q")
            items = [self.value(inner) for _ in range(n)]
            return items if n <= 64 else f"[{n} items]"
        return self.unpack(SCALARS[ty])


def read_header(path):
    with open(path, "rb") as f:
        r = Reader(f)
        if f.read(4) != b"GGUF":
            sys.exit(f"{path} is not a GGUF file")
        version = r.unpack("<I")
        if version < 2:
            sys.exit(f"GGUF version {version} is too old")
        n_tensors, n_kv = r.unpack("<Q"), r.unpack("<Q")
        meta = {}
        for _ in range(n_kv):
            key = r.string()
            meta[key] = r.value(r.unpack("<I"))
        tensors = []
        for _ in range(n_tensors):
            name = r.string()
            dims = [r.unpack("<Q") for _ in range(r.unpack("<I"))]
            r.unpack("<I")
            r.unpack("<Q")
            tensors.append((name, dims))
        return meta, tensors


TEMPLATE = '''//! {title}: TODO one or two lines on what its layers compute.

use super::Family;
use crate::blocks::{{Attention, Gate, Mixer, Rope, RopeLayout, SharedKv}};
use crate::loader::Loader;
use crate::model::Layer;
use crate::LoadError;

pub(crate) const FAMILY: Family =
    Family::decoder(&["{arch}"], |l, b| Ok(layers(l, b.d, b.eps)?.into()));

// starts as a Llama-style transformer: map every tensor of `blk.N` onto a block
pub(crate) fn layers<'a>(l: &Loader<'a>, d: usize, eps: f32) -> Result<Vec<Layer<'a>>, LoadError> {{
    let n_layer = l.usize("block_count")?;
    let n_head = l.usize("attention.head_count")?;
    let n_head_kv = l.usize_or("attention.head_count_kv", n_head)?;
    let head_dim = l.usize_or("attention.key_length", d / n_head)?;
    let n_ff = l.usize("feed_forward_length")?;
    let rope_dims = l.usize_or("rope.dimension_count", head_dim)?;
    let base = l.f32_or("rope.freq_base", 10_000.0)?;
    (0..n_layer)
        .map(|i| {{
            let t = |s: &str| format!("blk.{{i}}.{{s}}");
            let (q_dim, kv_dim) = (n_head * head_dim, n_head_kv * head_dim);
            let attention = Attention {{
                folding: None,
                q: l.matrix(&t("attn_q.weight"), d, q_dim)?,
                k: l.matrix(&t("attn_k.weight"), d, kv_dim)?,
                v: l.matrix(&t("attn_v.weight"), d, kv_dim)?,
                o: l.matrix(&t("attn_output.weight"), q_dim, d)?,
                gate: Gate::None,
                q_bias: None,
                k_bias: None,
                v_bias: None,
                q_norm: None,
                k_norm: None,
                norm_after_rope: false,
                n_head,
                n_head_kv,
                head_dim,
                rope: Rope {{
                    dims: rope_dims,
                    base,
                    factors: None,
                    layout: RopeLayout::Neox,
                    mscale: 1.0,
                }},
                window: None,
                scale: None,
                v_norm: None,
                shared_kv: SharedKv::No,
                eps,
            }};
            Ok(Layer {{
                mixer_norm: Some(l.vector(&t("attn_norm.weight"), d)?),
                mixer: Mixer::Attention(attention),
                mixer_out_norm: None,
                ffn_norm: Some(l.vector(&t("ffn_norm.weight"), d)?),
                ffn: Some(l.swiglu(i, d, n_ff)?),
                experts: None,
                ffn_out_norm: None,
                residual_scale: None,
            }})
        }})
        .collect()
}}
'''


def module_name(arch):
    name = re.sub(r"[^0-9a-z]+", "_", arch.lower()).strip("_")
    return name if name and not name[0].isdigit() else f"arch_{name}"


def register(mod_rs, module):
    text = open(mod_rs, encoding="utf-8").read()
    mods = re.findall(r"^(?:pub\(crate\) )?mod (\w+);$", text, re.M)
    if module in mods:
        sys.exit(f"arch/mod.rs already has a module {module}")
    line = f"pub(crate) mod {module};\n"
    after = [m for m in mods if m < module]
    if after:
        anchor = re.search(rf"^(?:pub\(crate\) )?mod {after[-1]};\n", text, re.M)
        text = text[:anchor.end()] + line + text[anchor.end():]
    else:
        text = line + text
    head, sep, tail = text.partition("pub(crate) const FAMILIES: &[Family] = &[\n")
    if not sep:
        sys.exit("FAMILIES not found in arch/mod.rs")
    body, end, rest = tail.partition("];")
    text = head + sep + body + f"    {module}::FAMILY,\n" + end + rest
    with open(mod_rs, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("gguf")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry-run", action="store_true", help="print, write nothing")
    a = ap.parse_args()

    meta, tensors = read_header(a.gguf)
    arch = meta.get("general.architecture")
    if not isinstance(arch, str):
        sys.exit("the file does not name its architecture")
    print(f"architecture  {arch}")
    print("metadata")
    for key, value in meta.items():
        if key.startswith(arch + "."):
            print(f"  {key[len(arch) + 1:]:40} {value}")
    print("tensors outside the layers")
    for name, dims in tensors:
        if not name.startswith("blk."):
            print(f"  {name:40} {dims}")
    print("tensors of layer 0")
    for name, dims in tensors:
        if name.startswith("blk.0."):
            print(f"  {name:40} {dims}")

    arch_dir = os.path.join(a.repo, ARCH_DIR)
    known = set()
    for f in os.listdir(arch_dir):
        if f.endswith(".rs"):
            text = open(os.path.join(arch_dir, f), encoding="utf-8").read()
            known.update(re.findall(r'"([\w.-]+)"', " ".join(re.findall(r"&\[[^\]]*\]", text))))
    if arch in known:
        sys.exit(f"{arch} is already a registered family")
    module = module_name(arch)
    path = os.path.join(arch_dir, module + ".rs")
    if os.path.exists(path):
        sys.exit(f"{path} exists")
    if a.dry_run:
        print(f"would write {path} and register {module}::FAMILY")
        return
    title = meta.get("general.basename") or arch
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(TEMPLATE.format(arch=arch, title=title))
    register(os.path.join(arch_dir, "mod.rs"), module)
    print(f"wrote {os.path.relpath(path, a.repo)} and added {module}::FAMILY to arch/mod.rs")
    print("next: map the tensors above onto blocks, then run scripts/conformance.py")


if __name__ == "__main__":
    main()
