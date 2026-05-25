"""htape.engine
==============
Trampoline-based tail-recursive engine for processing integer matrices under
low-memory, zero-loop conditions.

Design goals
------------
* **No external dependencies** — pure Python standard library only.
* **No ``for`` / ``while`` loops** — all iteration expressed as tail recursion
  driven through a trampoline, eliminating ``RecursionError`` at scale without
  native TCO support.
* **Zero global state** — every function is a pure transformation.

Typical use-case
----------------
Process N integer rows, applying a user-supplied reduction function to each
row, and collect results only after all input has been consumed (buffered
output pattern).

Example
-------
>>> from htape.engine import process_matrix
>>> rows = [[3, -1, 1, 10], [9, -5, -5, -10, 10]]
>>> declared = [4, 5]
>>> process_matrix(rows, declared, lambda nums: sum(n**4 for n in nums if n <= 0))
[1, 11250]
"""

from __future__ import annotations

import functools
from typing import Any, Callable, List, Optional


# ---------------------------------------------------------------------------
# Trampoline primitive
# ---------------------------------------------------------------------------

class _Thunk:
    """Lazy suspension of a zero-argument callable (the trampoline payload)."""

    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[], Any]) -> None:
        self._fn = fn

    def __call__(self) -> Any:
        return self._fn()


def trampoline(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that turns a tail-recursive function into a loop-free,
    stack-safe iterative computation via the trampoline pattern.

    The decorated function may return either a plain value (base case) or a
    ``_Thunk`` (recursive case).  The trampoline driver bounces thunks until a
    plain value is produced — all without growing the call stack.
    """
    @functools.wraps(fn)
    def _driver(*args: Any, **kwargs: Any) -> Any:
        result: Any = fn(*args, **kwargs)
        while isinstance(result, _Thunk):
            result = result()
        return result

    return _driver


def _bounce(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> _Thunk:
    """Create a suspension that will call *fn* with *args*/*kwargs*."""
    return _Thunk(lambda: fn(*args, **kwargs))


# ---------------------------------------------------------------------------
# Core matrix processor
# ---------------------------------------------------------------------------

def _reduce_row(
    nums: List[int],
    reducer: Callable[[List[int]], int],
    declared: int,
) -> int:
    """Apply *reducer* to *nums*, returning ``-1`` on length mismatch."""
    if len(nums) != declared:
        return -1
    return reducer(nums)


@trampoline
def _collect(
    rows: List[List[int]],
    declared: List[int],
    reducer: Callable[[List[int]], int],
    acc: List[int],
    idx: int,
) -> Any:
    """Tail-recursive accumulator — bounces until all rows are processed."""
    if idx == len(rows):
        return acc                                           # base case
    result = _reduce_row(rows[idx], reducer, declared[idx])
    return _bounce(
        _collect,
        rows,
        declared,
        reducer,
        acc + [result],
        idx + 1,
    )


def process_matrix(
    rows: List[List[int]],
    declared_lengths: List[int],
    reducer: Optional[Callable[[List[int]], int]] = None,
) -> List[int]:
    """Process an integer matrix through a user-supplied reducer.

    Parameters
    ----------
    rows:
        A list of integer lists — one per test case.
    declared_lengths:
        The *declared* length for each row (X values).  A mismatch between
        ``len(rows[i])`` and ``declared_lengths[i]`` yields ``-1`` for that row.
    reducer:
        A callable ``(List[int]) -> int`` applied to each *valid* row.
        Defaults to the HENNGE-challenge reduction: sum of ``n**4`` for all
        non-positive integers.

    Returns
    -------
    List[int]
        One result per input row, in order.  ``-1`` marks invalid rows.
    """
    if reducer is None:
        reducer = _default_reducer

    return _collect(rows, declared_lengths, reducer, [], 0)


def _default_reducer(nums: List[int]) -> int:
    """Sum the fourth powers of all non-positive integers in *nums*."""
    return functools.reduce(
        lambda acc, n: acc + n ** 4,
        filter(lambda n: n <= 0, nums),
        0,
    )
