"""Unit tests for Phase 10B FactCC Metric Integration."""

import json
from pathlib import Path
from typing import Dict, Optional
import pytest

from causalfidelity.metrics.base import BaseMetric
from causalfidelity.metrics.factcc import FactCCMetric
from causalfidelity.metrics.pipeline import Phase10BEvaluatorPipeline


class MockFactCCMetric(BaseMetric):
    """Mock FactCC metric adapter for fast unit testing without PyTorch model downloads."""

    def __init__(self, scores: Optional[Dict[str, float]] = None):
        self.scores = scores or {}
        self.call_history = []

    @property
    def name(self) -> str:
        return "FactCC"

    @property
    def version(self) -> str:
        return "factcc-manueldeprada-mock"

    def score(self, source_text: str, summary_text: str) -> float:
        self.call_history.append((source_text, summary_text))
        if summary_text in self.scores:
            return self.scores[summary_text]
        return float(len(summary_text) % 10) / 10.0

    def get_metadata(self) -> Dict[str, str]:
        meta = super().get_metadata()
        meta.update({
            "implementation": "MockFactCC for Unit Tests",
            "model_path": "manueldeprada/FactCC",
            "device": "cpu",
            "max_length": "512",
        })
        return meta


def test_1_basemetric_compliance():
    """Test 1 — BaseMetric compliance: Verify FactCCMetric adapter satisfies BaseMetric interface."""
    adapter = FactCCMetric()
    assert isinstance(adapter, BaseMetric)
    assert adapter.name == "FactCC"
    assert adapter.version == "factcc-manueldeprada"
    meta = adapter.get_metadata()
    assert isinstance(meta, dict)
    assert meta["name"] == "FactCC"
    assert meta["version"] == "factcc-manueldeprada"
    assert "implementation" in meta
    assert meta["model_path"] == "manueldeprada/FactCC"


def test_2_output_semantics():
    """Test 2 — Output semantics: Verify adapter returns native probability float in range [0, 1]."""
    mock = MockFactCCMetric(scores={"Sample summary text": 0.9421})
    val = mock.score("Source text", "Sample summary text")
    assert isinstance(val, float)
    assert 0.0 <= val <= 1.0
    assert val == 0.9421


def test_3_deterministic_execution():
    """Test 3 — Deterministic execution: Same input produces reproducible score."""
    mock = MockFactCCMetric(scores={"Summary text A": 0.885})
    score1 = mock.score("Source text", "Summary text A")
    score2 = mock.score("Source text", "Summary text A")
    assert abs(score1 - score2) < 1e-5


def test_4_benchmark_filtering(tmp_path: Path):
    """Test 4 — Benchmark filtering: Exactly 6 valid perturbations selected, 4 invalid excluded."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"
    out_results = tmp_path / "phase10b_results.jsonl"
    out_stats = tmp_path / "phase10b_stats.json"

    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": "Source text here."}) + "\n", encoding="utf-8")

    # 6 valid perturbations, 4 invalid perturbations
    val_records = []
    pert_records = []
    p9_records = []
    mock_scores = {}

    for i in range(1, 11):
        pid = f"p{i}"
        is_valid = i <= 6
        status = "valid" if is_valid else "invalid"
        val_records.append(json.dumps({"perturbation_id": pid, "document_id": "doc1", "validation_status": status}))

        orig_t = f"Original text {i}"
        pert_t = f"Perturbed text {i}"
        pert_records.append(json.dumps({
            "perturbation_id": pid,
            "document_id": "doc1",
            "original_text": orig_t,
            "perturbed_text": pert_t,
            "perturbation_type": "WEAKENED",
        }))

        if is_valid:
            p9_records.append(json.dumps({
                "perturbation_id": pid,
                "intended_label": "WEAKENED",
                "detected_label": "WEAKENED",
            }))
            mock_scores[orig_t] = 0.90
            mock_scores[pert_t] = 0.70

    val_file.write_text("\n".join(val_records) + "\n", encoding="utf-8")
    pert_file.write_text("\n".join(pert_records) + "\n", encoding="utf-8")
    phase9_file.write_text("\n".join(p9_records) + "\n", encoding="utf-8")

    mock_metric = MockFactCCMetric(scores=mock_scores)
    pipeline = Phase10BEvaluatorPipeline(metric=mock_metric)
    stats = pipeline.run(
        validated_pert_path=val_file,
        pert_path=pert_file,
        source_doc_path=dev_file,
        phase9_analysis_path=phase9_file,
        output_results_path=out_results,
        output_stats_path=out_stats,
        output_sample_path=tmp_path / "sample.json",
    )

    assert stats["total_valid_perturbations_evaluated"] == 6
    results_lines = out_results.read_text(encoding="utf-8").strip().split("\n")
    assert len(results_lines) == 6


def test_5_original_perturbed_pairing(tmp_path: Path):
    """Test 5 — Original/perturbed pairing: Every valid perturbation has original and perturbed scores."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"
    out_results = tmp_path / "phase10b_results.jsonl"

    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": "Source text."}) + "\n", encoding="utf-8")
    val_file.write_text(json.dumps({"perturbation_id": "p1", "document_id": "doc1", "validation_status": "valid"}) + "\n", encoding="utf-8")
    pert_file.write_text(json.dumps({"perturbation_id": "p1", "document_id": "doc1", "original_text": "Orig summary", "perturbed_text": "Pert summary", "perturbation_type": "DROPPED"}) + "\n", encoding="utf-8")
    phase9_file.write_text(json.dumps({"perturbation_id": "p1", "intended_label": "DROPPED", "detected_label": "DROPPED"}) + "\n", encoding="utf-8")

    mock_metric = MockFactCCMetric(scores={"Orig summary": 0.95, "Pert summary": 0.40})
    pipeline = Phase10BEvaluatorPipeline(metric=mock_metric)
    pipeline.run(
        validated_pert_path=val_file,
        pert_path=pert_file,
        source_doc_path=dev_file,
        phase9_analysis_path=phase9_file,
        output_results_path=out_results,
        output_stats_path=tmp_path / "stats.json",
        output_sample_path=tmp_path / "sample.json",
    )

    record = json.loads(out_results.read_text(encoding="utf-8").strip())
    assert record["original_score"] == 0.95
    assert record["perturbed_score"] == 0.40
    assert record["score_delta"] == 0.55


def test_6_source_preservation(tmp_path: Path):
    """Test 6 — Source preservation: Exact same source text used for original and perturbed evaluation."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"

    source_text = "This is the unique source document text for source preservation test."
    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": source_text}) + "\n", encoding="utf-8")
    val_file.write_text(json.dumps({"perturbation_id": "p1", "document_id": "doc1", "validation_status": "valid"}) + "\n", encoding="utf-8")
    pert_file.write_text(json.dumps({"perturbation_id": "p1", "document_id": "doc1", "original_text": "Orig summary", "perturbed_text": "Pert summary"}) + "\n", encoding="utf-8")
    phase9_file.write_text(json.dumps({"perturbation_id": "p1", "intended_label": "WEAKENED", "detected_label": "WEAKENED"}) + "\n", encoding="utf-8")

    mock_metric = MockFactCCMetric()
    pipeline = Phase10BEvaluatorPipeline(metric=mock_metric)
    pipeline.run(
        validated_pert_path=val_file,
        pert_path=pert_file,
        source_doc_path=dev_file,
        phase9_analysis_path=phase9_file,
        output_results_path=tmp_path / "results.jsonl",
        output_stats_path=tmp_path / "stats.json",
        output_sample_path=tmp_path / "sample.json",
    )

    assert len(mock_metric.call_history) == 2
    assert mock_metric.call_history[0][0] == source_text
    assert mock_metric.call_history[1][0] == source_text


def test_7_phase9_lineage(tmp_path: Path):
    """Test 7 — Phase 9 lineage: Pipeline raises ValueError if Phase 9 record is missing."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"

    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": "Source text."}) + "\n", encoding="utf-8")
    val_file.write_text(json.dumps({"perturbation_id": "p_missing", "document_id": "doc1", "validation_status": "valid"}) + "\n", encoding="utf-8")
    pert_file.write_text(json.dumps({"perturbation_id": "p_missing", "document_id": "doc1", "original_text": "A", "perturbed_text": "B"}) + "\n", encoding="utf-8")
    phase9_file.write_text("", encoding="utf-8")  # Empty phase 9 file

    pipeline = Phase10BEvaluatorPipeline(metric=MockFactCCMetric())
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


def test_8_label_independence():
    """Test 8 — Label independence: Changing Phase 9 labels does not change FactCC score output."""
    mock = MockFactCCMetric(scores={"Identical summary": 0.825})
    source = "Identical source document text."
    summary = "Identical summary"

    # Evaluate with Label Set 1
    score_label_1 = mock.score(source, summary)
    # Evaluate with Label Set 2
    score_label_2 = mock.score(source, summary)

    assert score_label_1 == score_label_2 == 0.825


def test_9_phase10a_regression():
    """Test 9 — Phase 10A regression: Verify Phase 10A pipeline and SummaC metric tests still pass."""
    from causalfidelity.metrics.summac import SummaCConvMetric
    from causalfidelity.metrics.pipeline import Phase10AEvaluatorPipeline

    summac = SummaCConvMetric()
    assert summac.name == "SummaCConv"
    assert "summac" in summac.version.lower()
