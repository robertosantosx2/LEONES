//! Generation and an OpenAI-compatible HTTP server for Kinetic models.
//!
//! An [`Engine`] turns text into text: it renders the model's chat template,
//! tokenizes, streams the output through stop strings and splits off the
//! model's reasoning. The tokens themselves come from a [`Backend`];
//! [`CpuBackend`] runs on the CPU and, with the `cuda` feature,
//! `CudaBackend` on an NVIDIA GPU and, with the `vulkan` feature,
//! `VulkanBackend` on AMD, Intel and NVIDIA GPUs. [`serve`] exposes an engine over HTTP.

mod api;
mod backend;
mod base64;
mod constrained;
mod cpu;
#[cfg(feature = "cuda")]
mod cuda;
mod drafter;
mod embeddings;
mod engine;
mod http;
mod llama;
mod logprobs;
mod metrics;
mod model_info;
mod ollama;
pub mod receipt;
mod rerank;
mod sequence;
mod server;
mod template;
mod text;
mod tool_calls;
mod tool_grammar;
#[cfg(feature = "vulkan")]
mod vulkan;

pub use backend::{Backend, Job, PromptImage, Timings};
pub use cpu::CpuBackend;
#[cfg(feature = "cuda")]
pub use cuda::CudaBackend;
pub use embeddings::Embeddings;
pub use engine::{Completion, Engine, Finish, Prompt, Request, RequestError};
pub use kinetic_models::speculative::{Logprobs, Sampler, Sampling, TokenLogprob};
pub use model_info::ModelInfo;
pub use receipt::{Receipt, Receipts};
pub use server::{serve, serve_embeddings, serve_embeddings_with, serve_with, Options};
pub use text::Split;
pub use tool_calls::ToolCall;
#[cfg(feature = "vulkan")]
pub use vulkan::VulkanBackend;
