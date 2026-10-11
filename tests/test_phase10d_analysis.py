"""Unit tests for Phase 10D Research Analysis and Cross-Metric Comparison."""

import json
from pathlib import Path
import pytest

from causalfidelity.analysis.cross_metric import CrossMetricAnalyzer
from causalfidelity.analysis.pipeline import Phase10DEvaluatorPipeline


@pytest.fixture
def sample_records():
    """Create synthetic test records for lineage and math validation."""
    p9 = [
        {
            "perturbation_id": "p_001",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "intended_label": "WEAKENED",
            "detected_label": "WEAKENED",
            "evidence_strength": "HIGH",
            "analysis_id": "p9_001",
            "agreement": True,
        },
        {
            "perturbation_id": "p_002",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "intended_label": "DROPPED",
            "detected_label": "DROPPED",
            "evidence_strength": "HIGH",
            "analysis_id": "p9_002",
            "agreement": True,
        },
    ]
    summac = [
        {
            "perturbation_id": "p_001",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "intended_label": "WEAKENED",
            "original_summary": "Initial summary content.",
            "perturbed_summary": "Perturbed summary content.",
            "original_score": 0.85,
            "perturbed_score": 0.70,
            "metadata": {"metric_version": "summac-0.0.4"},
        },
        {
            "perturbation_id": "p_002",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "intended_label": "DROPPED",
            "original_summary": "Second summary content.",
            "perturbed_summary": "Second perturbed content.",
            "original_score": 0.90,
            "perturbed_score": 0.90,
            "metadata": {"metric_version": "summac-0.0.4"},
        },
    ]
    factcc = [
        {
            "perturbation_id": "p_001",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "original_summary": "Initial summary content.",
            "perturbed_summary": "Perturbed summary content.",
            "original_score": 0.9912,
            "perturbed_score": 0.9925,
            "metadata": {"metric_version": "factcc-manueldeprada"},
        },
        {
            "perturbation_id": "p_002",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "original_summary": "Second summary content.",
            "perturbed_summary": "Second perturbed content.",
            "original_score": 0.9850,
            "perturbed_score": 0.9800,
            "metadata": {"metric_version": "factcc-manueldeprada"},
        },
    ]
    bertscore = [
        {
            "perturbation_id": "p_001",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "original_summary": "Initial summary content.",
            "perturbed_summary": "Perturbed summary content.",
            "bertscore_precision": 0.9800,
            "bertscore_recall": 0.9700,
            "bertscore_f1": 0.9750,
            "metadata": {"metric_version": "bert-score-0.3.12"},
        },
        {
            "perturbation_id": "p_002",
            "document_id": "doc_1",
            "summary_id": "sum_1",
            "original_summary": "Second summary content.",
            "perturbed_summary": "Second perturbed content.",
            "bertscore_precision": 0.9500,
            "bertscore_recall": 0.9300,
            "bertscore_f1": 0.9400,
            "metadata": {"metric_version": "bert-score-0.3.12"},
        },
    ]
    return p9, summac, factcc, bertscore


def test_1_loading_input_artifacts(tmp_path):
    """Test 1: Correct loading of all input artifacts."""
    p9_file = tmp_path / "p9.jsonl"
    p9_file.write_text('{"perturbation_id": "p1"}\n', encoding="utf-8")
    
    pipeline = Phase10DEvaluatorPipeline()
    records = pipeline._load_jsonl(p9_file)
    assert len(records) == 1
    assert records[0]["perturbation_id"] == "p1"


def test_2_duplicate_perturbation_id_detection(sample_records):
    """Test 2: Duplicate perturbation ID detection."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    
    # Duplicate in summac
    dup_summac = summac + [summac[0]]
    with pytest.raises(ValueError, match="Duplicate perturbation IDs"):
        analyzer.verify_lineage(p9, dup_summac, factcc, bertscore)


def test_3_missing_metric_record_detection(sample_records):
    """Test 3: Missing metric record detection."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    
    # Missing p_002 in factcc
    trunc_factcc = [factcc[0]]
    with pytest.raises(ValueError, match="Mismatch in perturbation IDs"):
        analyzer.verify_lineage(p9, summac, trunc_factcc, bertscore)


def test_4_extra_metric_record_detection(sample_records):
    """Test 4: Extra metric record detection."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    
    extra_bertscore = bertscore + [{
        "perturbation_id": "p_extra",
        "document_id": "doc_1",
        "original_summary": "a",
        "perturbed_summary": "b",
    }]
    with pytest.raises(ValueError, match="Mismatch in perturbation IDs"):
        analyzer.verify_lineage(p9, summac, factcc, extra_bertscore)


def test_5_phase9_lineage_validation(sample_records):
    """Test 5: Phase 9 lineage validation (missing Phase 9 ID)."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    
    # p9 missing p_001
    trunc_p9 = [p9[1]]
    with pytest.raises(ValueError, match="Lineage failure: Perturbation ID 'p_001' missing"):
        analyzer.verify_lineage(trunc_p9, summac, factcc, bertscore)


def test_6_source_document_id_consistency(sample_records):
    """Test 6: Source document ID consistency check."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    
    bad_factcc = [dict(factcc[0], document_id="mismatched_doc"), factcc[1]]
    with pytest.raises(ValueError, match="Document ID mismatch"):
        analyzer.verify_lineage(p9, summac, bad_factcc, bertscore)


def test_7_intended_label_consistency(sample_records):
    """Test 7: Intended label preservation and extraction."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    assert combined[0]["intended_perturbation_type"] == "WEAKENED"
    assert combined[1]["intended_perturbation_type"] == "DROPPED"


def test_8_detected_label_consistency(sample_records):
    """Test 8: Detected label preservation and extraction."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    assert combined[0]["detected_distortion_label"] == "WEAKENED"
    assert combined[1]["detected_distortion_label"] == "DROPPED"


def test_9_text_consistency(sample_records):
    """Test 9: Original and perturbed summary text consistency check."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    
    bad_bs = [dict(bertscore[0], original_summary="Different text"), bertscore[1]]
    with pytest.raises(ValueError, match="Original summary text mismatch"):
        analyzer.verify_lineage(p9, summac, factcc, bad_bs)


def test_10_summac_delta_calculation(sample_records):
    """Test 10: Correct SummaCConv delta calculation (orig - pert)."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    
    # 0.85 - 0.70 = 0.15
    assert combined[0]["summac_delta"] == pytest.approx(0.15, abs=1e-4)
    # 0.90 - 0.90 = 0.0
    assert combined[1]["summac_delta"] == pytest.approx(0.0, abs=1e-4)


def test_11_factcc_delta_calculation(sample_records):
    """Test 11: Correct FactCC delta calculation (orig - pert)."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    
    # 0.9912 - 0.9925 = -0.0013
    assert combined[0]["factcc_delta"] == pytest.approx(-0.0013, abs=1e-4)
    # 0.9850 - 0.9800 = 0.0050
    assert combined[1]["factcc_delta"] == pytest.approx(0.0050, abs=1e-4)


def test_12_bertscore_similarity_loss_calculation(sample_records):
    """Test 12: Correct BERTScore similarity-loss calculation (1.0 - f1)."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    
    # 1.0 - 0.9750 = 0.0250
    assert combined[0]["bertscore_similarity_loss"] == pytest.approx(0.0250, abs=1e-4)
    # 1.0 - 0.9400 = 0.0600
    assert combined[1]["bertscore_similarity_loss"] == pytest.approx(0.0600, abs=1e-4)


def test_13_grouping_by_perturbation_type(sample_records):
    """Test 13: Correct grouping by perturbation type."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    stats = analyzer.compute_statistics(combined)
    
    bk = stats["breakdown_by_intended_perturbation_type"]
    assert "WEAKENED" in bk
    assert bk["WEAKENED"]["count"] == 1
    assert bk["WEAKENED"]["is_single_observation"] is True
    assert bk["DROPPED"]["count"] == 1


def test_14_descriptive_statistics(sample_records):
    """Test 14: Correct descriptive statistics calculation."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    stats = analyzer.compute_statistics(combined)
    
    assert stats["benchmark_overview"]["total_valid_perturbations_evaluated"] == 2
    assert stats["summac_statistics"]["positive_count"] == 1
    assert stats["summac_statistics"]["zero_count"] == 1


def test_15_handling_missing_categories(sample_records):
    """Test 15: Handling of missing or zero-count categories."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    stats = analyzer.compute_statistics(combined)
    
    bk = stats["breakdown_by_intended_perturbation_type"]
    assert bk["REVERSED"]["count"] == 0
    assert "0 valid benchmark examples" in bk["REVERSED"]["coverage"]


def test_16_preservation_of_numeric_precision(sample_records):
    """Test 16: Preservation of original numeric precision in combined records."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined = analyzer.combine_records(p9, summac, factcc, bertscore)
    
    assert combined[0]["factcc_original_score"] == 0.9912
    assert combined[0]["factcc_perturbed_score"] == 0.9925


def test_17_deterministic_output_behavior(sample_records, tmp_path):
    """Test 17: Deterministic output behavior across multiple runs."""
    p9, summac, factcc, bertscore = sample_records
    analyzer = CrossMetricAnalyzer()
    combined1 = analyzer.combine_records(p9, summac, factcc, bertscore)
    stats1 = analyzer.compute_statistics(combined1)
    
    combined2 = analyzer.combine_records(p9, summac, factcc, bertscore)
    stats2 = analyzer.compute_statistics(combined2)
    
    assert json.dumps(stats1, sort_keys=True) == json.dumps(stats2, sort_keys=True)


def test_18_regression_protection_frozen_artifacts():
    """Test 18: Verify frozen artifacts exist and are not empty."""
    p9_path = Path("data/processed/causal_distortion_analysis.jsonl")
    sm_path = Path("data/processed/phase10a_summac_results.jsonl")
    fc_path = Path("data/processed/phase10b_factcc_results.jsonl")
    bs_path = Path("data/processed/phase10c_bertscore_results.jsonl")
    
    for p in [p9_path, sm_path, fc_path, bs_path]:
        assert p.exists(), f"Frozen artifact missing: {p}"
        assert p.stat().st_size > 0, f"Frozen artifact is empty: {p}"
