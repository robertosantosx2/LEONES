//! Sentence embeddings and relevance scores.
//!
//! An [`Embedder`] runs a BERT-style encoder or a decoder-only model over
//! whole inputs and pools each input's final hidden states into one vector,
//! the way the file's `pooling_type` says. Ranking models, such as
//! Qwen3-Reranker converted with its yes/no classifier, score inputs instead.

use kinetic_cpu::{l2_norm, matmul, softmax};
use kinetic_gguf::TensorSource;
use kinetic_quant::Matrix;

use crate::arch::bert::Encoder;
use crate::arch::{self, gemma_embedding};
use crate::loader::Loader;
use crate::{LoadError, Model};

/// How the hidden states of an input become one vector.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Pooling {
    /// The average over all tokens.
    Mean,
    /// The first token's state.
    Cls,
    /// The last token's state.
    Last,
    /// A classifier over the last token's state, whose first label's
    /// probability is the input's relevance.
    Rank,
}

/// A model loaded for embeddings or ranking, with weights borrowed from its
/// file.
pub struct Embedder<'a> {
    body: Body<'a>,
    pooling: Pooling,
    /// Label logits from the pooled state, for [`Pooling::Rank`].
    classifier: Option<Matrix<'a>>,
    /// Projections of the pooled state, in order.
    dense: Vec<Matrix<'a>>,
    n_ctx_train: usize,
}

enum Body<'a> {
    Encoder(Box<Encoder<'a>>),
    Decoder(Box<Model<'a>>),
    /// Decoder layers in which every token sees the whole input.
    Bidirectional(Box<Model<'a>>),
}

impl<'a> Embedder<'a> {
    /// Loads the model in `file`. Files that do not name a pooling use the
    /// last token, which suits decoder-only models.
    pub fn load(file: &'a dyn TensorSource) -> Result<Embedder<'a>, LoadError> {
        let l = Loader::new(file);
        let arch = file
            .header()
            .architecture()
            .ok_or_else(|| LoadError("file does not name its architecture".into()))?;
        let body = match arch::family(arch).map(|f| f.body) {
            Some(arch::Body::Encoder(load)) => Body::Encoder(Box::new(load(&l, arch)?)),
            Some(arch::Body::Bidirectional(_)) => {
                Body::Bidirectional(Box::new(crate::build(file, &Default::default())?))
            }
            _ => Body::Decoder(Box::new(crate::load(file)?)),
        };
        let mut dense = Vec::new();
        let mut width = l.usize("embedding_length")?;
        for name in ["dense_2.weight", "dense_3.weight"] {
            if let Some(t) = file.header().tensor(name) {
                let rows = t.dims[1] as usize;
                dense.push(l.matrix(name, width, rows)?);
                width = rows;
            }
        }
        if width != l.usize("embedding_length")? {
            return Err(LoadError(
                "dense layers must return to the model width".into(),
            ));
        }
        let pooling = match l.usize_or("pooling_type", 3)? {
            1 => Pooling::Mean,
            2 => Pooling::Cls,
            3 => Pooling::Last,
            4 => Pooling::Rank,
            other => return Err(LoadError(format!("pooling type {other} is not supported"))),
        };
        let classifier = match (pooling, &body) {
            (Pooling::Rank, Body::Decoder(m)) => {
                let labels = file
                    .header()
                    .tensor("cls.output.weight")
                    .map(|t| t.dims[1] as usize)
                    .ok_or_else(|| LoadError("ranking model without cls.output.weight".into()))?;
                if file.header().tensor("cls.output.bias").is_some() {
                    return Err(LoadError("classifier biases are not supported yet".into()));
                }
                Some(l.matrix("cls.output.weight", m.n_embd(), labels)?)
            }
            (Pooling::Rank, Body::Encoder(_)) => {
                return Err(LoadError(
                    "ranking heads on encoders are not supported yet".into(),
                ))
            }
            _ => None,
        };
        Ok(Embedder {
            body,
            pooling,
            classifier,
            dense,
            n_ctx_train: l.usize("context_length")?,
        })
    }

    /// Width of the embeddings.
    pub fn n_embd(&self) -> usize {
        match &self.body {
            Body::Encoder(e) => e.n_embd(),
            Body::Decoder(m) | Body::Bidirectional(m) => m.n_embd(),
        }
    }

    pub fn pooling(&self) -> Pooling {
        self.pooling
    }

    /// The longest input the model was trained on; encoders with learned
    /// positions cannot take more.
    pub fn n_ctx_train(&self) -> usize {
        self.n_ctx_train
    }

    /// One unit-length embedding per input.
    ///
    /// Panics if an input is empty, or if this is a ranking model.
    pub fn embed(&self, inputs: &[&[u32]]) -> Vec<Vec<f32>> {
        assert_ne!(self.pooling, Pooling::Rank, "ranking models score inputs");
        let mut pooled = self.pool(inputs);
        for w in &self.dense {
            for v in &mut pooled {
                let mut out = vec![0.0; w.rows];
                matmul(w, v, &mut out);
                *v = out;
            }
        }
        pooled
            .iter_mut()
            .for_each(|v| l2_norm(v, f32::MIN_POSITIVE));
        pooled
    }

    /// The relevance of each input, a probability. Inputs are usually a
    /// query and a document laid out by the model's rerank template.
    ///
    /// Panics if an input is empty, or if this is not a ranking model.
    pub fn rank(&self, inputs: &[&[u32]]) -> Vec<f32> {
        let head = self.classifier.as_ref().expect("not a ranking model");
        let pooled: Vec<f32> = self.pool(inputs).concat();
        let mut logits = vec![0.0; inputs.len() * head.rows];
        matmul(head, &pooled, &mut logits);
        logits
            .chunks_exact_mut(head.rows)
            .map(|labels| {
                softmax(labels);
                labels[0]
            })
            .collect()
    }

    fn pool(&self, inputs: &[&[u32]]) -> Vec<Vec<f32>> {
        assert!(inputs.iter().all(|t| !t.is_empty()), "empty input");
        let d = self.n_embd();
        match &self.body {
            Body::Encoder(e) => {
                let hidden = e.forward(inputs);
                let mut rest = &hidden[..];
                inputs
                    .iter()
                    .map(|t| {
                        let (rows, tail) = rest.split_at(t.len() * d);
                        rest = tail;
                        self.pool_rows(rows, d)
                    })
                    .collect()
            }
            // shortcut: decoder inputs run one after another, each as one
            // batch; sharing weight passes across inputs needs per-input
            // attention inside a single forward.
            Body::Decoder(m) => inputs
                .iter()
                .map(|t| {
                    let hidden = m.run(&mut m.new_state(), t, false).hidden;
                    self.pool_rows(&hidden, d)
                })
                .collect(),
            Body::Bidirectional(m) => inputs
                .iter()
                .map(|t| self.pool_rows(&gemma_embedding::encode(m, t), d))
                .collect(),
        }
    }

    fn pool_rows(&self, rows: &[f32], d: usize) -> Vec<f32> {
        let n = rows.len() / d;
        match self.pooling {
            Pooling::Mean => {
                let mut sum = vec![0.0; d];
                for row in rows.chunks_exact(d) {
                    sum.iter_mut().zip(row).for_each(|(s, v)| *s += v);
                }
                sum.iter_mut().for_each(|s| *s /= n as f32);
                sum
            }
            Pooling::Cls => rows[..d].to_vec(),
            // Only decoders rank, and they read the last token.
            Pooling::Last | Pooling::Rank => rows[(n - 1) * d..].to_vec(),
        }
    }
}
