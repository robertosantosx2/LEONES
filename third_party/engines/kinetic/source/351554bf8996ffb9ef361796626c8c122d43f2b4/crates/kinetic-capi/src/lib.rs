//! The C API declared in `include/kinetic.h`.
//!
//! Every entry point checks its pointers, turns Rust errors and panics into
//! a failure code with a message for `kinetic_last_error`, and never lets a
//! panic cross into C.

use std::cell::RefCell;
use std::ffi::{c_char, c_void, CStr, CString};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::ptr;
use std::sync::Arc;

use kinetic::{Error, Message, Model};

/// A loaded model, shared by the sessions made from it.
pub struct KineticModel(Arc<Model>);

/// A conversation with a text model.
pub struct KineticSession {
    model: Arc<Model>,
    messages: Vec<Message>,
}

/// Mirrors `kinetic_params` in the header.
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct KineticParams {
    pub max_tokens: i32,
    pub temperature: f32,
    pub seed: u64,
    pub has_seed: bool,
}

/// Mirrors `kinetic_text_fn` in the header.
pub type KineticTextFn = Option<extern "C" fn(*const c_char, usize, *mut c_void) -> bool>;

thread_local! {
    static LAST_ERROR: RefCell<Option<CString>> = const { RefCell::new(None) };
}

fn set_error(message: &str) {
    let message = CString::new(message.replace('\0', " ")).unwrap_or_default();
    LAST_ERROR.with(|e| *e.borrow_mut() = Some(message));
}

/// Runs `f`, recording its error or panic as the thread's last error.
fn guard<T>(f: impl FnOnce() -> Result<T, Error>) -> Option<T> {
    match catch_unwind(AssertUnwindSafe(f)) {
        Ok(Ok(value)) => Some(value),
        Ok(Err(e)) => {
            set_error(&e.to_string());
            None
        }
        Err(panic) => {
            let why = panic
                .downcast_ref::<&str>()
                .copied()
                .or_else(|| panic.downcast_ref::<String>().map(String::as_str))
                .unwrap_or("unknown cause");
            set_error(&format!("internal error: {why}"));
            None
        }
    }
}

/// # Safety
/// `p` is NULL or a NUL-terminated string.
unsafe fn text<'a>(p: *const c_char, what: &str) -> Result<&'a str, Error> {
    if p.is_null() {
        return Err(format!("{what} is NULL").into());
    }
    // SAFETY: the caller passes a NUL-terminated string.
    unsafe { CStr::from_ptr(p) }
        .to_str()
        .map_err(|_| format!("{what} is not UTF-8").into())
}

#[no_mangle]
pub extern "C" fn kinetic_version() -> *const c_char {
    concat!(env!("CARGO_PKG_VERSION"), "\0").as_ptr().cast()
}

#[no_mangle]
pub extern "C" fn kinetic_last_error() -> *const c_char {
    LAST_ERROR.with(|e| e.borrow().as_ref().map_or(ptr::null(), |s| s.as_ptr()))
}

/// # Safety
/// `path` is NULL or a NUL-terminated string.
#[no_mangle]
pub unsafe extern "C" fn kinetic_model_load(path: *const c_char) -> *mut KineticModel {
    guard(|| {
        // SAFETY: forwarded from the caller.
        let path = unsafe { text(path, "path") }?;
        Ok(Box::into_raw(Box::new(KineticModel(Arc::new(
            Model::open(path)?,
        )))))
    })
    .unwrap_or(ptr::null_mut())
}

/// # Safety
/// `model` is NULL or came from `kinetic_model_load` and is not used again.
#[no_mangle]
pub unsafe extern "C" fn kinetic_model_free(model: *mut KineticModel) {
    if !model.is_null() {
        // SAFETY: the caller hands back ownership of a model from `kinetic_model_load`.
        drop(unsafe { Box::from_raw(model) });
    }
}

#[no_mangle]
pub extern "C" fn kinetic_params_default() -> KineticParams {
    KineticParams {
        max_tokens: 0,
        temperature: -1.0,
        seed: 0,
        has_seed: false,
    }
}

/// # Safety
/// `model` is NULL or a live model; `system` is NULL or a NUL-terminated string.
#[no_mangle]
pub unsafe extern "C" fn kinetic_session_new(
    model: *const KineticModel,
    system: *const c_char,
) -> *mut KineticSession {
    guard(|| {
        // SAFETY: the caller passes NULL or a live model.
        let model = unsafe { model.as_ref() }.ok_or("model is NULL")?;
        if model.0.is_embedding() {
            return Err(format!("{} is an embedding model", model.0.name()).into());
        }
        let messages = if system.is_null() {
            Vec::new()
        } else {
            // SAFETY: forwarded from the caller.
            vec![Message::new("system", unsafe { text(system, "system") }?)]
        };
        Ok(Box::into_raw(Box::new(KineticSession {
            model: Arc::clone(&model.0),
            messages,
        })))
    })
    .unwrap_or(ptr::null_mut())
}

/// # Safety
/// `session` is NULL or came from `kinetic_session_new` and is not used again.
#[no_mangle]
pub unsafe extern "C" fn kinetic_session_free(session: *mut KineticSession) {
    if !session.is_null() {
        // SAFETY: the caller hands back ownership of a session from `kinetic_session_new`.
        drop(unsafe { Box::from_raw(session) });
    }
}

/// # Safety
/// `session` is NULL or a live session no other thread is using; `message`
/// is NULL or a NUL-terminated string; `params` is NULL or valid.
#[no_mangle]
pub unsafe extern "C" fn kinetic_session_generate(
    session: *mut KineticSession,
    message: *const c_char,
    params: *const KineticParams,
    on_text: KineticTextFn,
    user_data: *mut c_void,
) -> i64 {
    guard(|| {
        // SAFETY: the caller passes NULL or a live session it alone uses.
        let session = unsafe { session.as_mut() }.ok_or("session is NULL")?;
        // SAFETY: forwarded from the caller.
        let message = unsafe { text(message, "message") }?;
        // SAFETY: the caller passes NULL or valid parameters.
        let params = unsafe { params.as_ref() }.copied();
        let params = params.unwrap_or(kinetic_params_default());

        let model = &session.model;
        let mut request = model.request();
        request.max_tokens = usize::try_from(params.max_tokens).ok().filter(|&n| n > 0);
        if params.temperature >= 0.0 {
            request.sampling.temperature = params.temperature;
        }
        if params.has_seed {
            request.sampling.seed = Some(params.seed);
        }

        session.messages.push(Message::new("user", message));
        let mut buffer = Vec::new();
        let answer = model.chat(&session.messages, &request, &mut |piece| {
            let Some(f) = on_text else { return true };
            buffer.clear();
            buffer.extend_from_slice(piece.as_bytes());
            buffer.push(0);
            f(buffer.as_ptr().cast(), piece.len(), user_data)
        });
        match answer {
            Ok(answer) => {
                session
                    .messages
                    .push(Message::new("assistant", answer.content));
                Ok(answer.completion_tokens as i64)
            }
            Err(e) => {
                session.messages.pop();
                Err(e)
            }
        }
    })
    .unwrap_or(-1)
}

/// # Safety
/// `model` is NULL or a live model.
#[no_mangle]
pub unsafe extern "C" fn kinetic_embedding_size(model: *const KineticModel) -> usize {
    // SAFETY: the caller passes NULL or a live model.
    unsafe { model.as_ref() }
        .and_then(|m| m.0.embedding_size())
        .unwrap_or(0)
}

/// # Safety
/// `model` is NULL or a live model; `text` is NULL or a NUL-terminated
/// string; `out` is NULL or has room for `kinetic_embedding_size` floats.
#[no_mangle]
pub unsafe extern "C" fn kinetic_embed(
    model: *const KineticModel,
    text: *const c_char,
    out: *mut f32,
) -> i32 {
    guard(|| {
        // SAFETY: the caller passes NULL or a live model.
        let model = unsafe { model.as_ref() }.ok_or("model is NULL")?;
        // SAFETY: forwarded from the caller.
        let input = unsafe { self::text(text, "text") }?;
        if out.is_null() {
            return Err("out is NULL".into());
        }
        let vector = model.0.embed(&[input])?.remove(0);
        // SAFETY: the caller gives room for the model's embedding size,
        // which is the length of every vector it returns.
        unsafe { ptr::copy_nonoverlapping(vector.as_ptr(), out, vector.len()) };
        Ok(0)
    })
    .unwrap_or(-1)
}
