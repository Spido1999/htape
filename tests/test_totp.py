"""Tests for htape.totp — RFC 6238 TOTP implementation."""

import time

from htape.totp import generate_totp, verify_totp


class TestGenerateTotp:
    def test_output_is_10_digits(self):
        token = generate_totp("testsecret")
        assert len(token) == 10
        assert token.isdigit()

    def test_deterministic_within_window(self):
        now = time.time()
        t1 = generate_totp("secret", at_time=now)
        t2 = generate_totp("secret", at_time=now + 1)   # same 30-s window
        assert t1 == t2

    def test_different_windows_differ(self):
        now = time.time()
        t1 = generate_totp("secret", at_time=now)
        t2 = generate_totp("secret", at_time=now + 60)  # 2 steps ahead
        assert t1 != t2

    def test_zero_padded(self):
        """Token must be zero-padded to the requested digit length."""
        # Use a fixed time that produces a small OTP to exercise zero-padding.
        token = generate_totp("pad_test", at_time=0.0, digits=10)
        assert len(token) == 10

    def test_custom_digit_length(self):
        token = generate_totp("secret", digits=6)
        assert len(token) == 6

    def test_hennge_shared_secret_format(self):
        """Token shared secret: userid + 'HENNGECHALLENGE004'."""
        token = generate_totp("ninja@example.comHENNGECHALLENGE004")
        assert len(token) == 10
        assert token.isdigit()


class TestVerifyTotp:
    def test_current_window_accepted(self):
        secret = "verify_test_secret"
        token = generate_totp(secret)
        assert verify_totp(secret, token) is True

    def test_wrong_token_rejected(self):
        assert verify_totp("somesecret", "0000000000") is False

    def test_adjacent_window_accepted(self):
        secret = "window_test"
        now = time.time()
        # Generate token for 1 step in the past; should still verify with window=1
        past_token = generate_totp(secret, at_time=now - 30)
        assert verify_totp(secret, past_token, window=1) is True

    def test_expired_window_rejected(self):
        secret = "expired_test"
        now = time.time()
        old_token = generate_totp(secret, at_time=now - 120)  # 4 steps ago
        assert verify_totp(secret, old_token, window=1) is False
