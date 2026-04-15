# tests/test_middleware.py
import time
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


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
        assert "body" not in str(call_args)   # never sends body
        assert "stack_trace" in call_args["payload"]
