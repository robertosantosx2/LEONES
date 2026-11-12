# Kinetic on the CPU, serving an OpenAI-compatible API on port 8080.
#
#   docker build -f docker/Dockerfile -t kinetic .
#   docker run --rm -p 8080:8080 -v "$PWD/models:/models:ro" kinetic /models/model.gguf

FROM rust:1.96-bookworm AS build
WORKDIR /src
# Only the sources: rust-toolchain.toml would make rustup fetch another toolchain.
COPY Cargo.toml Cargo.lock ./
COPY crates crates
RUN cargo build --release --locked -p kinetic-cli --no-default-features

FROM debian:bookworm-slim
COPY --from=build /src/target/release/kinetic /usr/local/bin/kinetic
COPY LICENSE NOTICE README.md /usr/share/doc/kinetic/
RUN useradd --system --uid 10001 --no-create-home kinetic
USER kinetic
VOLUME /models
EXPOSE 8080
ENTRYPOINT ["kinetic", "serve", "--host", "0.0.0.0", "--port", "8080"]
CMD ["/models/model.gguf"]
