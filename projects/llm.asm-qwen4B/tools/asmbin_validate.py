#!/usr/bin/env python3
"""Strict, read-only validator for the llm.asm ASMBIN v1/v2 layout.

This validates the exact layout emitted by the pinned llm.asm exporter. It
never executes model code and never allocates model-sized buffers. The input
is memory-mapped read-only; all ranges are checked before they are accessed.
"""
from __future__ import annotations

import argparse
import json
import math
import mmap
import os
import struct
import sys
from dataclasses import asdict, dataclass
from typing import BinaryIO

MAGIC = b"ASML"
HEADER_SIZE = 128
TOKENIZER_HEADER_SIZE = 64
HASH_BITS = 19
HASH_SIZE = 1 << HASH_BITS
HASH_MASK = HASH_SIZE - 1
FIB_MULT = 0x9E3779B97F4A7C15
MAX_HASH_PROBES = 1024
EMPTY_RANK = 0xFFFFFFFF
FLAG_TIED_EMB = 1
FLAG_QK_NORM = 2
FLAG_FP16_SCALES = 4
KNOWN_FLAGS = FLAG_TIED_EMB | FLAG_QK_NORM | FLAG_FP16_SCALES
Q8_MAX_K = 16384
U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1
HEADER = struct.Struct("<4s9I2f4I6Q16s")


class ValidationError(ValueError):
    """The file is malformed or incompatible with this ASMBIN implementation."""


def fail(message: str) -> None:
    raise ValidationError(message)


def align64(value: int) -> int:
    if value < 0 or value > U64_MAX - 63:
        fail("64-byte alignment arithmetic overflows uint64")
    return (value + 63) & ~63


def checked_region(offset: int, length: int, file_size: int, label: str) -> None:
    if offset < 0 or length < 0 or offset > file_size:
        fail(f"{label}: offset outside file")
    if length > file_size - offset:
        fail(f"{label}: region extends beyond file")


def checked_product(label: str, *values: int) -> int:
    result = 1
    for value in values:
        if value < 0 or (value and result > U64_MAX // value):
            fail(f"{label} calculation overflows uint64")
        result *= value
    return result


def row_bytes(k: int, version: int) -> int:
    if k <= 0 or k % 32:
        fail(f"Q8_0 K={k} is not a positive multiple of 32")
    if k > Q8_MAX_K:
        fail(f"Q8_0 K={k} exceeds engine Q8_MAX_K={Q8_MAX_K}")
    scale_bytes = 2 if version == 2 else 4
    return k + (k // 32) * scale_bytes


@dataclass(frozen=True)
class Header:
    version: int
    dim: int
    hidden_dim: int
    n_layers: int
    n_heads: int
    n_kv_heads: int
    head_dim: int
    vocab_size: int
    max_seq_len: int
    rms_norm_eps: float
    rope_theta: float
    eos_1: int
    eos_2: int
    ht_mask: int
    flags: int
    off_tokenizer: int
    off_embed: int
    off_layers: int
    layer_stride: int
    off_final_norm: int
    file_size: int


def parse_header(data: memoryview) -> Header:
    if len(data) < HEADER_SIZE:
        fail(f"truncated header: need {HEADER_SIZE} bytes, got {len(data)}")
    fields = HEADER.unpack_from(data, 0)
    (magic, version, dim, hidden_dim, n_layers, n_heads, n_kv_heads,
     head_dim, vocab_size, max_seq_len, eps, theta, eos_1, eos_2,
     ht_mask, flags, off_tok, off_embed, off_layers, layer_stride,
     off_final, declared_size, reserved) = fields
    if magic != MAGIC:
        fail("invalid ASMBIN magic")
    if version not in (1, 2):
        fail(f"unsupported ASMBIN version {version}")
    if flags & ~KNOWN_FLAGS:
        fail(f"unknown header flag bits 0x{flags & ~KNOWN_FLAGS:x}")
    fp16_flag = bool(flags & FLAG_FP16_SCALES)
    if (version == 2) != fp16_flag:
        fail("scale flag is inconsistent with ASMBIN version")
    if not flags & FLAG_QK_NORM:
        fail("QK-Norm flag is required by this inference implementation")
    if not flags & FLAG_TIED_EMB:
        fail("tied embeddings are required by the current ASMBIN layout")
    if any(reserved):
        fail("reserved header bytes must be zero")
    if declared_size != len(data):
        fail(f"header file_size={declared_size} differs from actual size={len(data)}")
    h = Header(version, dim, hidden_dim, n_layers, n_heads, n_kv_heads,
               head_dim, vocab_size, max_seq_len, eps, theta, eos_1, eos_2,
               ht_mask, flags, off_tok, off_embed, off_layers, layer_stride,
               off_final, declared_size)
    validate_dimensions(h)
    return h


def validate_dimensions(h: Header) -> None:
    positive = {
        "dim": h.dim, "hidden_dim": h.hidden_dim, "n_layers": h.n_layers,
        "n_heads": h.n_heads, "n_kv_heads": h.n_kv_heads,
        "head_dim": h.head_dim, "vocab_size": h.vocab_size,
        "max_seq_len": h.max_seq_len,
    }
    for name, value in positive.items():
        if value <= 0:
            fail(f"{name} must be positive")
        if value > U32_MAX:
            fail(f"{name} exceeds uint32")
    if h.n_heads % h.n_kv_heads:
        fail("n_heads must be divisible by n_kv_heads")
    if h.head_dim % 2:
        fail("head_dim must be even for the RoPE implementation")
    q_dim = h.n_heads * h.head_dim
    kv_dim = h.n_kv_heads * h.head_dim
    if q_dim > U64_MAX or kv_dim > U64_MAX:
        fail("attention dimension multiplication overflows uint64")
    # K dimensions, not output-row dimensions, must satisfy the Q8 block rules.
    for name, k in (("dim", h.dim), ("q_dim", q_dim), ("hidden_dim", h.hidden_dim)):
        row_bytes(k, h.version)
    if not math.isfinite(h.rms_norm_eps) or h.rms_norm_eps <= 0:
        fail("rms_norm_eps must be finite and positive")
    if not math.isfinite(h.rope_theta) or h.rope_theta <= 0:
        fail("rope_theta must be finite and positive")
    # The current runtime stores K/V cache and attention scores as FP32.
    checked_product("KV-cache size", 2, h.n_layers, h.max_seq_len, kv_dim, 4)
    checked_product("attention-score buffer size", h.n_heads, h.max_seq_len, 4)
    checked_product("logits buffer size", h.vocab_size, 4)
    if h.eos_1 >= h.vocab_size or h.eos_2 >= h.vocab_size:
        fail("EOS token ID is outside vocabulary")
    if h.ht_mask != HASH_MASK:
        fail(f"tokenizer hash mask must be {HASH_MASK}")


def parse_tokenizer(data: memoryview, h: Header) -> dict:
    start = h.off_tokenizer
    end = h.off_embed
    if start % 64 or end % 64 or start < HEADER_SIZE or end <= start:
        fail("tokenizer section offsets are invalid or not 64-byte aligned")
    checked_region(start, end - start, len(data), "tokenizer section")
    section = data[start:end]
    if len(section) < TOKENIZER_HEADER_SIZE:
        fail("tokenizer section is shorter than its 64-byte header")
    off_b2t, off_offsets, off_bytes, off_ht = struct.unpack_from("<4Q", section, 0)
    if any(section[32:TOKENIZER_HEADER_SIZE]):
        fail("reserved tokenizer-header bytes must be zero")
    expected_b2t = TOKENIZER_HEADER_SIZE
    expected_offsets = align64(expected_b2t + 256 * 4)
    expected_bytes = align64(expected_offsets + (h.vocab_size + 1) * 4)
    if (off_b2t, off_offsets, off_bytes) != (expected_b2t, expected_offsets, expected_bytes):
        fail("tokenizer byte-to-token, offsets, or bytes sub-offset is non-canonical")
    checked_region(off_b2t, 256 * 4, len(section), "byte_to_tok")
    checked_region(off_offsets, (h.vocab_size + 1) * 4, len(section), "token offsets")
    if off_ht % 64 or off_ht < off_bytes or off_ht > len(section):
        fail("tokenizer merge-table offset is invalid")
    tok_offsets = struct.unpack_from(f"<{h.vocab_size + 1}I", section, off_offsets)
    if tok_offsets[0] != 0:
        fail("token offsets[0] must be zero")
    previous = 0
    for value in tok_offsets:
        if value < previous:
            fail("token offsets are not monotonic")
        previous = value
    tok_bytes_len = tok_offsets[-1]
    if tok_bytes_len > U32_MAX:
        fail("token byte string exceeds uint32 offset capacity")
    if off_ht != align64(off_bytes + tok_bytes_len):
        fail("tokenizer merge-table offset disagrees with token byte length")
    checked_region(off_bytes, tok_bytes_len, len(section), "token byte string")
    if off_ht + HASH_SIZE * 16 > len(section):
        fail("tokenizer merge table extends beyond tokenizer section")
    if len(section) != align64(off_ht + HASH_SIZE * 16):
        fail("tokenizer section length is not the canonical aligned size")
    byte_ids = struct.unpack_from("<256I", section, off_b2t)
    if any(token_id >= h.vocab_size for token_id in byte_ids):
        fail("byte_to_tok contains an ID outside vocabulary")
    # Validate all hash slots. A valid table has contiguous unique ranks and
    # every key/merged ID refers to the declared vocabulary.
    ranks = bytearray()
    seen_keys = set()
    occupied = 0
    for i in range(HASH_SIZE):
        key, merged_id, rank = struct.unpack_from("<QII", section, off_ht + i * 16)
        if rank == EMPTY_RANK:
            continue
        left, right = key >> 32, key & U32_MAX
        if left >= h.vocab_size or right >= h.vocab_size or merged_id >= h.vocab_size:
            fail(f"merge-table slot {i} contains a token ID outside vocabulary")
        if rank >= h.vocab_size:
            fail(f"merge-table slot {i} has an invalid rank")
        if key in seen_keys:
            fail(f"duplicate BPE key in merge-table slot {i}")
        seen_keys.add(key)
        if len(ranks) <= rank:
            ranks.extend(b"\\x00" * (rank + 1 - len(ranks)))
        if ranks[rank]:
            fail(f"duplicate BPE rank {rank}")
        ranks[rank] = 1
        # Confirm that linear probing from the Fibonacci hash reaches this
        # slot without crossing an empty entry; cap work on hostile clusters.
        slot = ((key * FIB_MULT) & U64_MAX) >> (64 - HASH_BITS)
        probes = 0
        while slot != i:
            prior_rank = struct.unpack_from("<I", section, off_ht + slot * 16 + 12)[0]
            if prior_rank == EMPTY_RANK:
                fail(f"broken BPE probe chain before merge-table slot {i}")
            slot = (slot + 1) & HASH_MASK
            probes += 1
            if probes > MAX_HASH_PROBES:
                fail(f"BPE probe chain exceeds safety limit at slot {i}")
        occupied += 1
        if occupied >= HASH_SIZE:
            fail("BPE merge table must retain at least one empty slot")
    if occupied != len(ranks) or (ranks and not all(ranks)):
        fail("BPE ranks must be unique and contiguous from zero")
    return {"tokenizer_bytes": tok_bytes_len, "merge_entries": occupied,
            "tokenizer_section_bytes": len(section)}


def layer_layout(h: Header) -> tuple[int, list[tuple[str, int, int]]]:
    """Return canonical layer stride and (name, rows, K) matrix descriptions."""
    q_dim = h.n_heads * h.head_dim
    kv_dim = h.n_kv_heads * h.head_dim
    matrices = [
        ("q_proj", q_dim, h.dim), ("k_proj", kv_dim, h.dim),
        ("v_proj", kv_dim, h.dim), ("o_proj", h.dim, q_dim),
        ("gate_proj", h.hidden_dim, h.dim), ("up_proj", h.hidden_dim, h.dim),
        ("down_proj", h.dim, h.hidden_dim),
    ]
    cursor = 4 * h.dim * 4 + 2 * h.head_dim * 4
    for _name, _rows, k in matrices:
        cursor = align64(cursor)
        size = _rows * row_bytes(k, h.version)
        if size > U64_MAX - cursor:
            fail("layer-size calculation overflows uint64")
        cursor += size
    return align64(cursor), matrices


def validate_layout(data: memoryview, h: Header) -> dict:
    size = len(data)
    for name, offset in (("off_tokenizer", h.off_tokenizer), ("off_embed", h.off_embed),
                         ("off_layers", h.off_layers), ("off_final_norm", h.off_final_norm)):
        if offset % 64:
            fail(f"{name} is not 64-byte aligned")
    if h.off_tokenizer != HEADER_SIZE:
        fail("tokenizer must begin immediately after the 128-byte header")
    tok = parse_tokenizer(data, h)
    if h.off_embed != align64(h.off_tokenizer + tok["tokenizer_section_bytes"]):
        fail("embedding offset does not follow tokenizer section")
    emb_size = h.vocab_size * row_bytes(h.dim, h.version)
    if emb_size > U64_MAX - h.off_embed:
        fail("embedding-size calculation overflows uint64")
    expected_layers = align64(h.off_embed + emb_size)
    if h.off_layers != expected_layers:
        fail("layer offset does not follow embedding section")
    stride, matrices = layer_layout(h)
    if h.layer_stride != stride:
        fail(f"layer_stride={h.layer_stride} differs from calculated {stride}")
    layers_size = h.n_layers * stride
    if layers_size > U64_MAX - h.off_layers:
        fail("layer-section size overflows uint64")
    expected_final = h.off_layers + layers_size
    if h.off_final_norm != expected_final:
        fail("final-norm offset does not follow layer section")
    final_size = h.dim * 4
    expected_file_size = align64(h.off_final_norm + final_size)
    if h.file_size != expected_file_size:
        fail(f"file size/layout mismatch: expected {expected_file_size}, got {h.file_size}")
    checked_region(h.off_embed, emb_size, size, "embeddings")
    checked_region(h.off_layers, layers_size, size, "layers")
    checked_region(h.off_final_norm, final_size, size, "final norm")
    return {"embedding_bytes": emb_size, "layer_stride": stride,
            "layers_bytes": layers_size, "final_norm_bytes": final_size,
            "q_dim": h.n_heads * h.head_dim,
            "kv_dim": h.n_kv_heads * h.head_dim, **tok}


def validate_buffer(data: bytes | bytearray | memoryview) -> dict:
    view = memoryview(data)
    h = parse_header(view)
    report = validate_layout(view, h)
    return {"valid": True, "header": asdict(h), "layout": report}


def validate_file(path: str) -> dict:
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        if size < HEADER_SIZE:
            fail(f"file is shorter than the {HEADER_SIZE}-byte header")
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            if len(mapped) != size:
                fail("file size changed while opening")
            return validate_buffer(mapped)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate llm.asm ASMBIN v1/v2 without loading model weights into RAM")
    parser.add_argument("file", help="ASMBIN file to inspect")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        report = validate_file(args.file)
    except (OSError, ValidationError, struct.error, OverflowError) as exc:
        print(f"ASMBIN INVALID: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        h = report["header"]
        layout = report["layout"]
        print(f"ASMBIN valid: v{h['version']} ({h['file_size']:,} bytes)")
        print(f"Architecture: dim={h['dim']} hidden={h['hidden_dim']} layers={h['n_layers']} heads={h['n_heads']}/{h['n_kv_heads']} head_dim={h['head_dim']}")
        print(f"Embedding: {layout['embedding_bytes']:,} B; layer stride: {layout['layer_stride']:,} B")
        print(f"Layers: {layout['layers_bytes']:,} B; tokenizer merges: {layout['merge_entries']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
