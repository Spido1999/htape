"""HTAPE — High-Throughput Algorithmic Processing Engine
========================================================
Public package surface.
"""

from htape.engine import process_matrix, trampoline
from htape.totp import generate_totp, verify_totp
from htape.middleware import HTapeMetricsMiddleware, metrics_router

__version__ = "1.0.0"
__author__ = "Akash Shinde"
__license__ = "MIT"

__all__ = [
    "process_matrix",
    "trampoline",
    "generate_totp",
    "verify_totp",
    "HTapeMetricsMiddleware",
    "metrics_router",
]
