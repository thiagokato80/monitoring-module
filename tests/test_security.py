# tests/test_security.py
import hashlib
import hmac
import time

import pytest
from monitoring_module.security import verify_hmac_with_secret, is_ip_allowed


SECRET = "test-secret-key"
APP_ID = "test-app"


def make_signature(app_id: str, secret: str, body: bytes = b"") -> dict:
    ts = str(int(time.time()))
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{app_id}:{ts}:{body_hash}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Monitoring-App-Id": app_id,
        "X-Monitoring-Timestamp": ts,
        "X-Monitoring-Signature": sig,
    }


def test_valid_signature():
    headers = make_signature(APP_ID, SECRET)
    assert verify_hmac_with_secret(
        app_id=headers["X-Monitoring-App-Id"],
        timestamp=headers["X-Monitoring-Timestamp"],
        signature=headers["X-Monitoring-Signature"],
        body=b"",
        secret=SECRET,
    ) is True


def test_invalid_signature():
    headers = make_signature(APP_ID, "wrong-secret")
    assert verify_hmac_with_secret(
        app_id=headers["X-Monitoring-App-Id"],
        timestamp=headers["X-Monitoring-Timestamp"],
        signature=headers["X-Monitoring-Signature"],
        body=b"",
        secret=SECRET,
    ) is False


def test_expired_timestamp():
    ts = str(int(time.time()) - 400)  # outside ±300s window
    body_hash = hashlib.sha256(b"").hexdigest()
    message = f"{APP_ID}:{ts}:{body_hash}"
    sig = hmac.new(SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    assert verify_hmac_with_secret(APP_ID, ts, sig, b"", SECRET) is False


def test_wrong_app_id():
    headers = make_signature("other-app", SECRET)
    assert verify_hmac_with_secret(
        APP_ID,
        headers["X-Monitoring-Timestamp"],
        headers["X-Monitoring-Signature"],
        b"",
        SECRET,
    ) is False


def test_ip_allowed():
    assert is_ip_allowed("1.2.3.4", ["1.2.3.4", "5.6.7.8"]) is True


def test_ip_blocked():
    assert is_ip_allowed("9.9.9.9", ["1.2.3.4"]) is False


def test_empty_allowlist_blocks_all():
    assert is_ip_allowed("1.2.3.4", []) is False
