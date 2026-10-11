"""Unit tests for interactive end-to-end pipeline analysis API route."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from causalfidelity.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("causalfidelity.api.routes.evaluation.get_summac_metric")
@patch("causalfidelity.api.routes.evaluation.get_factcc_metric")
@patch("causalfidelity.api.routes.evaluation.get_bertscore_metric")
def test_pipeline_analyze_success(mock_bs, mock_fc, mock_sm, client):
    """Test POST /api/v1/pipeline/analyze end-to-end processing with mocked metrics."""
    m_sm = MagicMock()
    m_sm.score.return_value = 0.8
    mock_sm.return_value = m_sm

    m_fc = MagicMock()
    m_fc.score.return_value = 0.9
    mock_fc.return_value = m_fc

    m_bs = MagicMock()
    m_bs.score_detailed.return_value = {
        "bertscore_precision": 0.95,
        "bertscore_recall": 0.95,
        "bertscore_f1": 0.95,
        "similarity_loss": 0.05,
    }
    mock_bs.return_value = m_bs

    payload = {
        "source_text": "The heavy rainfall caused severe flooding in the valley because the dam broke.",
        "summary_text": "Heavy rainfall caused severe flooding in the valley.",
        "document_id": "doc_interactive_test",
        "selected_strategies": ["WEAKENED"],
        "enabled_metrics": ["summac"],
    }

    response = client.post("/api/v1/pipeline/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc_interactive_test"
    assert data["status"] == "SUCCESS"
    assert "extraction" in data
    assert "graph" in data
    assert "perturbations" in data
    assert "validation" in data
    assert "fidelity" in data


def test_pipeline_analyze_empty_input_error(client):
    """Test POST /api/v1/pipeline/analyze with empty source or summary text."""
    payload = {
        "source_text": "   ",
        "summary_text": "Summary text",
    }
    response = client.post("/api/v1/pipeline/analyze", json=payload)
    assert response.status_code in (400, 422)
