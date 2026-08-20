# LEONES reference subprojects

These repositories are tracked as pinned Git submodules so LEONES can inspect and integrate them without copying their source into the main repository.

| Subproject | Upstream | Pinned revision | Role |
|---|---|---|---|
| ODS | https://github.com/Osmantic/ODS | `5a4450765976e2ad2792b9ac8927f4873dac60f6` | Local AI server / inference stack |
| Magnitude | https://github.com/magnitudedev/magnitude | `c3ace06488737be5383087d965d0e4e629f4f00b` | Hardware profiling, model selection and agent runtime |
| Buddy | https://github.com/juanje/buddy | `71ec96885dabdf8c19054450f0320fd1714d4174` | Reference agent harness |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness | `141eb6fef83422698aef7a981029e843e8161534` | Reference agent harness |

## Policy

- Keep upstream source intact; LEONES-specific integration lives outside the submodule.
- Pin revisions for reproducibility rather than tracking moving branches.
- Upgrade pins only after compatibility checks and CI validation.
- ODS, Magnitude, Buddy and DeepSeek Harness are reference implementations; none becomes a mandatory runtime dependency of LEONES.

## Checkout

```bash
git submodule sync --recursive
git submodule update --init --recursive
```
