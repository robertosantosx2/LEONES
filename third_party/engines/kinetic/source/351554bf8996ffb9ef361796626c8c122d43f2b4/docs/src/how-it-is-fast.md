# How Kinetic is fast

Kinetic gets its speed from doing less work per token, never from changing
the answer. RAD-1, Warm Start and Shortlist give exactly the output plain
decoding gives on the same device, and the test suite checks that on real
models. Flywheel changes where the work of a mixture-of-experts model runs.

Generating one token on a personal computer is limited by memory bandwidth,
not arithmetic: a dense model reads all of its weights once per token. A
4-billion-parameter model in Q4_K_M is about 2.8 GB, so a GPU with 300 GB/s
of bandwidth tops out near 110 tokens per second however fast its cores are.
There are four ways around that wall without touching the answer:

| | Idea | Saves |
|---|---|---|
| [RAD-1](#rad-1-exact-speculative-decoding) | check several guessed tokens in one pass over the weights | passes over the weights |
| [Warm Start](#warm-start) | resume from the state an earlier prompt left behind | prompt processing |
| [Shortlist](#shortlist) | read only the rows of the output layer that can win | reads of the output layer |
| [Flywheel](#flywheel) | keep the experts in use on the GPU, the rest in system memory | GPU memory for MoE models |

None of the ideas is new on its own; the references are below. What
Kinetic adds is that they are exact by construction, on by default and need
nothing from you: no draft model to pick, no cache to size, no flags.

## RAD-1: exact speculative decoding

Speculative decoding (Leviathan et al., 2023; Chen et al., 2023) guesses the
next few tokens cheaply, then runs the model once over all of them. Reading
the weights once costs about the same for one token as for eight, so every
correct guess is a token for free. The model keeps the guesses it agrees
with, adds one token of its own, and the rest are rolled back.

```text
context   ...  let total = count + 1;  ...  rename count to n:  let total =
draft     n      +      1      ;      }          <- guessed, almost free
verify    one pass over the weights scores all five positions
model     n      +      1      ;      \n         <- what plain decoding picks
kept      n      +      1      ;      \n         4 accepted + 1 = 5 tokens, 1 pass
```

### Where the guesses come from

RAD-1 needs no separate draft model. It runs several cheap sources side by
side and lets whichever has lately been right most propose the next draft:

- **The context.** The tokens that followed the last occurrence of the
  current few tokens, as in prompt lookup decoding. Right whenever the
  answer repeats the input: edits of code, quotes, structured output.
- **Earlier requests.** An index of every token the server has seen, across
  requests. Agents resend the same files and tool output over and over;
  this source drafts from all of it.
- **The model's own prediction block.** Some models ship one or more
  multi-token prediction (MTP) layers next to the main model (Gloeckle et
  al., 2024; DeepSeek-V3), as Qwen3.5 does. Kinetic runs that block to draft
  from the model's hidden state, in the spirit of Medusa (Cai et al., 2024)
  and EAGLE (Li et al., 2024). `kinetic info` shows `prediction yes` for such
  files.

A draft can branch into a tree of alternatives, all checked in the same
pass, with each row seeing only its own path (as in SpecInfer, Miao et al.,
2023). Draft length follows how well recent drafts did, and after drafts
that miss outright, drafting pauses for longer and longer, so text that
cannot be guessed costs almost nothing extra.

### Why the output does not change

Verification chooses each token exactly as plain decoding would: from the
same logits, with the same history, by the same rule.

- **Greedy decoding** (`temperature` 0) keeps a guess only when it is the
  model's top token. The output is plain greedy decoding, token for token.
- **Sampling** uses rejection sampling against a drafter that proposes one
  token with certainty: a guess `x` survives with probability `p(x)`, and on
  rejection the token is drawn from `p` without `x`, renormalized. Every
  kept token is drawn from exactly the distribution plain sampling uses, with
  one random number per token in the same order, so the same seed gives the
  same answer with drafting and without.

Both hold only if running eight tokens at once gives each of them the same
numbers as running it alone. Kinetic's kernels are written to be
batch-invariant, bit for bit, and every architecture is tested for it: a
batch must give the logits its tokens give one by one, a tree row the logits
of its path alone, and drafted decoding the tokens of plain decoding.
`kinetic bench` repeats the last check on your machine and prints
`drafted output identical to plain decoding: yes`.

## Warm Start

Chat clients and agents send the whole conversation with every request:
the same system prompt, the same tool definitions, the same history, and a
few new tokens at the end. Without a cache, every request pays for all of it
again.

```text
request 1   [system prompt][tools][user: fix the bug        ]
request 2   [system prompt][tools][user: fix the bug][answer][user: now add a test]
            |<---------- resumed from request 1's state ---------->|<-- runs -->|
```

Warm Start keeps the states that earlier prompts left behind and starts each
new prompt from the longest prefix it can return to exactly. This is prefix
caching, as in vLLM and SGLang, and llama.cpp's prompt cache.

Attention layers can be cut back to any length. Recurrent layers, such as
the Gated DeltaNet layers of Qwen3.5, the short convolutions of LFM2 and
LFM3 and the Mamba-2 layers of Granite 4.0 H and Falcon-H1, cannot be rewound;
for those Kinetic records a snapshot every 256 tokens (or a larger multiple
when a snapshot is large next to what it saves), and resumes from the last
snapshot before the prompts part.

- States are kept in memory (up to 1 GiB) and in your cache directory (up
  to 2 GiB, least recently used out first), so they survive a restart.
- A state is restored only when the prompt processing it saves outweighs
  restoring it, at speeds Kinetic measures as it goes; files are written in
  the background.
- A restored state is bit for bit the state its run left behind, and prompts
  are split into the same batches cold or warm, so a warm start gives
  exactly the answer of a cold one.

The `usage.prompt_tokens_details.cached_tokens` field of a server response
says how many prompt tokens were not recomputed. `--no-prompt-cache` turns
Warm Start off and `--cache-dir` moves it; see the [command line](cli.md).

## Zero Wait

Warm Start makes the history free; the message itself still has to run
after Enter, and a pasted 20,000-token document takes seconds. Zero Wait
runs it while it is being written:

```text
typing      [history][user: <pasted document> What does the second sec|
running     [history][user: <pasted document> What does the]           ahead, in batches
after Enter                                          [ second section say?][assistant]
```

`kinetic chat` sends every edit to a thread that runs the conversation up
to just before the last word of the message (its tokens may still merge
with the next keystroke) and never the end of the turn. Apps do the same
through [`/v1/prefill`](server.md#prefill).

- It runs only the whole batches the request would run first, from where
  the request would start, so the request continues with exactly the
  batches it would have run itself and gives exactly the same answer.
- When earlier text changes, it cuts back to the last batch both still
  share; on models with recurrent layers it records a snapshot where it
  started and on the Warm Start grid to return to.
- It gives way after every batch: a request never waits for more than one.
  Input never waits at all, since the model runs on its own thread.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/zero-wait-dark.svg">
  <img src="diagrams/zero-wait-light.svg" alt="Two timelines of typing and processing: without Zero Wait the document is processed after Enter, an 11 s wait; with it the document and each typed word are processed while you type, and the answer starts 0.13 s after Enter" width="100%">
</picture>
</p>

## Shortlist

Choosing the next token normally reads the whole output layer: one row of
weights per entry of a vocabulary that can be a quarter of a million tokens
long. In a small model that layer is a large share of all the bytes read per
token.

Shortlist keeps a smaller Q4_K copy of the output layer with a proven bound
on the error of every row. Each token then:

1. scores every row with the copy, which gives an upper bound for each row's
   true score;
2. computes the exact scores of the best-looking rows with the original
   weights, which gives a floor the winners cannot be below;
3. computes exact scores for the few other rows whose bound reaches that
   floor, and skips the rest.

```text
copy score + bound    ████████▌   ███████▌   ██████▏   ███▊   ██▍   ...   (250k rows)
exact floor           ─────────────────────────┤
exact scores for      row 1, row 2, row 3                 skipped: everything below the floor
```

The chosen tokens, their order and their scores are those of the full layer,
bit for bit, because every exact score comes from the layer's own kernel.
Shortlist serves greedy decoding, top-k sampling and draft verification. It
works on the CPU, for output layers stored as Q6_K or Q8_0.

## Flywheel

A mixture-of-experts (MoE) model has many expert feed-forward blocks per
layer and uses only a few of them for each token: Qwen3.5-35B-A3B uses about
3 billion of its 35 billion parameters per token. The model is large, but the
work per token is small, if the right experts are at hand.

```text
GPU memory    [attention, shared weights, KV cache][ expert cache: the experts in use ]
system RAM    [ every expert, memory-mapped from the model file                     ]

per layer     the router picks a few experts
              in the cache   -> run on the GPU
              not in cache   -> run on the CPU, or copy to the GPU, whichever is cheaper now
              next layer     -> likely experts prefetched while this one runs
```

Flywheel gives the experts all the GPU memory left after the rest of the
model, one sequence's state and a reserve. It measures how fast the CPU runs
an expert and how fast one copies to the GPU, keeps adjusting for other
programs that slow the CPU down, and splits the work accordingly. When every
expert fits, routing happens on the GPU and each one-token step runs as one
recorded CUDA graph. Expert offloading itself is known (for example Eliseev
and Mazur, 2023, and llama.cpp's `--override-tensor`); Flywheel makes the
placement automatic.

See [Devices and offload](devices.md) for what runs where.

## References

- Leviathan, Kalman, Matias. *Fast Inference from Transformers via
  Speculative Decoding.* ICML 2023. [arXiv:2211.17192](https://arxiv.org/abs/2211.17192)
- Chen, Borgeaud, Irving, Lespiau, Sifre, Jumper. *Accelerating Large
  Language Model Decoding with Speculative Sampling.* 2023.
  [arXiv:2302.01318](https://arxiv.org/abs/2302.01318)
- Miao et al. *SpecInfer: Accelerating Generative Large Language Model
  Serving with Tree-based Speculative Inference and Verification.* ASPLOS
  2024. [arXiv:2305.09781](https://arxiv.org/abs/2305.09781)
- Cai et al. *Medusa: Simple LLM Inference Acceleration Framework with
  Multiple Decoding Heads.* ICML 2024. [arXiv:2401.10774](https://arxiv.org/abs/2401.10774)
- Li, Wei, Zhang, Zhang. *EAGLE: Speculative Sampling Requires Rethinking
  Feature Uncertainty.* ICML 2024. [arXiv:2401.15077](https://arxiv.org/abs/2401.15077)
- Gloeckle et al. *Better & Faster Large Language Models via Multi-token
  Prediction.* ICML 2024. [arXiv:2404.19737](https://arxiv.org/abs/2404.19737)
- DeepSeek-AI. *DeepSeek-V3 Technical Report.* 2024.
  [arXiv:2412.19437](https://arxiv.org/abs/2412.19437)
- Saxena. *Prompt Lookup Decoding.* 2023.
  [github.com/apoorvumang/prompt-lookup-decoding](https://github.com/apoorvumang/prompt-lookup-decoding)
- Kwon et al. *Efficient Memory Management for Large Language Model Serving
  with PagedAttention* (vLLM). SOSP 2023. [arXiv:2309.06180](https://arxiv.org/abs/2309.06180)
- Zheng et al. *SGLang: Efficient Execution of Structured Language Model
  Programs.* NeurIPS 2024. [arXiv:2312.07104](https://arxiv.org/abs/2312.07104)
- Eliseev, Mazur. *Fast Inference of Mixture-of-Experts Language Models with
  Offloading.* 2023. [arXiv:2312.17238](https://arxiv.org/abs/2312.17238)
- [llama.cpp](https://github.com/ggml-org/llama.cpp) and
  [ggml](https://github.com/ggml-org/ggml), which define the GGUF format
  and its quantization types.
