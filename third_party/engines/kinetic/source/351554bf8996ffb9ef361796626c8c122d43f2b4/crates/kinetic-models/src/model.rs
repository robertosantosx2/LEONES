use std::sync::{Arc, OnceLock};

use kinetic_cpu::{matmul, pool, rms_norm};
use kinetic_quant::{dequantize_row, Matrix};

use crate::blocks::{end_lending, lend_kv, Folding, Mixer, MixerState, Moe, Part, SwiGlu, Tree};
use crate::convoy::{Convoy, Seat};
use crate::head::Shortlist;
use crate::per_layer::PerLayer;

/// One decoder layer: a token mixer and a feed-forward network, each with
/// optional normalization of its input and output, an optional scale, and
/// a residual connection. In a mixture-of-experts layer the feed-forward
/// is the routed experts plus, if the model has one, a shared expert.
pub(crate) struct Layer<'a> {
    pub mixer_norm: Option<Vec<f32>>,
    pub mixer: Mixer<'a>,
    pub mixer_out_norm: Option<Vec<f32>>,
    pub ffn_norm: Option<Vec<f32>>,
    pub ffn: Option<SwiGlu<'a>>,
    pub experts: Option<Moe<'a>>,
    pub ffn_out_norm: Option<Vec<f32>>,
    /// Multiplies the mixer and feed-forward outputs before they join the
    /// residual stream.
    pub residual_scale: Option<f32>,
}

impl Layer<'_> {
    /// The width of the hidden state.
    pub(crate) fn width(&self) -> usize {
        match (&self.ffn, &self.experts) {
            (Some(f), _) => f.down.rows,
            (None, Some(moe)) => moe.router.cols,
            (None, None) => unreachable!("a layer has a feed-forward"),
        }
    }

    /// Applies the layer to `x`, rows of hidden states, in place.
    pub(crate) fn forward(
        &self,
        x: &mut [f32],
        eps: f32,
        pos0: usize,
        grid: Option<&[[usize; 3]]>,
        tree: Option<&Tree>,
        state: &mut MixerState,
    ) {
        self.forward_with(x, eps, |h| self.mixer.forward(h, pos0, grid, tree, state));
    }

    /// [`Layer::forward`] on a batch made of `parts`, each on its own state.
    fn forward_parts(&self, x: &mut [f32], eps: f32, parts: &mut [Part]) {
        self.forward_with(x, eps, |h| self.mixer.forward_parts(h, parts));
    }

    /// [`Layer::forward`] with `mix` in place of the mixer.
    pub(crate) fn forward_with(
        &self,
        x: &mut [f32],
        eps: f32,
        mix: impl FnOnce(&[f32]) -> Vec<f32>,
    ) {
        let d = self.width();
        let norm = |x: &mut [f32], w: &Option<Vec<f32>>| {
            if let Some(w) = w {
                pool::for_each_chunk(x, d, |_, row| rms_norm(row, w, eps));
            }
        };
        let scale = self.residual_scale.unwrap_or(1.0);
        let add = |x: &mut [f32], y: &[f32]| {
            pool::for_each_chunk(x, d, |t, row| {
                row.iter_mut()
                    .zip(&y[t * d..])
                    .for_each(|(x, y)| *x += y * scale)
            })
        };
        let mut h = x.to_vec();
        norm(&mut h, &self.mixer_norm);
        let mut mixed = mix(&h);
        norm(&mut mixed, &self.mixer_out_norm);
        add(x, &mixed);

        h.copy_from_slice(x);
        norm(&mut h, &self.ffn_norm);
        let mut ffn = match &self.ffn {
            Some(f) => f.forward(&h),
            None => vec![0.0; h.len()],
        };
        if let Some(moe) = &self.experts {
            moe.forward(&h, &mut ffn);
        }
        norm(&mut ffn, &self.ffn_out_norm);
        add(x, &ffn);
    }
}

/// A multi-token prediction block: from the final hidden state at one
/// position and the token after it, it predicts the token after that.
pub(crate) struct Mtp<'a> {
    /// Projects the normalized token embedding followed by the normalized
    /// hidden state down to one hidden state.
    pub eh_proj: Matrix<'a>,
    pub embd_norm: Vec<f32>,
    pub hidden_norm: Vec<f32>,
    pub layer: Layer<'a>,
    pub head_norm: Vec<f32>,
}

/// Memory left to other programs when the experts are paged in.
const PAGE_IN_SPARE: u64 = 3 << 30;

/// A decoder-only language model with weights borrowed from its file.
pub struct Model<'a> {
    pub(crate) n_embd: usize,
    pub(crate) eps: f32,
    pub(crate) embd: Matrix<'a>,
    /// Multiplies every token embedding, for models trained that way.
    pub(crate) embd_scale: Option<f32>,
    /// Set when the embedding table was stored folded.
    pub(crate) embd_folding: Option<Arc<Folding>>,
    pub(crate) output: Matrix<'a>,
    /// Set when the output head was stored folded.
    pub(crate) head_folding: Option<Arc<Folding>>,
    /// Whether any weight was stored folded.
    #[cfg(any(feature = "cuda", feature = "vulkan"))]
    pub(crate) folded: bool,
    pub(crate) output_norm: Vec<f32>,
    /// Logits pass through `cap * tanh(logit / cap)`.
    pub(crate) logit_cap: Option<f32>,
    pub(crate) layers: Vec<Layer<'a>>,
    pub(crate) per_layer: Option<PerLayer<'a>>,
    pub(crate) mtp: Option<Mtp<'a>>,
    /// Whether attention takes (time, row, column) rotary positions, which
    /// give an image fewer positions than it has tokens.
    pub(crate) grid_rope: bool,
    /// Built on first use by [`Model::run_top`].
    pub(crate) shortlist: OnceLock<Option<Shortlist>>,
    /// Gathers the runs of sequences that hold a [`Seat`] into shared passes.
    pub(crate) convoy: Convoy<Lane, (State, Forward)>,
}

/// One sequence's run in a pass that several share.
pub(crate) struct Lane {
    state: State,
    /// Input embeddings, `n_embd` values per row.
    x: Vec<f32>,
    /// Per-layer inputs of the rows, when the model has them.
    inputs: Vec<f32>,
    all_logits: bool,
    top: Option<usize>,
}

/// Everything a sequence carries between calls. A clone is an exact copy
/// that continues independently.
#[derive(Clone)]
pub struct State {
    pub(crate) pos: usize,
    checkpoint: Option<usize>,
    pub(crate) layers: Vec<MixerState>,
    /// Earlier lengths [`Model::truncate`] can return to, oldest first.
    pub(crate) marks: Vec<Mark>,
    /// For every image run with grid positions: the length after it, and
    /// how far rotary positions then lag behind the length.
    pub(crate) image_shifts: Vec<(usize, usize)>,
}

/// A copy, at one length, of every layer state that cannot be cut back in
/// place; `None` for the others.
#[derive(Clone)]
pub(crate) struct Mark {
    pub pos: usize,
    pub layers: Vec<Option<MixerState>>,
}

impl State {
    /// A state of no layers, which holds the place of one that is away in
    /// a shared pass.
    fn placeholder() -> State {
        State {
            pos: 0,
            checkpoint: None,
            layers: Vec::new(),
            marks: Vec::new(),
            image_shifts: Vec::new(),
        }
    }

    /// Number of tokens processed so far.
    pub fn len(&self) -> usize {
        self.pos
    }

    pub fn is_empty(&self) -> bool {
        self.pos == 0
    }

    /// How far the rotary position of the next token lags behind
    /// [`State::len`].
    pub(crate) fn rope_shift(&self) -> usize {
        self.image_shifts.last().map_or(0, |s| s.1)
    }

    /// The lengths saved by [`Model::mark`], oldest first.
    pub fn marks(&self) -> impl Iterator<Item = usize> + '_ {
        self.marks.iter().map(|m| m.pos)
    }

    /// Drops every mark, so [`Model::truncate`] returns only to the current
    /// length or zero, unless every layer cuts back in place.
    pub fn forget_marks(&mut self) {
        self.marks.clear();
    }
}

/// The result of running a batch: logits for the requested rows and the
/// normalized final hidden state of every token.
pub struct Forward {
    pub logits: Vec<f32>,
    pub hidden: Vec<f32>,
}

/// The cache of a model's prediction block, one entry per position fed.
pub struct MtpState {
    len: usize,
    cache: MixerState,
}

impl MtpState {
    /// Number of positions fed so far.
    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
}

impl Model<'_> {
    pub fn n_vocab(&self) -> usize {
        self.output.rows
    }

    pub fn n_embd(&self) -> usize {
        self.n_embd
    }

    pub fn n_layers(&self) -> usize {
        self.layers.len()
    }

    /// Reads the routed experts of a mixture-of-experts model into memory,
    /// which later tokens would otherwise fault in page by page, when the
    /// system has room for them and 3 GiB more. Best done after anything
    /// else is read from the file.
    pub fn page_in_experts(&self) {
        let experts = || self.layers.iter().filter_map(|l| l.experts.as_ref());
        let bytes: u64 = experts()
            .flat_map(|m| [m.gate.data.len(), m.up.data.len(), m.down.data.len()])
            .map(|n| n as u64)
            .sum();
        // Reading what does not fit would push out other programs' memory
        // and then the experts' own first pages.
        if bytes > 0 && crate::memory::available().is_some_and(|a| a >= bytes + PAGE_IN_SPARE) {
            experts().for_each(crate::blocks::Moe::page_in);
        }
    }

    /// Bytes of the state of a sequence `len` tokens long.
    pub fn state_bytes(&self, len: usize) -> usize {
        self.layers.iter().map(|l| l.mixer.state_bytes(len)).sum()
    }

    /// An empty state for a new sequence.
    pub fn new_state(&self) -> State {
        State {
            pos: 0,
            checkpoint: None,
            layers: self.layers.iter().map(|l| l.mixer.new_state()).collect(),
            marks: Vec::new(),
            image_shifts: Vec::new(),
        }
    }

    /// Runs one token and returns the logits for the next.
    pub fn forward(&self, state: &mut State, token: u32) -> Vec<f32> {
        self.forward_batch(state, &[token])
    }

    /// Runs `tokens` in order and returns the logits after the last one.
    /// Weights are read once per batch, so prompts should go through here
    /// rather than token by token.
    pub fn forward_batch(&self, state: &mut State, tokens: &[u32]) -> Vec<f32> {
        self.run(state, tokens, false).logits
    }

    /// Runs `tokens` in order. With `all_logits` the logits after every
    /// token are returned, `tokens.len()` rows of [`Model::n_vocab`] values,
    /// and the output head reads its weights once for all of them; otherwise
    /// only those after the last token.
    pub fn run(&self, state: &mut State, tokens: &[u32], all_logits: bool) -> Forward {
        assert!(!tokens.is_empty(), "empty batch");
        self.run_rows(state, self.embed(tokens), tokens, None, all_logits)
    }

    /// [`Model::run`] from input embeddings, `n_embd` values per position,
    /// optionally with a (time, row, column) rotary position for each.
    /// `tokens` gives each row's token for per-layer inputs.
    pub(crate) fn run_rows(
        &self,
        state: &mut State,
        x: Vec<f32>,
        tokens: &[u32],
        grid: Option<&[[usize; 3]]>,
        all_logits: bool,
    ) -> Forward {
        self.run_layers(state, x, tokens, grid, None, all_logits, None)
    }

    /// [`Model::run`] for a choice that depends only on the `top` highest
    /// logits of a row and their values, ties going to the lower token, as
    /// greedy decoding and top-k sampling do. Each row's logits are exact
    /// for a set of tokens that holds those, which is usually small, and
    /// negative infinity for every other token.
    pub fn run_top(
        &self,
        state: &mut State,
        tokens: &[u32],
        all_logits: bool,
        top: usize,
    ) -> Forward {
        assert!(!tokens.is_empty(), "empty batch");
        let x = self.embed(tokens);
        self.run_layers(state, x, tokens, None, None, all_logits, Some(top))
    }

    /// Runs a tree of tokens in one batch inside a checkpoint: token `i`
    /// follows token `parents[i]`, an earlier one, or the tokens already run
    /// when `None`. Returns logits for every token, each exactly what
    /// running its path from the root alone gives. Follow it with
    /// [`Model::rollback_rows`] to keep one path.
    pub fn run_tree(
        &self,
        state: &mut State,
        tokens: &[u32],
        parents: &[Option<usize>],
    ) -> Forward {
        assert!(state.checkpoint.is_some(), "tree outside a checkpoint");
        assert_eq!(tokens.len(), parents.len());
        let tree = Tree::new(parents);
        let x = self.embed(tokens);
        self.run_layers(state, x, tokens, None, Some(&tree), true, None)
    }

    /// Takes a seat for one sequence: while it is held, runs of this model
    /// from other threads wait for that sequence's next run, up to a few
    /// milliseconds, and go through the weights together with it. Every row
    /// of a shared pass comes out exactly as running its sequence alone
    /// gives it, so seats change speed, never output.
    pub fn seat(&self) -> Seat<'_> {
        self.convoy.seat()
    }

    #[allow(clippy::too_many_arguments)]
    fn run_layers(
        &self,
        state: &mut State,
        x: Vec<f32>,
        tokens: &[u32],
        grid: Option<&[[usize; 3]]>,
        tree: Option<&Tree>,
        all_logits: bool,
        top: Option<usize>,
    ) -> Forward {
        let inputs = self
            .per_layer
            .as_ref()
            .map_or_else(Vec::new, |p| p.inputs(tokens, &x, self.eps));
        if grid.is_some() || tree.is_some() {
            return self.run_alone(state, x, &inputs, grid, tree, all_logits, top);
        }
        let lane = Lane {
            state: std::mem::replace(state, State::placeholder()),
            x,
            inputs,
            all_logits,
            top,
        };
        let (done, forward) = self.convoy.run(lane, |lanes| self.run_lanes(lanes));
        *state = done;
        forward
    }

    /// Runs the lanes of one pass: a lone one as it always runs, several
    /// with every weight read once for all of their rows.
    fn run_lanes(&self, mut lanes: Vec<Lane>) -> Vec<(State, Forward)> {
        if let [lane] = &mut lanes[..] {
            let (x, all, top) = (std::mem::take(&mut lane.x), lane.all_logits, lane.top);
            let inputs = std::mem::take(&mut lane.inputs);
            let forward = self.run_alone(&mut lane.state, x, &inputs, None, None, all, top);
            let lane = lanes.pop().expect("one lane");
            return vec![(lane.state, forward)];
        }
        let d = self.n_embd;
        let rows: Vec<usize> = lanes.iter().map(|l| l.x.len() / d).collect();
        let pos0: Vec<usize> = lanes
            .iter()
            .map(|l| l.state.pos - l.state.rope_shift())
            .collect();
        let mut x: Vec<f32> = lanes
            .iter_mut()
            .flat_map(|l| std::mem::take(&mut l.x))
            .collect();
        let inputs: Vec<f32> = lanes
            .iter_mut()
            .flat_map(|l| std::mem::take(&mut l.inputs))
            .collect();
        for (i, layer) in self.layers.iter().enumerate() {
            if let Some(from) = layer.mixer.kv_source() {
                lanes
                    .iter_mut()
                    .for_each(|l| lend_kv(&mut l.state.layers, from, i));
            }
            let mut parts: Vec<Part> = lanes
                .iter_mut()
                .zip(&rows)
                .zip(&pos0)
                .map(|((l, &rows), &pos0)| Part {
                    rows,
                    pos0,
                    state: &mut l.state.layers[i],
                })
                .collect();
            layer.forward_parts(&mut x, self.eps, &mut parts);
            if let Some(p) = &self.per_layer {
                p.apply(i, &mut x, &inputs, self.eps);
            }
        }
        lanes
            .iter_mut()
            .for_each(|l| end_lending(&mut l.state.layers));
        self.norm_rows(&mut x, &self.output_norm);

        // Rows of each lane given to the head, and their logits.
        let mut starts = Vec::with_capacity(lanes.len());
        let mut at = 0;
        for &n in &rows {
            starts.push(at);
            at += n;
        }
        let heads: Vec<std::ops::Range<usize>> = lanes
            .iter()
            .zip(&rows)
            .zip(&starts)
            .map(|((l, &n), &s)| {
                if l.all_logits {
                    s..s + n
                } else {
                    s + n - 1..s + n
                }
            })
            .collect();
        let mut logits: Vec<Vec<f32>> = vec![Vec::new(); lanes.len()];
        let mut tops: Vec<Option<usize>> = lanes.iter().map(|l| l.top).collect();
        tops.sort_unstable();
        tops.dedup();
        for top in tops {
            let group: Vec<usize> = (0..lanes.len()).filter(|&i| lanes[i].top == top).collect();
            let input: Vec<f32> = group
                .iter()
                .flat_map(|&i| &x[heads[i].start * d..heads[i].end * d])
                .copied()
                .collect();
            let out = match top {
                Some(top) => self.head_top(&input, top),
                None => self.head(&input),
            };
            let vocab = self.n_vocab();
            let mut out = &out[..];
            for &i in &group {
                let (mine, rest) = out.split_at(heads[i].len() * vocab);
                logits[i] = mine.to_vec();
                out = rest;
            }
        }

        let mut hidden = &x[..];
        lanes
            .into_iter()
            .zip(rows)
            .zip(logits)
            .map(|((mut l, n), logits)| {
                l.state.pos += n;
                let (mine, rest) = hidden.split_at(n * d);
                hidden = rest;
                let forward = Forward {
                    logits,
                    hidden: mine.to_vec(),
                };
                (l.state, forward)
            })
            .collect()
    }

    #[allow(clippy::too_many_arguments)]
    fn run_alone(
        &self,
        state: &mut State,
        mut x: Vec<f32>,
        inputs: &[f32],
        grid: Option<&[[usize; 3]]>,
        tree: Option<&Tree>,
        all_logits: bool,
        top: Option<usize>,
    ) -> Forward {
        let d = self.n_embd;
        let pos0 = state.pos - state.rope_shift();
        for (i, layer) in self.layers.iter().enumerate() {
            if let Some(from) = layer.mixer.kv_source() {
                lend_kv(&mut state.layers, from, i);
            }
            layer.forward(&mut x, self.eps, pos0, grid, tree, &mut state.layers[i]);
            if let Some(p) = &self.per_layer {
                p.apply(i, &mut x, inputs, self.eps);
            }
        }
        end_lending(&mut state.layers);
        state.pos += x.len() / d;

        self.norm_rows(&mut x, &self.output_norm);
        let rows = if all_logits {
            &x[..]
        } else {
            &x[x.len() - d..]
        };
        Forward {
            logits: match top {
                Some(top) => self.head_top(rows, top),
                None => self.head(rows),
            },
            hidden: x,
        }
    }

    /// Marks the current length so a later [`Model::rollback`] can return to
    /// any point after it.
    pub fn checkpoint(&self, state: &mut State) {
        state.checkpoint = Some(state.pos);
        state.layers.iter_mut().for_each(MixerState::checkpoint);
    }

    /// Keeps the first `keep` tokens run since the checkpoint and discards
    /// the rest, leaving the state exactly as if they had never run.
    pub fn rollback(&self, state: &mut State, keep: usize) {
        self.rollback_rows(state, &Vec::from_iter(0..keep));
    }

    /// Keeps `rows`, an increasing path through the tokens run since the
    /// checkpoint, such as one root-to-node path of [`Model::run_tree`],
    /// leaving the state exactly as if only they had run.
    pub fn rollback_rows(&self, state: &mut State, rows: &[usize]) {
        let start = state
            .checkpoint
            .take()
            .expect("rollback without a checkpoint");
        assert!(
            rows.windows(2).all(|w| w[0] < w[1])
                && rows.last().is_none_or(|&r| start + r < state.pos),
            "rows must increase and have run"
        );
        for (layer, ls) in self.layers.iter().zip(&mut state.layers) {
            layer.mixer.rollback(ls, rows);
        }
        state.pos = start + rows.len();
        state.marks.retain(|m| m.pos <= state.pos);
        state.image_shifts.retain(|&(end, _)| end <= state.pos);
    }

    /// Saves what [`Model::truncate`] needs to return to the current length
    /// later: a copy of each recurrent or windowed layer state. Attention
    /// caches of every position are cut back instead, so on a model made of
    /// only those a mark costs nothing.
    pub fn mark(&self, state: &mut State) {
        assert!(state.checkpoint.is_none(), "mark inside a checkpoint");
        if state.marks.last().is_some_and(|m| m.pos == state.pos) {
            return;
        }
        let layers = self
            .layers
            .iter()
            .zip(&state.layers)
            .map(|(l, s)| l.mixer.needs_mark().then(|| s.clone()))
            .collect();
        state.marks.push(Mark {
            pos: state.pos,
            layers,
        });
    }

    /// The longest length up to `len` that [`Model::truncate`] returns
    /// `state` to: `len` itself when every layer cuts back in place,
    /// otherwise the latest mark at or before it, or zero.
    pub fn reach(&self, state: &State, len: usize) -> usize {
        let len = len.min(state.pos);
        let in_place = self
            .layers
            .iter()
            .all(|l| l.mixer.truncates_in_place(state.pos));
        if len == state.pos || in_place {
            return len;
        }
        state
            .marks
            .iter()
            .map(|m| m.pos)
            .filter(|&p| p <= len)
            .max()
            .unwrap_or(0)
    }

    /// Returns `state` to the length [`Model::reach`] gives for `len` and
    /// returns that length. Every value left is exactly what the batches
    /// that ran those tokens produced; marks after the length are dropped.
    pub fn truncate(&self, state: &mut State, len: usize) -> usize {
        assert!(state.checkpoint.is_none(), "truncate inside a checkpoint");
        let to = self.reach(state, len);
        if to == state.pos {
            return to;
        }
        if to == 0 {
            *state = self.new_state();
            return 0;
        }
        let mark = state.marks.iter().position(|m| m.pos == to);
        for (i, (layer, ls)) in self.layers.iter().zip(&mut state.layers).enumerate() {
            match mark.and_then(|m| state.marks[m].layers[i].as_ref()) {
                Some(saved) => *ls = saved.clone(),
                None => layer.mixer.truncate(ls, to),
            }
        }
        state.marks.retain(|m| m.pos <= to);
        state.image_shifts.retain(|&(end, _)| end <= to);
        state.pos = to;
        to
    }

    /// Turns Shortlist off: every token's score reads the whole output layer.
    /// Takes effect only before the first token is chosen.
    pub fn disable_shortlist(&self) {
        let _ = self.shortlist.set(None);
    }

    /// Whether the model has a prediction block.
    pub fn has_mtp(&self) -> bool {
        self.mtp.is_some()
    }

    pub fn new_mtp_state(&self) -> Option<MtpState> {
        let mtp = self.mtp.as_ref()?;
        Some(MtpState {
            len: 0,
            cache: mtp.layer.mixer.new_state(),
        })
    }

    /// Feeds the prediction block one entry per row: the normalized hidden
    /// state at a position and the token that followed it. Returns the
    /// block's output after the last row, normalized for the output head;
    /// pass it to [`Model::draft_logits`] for a prediction or back in here to
    /// chain the block.
    ///
    /// Panics if the model has no prediction block.
    pub fn mtp_forward(&self, state: &mut MtpState, hidden: &[f32], tokens: &[u32]) -> Vec<f32> {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        let d = self.n_embd;
        assert_eq!(hidden.len(), tokens.len() * d);
        let mut e = self.embed(tokens);
        self.norm_rows(&mut e, &mtp.embd_norm);
        let mut h = hidden.to_vec();
        self.norm_rows(&mut h, &mtp.hidden_norm);
        let joined: Vec<f32> = e
            .chunks_exact(d)
            .zip(h.chunks_exact(d))
            .flat_map(|(e, h)| e.iter().chain(h))
            .copied()
            .collect();
        let mut x = vec![0.0; tokens.len() * d];
        matmul(&mtp.eh_proj, &joined, &mut x);

        mtp.layer
            .forward(&mut x, self.eps, state.len, None, None, &mut state.cache);
        state.len += tokens.len();

        let mut last = x.split_off((tokens.len() - 1) * d);
        rms_norm(&mut last, &mtp.head_norm, self.eps);
        last
    }

    /// Output-head logits for only the first `vocab` tokens. Byte-pair
    /// vocabularies put their most frequent merges first, so this is a
    /// cheap, approximate head for drafts, which never need to be exact.
    pub fn draft_logits(&self, hidden: &[f32], vocab: usize) -> Vec<f32> {
        let head = self.output.top_rows(vocab);
        let hidden = self.head_input(hidden);
        let mut logits = vec![0.0; hidden.len() / self.n_embd * head.rows];
        matmul(&head, &hidden, &mut logits);
        logits
    }

    pub fn mtp_checkpoint(&self, state: &mut MtpState) {
        state.cache.checkpoint();
    }

    /// Drops every entry fed since the last [`Model::mtp_checkpoint`] after
    /// the first `keep`.
    pub fn mtp_rollback(&self, state: &mut MtpState, fed: usize, keep: usize) {
        let mtp = self.mtp.as_ref().expect("model has no prediction block");
        mtp.layer
            .mixer
            .rollback(&mut state.cache, &Vec::from_iter(0..keep));
        state.len -= fed - keep;
    }

    pub(crate) fn embed(&self, tokens: &[u32]) -> Vec<f32> {
        let mut x = vec![0.0; tokens.len() * self.n_embd];
        embed_into(&self.embd, self.embd_scale, tokens, &mut x);
        if let Some(f) = &self.embd_folding {
            f.restore(&mut x, self.n_embd);
        }
        x
    }

    /// What the output head multiplies, given normalized hidden states.
    fn head_input<'h>(&self, rows: &'h [f32]) -> std::borrow::Cow<'h, [f32]> {
        match &self.head_folding {
            Some(f) => f.rotate(rows, self.n_embd).into(),
            None => rows.into(),
        }
    }

    fn head(&self, rows: &[f32]) -> Vec<f32> {
        self.folded_head(&self.head_input(rows))
    }

    fn folded_head(&self, rows: &[f32]) -> Vec<f32> {
        let mut logits = vec![0.0; rows.len() / self.n_embd * self.n_vocab()];
        matmul(&self.output, rows, &mut logits);
        self.cap(&mut logits);
        logits
    }

    fn head_top(&self, rows: &[f32], top: usize) -> Vec<f32> {
        let shortlist = self
            .shortlist
            .get_or_init(|| Shortlist::build(&self.output));
        let rows = &self.head_input(rows)[..];
        let logits = shortlist
            .as_ref()
            .filter(|_| top * 8 < self.n_vocab())
            .and_then(|s| s.logits(&self.output, rows, top));
        match logits {
            Some(mut logits) => {
                self.cap(&mut logits);
                logits
            }
            None => self.folded_head(rows),
        }
    }

    pub(crate) fn cap(&self, logits: &mut [f32]) {
        if let Some(cap) = self.logit_cap {
            pool::for_each_chunk(logits, 1 << 14, |_, c| {
                c.iter_mut().for_each(|l| *l = cap * (*l / cap).tanh())
            });
        }
    }

    fn norm_rows(&self, x: &mut [f32], w: &[f32]) {
        pool::for_each_chunk(x, self.n_embd, |_, row| rms_norm(row, w, self.eps));
    }
}

/// Writes the embeddings of `tokens`, rows of `embd` times `scale`, to `x`.
pub(crate) fn embed_into(embd: &Matrix, scale: Option<f32>, tokens: &[u32], x: &mut [f32]) {
    for (&token, x) in tokens.iter().zip(x.chunks_exact_mut(embd.cols)) {
        dequantize_row(embd.ty, embd.data, token as usize, x).expect("embedding type");
    }
    if let Some(scale) = scale {
        x.iter_mut().for_each(|v| *v *= scale);
    }
}
