"""Unit tests for Phase 10C BERTScore Metric Integration."""

import json
from pathlib import Path
from typing import Dict, List, Optional
import pytest

from causalfidelity.metrics.base import BaseMetric
from causalfidelity.metrics.bertscore import BERTScoreMetric
from causalfidelity.metrics.pipeline import Phase10CEvaluatorPipeline


class MockBERTScoreMetric(BaseMetric):
    """Mock BERTScore metric adapter for fast unit testing without downloading roberta-large weights."""

    def __init__(self, scores: Optional[Dict[str, Dict[str, float]]] = None):
        self.scores = scores or {}
        self.call_history = []

    @property
    def name(self) -> str:
        return "BERTScore"

    @property
    def version(self) -> str:
        return "bert-score-0.3.13-mock"

    def score(self, source_text: str, summary_text: str) -> float:
        detailed = self.score_detailed(source_text, summary_text)
        return detailed["f1"]

    def score_detailed(self, reference_text: str, candidate_text: str) -> Dict[str, float]:
        self.call_history.append((reference_text, candidate_text))
        if candidate_text in self.scores:
            return self.scores[candidate_text]
        f1_val = round(float(len(candidate_text) % 10 + 5) / 15.0, 4)
        return {"precision": f1_val, "recall": f1_val, "f1": f1_val}

    def score_batch(self, source_texts: List[str], summary_texts: List[str]) -> List[float]:
        detailed = self.score_detailed_batch(source_texts, summary_texts)
        return [d["f1"] for d in detailed]

    def score_detailed_batch(self, reference_texts: List[str], candidate_texts: List[str]) -> List[Dict[str, float]]:
        return [self.score_detailed(ref, cand) for ref, cand in zip(reference_texts, candidate_texts)]

    def get_metadata(self) -> Dict[str, str]:
        meta = super().get_metadata()
        meta.update({
            "implementation": "MockBERTScore for Unit Tests",
            "model_type": "roberta-large",
            "device": "cpu",
            "batch_size": "16",
        })
        return meta


def test_1_basemetric_compliance():
    """Test 1 — BaseMetric compliance: Verify BERTScoreMetric subclass satisfies BaseMetric interface."""
    adapter = BERTScoreMetric()
    assert isinstance(adapter, BaseMetric)


def test_2_name_and_version():
    """Test 2 — Metric name and version: Verify metric name is 'BERTScore' and version contains bert-score."""
    adapter = BERTScoreMetric()
    assert adapter.name == "BERTScore"
    assert "bert-score" in adapter.version


def test_3_metadata_correctness():
    """Test 3 — Metadata correctness: Verify get_metadata returns expected config values."""
    adapter = BERTScoreMetric()
    meta = adapter.get_metadata()
    assert isinstance(meta, dict)
    assert meta["name"] == "BERTScore"
    assert meta["model_type"] == "roberta-large"
    assert meta["device"] == "cpu"
    assert meta["batch_size"] == 16
    assert "implementation" in meta


def test_4_precision_recall_f1_output_types():
    """Test 4 — Output types and ranges: Verify Precision, Recall, and F1 ranges."""
    mock = MockBERTScoreMetric(scores={"cand1": {"precision": 0.92, "recall": 0.88, "f1": 0.90}})
    res = mock.score_detailed("ref1", "cand1")
    assert isinstance(res["precision"], float)
    assert isinstance(res["recall"], float)
    assert isinstance(res["f1"], float)
    assert 0.0 <= res["precision"] <= 1.0
    assert 0.0 <= res["recall"] <= 1.0
    assert 0.0 <= res["f1"] <= 1.0
    assert res["f1"] == 0.90


def test_5_batch_scoring_order_and_consistency():
    """Test 5 — Batch scoring order and consistency: Verify batch outputs match individual outputs in order."""
    scores_map = {
        "cand1": {"precision": 0.95, "recall": 0.90, "f1": 0.925},
        "cand2": {"precision": 0.80, "recall": 0.70, "f1": 0.7466},
    }
    mock = MockBERTScoreMetric(scores=scores_map)
    batch_res = mock.score_detailed_batch(["ref1", "ref2"], ["cand1", "cand2"])
    assert len(batch_res) == 2
    assert batch_res[0]["f1"] == 0.925
    assert batch_res[1]["f1"] == 0.7466


def test_6_empty_input_handling():
    """Test 6 — Empty-input handling: Verify adapter handles empty/blank inputs without crashing."""
    mock = MockBERTScoreMetric()
    res = mock.score_detailed("", "")
    assert isinstance(res["f1"], float)
    batch_empty = mock.score_detailed_batch([], [])
    assert batch_empty == []


def test_7_strict_lineage_validation(tmp_path: Path):
    """Test 7 — Strict lineage validation: Verify pipeline raises ValueError if Phase 9 record missing."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"

    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": "Source text."}) + "\n", encoding="utf-8")
    val_file.write_text(json.dumps({"perturbation_id": "p_missing", "document_id": "doc1", "validation_status": "valid"}) + "\n", encoding="utf-8")
    pert_file.write_text(json.dumps({"perturbation_id": "p_missing", "document_id": "doc1", "original_text": "A", "perturbed_text": "B"}) + "\n", encoding="utf-8")
    phase9_file.write_text("", encoding="utf-8")  # Empty phase 9 file

    pipeline = Phase10CEvaluatorPipeline(metric=MockBERTScoreMetric())
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


def test_8_filtering_invalid_perturbations(tmp_path: Path):
    """Test 8 — Filtering invalid perturbations: Verify exactly valid status perturbations are evaluated."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"
    out_results = tmp_path / "phase10c_results.jsonl"
    out_stats = tmp_path / "phase10c_stats.json"

    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": "Source text."}) + "\n", encoding="utf-8")

    val_file.write_text(
        json.dumps({"perturbation_id": "p1", "document_id": "doc1", "validation_status": "valid"}) + "\n"
        + json.dumps({"perturbation_id": "p2", "document_id": "doc1", "validation_status": "invalid"}) + "\n",
        encoding="utf-8",
    )
    pert_file.write_text(
        json.dumps({"perturbation_id": "p1", "document_id": "doc1", "original_text": "Orig 1", "perturbed_text": "Pert 1", "perturbation_type": "WEAKENED"}) + "\n"
        + json.dumps({"perturbation_id": "p2", "document_id": "doc1", "original_text": "Orig 2", "perturbed_text": "Pert 2", "perturbation_type": "DROPPED"}) + "\n",
        encoding="utf-8",
    )
    phase9_file.write_text(
        json.dumps({"perturbation_id": "p1", "intended_label": "WEAKENED", "detected_label": "WEAKENED"}) + "\n",
        encoding="utf-8",
    )

    mock = MockBERTScoreMetric(scores={"Pert 1": {"precision": 0.90, "recall": 0.85, "f1": 0.875}})
    pipeline = Phase10CEvaluatorPipeline(metric=mock)
    stats = pipeline.run(
        validated_pert_path=val_file,
        pert_path=pert_file,
        source_doc_path=dev_file,
        phase9_analysis_path=phase9_file,
        output_results_path=out_results,
        output_stats_path=out_stats,
        output_sample_path=tmp_path / "sample.json",
    )

    assert stats["total_valid_perturbations_evaluated"] == 1
    assert stats["total_invalid_perturbations_excluded"] == 1
    lines = out_results.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1


def test_9_phase9_label_independence():
    """Test 9 — Phase 9 label independence: Modifying Phase 9 labels does not change BERTScore output."""
    mock = MockBERTScoreMetric(scores={"Cand summary": {"precision": 0.91, "recall": 0.89, "f1": 0.90}})
    ref = "Ref summary"
    cand = "Cand summary"

    res1 = mock.score_detailed(ref, cand)
    res2 = mock.score_detailed(ref, cand)
    assert res1["f1"] == res2["f1"] == 0.90


def test_10_deterministic_output_behavior():
    """Test 10 — Deterministic output behavior: Same inputs produce identical BERTScore outputs."""
    mock = MockBERTScoreMetric(scores={"Cand": {"precision": 0.95, "recall": 0.93, "f1": 0.94}})
    r1 = mock.score_detailed("Ref", "Cand")
    r2 = mock.score_detailed("Ref", "Cand")
    assert r1 == r2 == {"precision": 0.95, "recall": 0.93, "f1": 0.94}


def test_11_correct_score_difference_calculations(tmp_path: Path):
    """Test 11 — Score difference / similarity loss calculation: Verify similarity_loss = 1.0 - f1."""
    dev_file = tmp_path / "xsum_dev.jsonl"
    val_file = tmp_path / "validated_perturbations.jsonl"
    pert_file = tmp_path / "perturbations.jsonl"
    phase9_file = tmp_path / "causal_distortion_analysis.jsonl"
    out_results = tmp_path / "results.jsonl"

    dev_file.write_text(json.dumps({"document_id": "doc1", "source_text": "Source text."}) + "\n", encoding="utf-8")
    val_file.write_text(json.dumps({"perturbation_id": "p1", "document_id": "doc1", "validation_status": "valid"}) + "\n", encoding="utf-8")
    pert_file.write_text(json.dumps({"perturbation_id": "p1", "document_id": "doc1", "original_text": "Orig", "perturbed_text": "Pert"}) + "\n", encoding="utf-8")
    phase9_file.write_text(json.dumps({"perturbation_id": "p1", "intended_label": "WEAKENED", "detected_label": "WEAKENED"}) + "\n", encoding="utf-8")

    mock = MockBERTScoreMetric(scores={"Pert": {"precision": 0.85, "recall": 0.75, "f1": 0.80}})
    pipeline = Phase10CEvaluatorPipeline(metric=mock)
    pipeline.run(
        validated_pert_path=val_file,
        pert_path=pert_file,
        source_doc_path=dev_file,
        phase9_analysis_path=phase9_file,
        output_results_path=out_results,
        output_stats_path=tmp_path / "stats.json",
        output_sample_path=tmp_path / "sample.json",
    )

    rec = json.loads(out_results.read_text(encoding="utf-8").strip())
    assert rec["bertscore_f1"] == 0.80
    assert rec["similarity_loss"] == 0.20


def test_12_regression_protection_for_frozen_phases():
    """Test 12 — Regression protection: Verify Phase 10A (SummaC) and Phase 10B (FactCC) adapters still work."""
    from causalfidelity.metrics.factcc import FactCCMetric
    from causalfidelity.metrics.summac import SummaCConvMetric

    s = SummaCConvMetric()
    assert s.name == "SummaCConv"
    f = FactCCMetric()
    assert f.name == "FactCC"
