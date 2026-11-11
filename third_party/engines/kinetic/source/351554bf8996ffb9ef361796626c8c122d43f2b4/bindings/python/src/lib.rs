//! The `kinetic._kinetic` extension module; `kinetic` re-exports it.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver};
use std::sync::Arc;

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};

/// A local model loaded from a .gguf or .ktc file.
#[pyclass(frozen, module = "kinetic")]
struct Model {
    inner: Arc<kinetic::Model>,
}

/// What a generation thread sends.
enum Event {
    Text(String),
    Done(Summary),
}

/// How a generation ended.
struct Summary {
    finish: &'static str,
    prompt_tokens: usize,
    completion_tokens: usize,
}

impl Summary {
    fn new(c: &kinetic::Completion) -> Self {
        Summary {
            finish: c.finish.as_str(),
            prompt_tokens: c.prompt_tokens,
            completion_tokens: c.completion_tokens,
        }
    }

    fn into_dict<'py>(self, py: Python<'py>, text: String) -> PyResult<Bound<'py, PyDict>> {
        let d = PyDict::new_bound(py);
        d.set_item("text", text)?;
        d.set_item("finish_reason", self.finish)?;
        d.set_item("prompt_tokens", self.prompt_tokens)?;
        d.set_item("completion_tokens", self.completion_tokens)?;
        Ok(d)
    }
}

/// Pieces of text as the model writes them. Dropping the stream stops the
/// generation.
#[pyclass(module = "kinetic")]
struct TextStream {
    events: Receiver<Result<Event, String>>,
    /// Yields dicts, ending with one that says how the generation ended,
    /// rather than bare strings.
    detailed: bool,
}

/// Sampling and limits for one generation; `None` keeps the model's.
#[derive(Clone, Default)]
struct Settings {
    max_tokens: Option<usize>,
    temperature: Option<f32>,
    top_p: Option<f32>,
    top_k: Option<usize>,
    min_p: Option<f32>,
    repeat_penalty: Option<f32>,
    seed: Option<u64>,
    stop: Vec<String>,
}

fn runtime_error(e: kinetic::Error) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

fn messages(messages: Vec<HashMap<String, String>>) -> PyResult<Vec<kinetic::Message>> {
    messages
        .into_iter()
        .map(|mut m| match (m.remove("role"), m.remove("content")) {
            (Some(role), Some(content)) => Ok(kinetic::Message { role, content }),
            _ => Err(PyValueError::new_err(
                "every message needs a role and a content",
            )),
        })
        .collect()
}

#[pymethods]
impl Model {
    /// Loads a model. `context` caps the tokens per conversation; with
    /// `gpu=False` a text model runs on the CPU even when a GPU could take
    /// it.
    #[new]
    #[pyo3(signature = (path, context=None, gpu=true))]
    fn new(py: Python<'_>, path: PathBuf, context: Option<usize>, gpu: bool) -> PyResult<Self> {
        let options = kinetic::Options { context, gpu };
        let model = py
            .allow_threads(|| kinetic::Model::open_with(path, &options))
            .map_err(runtime_error)?;
        Ok(Model {
            inner: Arc::new(model),
        })
    }

    /// The file name without its extension.
    #[getter]
    fn name(&self) -> &str {
        self.inner.name()
    }

    /// Tokens per conversation; `None` for an embedding model.
    #[getter]
    fn context_length(&self) -> Option<usize> {
        self.inner.context_length()
    }

    #[getter]
    fn is_embedding(&self) -> bool {
        self.inner.is_embedding()
    }

    /// The beginning-of-sequence token id, if the model has one.
    #[getter]
    fn bos(&self) -> Option<u32> {
        self.inner.special_tokens().0
    }

    /// The end-of-sequence token id, if the model has one.
    #[getter]
    fn eos(&self) -> Option<u32> {
        self.inner.special_tokens().1
    }

    /// Continues `prompt` exactly as written. Returns the text, or with
    /// `stream=True` an iterator over its pieces.
    #[pyo3(signature = (prompt, max_tokens=None, temperature=None, seed=None, stream=false))]
    fn generate(
        &self,
        py: Python<'_>,
        prompt: String,
        max_tokens: Option<usize>,
        temperature: Option<f32>,
        seed: Option<u64>,
        stream: bool,
    ) -> PyResult<PyObject> {
        let settings = Settings {
            max_tokens,
            temperature,
            seed,
            ..Settings::default()
        };
        self.run(py, Job::Generate(prompt), settings, stream, false)
    }

    /// Answers `messages`, a list of {"role": ..., "content": ...} dicts,
    /// through the model's chat template. Returns the answer, or with
    /// `stream=True` an iterator over its pieces.
    #[pyo3(signature = (messages, max_tokens=None, temperature=None, seed=None, stream=false))]
    fn chat(
        &self,
        py: Python<'_>,
        messages: Vec<HashMap<String, String>>,
        max_tokens: Option<usize>,
        temperature: Option<f32>,
        seed: Option<u64>,
        stream: bool,
    ) -> PyResult<PyObject> {
        let settings = Settings {
            max_tokens,
            temperature,
            seed,
            ..Settings::default()
        };
        self.run(
            py,
            Job::Chat(self::messages(messages)?),
            settings,
            stream,
            false,
        )
    }

    /// Generates after a raw `prompt` or, given `messages`, a chat, with
    /// every sampling setting. Returns a dict with the text, the
    /// finish_reason and the token counts; with `stream=True` an iterator
    /// of dicts with the text of each piece, the last also with the rest.
    #[pyo3(signature = (
        prompt=None, messages=None, max_tokens=None, temperature=None, top_p=None,
        top_k=None, min_p=None, repeat_penalty=None, seed=None, stop=None, stream=false,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn complete(
        &self,
        py: Python<'_>,
        prompt: Option<String>,
        messages: Option<Vec<HashMap<String, String>>>,
        max_tokens: Option<usize>,
        temperature: Option<f32>,
        top_p: Option<f32>,
        top_k: Option<usize>,
        min_p: Option<f32>,
        repeat_penalty: Option<f32>,
        seed: Option<u64>,
        stop: Option<Vec<String>>,
        stream: bool,
    ) -> PyResult<PyObject> {
        let job = match (prompt, messages) {
            (Some(p), None) => Job::Generate(p),
            (None, Some(m)) => Job::Chat(self::messages(m)?),
            _ => return Err(PyValueError::new_err("pass either prompt or messages")),
        };
        let settings = Settings {
            max_tokens,
            temperature,
            top_p,
            top_k,
            min_p,
            repeat_penalty,
            seed,
            stop: stop.unwrap_or_default(),
        };
        self.run(py, job, settings, stream, true)
    }

    /// The token ids of `text`, with BOS where the model adds one. With
    /// `special=True`, control tokens written in the text become their ids.
    #[pyo3(signature = (text, special=false))]
    fn tokenize(&self, py: Python<'_>, text: &str, special: bool) -> Vec<u32> {
        py.allow_threads(|| self.inner.tokenize(text, special))
    }

    /// The bytes `tokens` stand for.
    fn detokenize<'py>(&self, py: Python<'py>, tokens: Vec<u32>) -> Bound<'py, PyBytes> {
        PyBytes::new_bound(py, &self.inner.detokenize(&tokens))
    }

    /// One vector per text, from an embedding model.
    fn embed(&self, py: Python<'_>, texts: Vec<String>) -> PyResult<Vec<Vec<f32>>> {
        let texts: Vec<&str> = texts.iter().map(String::as_str).collect();
        py.allow_threads(|| self.inner.embed(&texts))
            .map_err(runtime_error)
    }

    fn __repr__(&self) -> String {
        format!("kinetic.Model({:?})", self.inner.name())
    }
}

enum Job {
    Generate(String),
    Chat(Vec<kinetic::Message>),
}

impl Model {
    fn request(&self, s: &Settings) -> kinetic::Request {
        let mut request = self.inner.request();
        request.max_tokens = s.max_tokens.filter(|&n| n > 0);
        let sampling = &mut request.sampling;
        sampling.temperature = s.temperature.unwrap_or(sampling.temperature);
        sampling.top_p = s.top_p.unwrap_or(sampling.top_p);
        sampling.top_k = s.top_k.unwrap_or(sampling.top_k);
        sampling.min_p = s.min_p.unwrap_or(sampling.min_p);
        sampling.repeat_penalty = s.repeat_penalty.unwrap_or(sampling.repeat_penalty);
        sampling.seed = s.seed.or(sampling.seed);
        request.stop = s.stop.clone();
        request
    }

    /// Runs `job` without the GIL: to the end, returning the text (or with
    /// `detailed` a dict), or on its own thread, returning a [`TextStream`].
    fn run(
        &self,
        py: Python<'_>,
        job: Job,
        settings: Settings,
        stream: bool,
        detailed: bool,
    ) -> PyResult<PyObject> {
        let model = Arc::clone(&self.inner);
        let request = self.request(&settings);
        let generate = move |on_text: &mut dyn FnMut(&str) -> bool| match &job {
            Job::Generate(prompt) => model.generate(prompt, &request, on_text),
            Job::Chat(messages) => model.chat(messages, &request, on_text),
        };
        if !stream {
            let c = py
                .allow_threads(|| generate(&mut |_| true))
                .map_err(runtime_error)?;
            if !detailed {
                return Ok(c.content.into_py(py));
            }
            let summary = Summary::new(&c);
            return Ok(summary.into_dict(py, c.content)?.into_py(py));
        }
        let (tx, events) = mpsc::channel();
        std::thread::spawn(move || {
            let sent = generate(&mut |text| tx.send(Ok(Event::Text(text.to_owned()))).is_ok());
            let _ = tx.send(
                sent.map(|c| Event::Done(Summary::new(&c)))
                    .map_err(|e| e.to_string()),
            );
        });
        Ok(Py::new(py, TextStream { events, detailed })?.into_py(py))
    }
}

#[pymethods]
impl TextStream {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&mut self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let events = &mut self.events;
        match py.allow_threads(move || events.recv()) {
            Ok(Ok(Event::Text(text))) if self.detailed => {
                let d = PyDict::new_bound(py);
                d.set_item("text", text)?;
                Ok(Some(d.into_py(py)))
            }
            Ok(Ok(Event::Text(text))) => Ok(Some(text.into_py(py))),
            Ok(Ok(Event::Done(summary))) if self.detailed => {
                Ok(Some(summary.into_dict(py, String::new())?.into_py(py)))
            }
            Ok(Ok(Event::Done(_))) | Err(_) => Ok(None),
            Ok(Err(e)) => Err(PyRuntimeError::new_err(e)),
        }
    }
}

/// Kinetic: open engine for running AI locally.
#[pymodule]
#[pyo3(name = "_kinetic")]
fn kinetic_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<Model>()?;
    m.add_class::<TextStream>()?;
    Ok(())
}
