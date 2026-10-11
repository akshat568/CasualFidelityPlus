"""Unit tests for perturbation generation and quality validation API routes."""

import pytest
from fastapi.testclient import TestClient
from causalfidelity.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_generate_perturbations_success(client):
    """Test POST /api/v1/perturbation/generate with summary text containing causal connective."""
    payload = {
        "document_id": "doc_pert_001",
        "summary_id": "sum_pert_001",
        "summary_text": "The engine failure caused the crash.",
        "selected_strategies": ["WEAKENED", "DROPPED"],
    }
    response = client.post("/api/v1/perturbation/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc_pert_001"
    assert "perturbations" in data


def test_generate_perturbations_unsupported_strategy(client):
    """Test POST /api/v1/perturbation/generate with invalid strategy returns HTTP 400."""
    payload = {
        "summary_text": "The engine failure caused the crash.",
        "selected_strategies": ["INVALID_STRATEGY_FOO"],
    }
    response = client.post("/api/v1/perturbation/generate", json=payload)
    assert response.status_code == 400
    assert "Unsupported perturbation strategy" in response.json()["message"]


def test_validate_perturbations_success(client):
    """Test POST /api/v1/perturbation/validate with perturbation records."""
    payload = {
        "records": [
            {
                "perturbation_id": "p_test_001",
                "document_id": "doc_001",
                "summary_id": "sum_001",
                "strategy": "WEAKENED",
                "original_text": "Heavy rain caused flooding.",
                "perturbed_text": "Heavy rain was associated with flooding.",
                "target_relation": {
                    "relation_id": "r1",
                    "cause": "Heavy rain",
                    "effect": "flooding",
                    "connective": "caused",
                },
            }
        ]
    }
    response = client.post("/api/v1/perturbation/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_examined"] == 1
    assert "results" in data
    assert data["results"][0]["perturbation_id"] == "p_test_001"
    assert "is_valid" in data["results"][0]


def test_validate_perturbations_empty_list(client):
    """Test POST /api/v1/perturbation/validate with empty list returns HTTP 400 or 422."""
    payload = {"records": []}
    response = client.post("/api/v1/perturbation/validate", json=payload)
    assert response.status_code in (400, 422)
