"""Tests for htape.engine — trampoline-based matrix processor."""

from htape.engine import process_matrix, _default_reducer, trampoline, _bounce


class TestDefaultReducer:
    def test_all_negative(self):
        assert _default_reducer([-1, -2, -3]) == 1 + 16 + 81  # 98

    def test_mixed_signs(self):
        # positives excluded; only -1 and -10 counted
        assert _default_reducer([3, -1, 1, 10]) == (-1) ** 4  # 1

    def test_all_positive(self):
        assert _default_reducer([1, 2, 3]) == 0

    def test_zero_included(self):
        assert _default_reducer([0]) == 0 ** 4  # 0

    def test_hennge_sample_case_1(self):
        assert _default_reducer([3, -1, 1, 10]) == 1

    def test_hennge_sample_case_2(self):
        assert _default_reducer([9, -5, -5, -10, 10]) == 625 + 625 + 10000  # 11250


class TestProcessMatrix:
    def test_hennge_sample(self):
        rows = [[3, -1, 1, 10], [9, -5, -5, -10, 10]]
        declared = [4, 5]
        assert process_matrix(rows, declared) == [1, 11250]

    def test_length_mismatch_returns_minus_one(self):
        rows = [[1, 2, 3]]
        declared = [5]          # declared 5 but only 3 provided
        assert process_matrix(rows, declared) == [-1]

    def test_empty_input(self):
        assert process_matrix([], []) == []

    def test_single_row_all_positive(self):
        assert process_matrix([[1, 2, 3]], [3]) == [0]

    def test_custom_reducer(self):
        rows = [[1, 2, 3, 4]]
        declared = [4]
        result = process_matrix(rows, declared, reducer=sum)
        assert result == [10]

    def test_deep_recursion_does_not_overflow(self):
        """100 rows — well within default recursion limit but proves trampoline path."""
        n = 100
        rows = [[-1]] * n
        declared = [1] * n
        results = process_matrix(rows, declared)
        assert results == [1] * n


class TestTrampoline:
    def test_basic_factorial(self):
        """Verify the trampoline drives a simple tail-recursive factorial."""

        @trampoline
        def _fact(n: int, acc: int = 1):
            if n <= 1:
                return acc
            return _bounce(_fact, n - 1, acc * n)

        assert _fact(10) == 3628800

    def test_large_input_no_recursion_error(self):
        """Trampoline must handle depths far beyond Python's default limit."""

        @trampoline
        def _countdown(n: int, acc: int = 0):
            if n == 0:
                return acc
            return _bounce(_countdown, n - 1, acc + 1)

        assert _countdown(10_000) == 10_000
