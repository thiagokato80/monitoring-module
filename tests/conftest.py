# tests/conftest.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def base_app():
    """App FastAPI mínima para testes."""
    app = FastAPI()

    @app.get("/api/test")
    def test_endpoint():
        return {"ok": True}

    return app


@pytest.fixture
def test_client(base_app):
    return TestClient(base_app)
