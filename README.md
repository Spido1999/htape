# HTAPE — High-Throughput Algorithmic Processing Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/Spido1999/htape/actions/workflows/ci.yml/badge.svg)](https://github.com/Spido1999/htape/actions)

A dependency-free Python microservice library for processing complex integer matrices under **zero-loop, low-memory conditions** using **trampoline-based tail-recursion** — eliminates `RecursionError` at scale without native TCO support.

---

## Features

| Module | What it does |
|---|---|
| `htape.engine` | Trampoline-driven tail-recursive matrix processor; no `for`/`while` loops, no globals |
| `htape.totp` | Native RFC 6238 TOTP using only `hmac` + `hashlib`; configurable hash, step, digits |
| `htape.middleware` | Plug-and-play FastAPI ASGI middleware exposing a Prometheus-compatible `/metrics` endpoint |

---

## Installation

```bash
# Core engine + TOTP (zero runtime dependencies)
pip install htape

# With FastAPI middleware support
pip install "htape[middleware]"
```

---

## Quick Start

### Integer matrix processing

```python
from htape.engine import process_matrix

rows     = [[3, -1, 1, 10], [9, -5, -5, -10, 10]]
declared = [4, 5]

# Default reducer: sum of n**4 for every non-positive n
results = process_matrix(rows, declared)
print(results)   # [1, 11250]
```

Length mismatch between a row and its declared count yields `-1` for that row:

```python
process_matrix([[1, 2, 3]], declared_lengths=[5])  # [-1]
```

### Custom reducer

```python
process_matrix(rows, declared, reducer=sum)  # sum of all values per row
```

### Trampoline primitive (standalone)

```python
from htape.engine import trampoline, _bounce

@trampoline
def countdown(n: int, acc: int = 0):
    if n == 0:
        return acc
    return _bounce(countdown, n - 1, acc + 1)

countdown(100_000)   # no RecursionError
```

### RFC 6238 TOTP

```python
from htape.totp import generate_totp, verify_totp

# 10-digit HMAC-SHA-512 token (HENNGE challenge defaults)
secret = "user@example.comHENNGECHALLENGE004"
token  = generate_totp(secret)                    # e.g. "1595942560"

# Verify with ±1 window clock-skew tolerance
verify_totp(secret, token, window=1)              # True
```

### FastAPI metrics middleware

```python
from fastapi import FastAPI
from htape.middleware import HTapeMetricsMiddleware, metrics_router

app = FastAPI()
app.add_middleware(HTapeMetricsMiddleware)
app.include_router(metrics_router)   # GET /metrics → Prometheus text format
```

Metrics exposed:

```
# TYPE htape_requests_total counter
htape_requests_total{method="GET", status="200"} 42.0
# TYPE htape_request_duration_seconds histogram
htape_request_duration_seconds_sum{path="/"} 0.031200
htape_request_duration_seconds_count{path="/"} 42
# TYPE htape_active_requests gauge
htape_active_requests 1.0
```

---

## Design principles

- **No external runtime dependencies** in the core engine — minimises supply-chain risk in security-sensitive deployments.
- **No `for`/`while` loops** — all iteration is expressed as tail recursion driven through the trampoline; safe for arbitrary depth without native TCO.
- **No global variables** — every function is a pure transformation; trivial to test and reason about.
- **Standard library only** for engine and TOTP modules (`hmac`, `hashlib`, `struct`, `functools`).

---

## Running tests

```bash
pip install "htape[dev]"
pytest -v
```

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss the change. All PRs must include tests and pass `pytest` cleanly.

---

## License

[MIT](LICENSE) © Akash Shinde
