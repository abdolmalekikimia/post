from __future__ import annotations

from dataclasses import dataclass, field
import statistics
from typing import Any

from utils.step_report import format_detail


def percentile(values: list[float], percentage: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = percentage / 100 * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@dataclass
class StressSample:
    iteration: int
    case_name: str
    expected_status: Any
    actual_status: Any = None
    passed: bool = False
    latency_seconds: float = 0.0
    payload_sent: Any = None
    response_received: Any = None
    correlation_id: str | None = None
    error: str = ""
    error_kind: str = ""


@dataclass
class StressSummary:
    samples: list[StressSample] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return len(self.samples)

    @property
    def passed_expected_responses(self) -> int:
        return sum(sample.passed for sample in self.samples)

    @property
    def unexpected_responses(self) -> int:
        return sum(
            not sample.passed and not sample.error_kind
            for sample in self.samples
        )

    @property
    def transport_errors(self) -> int:
        return sum(bool(sample.error_kind) for sample in self.samples)

    @property
    def connection_resets(self) -> int:
        return sum(
            any(
                marker in f"{sample.error} {sample.error_kind}".lower()
                for marker in ("reset", "closed", "broken pipe")
            )
            for sample in self.samples
        )

    @property
    def timeout_count(self) -> int:
        return sum(
            any(
                marker in f"{sample.error} {sample.error_kind}".lower()
                for marker in ("timeout", "timed out")
            )
            for sample in self.samples
        )

    @property
    def latencies(self) -> list[float]:
        return [sample.latency_seconds for sample in self.samples]

    def metrics(self) -> dict[str, float]:
        values = self.latencies
        return {
            "minimum_latency": min(values, default=0.0),
            "average_latency": statistics.fmean(values) if values else 0.0,
            "maximum_latency": max(values, default=0.0),
            "p50_latency": percentile(values, 50),
            "p95_latency": percentile(values, 95),
            "p99_latency": percentile(values, 99),
        }

    def render(self, flow_name: str) -> str:
        metrics = self.metrics()
        lines = [
            f"Stress report: {flow_name}",
            (
                "Summary: "
                f"total={self.total_requests}, "
                f"passed={self.passed_expected_responses}, "
                f"unexpected={self.unexpected_responses}, "
                f"transportErrors={self.transport_errors}, "
                f"connectionResets={self.connection_resets}, "
                f"timeouts={self.timeout_count}"
            ),
            (
                "Latency(s): "
                f"min={metrics['minimum_latency']:.3f}, "
                f"avg={metrics['average_latency']:.3f}, "
                f"max={metrics['maximum_latency']:.3f}, "
                f"p50={metrics['p50_latency']:.3f}, "
                f"p95={metrics['p95_latency']:.3f}, "
                f"p99={metrics['p99_latency']:.3f}"
            ),
        ]
        for sample in sorted(self.samples, key=lambda item: item.iteration):
            result = "PASS" if sample.passed else "FAIL"
            lines.append(
                f"{sample.iteration:03d}. [{result}] {sample.case_name} "
                f"expected={sample.expected_status} "
                f"actual={sample.actual_status!r} "
                f"latency={sample.latency_seconds:.3f}s"
            )
            if sample.correlation_id:
                lines.append(f"    correlationId: {sample.correlation_id}")
            if sample.payload_sent is not None:
                lines.append(
                    f"    payloadSent: {format_detail(sample.payload_sent)}"
                )
            if sample.response_received is not None:
                lines.append(
                    "    responseReceived: "
                    f"{format_detail(sample.response_received)}"
                )
            if sample.error:
                lines.append(f"    error: {sample.error}")
        return "\n".join(lines)
