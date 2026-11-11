#!/usr/bin/env python3
"""Compare Strata token ids with llama-tokenize on varied strings. Usage: tok_check.py GGUF STRATA_TOK_IDS LLAMA_TOKENIZE"""
import json, subprocess, sys
gguf, ours, theirs = sys.argv[1:4]
S = ["The capital of France is", "Hello, world!", " leading space", "trailing space ", "tabs\tand\nnewlines\n\n", "def quicksort(arr):\n    return arr",
     "fn main() { println!(\"{}\", 1 + 2); }", "12345678901234567890", "3.14159 and 1,000,000", "你好，世界！今天天气很好。", "こんにちは世界、カタカナとひらがな",
     "Привет, мир!", "émigré naïve café", "emoji 😀🎉 test", "<｜begin▁of▁sentence｜>hello", "<｜User｜>Hi<｜Assistant｜>", "URL https://example.com/a?b=c&d=e#f",
     "snake_case camelCase PascalCase kebab-case", "a" * 50, "   ", "", "x=1;y=2;z=x+y", "'s 't 're 've 'm 'll 'd", "!!!???...", "<think>reason</think>", "$$\\alpha + \\beta$$",
     "tool_calls ｜DSML｜ marker", "ÀÉÎÕÜ ß ø å", "line1\r\nline2\r\n", "0x7fffffff 0b1010 1e-9"]
inp = "\n".join(json.dumps(s) for s in S) + "\n"
mine = [json.loads(l) for l in subprocess.run([ours, gguf], input=inp, capture_output=True, text=True, check=True).stdout.splitlines()]
bad = 0
for s, m in zip(S, mine):
    r = subprocess.run([theirs, "-m", gguf, "--ids", "--no-bos", "--log-disable", "-p", s], capture_output=True, text=True)
    t = json.loads(r.stdout.strip() or "[]")
    ok = t == m
    bad += not ok
    print("OK  " if ok else "DIFF", repr(s)[:50], "" if ok else f"\n  llama {t}\n  ours  {m}")
print(f"{len(S)-bad}/{len(S)} match")
sys.exit(bad > 0)
