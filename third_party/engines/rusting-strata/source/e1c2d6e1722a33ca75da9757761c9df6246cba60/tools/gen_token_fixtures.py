# Tokenize fixed strings with llama.cpp's llama-tokenize and store them as a test fixture.
# Usage: python -I tools/gen_token_fixtures.py <model.gguf> <llama-tokenize> > tests/fixtures/tokens.json
import ast
import json
import subprocess
import sys

TEXTS = [
    "Hello world",
    'fn main() {\n    println!("hi");\n}',
    "Привіт, як справи?",
    "<|im_start|>user\nWhat is 2+2?<|im_end|>\n<|im_start|>assistant\n",
    "   spaces\t\ttabs\n\n\n",
    "数字 12345 and émojis 🚀",
    "I'm sure it's DON'T we'll they've 3.14159",
]
out = []
for t in TEXTS:
    r = subprocess.run(
        [sys.argv[2], "-m", sys.argv[1], "-p", t, "--ids", "--log-disable", "--no-bos"],
        capture_output=True,
        text=True,
        check=True,
    )
    line = [l for l in r.stdout.splitlines() if l.startswith("[")][-1]
    out.append({"text": t, "ids": ast.literal_eval(line)})
json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
