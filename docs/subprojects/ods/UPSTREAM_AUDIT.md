# ODS upstream audit — 2026-08-20

## Scope

Audited the public `sentient-agi/OpenDeepSearch` `main` tree as the upstream for the LEONES ODS subproject. The upstream repository is MIT licensed and currently declares Python >=3.10. The current upstream package metadata contains a single undifferentiated runtime dependency list and a second, slightly divergent `requirements.txt`.

## Baseline findings

### Packaging

- `pyproject.toml` declares the core stack but omits runtime imports used by the source, notably `python-dotenv`, `loguru`, `nest-asyncio`, `langchain-text-splitters`, `requests`, and `torch`.
- `requirements.txt` duplicates the dependency list and is not identical to `pyproject.toml`.
- `crawl4ai` is pinned directly to the `main` branch of a Git repository, which makes reproducible builds harder.
- The current metadata does not separate CPU/base dependencies from optional ranking, evaluation, demo, or GPU dependencies.

### Context building

`src/opendeepsearch/context_building/build_context.py` imports `RecursiveCharacterTextSplitter` from the obsolete `langchain.text_splitter` path. The actual `Chunker` already uses the modern `langchain_text_splitters` package. The import in `build_context.py` is unused and should be removed rather than replaced.

### Ranking API

The actual public classes in `ranking_models` are:

- `BaseSemanticSearcher`
- `InfinitySemanticSearcher`
- `JinaReranker`

There is no `BaseReranker` or `InfinityReranker`. Any test referring to those names is invalid and must be corrected to the real API.

### Ranking contract bug

`BaseSemanticSearcher.get_reranked_documents()` advertises `List[str] | List[List[str]]` but currently returns a single newline-joined `str` for the single-query case. This is a contract mismatch and must be fixed with a regression test before changing the behavior.

### Infinity ranking bug candidate

`InfinitySemanticSearcher._get_embeddings()` supports an `embedding_type` parameter and prefixes queries, but `BaseSemanticSearcher.calculate_scores()` calls `_get_embeddings()` identically for queries and documents. This means the base implementation does not actually request document embeddings separately. The behavior needs an isolated contract test and then a targeted fix.

### Source processor defects

`context_building/process_sources_pro.py` annotates `sources` as `List[dict]` but accesses `sources.data` repeatedly. It also returns `sources.data` in some branches and `sources` in others. This is a strong type/behavior inconsistency and should be fixed before considering ODS integration stable.

The default reranker path initializes `InfinitySemanticSearcher`, which implies an external Infinity service is required for normal processing. LEONES should treat this as an optional external service, not as a mandatory local dependency.

### Jina ranking

`JinaReranker` imports `python-dotenv` and requires `JINA_API_KEY` unless an API key is passed explicitly. This dependency belongs to the ranking/remote-provider layer rather than the minimal ODS core.

### Import strategy

`opendeepsearch.__init__` imports the full agent/tool stack eagerly. This makes a package-level import transitively depend on search, scraping, LiteLLM, environment helpers, and other optional runtime components. LEONES should add an import contract and decide whether optional providers should be lazy-loaded.

## LEONES policy resulting from the audit

1. Do not repair ODS by adding arbitrary packages until their source usage is classified.
2. Do not make CUDA/GPU packages part of the CPU baseline.
3. Keep external ranking providers optional.
4. Test the actual ODS API names, not names inferred from filenames.
5. Separate package/import contracts from network/service integration tests.
6. Make CI perform static/import/unit validation; reserve Debian for hardware-specific validation only.
7. Keep the upstream snapshot identifiable by commit SHA so LEONES can reproduce and audit provenance.

## Current upstream reference

Upstream default branch: `main`

The Git tree audited for this document was commit:

`ec7aa06dc5ead71821a3d92ea56e54a8a9d16ece`

## Next implementation pass

- vendor/snapshot the upstream ODS source under `docs/subprojects/ods/upstream` in the LEONES branch;
- repair the unused LangChain import;
- add missing runtime dependency declarations according to actual usage;
- add contract tests for the ranking API;
- resolve the `get_reranked_documents()` return-type mismatch;
- resolve the `sources.data` inconsistency in `SourceProcessor`;
- isolate Infinity/Jina network tests from the CPU package tests;
- add a dedicated ODS CI job.

## Local Debian finding

The local Debian validation has already established that a CPU-only PyTorch installation works (`torch 2.13.0+cpu`, CUDA unavailable). A CUDA-enabled installation attempted to pull a large NVIDIA dependency stack and hit the user's filesystem quota. This is precisely why the LEONES baseline must keep CPU and GPU environments separate.
