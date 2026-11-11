use rusting_strata::chat::{Hold, Json, Msg, Template};
use rusting_strata::serve::{Keys, Who, chat_request, host_ok, key_ok, list_models, messages_body, models, read_request};

/// Every request in tests/fixtures/chat renders byte-identical to llama.cpp's Jinja rendering of the model's own
/// template (tools/gen_chat_fixtures.py); a request llama.cpp rejects must be rejected too.
#[test]
fn prompts_match_llama_cpp() {
    let dir = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/chat/");
    let read = |f: &str| std::fs::read_to_string(format!("{dir}{f}")).unwrap();
    // Json keeps key order, which the prompt depends on (serde_json's map sorts keys).
    let Json::Obj(reqs) = serde_json::from_str(&read("requests.json")).unwrap() else { panic!() };
    for name in ["qwen36", "qwen3-4b-2507", "qwen3-30b-2507", "qwen3next"] {
        let tpl = Template::detect(Some(&read(&format!("{name}.jinja"))));
        let want: serde_json::Value = serde_json::from_str(&read(&format!("{name}.json"))).unwrap();
        for (case, body) in &reqs {
            let q = chat_request(body.dump().as_bytes());
            match want[case].as_str() {
                Some(w) => { let q = q.unwrap(); assert_eq!(tpl.render(&q.messages, &q.tools, q.think, false, true), w, "{name} {case}") }
                None => assert!(q.is_err(), "{name} {case} should be rejected"),
            }
        }
    }
}

#[test]
fn json_keeps_key_order_and_scales() {
    let j: Json = serde_json::from_str(r#"{"b": 1, "a": 2, "b": 3}"#).unwrap();
    assert_eq!(j.dump(), r#"{"b": 3, "a": 2}"#);
    // 200k distinct keys: quadratic duplicate checks would take minutes.
    let big = format!("{{{}}}", (0..200_000).map(|i| format!("\"k{i}\":0")).collect::<Vec<_>>().join(","));
    let t = std::time::Instant::now();
    let Json::Obj(o) = serde_json::from_str(&big).unwrap() else { panic!() };
    assert_eq!(o.len(), 200_000);
    assert!(t.elapsed().as_secs() < 5);
}

#[test]
fn detects_template_family() {
    let dir = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/chat/");
    let t = |f: &str| Template::detect(Some(&std::fs::read_to_string(format!("{dir}{f}.jinja")).unwrap()));
    assert_eq!(t("qwen36"), Template::Xml);
    assert_eq!(t("qwen3-4b-2507"), Template::Json { reasoning: true });
    assert_eq!(t("qwen3next"), Template::Json { reasoning: false });
}

#[test]
fn parses_tool_calls() {
    let tools: Vec<Json> = serde_json::from_str(r#"[{"type":"function","function":{"name":"get_weather","parameters":
        {"type":"object","properties":{"city":{"type":"string"},"days":{"type":"integer"},"code":{"type":"string"}}}}}]"#).unwrap();
    let xml = "Checking.\n\n<tool_call>\n<function=get_weather>\n<parameter=city>\nParis\n</parameter>\n<parameter=days>\n3\n</parameter>\n\
        <parameter=code>\n12\n</parameter>\n</function>\n</tool_call>\n<tool_call>\n<function=other>\n<parameter=x>\n[1, \"a\"]\n</parameter>\n\
        <parameter=y>\nnot json\n</parameter>\n<parameter=z>\nFalse\n</parameter>\n</function>\n</tool_call>";
    assert_eq!(Template::Xml.parse_calls(xml, &tools), Some(("Checking.".into(), vec![
        ("get_weather".into(), r#"{"city": "Paris", "days": 3, "code": "12"}"#.into()),
        ("other".into(), r#"{"x": [1, "a"], "y": "not json", "z": false}"#.into())])));
    let js = Template::Json { reasoning: true };
    assert_eq!(js.parse_calls("<tool_call>\n{\"name\": \"f\", \"arguments\": {\"b\": 1, \"a\": \"é\"}}\n</tool_call>", &[]),
        Some((String::new(), vec![("f".into(), r#"{"b": 1, "a": "é"}"#.into())])));
    assert_eq!(js.parse_calls(r#"<tool_call>{"name": "f", "arguments": "{\"a\": 1}"}</tool_call>"#, &[]),
        Some((String::new(), vec![("f".into(), r#"{"a": 1}"#.into())])));
    // Malformed or absent calls: plain text.
    for bad in ["no call", "<tool_call>\n{\"name\": \"f\"", "<tool_call>{\"name\": \"f\", \"arguments\": 3}</tool_call>",
                "<tool_call>{bad}</tool_call>", "<tool_call>{\"name\": \"f\", \"arguments\": {}}</tool_call> trailing"] {
        assert_eq!(js.parse_calls(bad, &[]), None, "{bad}");
    }
    for bad in ["<tool_call>\n<function=f>\n<parameter=a>\n1\n</function>\n</tool_call>", "<tool_call><function=f></function>x</tool_call>",
                "<tool_call>{\"name\": \"f\", \"arguments\": {}}</tool_call>"] {
        assert_eq!(Template::Xml.parse_calls(bad, &tools), None, "{bad}");
    }
}

#[test]
fn hold_never_streams_a_call() {
    let reply = "Sure <tool <tool_call>\n<function=f>\n</function>\n</tool_call>";
    for step in 1..6 {
        let mut h = Hold::default();
        let mut sent = String::new();
        for c in reply.as_bytes().chunks(step) { sent += h.push(std::str::from_utf8(c).unwrap()); }
        assert_eq!(sent, "Sure <tool ", "step {step}");
        assert_eq!(h.rest(), &reply[11..]);
    }
    let mut h = Hold::default();
    assert_eq!(h.push("a <tool_"), "a ");
    assert_eq!(h.push("x"), "<tool_x");
    assert_eq!(h.rest(), "");
}

#[test]
fn old_chat_prompt_unchanged() {
    let m = vec![Msg::new("system", "Be brief."), Msg::new("user", "Hi")];
    assert_eq!(Template::Xml.render(&m, &[], false, false, true),
        "<|im_start|>system\nBe brief.<|im_end|>\n<|im_start|>user\nHi<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n");
    assert!(Template::Xml.render(&m, &[], true, false, true).ends_with("<|im_start|>assistant\n<think>\n"));
}

#[test]
fn preserve_thinking_keeps_history_text() {
    let mut m = vec![Msg::new("user", "Find X"), Msg::new("assistant", "Looking."), Msg::new("user", "<tool_response>\nr\n</tool_response>"),
        Msg::new("assistant", "Found.")];
    let before = Template::Xml.render(&m, &[], false, true, false);
    m.push(Msg::new("user", "Now Y"));
    let after = Template::Xml.render(&m, &[], false, true, false);
    assert!(after.starts_with(&before), "{before:?}\n{after:?}");
    assert!(before.contains("<|im_start|>assistant\n<think>\n\n</think>\n\nLooking."));
    // Without it, the template drops the think block once a new user turn follows, as Qwen3.6's template does.
    assert!(!Template::Xml.render(&m, &[], false, false, false).contains("<think>"));
    let r = chat_request(br#"{"messages":[{"role":"user","content":"a"}],"chat_template_kwargs":{"preserve_thinking":true}}"#).unwrap();
    assert_eq!(r.preserve_thinking, Some(true));
}

#[test]
fn messages_api_request() {
    let body = br#"{"model":"m","max_tokens":50,"stream":true,"system":[{"type":"text","text":"Be brief.","cache_control":{"type":"ephemeral"}}],
        "tools":[{"name":"read","description":"Read a file","input_schema":{"type":"object","properties":{"path":{"type":"string"}}}},{"type":"web_search_20250305","name":"web_search"}],
        "messages":[{"role":"user","content":"Fix it"},
            {"role":"assistant","content":[{"type":"text","text":"Reading."},{"type":"tool_use","id":"t1","name":"read","input":{"path":"a.rs"}}]},
            {"role":"user","content":[{"type":"tool_result","tool_use_id":"t1","content":[{"type":"text","text":"fn a() {}"}]},{"type":"text","text":"go on"}]}]}"#;
    let r = chat_request(&messages_body(body).unwrap()).unwrap();
    let m: Vec<_> = r.messages.iter().map(|m| (m.role.as_str(), m.content.as_str(), m.calls.len())).collect();
    assert_eq!(m, [("system", "Be brief.", 0), ("user", "Fix it", 0), ("assistant", "Reading.", 1), ("tool", "fn a() {}", 0), ("user", "go on", 0)]);
    assert_eq!(r.messages[2].calls[0].args.dump(), r#"{"path": "a.rs"}"#);
    assert_eq!(r.tools.len(), 1);
    assert_eq!((r.max_tokens, r.stream), (Some(50), true));
    // The Anthropic key header counts as the bearer key.
    let raw = "POST /v1/messages?beta=true HTTP/1.1\r\nx-api-key: k\r\ncontent-length: 0\r\n\r\n";
    assert!(key_ok(&read_request(&mut raw.as_bytes()).unwrap().auth, "k"));
}

#[test]
fn parses_request() {
    let body = r#"{"messages":[{"role":"user","content":[{"type":"text","text":"a"},{"type":"text","text":"b"}]}],"stream":true,"max_tokens":7,"temperature":0.7,"top_p":0.8,"seed":5}"#;
    let raw = format!("POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\ncontent-length: {}\r\n\r\n{body}", body.len());
    let r = read_request(&mut raw.as_bytes()).unwrap();
    assert_eq!((r.method.as_str(), r.path.as_str(), r.host.as_str(), r.json), ("POST", "/v1/chat/completions", "x", true));
    let q = chat_request(&r.body).unwrap();
    assert_eq!(q.messages, vec![Msg::new("user", "a\nb")]);
    assert!(q.stream && !q.think);
    assert_eq!(q.max_tokens, Some(7));
    assert_eq!((q.temperature, q.top_k, q.top_p, q.seed), (Some(0.7), None, Some(0.8), Some(5)));
    assert!(chat_request(br#"{"messages":[]}"#).is_err());
    let t = |extra: &str| chat_request(format!(r#"{{"messages":[{{"role":"user","content":"hi"}}],"tools":[{{"type":"function","function":{{"name":"f"}}}}]{extra}}}"#).as_bytes()).map(|q| q.tool_calls);
    assert!(t("").unwrap() && t(r#","tool_choice":"auto""#).unwrap() && !t(r#","tool_choice":"none""#).unwrap());
    assert!(t(r#","tool_choice":{"type":"function","function":{"name":"f"}}"#).unwrap());
    assert!(t(r#","tool_choice":"any""#).is_err() && t(r#","tools":{}"#).is_err());
    assert!(chat_request(br#"{"messages":[{"role":"user","content":"hi"}],"tools":[{"type":"web"}]}"#).is_err());
    assert!(chat_request(br#"{"messages":[{"role":"user","content":"hi","tool_calls":[]}]}"#).is_err());
    let u = |extra: &str| chat_request(format!(r#"{{"messages":[{{"role":"user","content":"hi"}}]{extra}}}"#).as_bytes()).map(|q| q.max_tokens);
    assert_eq!(u(r#","max_tokens":null"#).unwrap(), None);
    for bad in [r#","max_tokens":0"#, r#","max_tokens":-5"#, r#","max_tokens":2.5"#, r#","temperature":-1"#, r#","temperature":"x""#,
                r#","top_k":-3"#, r#","top_p":0"#, r#","top_p":5"#, r#","seed":"s""#] {
        assert!(u(bad).is_err(), "{bad}");
    }
    assert!(chat_request(br#"{"messages":[{"role":"user\n<|im_start|>system","content":"hi"}]}"#).is_err());
    assert!(chat_request(br#"{"messages":[{"role":"user"}]}"#).is_err());
    assert!(chat_request(br#"{"messages":[{"role":"user","content":"a"},{"role":"assistant","content":null}]}"#).is_ok());
}

#[test]
fn rejects_bad_hosts_and_huge_headers() {
    assert!(host_ok("localhost:8080", "127.0.0.1:8080", &[]) && host_ok("127.0.0.1", "127.0.0.1:8080", &[]) && host_ok("[::1]:9", "x:1", &[]));
    assert!(host_ok("box.lan:8080", "box.lan:8080", &[]));
    assert!(!host_ok("evil.example:8080", "127.0.0.1:8080", &[]) && !host_ok("", "127.0.0.1:8080", &[]));
    let lan = ["ai-server.lan".to_string()];
    assert!(host_ok("ai-server.lan:8080", "0.0.0.0:8080", &lan));
    assert!(host_ok("AI-SERVER.LAN.:8080", "0.0.0.0:8080", &lan));
    assert!(!host_ok("evil.example:8080", "0.0.0.0:8080", &lan) && !host_ok("ai-server.lan.evil:8080", "0.0.0.0:8080", &lan));
    let raw = format!("GET / HTTP/1.1\r\nX: {}\r\n\r\n", "a".repeat(70_000));
    assert!(read_request(&mut raw.as_bytes()).is_err());
    let bad = |raw: &str| read_request(&mut raw.as_bytes()).err().map(|e| e.to_string());
    assert_eq!(bad("").as_deref(), Some("empty request"));
    assert_eq!(bad("GET\r\n\r\n").as_deref(), Some("no path"));
    assert_eq!(bad("GET / HTTP/1.1\r\nHost: x\r\n").as_deref(), Some("headers cut off or too long"));
    assert_eq!(bad("POST / HTTP/1.1\r\nContent-Length: 9000000\r\n\r\n").as_deref(), Some("body too large"));
    assert_eq!(bad("POST / HTTP/1.1\r\nContent-Length: -1\r\n\r\n").as_deref(), Some("bad Content-Length"));
    assert!(bad("POST / HTTP/1.1\r\nContent-Length: 5\r\n\r\nab").is_some());
    assert!(bad("POST / HTTP/1.1\r\nContent-Length: 2\r\n\r\nab").is_none());
}

#[test]
fn checks_api_key() {
    assert!(key_ok("Bearer s3cret", "s3cret"));
    assert!(!key_ok("Bearer s3cres", "s3cret") && !key_ok("Bearer s3cret2", "s3cret") && !key_ok("s3cret", "s3cret") && !key_ok("", "s3cret"));
    assert!(!key_ok("", "") && !key_ok("Bearer ", ""));
}

#[test]
fn hold_stops_before_a_stop_string() {
    let reply = "1 2 3 4 5 6 7";
    for step in 1..5 {
        let mut h = Hold::new(false, vec!["4 5".into(), "zz".into()]);
        let mut sent = String::new();
        for c in reply.as_bytes().chunks(step) {
            sent += h.push(std::str::from_utf8(c).unwrap());
            if h.stopped { break; }
        }
        assert!(h.stopped, "step {step}");
        assert_eq!((sent.as_str(), h.text.as_str(), h.rest()), ("1 2 3 ", "1 2 3 ", ""), "step {step}");
    }
    // A partial match is held back, then sent when the text goes another way; multi-byte stops cut on a char boundary.
    let mut h = Hold::new(false, vec!["кіт!".into()]);
    assert_eq!(h.push("a кі"), "a ");
    assert_eq!(h.push("тя"), "кітя");
    assert_eq!(h.push(" кіт!b"), " ");
    assert!(h.stopped);
    // With the tag held too, a stop inside a held call still ends the reply.
    let mut h = Hold::new(true, vec!["</tool_call>".into()]);
    assert_eq!(h.push("x <tool_call>{}</tool_call>y"), "x ");
    assert_eq!((h.stopped, h.rest()), (true, "<tool_call>{}"));
}

#[test]
fn parses_stop_and_n() {
    let q = |extra: &str| chat_request(format!(r#"{{"messages":[{{"role":"user","content":"hi"}}]{extra}}}"#).as_bytes()).map(|q| q.stop);
    assert_eq!(q("").unwrap(), Vec::<String>::new());
    assert_eq!(q(r#","stop":"\n""#).unwrap(), vec!["\n"]);
    assert_eq!(q(r#","stop":["a","","b"]"#).unwrap(), vec!["a", "b"]);
    assert!(q(r#","stop":[1]"#).is_err());
    assert!(q(r#","stop":5"#).is_err());
    assert!(q(&format!(r#","stop":{:?}"#, vec!["x"; 16])).is_ok());
    assert!(q(&format!(r#","stop":{:?}"#, vec!["x"; 17])).is_err());
    assert!(q(&format!(r#","stop":"{}""#, "x".repeat(256))).is_ok());
    assert!(q(&format!(r#","stop":"{}""#, "x".repeat(257))).is_err());
    assert!(q(r#","n":1"#).is_ok());
    assert!(q(r#","n":2"#).is_err());
}

#[test]
fn lists_models_once_per_split() {
    let d = std::env::temp_dir().join(format!("strata-list-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(d.join("org/repo")).unwrap();
    for (f, n) in [("a.gguf", 3), ("mmproj-a.gguf", 1), ("notes.txt", 1), ("org/repo/big-00001-of-00002.gguf", 5),
        ("org/repo/big-00002-of-00002.gguf", 7)] {
        std::fs::write(d.join(f), vec![0u8; n]).unwrap();
    }
    let l: Vec<_> = list_models(&d).into_iter().map(|(id, p, n)| (id, p.strip_prefix(&d).unwrap().to_path_buf(), n)).collect();
    std::fs::remove_dir_all(&d).unwrap();
    assert_eq!(l, [("a.gguf".into(), "a.gguf".into(), 3), ("org/repo/big-00001-of-00002.gguf".into(), "org/repo/big-00001-of-00002.gguf".into(), 12)]);
}

#[test]
fn lists_only_complete_split_models() {
    let files = vec![
        ("model-00001-of-00003.gguf".into(), 10),
        ("model-00002-of-00003.gguf".into(), 20),
        ("model-00001-of-00002.gguf".into(), 100),
        ("model-00002-of-00002.gguf".into(), 20),
        ("plain.gguf".into(), 7),
    ];
    assert_eq!(models(&files), vec![("model-00001-of-00002.gguf".into(), 120), ("plain.gguf".into(), 7)]);

    let mut complete = files;
    complete.push(("model-00003-of-00003.gguf".into(), 30));
    assert_eq!(models(&complete), vec![
        ("model-00001-of-00003.gguf".into(), 60),
        ("model-00001-of-00002.gguf".into(), 120),
        ("plain.gguf".into(), 7),
    ]);
}

#[test]
fn download_names_stay_in_the_models_folder() {
    use rusting_strata::hf::local_name;
    assert_eq!(local_name("Q4_K_M/m-00001-of-00002.gguf"), Some("m-00001-of-00002.gguf"));
    for bad in ["a/..\\..\\x.gguf", "C:x.gguf", "x.gguf:s.gguf", ".gguf", "a\nb.gguf", "x.bin", "dir/"] {
        assert_eq!(local_name(bad), None, "{bad:?}");
    }
}

/// The side panel's totals count every request since the server started, across model loads, and keep the last 40.
#[test]
fn stats_keep_totals_across_loads() {
    use rusting_strata::serve::{Last, Stats};
    let mut s = Stats::default();
    s.unload(Some("a".into()));
    assert!(s.loading && s.model.as_deref() == Some("a"));
    for i in 0..45 {
        s.record(Last { at: i, prompt_tokens: 10, cached_tokens: 4, completion_tokens: 2, finish: "stop".into(), ..Default::default() });
    }
    s.vram = Some((1, 2));
    s.unload(Some("b".into()));
    assert_eq!((s.requests, s.prompt_tokens, s.cached_tokens, s.completion_tokens), (45, 450, 180, 90));
    assert_eq!((s.recent.len(), s.recent[0].at), (40, 5));
    assert!(s.loading && s.vram.is_none() && s.model.as_deref() == Some("b"));
    s.unload(None);
    assert!(!s.loading && s.model.is_none() && s.requests == 45);
    let p = s.prometheus(3, 9);
    for l in ["strata_up 0\n", "strata_waiting 3\n", "strata_uptime_seconds 9\n", "strata_prompt_tokens_total 450\n", "# TYPE strata_requests_total counter\n"] {
        assert!(p.contains(l), "{l:?} missing from\n{p}");
    }
    assert!(!p.contains("vram") && !p.contains("expert"));
}

#[test]
fn keys_file_and_access() {
    let users = Keys::parse("# customers\nacme  acme-0123456789abcdef  # first\n\nbeta beta-0123456789abcdef\n").unwrap();
    assert_eq!(users, [("acme".to_string(), "acme-0123456789abcdef".to_string()), ("beta".into(), "beta-0123456789abcdef".into())]);
    assert!(Keys::parse("acme short").is_err() && Keys::parse("acme").is_err() && Keys::parse("a b c").is_err());
    assert!(Keys::parse("a acme-0123456789abcdef\na beta-0123456789abcdef").is_err(), "repeated name");
    assert!(Keys::parse("a acme-0123456789abcdef\nb acme-0123456789abcdef").is_err(), "repeated key");
    let open = Keys::default();
    assert_eq!(open.who(""), Some(Who { name: "".into(), id: 0, admin: true }));
    let k = Keys { admin: Some("root-key".into()), users };
    assert_eq!(k.who("Bearer root-key").map(|w| (w.id, w.admin)), Some((0, true)));
    let beta = k.who("Bearer beta-0123456789abcdef").unwrap();
    assert!(beta.name == "beta" && beta.id != 0 && !beta.admin && beta.id != k.who("Bearer acme-0123456789abcdef").unwrap().id);
    // A reloaded file with the lines in another order keeps each key's id (its cached conversations).
    let swapped = Keys { admin: None, users: k.users.iter().rev().cloned().collect() };
    assert_eq!(swapped.who("Bearer beta-0123456789abcdef"), Some(beta));
    assert_eq!(k.who("Bearer nope"), None);
    assert_eq!(k.who(""), None);
    let only_users = Keys { admin: None, users: k.users.clone() };
    assert_eq!(only_users.who(""), None, "customer keys alone close the server to keyless requests");
}

#[test]
fn per_key_holds() {
    use rusting_strata::serve::{Hold, Open};
    let open = Open::default();
    let (a, b) = (Hold::take(&open, 7, 2), Hold::take(&open, 7, 2));
    assert!(a.is_some() && b.is_some() && Hold::take(&open, 7, 2).is_none());
    assert!(Hold::take(&open, 8, 2).is_some(), "another key has its own count");
    drop(a);
    let c = Hold::take(&open, 7, 2);
    assert!(c.is_some());
    drop((b, c));
    assert!(open.lock().unwrap().is_empty());
}

/// A server with no keys checks `Host`; `--allowed-hosts` adds a LAN name without opening it to other names.
#[test]
fn serve_allows_configured_host_names() {
    use std::io::{Read, Write};
    let dir = std::env::temp_dir().join(format!("strata-host-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let addr = std::net::TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().to_string();
    let mut p = std::process::Command::new(env!("CARGO_BIN_EXE_rustingstrata"))
        .args(["serve", "--addr", &addr, "--allowed-hosts", "ai-server.lan"])
        .arg("--models-dir").arg(&dir)
        .env_remove("STRATA_API_KEY").env_remove("STRATA_ALLOWED_HOSTS")
        .stderr(std::process::Stdio::null()).spawn().unwrap();
    let get = |host: &str| -> String {
        let mut c = (0..100).find_map(|_| std::net::TcpStream::connect(&addr).ok().or_else(|| { std::thread::sleep(std::time::Duration::from_millis(50)); None }))
            .expect("server up");
        c.write_all(format!("GET / HTTP/1.1\r\nHost: {host}\r\n\r\n").as_bytes()).unwrap();
        let mut s = String::new();
        c.read_to_string(&mut s).unwrap();
        s.lines().next().unwrap_or_default().to_string()
    };
    assert!(get("ai-server.lan:8080").contains("200"));
    assert!(get("evil.example:8080").contains("403"));
    let _ = p.kill();
    let _ = p.wait();
    let _ = std::fs::remove_dir_all(&dir);
}

/// `strata serve` without a model, over HTTP: what the connection threads answer before the queue, a customer key
/// refused an admin route by `handle`, and a SIGTERM that exits.
#[test]
fn serve_without_a_model() {
    use std::io::{Read, Write};
    let dir = std::env::temp_dir().join(format!("strata-serve-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("keys.txt"), "acme acme-0123456789abcdef\n").unwrap();
    let addr = std::net::TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().to_string();
    let mut p = std::process::Command::new(env!("CARGO_BIN_EXE_rustingstrata"))
        .args(["serve", "--addr", &addr, "--api-key", "root-0123456789abcdef", "--api-keys"]).arg(dir.join("keys.txt"))
        .arg("--models-dir").arg(&dir).stderr(std::process::Stdio::null()).spawn().unwrap();
    // The status line and body of one request.
    let get = |raw: &str| -> (String, String) {
        let mut c = (0..100).find_map(|_| std::net::TcpStream::connect(&addr).ok().or_else(|| { std::thread::sleep(std::time::Duration::from_millis(50)); None }))
            .expect("server up");
        c.write_all(raw.as_bytes()).unwrap();
        let mut s = String::new();
        c.read_to_string(&mut s).unwrap();
        let (head, body) = s.split_once("\r\n\r\n").unwrap();
        (head.lines().next().unwrap().to_string(), body.to_string())
    };
    let req = |method: &str, path: &str, key: &str| {
        get(&format!("{method} {path} HTTP/1.1\r\nHost: {addr}\r\nAuthorization: Bearer {key}\r\nContent-Length: 0\r\n\r\n"))
    };
    let (s, b) = req("GET", "/health", "");
    assert!(s.contains("503") && b.contains("no model"), "{s} {b}");
    let (s, b) = req("POST", "/v1/chat/completions", "wrong");
    assert!(s.contains("401") && b.contains("invalid_api_key"), "{s} {b}");
    assert!(req("GET", "/", "").0.contains("200"), "the page loads without a key");
    let (s, b) = req("GET", "/v1/models?x=1", "acme-0123456789abcdef");
    assert!(s.contains("200") && b.contains(r#""data":[]"#), "{s} {b}");
    let (s, b) = req("GET", "/api/stats", "acme-0123456789abcdef");
    assert!(s.contains("403") && b.contains("permission_error"), "{s} {b}");
    assert!(req("GET", "/metrics", "root-0123456789abcdef").1.contains("strata_up"));
    assert!(get("GARBAGE\r\n\r\n").0.contains("400"));
    #[cfg(unix)]
    {
        std::process::Command::new("kill").args(["-TERM", &p.id().to_string()]).status().unwrap();
        let t = std::time::Instant::now();
        while p.try_wait().unwrap().is_none() {
            assert!(t.elapsed().as_secs() < 15, "no exit after SIGTERM");
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        assert!(p.wait().unwrap().success());
    }
    let _ = p.kill();
    let _ = std::fs::remove_dir_all(&dir);
}

/// `--parallel` outside 1..=255 is an invalid request: the server exits non-zero before it loads a model, naming the
/// flag and the allowed range. No GPU, no model needed.
#[test]
fn serve_rejects_a_bad_parallel_count() {
    for n in ["0", "256"] {
        let out = std::process::Command::new(env!("CARGO_BIN_EXE_rustingstrata"))
            .args(["serve", "--addr", "127.0.0.1:0", "--parallel", n])
            .output().unwrap();
        let err = String::from_utf8_lossy(&out.stderr);
        assert!(!out.status.success(), "--parallel {n} exited 0: {err}");
        assert!(err.contains(&format!("--parallel {n}: 1 to 255 slots")), "--parallel {n}: {err}");
    }
}

/// `serve --parallel 2 --kv q8` answers two concurrent chat requests (end to end through the binary). Model- and
/// GPU-gated: skipped unless `STRATA_MODEL` names a model and `STRATA_TEST_BACKENDS` asks for cuda (the GPU windows set
/// both).
#[test]
fn serve_parallel_smoke() {
    let Some(model) = std::env::var_os("STRATA_MODEL").filter(|p| std::path::Path::new(p).exists()) else {
        eprintln!("SKIP: no STRATA_MODEL"); return
    };
    if !std::env::var("STRATA_TEST_BACKENDS").is_ok_and(|v| v.split(',').any(|b| b.trim().eq_ignore_ascii_case("cuda"))) {
        eprintln!("SKIP: STRATA_TEST_BACKENDS does not select cuda");
        return
    }
    use std::io::{Read, Write};
    let addr = std::net::TcpListener::bind("127.0.0.1:0").unwrap().local_addr().unwrap().to_string();
    let mut p = std::process::Command::new(env!("CARGO_BIN_EXE_rustingstrata"))
        .args(["serve", "--model"]).arg(&model)
        .args(["--gpu", "--backend", "cuda", "--kv", "q8", "--ctx", "512", "--parallel", "2", "--addr", &addr])
        .spawn().unwrap();
    let result = (|| -> Result<Vec<String>, String> {
        // The listener opens before the model is loaded: wait until `/health` answers 200.
        let mut up = false;
        for _ in 0..3000 {
            if let Ok(mut c) = std::net::TcpStream::connect(&addr) {
                let _ = write!(c, "GET /health HTTP/1.1\r\nHost: {addr}\r\nConnection: close\r\n\r\n");
                let mut s = String::new();
                let _ = c.read_to_string(&mut s);
                if s.starts_with("HTTP/1.1 200") { up = true; break; }
            }
            if p.try_wait().unwrap().is_some() { return Err("server exited before it loaded the model".into()) }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        if !up { return Err("server did not become healthy within 300 s".into()) }
        let body = r#"{"messages":[{"role":"user","content":"Reply with one word."}],"max_tokens":4}"#;
        let ask = |i: usize| -> String {
            let mut c = std::net::TcpStream::connect(&addr).unwrap();
            write!(c, "POST /v1/chat/completions HTTP/1.1\r\nHost: {addr}\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: {}\r\n\r\n{body}", body.len()).unwrap();
            let mut s = String::new();
            c.read_to_string(&mut s).unwrap();
            format!("request {i}: {s}")
        };
        Ok(std::thread::scope(|sc| (0..2).map(|i| sc.spawn(move || ask(i))).collect::<Vec<_>>()
            .into_iter().map(|t| t.join().unwrap()).collect()))
    })();
    #[cfg(unix)]
    let _ = std::process::Command::new("kill").args(["-TERM", &p.id().to_string()]).status();
    let _ = p.kill();
    let _ = p.wait();
    let replies = result.unwrap_or_else(|e| panic!("{e}"));
    assert_eq!(replies.len(), 2);
    for r in replies {
        assert!(r.contains("200 OK"), "{r}");
        assert!(r.contains("\"choices\""), "{r}");
    }
}
