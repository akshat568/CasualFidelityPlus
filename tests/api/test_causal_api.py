"""Unit tests for causal extraction and graph API routes."""

import pytest
from fastapi.testclient import TestClient
from causalfidelity.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_extract_causal_relations_success(client):
    """Test POST /api/v1/causal/extract with valid text containing causal connectives."""
    payload = {
        "text": "The heavy rain caused severe flooding because the dam collapsed.",
        "document_id": "doc_test_001",
    }
    response = client.post("/api/v1/causal/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc_test_001"
    assert data["relations_count"] >= 1
    rel = data["relations"][0]
    assert "cause" in rel
    assert "effect" in rel
    assert "connective" in rel


def test_extract_causal_relations_empty_text(client):
    """Test POST /api/v1/causal/extract with empty text returns HTTP 400 or 422."""
    payload = {"text": "   ", "document_id": "doc_test"}
    response = client.post("/api/v1/causal/extract", json=payload)
    assert response.status_code in (400, 422)


def test_build_causal_graph_from_text(client):
    """Test POST /api/v1/causal/graph constructing DiGraph and Mermaid representation from text."""
    payload = {
        "document_id": "doc_graph_001",
        "text": "The flood occurred because of heavy rain.",
    }
    response = client.post("/api/v1/causal/graph", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc_graph_001"
    assert "nodes" in data
    assert "edges" in data
    assert data["is_dag"] is True
    assert "graph TD" in data["mermaid_code"]


def test_build_causal_graph_from_relations_list(client):
    """Test POST /api/v1/causal/graph with pre-extracted relations list."""
    payload = {
        "document_id": "doc_graph_002",
        "relations": [
            {
                "relation_id": "r1",
                "cause": "storm",
                "effect": "blackout",
                "connective": "caused",
                "confidence": 0.9,
            }
        ],
    }
    response = client.post("/api/v1/causal/graph", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["node_count"] == 2
    assert data["edge_count"] == 1
