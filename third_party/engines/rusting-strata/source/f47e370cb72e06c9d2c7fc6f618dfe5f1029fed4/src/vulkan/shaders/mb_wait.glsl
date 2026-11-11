// Wait of the MoE combines for the CPU worker's done flag (mailbox word 16) to reach seq. Every workgroup of one combine
// gets the same answer through the verdict word (8, zeroed by moe_route): 1 once one of them saw the flag, 2 once one
// gave up first. On 2 none adds to x and err[0] = 1 tells the host; with conditional rendering the rest of the
// submission is skipped, and the host waits for the worker and runs the forward again from this combine
// (GpuModel::finish). The combines of one submission share SPINS polls (about 0.1 s on an RTX 3060; err[1] counts them,
// the host zeroes it at each wait), so a submission cannot outlast the driver's job timeout (amdgpu resets the GPU
// after 10 s) however long the worker reads experts from a cold drive. A poll can take far longer on other GPUs (RADV),
// so the host also sets err[2] once it has waited too long for a submission (Vk::submit), and a waiting combine gives
// up on it within 256 polls.
const uint SPINS = 1u << 19;
bool mb_wait(MB mb, uint seq, U32 err) {
    uint base = atomicLoad(err.v[1], gl_ScopeDevice, 0, 0), spins = base, v;
    for (;;) {
        if (atomicLoad(mb.v[16], gl_ScopeDevice, gl_StorageSemanticsBuffer, gl_SemanticsAcquire | gl_SemanticsMakeVisible) == seq) {
            v = atomicCompSwap(mb.v[8], 0u, 1u);
            // The workgroup that decided counts the polls of this combine.
            if (v == 0u) atomicAdd(err.v[1], spins - base);
            break;
        }
        // Without conditional rendering a later layer of a submission whose wait gave up stops within 256 polls.
        if (++spins >= SPINS || ((spins & 0xffu) == 0 && (atomicLoad(mb.v[8], gl_ScopeDevice, 0, 0) == 2u || atomicLoad(err.v[0], gl_ScopeDevice, 0, 0) != 0
                || atomicLoad(err.v[2], gl_ScopeDevice, 0, 0) != 0))) {
            v = atomicCompSwap(mb.v[8], 0u, 2u);
            if (v == 0u) v = 2u;
            break;
        }
    }
    if (v == 2u) { err.v[0] = 1; return false; }
    // 0 or 1: the flag is up (seen here or by the workgroup that wrote 1).
    while (atomicLoad(mb.v[16], gl_ScopeDevice, gl_StorageSemanticsBuffer, gl_SemanticsAcquire | gl_SemanticsMakeVisible) != seq) {}
    return true;
}
