# Write dequant fixtures from a real GGUF using gguf-py's numpy reference (independent of our Rust port).
# Usage: python -I tools/gen_fixtures.py <model.gguf> <out_dir>
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path.home() / "llama.cpp/gguf-py"))
from gguf import GGMLQuantizationType as Q
from gguf import GGUFReader
from gguf.constants import GGML_QUANT_SIZES
from gguf.quants import dequantize

WANT = {
    Q.F32,
    Q.BF16,
    Q.Q8_0,
    Q.Q2_K,
    Q.Q3_K,
    Q.Q4_K,
    Q.Q5_K,
    Q.Q6_K,
    Q.IQ2_XS,
    Q.IQ3_XXS,
    Q.IQ4_XS,
}
r = GGUFReader(sys.argv[1])
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
done = set()
for t in r.tensors:
    q = t.tensor_type
    if q not in WANT or q in done:
        continue
    blk, tsz = GGML_QUANT_SIZES[q]
    nblocks = min(8 if blk > 1 else 256, int(t.shape[0]) // blk)  # from the first row
    raw = np.frombuffer(t.data.tobytes()[: nblocks * tsz], dtype=np.uint8)
    deq = dequantize(raw, q).astype(np.float32).reshape(-1)
    (out / f"{q.name}.raw").write_bytes(raw.tobytes())
    (out / f"{q.name}.f32").write_bytes(deq.tobytes())
    print(q.name, t.name, nblocks, "blocks")
    done.add(q)
print("missing:", [m.name for m in WANT - done])
