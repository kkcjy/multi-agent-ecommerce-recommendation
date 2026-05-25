import importlib
import os
import sys

from fastapi.testclient import TestClient


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _build_client():
    os.environ["ECOM_ADMIN_API_KEY"] = "test-admin-key"
    os.environ["ECOM_RATE_LIMIT_ENABLED"] = "true"
    os.environ["ECOM_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    os.environ["ECOM_RATE_LIMIT_RECOMMEND_PER_WINDOW"] = "2"
    os.environ["ECOM_RATE_LIMIT_GRAPH_PER_WINDOW"] = "2"
    os.environ["ECOM_CORS_ALLOW_ORIGINS"] = "http://localhost:8866"

    import config.settings as settings_mod
    importlib.reload(settings_mod)
    settings_mod.get_settings.cache_clear()

    import main as app_main
    app_main = importlib.reload(app_main)
    return TestClient(app_main.app)


def test_admin_api_requires_key():
    client = _build_client()
    response = client.get("/api/v1/experiments")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


def test_recommend_rate_limit_hit():
    client = _build_client()
    payload = {"user_id": "rate_user", "scene": "homepage", "num_items": 2}

    r1 = client.post("/api/v1/recommend", json=payload)
    r2 = client.post("/api/v1/recommend", json=payload)
    r3 = client.post("/api/v1/recommend", json=payload)

    assert r1.status_code in (200, 503)
    assert r2.status_code in (200, 503)
    assert r3.status_code == 429


def test_invalid_request_rejected():
    client = _build_client()

    invalid_num_items = client.post(
        "/api/v1/recommend",
        json={"user_id": "u1", "scene": "homepage", "num_items": 999},
    )
    assert invalid_num_items.status_code == 422

    huge_context = {"k": "x" * 5000}
    invalid_context = client.post(
        "/api/v1/recommend",
        json={"user_id": "u1", "scene": "homepage", "num_items": 5, "context": huge_context},
    )
    assert invalid_context.status_code == 422
