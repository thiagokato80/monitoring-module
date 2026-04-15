# tests/test_core.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_monitoring_module_registers_health(monkeypatch):
    monkeypatch.setenv("MONITORING_TIER", "1")
    monkeypatch.setenv("MONITORING_APP_ID", "my-app")
    monkeypatch.setenv("MONITORING_SECRET", "my-secret")
    monkeypatch.setenv("MONITORING_HUB_URL", "")
    monkeypatch.setenv("MONITORING_ALLOWED_IPS", "")

    from monitoring_module import MonitoringModule
    app = FastAPI()
    MonitoringModule(app)

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["app_id"] == "my-app"


def test_monitoring_module_registers_ping(monkeypatch):
    monkeypatch.setenv("MONITORING_TIER", "1")
    monkeypatch.setenv("MONITORING_APP_ID", "my-app")
    monkeypatch.setenv("MONITORING_SECRET", "my-secret")
    monkeypatch.setenv("MONITORING_HUB_URL", "")
    monkeypatch.setenv("MONITORING_ALLOWED_IPS", "127.0.0.1")

    from monitoring_module import MonitoringModule
    app = FastAPI()
    MonitoringModule(app)

    client = TestClient(app)
    # no HMAC → 403
    resp = client.post("/monitoring/ping")
    assert resp.status_code == 403
