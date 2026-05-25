"""htape.middleware
==================
Plug-and-play FastAPI middleware with a Prometheus-compatible ``/metrics``
endpoint.  Zero external dependencies — metrics are exposed in the standard
Prometheus text-format using only the Python standard library.

Tracked metrics
---------------
* ``htape_requests_total``         — counter, labelled by ``method`` and ``status``
* ``htape_request_duration_seconds`` — histogram (sum + count), labelled by ``path``
* ``htape_active_requests``        — gauge (in-flight requests)

Usage
-----
::

    from fastapi import FastAPI
    from htape.middleware import HTapeMetricsMiddleware, metrics_router

    app = FastAPI()
    app.add_middleware(HTapeMetricsMiddleware)
    app.include_router(metrics_router)          # exposes GET /metrics

"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Callable, DefaultDict, Dict, Tuple

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ---------------------------------------------------------------------------
# Thread-safe in-memory metric store
# ---------------------------------------------------------------------------

class _MetricStore:
    """Minimal, thread-safe store for counters, gauges, and histogram buckets."""

    def __init__(self) -> None:
        self._lock = Lock()
        # counter: label_tuple -> float
        self._counters: DefaultDict[Tuple, float] = defaultdict(float)
        # gauge: name -> float
        self._gauges: DefaultDict[str, float] = defaultdict(float)
        # histogram: label_tuple -> {"sum": float, "count": int}
        self._histograms: DefaultDict[Tuple, Dict[str, float]] = defaultdict(
            lambda: {"sum": 0.0, "count": 0}
        )

    def inc_counter(self, name: str, **labels: str) -> None:
        key = (name,) + tuple(sorted(labels.items()))
        with self._lock:
            self._counters[key] += 1

    def inc_gauge(self, name: str, delta: float = 1.0) -> None:
        with self._lock:
            self._gauges[name] += delta

    def observe_histogram(self, name: str, value: float, **labels: str) -> None:
        key = (name,) + tuple(sorted(labels.items()))
        with self._lock:
            self._histograms[key]["sum"] += value
            self._histograms[key]["count"] += 1

    # ------------------------------------------------------------------
    # Prometheus text-format serialiser
    # ------------------------------------------------------------------

    def render(self) -> str:
        lines: list[str] = []

        with self._lock:
            for key, value in self._counters.items():
                metric_name = key[0]
                label_str = _format_labels(dict(pair for pair in key[1:]))
                lines.append(f"# TYPE {metric_name} counter")
                lines.append(f"{metric_name}{label_str} {value}")

            for name, value in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")

            for key, data in self._histograms.items():
                metric_name = key[0]
                label_str = _format_labels(dict(pair for pair in key[1:]))
                lines.append(f"# TYPE {metric_name} histogram")
                lines.append(f"{metric_name}_sum{label_str} {data['sum']:.6f}")
                lines.append(f"{metric_name}_count{label_str} {data['count']}")

        return "\n".join(lines) + "\n"


def _format_labels(labels: Dict[str, str]) -> str:
    if not labels:
        return ""
    pairs = ", ".join(f'{k}="{v}"' for k, v in labels.items())
    return "{" + pairs + "}"


# Global singleton — scoped to the process, never shared across processes.
_store = _MetricStore()


# ---------------------------------------------------------------------------
# Starlette / FastAPI middleware
# ---------------------------------------------------------------------------

class HTapeMetricsMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records request metrics into the global store."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        _store.inc_gauge("htape_active_requests", 1.0)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            _store.inc_gauge("htape_active_requests", -1.0)
            raise

        elapsed = time.perf_counter() - start
        _store.inc_gauge("htape_active_requests", -1.0)
        _store.inc_counter(
            "htape_requests_total",
            method=request.method,
            status=str(response.status_code),
        )
        _store.observe_histogram(
            "htape_request_duration_seconds",
            elapsed,
            path=request.url.path,
        )
        return response


# ---------------------------------------------------------------------------
# /metrics router
# ---------------------------------------------------------------------------

metrics_router = APIRouter()


@metrics_router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def prometheus_metrics() -> str:
    """Expose accumulated metrics in Prometheus text exposition format."""
    return _store.render()
