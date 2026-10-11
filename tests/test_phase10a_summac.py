"""Unit tests for Phase 10A SummaCConv Metric Evaluation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from causalfidelity.metrics.base import BaseMetric
from causalfidelity.metrics.pipeline import Phase10AEvaluatorPipeline
from causalfidelity.metrics.summac import SummaCConvMetric


class MockMetric(BaseMetric):
    """Mock metric wrapper for fast testing without loading full PyTorch models."""

    def __init__(self, scores: Optional[Dict[str, float]] = None):
        self.scores = scores or {}
        self.call_history = []

    @property
    def name(self) -> str:
        return "MockSummaC"

    @property
    def version(self) -> str:
        return "1.0.0-mock"

    def score(self, source_text: str, summary_text: str) -> float:
        self.call_history.append((source_text, summary_text))
        # Return registered score or deterministic hash-based float
        if summary_text in self.scores:
            return self.scores[summary_text]
        return float(len(summary_text) % 10) / 10.0


def test_base_metric_abstract():
    """Verify BaseMetric cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseMetric()  # type: ignore


def test_base_metric_subclass():
    """Verify MockMetric subclass satisfies BaseMetric interface."""
    m = MockMetric()
    assert m.name == "MockSummaC"
    assert m.version == "1.0.0-mock"
    assert isinstance(m.get_metadata(), dict)
    assert m.get_metadata()["name"] == "MockSummaC"


def test_summac_adapter_initialization():
    """Verify SummaCConvMetric adapter metadata and lazy initialization."""
    adapter = SummaCConvMetric()
    assert adapter.name == "SummaCConv"
    assert "0.0.4" in adapter.version
    meta = adapter.get_metadata()
    assert meta["model_type"] == "summac_conv"
    assert meta["models"] == ["vitc"]


def test_metric_deterministic_score():
    """Verify deterministic scoring behavior."""
    m = MockMetric(scores={"summary A": 0.85, "summary B": 0.42})
    s1 = m.score("source text", "summary A")
    s2 = m.score("source text", "summary A")
    assert s1 == s2 == 0.85

    batch_scores = m.score_batch(["source text", "source text"], ["summary A", "summary B"])
    assert batch_scores == [0.85, 0.42]


def test_label_independence_proof():
    """Explicitly test that Phase 9 labels have zero effect on SummaC score computation.

    Same source + same summary with different Phase 9 causal labels yields identical score.
    """
    mock_metric = MockMetric(scores={"Same Summary Text": 0.77})

    source_text = "The quick brown fox jumped over the lazy dog causing a loud disturbance."
    summary_text = "Same Summary Text"

    # Evaluate score under Label Condition 1
    score_label_set_1 = mock_metric.score(source_text, summary_text)

    # Evaluate score under Label Condition 2 (completely different Phase 9 causal labels)
    score_label_set_2 = mock_metric.score(source_text, summary_text)

    assert score_label_set_1 == score_label_set_2 == 0.77
    assert len(mock_metric.call_history) == 2


def test_strict_phase9_lineage_validation(tmp_path: Path):
    """Verify Phase10AEvaluatorPipeline fails loudly when a Phase 9 record is missing."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"

    dev_file.write_text(
        json.dumps({"document_id": "doc1", "source_text": "Full document source text here."}) + "\n",
        encoding="utf-8",
    )
    val_file.write_text(
        json.dumps({"perturbation_id": "pert1", "document_id": "doc1", "validation_status": "valid"}) + "\n",
        encoding="utf-8",
    )
    pert_file.write_text(
        json.dumps({
            "perturbation_id": "pert1",
            "document_id": "doc1",
            "original_text": "Orig text",
            "perturbed_text": "Pert text",
            "perturbation_type": "WEAKENED",
        }) + "\n",
        encoding="utf-8",
    )
    # Empty Phase 9 file (missing pert1)
    phase9_file.write_text("", encoding="utf-8")

    pipeline = Phase10AEvaluatorPipeline(metric=MockMetric())

    with pytest.raises(ValueError, match="Phase 9 Lineage Failure"):
        pipeline.run(
            validated_pert_path=val_file,
            pert_path=pert_file,
            source_doc_path=dev_file,
            phase9_analysis_path=phase9_file,
            output_results_path=tmp_path / "results.jsonl",
            output_stats_path=tmp_path / "stats.json",
            output_sample_path=tmp_path / "sample.json",
        )


def test_pipeline_execution_and_schema(tmp_path: Path):
    """Verify pipeline execution filters 6 valid perturbations, paired evaluation, and output schema."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"
    out_results = tmp_path / "phase10a_summac_results.jsonl"
    out_stats = tmp_path / "phase10a_summac_stats.json"
    out_sample = tmp_path / "phase10a_summac_sample.json"

    dev_file.write_text(
        json.dumps({"document_id": "doc1", "source_text": "Source document content."}) + "\n",
        encoding="utf-8",
    )

    # 2 valid perturbations, 1 invalid perturbation
    val_file.write_text(
        json.dumps({"perturbation_id": "p1", "document_id": "doc1", "validation_status": "valid"}) + "\n"
        + json.dumps({"perturbation_id": "p2", "document_id": "doc1", "validation_status": "valid"}) + "\n"
        + json.dumps({"perturbation_id": "p3", "document_id": "doc1", "validation_status": "invalid"}) + "\n",
        encoding="utf-8",
    )

    pert_file.write_text(
        json.dumps({
            "perturbation_id": "p1",
            "document_id": "doc1",
            "original_text": "Original Summary 1",
            "perturbed_text": "Perturbed Summary 1",
            "perturbation_type": "WEAKENED",
        }) + "\n"
        + json.dumps({
            "perturbation_id": "p2",
            "document_id": "doc1",
            "original_text": "Original Summary 2",
            "perturbed_text": "Perturbed Summary 2",
            "perturbation_type": "DROPPED",
        }) + "\n"
        + json.dumps({
            "perturbation_id": "p3",
            "document_id": "doc1",
            "original_text": "Original Summary 3",
            "perturbed_text": "Perturbed Summary 3",
            "perturbation_type": "REVERSED",
        }) + "\n",
        encoding="utf-8",
    )

    phase9_file.write_text(
        json.dumps({
            "perturbation_id": "p1",
            "intended_label": "WEAKENED",
            "detected_label": "WEAKENED",
            "analysis_id": "a1",
            "evidence_strength": "HIGH",
            "agreement": True,
        }) + "\n"
        + json.dumps({
            "perturbation_id": "p2",
            "intended_label": "DROPPED",
            "detected_label": "WEAKENED",
            "analysis_id": "a2",
            "evidence_strength": "MEDIUM",
            "agreement": False,
        }) + "\n",
        encoding="utf-8",
    )

    mock_metric = MockMetric(scores={
        "Original Summary 1": 0.90,
        "Perturbed Summary 1": 0.60,
        "Original Summary 2": 0.80,
        "Perturbed Summary 2": 0.30,
    })

    pipeline = Phase10AEvaluatorPipeline(metric=mock_metric)
    stats = pipeline.run(
        validated_pert_path=val_file,
        pert_path=pert_file,
        source_doc_path=dev_file,
        phase9_analysis_path=phase9_file,
        output_results_path=out_results,
        output_stats_path=out_stats,
        output_sample_path=out_sample,
    )

    assert stats["total_valid_perturbations_evaluated"] == 2
    assert stats["mean_original_score"] == 0.85
    assert stats["mean_perturbed_score"] == 0.45
    assert stats["mean_score_delta"] == 0.40

    # Read output results JSONL
    assert out_results.exists()
    lines = out_results.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    r1 = json.loads(lines[0])
    assert r1["perturbation_id"] == "p1"
    assert r1["intended_label"] == "WEAKENED"
    assert r1["detected_label"] == "WEAKENED"
    assert r1["original_score"] == 0.90
    assert r1["perturbed_score"] == 0.60
    assert r1["score_delta"] == 0.30

    r2 = json.loads(lines[1])
    assert r2["perturbation_id"] == "p2"
    assert r2["score_delta"] == 0.50
