#pragma once

#include "quantize.cuh"

struct ShortConvArgs {
    // [first position, token ids...]
    const unsigned* batch;
    // Per token: input gate b, output gate c and value x, `channels` each.
    const float* bcx;
    // `taps` weights per channel, oldest input first.
    const float* conv;
    // The last gated inputs, row `pos % ring` holding position `pos`.
    float* ring;
    Act out;
    unsigned n;
    unsigned channels;
    unsigned taps;
    unsigned ring_len;
};

// One thread per channel steps through the batch: out = c * conv(b * x).
extern "C" __global__ void short_conv_q8(ShortConvArgs a) {
    const unsigned ch = blockIdx.x * blockDim.x + threadIdx.x;
    if (ch >= a.channels) return;
    const float* w = a.conv + static_cast<size_t>(ch) * a.taps;
    const unsigned pos0 = a.batch[0];
    for (unsigned t = 0; t < a.n; ++t) {
        const unsigned pos = pos0 + t;
        const float* bcx = a.bcx + static_cast<size_t>(t) * 3 * a.channels;
        a.ring[static_cast<size_t>(pos % a.ring_len) * a.channels + ch] =
            bcx[ch] * bcx[2 * a.channels + ch];
        float acc = 0.0f;
        for (unsigned i = 0; i < a.taps; ++i) {
            const unsigned p = (pos + a.ring_len - (a.taps - 1) + i) % a.ring_len;
            acc = fmaf(w[i], a.ring[static_cast<size_t>(p) * a.channels + ch], acc);
        }
        a.out.put(static_cast<size_t>(t) * a.channels + ch, bcx[a.channels + ch] * acc);
    }
}

// A large batch: one thread per (channel, token), inputs before the batch
// from the ring. grid (ceil(channels / 128), n), block 128.
extern "C" __global__ void short_conv_batch(ShortConvArgs a) {
    const unsigned ch = blockIdx.x * blockDim.x + threadIdx.x, t = blockIdx.y;
    if (ch >= a.channels) return;
    const float* w = a.conv + static_cast<size_t>(ch) * a.taps;
    const int pos0 = static_cast<int>(a.batch[0]), pos = pos0 + static_cast<int>(t);
    float acc = 0.0f;
    for (unsigned i = 0; i < a.taps; ++i) {
        const int p = pos - static_cast<int>(a.taps - 1 - i);
        float x = 0.0f;
        if (p >= pos0) {
            const float* bcx = a.bcx + static_cast<size_t>(p - pos0) * 3 * a.channels;
            x = bcx[ch] * bcx[2 * a.channels + ch];
        } else if (p >= 0) {
            x = a.ring[static_cast<size_t>(p % a.ring_len) * a.channels + ch];
        }
        acc = fmaf(w[i], x, acc);
    }
    const float* bcx = a.bcx + static_cast<size_t>(t) * 3 * a.channels;
    a.out.put(static_cast<size_t>(t) * a.channels + ch, bcx[a.channels + ch] * acc);
}

// grid ceil(channels / 128), block 128: the last taps - 1 gated inputs into
// the ring, after `short_conv_batch` has read the older ones.
extern "C" __global__ void short_conv_ring_store(ShortConvArgs a) {
    const unsigned ch = blockIdx.x * blockDim.x + threadIdx.x;
    if (ch >= a.channels) return;
    const unsigned pos0 = a.batch[0];
    for (unsigned i = 0; i + 1 < a.taps && i < a.n; ++i) {
        const unsigned t = a.n - 1 - i;
        const float* bcx = a.bcx + static_cast<size_t>(t) * 3 * a.channels;
        a.ring[static_cast<size_t>((pos0 + t) % a.ring_len) * a.channels + ch] =
            bcx[ch] * bcx[2 * a.channels + ch];
    }
}
