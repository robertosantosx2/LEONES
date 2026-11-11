//! KINETIC_TEST_GGUF=SmolLM2-135M-Instruct-f16.gguf KINETIC_TEST_EMBED_GGUF=bge-small-en-v1.5-f16.gguf
//! cargo test --release -p kinetic -- --include-ignored

use kinetic::{Message, Model};

fn text_model() -> Model {
    Model::open(std::env::var("KINETIC_TEST_GGUF").expect("set KINETIC_TEST_GGUF")).unwrap()
}

#[test]
fn models_cross_threads() {
    fn shared<T: Send + Sync>() {}
    shared::<Model>();
}

#[test]
fn missing_file_is_an_error() {
    let err = Model::open("no-such-model.gguf").err().unwrap();
    assert!(err.to_string().contains("no-such-model.gguf"), "{err}");
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn greedy_chat_streams_its_answer_and_repeats() {
    let model = text_model();
    assert!(!model.is_embedding());
    let mut request = model.request();
    request.sampling.temperature = 0.0;
    request.max_tokens = Some(16);
    let messages = [Message::new("user", "What is the capital of France?")];
    let mut streamed = String::new();
    let first = model
        .chat(&messages, &request, &mut |t| {
            streamed.push_str(t);
            true
        })
        .unwrap();
    assert!(!first.content.trim().is_empty());
    assert_eq!(streamed, first.content);
    let again = model.chat(&messages, &request, &mut |_| true).unwrap();
    assert_eq!(again.content, first.content);
    assert!(model.embed(&["text"]).is_err());
}

#[test]
#[ignore = "needs KINETIC_TEST_GGUF"]
fn generation_stops_when_asked() {
    let model = text_model();
    let mut request = model.request();
    request.max_tokens = Some(64);
    let mut pieces = 0;
    let c = model
        .generate("Once upon a time", &request, &mut |_| {
            pieces += 1;
            pieces < 3
        })
        .unwrap();
    assert_eq!(pieces, 3);
    assert!(c.completion_tokens < 64);
}

#[test]
#[ignore = "needs KINETIC_TEST_EMBED_GGUF"]
fn embeddings_have_the_model_width() {
    let path = std::env::var("KINETIC_TEST_EMBED_GGUF").expect("set KINETIC_TEST_EMBED_GGUF");
    let model = Model::open(path).unwrap();
    let size = model.embedding_size().unwrap();
    let v = model.embed(&["a cat", "a dog"]).unwrap();
    assert_eq!(v.len(), 2);
    assert!(v.iter().all(|e| e.len() == size));
    assert_ne!(v[0], v[1]);
    assert!(model.embed(&[""]).is_err());
}
