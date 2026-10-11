"""Unit tests for research report and artifact retrieval API routes."""

import pytest
from fastapi.testclient import TestClient
from causalfidelity.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize(
    "report_type, expected_content_type",
    [
        ("phase13_report", "text/markdown"),
        ("phase13_summary", "application/json"),
        ("ablation_manifest", "application/json"),
        ("step4_analysis", "text/markdown"),
    ],
)
def test_get_report_success(client, report_type, expected_content_type):
    """Test GET /api/v1/reports/{report_type} for all approved report allowlist items."""
    response = client.get(f"/api/v1/reports/{report_type}")
    assert response.status_code == 200
    data = response.json()
    assert data["report_type"] == report_type
    assert data["content_type"] == expected_content_type
    assert "data" in data
    assert data["data"] is not None


def test_get_report_unsupported_type(client):
    """Test GET /api/v1/reports/{report_type} with unsupported type returns HTTP 400."""
    response = client.get("/api/v1/reports/unsupported_foo_report")
    assert response.status_code == 400
    assert "Unsupported report type" in response.json()["message"]


def test_get_report_path_traversal_protection(client):
    """Test path traversal protection on /api/v1/reports/ endpoint."""
    response = client.get("/api/v1/reports/..%2F..%2Fconfigs%2Fbase.yaml")
    assert response.status_code in (400, 404)
