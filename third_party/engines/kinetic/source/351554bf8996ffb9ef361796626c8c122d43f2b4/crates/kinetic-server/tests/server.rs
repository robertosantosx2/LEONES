//! Drives the server over HTTP with a real model.
//!
//! KINETIC_TEST_GGUF=LFM3-1.7B-Q4_K_M.gguf cargo test --release -p kinetic-server -- --ignored
//!
//! With `--features cuda` and `KINETIC_TEST_DEVICE=cuda` the server runs on
//! the GPU.

use std::net::TcpListener;
use std::sync::OnceLock;

use kinetic_gguf::GgufFile;
use kinetic_models::Model;
use kinetic_server::{Backend, CpuBackend, Engine};
use serde_json::{json, Value};

/// Starts one server for every test; requests take turns on the model.
fn base() -> &'static str {
    static BASE: OnceLock<String> = OnceLock::new();
    BASE.get_or_init(|| {
        let path = std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF");
        let file: &'static GgufFile = Box::leak(Box::new(GgufFile::open(path).unwrap()));
        let model: &'static Model = Box::leak(Box::new(kinetic_models::load(file).unwrap()));
        let engine: &'static Engine = Box::leak(Box::new(
            Engine::new("test-model", file.header(), backend(model), 4096).unwrap(),
        ));
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let base = format!("http://{}", listener.local_addr().unwrap());
        std::thread::spawn(move || kinetic_server::serve(engine, listener));
        base
    })
}

/// The CPU backend, or the GPU one when `KINETIC_TEST_DEVICE` is `cuda`.
fn backend(model: &'static Model) -> Box<dyn Backend> {
    #[cfg(feature = "cuda")]
    if std::env::var("KINETIC_TEST_DEVICE").is_ok_and(|d| d == "cuda") {
        return Box::new(kinetic_server::CudaBackend::new(model, 4096).unwrap());
    }
    Box::new(CpuBackend::new(model))
}

type Response = Result<ureq::Response, Box<ureq::Error>>;

fn post(path: &str, body: Value) -> Response {
    ureq::post(&format!("{}{path}", base()))
        .send_json(body)
        .map_err(Box::new)
}

fn chat(body: Value) -> Value {
    post("/v1/chat/completions", body)
        .unwrap()
        .into_json()
        .unwrap()
}

/// The `data:` payloads of an event stream.
fn events(body: Value) -> Vec<String> {
    let response = post("/v1/chat/completions", body).unwrap();
    assert_eq!(response.content_type(), "text/event-stream");
    let text = response.into_string().unwrap();
    assert!(text.ends_with("\n\n"), "{text:?}");
    text.split("\n\n")
        .filter(|e| !e.is_empty())
        .map(|e| e.strip_prefix("data: ").expect("data line").to_owned())
        .collect()
}

fn question(q: &str) -> Value {
    json!({"model": "any", "messages": [{"role": "user", "content": q}], "temperature": 0, "max_tokens": 40})
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn health_and_models() {
    let health: Value = ureq::get(&format!("{}/health", base()))
        .call()
        .unwrap()
        .into_json()
        .unwrap();
    assert_eq!(health["status"], "ok");
    let models: Value = ureq::get(&format!("{}/v1/models", base()))
        .call()
        .unwrap()
        .into_json()
        .unwrap();
    assert_eq!(models["data"][0]["id"], "test-model");
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn chat_answers_with_usage() {
    let r = chat(question("What is the capital of France?"));
    assert_eq!(r["object"], "chat.completion");
    let message = &r["choices"][0]["message"];
    assert_eq!(message["role"], "assistant");
    assert!(
        message["content"].as_str().unwrap().contains("Paris"),
        "{r}"
    );
    assert!(message.get("reasoning_content").is_none());
    let u = &r["usage"];
    let (p, c) = (
        u["prompt_tokens"].as_u64().unwrap(),
        u["completion_tokens"].as_u64().unwrap(),
    );
    assert!(p > 5 && c > 0 && c <= 40);
    assert_eq!(u["total_tokens"].as_u64(), Some(p + c));
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn stream_matches_the_plain_answer() {
    let plain = chat(question("Name three primary colours."));
    let mut body = question("Name three primary colours.");
    body["stream"] = true.into();
    body["stream_options"] = json!({"include_usage": true});
    let events = events(body);

    assert_eq!(events.last().map(String::as_str), Some("[DONE]"));
    let chunks: Vec<Value> = events[..events.len() - 1]
        .iter()
        .map(|e| serde_json::from_str(e).unwrap())
        .collect();
    assert_eq!(chunks[0]["choices"][0]["delta"]["role"], "assistant");
    let text: String = chunks
        .iter()
        .filter_map(|c| c["choices"][0]["delta"]["content"].as_str())
        .collect();
    assert_eq!(text, plain["choices"][0]["message"]["content"]);

    let usage = chunks.last().unwrap();
    assert_eq!(usage["choices"], json!([]));
    assert_eq!(usage["usage"], plain["usage"]);
    let finish = &chunks[chunks.len() - 2]["choices"][0]["finish_reason"];
    assert_eq!(*finish, plain["choices"][0]["finish_reason"]);
    assert!(chunks
        .iter()
        .all(|c| c["object"] == "chat.completion.chunk"));
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn polish_text_streams_intact() {
    let mut body = question("Jaka jest stolica Polski? Odpowiedz jednym zdaniem po polsku.");
    body["stream"] = true.into();
    let text: String = events(body)
        .iter()
        .filter(|e| *e != "[DONE]")
        .filter_map(|e| {
            let v: Value = serde_json::from_str(e).unwrap();
            v["choices"][0]["delta"]["content"]
                .as_str()
                .map(str::to_owned)
        })
        .collect();
    assert!(text.contains("Warszaw"), "{text}");
    assert!(!text.contains('\u{fffd}'));
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn stop_strings_and_token_limits() {
    let mut body = question("What is the capital of France? Answer in one word.");
    body["stop"] = json!(["Paris"]);
    let r = chat(body);
    assert!(!r["choices"][0]["message"]["content"]
        .as_str()
        .unwrap()
        .contains("Paris"));
    assert_eq!(r["choices"][0]["finish_reason"], "stop");

    let mut body = question("Count from one to fifty in words.");
    body["max_completion_tokens"] = 5.into();
    let r = chat(body);
    assert_eq!(r["choices"][0]["finish_reason"], "length");
    assert_eq!(r["usage"]["completion_tokens"], 5);
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn seeded_sampling_repeats() {
    let body = json!({
        "messages": [{"role": "user", "content": "Write a short poem about the sea."}],
        "temperature": 1.0, "seed": 42, "max_tokens": 16,
    });
    assert_eq!(
        chat(body.clone())["choices"][0]["message"],
        chat(body)["choices"][0]["message"]
    );
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn text_completions() {
    let r: Value = post(
        "/v1/completions",
        json!({"prompt": "The capital of France is", "max_tokens": 4, "temperature": 0}),
    )
    .unwrap()
    .into_json()
    .unwrap();
    assert_eq!(r["object"], "text_completion");
    assert!(
        r["choices"][0]["text"].as_str().unwrap().contains("Paris"),
        "{r}"
    );
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn token_limits_never_cut_a_character() {
    // fraktur letters take two tokens each in byte-level vocabularies
    let prompt = "\u{1d504}\u{1d505}\u{212d}\u{1d507}\u{1d508}\u{1d509}\u{1d50a}";
    for n in 1..=6 {
        let r: Value = post(
            "/v1/completions",
            json!({"prompt": prompt, "max_tokens": n, "temperature": 0}),
        )
        .unwrap()
        .into_json()
        .unwrap();
        let text = r["choices"][0]["text"].as_str().unwrap();
        assert!(!text.contains('\u{fffd}'), "{n}: {text:?}");
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn errors_are_openai_shaped() {
    let status = |r: Response| match r.map_err(|e| *e) {
        Err(ureq::Error::Status(code, response)) => {
            let body: Value = response.into_json().unwrap();
            assert!(body["error"]["message"].is_string(), "{body}");
            code
        }
        other => panic!("expected an error status, got {other:?}"),
    };
    assert_eq!(status(post("/v1/nothing", json!({}))), 404);
    assert_eq!(
        status(post("/v1/chat/completions", json!({"messages": []}))),
        400
    );
    assert_eq!(
        status(post("/v1/chat/completions", json!({"messages": "hi"}))),
        400
    );
    assert_eq!(
        status(
            ureq::post(&format!("{}/v1/chat/completions", base()))
                .set("Content-Type", "application/json")
                .send_string("{")
                .map_err(Box::new)
        ),
        400
    );
    assert_eq!(
        status(
            ureq::post(&format!("{}/health", base()))
                .call()
                .map_err(Box::new)
        ),
        405
    );
    let long = "word ".repeat(5000);
    assert_eq!(status(post("/v1/chat/completions", question(&long))), 400);
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn json_schema_output_matches_the_schema() {
    let schema = json!({
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "population_millions": {"type": "number"},
            "sights": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
        },
        "required": ["city", "population_millions", "sights"],
        "additionalProperties": false,
    });
    for temperature in [0.0, 0.8] {
        let r = chat(json!({
            "messages": [{"role": "user", "content": "Describe Warsaw."}],
            "temperature": temperature, "seed": 3, "max_tokens": 200,
            "response_format": {"type": "json_schema", "json_schema": {"name": "city", "schema": schema}},
        }));
        assert_eq!(r["choices"][0]["finish_reason"], "stop");
        let content = r["choices"][0]["message"]["content"].as_str().unwrap();
        let doc: Value = serde_json::from_str(content).expect("valid JSON");
        let keys: Vec<&str> = doc
            .as_object()
            .unwrap()
            .keys()
            .map(String::as_str)
            .collect();
        assert_eq!(keys, ["city", "population_millions", "sights"]);
        assert!(doc["population_millions"].is_number());
        assert_eq!(doc["sights"].as_array().unwrap().len(), 2);
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn bad_response_formats_are_refused() {
    let mut body = question("Hi");
    body["response_format"] = json!({"type": "xml"});
    match post("/v1/chat/completions", body).map_err(|e| *e) {
        Err(ureq::Error::Status(code, _)) => assert_eq!(code, 400),
        other => panic!("expected 400, got {other:?}"),
    }
}

fn weather_tool() -> Value {
    json!({"type": "function", "function": {
        "name": "get_weather",
        "description": "Current weather in a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "The city name"}},
            "required": ["city"],
        },
    }})
}

fn weather_question() -> Value {
    json!({
        "messages": [{"role": "user", "content": "What is the weather in Paris right now?"}],
        "tools": [weather_tool()], "temperature": 0, "max_tokens": 120,
    })
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn tool_calls_round_trip() {
    let r = chat(weather_question());
    let choice = &r["choices"][0];
    assert_eq!(choice["finish_reason"], "tool_calls", "{r}");
    let call = &choice["message"]["tool_calls"][0];
    assert_eq!(call["type"], "function");
    assert_eq!(call["function"]["name"], "get_weather");
    let args: Value =
        serde_json::from_str(call["function"]["arguments"].as_str().unwrap()).unwrap();
    assert!(args["city"].as_str().unwrap().contains("Paris"), "{args}");

    let mut followup = weather_question();
    let messages = followup["messages"].as_array_mut().unwrap();
    messages.push(choice["message"].clone());
    messages.push(json!({"role": "tool", "tool_call_id": call["id"], "content": "{\"temperature_c\": 17, \"sky\": \"sunny\"}"}));
    let answer = chat(followup);
    assert_eq!(answer["choices"][0]["finish_reason"], "stop", "{answer}");
    let text = answer["choices"][0]["message"]["content"].as_str().unwrap();
    assert!(text.contains("17"), "{text}");

    let mut none = weather_question();
    none["tool_choice"] = "none".into();
    assert_ne!(chat(none)["choices"][0]["finish_reason"], "tool_calls");
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn tool_calls_stream_as_deltas() {
    let plain = chat(weather_question());
    let mut body = weather_question();
    body["stream"] = true.into();
    let chunks: Vec<Value> = events(body)
        .iter()
        .filter(|e| *e != "[DONE]")
        .map(|e| serde_json::from_str(e).unwrap())
        .collect();
    let calls: Vec<&Value> = chunks
        .iter()
        .filter_map(|c| c["choices"][0]["delta"]["tool_calls"].as_array())
        .flatten()
        .collect();
    let expected = &plain["choices"][0]["message"]["tool_calls"];
    assert_eq!(calls.len(), expected.as_array().unwrap().len());
    assert_eq!(calls[0]["index"], 0);
    assert_eq!(calls[0]["function"], expected[0]["function"]);
    let last = &chunks.last().unwrap()["choices"][0];
    assert_eq!(last["finish_reason"], "tool_calls");
    let text: String = chunks
        .iter()
        .filter_map(|c| c["choices"][0]["delta"]["content"].as_str())
        .collect();
    assert!(!text.contains("<tool_call>"), "{text}");
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn forced_tool_calls() {
    let mut body = json!({
        "messages": [{"role": "user", "content": "Tell me a short joke."}],
        "tools": [weather_tool()], "temperature": 0, "max_tokens": 120,
    });
    for choice in [
        json!("required"),
        json!({"type": "function", "function": {"name": "get_weather"}}),
    ] {
        body["tool_choice"] = choice;
        let r = chat(body.clone());
        let message = &r["choices"][0]["message"];
        assert_eq!(r["choices"][0]["finish_reason"], "tool_calls", "{r}");
        assert_eq!(message["tool_calls"].as_array().unwrap().len(), 1, "{r}");
        let call = &message["tool_calls"][0]["function"];
        assert_eq!(call["name"], "get_weather");
        let args: Value = serde_json::from_str(call["arguments"].as_str().unwrap()).unwrap();
        assert!(args["city"].is_string(), "{args}");
    }
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn metrics_and_slots() {
    chat(question("Say hi."));
    let text = ureq::get(&format!("{}/metrics", base()))
        .call()
        .unwrap()
        .into_string()
        .unwrap();
    let value = |name: &str| -> f64 {
        let line = text
            .lines()
            .find(|l| l.starts_with(&format!("llamacpp:{name} ")))
            .unwrap_or_else(|| panic!("no {name} in\n{text}"));
        line.rsplit(' ').next().unwrap().parse().unwrap()
    };
    assert!(value("requests_total") >= 1.0);
    assert!(value("tokens_predicted_total") >= 1.0);
    assert!(value("predicted_tokens_seconds") > 0.0);
    let slots: Value = ureq::get(&format!("{}/slots", base()))
        .call()
        .unwrap()
        .into_json()
        .unwrap();
    let used = slots
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s.get("id_task").is_some())
        .expect("a slot that ran a request");
    // other tests share the slot, so its request may still be running
    assert!(used["params"]["n_predict"].is_number(), "{used}");
    assert!(used["next_token"][0]["n_remain"].is_number(), "{used}");
}
