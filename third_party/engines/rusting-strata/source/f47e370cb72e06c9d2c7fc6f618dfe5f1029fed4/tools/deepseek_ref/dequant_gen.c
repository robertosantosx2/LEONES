// Writes random quant blocks and ggml's dequantized floats: <name>.blk (raw), <name>.f32.
// Build: gcc dequant_gen.c -I$L/ggml/include -L$L/build-cuda/bin -lggml-base -Wl,-rpath,$L/build-cuda/bin -lm -o dequant_gen
#include "ggml.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
int main(int argc, char **argv) {
    struct { const char *n; enum ggml_type t; } T[] = {
        {"iq2_xxs", GGML_TYPE_IQ2_XXS}, {"iq2_xs", GGML_TYPE_IQ2_XS}, {"iq1_m", GGML_TYPE_IQ1_M},
        {"iq4_nl", GGML_TYPE_IQ4_NL}, {"q5_k", GGML_TYPE_Q5_K}, {"q8_0", GGML_TYPE_Q8_0}, {"bf16", GGML_TYPE_BF16}};
    srand(12345);
    for (int i = 0; i < 7; i++) {
        const struct ggml_type_traits *tr = ggml_get_type_traits(T[i].t);
        size_t bs = tr->type_size; int ne = tr->blck_size, kept = 0;
        char p[256]; snprintf(p, sizeof p, "%s/%s.blk", argv[1], T[i].n); FILE *fb = fopen(p, "wb");
        snprintf(p, sizeof p, "%s/%s.f32", argv[1], T[i].n); FILE *ff = fopen(p, "wb");
        unsigned char *b = malloc(bs); float *o = malloc(ne * 4);
        while (kept < 64) {
            for (size_t k = 0; k < bs; k++) b[k] = rand() >> 7;
            tr->to_float(b, o, ne);
            int ok = 1; for (int k = 0; k < ne; k++) if (!isfinite(o[k]) || fabsf(o[k]) > 1e4f) ok = 0;
            if (!ok) continue;
            fwrite(b, 1, bs, fb); fwrite(o, 4, ne, ff); kept++;
        }
        fclose(fb); fclose(ff); printf("%s bs=%zu ne=%d\n", T[i].n, bs, ne);
    }
}
