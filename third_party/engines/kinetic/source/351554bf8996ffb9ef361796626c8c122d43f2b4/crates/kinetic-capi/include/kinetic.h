/*
 * Kinetic C API: load a local model, chat with it and embed text.
 *
 * Copyright 2026 Velocity. Licensed under the Apache License, Version 2.0.
 *
 * Strings are UTF-8 and NUL-terminated. Functions that can fail return
 * NULL or a negative number; kinetic_last_error() then says why. A model
 * may be shared between threads, whose requests take turns on it; a
 * session belongs to one thread at a time.
 */
#ifndef KINETIC_H
#define KINETIC_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* A loaded model. */
typedef struct kinetic_model kinetic_model;

/* A conversation with a text model: the system prompt and every turn so far. */
typedef struct kinetic_session kinetic_session;

/* How to generate. Start from kinetic_params_default(). */
typedef struct kinetic_params {
    /* Most tokens to generate; 0 or less runs until the answer ends. */
    int32_t max_tokens;
    /* 0 always takes the likeliest token; below 0 uses the model's own. */
    float temperature;
    /* Makes sampled output repeatable when has_seed is true. */
    uint64_t seed;
    bool has_seed;
} kinetic_params;

/*
 * Receives each new piece of generated text, len bytes long and also
 * NUL-terminated. Return false to stop generating.
 */
typedef bool (*kinetic_text_fn)(const char *text, size_t len, void *user_data);

/* The library version, such as "0.1.0". */
const char *kinetic_version(void);

/*
 * Why the last failing call on this thread failed, or NULL. Valid until
 * the next call into the library on this thread.
 */
const char *kinetic_last_error(void);

/* Loads a .gguf or .ktc file. NULL on failure. */
kinetic_model *kinetic_model_load(const char *path);

/* Frees the model once every session made from it is freed too. NULL is ignored. */
void kinetic_model_free(kinetic_model *model);

/* The defaults: no token limit, the model's temperature, no seed. */
kinetic_params kinetic_params_default(void);

/* Starts a conversation; system may be NULL. NULL on failure. */
kinetic_session *kinetic_session_new(const kinetic_model *model, const char *system);

/* Frees the session. NULL is ignored. */
void kinetic_session_free(kinetic_session *session);

/*
 * Adds the user's message, streams the answer to on_text and adds the
 * answer to the conversation. params may be NULL for the defaults and
 * on_text NULL to only count tokens. Returns the number of tokens
 * generated, or -1 on failure.
 */
int64_t kinetic_session_generate(kinetic_session *session, const char *message,
                                 const kinetic_params *params, kinetic_text_fn on_text,
                                 void *user_data);

/* Length of an embedding model's vectors; 0 for a text model. */
size_t kinetic_embedding_size(const kinetic_model *model);

/*
 * Writes the vector for text, kinetic_embedding_size(model) floats, to out.
 * Returns 0, or -1 on failure.
 */
int kinetic_embed(const kinetic_model *model, const char *text, float *out);

#ifdef __cplusplus
}
#endif

#endif /* KINETIC_H */
