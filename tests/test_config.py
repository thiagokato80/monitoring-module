# tests/test_config.py
import pytest
from monitoring_module.config import MonitoringConfig


def test_from_env_tier1(monkeypatch):
    monkeypatch.setenv("MONITORING_TIER", "1")
    monkeypatch.setenv("MONITORING_APP_ID", "test-app")
    monkeypatch.setenv("MONITORING_SECRET_HASH", "abc123")
    monkeypatch.setenv("MONITORING_HUB_URL", "http://hub/ingest")
    monkeypatch.setenv("MONITORING_ALLOWED_IPS", "1.2.3.4,5.6.7.8")

    cfg = MonitoringConfig.from_env()

    assert cfg.tier == 1
    assert cfg.app_id == "test-app"
    assert cfg.allowed_ips == ["1.2.3.4", "5.6.7.8"]
    assert cfg.db_provider is None


def test_from_env_missing_app_id(monkeypatch):
    monkeypatch.setenv("MONITORING_TIER", "1")
    monkeypatch.delenv("MONITORING_APP_ID", raising=False)

    with pytest.raises(ValueError, match="MONITORING_APP_ID"):
        MonitoringConfig.from_env()


def test_from_env_invalid_tier(monkeypatch):
    monkeypatch.setenv("MONITORING_TIER", "9")
    monkeypatch.setenv("MONITORING_APP_ID", "test-app")

    with pytest.raises(ValueError, match="MONITORING_TIER"):
        MonitoringConfig.from_env()


def test_maintenance_mode_default_false(monkeypatch):
    monkeypatch.setenv("MONITORING_TIER", "1")
    monkeypatch.setenv("MONITORING_APP_ID", "test-app")
    monkeypatch.delenv("MAINTENANCE_MODE", raising=False)

    cfg = MonitoringConfig.from_env()
    assert cfg.maintenance_mode is False
