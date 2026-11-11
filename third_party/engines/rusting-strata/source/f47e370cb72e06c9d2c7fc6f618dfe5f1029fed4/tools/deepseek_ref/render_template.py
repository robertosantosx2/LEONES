#!/usr/bin/env python3
"""Render the DeepSeek-V4.1 chat template with jinja2 for the cases in src/chat.rs ds_tests.
usage: render_template.py chat_template.jinja"""
import json, sys, jinja2
def raise_exception(m): raise Exception(m)
env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols"])
env.globals["raise_exception"] = raise_exception
env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
t = env.from_string(open(sys.argv[1]).read())
cases = [
    ([{"role": "user", "content": "Hi"}], True),
    ([{"role": "user", "content": "Hi"}], False),
    ([{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello."}, {"role": "user", "content": "Bye"}], False),
    ([{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello.", "reasoning_content": "greet"}, {"role": "user", "content": "Bye"}], True),
]
for msgs, think in cases:
    print(json.dumps(t.render(messages=msgs, thinking_mode="thinking" if think else "chat", add_generation_prompt=True), ensure_ascii=False))
