# Local model comparison for REDIL — November 2026

> **Document type:** comparative research and record of upstream benchmarks and local measurements.  
> **Cut-off date:** 7 November 2026.  
> **Scope:** Qwen3.5-4B, Qwen3-30B-A3B, Qwen3.5-35B-A3B, LFM3-1.7B and TwIL-8B.  
> **REDIL relevance:** model selection and specialist assignment for a future distributed local-AI service architecture.  
> **Status:** documentary evaluation plus the author's local experimental results. This is not a REDIL deployment validation or a normalized cross-model benchmark.

## 1. Executive summary

These five models are not interchangeable. Available evidence supports a specialist architecture:

- **Qwen3.5-35B-A3B:** leading candidate for advanced general reasoning, vision, documents and video understanding.
- **Qwen3.5-4B:** compact multimodal generalist with an attractive balance of quality and local speed.
- **LFM3-1.7B (text checkpoint):** candidate for lightweight agents, tool use, classification and low-cost automation.
- **TwIL-8B:** text specialist for mathematics, programming and instruction following; not a general knowledge model equivalent to Qwen3.5.
- **Qwen3-30B-A3B:** previous-generation text MoE reference, useful for runtime and reasoning experiments.

The preliminary REDIL recommendation is to keep Qwen3.5-35B-A3B, Qwen3.5-4B and LFM3-1.7B as the core evaluation set; add TwIL-8B as a specialist and retain Qwen3-30B-A3B as an experimental reference.

## 2. Identity, architecture and context

| Model | Parameters / architecture | Published context | Input/output of checkpoint considered | Specialty |
|---|---|---:|---|---|
| Qwen3.5-4B | Approx. 4.7B; dense | 262,144 | Text + image; video through frame sequences; text output | Compact multimodal generalist, reasoning, OCR/documents, agents |
| Qwen3-30B-A3B | 30.5B total; 3.3B active; MoE, 128 experts and 8 active in Thinking-2507 | Up to 262,144 in Thinking-2507; verify exact variant | Text → text | Reasoning, knowledge, math, code and tool use |
| Qwen3.5-35B-A3B | 35B total; 3B active; MoE with 256 experts, 8 routed + 1 shared | 262,144 native; model card says extensible to 1,010,000 | Text + image; video through frames; text output | Advanced reasoning, vision-language, documents, video and agents |
| LFM3-1.7B | 1.73B; tri-hybrid architecture (convolutions, local and global attention) | 256K | **The tested checkpoint is text → text** | Local agents, tool calls, specialized tasks and edge |
| TwIL-8B | 8.79B; dense Transformer based on Granite 4.2 8B | 131,072 | Text → text; English per model card | Contest math, code and instruction following |

**Variant caution:** Qwen3-30B-A3B has thinking and non-thinking variants and later revisions (e.g. Instruct-2507 and Thinking-2507). The benchmark figures below for Thinking-2507 are official reference results for that revision, not a claim that the user's local artifact is identical. TwIL-8B has `balanced` and `verbose` variants; its model card explicitly marks which tests used each.

## 3. Language, reasoning, coding and agent benchmarks

The following values are published model-author scores, expressed as percentages unless noted. They are representative tests, not an aggregate score. **They are not a perfectly homogeneous ranking**: revisions, prompts, token budgets, tools, reasoning variants and evaluation protocols can differ.

| Benchmark | Qwen3.5-4B | Qwen3-30B-A3B Thinking-2507 | Qwen3.5-35B-A3B | LFM3-1.7B | TwIL-8B |
|---|---:|---:|---:|---:|---:|
| MMLU-Pro (knowledge) | 79.1 | 80.9 | **85.3** | N/A | 76.5† |
| GPQA Diamond (science) | 76.2 | 73.4 (GPQA in card) | **84.2** | 63.37 | 70.2 |
| IFEval (instructions) | 89.8 | 88.9 | 91.9 | **96.66** | 91.8 |
| IFBench (hard instructions) | 59.2 | N/A in comparable table | 70.2 | 73.03 | **74.4†** |
| HMMT Feb 2025 (math) | 74.0 | 71.4 (HMMT25) | 89.0 | N/A | 85.0 |
| LiveCodeBench | 55.8 (v6) | 66.0 (v6) | 74.6 (v6) | 73.46 (v6) | **81.6†** |
| SWE-bench Verified (coding agent) | N/A here | N/A here | 69.2 | 43.40 | N/A |
| BFCL (tool use) | TIR-Bench: 38.9/29.9* | BFCL-v3: 72.4 | BFCL-v4: 67.3 | BFCL-v4: 71.39 | N/A |
| RULER 128K / long context | 84.63 | Check revision protocol | N/A in this table | 65.56 | N/A |

† TwIL: measured on the **verbose** variant, not balanced, according to the model card.  
* Qwen3.5-4B: TIR-Bench is reported with two CI settings; it is not the same benchmark as BFCL.  
N/A means no comparable published figure was found in the model cards consulted; it does not mean zero or inability.

### Interpretation

- **Qwen3.5-35B-A3B** is strongest in this group on the listed knowledge/science figures (MMLU-Pro 85.3; GPQA Diamond 84.2) and remains competitive in coding, agents and math.
- **Qwen3.5-4B** is capable for its size: 79.1 MMLU-Pro, 76.2 GPQA Diamond and 55.8 LiveCodeBench v6.
- **Qwen3-30B-A3B Thinking-2507** improves over the original version on reasoning tasks, with 85.0 AIME25, 71.4 HMMT25 and 66.0 LiveCodeBench v6. Do not mix these with non-thinking base results.
- **LFM3-1.7B** is designed for agents, tools and specialized tasks. Its published results are notable on IFEval (96.66), IFBench (73.03), BFCL V4 (71.39) and LiveCodeBench v6 (73.46), while GPQA Diamond (63.37) shows it is not a replacement for a large knowledge model.
- **TwIL-8B** stands out on MATH-500 (98.2), AIME 2025 (88.3) and LiveCodeBench (81.6†) in its own model-card comparison. The card notes that LiveCodeBench, IFBench and several coding tests were measured on verbose, not balanced. It also trails larger models on knowledge (GPQA Diamond 70.2; MMLU-Pro 76.5†).

### Additional highlighted benchmarks

| Model | Test | Published result | Interpretation |
|---|---|---:|---|
| Qwen3-30B-A3B Thinking-2507 | AIME25 | 85.0 | Competitive mathematical reasoning |
| Qwen3-30B-A3B Thinking-2507 | BFCL-v3 | 72.4 | Tool/function calling |
| Qwen3.5-35B-A3B | SWE-bench Verified | 69.2 | Repository issue resolution |
| Qwen3.5-35B-A3B | TAU2-Bench | 81.2 | Agent execution in simulated domains |
| Qwen3.5-35B-A3B | BrowseComp | 61.0 | Tool-assisted search and research |
| LFM3-1.7B | LiveClaw | 45.60 | Agent evaluation published by Liquid AI |
| LFM3-1.7B | Claw-Eval General (EN), average | 68.64 | General tasks in agent harnesses |
| LFM3-1.7B | MCP-Atlas | 32.57 | MCP tool selection/use |
| TwIL-8B balanced | MATH-500 | 98.2 | Mathematical specialization |
| TwIL-8B balanced | AIME 2025 | 88.3 | Contest mathematics |

Do not combine these results into a single global score: the evaluation sets and protocols differ.

## 4. Vision, video and audio: actual checkpoint capabilities

| Model / checkpoint | Text | Image | Video | Audio |
|---|---|---|---|---|
| Qwen3.5-4B | Yes | Yes, native | Yes, frame/sequence understanding | No native audio declared for this checkpoint |
| Qwen3-30B-A3B | Yes | No | No | No |
| Qwen3.5-35B-A3B | Yes | Yes, native | Yes, frame/sequence understanding | No native audio declared for this checkpoint |
| LFM3-1.7B **Text** | Yes | No | No | No |
| TwIL-8B | Yes | No | No | No |

### 4.1 Qwen3.5-4B and Qwen3.5-35B-A3B

The Qwen3.5 family integrates vision and language. Documented uses include:

- Understanding photographs, screenshots, charts and diagrams.
- OCR, document understanding and visual information extraction.
- Visual and spatial reasoning.
- Video understanding from frame sequences, evaluated on benchmarks such as VideoMME, VideoMMMU, MLVU and MVBench.
- Visual agents and interface-interaction tasks, subject to compatible tools and runtime.

Representative published results:

| Vision / video benchmark | Qwen3.5-4B | Qwen3.5-35B-A3B |
|---|---:|---:|
| MMMU (visual reasoning) | N/A in the summarized 4B table consulted | 81.4 |
| MMMU-Pro | N/A in the summarized 4B table consulted | 75.1 |
| MathVista (mini) | N/A in the summarized 4B table consulted | 86.2 |
| RealWorldQA | N/A in the summarized 4B table consulted | 84.1 |
| MMBench EN-DEV | N/A in the summarized 4B table consulted | 91.5 |
| OCRBench | 85.0 | 91.0 |
| VideoMME with subtitles | 83.5 | 86.6 |
| VideoMME without subtitles | 76.9 | 82.5 |
| MLVU | 82.8 | 85.6 |
| MVBench | 71.2 | 74.8 |
| LVBench | 66.4 | 71.4 |

The Qwen3.5-4B card also reports its own video and OCR results. Where a 4B visual result is not listed in this table, do not infer zero or copy a result from another model size.

**Interpretation limit:** video understanding is not video generation. Video input is processed through frames/temporal representations supported by the model and runtime. Actual performance depends on sampling, resolution, frame count, context and preprocessing.

### 4.2 LFM3: separate the family from the checkpoint

Liquid AI presents LFM3 as a multimodal family with separate text, vision, audio, omni and decision variants. The installed/tested model here is **LFM3-1.7B Text**. Therefore:

- LFM3-1.7B Text: text and tools; do not attribute image, video or audio input to it.
- Vision/Audio/Omni variants are distinct checkpoints requiring their own selection, download, runtime and validation.
- The text checkpoint is designed for local agents and specialization; Liquid AI states 256K context and about 1 GB at 4-bit.
- The family name does not automatically enable all modalities in one binary or checkpoint.

### 4.3 Qwen3-30B-A3B and TwIL-8B

Both checkpoints considered here are text models. They can work with textual descriptions of images or transcripts, but that does not make them native vision or audio models. REDIL should connect a VLM, OCR, ASR or TTS service when a task requires those modalities.

## 5. User's local measurements on MSI Thin 15

**Reference hardware:** MSI Thin 15 B12UC, Intel Core i7-12650H, NVIDIA RTX 3050 Laptop 4 GB VRAM, 14 GB RAM, Ubuntu. These measurements were supplied by the user from their experiments and are recorded as local evidence; they are not vendor results.

| Model | Engine / version | Measured generation | Notes |
|---|---|---:|---|
| Qwen3.5-4B | TensorFold | 53–55 tok/s | Local measurement |
| Qwen3.5-4B | TensorFold PR #1879 | 54–56 tok/s | PR related to CUDA memory reservation; local measurement |
| Qwen3.5-4B | llama.cpp CUDA CLI | 42.4 tok/s | CLI |
| Qwen3.5-4B | llama.cpp CUDA API | 47.65 tok/s | API |
| Qwen3.5-4B | RustingStrata | Not exposed by API | No comparable figure available |
| Qwen3-30B-A3B | llama.cpp CUDA | 1.51–2.00 tok/s | Long batch |
| Qwen3-30B-A3B | RustingStrata | 7.74 tok/s | 64-token generation |
| Qwen3.5-35B-A3B | Tandem.cpp | **35.6 tok/s** | CPU-MoE run; experimental configuration documented separately |
| LFM3-1.7B | Pithos 0.5.0 | 87.22 tok/s | Local run |
| LFM3-1.7B | Pithos 0.5.1 | **104.84 tok/s** | Local run |
| TwIL-8B | llama.cpp CUDA | 3.89–5.11 tok/s | GGUF Q4_K_M balanced; observed range |

### 5.1 Performance interpretation

- LFM3-1.7B on Pithos 0.5.1 has the highest recorded generation speed: 104.84 tok/s.
- Qwen3.5-4B runs at approximately 42–56 tok/s depending on engine/API.
- Tandem.cpp reaches 35.6 tok/s with Qwen3.5-35B-A3B, a notable local result for a 35B-total-parameter MoE on this machine.
- RustingStrata records 7.74 tok/s with Qwen3-30B-A3B in a 64-token generation, versus 1.51–2.00 tok/s in the llama.cpp long-batch run; this is not a controlled comparison.
- TwIL-8B is slower in the recorded run, but its math/code specialization may justify a dedicated service.

**Warning:** do not directly compare tok/s from runs with different contexts, quantizations, prompts, output lengths, reasoning modes or configurations. A normalized REDIL benchmark must fix model/hash, quantization, runtime/commit, context, prompt, output tokens, temperature, batch, offload, thinking mode, cache and repetitions. Record TTFT, prefill tok/s, decode tok/s, peak RAM/VRAM, swap, energy if measured and task quality.

## 6. Artificial Analysis Intelligence Index: usage policy

This report does not assign an Artificial Analysis Intelligence Index number to each of the five models. A composite index should only be recorded when the exact model and configuration appear in the official results table and the methodology version can be identified.

Artificial Analysis announced Intelligence Index v5 on 27 October 2026. V5 introduces new and private tests, changes weights and datasets, and is not interchangeable with earlier versions. Therefore:

- Do not reuse old AA scores as if they were v5.
- Do not infer the index from MMLU, GPQA, LiveCodeBench or a qualitative rating.
- Record **AA Intelligence Index (version)** separately from individual benchmarks.
- If a model is not in the official comparable table, record **N/A — not listed/not verified**, not an estimate.

## 7. Technical assessment for REDIL

The following is a qualitative assessment for service assignment. It is not an official score and does not replace benchmarks.

| Model | General capability | Observed local speed | Checkpoint multimodality | Specialty | Proposed role |
|---|---|---|---|---|---|
| Qwen3.5-4B | High for its size | 42.4–56 tok/s | Text + image + video | Multimodal generalist, documents, OCR, lightweight agents | Low-latency multimodal general service |
| Qwen3-30B-A3B | High in text/reasoning | 1.51–7.74 tok/s depending on test/engine | Text only | Reasoning, math, code | MoE test bench / alternative text specialist |
| Qwen3.5-35B-A3B | Very high | 35.6 tok/s with Tandem.cpp | Text + image + video | Reasoning, vision, video, agents | Main specialist for complex tasks |
| LFM3-1.7B Text | Specialized; less general knowledge than large models | 87.22–104.84 tok/s | Text only in this checkpoint | Agents, tools, classification and automation | Lightweight agent and frequent tasks |
| TwIL-8B | High in specific domains | 3.89–5.11 tok/s | Text only | Math, code and instructions | Math/programming specialist |

### Recommended architecture

1. **Qwen3.5-35B-A3B — advanced reasoning and multimodality.** Use when task complexity justifies memory/latency cost. Its Tandem.cpp speed is a notable local result, but keep the experimental configuration documented.
2. **Qwen3.5-4B — frequent multimodal generalist.** Candidate for normal requests involving text, images, documents or video clips.
3. **LFM3-1.7B Text — high-frequency agent.** Suitable for short tasks, classification, structured extraction and tool calls; do not route images or audio to it as if the checkpoint were multimodal.
4. **TwIL-8B — math and code.** Route programming and math tasks when internal tests confirm a real advantage; account for its non-commercial license.
5. **Qwen3-30B-A3B — experimental reference.** Retain it to compare MoE, runtimes and offload strategies; it does not appear to be the best general candidate against Qwen3.5-35B-A3B in the consulted results.

## 8. Local hardware and REDIL node implications

The reference machine has 4 GB VRAM and 14 GB RAM. Active MoE parameters are not the same as the total weights that must be stored. Qwen3-30B-A3B and Qwen3.5-35B-A3B require sizing for weights, buffers, KV cache, context and runtime memory; activating about 3B parameters per token does not mean only 3B parameters need to be hosted.

Deployment recommendations:

- Do not keep all five models resident simultaneously on the MSI.
- Load specialists on demand and release memory between services.
- Set explicit context and concurrency limits; measure swap and peak memory.
- Separate processes and ports so tests do not interfere with LEONES/ODS or other services.
- Do not assume model compatibility with one runtime carries over to another runtime or version.
- For distributed REDIL, assign services to nodes by specialty; do not describe RAM across computers as unified memory unless a backend explicitly implements weight partitioning.

## 9. Limitations, licensing and reproducibility

- **TwIL-8B:** its model card states webAI Non-Commercial License 1.0. Do not treat it as commercially usable without reviewing the terms.
- **Qwen3-30B-A3B and Qwen3.5:** verify the license and exact artifact for each revision before redistribution.
- **LFM3:** the family has separate text, vision, audio, omni and decision checkpoints. Verify license and compatibility for the chosen artifact.
- Vendor benchmark scores are author-reported results, not LEONES measurements.
- The user's local figures are not yet a common benchmark across all five models.
- Always record engine, version, model, quantization and configuration alongside each result.

### Minimum protocol for the next REDIL test round

1. Record model SHA, exact artifact name, quantization and tokenizer.
2. Pin runtime, commit/build, effective backend (CUDA/CPU), flags and context.
3. Run identical prompts and control thinking/non-thinking, temperature, batch and maximum output.
4. Perform at least three repetitions and record mean, median and spread.
5. Measure TTFT, prefill tok/s, decode tok/s, peak RAM/VRAM, swap and stability.
6. Evaluate task quality by specialty: MMLU/GPQA for knowledge, MATH/AIME for math, LiveCodeBench/SWE-bench for code, IFEval/IFBench for instructions, MMMU/OCRBench/VideoMME for vision/video, and BFCL/τ-bench for tools.
7. Preserve logs, commands, manifest, environment and JSON/JSONL results.
8. Mark as **MEASURED-LEONES** only results reproducible on the identified hardware. Keep upstream results as **UPSTREAM-REPORTED**.

## 10. Primary sources and traceability

Consulted on 7 November 2026 unless the page states another date:

1. [Qwen3.5-4B — official Hugging Face model card](https://huggingface.co/Qwen/Qwen3.5-4B) — language, vision, video, tool and context benchmarks.
2. [Qwen3-30B-A3B-Thinking-2507 — official model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Thinking-2507) — MoE architecture and reasoning, coding, agent and multilingual benchmarks.
3. [Qwen3.5-35B-A3B — official model card](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) — architecture, active parameters, context and language, vision and video benchmarks.
4. [Liquid AI — Introducing LFM3](https://www.liquid.ai/blog/lfm3) — family, modality variants and LFM3-1.7B Text benchmarks. Published 27 October 2026.
5. [LFM3-1.7B-Base — Hugging Face model card](https://huggingface.co/LiquidAI/LFM3-1.7B-Base) — base model architecture, size and context.
6. [TwIL-8B — official webAI model card](https://huggingface.co/webAI-Official/TwIL-8B) — balanced/verbose variants, benchmarks, protocol, context, language and license.
7. [Artificial Analysis — Intelligence Index v5](https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v5/) — methodology and changes announced on 27 October 2026.
8. [Artificial Analysis — benchmarking methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking) — composite index definition and evaluations.

### Provenance labels

- **UPSTREAM-REPORTED:** scores published in official model cards/blogs.
- **LOCAL-MEASURED-USER:** inference speeds supplied by the user for the MSI Thin 15; preserve original experiment logs for reproducibility.
- **QUALITATIVE-ASSESSMENT:** report's proposed REDIL assessment and assignment; not an external score.
- **N/A:** unavailable or not comparable in sources consulted.

---
*REDIL research document within LEONES. Update when model revisions, upstream benchmarks or local measurements change. Do not overwrite historical results: add date, artifact and configuration to preserve traceability.*
