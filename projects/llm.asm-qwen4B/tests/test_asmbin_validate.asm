; ============================================================================
; test_asmbin_validate.asm — standalone Linux syscall harness
; Tests a valid synthetic header and malformed size/range/dimension cases.
; Exit status 0 means all assertions passed.
; ============================================================================

bits 64
default rel
%include "constants.inc"

%define FIXTURE_SIZE 1180096

extern asmbin_validate
global _start

section .text
_start:
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jnz     fail

    ; ASMBIN v2 requires the FP16-scales flag and is accepted.
    mov     dword [rel fixture + HDR_VERSION], ASMBIN_VERSION_V2
    mov     dword [rel fixture + HDR_FLAGS], HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM | HDR_FLAG_FP16_SCALES
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jnz     fail
    mov     dword [rel fixture + HDR_VERSION], ASMBIN_VERSION
    mov     dword [rel fixture + HDR_FLAGS], HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM

    ; Invalid magic must be rejected.
    mov     dword [rel fixture + HDR_MAGIC], 0
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_MAGIC], ASMBIN_MAGIC

    ; Unknown format versions must be rejected.
    mov     dword [rel fixture + HDR_VERSION], 3
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_VERSION], ASMBIN_VERSION

    ; A missing required flag must be rejected.
    mov     dword [rel fixture + HDR_FLAGS], HDR_FLAG_TIED_EMB
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_FLAGS], HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM

    ; A truncated fixed header must be rejected before dereference.
    lea     rdi, [rel fixture]
    mov     rsi, 127
    call    asmbin_validate
    test    rax, rax
    jz      fail

    ; Declared size mismatch.
    mov     qword [rel fixture + HDR_FILE_SIZE], FIXTURE_SIZE - 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_FILE_SIZE], FIXTURE_SIZE

    ; Embedding offset outside the file.
    mov     qword [rel fixture + HDR_OFF_EMBED], FIXTURE_SIZE + 8
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_OFF_EMBED], 256

    ; Top-level sections must begin at 64-byte boundaries.
    mov     qword [rel fixture + HDR_OFF_EMBED], 257
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_OFF_EMBED], 256

    ; Layer stride must be 64-byte aligned.
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 65
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 64

    ; Final norm must immediately follow the complete layer section.
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 1180032
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 1179968

    ; Tokenizer sub-offset must not overlap its 64-byte section header.
    mov     qword [rel fixture + 128 + TOKH_OFF_B2T], 32
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 128 + TOKH_OFF_B2T], 64

    ; Invalid tokenizer hash mask must be rejected.
    mov     dword [rel fixture + HDR_HT_MASK], 63
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_HT_MASK], 524287

    ; EOS IDs must be inside the vocabulary.
    mov     dword [rel fixture + HDR_EOS_1], 32768
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_EOS_1], 0

    ; EOS_2 must also be inside the vocabulary.
    mov     dword [rel fixture + HDR_EOS_2], 32768
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_EOS_2], 0

    ; q_dim above the fixed Q8 kernel limit must be rejected.
    mov     dword [rel fixture + HDR_N_HEADS], 129
    mov     dword [rel fixture + HDR_HEAD_DIM], 128
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_N_HEADS], 1
    mov     dword [rel fixture + HDR_HEAD_DIM], 32

    ; max_seq_len must be nonzero.
    mov     dword [rel fixture + HDR_MAX_SEQ_LEN], 0
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + HDR_MAX_SEQ_LEN], 128

    ; Reserved header bytes must be zero.
    mov     qword [rel fixture + 112], 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 112], 0

    ; Invalid GQA divisibility.
    mov     dword [rel fixture + HDR_N_KV_HEADS], 2
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail

    mov     eax, 60
    xor     edi, edi
    syscall
fail:
    ; Return the low byte of the boundary delta for a rejected valid fixture;
    ; 100 means a malformed fixture was unexpectedly accepted.
    test    rax, rax
    jz      .assertion_failed
    mov     edi, eax
    and     edi, 255
    jnz     .exit_diagnostic
    mov     edi, 99
.exit_diagnostic:
    mov     eax, 60
    syscall
.assertion_failed:
    mov     eax, 60
    mov     edi, 100
    syscall

section .data
align 8
fixture:
    dd ASMBIN_MAGIC
    dd ASMBIN_VERSION
    dd 32                         ; dim
    dd 32                         ; hidden_dim
    dd 1                          ; n_layers
    dd 1                          ; n_heads
    dd 1                          ; n_kv_heads
    dd 32                         ; head_dim
    dd 32768                     ; vocab_size
    dd 128                        ; max_seq_len
    dd 0x3A83126F                 ; rms_eps (float32)
    dd 0x44800000                 ; rope_theta (float32)
    dd 0, 0                       ; eos ids
    dd 524287                     ; fixed 19-bit BPE hash mask
    dd HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM
    dq 128                        ; tokenizer offset
    dq 256                        ; embedding offset
    dq 1179904                    ; layers offset
    dq 64                         ; layer stride
    dq 1179968                    ; final norm offset
    dq FIXTURE_SIZE               ; file size
    times 128 - ($ - fixture) db 0
    dq 64, 72, 80, 88             ; tokenizer-relative sub-offsets after 64-byte header
    times 256 - ($ - fixture) db 0
    times FIXTURE_SIZE - ($ - fixture) db 0
