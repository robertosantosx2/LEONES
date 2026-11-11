#!/usr/bin/env python3
"""Writes the llama.cpp flag table of the docs from crates/kinetic-cli/src/llama_flags.rs.

    python scripts/llama_flags_doc.py            # rewrite docs/src/llama-flags-table.md
    python scripts/llama_flags_doc.py --check    # fail if it is out of date
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "crates/kinetic-cli/src/llama_flags.rs"
TABLE = ROOT / "docs/src/llama-flags-table.md"


def const_body(src, name):
    # inner lists end in `],`, so the first `];` closes the constant
    m = re.search(rf"const {name}: [^=]+= &\[(.*?)\];", src, re.S)
    if not m:
        sys.exit(f"{SOURCE.name}: no const {name}")
    return m.group(1)


def strings(text):
    return re.findall(r'"((?:[^"\\]|\\.)*)"', text)


def flags(names):
    return ", ".join(f"`{n}`" for n in names)


def prose(why):
    """The reason as markdown: commands in code spans, `<` escaped elsewhere."""
    if "`" not in why:
        why = re.sub(r"(kinetic (?:run|chat|serve) .*)$", r"`\1`", why)
        why = re.sub(r"(^-t\b|--device$)", r"`\1`", why)
    parts = why.split("`")
    parts[::2] = [p.replace("<", "&lt;") for p in parts[::2]]
    return "`".join(parts)


def table(src):
    rows = []
    renamed = strings(const_body(src, "RENAMED"))
    for old, new in zip(renamed[::2], renamed[1::2]):
        rows.append((flags([old]), f"works, as `{new}`"))
    gpu = strings(const_body(src, "GPU_LAYERS"))
    rows.append((flags(gpu), "works: `0` means `--device cpu`, any other number `--device cuda`, `all` as many as fit"))
    ignored = [n for c in ("FLASH_ATTN", "IGNORED_SWITCHES", "IGNORED_WITH_VALUE") for n in strings(const_body(src, c))]
    rows.append((flags(ignored), "accepted and not needed: Kinetic does this by itself"))
    entries = re.findall(r'\(\s*&\[(.*?)\],\s*("(?:[^"\\]|\\.)*")', const_body(src, "UNSUPPORTED"), re.S)
    for names, why in entries:
        rows.append((flags(strings(names)), prose(strings(why)[0])))
    out = ["| llama.cpp flag | In Kinetic |", "|---|---|"]
    out += [f"| {a} | {b} |" for a, b in rows]
    return "\n".join(out) + "\n"


def main():
    text = table(SOURCE.read_text(encoding="utf-8"))
    if "--check" in sys.argv[1:]:
        if TABLE.read_text(encoding="utf-8") != text:
            sys.exit(f"{TABLE.relative_to(ROOT)} is out of date; run scripts/llama_flags_doc.py")
        return
    TABLE.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
