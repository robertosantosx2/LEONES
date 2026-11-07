# LEONES reference subprojects

This directory tracks external projects used as references or active development dependencies. A row in the reference table does not imply that the repository is installed as a Git submodule.

## Reference revisions

| Subproject | Upstream | Pinned revision | Role |
|---|---|---|---|
| ODS | https://github.com/Osmantic/ODS | `5a4450765976e2ad2792b9ac8927f4873dac60f6` | Local AI server / inference stack |
| Magnitude | https://github.com/magnitudedev/magnitude | `c3ace06488737be5383087d965d0e4e629f4f00b` | Hardware profiling, model selection and agent runtime |
| Buddy | https://github.com/juanje/buddy | `71ec96885dabdf8c19054450f0320fd1714d4174` | Reference agent harness |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness | `141eb6fef83422698aef7a981029e843e8161534` | Reference agent harness |

## Active development projects

| Project | Upstream | Development repository / branch | Role and status |
|---|---|---|---|
| Picchio | https://github.com/benmaster82/picchio | https://github.com/robertosantosx2/picchio — `feature/cuda-pinned-host-slabs` | Experimental MoE CPU/CUDA backend; bounded CUDA pinned-host slabs implemented in the fork, awaiting Ubuntu/RTX 3050 validation. [Full report](Picchio/README.md) · [Code PR #1](https://github.com/robertosantosx2/picchio/pull/1) |

## Policy

- Keep upstream source intact; LEONES-specific integration lives in its own fork or outside the upstream repository.
- Pin revisions for reproducibility rather than tracking moving branches.
- Upgrade reference pins only after compatibility checks and CI validation.
- Experimental projects must distinguish measured results from hypotheses and estimates.
- Do not describe an optimization as validated or faster until it has passed compilation, functional tests and controlled benchmarks.

## Checkout reference submodules

For repositories actually configured as Git submodules:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

Picchio is currently tracked as an active development fork, not as a Git submodule.
