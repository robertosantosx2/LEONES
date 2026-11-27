; ============================================================================
; test_asmbin_validate.asm — standalone Linux syscall harness
; Tests a valid synthetic header and malformed size/range/dimension cases.
; Exit status 0 means all assertions passed.
; ============================================================================

bits 64
default rel
%include "constants.inc"

%define FIXTURE_SIZE 9709568

extern asmbin_validate
global _start

section .text
_start:
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jnz     fail

    ; ASMBIN v2 uses 2-byte scales per Q8 block, so its canonical
    ; embedding/layer/final-norm offsets and actual size differ from v1.
    mov     dword [rel fixture + HDR_VERSION], ASMBIN_VERSION_V2
    mov     dword [rel fixture + HDR_FLAGS], HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM | HDR_FLAG_FP16_SCALES
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 8384
    mov     qword [rel fixture + HDR_OFF_EMBED], 8520960
    mov     qword [rel fixture + HDR_OFF_LAYERS], 9635072
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 9643456
    mov     qword [rel fixture + HDR_FILE_SIZE], 9643584
    lea     rdi, [rel fixture]
    mov     rsi, 9643584
    call    asmbin_validate
    test    rax, rax
    jnz     fail
    mov     dword [rel fixture + HDR_VERSION], ASMBIN_VERSION
    mov     dword [rel fixture + HDR_FLAGS], HDR_FLAG_TIED_EMB | HDR_FLAG_QK_NORM
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 8832
    mov     qword [rel fixture + HDR_OFF_EMBED], 8520960
    mov     qword [rel fixture + HDR_OFF_LAYERS], 9700608
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 9709440
    mov     qword [rel fixture + HDR_FILE_SIZE], FIXTURE_SIZE

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
    mov     qword [rel fixture + HDR_OFF_EMBED], 8520960

    ; Top-level sections must begin at 64-byte boundaries.
    mov     qword [rel fixture + HDR_OFF_EMBED], 8520961
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_OFF_EMBED], 8520960

    ; A tokenizer section extending past actual_size must be rejected pre-read.
    mov     qword [rel fixture + HDR_OFF_EMBED], FIXTURE_SIZE + 64
    mov     qword [rel fixture + HDR_OFF_LAYERS], FIXTURE_SIZE + 128
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], FIXTURE_SIZE + 192
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_OFF_EMBED], 8520960
    mov     qword [rel fixture + HDR_OFF_LAYERS], 9700608
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 9709440

    ; Layer stride must be 64-byte aligned.
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 65
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 8832

    ; A 64-byte-aligned but incorrect canonical layer stride must be rejected.
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 8896
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_LAYER_STRIDE], 8832

    ; Final norm must immediately follow the complete layer section.
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 9709504
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + HDR_OFF_FINAL_NORM], 9709440

    ; Tokenizer sub-offset must not overlap its 64-byte section header.
    mov     qword [rel fixture + 128 + TOKH_OFF_B2T], 32
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 128 + TOKH_OFF_B2T], 64

    ; Tokenizer reserved header bytes must remain zero.
    mov     qword [rel fixture + 128 + 32], 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 128 + 32], 0

    ; Byte-to-token IDs must be inside the vocabulary.
    mov     dword [rel fixture + 192], 32768
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + 192], 0

    ; Token offsets must be monotonic.
    mov     dword [rel fixture + 1220], 2
    mov     dword [rel fixture + 1224], 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + 1220], 0
    mov     dword [rel fixture + 1224], 0

    ; Last token offset must produce the canonical token-bytes/table boundary.
    mov     dword [rel fixture + 132288], 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + 132288], 0

    ; Token-offset sub-array must begin at its canonical location.
    mov     qword [rel fixture + 128 + TOKH_OFF_OFFSETS], 1096
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 128 + TOKH_OFF_OFFSETS], 1088

    ; BPE left/right token IDs must be inside the vocabulary.
    mov     dword [rel fixture + 6283700], 32768
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + 6283700], 1

    ; BPE merged token ID must be inside the vocabulary.
    mov     dword [rel fixture + 6283704], 32768
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + 6283704], 3

    ; BPE rank must be inside the vocabulary.
    mov     dword [rel fixture + 6283708], 32768
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     dword [rel fixture + 6283708], 0

    ; Empty BPE slots must have zero key and merged ID.
    mov     qword [rel fixture + 6283728], 1
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 6283728], 0

    ; Duplicate BPE keys in the same probe chain must be rejected.
    mov     qword [rel fixture + 6283712], 0x0000000100000002
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 6283712], 0x000020620000079A

    ; An empty slot before a displaced key breaks its linear-probe chain.
    mov     qword [rel fixture + 6283696], 0
    mov     dword [rel fixture + 6283704], 0
    mov     dword [rel fixture + 6283708], 0xFFFFFFFF
    lea     rdi, [rel fixture]
    mov     rsi, FIXTURE_SIZE
    call    asmbin_validate
    test    rax, rax
    jz      fail
    mov     qword [rel fixture + 6283696], 0x0000000100000002
    mov     dword [rel fixture + 6283704], 3
    mov     dword [rel fixture + 6283708], 0

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
    ; 101: valid fixture rejected. 100: malformed fixture unexpectedly accepted.
    test    rax, rax
    jz      .assertion_failed
    mov     edi, 101
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
    dq 8520960                   ; embedding offset
    dq 9700608                    ; layers offset
    dq 8832                       ; canonical v1 layer stride
    dq 9709440                    ; final norm offset
    dq FIXTURE_SIZE               ; file size
    times 128 - ($ - fixture) db 0
    dq 64, 1088, 132224, 132224  ; canonical tokenizer sub-offsets
    times 192 - ($ - fixture) db 0
    times 1024 db 0              ; byte_to_tok[256]
    times 1216 - ($ - fixture) db 0
    times (32768 + 1) * 4 db 0   ; monotonic token_offsets[]
    times 132352 - ($ - fixture) db 0
    times 384459 dq 0, 0xFFFFFFFF00000000 ; empty slots before the collision cluster
    dq 0x0000000100000002      ; key (1,2), home slot 384459
    dd 3, 0                     ; merged_id=3, rank=0
    dq 0x000020620000079A      ; key (8290,1946), same home slot
    dd 4, 1                     ; merged_id=4, rank=1
    times 139827 dq 0, 0xFFFFFFFF00000000 ; remaining empty slots
    times FIXTURE_SIZE - ($ - fixture) db 0
