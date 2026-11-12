#!/usr/bin/env python3
"""Render the DeepSeek-V4.1 template with tools (cases for src/chat.rs ds_tests) to tools/deepseek_ref/tpl_tools.json.
usage: render_tools.py chat_template.jinja   (the template is tokenizer.chat_template of the GGUF)"""
import json, sys, jinja2
def raise_exception(m): raise Exception(m)
env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols"])
env.globals["raise_exception"] = raise_exception
env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
t = env.from_string(open(sys.argv[1]).read())
tools = [{"type": "function", "function": {"name": "get_weather", "description": "Get weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "days": {"type": "integer"}}, "required": ["city"]}}},
         {"type": "function", "function": {"name": "ping", "description": "Ping", "parameters": {}}}]
call = lambda i, n, a: {"id": i, "type": "function", "function": {"name": n, "arguments": a}}
cases = [
    ([{"role": "user", "content": "Weather in Paris?"}], True),
    ([{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Weather in Paris and Rome?"},
      {"role": "assistant", "content": "Checking.", "reasoning_content": "need tool", "tool_calls": [call("a", "get_weather", {"city": "Paris", "days": 2}), call("b", "get_weather", {"city": "Rome", "flag": True, "x": [1, "é"]})]},
      {"role": "tool", "tool_call_id": "a", "content": "sunny"}, {"role": "tool", "tool_call_id": "b", "content": "rainy"},
      {"role": "user", "content": "thanks"}], True),
    ([{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "", "tool_calls": [call("a", "get_weather", {"city": "Paris"})]},
      {"role": "tool", "tool_call_id": "a", "content": "sunny"}], False),
]
out = []
for msgs, think in cases:
    out.append({"think": think, "req": {"messages": msgs, "tools": tools},
                "prompt": t.render(messages=msgs, tools=tools, thinking_mode="thinking" if think else "chat", add_generation_prompt=True)})
json.dump(out, open("tools/deepseek_ref/tpl_tools.json", "w"), ensure_ascii=False, indent=1)
