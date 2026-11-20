# HDAE recursive subproject audit — LEONES

**Audit date:** 2026-11-20  
**Scope:** repository tree, root agent instructions, subproject documentation map, README/index/roadmap/checkpoint inventory, and focused consistency checks.  
**Status:** initial documentary audit; not a full source-code, dependency, security, runtime or hardware audit.  
**Authority:** root `AGENTS.md`, [HDAE directive](HDAE-DIRECTIVE.md), and each subproject's existing canonical master INDEX where one is explicitly designated. This audit does not create or replace a priority source.

## 1. Executive findings

1. The merged root `AGENTS.md` is the only `AGENTS.md` found in the complete GitHub repository tree. No nested subproject-specific agent instructions were found.
2. The user-designated LEONES master INDEX is `research/moe/tandem.cpp/NEPENTHES-INDEX.md` on `main`. It remains the sole source of priority and acceptance; its unusual path does not authorize creating a competing root index. The JGB index is a domain classification index, not a software priority index.
3. Several other workstreams have roadmaps or integration documents, but no dedicated, clearly designated master INDEX was found in the initial filename inventory. This includes ODS/Magnitude integration, TensorFold Web, agentic benchmarks, and multiple documented subprojects.
4. A concrete stale-state conflict was found: `docs/subprojects/NEPENTHES/TRACE-ENVELOPE.md` described LEONES PR #210 as open, while PR #210 is merged at `fcaf17005f7771c2521fc07387409a79c47f1b7b` and the NEPENTHES master INDEX already records it as merged. This audit phase corrects that stale status paragraph only; the INDEX remains authoritative.
5. Several documents are intentionally designs, proposals or evidence summaries. They must not be promoted to implementation/acceptance merely because their roadmap says a phase is planned or a README exists.

## 2. Repository-wide instruction inventory

| Item | Finding | Action |
|---|---|---|
| Root `AGENTS.md` | Present; links the pinned HDAE snapshot and sets remote-first workflow | Adopted by merge PR #237 |
| Nested `AGENTS.md` | None found in the complete repository tree | Do not add blanket copies; create scoped instructions only where a subproject has a distinct boundary |
| LEONES master INDEX | `research/moe/tandem.cpp/NEPENTHES-INDEX.md`, explicitly designated by the user | Sole source of priority and acceptance; do not create a parallel root index or promote roadmaps to master status |
| NEPENTHES | Dedicated master INDEX present | Preserve as sole priority/status/acceptance source |
| JGB | Dedicated domain index present | Keep scoped to openness classification, not engineering governance |

## 3. Subproject and workstream inventory

| Workstream | Existing canonical navigation / planning | Initial gap or risk |
|---|---|---|
| LFM3 | `docs/subprojects/LFM3/README.md` | Evidence/report collection; no dedicated master INDEX or durable project checkpoint identified |
| LLMFit | `docs/subprojects/LLMFit/README.md`; pinned upstream submodule | Integration boundary documented; no dedicated subproject master INDEX/checkpoint identified |
| REDIL / LLuvIA | `docs/subprojects/LLuvIA-IA-distribuida/README.md`, plus REDIL architecture docs | Explicitly proposal/research and not physically deployed; no dedicated master INDEX/checkpoint identified |
| ODS | `docs/subprojects/ODS/README.md`, ODS-Magnitude integration/audit, `docs/integrations/ROADMAP.md` | Roadmap and status documents overlap; no dedicated authoritative ODS INDEX/checkpoint identified |
| Magnitude | `docs/subprojects/Magnitude/README.md`, ODS-Magnitude integration/audit, `docs/integrations/ROADMAP.md` | Same shared integration roadmap; no dedicated authoritative Magnitude INDEX/checkpoint identified |
| Open-dCoder | README, executive summary and V1/V2/V3 experiment records | Evidence-rich, but no dedicated master INDEX/checkpoint; README records local modifications and missing commit/dependency manifest |
| TensorFold | `docs/subprojects/TensorFold/README.md`, CUDA audit, PR1879 record | Main TensorFold runtime audit and TensorFold Web work overlap; no single subproject master INDEX/checkpoint identified |
| TensorFold Web | `TENSORFOLD-WEB-ROADMAP.md` and nested README | Roadmap identifies target-machine browser/Engine/Pake checks pending; no dedicated master INDEX/checkpoint identified |
| Buddy | README, harness contract, ODS/Magnitude integration docs | Integration boundaries exist; no dedicated master INDEX/checkpoint identified |
| LEONES Lab Agent | `projects/leones-lab-agent/README.md` | Versioned project README; no dedicated master INDEX/checkpoint identified |
| Agentic Benchmark | `benchmarks/agentic/ROADMAP.md`, README and grader/contracts | Roadmap exists; no clearly designated master INDEX/checkpoint identified |
| Research E2E | `research/e2e/README.md` | Research workstream; no dedicated master INDEX/checkpoint identified |
| Tandem.cpp / NEPENTHES | `research/moe/tandem.cpp/NEPENTHES-INDEX.md` | Has canonical master INDEX; other docs must be synchronized to it |

## 4. Consistency findings

### 4.1 Corrected during this audit

- `docs/subprojects/NEPENTHES/TRACE-ENVELOPE.md` stale PR #210 status corrected to merged commit `fcaf17005f7771c2521fc07387409a79c47f1b7b`.
- The document now explicitly defers current NEPENTHES state and acceptance to `NEPENTHES-INDEX.md`.
- Scope remains host-only; it does not claim TensorFold CUDA/NVTX producer acceptance or physical C07/C08 closure.

### 4.2 Needs a bounded follow-up

- `docs/subprojects/README.md` links `leones-lab-agent/README.md` as if it were a sibling under `docs/subprojects`, while the discovered project README is `projects/leones-lab-agent/README.md`. Verify and repair this relative link in a small documentation PR.
- ODS/Magnitude have a shared roadmap and several overlapping audit/integration documents. Designate a master INDEX (or explicitly name an existing canonical document) only after reviewing the project owner's intended priority authority; do not infer that the roadmap is the master.
- TensorFold Web has its own roadmap, while TensorFold's README is the general integration hub. Define the hierarchy between the two and record a single checkpoint without merging unrelated TensorFold runtime priorities.
- Open-dCoder's README records temporary local source modifications and missing upstream SHA/dependency manifest. This is a reproducibility/record-keeping gate, not a reason to rewrite historical results.
- LFM3 and other benchmark-only dossiers should remain evidence records unless their scope becomes an actively maintained engineering subproject.

## 5. Recommended remediation sequence (proposal, not a new priority source)

1. **Resolve LEONES root INDEX authority.** Locate the owner's intended master INDEX or explicitly confirm which existing document serves as the root priority/acceptance authority. Do not create a competing roadmap.
2. **NEPENTHES synchronization.** Keep `NEPENTHES-INDEX.md` authoritative; audit all linked technical docs for stale PR/CI/physical-gate claims. Do not alter its execution order without the INDEX owner.
3. **ODS + Magnitude.** Resolve whether the shared `docs/integrations/ROADMAP.md` is the single shared integration plan; create scoped subproject INDEX/checkpoint only if separate ownership/priorities exist.
4. **TensorFold / TensorFold Web.** Establish parent/child document authority and update stale state against the active upstream PR and LEONES work.
5. **Active code projects.** Add or designate a master INDEX and durable checkpoint for LEONES Lab Agent, Agentic Benchmark, and Buddy only where active multi-step engineering work warrants it.
6. **Evidence-only dossiers.** Preserve LFM3/Open-dCoder historical evidence; add reproducibility metadata through focused, evidence-preserving PRs.

## 6. Acceptance and limitations

- [x] Complete GitHub tree inventory for `AGENTS.md`, README, INDEX-like, roadmap and checkpoint-like filenames.
- [x] Read root `AGENTS.md` and the subproject documentation map.
- [x] Inspect the canonical NEPENTHES INDEX and selected project roadmaps/contracts.
- [x] Verify LEONES PR #210 is merged and correct one stale dependent status statement.
- [x] Resolve master INDEX authority: use `research/moe/tandem.cpp/NEPENTHES-INDEX.md` as the user-designated LEONES source of priority and acceptance; do not create a competing root index.
- [ ] Audit every subproject's complete source, dependencies, tests, workflows, issues/PRs and current checkpoint.
- [ ] Produce bounded remediation PRs and verify each against its own master INDEX.
- [ ] Record per-project HDAE adoption and exceptions.

This report is a documentary inventory, not a claim that every subproject has been fully audited or accepted. No MSI action was required for this remote inspection.
