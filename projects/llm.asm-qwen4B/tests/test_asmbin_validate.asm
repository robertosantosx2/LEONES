; ============================================================================
; test_asmbin_validate.asm — standalone Linux syscall harness
; Tests a valid synthetic header and malformed size/range/dimension cases.
; Exit status 0 means all assertions passed.
; ============================================================================

bits 64
default rel
%include "constants.inc"

extern asmbin_validate
global _start

section .text
_start:
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jnz     .fail

    ; A truncated fixed header must be rejected before dereference.
    lea     rdi, [rel fixture]
    mov     rsi, 127
    call    asmbin_validate
    test    rax, rax
    jz      .fail

    ; Declared size mismatch.
    mov     qword [rel fixture + HDR_FILE_SIZE], FIXTURE_SIZE - 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      .fail
    mov     qword [rel fixture + HDR_FILE_SIZE], FIXTURE_SIZE

    ; Embedding offset outside the file.
    mov     qword [rel fixture + HDR_OFF_EMBED], FIXTURE_SIZE + 8
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      .fail
    mov     qword [rel fixture + HDR_OFF_EMBED], 192

    ; Invalid GQA divisibility.
    mov     dword [rel fixture + HDR_N_KV_HEADS], 2
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      .fail

    mov     eax, 60
    xor     edi, edi
    syscall
.fail:
    mov     eax, 60
    mov     edi, 1
    syscall

%define FIXTURE_SIZE 1536
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
    dd 32                         ; vocab_size
    dd 128                        ; max_seq_len
    dd 0x3A83126F                 ; rms_eps (float32)
    dd 0x44800000                 ; rope_theta (float32)
    dd 0, 0                       ; eos ids
    dd 63                         ; ht_mask (not validated by this stage)
    dd HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM
    dq 128                        ; tokenizer offset
    dq 192                        ; embedding offset
    dq 1344                       ; layers offset
    dq 64                         ; layer stride
    dq 1408                       ; final norm offset
    dq FIXTURE_SIZE               ; file size
    times FIXTURE_SIZE - ($ - fixture) db 0
