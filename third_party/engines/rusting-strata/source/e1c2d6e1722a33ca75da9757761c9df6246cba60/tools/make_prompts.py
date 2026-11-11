# Build tools/prompts.json: 20 fixed chat-formatted prompts (7 code, 7 chat, 6 long-document).
import json
import pathlib

here = pathlib.Path(__file__).parent
root = here.parent
code = [
    "Write a Rust function that returns the n-th Fibonacci number using iteration.",
    "In Python, how do I read a CSV file and compute the average of the 'price' column?",
    "Explain what this C code does: int f(int *a, int n){int s=0;for(int i=0;i<n;i++)s+=a[i]*a[i];return s;}",
    "Write a SQL query that returns the top 5 customers by total order amount from tables customers(id,name) and orders(id,customer_id,amount).",
    "Write a regular expression that matches an IPv4 address and explain each part.",
    "Fix the bug: def avg(xs): return sum(xs) / len(xs) - it crashes on an empty list.",
    "Give a bash one-liner that finds the 10 largest files under the current directory.",
]
chat = [
    "Why is the sky blue? Answer in three sentences.",
    "Розкажи коротко про історію Києва.",
    "Объясни, что такое квантовая запутанность, простыми словами.",
    "请用简单的语言解释什么是机器学习。",
    "A train leaves at 9:15 and travels 180 km at 72 km/h. When does it arrive? Show your steps.",
    "Define the word 'entropy' as used in information theory.",
    "Give me a simple recipe for pancakes.",
]
lic = (
    root / "docs/superpowers/specs/2026-10-06-rusting-strata-v1-design.md"
).read_text()[:2400]
long_docs = [
    "Summarize this design document in five bullet points:\n\n" + lic,
    "What license terms apply here? Summarize:\n\n"
    + (
        'Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. '
        * 3
    ),
    "Find the error in this log:\n\n"
    + "\n".join(
        f"2026-10-06T12:{i:02d}:01Z INFO worker-{i % 4} processed batch {1000 + i} in {37 + i * 3} ms"
        for i in range(30)
    )
    + "\n2026-10-06T12:30:02Z ERROR worker-2 batch 1030 failed: connection reset by peer (retry 3/3)\n"
    + "\n".join(
        f"2026-10-06T12:{31 + i:02d}:01Z INFO worker-{i % 4} processed batch {1031 + i} in {40 + i} ms"
        for i in range(5)
    ),
    "Which of these cities is the largest by population? Explain.\n\n"
    + " ".join(
        f"{c} is a city in {k}. It has a long history of trade, culture and industry, with many museums, parks and universities attracting visitors every year."
        for c, k in [
            ("Lyon", "France"),
            ("Porto", "Portugal"),
            ("Krakow", "Poland"),
            ("Lviv", "Ukraine"),
            ("Seville", "Spain"),
            ("Turin", "Italy"),
            ("Ghent", "Belgium"),
            ("Brno", "Czechia"),
        ]
    ),
    "List the keys whose value is false:\n\n"
    + json.dumps({f"feature_{i}": (i % 3 != 0) for i in range(60)}, indent=1),
    "Which row has the highest score?\n\n| name | team | score |\n|---|---|---|\n"
    + "\n".join(f"| player{i} | team{i % 5} | {(i * 37) % 97} |" for i in range(40)),
]
wrap = lambda u: (
    f"<|im_start|>user\n{u}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
)
json.dump(
    [wrap(p) for p in code + chat + long_docs],
    open(here / "prompts.json", "w"),
    ensure_ascii=False,
    indent=1,
)
