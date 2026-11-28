import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import asmbin_validate as av


def make_fixture(version=2):
    vocab, dim, hidden, layers = 256, 32, 32, 1
    heads = kv_heads = 1
    head_dim = 32
    flags = av.FLAG_TIED_EMB | av.FLAG_QK_NORM | (av.FLAG_FP16_SCALES if version == 2 else 0)
    off_tok = av.HEADER_SIZE
    off_b2t = av.TOKENIZER_HEADER_SIZE
    off_offsets = av.align64(off_b2t + 256 * 4)
    off_bytes = av.align64(off_offsets + (vocab + 1) * 4)
    off_ht = av.align64(off_bytes)
    tok_len = av.align64(off_ht + av.HASH_SIZE * 16)
    off_embed = av.align64(off_tok + tok_len)
    emb_size = vocab * av.row_bytes(dim, version)
    off_layers = av.align64(off_embed + emb_size)
    h = av.Header(version, dim, hidden, layers, heads, kv_heads, head_dim,
                  vocab, 64, 1e-6, 10000.0, 1, 2, av.HASH_MASK, flags,
                  off_tok, off_embed, off_layers, 0, 0, 0)
    stride, _ = av.layer_layout(h)
    off_final = off_layers + layers * stride
    file_size = av.align64(off_final + dim * 4)
    h = av.Header(version, dim, hidden, layers, heads, kv_heads, head_dim,
                  vocab, 64, 1e-6, 10000.0, 1, 2, av.HASH_MASK, flags,
                  off_tok, off_embed, off_layers, stride, off_final, file_size)

    data = bytearray(file_size)
    av.HEADER.pack_into(
        data, 0, av.MAGIC, version, dim, hidden, layers, heads, kv_heads,
        head_dim, vocab, 64, 1e-6, 10000.0, 1, 2, av.HASH_MASK, flags,
        off_tok, off_embed, off_layers, stride, off_final, file_size, b"\0" * 16
    )
    struct.pack_into("<4Q", data, off_tok, off_b2t, off_offsets, off_bytes, off_ht)
    struct.pack_into("<256I", data, off_tok + off_b2t, *range(256))
    struct.pack_into(f"<{vocab + 1}I", data, off_tok + off_offsets, *([0] * (vocab + 1)))
    empty_slot = struct.pack("<QII", 0, 0, av.EMPTY_RANK)
    ht_start = off_tok + off_ht
    data[ht_start:ht_start + av.HASH_SIZE * 16] = empty_slot * av.HASH_SIZE
    return data


def rewrite_header(data, **changes):
    values = list(av.HEADER.unpack_from(data, 0))
    names = ["magic", "version", "dim", "hidden_dim", "n_layers", "n_heads",
             "n_kv_heads", "head_dim", "vocab_size", "max_seq_len",
             "rms_norm_eps", "rope_theta", "eos_1", "eos_2", "ht_mask",
             "flags", "off_tokenizer", "off_embed", "off_layers",
             "layer_stride", "off_final_norm", "file_size", "reserved"]
    for key, value in changes.items():
        values[names.index(key)] = value
    av.HEADER.pack_into(data, 0, *values)


class AsmbinValidatorTests(unittest.TestCase):
    def test_read_only_mmap_file_path(self):
        data = make_fixture()
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(data)
            tmp.flush()
            report = av.validate_file(tmp.name)
        self.assertTrue(report["valid"])

    def test_valid_v1(self):
        report = av.validate_buffer(make_fixture(1))
        self.assertTrue(report["valid"])
        self.assertEqual(report["header"]["version"], 1)

    def test_valid_v2(self):
        report = av.validate_buffer(make_fixture(2))
        self.assertTrue(report["valid"])
        self.assertEqual(report["header"]["version"], 2)

    def test_truncated_header(self):
        for size in (0, 4, 127):
            with self.subTest(size=size):
                with self.assertRaisesRegex(av.ValidationError, "truncated header"):
                    av.validate_buffer(b"\0" * size)

    def test_bad_magic_and_version(self):
        data = make_fixture()
        rewrite_header(data, magic=b"NOPE")
        with self.assertRaisesRegex(av.ValidationError, "magic"):
            av.validate_buffer(data)
        data = make_fixture()
        rewrite_header(data, version=3)
        with self.assertRaisesRegex(av.ValidationError, "version"):
            av.validate_buffer(data)

    def test_version_scale_flag_mismatch(self):
        data = make_fixture(2)
        rewrite_header(data, flags=av.FLAG_TIED_EMB | av.FLAG_QK_NORM)
        with self.assertRaisesRegex(av.ValidationError, "scale flag"):
            av.validate_buffer(data)

    def test_unknown_flags_and_reserved_bytes(self):
        data = make_fixture()
        h = av.HEADER.unpack_from(data, 0)
        rewrite_header(data, flags=h[15] | 0x80000000)
        with self.assertRaisesRegex(av.ValidationError, "unknown header flag"):
            av.validate_buffer(data)
        data = make_fixture()
        data[112] = 1
        with self.assertRaisesRegex(av.ValidationError, "reserved header"):
            av.validate_buffer(data)

    def test_untied_embeddings_rejected(self):
        data = make_fixture()
        rewrite_header(data, flags=av.FLAG_QK_NORM | av.FLAG_FP16_SCALES)
        with self.assertRaisesRegex(av.ValidationError, "tied embeddings"):
            av.validate_buffer(data)

    def test_file_size_mismatch(self):
        data = make_fixture()
        rewrite_header(data, file_size=len(data) - 64)
        with self.assertRaisesRegex(av.ValidationError, "file_size"):
            av.validate_buffer(data)

    def test_zero_dimension_and_head_divisibility(self):
        data = make_fixture()
        rewrite_header(data, dim=0)
        with self.assertRaisesRegex(av.ValidationError, "dim"):
            av.validate_buffer(data)
        data = make_fixture()
        rewrite_header(data, n_kv_heads=2)
        with self.assertRaisesRegex(av.ValidationError, "divisible"):
            av.validate_buffer(data)

    def test_runtime_buffer_overflow(self):
        data = make_fixture()
        rewrite_header(data, n_layers=0xFFFFFFFF, max_seq_len=0xFFFFFFFF)
        with self.assertRaisesRegex(av.ValidationError, "KV-cache size"):
            av.validate_buffer(data)

    def test_q8_k_constraints(self):
        data = make_fixture()
        rewrite_header(data, dim=48)
        with self.assertRaisesRegex(av.ValidationError, "multiple of 32"):
            av.validate_buffer(data)
        data = make_fixture()
        rewrite_header(data, n_heads=513)
        with self.assertRaisesRegex(av.ValidationError, "Q8_MAX_K"):
            av.validate_buffer(data)

    def test_tokenizer_byte_id_out_of_range(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_b2t = struct.unpack_from("<Q", data, off_tok)[0]
        struct.pack_into("<I", data, off_tok + off_b2t, 256)
        with self.assertRaisesRegex(av.ValidationError, "byte_to_tok"):
            av.validate_buffer(data)

    def test_non_monotonic_token_offsets(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_offsets = struct.unpack_from("<4Q", data, off_tok)[1]
        struct.pack_into("<III", data, off_tok + off_offsets, 0, 1, 0)
        with self.assertRaisesRegex(av.ValidationError, "not monotonic"):
            av.validate_buffer(data)

    def test_valid_bpe_entry_and_broken_probe_chain(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_ht = struct.unpack_from("<4Q", data, off_tok)[3]
        struct.pack_into("<QII", data, off_tok + off_ht, 0, 1, 0)
        self.assertTrue(av.validate_buffer(data)["valid"])

        data = make_fixture()
        struct.pack_into("<QII", data, off_tok + off_ht + 16, 0, 1, 0)
        with self.assertRaisesRegex(av.ValidationError, "probe chain"):
            av.validate_buffer(data)

    def test_duplicate_bpe_key(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_ht = struct.unpack_from("<4Q", data, off_tok)[3]
        struct.pack_into("<QII", data, off_tok + off_ht, 0, 1, 0)
        struct.pack_into("<QII", data, off_tok + off_ht + 16, 0, 2, 1)
        with self.assertRaisesRegex(av.ValidationError, "duplicate BPE key"):
            av.validate_buffer(data)

    def test_byte_to_tok_ids_must_be_unique(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_b2t = struct.unpack_from("<Q", data, off_tok)[0]
        struct.pack_into("<I", data, off_tok + off_b2t + 4, 0)
        with self.assertRaisesRegex(av.ValidationError, "distinct token IDs"):
            av.validate_buffer(data)

    def test_duplicate_bpe_ranks_are_rejected(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_ht = struct.unpack_from("<4Q", data, off_tok)[3]
        entries = [(0, 1, 10, 0), (0, 2, 11, 0)]
        for left, right, merged, rank in entries:
            key = (left << 32) | right
            slot = ((key * av.FIB_MULT) & av.U64_MAX) >> (64 - av.HASH_BITS)
            while struct.unpack_from("<I", data, off_tok + off_ht + slot * 16 + 12)[0] != av.EMPTY_RANK:
                slot = (slot + 1) & av.HASH_MASK
            struct.pack_into("<QII", data, off_tok + off_ht + slot * 16, key, merged, rank)
        with self.assertRaisesRegex(av.ValidationError, "duplicate BPE rank"):
            av.validate_buffer(data)

    def test_bpe_ranks_must_be_contiguous_from_zero(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_ht = struct.unpack_from("<4Q", data, off_tok)[3]
        for left, right, merged, rank in ((0, 1, 10, 0), (0, 2, 11, 2)):
            key = (left << 32) | right
            slot = ((key * av.FIB_MULT) & av.U64_MAX) >> (64 - av.HASH_BITS)
            while struct.unpack_from("<I", data, off_tok + off_ht + slot * 16 + 12)[0] != av.EMPTY_RANK:
                slot = (slot + 1) & av.HASH_MASK
            struct.pack_into("<QII", data, off_tok + off_ht + slot * 16, key, merged, rank)
        with self.assertRaisesRegex(av.ValidationError, "unique and contiguous"):
            av.validate_buffer(data)

    def test_merge_id_out_of_range(self):
        data = make_fixture()
        off_tok = av.HEADER.unpack_from(data, 0)[16]
        off_ht = struct.unpack_from("<4Q", data, off_tok)[3]
        struct.pack_into("<QII", data, off_tok + off_ht, 0, 256, 0)
        with self.assertRaisesRegex(av.ValidationError, "merge-table"):
            av.validate_buffer(data)

    def test_bad_layer_stride_and_offsets(self):
        data = make_fixture()
        h = av.HEADER.unpack_from(data, 0)
        rewrite_header(data, layer_stride=h[19] + 64)
        with self.assertRaisesRegex(av.ValidationError, "layer_stride"):
            av.validate_buffer(data)
        data = make_fixture()
        rewrite_header(data, off_layers=len(data) + 64)
        with self.assertRaises(av.ValidationError):
            av.validate_buffer(data)

    def test_versioned_qwen3_profile_registry(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "profiles" / "model-profile.schema.json").read_text())
        registry = json.loads((root / "profiles" / "qwen3-profiles.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(registry["schema_version"], 1)
        profiles = {p["profile_id"]: p for p in registry["profiles"]}
        self.assertEqual(set(profiles), {
            "qwen3-0.6b", "qwen3-4b", "qwen3-8b", "qwen3-14b", "qwen3-32b"
        })
        self.assertEqual(profiles["qwen3-0.6b"]["status"], "validated")
        self.assertEqual(profiles["qwen3-4b"]["status"], "audited")
        for size in ("8b", "14b", "32b"):
            self.assertEqual(profiles[f"qwen3-{size}"]["status"], "planned")
            self.assertIsNone(profiles[f"qwen3-{size}"]["architecture"])
        for profile in profiles.values():
            arch = profile["architecture"]
            if arch is None:
                continue
            h = av.Header(2, arch["hidden_size"], arch["intermediate_size"],
                          arch["num_hidden_layers"], arch["num_attention_heads"],
                          arch["num_key_value_heads"], arch["head_dim"],
                          arch["vocab_size"], 4096, 1e-6, 10000.0,
                          151645, 151643, av.HASH_MASK,
                          av.FLAG_TIED_EMB | av.FLAG_QK_NORM | av.FLAG_FP16_SCALES,
                          128, 0, 0, 0, 0, 0)
            av.validate_dimensions(h)

    def test_qwen3_06b_layer_stride_matches_exporter_norm_layout(self):
        h = av.Header(
            2, 1024, 3072, 28, 16, 8, 128, 151936, 4096,
            1e-6, 10000.0, 151645, 151643, av.HASH_MASK,
            av.FLAG_TIED_EMB | av.FLAG_QK_NORM | av.FLAG_FP16_SCALES,
            128, 0, 0, 0, 0, 0,
        )
        stride, _ = av.layer_layout(h)
        self.assertEqual(stride, 16_720_896)

    def test_qwen3_profiles_do_not_assume_dim_equals_q_dim(self):
        profiles = [
            (1024, 3072, 28, 16, 8, 128),
            (2560, 9728, 36, 32, 8, 128),
        ]
        for dim, hidden, layers, heads, kv_heads, head_dim in profiles:
            h = av.Header(2, dim, hidden, layers, heads, kv_heads, head_dim,
                          151936, 4096, 1e-6, 10000.0, 151645, 151643,
                          av.HASH_MASK, av.FLAG_QK_NORM | av.FLAG_FP16_SCALES,
                          128, 0, 0, 0, 0, 0)
            av.validate_dimensions(h)
        self.assertNotEqual(2560, 32 * 128)


if __name__ == "__main__":
    unittest.main(verbosity=2)
