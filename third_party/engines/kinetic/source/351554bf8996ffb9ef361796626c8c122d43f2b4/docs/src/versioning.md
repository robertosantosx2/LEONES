# Versioning

Kinetic's version is the one in the workspace `Cargo.toml`; the command
line, the libraries and the Python package all carry it, and `kinetic
--version` prints it.

- **0.1.x** releases fix bugs. They add support where it was missing (a
  pre-tokenizer, a weight type on a device) but do not change how existing
  commands, flags or API fields behave.
- **0.2** brings new features, such as the Vulkan backend, partial offload of
  dense models and `--parallel`. While Kinetic is below 1.0, a minor version
  may also change behavior; the [changelog](changelog.md) lists every such
  change.
- **File formats are versioned on their own.** A `.ktc` file starts with the
  magic `KTC1` and a format version, which changes only when the layout does,
  independent of Kinetic's version. See
  [FORMAT.md](https://github.com/Veloresearch/kinetic/blob/main/crates/kinetic-ktc/FORMAT.md).
- **Releases are git tags** named `vX.Y.Z`, such as `v0.1.0`. Each tag builds
  the release archives, the Python wheels and their `SHA256SUMS`.
