"""Unit tests for FastAPI health check, startup behavior, and OpenAPI schema."""

import pytest
from fastapi.testclient import TestClient

from causalfidelity.api.dependencies import check_models_loaded
from causalfidelity.api.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_heavy_models_not_loaded_on_startup():
    """Verify that starting the FastAPI application does NOT load heavy neural models."""
    models_status = check_models_loaded()
    assert models_status["summac"] is False
    assert models_status["factcc"] is False
    assert models_status["bertscore"] is False


def test_health_endpoint_success(client):
    """Test GET /api/v1/health returns HTTP 200 and correct status payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["components_available"]["causal_extractor"] is True
    assert data["components_available"]["graph_builder"] is True
    assert "timestamp" in data


def test_openapi_schema_generation():
    """Test that OpenAPI schema is generated cleanly without error."""
    schema = app.openapi()
    assert schema["info"]["title"] == "CausalFidelityPlus API"
    assert schema["info"]["version"] == "1.0.0"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/causal/extract" in schema["paths"]
    assert "/api/v1/causal/graph" in schema["paths"]
    assert "/api/v1/perturbation/generate" in schema["paths"]
    assert "/api/v1/perturbation/validate" in schema["paths"]
    assert "/api/v1/evaluation/fidelity" in schema["paths"]
    assert "/api/v1/pipeline/analyze" in schema["paths"]
    assert "/api/v1/reports/{report_type}" in schema["paths"]
