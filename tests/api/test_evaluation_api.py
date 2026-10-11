"""Unit tests for fidelity evaluation API route."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from causalfidelity.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_fidelity_evaluation_ablated_metrics(client):
    """Test POST /api/v1/evaluation/fidelity with disabled/ablated metric settings."""
    payload = {
        "source_text": "Heavy rain caused severe flooding.",
        "original_summary": "Heavy rain caused flooding.",
        "perturbed_summary": "Heavy rain was associated with flooding.",
        "enabled_metrics": [],  # All metrics disabled/ablated
    }
    response = client.post("/api/v1/evaluation/fidelity", json=payload)
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]
    assert metrics["summac"]["status"] == "ABLATED"
    assert metrics["factcc"]["status"] == "ABLATED"
    assert metrics["bertscore"]["status"] == "ABLATED"


def test_fidelity_evaluation_unsupported_metric(client):
    """Test POST /api/v1/evaluation/fidelity with unsupported metric name."""
    payload = {
        "source_text": "Source text...",
        "original_summary": "Original...",
        "perturbed_summary": "Perturbed...",
        "enabled_metrics": ["invalid_metric_name"],
    }
    response = client.post("/api/v1/evaluation/fidelity", json=payload)
    assert response.status_code == 400
    assert "Unsupported metric names requested" in response.json()["message"]


@patch("causalfidelity.api.routes.evaluation.get_summac_metric")
@patch("causalfidelity.api.routes.evaluation.get_factcc_metric")
@patch("causalfidelity.api.routes.evaluation.get_bertscore_metric")
def test_fidelity_evaluation_mocked_metrics(mock_bs, mock_fc, mock_sm, client):
    """Test POST /api/v1/evaluation/fidelity with mocked neural metrics."""
    # Mock SummaC
    m_sm = MagicMock()
    m_sm.score.side_effect = lambda src, sum_t: 0.85 if "caused" in sum_t else 0.70
    m_sm.get_metadata.return_value = {"metric_version": "summac-mock"}
    mock_sm.return_value = m_sm

    # Mock FactCC
    m_fc = MagicMock()
    m_fc.score.side_effect = lambda src, sum_t: 0.90 if "caused" in sum_t else 0.40
    m_fc.get_metadata.return_value = {"metric_version": "factcc-mock"}
    mock_fc.return_value = m_fc

    # Mock BERTScore
    m_bs = MagicMock()
    m_bs.score_detailed.return_value = {
        "bertscore_precision": 0.95,
        "bertscore_recall": 0.96,
        "bertscore_f1": 0.955,
        "similarity_loss": 0.045,
    }
    m_bs.get_metadata.return_value = {"metric_version": "bertscore-mock"}
    mock_bs.return_value = m_bs

    payload = {
        "source_text": "Heavy rain caused severe flooding.",
        "original_summary": "Heavy rain caused flooding.",
        "perturbed_summary": "Heavy rain was associated with flooding.",
        "enabled_metrics": ["summac", "factcc", "bertscore"],
    }

    response = client.post("/api/v1/evaluation/fidelity", json=payload)
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]

    assert metrics["summac"]["status"] == "SUCCESS"
    assert metrics["summac"]["score_delta"] == 0.15

    assert metrics["factcc"]["status"] == "SUCCESS"
    assert metrics["factcc"]["score_delta"] == 0.50

    assert metrics["bertscore"]["status"] == "SUCCESS"
    assert metrics["bertscore"]["bertscore_f1"] == 0.955
    assert metrics["bertscore"]["similarity_loss"] == 0.045
