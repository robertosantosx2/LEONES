# Reference prompts for the chat template tests (tests/serve.rs): llama.cpp's Jinja rendering of each request.
# Usage: python -I tools/gen_chat_fixtures.py <name> [--port 8198]
# Needs llama-server running with `--jinja --chat-template-file tests/fixtures/chat/<name>.jinja` (any model; the CPU
# build with a small model is enough). Writes tests/fixtures/chat/requests.json and tests/fixtures/chat/<name>.json,
# which maps each case to the prompt, or to null when llama-server rejects the request.
import argparse
import json
import urllib.error
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--port", type=int, default=8198)
a = ap.parse_args()


def fn(name, desc, props, req):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req},
        },
    }


weather = fn(
    "get_weather",
    "Current weather for a city.",
    {
        "city": {"type": "string", "description": "City name"},
        "unit": {"type": "string", "enum": ["c", "f"]},
    },
    ["city"],
)
clock = fn("get_time", "Local time in a city.", {"city": {"type": "string"}}, ["city"])
TOOLS = [weather, clock]


def call(i, name, args):
    return {
        "id": f"call_{i}",
        "type": "function",
        "function": {"name": name, "arguments": args},
    }


U = lambda c: {"role": "user", "content": c}
A = lambda c, **k: {"role": "assistant", "content": c, **k}
S = lambda c: {"role": "system", "content": c}
T = lambda i, c: {"role": "tool", "tool_call_id": f"call_{i}", "content": c}
q = "What is the weather and the time in Paris?"
two_calls = A(
    "",
    tool_calls=[
        call(0, "get_weather", '{"city": "Paris"}'),
        call(1, "get_time", '{"city": "Paris"}'),
    ],
)
flow = [
    S("Be brief."),
    U(q),
    two_calls,
    T(0, '{"temp": 21, "sky": "clear"}'),
    T(1, "14:05"),
]

cases = {
    "plain_system": {"messages": [S("Be brief."), U("Hi")]},
    "multi_turn": {
        "messages": [U("Hi"), A("Hello! How can I help?"), U("Tell me a joke.")]
    },
    "tools_system": {"messages": [S("Be brief."), U(q)], "tools": TOOLS},
    "tools_no_system": {"messages": [U(q)], "tools": TOOLS},
    "two_tool_flow": {"messages": flow, "tools": TOOLS},
    "final_answer": {
        "messages": flow
        + [A("It is 21 C and clear, and the time is 14:05."), U("Thanks!")],
        "tools": TOOLS,
    },
    "call_with_content": {
        "messages": [
            U(q),
            A(
                "Let me check.",
                tool_calls=[call(0, "get_weather", '{"city": "Paris", "unit": "c"}')],
            ),
            T(0, "21 C"),
        ],
        "tools": TOOLS,
    },
    "think_on": {"messages": [U("Hi")], "think": True},
    "think_history": {
        "messages": [
            U("Hi"),
            A("<think>\nThe user greets.\n</think>\n\nHello!"),
            U("Bye"),
        ]
    },
    "think_after_query": {
        "messages": [
            U(q),
            A(
                "<think>\nNeed tools.\n</think>\n\n",
                tool_calls=[call(0, "get_weather", '{"city": "Paris"}')],
            ),
            T(0, "21 C"),
        ],
        "tools": TOOLS,
    },
    "reasoning_field": {
        "messages": [
            U(q),
            A(
                "",
                reasoning_content=" Need tools. ",
                tool_calls=[call(0, "get_weather", '{"city": "Paris"}')],
            ),
            T(0, "21 C"),
        ],
        "tools": TOOLS,
    },
    "value_types": {
        "messages": [
            U("x"),
            A(
                None,
                tool_calls=[
                    call(
                        0,
                        "f",
                        json.dumps(
                            {
                                "s": "line1\nline2",
                                "i": -3,
                                "f": 1.5,
                                "t": True,
                                "n": None,
                                "l": [1, "é\u0001"],
                                "o": {"b": 1, "a": 2},
                            }
                        ),
                    )
                ],
            ),
            T(0, "ok"),
        ],
        "tools": [fn("f", "", {}, [])],
    },
    "args_object": {
        "messages": [
            U("x"),
            A("", tool_calls=[call(0, "f", {"z": 1, "a": "q"})]),
            T(0, "ok"),
        ],
        "tools": [fn("f", "d", {}, [])],
    },
    "args_bad_json": {
        "messages": [U("x"), A("", tool_calls=[call(0, "f", "not json")]), T(0, "ok")],
        "tools": [fn("f", "d", {}, [])],
    },
    "tools_canonical": {
        "messages": [U("x")],
        "tools": [
            {
                "function": {
                    "parameters": {
                        "type": "object",
                        "properties": {"n": {"type": "integer", "minimum": 1.0}},
                    },
                    "name": "f",
                    "strict": True,
                },
                "type": "function",
            }
        ],
    },
    "unicode": {
        "messages": [S('Réponds en français "vite".'), U("Météo à Paris ? \t日本")],
        "tools": [
            fn(
                "météo",
                'Temps qu\'il fait "ici" \\ là\n',
                {"ville": {"type": "string"}},
                ["ville"],
            )
        ],
    },
    "parts": {
        "messages": [
            U([{"type": "text", "text": " a "}, {"type": "text", "text": "b"}])
        ]
    },
    "whitespace": {
        "messages": [S("  sys \n"), U("\n hi \n"), A("  hello \n"), U("again ")]
    },
    "two_systems": {"messages": [S("s1"), S("s2"), U("x"), S("s3"), U("y")]},
    "tool_first": {"messages": [T(0, "r"), U("x")]},
    "tool_response_user": {
        "messages": [
            U("a"),
            A("<think>\nx\n</think>\n\nb"),
            U("<tool_response>\nr\n</tool_response>"),
        ],
        "tools": TOOLS,
    },
}
out, reqs = {}, {}
for name, c in cases.items():
    body = {
        "messages": c["messages"],
        "chat_template_kwargs": {"enable_thinking": c.get("think", False)},
    }
    if "tools" in c:
        body["tools"] = c["tools"]
    reqs[name] = body
    r = urllib.request.Request(
        f"http://127.0.0.1:{a.port}/apply-template",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
    )
    try:
        out[name] = json.load(urllib.request.urlopen(r))["prompt"]
    except urllib.error.HTTPError:
        out[name] = None
d = "tests/fixtures/chat/"
json.dump(reqs, open(d + "requests.json", "w"), indent=1, ensure_ascii=False)
json.dump(out, open(d + a.name + ".json", "w"), indent=1, ensure_ascii=False)
print({k: v is not None for k, v in out.items()})
