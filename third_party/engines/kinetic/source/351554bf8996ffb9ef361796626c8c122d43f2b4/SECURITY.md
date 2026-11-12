# Security

## Reporting a vulnerability

Email **contact@veloresearch.com**. Please do not open a public issue,
discussion or pull request for a vulnerability.

Include what you can of:

- the Kinetic version (`kinetic --version`) and your operating system;
- what an attacker can do, and what they need to do it;
- steps or a file that reproduce it; model files can be large, so a script
  that builds the file is welcome instead.

We will acknowledge your report, keep you informed while we work on a fix
and credit you in the release notes unless you prefer otherwise. Please give
us reasonable time to release a fix before you disclose the issue.

## Supported versions

Security fixes go into the latest release. Kinetic is young; there are no
long-term support branches yet.

## Scope

In scope, among others:

- memory safety bugs, crashes or hangs caused by a model file (`.gguf`,
  `.ktc`), an image or a request; model files are untrusted input;
- `kinetic verify` passing a `.ktc` file whose contents do not match its
  manifest, or accepting a signature it should reject;
- the server answering requests it should refuse, such as cross-origin
  requests from web pages;
- any network connection Kinetic makes on its own. Kinetic never connects
  to the network, except when you run `kinetic pull`, and anything else is a
  bug.

Out of scope:

- exposing `kinetic serve` beyond `127.0.0.1` with `--host`. The server has no
  authentication; put it behind a proxy that has.
- what a model says. Output quality and safety are properties of the model,
  not of the engine.
