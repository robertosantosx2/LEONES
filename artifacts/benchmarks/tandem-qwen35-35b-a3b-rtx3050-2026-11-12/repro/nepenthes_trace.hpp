#pragma once

// Header-only, allocation-free event hook for engine-side NEPENTHES adapters.
// Install the sink before worker threads start; disable it after they join.
#include <atomic>
#include <chrono>
#include <cstdint>

namespace nepenthes {

enum class EventKind : std::uint16_t {
    request_start,
    request_end,
    model_load,
    model_unload,
    routing,
    cache_hit,
    cache_miss,
    eviction,
    prefetch,
    kv_cache,
    allocation,
    free,
    transfer,
    kernel,
    sync,
    stall,
    oom,
    fallback,
    error,
};

constexpr std::uint32_t phase_begin = 1u << 0;
constexpr std::uint32_t phase_end = 1u << 1;

struct Event {
    EventKind kind{EventKind::error};
    std::uint64_t monotonic_ns{0};
    std::uint64_t request_id{0};
    std::uint64_t object_id{0};
    std::uint64_t bytes{0};
    std::uint64_t duration_ns{0};
    std::uint32_t layer{0};
    std::uint32_t expert{0};
    std::uint32_t stream_id{0};
    std::uint32_t flags{0};
};

using Sink = void (*)(const Event&, void*) noexcept;

inline std::uint64_t monotonic_now_ns() noexcept {
    const auto now = std::chrono::steady_clock::now().time_since_epoch();
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(now).count());
}

class Trace final {
public:
    Trace() = delete;

    // The callback must be non-blocking, thread-safe and must not throw.
    // Configure once before concurrent inference; do not hot-swap the sink.
    static void install(Sink sink, void* context = nullptr) noexcept {
        context_.store(context, std::memory_order_relaxed);
        sink_.store(sink, std::memory_order_release);
    }

    static void disable() noexcept {
        sink_.store(nullptr, std::memory_order_release);
        context_.store(nullptr, std::memory_order_relaxed);
    }

    static bool enabled() noexcept {
        return sink_.load(std::memory_order_acquire) != nullptr;
    }

    static void emit(Event event) noexcept {
        const Sink sink = sink_.load(std::memory_order_acquire);
        if (sink == nullptr) {
            return;
        }
        if (event.monotonic_ns == 0) {
            event.monotonic_ns = monotonic_now_ns();
        }
        sink(event, context_.load(std::memory_order_relaxed));
    }

private:
    inline static std::atomic<Sink> sink_{nullptr};
    inline static std::atomic<void*> context_{nullptr};
};

class ScopedEvent final {
public:
    explicit ScopedEvent(Event event) noexcept
        : event_(event), started_ns_(monotonic_now_ns()) {}

    ScopedEvent(const ScopedEvent&) = delete;
    ScopedEvent& operator=(const ScopedEvent&) = delete;
    ScopedEvent(ScopedEvent&&) = delete;
    ScopedEvent& operator=(ScopedEvent&&) = delete;

    ~ScopedEvent() noexcept {
        const std::uint64_t finished = monotonic_now_ns();
        event_.monotonic_ns = started_ns_;
        event_.duration_ns = finished >= started_ns_ ? finished - started_ns_ : 0;
        Trace::emit(event_);
    }

private:
    Event event_;
    std::uint64_t started_ns_;
};

}  // namespace nepenthes
