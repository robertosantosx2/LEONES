/*
 * Asks a local model one question and streams the answer.
 *
 *   cl /I include examples\chat.c <target>\release\kinetic_capi.dll.lib
 *   gcc -I include examples/chat.c -L <target>/release -lkinetic_capi
 *
 *   chat model.gguf "Name three rivers."
 */
#include <stdio.h>

#include "kinetic.h"

static bool print_text(const char *text, size_t len, void *user_data) {
    (void)user_data;
    fwrite(text, 1, len, stdout);
    fflush(stdout);
    return true;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s MODEL PROMPT\n", argv[0]);
        return 2;
    }
    kinetic_model *model = kinetic_model_load(argv[1]);
    if (!model) {
        fprintf(stderr, "kinetic: %s\n", kinetic_last_error());
        return 1;
    }
    kinetic_session *session = kinetic_session_new(model, NULL);
    if (!session) {
        fprintf(stderr, "kinetic: %s\n", kinetic_last_error());
        kinetic_model_free(model);
        return 1;
    }
    kinetic_params params = kinetic_params_default();
    params.max_tokens = 128;
    int64_t tokens = kinetic_session_generate(session, argv[2], &params, print_text, NULL);
    if (tokens < 0) {
        fprintf(stderr, "kinetic: %s\n", kinetic_last_error());
    } else {
        fprintf(stderr, "\n[%lld tokens, kinetic %s]\n", (long long)tokens, kinetic_version());
    }
    kinetic_session_free(session);
    kinetic_model_free(model);
    return tokens < 0;
}
