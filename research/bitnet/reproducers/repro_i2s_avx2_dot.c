/*
 * Standalone differential reproducer for the I2_S AVX2 vec-dot accumulator.
 *
 * Loads ggml_vec_dot_i2_i8_s from an existing libggml-cpu shared library.
 * The test intentionally uses valid I2_S codes (0..2) and I8_S activations
 * in the quantizer's [-128, 127] output domain.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      research/bitnet/reproducers/repro_i2s_avx2_dot.c -ldl -o /tmp/repro_i2s_avx2_dot
 *
 * Run:
 *   /tmp/repro_i2s_avx2_dot /path/to/libggml-cpu.so
 *   /tmp/repro_i2s_avx2_dot /path/to/libggml-cpu.so --expect-baseline
 *
 * Default mode expects exact arithmetic. --expect-baseline expects overflow
 * for all-positive and 90%-positive patterns, while alternating blocks and
 * +64 remain exact. Remove --expect-baseline after a fix for regression use.
 */

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    K = 3072,
    WEIGHT_BYTES = K / 4,
};

typedef void (*i2s_dot_fn)(
    int n,
    float * s,
    size_t bs,
    const void * vx,
    size_t bx,
    const void * vy,
    size_t by,
    int nrc
);

typedef enum {
    PATTERN_ALL_POSITIVE_127,
    PATTERN_NINETY_PERCENT_POSITIVE,
    PATTERN_ALTERNATING_BLOCKS,
    PATTERN_ALL_POSITIVE_64,
} activation_pattern;

static const char * pattern_name(activation_pattern pattern) {
    switch (pattern) {
        case PATTERN_ALL_POSITIVE_127: return "all +127";
        case PATTERN_NINETY_PERCENT_POSITIVE: return "90% +127 / 10% -127";
        case PATTERN_ALTERNATING_BLOCKS: return "alternating 128-element blocks";
        case PATTERN_ALL_POSITIVE_64: return "all +64";
    }
    return "unknown";
}

static void fill_activations(int8_t * y, activation_pattern pattern) {
    for (int i = 0; i < K; ++i) {
        switch (pattern) {
            case PATTERN_ALL_POSITIVE_127:
                y[i] = 127;
                break;
            case PATTERN_NINETY_PERCENT_POSITIVE:
                y[i] = (i % 10 == 0) ? -127 : 127;
                break;
            case PATTERN_ALTERNATING_BLOCKS:
                y[i] = ((i / 128) & 1) ? -127 : 127;
                break;
            case PATTERN_ALL_POSITIVE_64:
                y[i] = 64;
                break;
        }
    }
}

/*
 * I2_S block layout: 32 packed bytes encode 128 values. For byte lane b,
 * bit planes 6:7, 4:5, 2:3, 0:1 map to activation positions
 * b, 32+b, 64+b, 96+b respectively.
 */
static int64_t reference_raw_dot(const uint8_t * weights, const int8_t * y) {
    int64_t sum = 0;
    for (int i = 0; i < K; ++i) {
        const int block = i / 128;
        const int in_block = i % 128;
        const int plane = in_block / 32;
        const int lane = in_block % 32;
        const uint8_t packed = weights[block * 32 + lane];
        const int shift = 6 - 2 * plane;
        const int code = (packed >> shift) & 0x03;
        sum += (int64_t) code * y[i];
    }
    return sum;
}

static int run_case(
    i2s_dot_fn dot,
    const uint8_t * weights,
    int8_t * activations,
    activation_pattern pattern,
    int expect_mismatch
) {
    fill_activations(activations, pattern);
    const int64_t expected_raw = reference_raw_dot(weights, activations);
    int64_t activation_sum = 0;
    for (int i = 0; i < K; ++i) activation_sum += activations[i];

    float actual_float = 0.0f;
    dot(K, &actual_float, 1, weights, K, activations, 0, 1);

    const int64_t actual_raw = (int64_t) actual_float;
    const int64_t expected_ternary = expected_raw - activation_sum;
    const int64_t actual_after_caller_correction = actual_raw - activation_sum;
    const int64_t difference = actual_raw - expected_raw;
    const int mismatch = difference != 0;
    const int unexpected = mismatch != expect_mismatch;

    printf(
        "%-34s raw_expected=%lld raw_actual=%lld diff=%lld "
        "act_sum=%lld corrected_expected=%lld corrected_actual=%lld "
        "expect=%s result=%s\n",
        pattern_name(pattern), (long long) expected_raw, (long long) actual_raw,
        (long long) difference, (long long) activation_sum,
        (long long) expected_ternary, (long long) actual_after_caller_correction,
        expect_mismatch ? "overflow" : "exact", unexpected ? "UNEXPECTED" : "OK"
    );
    return unexpected;
}

int main(int argc, char ** argv) {
    const int expect_baseline = argc == 3 && strcmp(argv[2], "--expect-baseline") == 0;
    if (argc < 2 || argc > 3 || (argc == 3 && !expect_baseline)) {
        fprintf(stderr, "Usage: %s /path/to/libggml-cpu.so [--expect-baseline]\n", argv[0]);
        return 2;
    }

    void * library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 2;
    }
    dlerror();
    i2s_dot_fn dot = (i2s_dot_fn) dlsym(library, "ggml_vec_dot_i2_i8_s");
    const char * symbol_error = dlerror();
    if (symbol_error || !dot) {
        fprintf(stderr, "dlsym failed: %s\n", symbol_error ? symbol_error : "symbol not found");
        dlclose(library);
        return 2;
    }

    uint8_t * weights = (uint8_t *) malloc(WEIGHT_BYTES);
    int8_t * activations = (int8_t *) malloc(K);
    if (!weights || !activations) {
        fprintf(stderr, "allocation failed\n");
        free(weights); free(activations); dlclose(library);
        return 2;
    }

    memset(weights, 0xAA, WEIGHT_BYTES);
    printf("kernel=ggml_vec_dot_i2_i8_s K=%d packed_code=2 rows=1 mode=%s\n",
           K, expect_baseline ? "known-baseline" : "expect-correct");
    int failures = 0;
    failures += run_case(dot, weights, activations, PATTERN_ALL_POSITIVE_127, expect_baseline);
    failures += run_case(dot, weights, activations, PATTERN_NINETY_PERCENT_POSITIVE, expect_baseline);
    failures += run_case(dot, weights, activations, PATTERN_ALTERNATING_BLOCKS, 0);
    failures += run_case(dot, weights, activations, PATTERN_ALL_POSITIVE_64, 0);
    printf("cases=4 unexpected_cases=%d result=%s\n", failures, failures ? "FAIL" : "PASS");

    free(weights); free(activations); dlclose(library);
    return failures ? 1 : 0;
}
