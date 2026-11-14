#include "nepenthes_trace.hpp"

#include <atomic>
#include <cassert>
#include <cstdint>

struct Capture {
    std::atomic<std::uint64_t> count{0};
    std::atomic<std::uint64_t> last_timestamp{0};
    std::atomic<std::uint64_t> last_duration{0};
    std::atomic<std::uint32_t> last_layer{0};
    std::atomic<std::uint16_t> last_kind{0};
};

static void capture_event(const nepenthes::Event& event, void* opaque) noexcept {
    auto* capture = static_cast<Capture*>(opaque);
    capture->last_timestamp.store(event.monotonic_ns, std::memory_order_relaxed);
    capture->last_duration.store(event.duration_ns, std::memory_order_relaxed);
    capture->last_layer.store(event.layer, std::memory_order_relaxed);
    capture->last_kind.store(static_cast<std::uint16_t>(event.kind), std::memory_order_relaxed);
    capture->count.fetch_add(1, std::memory_order_relaxed);
}

int main() {
    nepenthes::Trace::disable();

    // Disabled instrumentation is a safe no-op.
    nepenthes::Event disabled{};
    disabled.kind = nepenthes::EventKind::cache_miss;
    nepenthes::Trace::emit(disabled);
    assert(!nepenthes::Trace::enabled());

    Capture capture;
    nepenthes::Trace::install(&capture_event, &capture);
    assert(nepenthes::Trace::enabled());

    nepenthes::Event route{};
    route.kind = nepenthes::EventKind::routing;
    route.request_id = 42;
    route.layer = 7;
    route.expert = 19;
    nepenthes::Trace::emit(route);
    assert(capture.count.load() == 1);
    assert(capture.last_timestamp.load() > 0);
    assert(capture.last_layer.load() == 7);
    assert(capture.last_kind.load() == static_cast<std::uint16_t>(nepenthes::EventKind::routing));

    nepenthes::Event wait{};
    wait.kind = nepenthes::EventKind::stall;
    wait.request_id = 42;
    wait.layer = 7;
    {
        nepenthes::ScopedEvent span(wait);
    }
    assert(capture.count.load() == 2);
    assert(capture.last_duration.load() <= nepenthes::monotonic_now_ns());
    assert(capture.last_kind.load() == static_cast<std::uint16_t>(nepenthes::EventKind::host_wait_end));

    nepenthes::Trace::disable();
    assert(!nepenthes::Trace::enabled());
    nepenthes::Trace::emit(route);
    assert(capture.count.load() == 2);
    return 0;
}
