"""End-to-end API tests using FastAPI TestClient."""
from fastapi.testclient import TestClient

from theme2.src.api import app

client = TestClient(app)


def test_health_endpoint():
    """Gate G2: GET /health must return 200 with {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_troubleshoot_endpoint_success():
    payload = {
        "query": "My Galaxy phone screen flickers and is very dark",
        "siis_response": {
            "title": "Screen flickering troubleshooting",
            "content": "## Display settings\nNavigate to Settings > Display and adjust Adaptive brightness.\n## Force Restart\nPress Volume Down and Power buttons simultaneously."
        }
    }
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "contexts" in data
    assert len(data["contexts"]) > 0
    assert "X-Cache-Status" in response.headers
    assert "X-Processing-Time-Ms" in response.headers
    assert float(response.headers["X-Processing-Time-Ms"]) >= 0


def test_troubleshoot_endpoint_validation_errors():
    # Empty query should return 422
    response1 = client.post("/v1/troubleshoot", json={"query": "", "siis_response": {"title": "A", "content": "B"}})
    assert response1.status_code == 422

    # Empty content should return 422
    response2 = client.post("/v1/troubleshoot", json={"query": "test", "siis_response": {"title": "A", "content": ""}})
    assert response2.status_code == 422


def test_preview_endpoint():
    payload = {
        "query": "My Galaxy phone screen is blank",
        "siis_response": {
            "title": "Black screen issue",
            "content": "## Check Display\nInspect the screen for cracks or damage."
        },
        "facts": {
            "screen_visible": False,
            "touch_working": False
        }
    }
    response = client.post("/v1/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "normalized" in data
    assert "trace" in data
    assert data["normalized"]["facts"]["screen_visible"] is False
    assert "preview_projection" in data["trace"]["stage_timings_ms"]
    repeated = client.post("/v1/preview", json=payload)
    assert repeated.status_code == 200
    assert repeated.json()["trace"]["cache_status"] == "exact_hit"
    assert repeated.json()["trace"]["stages"]["normalization"] == "executed for preview"


def test_development_sample_is_explicitly_labeled_synthetic():
    response = client.get("/api/development-sample")
    assert response.status_code == 200
    assert response.json()["provenance"] == "team-authored synthetic development fixture"
    assert "inner display" in response.json()["content"].lower()
