from __future__ import annotations

from prometheus_client import Counter, Histogram, CollectorRegistry


class APIMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests_total = Counter(
            "api_requests_total",
            "Total API requests",
            labelnames=("method", "path", "status"),
            registry=self.registry,
        )
        self.request_latency = Histogram(
            "api_request_latency_seconds",
            "Latency per endpoint",
            labelnames=("method", "path"),
            registry=self.registry,
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
        )


api_metrics = APIMetrics()
