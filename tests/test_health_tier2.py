# tests/test_health_tier2.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from monitoring_module.routes.health import make_health_router
from monitoring_module.config import MonitoringConfig


def make_config_tier2():
    return MonitoringConfig(
        tier=2, app_id="test-app", secret="sec", secret_hash="h",
        hub_url="", allowed_ips=[], db_provider="supabase",
        database_url="postgresql://localhost/test",
        maintenance_mode=False, maintenance_message="",
    )


def test_health_tier2_includes_db_status():
    cfg = make_config_tier2()

    with patch("monitoring_module.routes.health.get_db_adapter") as mock_adapter_fn:
        mock_db = MagicMock()
        mock_db.check.return_value = {"status": "ok", "latency_ms": 12}
        mock_adapter_fn.return_value = mock_db

        app = FastAPI()
        app.include_router(make_health_router(cfg))
        client = TestClient(app)

        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == 2
        assert data["db_status"] == "ok"
        assert data["db_latency_ms"] == 12


def test_health_tier2_db_down():
    cfg = make_config_tier2()

    with patch("monitoring_module.routes.health.get_db_adapter") as mock_adapter_fn:
        mock_db = MagicMock()
        mock_db.check.return_value = {"status": "error", "latency_ms": None}
        mock_adapter_fn.return_value = mock_db

        app = FastAPI()
        app.include_router(make_health_router(cfg))
        client = TestClient(app)

        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["db_status"] == "error"
