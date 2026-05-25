"""htape.totp
============
Native RFC 6238 TOTP implementation using **only** Python standard library
modules (``hmac``, ``hashlib``, ``struct``, ``time``).  No external
dependencies required.

Supports configurable hash algorithms, time steps, and token lengths.
Defaults match the HENNGE challenge specification:

* Hash   : HMAC-SHA-512
* Step X : 30 seconds
* T0     : 0 (Unix epoch)
* Digits : 10

References
----------
* RFC 4226 — HOTP: An HMAC-Based One-Time Password Algorithm
* RFC 6238 — TOTP: Time-Based One-Time Password Algorithm (+ errata)

Example
-------
>>> from htape.totp import generate_totp
>>> token = generate_totp("user@example.comHENNGECHALLENGE004")
>>> len(token)
10
>>> token.isdigit()
True
"""

from __future__ import annotations

import hashlib
import hmac
import struct
import time
from typing import Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_totp(
    secret: str,
    *,
    at_time: Optional[float] = None,
    digits: int = 10,
    step: int = 30,
    t0: int = 0,
    algorithm: str = "sha512",
) -> str:
    """Generate a zero-padded TOTP token (RFC 6238).

    Parameters
    ----------
    secret:
        Shared secret as a plain ASCII string.  The raw byte representation is
        used directly as the HMAC key (no base-32 decoding).
    at_time:
        Unix timestamp to evaluate; defaults to the current wall-clock time.
    digits:
        Number of decimal digits in the output token (default: 10).
    step:
        Time step window in seconds (default: 30).
    t0:
        Unix time of the initial counter (default: 0, i.e. the epoch).
    algorithm:
        HMAC hash function name accepted by :mod:`hashlib`
        (default: ``"sha512"``).

    Returns
    -------
    str
        Zero-padded *digits*-digit OTP string.
    """
    unix_time: float = at_time if at_time is not None else time.time()

    # T = floor((Unix_time - T0) / X)   (RFC 6238 §4 + errata)
    t_counter: int = int(unix_time - t0) // step
    t_bytes: bytes = struct.pack(">Q", t_counter)          # 8-byte big-endian

    digest_fn = getattr(hashlib, algorithm, None)
    if digest_fn is None:
        raise ValueError(f"Unsupported hash algorithm: {algorithm!r}")

    hmac_digest: bytes = hmac.new(
        secret.encode("ascii"),
        t_bytes,
        digest_fn,
    ).digest()

    # Dynamic truncation — RFC 4226 §5.3
    offset: int = hmac_digest[-1] & 0x0F
    p: int = struct.unpack(">I", hmac_digest[offset: offset + 4])[0] & 0x7FFF_FFFF

    otp: int = p % (10 ** digits)
    return str(otp).zfill(digits)


def verify_totp(
    secret: str,
    token: str,
    *,
    window: int = 1,
    **kwargs,
) -> bool:
    """Verify a TOTP token within ±*window* time steps (clock-skew tolerance).

    Parameters
    ----------
    secret:
        Shared secret (same as used for generation).
    token:
        The token string submitted by the client.
    window:
        Number of adjacent time windows to check on each side (default: 1).
    **kwargs:
        Forwarded to :func:`generate_totp` (``digits``, ``step``, etc.).

    Returns
    -------
    bool
        ``True`` if the token matches any window within the tolerance range.
    """
    now: float = time.time()
    step: int = kwargs.get("step", 30)

    return any(
        hmac.compare_digest(
            generate_totp(secret, at_time=now + offset * step, **kwargs),
            token,
        )
        for offset in range(-window, window + 1)
    )
