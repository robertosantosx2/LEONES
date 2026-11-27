; ============================================================================
; asmbin_validate.asm — bounded ASMBIN v1/v2 header and section validator
;
; ABI: int64 asmbin_validate(const void *base, uint64 actual_size)
; Returns 0 when the fixed header and top-level section ranges are safe,
; otherwise a negative error code. Does not mutate the artifact.
;
; This is deliberately a first-stage guard, not a complete tokenizer/BPE
; validator and not yet wired into model_init. Keep the checks before any
; data-dependent pointer construction.
; ============================================================================

bits 64
default rel
%include "constants.inc"

%define ASMBIN_HEADER_SIZE 128
%define Q8_MAX_K 16384
%define ERR_SIZE       -1
%define ERR_HEADER     -2
%define ERR_VERSION    -3
%define ERR_FLAGS      -4
%define ERR_DIMS       -5
%define ERR_RANGE      -6
%define ERR_TOKENIZER  -7

section .text
global asmbin_validate

; Range macro: verify [offset, offset+length) lies inside actual_size
; Inputs: offset register, length register, actual_size in rsi
%macro CHECK_RANGE 2
    cmp     %1, rsi
    ja      .bad_range
    mov     r11, rsi
    sub     r11, %1
    cmp     %2, r11
    ja      .bad_range
%endmacro

asmbin_validate:
    ; Do not dereference base until the complete fixed header is available.
    cmp     rsi, ASMBIN_HEADER_SIZE
    jb      .bad_size

    cmp     dword [rdi + HDR_MAGIC], ASMBIN_MAGIC
    jne     .bad_header

    mov     eax, [rdi + HDR_VERSION]
    cmp     eax, ASMBIN_VERSION
    je      .version_v1
    cmp     eax, ASMBIN_VERSION_V2
    jne     .bad_version
    mov     r10d, 4                    ; scale shift for v2
    jmp     .version_ok
.version_v1:
    mov     r10d, 3                    ; scale shift for v1
.version_ok:
    ; Require tied embeddings + QK norm; reject unknown flags.
    mov     eax, [rdi + HDR_FLAGS]
    mov     ecx, eax
    and     ecx, (HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM)
    cmp     ecx, (HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM)
    jne     .bad_flags
    and     eax, ~(HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM | HDR_FLAG_FP16_SCALES)
    jnz     .bad_flags
    cmp     dword [rdi + HDR_VERSION], ASMBIN_VERSION
    jne     .check_v2_flag
    test    dword [rdi + HDR_FLAGS], HDR_FLAG_FP16_SCALES
    jnz     .bad_flags
    jmp     .flags_ok
.check_v2_flag:
    test    dword [rdi + HDR_FLAGS], HDR_FLAG_FP16_SCALES
    jz      .bad_flags
.flags_ok:
    ; Header-declared file size must match the mapped/file size exactly.
    mov     rax, [rdi + HDR_FILE_SIZE]
    cmp     rax, rsi
    jne     .bad_size

    ; Reserved header bytes must remain zero in this format revision.
    mov     rax, [rdi + 112]
    or      rax, [rdi + 120]
    jnz     .bad_header

    ; Runtime-critical scalar fields and fixed tokenizer hash mask.
    cmp     dword [rdi + HDR_MAX_SEQ_LEN], 0
    je      .bad_dims
    cmp     dword [rdi + HDR_HT_MASK], 524287
    jne     .bad_tokenizer

    ; Required dimensions must be nonzero.
    mov     eax, [rdi + HDR_DIM]
    test    eax, eax
    jz      .bad_dims
    mov     ecx, [rdi + HDR_HIDDEN_DIM]
    test    ecx, ecx
    jz      .bad_dims
    mov     edx, [rdi + HDR_N_LAYERS]
    test    edx, edx
    jz      .bad_dims
    mov     r8d, [rdi + HDR_N_HEADS]
    test    r8d, r8d
    jz      .bad_dims
    mov     r9d, [rdi + HDR_N_KV_HEADS]
    test    r9d, r9d
    jz      .bad_dims
    mov     r11d, [rdi + HDR_HEAD_DIM]
    test    r11d, r11d
    jz      .bad_dims

    ; EOS IDs must address entries in the declared vocabulary.
    mov     eax, [rdi + HDR_VOCAB_SIZE]
    test    eax, eax
    jz      .bad_dims
    cmp     [rdi + HDR_EOS_1], eax
    jae     .bad_dims
    cmp     [rdi + HDR_EOS_2], eax
    jae     .bad_dims

    ; Quantized K dimensions must be block aligned and within current kernel.
    test    eax, 31
    jnz     .bad_dims
    test    ecx, 31
    jnz     .bad_dims
    cmp     eax, Q8_MAX_K
    ja      .bad_dims
    cmp     ecx, Q8_MAX_K
    ja      .bad_dims

    ; GQA divisibility and head dimension constraints.
    mov     eax, r8d
    xor     edx, edx
    div     r9d
    test    edx, edx
    jnz     .bad_dims
    test    r11d, 1
    jnz     .bad_dims

    ; q_dim = n_heads * head_dim must fit Q8 kernel and uint32.
    mov     eax, r8d
    mul     r11d
    test    edx, edx
    jnz     .bad_dims
    test    eax, 31
    jnz     .bad_dims
    cmp     eax, Q8_MAX_K
    ja      .bad_dims

    ; hidden_dim is also a quantized K dimension.
    ; Validate ordered top-level sections and their minimum required spans.
    mov     r8, [rdi + HDR_OFF_TOKENIZER]
    mov     r9, [rdi + HDR_OFF_EMBED]
    mov     r10, [rdi + HDR_OFF_LAYERS]
    mov     r11, [rdi + HDR_OFF_FINAL_NORM]
    mov     rdx, [rdi + HDR_LAYER_STRIDE]

    cmp     r8, ASMBIN_HEADER_SIZE
    jb      .bad_range
    cmp     r8, r9
    jae     .bad_range
    cmp     r9, r10
    jae     .bad_range
    cmp     r10, r11
    jae     .bad_range
    test    rdx, rdx
    jz      .bad_range

    ; Tokenizer header (four uint64 sub-offsets) must fit.
    mov     rax, r8
    mov     rcx, 64
    CHECK_RANGE rax, rcx
    ; Every tokenizer sub-offset must remain inside tokenizer section.
    mov     rax, r9
    sub     rax, r8                    ; tokenizer section length
    mov     rcx, [rdi + r8 + TOKH_OFF_B2T]
    cmp     rcx, 64
    jb      .bad_tokenizer
    cmp     rcx, rax
    jae     .bad_tokenizer
    mov     rcx, [rdi + r8 + TOKH_OFF_OFFSETS]
    cmp     rcx, 64
    jb      .bad_tokenizer
    cmp     rcx, rax
    jae     .bad_tokenizer
    mov     rcx, [rdi + r8 + TOKH_OFF_BYTES]
    cmp     rcx, 64
    jb      .bad_tokenizer
    cmp     rcx, rax
    jae     .bad_tokenizer
    mov     rcx, [rdi + r8 + TOKH_OFF_HT]
    cmp     rcx, 64
    jb      .bad_tokenizer
    cmp     rcx, rax
    jae     .bad_tokenizer

    ; Embedding extent: vocab * (dim + dim/2^scale_shift).
    mov     eax, [rdi + HDR_DIM]
    ; Derive scale shift from the version; do not trust an unvalidated flag.
    mov     r8d, 3
    cmp     dword [rdi + HDR_VERSION], ASMBIN_VERSION_V2
    jne     .embed_shift_ready
    mov     r8d, 4
.embed_shift_ready:
    mov     ecx, eax
    mov     edx, ecx
    mov     cl, r8b
    shr     edx, cl
    add     eax, edx
    mov     ecx, [rdi + HDR_VOCAB_SIZE]
    test    ecx, ecx
    jz      .bad_dims
    mul     ecx
    test    edx, edx
    jnz     .bad_range
    mov     rcx, rax                  ; embedding byte length
    mov     rax, [rdi + HDR_OFF_EMBED]
    CHECK_RANGE rax, rcx
    mov     rax, [rdi + HDR_OFF_EMBED]
    add     rax, rcx
    cmp     rax, [rdi + HDR_OFF_LAYERS]
    ja      .bad_range

    ; Layer section extent: n_layers * layer_stride, bounded before final norm.
    mov     eax, [rdi + HDR_N_LAYERS]
    mul     qword [rdi + HDR_LAYER_STRIDE]
    test    rdx, rdx
    jnz     .bad_range
    mov     rcx, rax
    mov     rax, [rdi + HDR_OFF_LAYERS]
    CHECK_RANGE rax, rcx
    add     rax, rcx
    cmp     rax, [rdi + HDR_OFF_FINAL_NORM]
    ja      .bad_range

    ; Final RMSNorm vector: dim * sizeof(float32).
    mov     eax, [rdi + HDR_DIM]
    shl     rax, 2
    mov     rcx, rax
    mov     rax, [rdi + HDR_OFF_FINAL_NORM]
    CHECK_RANGE rax, rcx

    xor     eax, eax
    ret

.bad_size:
    mov     rax, ERR_SIZE
    ret
.bad_header:
    mov     rax, ERR_HEADER
    ret
.bad_version:
    mov     rax, ERR_VERSION
    ret
.bad_flags:
    mov     rax, ERR_FLAGS
    ret
.bad_dims:
    mov     rax, ERR_DIMS
    ret
.bad_range:
    mov     rax, ERR_RANGE
    ret
.bad_tokenizer:
    mov     rax, ERR_TOKENIZER
    ret
