"""Unit tests for Phase 12 Step 3 Statistical Correlation & Metric Sensitivity Evaluator."""

import json
import pytest
from causalfidelity.annotation.schema import AnnotationRecord
from causalfidelity.annotation.correlation import (
    CorrelationResult,
    StatisticalCorrelationEvaluator,
    compute_descriptive_stats,
    compute_pearson_r,
    compute_roc_auc,
    compute_spearman_rho,
)


@pytest.fixture
def evaluator():
    return StatisticalCorrelationEvaluator()


def test_1_pearson_correlation_known_dataset():
    """Test 1: Pearson r calculation on a known linear dataset (x=[1,2,3,4,5], y=[2,4,6,8,10] => r=1.0)."""
    res = compute_pearson_r([1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 4.0, 6.0, 8.0, 10.0])
    assert res["r"] == 1.0
    assert res["status"] == "calculated"


def test_2_spearman_correlation_known_dataset():
    """Test 2: Spearman rho calculation on monotonic rank dataset."""
    res = compute_spearman_rho([1.0, 2.0, 3.0, 4.0, 5.0], [10.0, 20.0, 30.0, 40.0, 50.0])
    assert res["rho"] == 1.0
    assert res["status"] == "calculated"


def test_3_perfect_positive_correlation():
    """Test 3: Perfect positive correlation produces r = 1.0."""
    res = compute_pearson_r([10.0, 20.0, 30.0], [100.0, 200.0, 300.0])
    assert res["r"] == 1.0


def test_4_perfect_negative_correlation():
    """Test 4: Perfect negative correlation produces r = -1.0."""
    res = compute_pearson_r([1.0, 2.0, 3.0, 4.0], [10.0, 8.0, 6.0, 4.0])
    assert res["r"] == -1.0


def test_5_constant_input_handling():
    """Test 5: Constant input (zero variance) returns r = None with status 'undefined'."""
    res_x_const = compute_pearson_r([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])
    assert res_x_const["r"] is None
    assert res_x_const["status"] == "undefined"
    assert res_x_const["undefined_reason"] == "constant_input"


def test_6_empty_input_handling():
    """Test 6: Empty input returns r = None with status 'undefined' and undefined_reason 'insufficient_observations'."""
    res = compute_pearson_r([], [])
    assert res["r"] is None
    assert res["status"] == "undefined"
    assert res["undefined_reason"] == "insufficient_observations"


def test_7_missing_metric_scores(evaluator):
    """Test 7: Missing metric score for human record is logged as excluded with reason 'missing_metric_score'."""
    human_recs = [
        AnnotationRecord("a1", "pert_001", "u1", "Faithful", 5),
        AnnotationRecord("a2", "pert_002", "u1", "Reversed", 2),
    ]
    automated_metrics = [
        {"perturbation_id": "pert_001", "summac_score": 0.9},
        # pert_002 is missing from metrics
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    assert result.matched_records_count == 1
    assert result.unmatched_human_count == 1
    assert any(exc["reason"] == "missing_metric_score" for exc in result.excluded_records)


def test_8_missing_human_judgments(evaluator):
    """Test 8: Metric score with no human judgment is logged as excluded with reason 'missing_human_judgment'."""
    human_recs = [
        AnnotationRecord("a1", "pert_001", "u1", "Faithful", 5),
    ]
    automated_metrics = [
        {"perturbation_id": "pert_001", "summac_score": 0.9},
        {"perturbation_id": "pert_999", "summac_score": 0.2},  # pert_999 missing in human recs
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    assert result.matched_records_count == 1
    assert result.unmatched_metric_count == 1
    assert any(exc["reason"] == "missing_human_judgment" for exc in result.excluded_records)


def test_9_duplicate_identifier_detection(evaluator):
    """Test 9: Duplicate metric perturbation_id is detected and flagged in warnings and excluded records."""
    human_recs = [
        AnnotationRecord("a1", "pert_001", "u1", "Faithful", 5),
    ]
    automated_metrics = [
        {"perturbation_id": "pert_001", "summac_score": 0.9},
        {"perturbation_id": "pert_001", "summac_score": 0.8},  # Duplicate pert_001
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    assert len(result.data_quality_warnings) > 0
    assert any(exc["reason"] == "duplicate_identifier" for exc in result.excluded_records)


def test_10_unmatched_record_reporting(evaluator):
    """Test 10: Unmatched records report accurate counts and explicit exclusion entries."""
    human_recs = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p2", "u1", "Weakened", 3),
    ]
    automated_metrics = [
        {"perturbation_id": "p1", "summac_score": 0.9},
        {"perturbation_id": "p3", "summac_score": 0.1},
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    assert result.matched_records_count == 1
    assert result.unmatched_human_count == 1
    assert result.unmatched_metric_count == 1


def test_11_roc_auc_valid_binary_example():
    """Test 11: ROC-AUC on a separable binary classification example produces expected AUC score."""
    y_true = [1, 1, 0, 0]
    # Score where lower metric = higher distortion probability (faithfulness score)
    y_score = [0.1, 0.2, 0.8, 0.9]
    res = compute_roc_auc(y_true, y_score, is_faithfulness_metric=True)
    assert res["roc_auc"] == 1.0
    assert res["status"] == "calculated"


def test_12_roc_auc_handling_single_class_target():
    """Test 12: ROC-AUC returns None with undefined_reason 'single_class_target' when only 1 class is present."""
    y_true = [1, 1, 1, 1]  # All positive class
    y_score = [0.1, 0.2, 0.3, 0.4]
    res = compute_roc_auc(y_true, y_score)
    assert res["roc_auc"] is None
    assert res["status"] == "undefined"
    assert res["undefined_reason"] == "single_class_target"


def test_13_roc_auc_unavailable_when_binary_mapping_undefined():
    """Test 13: ROC-AUC returns None with undefined_reason 'binary_mapping_undefined' when disabled."""
    y_true = [1, 0, 1, 0]
    y_score = [0.1, 0.9, 0.2, 0.8]
    res = compute_roc_auc(y_true, y_score, binary_mapping_enabled=False)
    assert res["roc_auc"] is None
    assert res["status"] == "undefined"
    assert res["undefined_reason"] == "binary_mapping_undefined"


def test_14_per_category_descriptive_statistics():
    """Test 14: Per-category descriptive statistics calculate count, mean, min, max, std correctly."""
    vals = [2.0, 4.0, 4.0, 4.0, 6.0]
    stats = compute_descriptive_stats(vals)
    assert stats["count"] == 5
    assert stats["mean"] == 4.0
    assert stats["min"] == 2.0
    assert stats["max"] == 6.0
    assert stats["std"] == 1.4142


def test_15_missing_category_reporting(evaluator):
    """Test 15: Missing categories are identified and reported with count=0 and is_present=False."""
    human_recs = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
    ]
    automated_metrics = [
        {"perturbation_id": "p1", "summac_score": 0.9},
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    cat_stats = result.category_sensitivity
    assert "Reversed" in cat_stats
    assert cat_stats["Reversed"]["count"] == 0
    assert cat_stats["Reversed"]["is_present"] is False


def test_16_json_serialization(evaluator):
    """Test 16: CorrelationResult object serializes to JSON string and back to dict without loss."""
    human_recs = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p2", "u1", "Reversed", 2),
    ]
    automated_metrics = [
        {"perturbation_id": "p1", "summac_score": 0.9, "factcc_score": 0.95},
        {"perturbation_id": "p2", "summac_score": 0.1, "factcc_score": 0.05},
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    json_str = result.to_json()
    assert "pearson_correlations" in json_str

    parsed = json.loads(json_str)
    assert parsed["matched_records_count"] == 2
    assert "summac_score_vs_human_distortion" in parsed["pearson_correlations"]


def test_17_metric_score_direction_handling(evaluator):
    """Test 17: Faithfulness metric direction (lower score -> higher distortion probability) is handled correctly."""
    human_recs = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),  # is_distorted = False
        AnnotationRecord("a2", "p2", "u1", "Reversed", 1),  # is_distorted = True
    ]
    automated_metrics = [
        {"perturbation_id": "p1", "summac_score": 0.9},  # High summac = Faithful
        {"perturbation_id": "p2", "summac_score": 0.1},  # Low summac = Distorted
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    binary_metrics = result.binary_classification_metrics["summac_score"]
    assert binary_metrics["score_direction"] == "faithfulness_lower_is_distorted"
    assert binary_metrics["tp"] == 1
    assert binary_metrics["tn"] == 1
    assert binary_metrics["f1_score"] == 1.0


def test_18_invalid_input_record_handling(evaluator):
    """Test 18: Unparseable/invalid dictionary in automated_metrics is recorded as excluded."""
    human_recs = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
    ]
    automated_metrics = [
        "not_a_dictionary",  # Invalid type
    ]
    result = evaluator.evaluate(human_recs, automated_metrics)
    assert len(result.excluded_records) == 2
    assert result.excluded_records[0]["reason"] == "missing_metric_score"
    assert result.excluded_records[0]["record_index"] == 0
