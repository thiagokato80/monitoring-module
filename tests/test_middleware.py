# tests/test_middleware.py
import time
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from monitoring_module.middleware import sanitize_path, sanitize_stack


def make_app_with_middleware(tier: int = 1, maintenance: bool = False):
    from monitoring_module.middleware import ErrorLoggingMiddleware, MaintenanceMiddleware
    from monitoring_module.config import MonitoringConfig

    cfg = MonitoringConfig(
        tier=tier, app_id="test", secret="sec", secret_hash="hash",
        hub_url="http://hub/ingest", allowed_ips=["1.2.3.4"],
        db_provider=None, database_url=None,
        maintenance_mode=maintenance,
        maintenance_message="Em manutenção",
    )
    app = FastAPI()

    @app.get("/api/data")
    def data():
        return {"data": "ok"}

    @app.get("/api/fail")
    def fail():
        raise ValueError("erro interno")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/monitoring/ping")
    def monitoring_ping():
        return {"pong": True}

    app.add_middleware(ErrorLoggingMiddleware, config=cfg)
    app.add_middleware(MaintenanceMiddleware, config=cfg)
    return app


# ── sanitize_path ────────────────────────────────────────────────────────────

def test_sanitize_path_replaces_uuid():
    path = "/api/v1/usuarios/f47ac10b-58cc-4372-a567-0e02b2c3d479"
    assert sanitize_path(path) == "/api/v1/usuarios/{id}"


def test_sanitize_path_replaces_numeric_id():
    assert sanitize_path("/api/v1/processos/12345/itens") == "/api/v1/processos/{id}/itens"


def test_sanitize_path_replaces_multiple_uuids():
    path = "/api/v1/aqs/f47ac10b-58cc-4372-a567-0e02b2c3d479/processos/a1b2c3d4-0000-0000-0000-000000000000"
    assert sanitize_path(path) == "/api/v1/aqs/{id}/processos/{id}"


def test_sanitize_path_leaves_short_numbers():
    # Números curtos (ex: versão /v1) não devem ser substituídos
    assert sanitize_path("/api/v1/health") == "/api/v1/health"


def test_sanitize_path_clean_path_unchanged():
    assert sanitize_path("/api/v1/processos") == "/api/v1/processos"


# ── sanitize_stack ───────────────────────────────────────────────────────────

def test_sanitize_stack_removes_sensitive_lines():
    stack = "File app.py line 10\n  cpf = '123.456.789-00'\nFile app.py line 20\n  result = ok"
    result = sanitize_stack(stack)
    assert "123.456.789-00" not in result
    assert "[linha removida" in result
    assert "result = ok" in result


def test_sanitize_stack_truncates_long_lines():
    long_line = "x" * 300
    result = sanitize_stack(long_line)
    assert len(result) <= 200


def test_sanitize_stack_limits_total_lines():
    stack = "\n".join([f"line {i}" for i in range(100)])
    result = sanitize_stack(stack)
    assert len(result.splitlines()) <= 30


def test_sanitize_stack_removes_email_line():
    stack = "raise ValueError(f'email {user.email} not found')"
    result = sanitize_stack(stack)
    assert "[linha removida" in result


def test_sanitize_stack_removes_password_line():
    stack = "auth failed for password=abc123"
    result = sanitize_stack(stack)
    assert "abc123" not in result


# ── middleware integration ───────────────────────────────────────────────────

def test_normal_request_passes():
    app = make_app_with_middleware()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/data")
    assert resp.status_code == 200


def test_maintenance_mode_blocks_api():
    app = make_app_with_middleware(maintenance=True)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/data")
    assert resp.status_code == 503
    assert "manutenção" in resp.json()["detail"].lower()


def test_maintenance_mode_allows_health():
    app = make_app_with_middleware(maintenance=True)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_maintenance_mode_allows_monitoring_paths():
    app = make_app_with_middleware(maintenance=True)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/monitoring/ping")
    assert resp.status_code == 200


def test_error_middleware_sends_webhook_on_5xx():
    app = make_app_with_middleware()
    client = TestClient(app, raise_server_exceptions=False)

    with patch("monitoring_module.middleware.send_event") as mock_send:
        mock_send.return_value = None
        resp = client.get("/api/fail")
        assert resp.status_code == 500
        # send_event runs in a background thread — wait briefly for it to complete
        deadline = time.monotonic() + 2.0
        while not mock_send.called and time.monotonic() < deadline:
            time.sleep(0.01)
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["event_type"] == "error"
        assert "body" not in str(call_args)
        assert "stack_trace" in call_args["payload"]


def test_error_middleware_sanitizes_path_in_webhook():
    """UUID no path deve ser substituído por {id} antes de sair para o hub."""
    from monitoring_module.middleware import ErrorLoggingMiddleware
    from monitoring_module.config import MonitoringConfig

    cfg = MonitoringConfig(
        tier=1, app_id="test", secret="sec", secret_hash="hash",
        hub_url="http://hub/ingest", allowed_ips=[],
        db_provider=None, database_url=None,
        maintenance_mode=False, maintenance_message="",
    )
    app = FastAPI()

    @app.get("/api/v1/usuarios/{user_id}/dados")
    def user_data(user_id: str):
        raise ValueError("erro")

    app.add_middleware(ErrorLoggingMiddleware, config=cfg)
    client = TestClient(app, raise_server_exceptions=False)

    with patch("monitoring_module.middleware.send_event") as mock_send:
        mock_send.return_value = None
        client.get("/api/v1/usuarios/f47ac10b-58cc-4372-a567-0e02b2c3d479/dados")
        deadline = time.monotonic() + 2.0
        while not mock_send.called and time.monotonic() < deadline:
            time.sleep(0.01)
        call_args = mock_send.call_args[0][0]
        path_sent = call_args["payload"]["path"]
        assert "f47ac10b" not in path_sent
        assert "{id}" in path_sent
