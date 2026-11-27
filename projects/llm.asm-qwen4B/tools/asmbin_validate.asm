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
%define ERR_LAYOUT     -8
%define ERR_EMBED_END  -9
%define ERR_LAYER_END  -10
%define ERR_FILE_END   -11
%define BPE_HASH_MULT  0x9E3779B97F4A7C15
%define BPE_MAX_PROBE  128

section .text
global asmbin_validate

%macro ADD_Q8_MATRIX 2
    ; Align matrix start to 64 bytes.
    add     rsi, 63
    jc      .bad_layer_stride
    and     rsi, -64

    ; row_bytes(K) = K + K/8 for v1, K + K/16 for v2.
    mov     rax, %2
    mov     rdx, rax
    cmp     dword [rdi + HDR_VERSION], ASMBIN_VERSION_V2
    je      %%fp16_scales
    shr     rdx, 3
    jmp     %%row_size_ready
%%fp16_scales:
    shr     rdx, 4
%%row_size_ready:
    add     rax, rdx

    ; rows * row_bytes, with the high half checked for overflow.
    mul     %1
    test    rdx, rdx
    jnz     .bad_layer_stride
    add     rsi, rax
    jc      .bad_layer_stride
%endmacro

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

    ; Restore dim: EAX held vocab_size for the EOS bounds checks above.
    mov     eax, [rdi + HDR_DIM]

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

    ; Verify the exact canonical stride implied by the seven Q8 matrices.
    ; Preserve actual_size because the helper uses RSI as its size cursor.
    push    rsi
    call    asmbin_expected_layer_stride
    pop     rsi
    test    rax, rax
    js      .bad_range
    cmp     rax, [rdi + HDR_LAYER_STRIDE]
    jne     .bad_layout

    ; hidden_dim is also a quantized K dimension.
    ; Validate ordered top-level sections and their minimum required spans.
    mov     r8, [rdi + HDR_OFF_TOKENIZER]
    mov     r9, [rdi + HDR_OFF_EMBED]
    mov     r10, [rdi + HDR_OFF_LAYERS]
    mov     r11, [rdi + HDR_OFF_FINAL_NORM]
    mov     rdx, [rdi + HDR_LAYER_STRIDE]

    ; Canonical top-level section starts and layer stride are 64-byte aligned.
    cmp     r8, ASMBIN_HEADER_SIZE
    jne     .bad_layout
    test    r9, 63
    jnz     .bad_layout
    test    r10, 63
    jnz     .bad_layout
    test    r11, 63
    jnz     .bad_layout
    test    rdx, 63
    jnz     .bad_layout
    cmp     r8, r9
    jae     .bad_layout
    cmp     r9, r10
    jae     .bad_layout
    cmp     r10, r11
    jae     .bad_layout
    test    rdx, rdx
    jz      .bad_range

    ; Bound the entire tokenizer section before the helper dereferences it.
    mov     rax, r8
    mov     rcx, r9
    sub     rcx, rax
    CHECK_RANGE rax, rcx

    ; Validate the canonical tokenizer sub-layout and bounded arrays.
    push    rsi
    call    asmbin_validate_tokenizer
    pop     rsi
    test    rax, rax
    js      .bad_tokenizer

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
    ; The exporter aligns the next section start to 64 bytes.
    add     rax, 63
    and     rax, -64
    cmp     rax, [rdi + HDR_OFF_LAYERS]
    jne     .bad_embed_end

    ; Layer section extent: n_layers * layer_stride, ending exactly at final norm.
    mov     eax, [rdi + HDR_N_LAYERS]
    mul     qword [rdi + HDR_LAYER_STRIDE]
    test    rdx, rdx
    jnz     .bad_range
    mov     rcx, rax
    mov     rax, [rdi + HDR_OFF_LAYERS]
    CHECK_RANGE rax, rcx
    add     rax, rcx
    cmp     rax, [rdi + HDR_OFF_FINAL_NORM]
    jne     .bad_layer_end

    ; Final RMSNorm vector: dim * sizeof(float32).
    mov     eax, [rdi + HDR_DIM]
    shl     rax, 2
    mov     rcx, rax
    mov     rax, [rdi + HDR_OFF_FINAL_NORM]
    CHECK_RANGE rax, rcx
    add     rax, rcx
    ; The file ends at the next 64-byte boundary after final RMSNorm.
    add     rax, 63
    and     rax, -64
    cmp     rax, rsi
    jne     .bad_file_end

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
.bad_layout:
    mov     rax, ERR_LAYOUT
    ret
.bad_embed_end:
    mov     rax, ERR_EMBED_END
    ret
.bad_layer_end:
    mov     rax, ERR_LAYER_END
    ret
.bad_file_end:
    mov     rax, ERR_FILE_END
    ret

; Validate the canonical tokenizer section layout without parsing BPE entries.
; Input: RDI = ASMBIN base. Output: zero or ERR_TOKENIZER.
; Checks sub-offsets, reserved bytes, byte IDs, monotonic token offsets,
; token-byte extent, and the complete fixed-size merge-table region.
asmbin_validate_tokenizer:
    push    r12                         ; preserve SysV callee-saved register
    mov     r8, [rdi + HDR_OFF_TOKENIZER]
    mov     r9, [rdi + HDR_OFF_EMBED]
    cmp     r9, r8
    jbe     .bad_tokenizer_layout
    mov     rsi, r9
    sub     rsi, r8                    ; tokenizer section length
    cmp     rsi, 64
    jb      .bad_tokenizer_layout
    lea     r10, [rdi + r8]            ; tokenizer section base

    ; Reserved tokenizer-header bytes must be zero.
    mov     rax, [r10 + 32]
    or      rax, [r10 + 40]
    or      rax, [r10 + 48]
    or      rax, [r10 + 56]
    jnz     .bad_tokenizer_layout

    ; Exporter-canonical byte_to_tok and token-offset array starts.
    cmp     qword [r10 + TOKH_OFF_B2T], 64
    jne     .bad_tokenizer_layout
    cmp     qword [r10 + TOKH_OFF_OFFSETS], 1088
    jne     .bad_tokenizer_layout

    ; token_offsets occupies (vocab_size + 1) uint32 entries.
    mov     eax, [rdi + HDR_VOCAB_SIZE]
    inc     rax
    shl     rax, 2
    mov     rdx, [r10 + TOKH_OFF_OFFSETS]
    cmp     rdx, rsi
    ja      .bad_tokenizer_layout
    mov     rcx, rsi
    sub     rcx, rdx
    cmp     rax, rcx
    ja      .bad_tokenizer_layout

    ; off_tok_bytes = align64(off_tok_offsets + token_offsets_bytes).
    add     rax, rdx
    add     rax, 63
    and     rax, -64
    cmp     rax, [r10 + TOKH_OFF_BYTES]
    jne     .bad_tokenizer_layout

    ; offsets[0] must be zero and the array must be monotonic.
    mov     rdx, [r10 + TOKH_OFF_OFFSETS]
    lea     rdx, [r10 + rdx]
    cmp     dword [rdx], 0
    jne     .bad_tokenizer_layout
    mov     ecx, [rdi + HDR_VOCAB_SIZE]
    xor     eax, eax
    add     rdx, 4
.token_offsets_loop:
    mov     r8d, [rdx]
    cmp     r8d, eax
    jb      .bad_tokenizer_layout
    mov     eax, r8d
    add     rdx, 4
    dec     ecx
    jnz     .token_offsets_loop

    ; The last token offset determines the exact token-byte region length.
    mov     r9, [r10 + TOKH_OFF_BYTES]
    cmp     r9, rsi
    ja      .bad_tokenizer_layout
    mov     rcx, rsi
    sub     rcx, r9
    mov     edx, eax
    cmp     rdx, rcx
    ja      .bad_tokenizer_layout

    ; off_merge_ht = align64(off_tok_bytes + last_token_offset).
    mov     rax, r9
    add     rax, rdx
    add     rax, 63
    and     rax, -64
    cmp     rax, [r10 + TOKH_OFF_HT]
    jne     .bad_tokenizer_layout

    ; The fixed 524288-entry table occupies exactly 8 MiB.
    mov     rcx, [r10 + TOKH_OFF_HT]
    cmp     rcx, rsi
    ja      .bad_tokenizer_layout
    mov     rdx, rsi
    sub     rdx, rcx
    cmp     rdx, 8388608
    jb      .bad_tokenizer_layout
    mov     rax, rcx
    add     rax, 8388608
    add     rax, 63
    and     rax, -64
    cmp     rax, rsi
    jne     .bad_tokenizer_layout

    ; All 256 byte_to_tok IDs must be inside the vocabulary.
    lea     rdx, [r10 + 64]
    mov     ecx, 256
    mov     r11d, [rdi + HDR_VOCAB_SIZE]
.byte_to_tok_loop:
    mov     eax, [rdx]
    cmp     eax, r11d
    jae     .bad_tokenizer_layout
    add     rdx, 4
    dec     ecx
    jnz     .byte_to_tok_loop

    ; Validate merge-entry IDs/ranks, canonical empty slots, and linear-probe
    ; reachability. The 128-probe cap bounds worst-case validation work.
    mov     rax, [r10 + TOKH_OFF_HT]
    lea     r10, [r10 + rax]          ; merge table base
    mov     esi, 524288               ; outer slot count
    xor     r8d, r8d                  ; current slot index
    xor     r9d, r9d                  ; count empty slots
.bpe_entry_loop:
    lea     rdx, [r10 + r8*8]
    lea     rdx, [rdx + r8*8]         ; current entry = table + slot*16
    mov     eax, [rdx + 12]           ; rank
    cmp     eax, 0xFFFFFFFF
    je      .bpe_empty

    mov     r11d, [rdi + HDR_VOCAB_SIZE]
    mov     eax, [rdx]                ; right token ID
    cmp     eax, r11d
    jae     .bad_tokenizer_layout
    mov     eax, [rdx + 4]            ; left token ID
    cmp     eax, r11d
    jae     .bad_tokenizer_layout
    mov     eax, [rdx + 8]            ; merged token ID
    cmp     eax, r11d
    jae     .bad_tokenizer_layout
    mov     eax, [rdx + 12]           ; merge rank
    cmp     eax, r11d
    jae     .bad_tokenizer_layout

    ; Home slot = low64(key * Fibonacci multiplier) >> 45.
    mov     r12, [rdx]
    mov     rax, r12
    mov     rcx, BPE_HASH_MULT
    imul    rax, rcx
    shr     rax, 45
    mov     r11d, eax
    xor     ecx, ecx
.bpe_probe_loop:
    cmp     r11d, r8d
    je      .bpe_next
    inc     ecx
    cmp     ecx, BPE_MAX_PROBE
    ja      .bad_tokenizer_layout
    lea     rax, [r10 + r11*8]
    lea     rax, [rax + r11*8]
    cmp     dword [rax + 12], 0xFFFFFFFF
    je      .bad_tokenizer_layout     ; an empty slot breaks the probe chain
    cmp     qword [rax], r12
    je      .bad_tokenizer_layout     ; duplicate key earlier in the chain
    inc     r11d
    and     r11d, 524287
    jmp     .bpe_probe_loop
.bpe_empty:
    cmp     qword [rdx], 0
    jne     .bad_tokenizer_layout
    cmp     dword [rdx + 8], 0
    jne     .bad_tokenizer_layout
    inc     r9d
.bpe_next:
    inc     r8d
    dec     esi
    jnz     .bpe_entry_loop
    test    r9d, r9d
    jz      .bad_tokenizer_layout

    xor     eax, eax
    pop     r12
    ret
.bad_tokenizer_layout:
    mov     rax, ERR_TOKENIZER
    pop     r12
    ret

; Return the canonical per-layer stride from the exporter layout.
; Input: RDI = ASMBIN base. Output: RAX = stride or negative error.
; Uses only caller-saved registers; RSI is the running byte cursor.
asmbin_expected_layer_stride:
    mov     r8d, [rdi + HDR_DIM]
    mov     r9d, [rdi + HDR_HIDDEN_DIM]

    ; q_dim and kv_dim (both were already bounded by the caller).
    mov     eax, [rdi + HDR_N_HEADS]
    mov     edx, [rdi + HDR_HEAD_DIM]
    imul    rax, rdx
    mov     r10, rax
    mov     eax, [rdi + HDR_N_KV_HEADS]
    imul    rax, rdx
    mov     r11, rax

    ; Four dim-sized norms plus q_norm and k_norm (head_dim each).
    mov     rsi, r8
    shl     rsi, 4                    ; 4 * dim * sizeof(float32)
    mov     rax, rdx
    shl     rax, 3                    ; 2 * head_dim * sizeof(float32)
    add     rsi, rax
    jc      .bad_layer_stride

    ; Q, K, V, O, gate, up, down in exporter order.
    ADD_Q8_MATRIX r10, r8
    ADD_Q8_MATRIX r11, r8
    ADD_Q8_MATRIX r11, r8
    ADD_Q8_MATRIX r8,  r10
    ADD_Q8_MATRIX r9,  r8
    ADD_Q8_MATRIX r9,  r8
    ADD_Q8_MATRIX r8,  r9

    add     rsi, 63
    jc      .bad_layer_stride
    and     rsi, -64
    mov     rax, rsi
    ret
.bad_layer_stride:
    mov     rax, ERR_RANGE
    ret
