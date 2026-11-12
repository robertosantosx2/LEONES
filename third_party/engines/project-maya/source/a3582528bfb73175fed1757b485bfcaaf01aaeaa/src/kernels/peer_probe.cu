// src/kernels/peer_probe.cpp - does this driver actually support the peer-expert-tier ops?
//
//   build/peer_probe
//
// Mercury's driver wedged (D-state, os_acquire_mutex) on host->peer copies during M2b phase 2;
// this probe decides which P2P primitives are safe BEFORE a model run risks the driver again.
// Ordered safest-first, each verified by data.  Markers are flushed before every op, so if a step
// wedges the host, the last printed line names the culprit exactly.
//
//   0. H2D on the peer device itself (cudaSetDevice(1) + plain copy) - the control.
//   1. a kernel on device 0 READING peer memory (UVA peer read).
//   2. cudaMemcpyPeerAsync device0 -> device1 (the D2D form).
//   3. pinned host -> peer device, issued from device 0 (the variant that wedged; last on purpose).
#include <cuda_runtime.h>

#include <cstdio>
#include <cstdlib>
#include <vector>

#define PEER_CHECK(what)                                                                     \
    do {                                                                                     \
        const cudaError_t e_ = cudaGetLastError();                                           \
        if (e_ != cudaSuccess) {                                                             \
            std::printf("PEERPROBE %s: FAILED (%s)\n", what, cudaGetErrorString(e_));        \
            std::fflush(stdout);                                                             \
            return 1;                                                                        \
        }                                                                                    \
    } while (0)

static void mark(const char* s) {
    std::printf("%s\n", s);
    std::fflush(stdout);
}

// reads `in` (may live on a peer device) and writes doubled values to `out`
__global__ void peek_kernel(const float* __restrict__ in, float* __restrict__ out, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = in[i] * 2.0f;
}

int main() {
    constexpr int kN = 1 << 18;   // 1 MB of floats
    const size_t bytes = (size_t) kN * sizeof(float);

    int n_dev = 0;
    cudaGetDeviceCount(&n_dev);
    if (n_dev < 2) {
        mark("PEERPROBE: single-GPU host; nothing to probe");
        return 0;
    }
    int can = 0;
    cudaDeviceCanAccessPeer(&can, 0, 1);
    std::printf("PEERPROBE: can_access_peer(0,1) = %d\n", can);
    std::fflush(stdout);
    if (!can) return 1;
    cudaDeviceEnablePeerAccess(1, 0);
    PEER_CHECK("enable_peer_access");

    // allocations on both devices
    float* d0 = nullptr;
    float* d0s = nullptr;
    cudaMalloc(&d0, bytes);                        // device 0 output
    cudaMalloc(&d0s, bytes);                       // device 0 staging
    cudaSetDevice(1);
    float* d1 = nullptr;
    float* d1b = nullptr;
    cudaMalloc(&d1, bytes);                        // device 1 resident
    cudaMalloc(&d1b, bytes);                       // device 1 second buffer
    cudaDeviceSynchronize();
    cudaSetDevice(0);
    PEER_CHECK("malloc");

    std::vector<float> host((size_t) kN);
    for (int i = 0; i < kN; ++i) host[(size_t) i] = (float) (i % 97) * 0.25f;
    float* pin = nullptr;
    cudaHostAlloc(&pin, bytes, cudaHostAllocDefault);
    for (int i = 0; i < kN; ++i) pin[i] = host[(size_t) i];
    PEER_CHECK("host_alloc");

    std::vector<float> out((size_t) kN);

    mark("PEERPROBE step0: H2D on device 1 (control) start");
    cudaSetDevice(1);
    cudaMemcpy(d1, pin, bytes, cudaMemcpyHostToDevice);
    cudaDeviceSynchronize();
    cudaSetDevice(0);
    PEER_CHECK("step0");
    mark("PEERPROBE step0: ok");

    mark("PEERPROBE step1: kernel on dev0 reads peer memory start");
    peek_kernel<<<(kN + 255) / 256, 256>>>(d1, d0, kN);
    cudaDeviceSynchronize();
    PEER_CHECK("step1 launch");
    cudaMemcpy(out.data(), d0, bytes, cudaMemcpyDeviceToHost);
    for (int i = 0; i < kN; ++i)
        if (out[(size_t) i] != host[(size_t) i] * 2.0f) {
            std::printf("PEERPROBE step1: WRONG DATA at %d\n", i);
            return 1;
        }
    mark("PEERPROBE step1: ok");

    mark("PEERPROBE step2: cudaMemcpyPeerAsync dev0 -> dev1 start");
    cudaMemcpyPeerAsync(d1b, 1, d0, 0, bytes, 0);
    cudaDeviceSynchronize();
    PEER_CHECK("step2");
    mark("PEERPROBE step2: ok");

    mark("PEERPROBE step3: pinned host -> dev1 issued from dev0 (the wedge suspect) start");
    cudaMemcpyAsync(d1, pin, bytes, cudaMemcpyHostToDevice, 0);
    cudaDeviceSynchronize();
    PEER_CHECK("step3");
    mark("PEERPROBE step3: ok");

    mark("PEERPROBE: ALL STEPS OK");
    return 0;
}
