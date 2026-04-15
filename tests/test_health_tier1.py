# tests/test_health_tier1.py
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from monitoring_module.routes.health import make_health_router
from monitoring_module.config import MonitoringConfig


def make_config(tier=1):
    return MonitoringConfig(
        tier=tier, app_id="test-app", secret="sec", secret_hash="h",
        hub_url="", allowed_ips=[], db_provider=None, database_url=None,
        maintenance_mode=False, maintenance_message="",
    )


def make_test_app(tier=1):
    cfg = make_config(tier)
    app = FastAPI()
    app.include_router(make_health_router(cfg))
    return TestClient(app)


def test_health_returns_ok():
    client = make_test_app()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["tier"] == 1
    assert "uptime_seconds" in data
    assert "version" in data


def test_health_uptime_increases():
    client = make_test_app()
    r1 = client.get("/health").json()["uptime_seconds"]
    time.sleep(0.1)
    r2 = client.get("/health").json()["uptime_seconds"]
    assert r2 >= r1


def test_ping_requires_hmac():
    """POST /monitoring/ping sem assinatura deve retornar 403."""
    from monitoring_module.routes.monitoring import make_monitoring_router
    cfg = make_config()
    app = FastAPI()
    app.include_router(make_monitoring_router(cfg))
    client = TestClient(app)
    resp = client.post("/monitoring/ping")
    assert resp.status_code == 403
