<!-- Thanks for contributing. Please read CONTRIBUTING.md first. -->

## What and why

<!-- What this changes and why. Link the issue it closes: "Closes #123". -->

## How it was tested

<!-- Commands you ran, models you used, hardware. -->

- [ ] `cargo fmt --all -- --check`
- [ ] `cargo clippy --release --workspace --all-targets --all-features -- -D warnings`
- [ ] `cargo test --release` for the crates I touched
- [ ] Every commit is signed off (`git commit -s`)

## Exactness and speed

<!--
If this touches decoding, caching, kernels or a model: does greedy output
stay token for token what plain decoding gives? Which identity test covers it?
If it claims to be faster: model, hardware, command, before and after, best of several runs.
Delete this section if it does not apply.
-->
