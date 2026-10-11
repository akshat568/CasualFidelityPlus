"""Unit tests for Phase 12 Step 2 Inter-Annotator Agreement Evaluator."""

import json
import pytest
from causalfidelity.annotation.agreement import AgreementResult, InterAnnotatorAgreementEvaluator
from causalfidelity.annotation.schema import AnnotationRecord


@pytest.fixture
def evaluator():
    return InterAnnotatorAgreementEvaluator()


def test_1_perfect_agreement_produces_kappa_one(evaluator):
    """Test 1: Perfect agreement across multiple categories produces Cohen's Kappa = 1.0."""
    records = [
        # Item 1
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p1", "u2", "Faithful", 5),
        # Item 2
        AnnotationRecord("a3", "p2", "u1", "Reversed", 4),
        AnnotationRecord("a4", "p2", "u2", "Reversed", 4),
        # Item 3
        AnnotationRecord("a5", "p3", "u1", "Weakened", 3),
        AnnotationRecord("a6", "p3", "u2", "Weakened", 3),
        # Item 4
        AnnotationRecord("a7", "p4", "u1", "Dropped", 2),
        AnnotationRecord("a8", "p4", "u2", "Dropped", 2),
        # Item 5
        AnnotationRecord("a9", "p5", "u1", "Cause_Changed", 1),
        AnnotationRecord("a10", "p5", "u2", "Cause_Changed", 1),
    ]

    result = evaluator.evaluate(records)
    assert result.eligible_paired_items == 5
    assert result.causal_classification_agreement["cohens_kappa"] == 1.0
    assert result.causal_classification_agreement["observed_agreement"] == 1.0
    assert result.naturalness_agreement["cohens_kappa"] == 1.0


def test_2_known_example_produces_expected_kappa(evaluator):
    """Test 2: Known numerical agreement example produces expected Kappa (P_o=0.8, P_e=0.24, Kappa=0.7368)."""
    # 5 items, 4 matches, 1 disagreement
    records = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p1", "u2", "Faithful", 5),

        AnnotationRecord("a3", "p2", "u1", "Faithful", 4),
        AnnotationRecord("a4", "p2", "u2", "Weakened", 4),  # Disagreement

        AnnotationRecord("a5", "p3", "u1", "Reversed", 3),
        AnnotationRecord("a6", "p3", "u2", "Reversed", 3),

        AnnotationRecord("a7", "p4", "u1", "Weakened", 2),
        AnnotationRecord("a8", "p4", "u2", "Weakened", 2),

        AnnotationRecord("a9", "p5", "u1", "Dropped", 1),
        AnnotationRecord("a10", "p5", "u2", "Dropped", 1),
    ]

    result = evaluator.evaluate(records)
    causal_stats = result.causal_classification_agreement
    assert causal_stats["matched_pairs_count"] == 5
    assert causal_stats["observed_agreement"] == 0.8
    assert causal_stats["expected_agreement"] == 0.24
    assert causal_stats["cohens_kappa"] == 0.7368


def test_3_causal_classification_agreement_across_six_categories(evaluator):
    """Test 3: Causal classification agreement includes all six approved categories in confusion matrix."""
    records = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p1", "u2", "Effect_Changed", 5),
    ]
    result = evaluator.evaluate(records)
    cm = result.causal_classification_agreement["confusion_matrix"]
    expected_categories = ["Cause_Changed", "Dropped", "Effect_Changed", "Faithful", "Reversed", "Weakened"]
    assert sorted(list(cm.keys())) == expected_categories
    for cat in expected_categories:
        assert sorted(list(cm[cat].keys())) == expected_categories


def test_4_naturalness_agreement_across_ratings_1_to_5(evaluator):
    """Test 4: Naturalness rating agreement handles integer categories 1 through 5."""
    records = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 1),
        AnnotationRecord("a2", "p1", "u2", "Faithful", 1),
        AnnotationRecord("a3", "p2", "u1", "Faithful", 5),
        AnnotationRecord("a4", "p2", "u2", "Faithful", 5),
    ]
    result = evaluator.evaluate(records)
    nat_stats = result.naturalness_agreement
    assert nat_stats["matched_pairs_count"] == 2
    cm = nat_stats["confusion_matrix"]
    assert sorted([int(k) for k in cm.keys()]) == [1, 2, 3, 4, 5]


def test_5_empty_input_handling(evaluator):
    """Test 5: Empty input returns zero paired items and undefined Kappa with clear reason."""
    result = evaluator.evaluate([])
    assert result.total_input_records == 0
    assert result.eligible_paired_items == 0
    assert result.causal_classification_agreement["cohens_kappa"] is None
    assert result.causal_classification_agreement["undefined_reason"] == "no_eligible_annotation_pairs"


def test_6_no_eligible_pairs(evaluator):
    """Test 6: Input with no eligible pairs (only single annotations per item) returns zero pairs."""
    records = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p2", "u2", "Reversed", 4),
    ]
    result = evaluator.evaluate(records)
    assert result.total_unique_items == 2
    assert result.eligible_paired_items == 0
    assert result.excluded_items_count == 2
    assert result.causal_classification_agreement["cohens_kappa"] is None
    assert result.causal_classification_agreement["undefined_reason"] == "no_eligible_annotation_pairs"


def test_7_missing_annotator_records(evaluator):
    """Test 7: Record with empty annotator_id is excluded from pairing."""
    raw_records = [
        {"annotation_id": "a1", "perturbation_id": "p1", "annotator_id": "", "causal_label": "Faithful", "naturalness_rating": 5},
        {"annotation_id": "a2", "perturbation_id": "p1", "annotator_id": "u2", "causal_label": "Faithful", "naturalness_rating": 5},
    ]
    result = evaluator.evaluate(raw_records)
    assert result.eligible_paired_items == 0
    assert result.excluded_items_count >= 1
    assert any("invalid_record" in exc["reason"] for exc in result.excluded_items)


def test_8_more_than_two_annotators_for_item(evaluator):
    """Test 8: Item with 3 annotators is excluded from agreement calculation."""
    records = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p1", "u2", "Faithful", 5),
        AnnotationRecord("a3", "p1", "u3", "Weakened", 4),  # 3rd annotator
    ]
    result = evaluator.evaluate(records)
    assert result.eligible_paired_items == 0
    assert result.excluded_items_count == 1
    assert result.excluded_items[0]["reason"] == "excess_annotators_count: 3"


def test_9_duplicate_annotator_item_pair_detection(evaluator):
    """Test 9: Item with duplicate annotations from same annotator is excluded."""
    records = [
        AnnotationRecord("a1", "p1", "user_a", "Faithful", 5),
        AnnotationRecord("a2", "p1", "user_a", "Reversed", 4),  # Duplicate user_a on p1
    ]
    result = evaluator.evaluate(records)
    assert result.eligible_paired_items == 0
    assert result.excluded_items_count == 1
    assert result.excluded_items[0]["reason"] == "duplicate_annotator_for_item"


def test_10_invalid_causal_label_handling(evaluator):
    """Test 10: Annotation with invalid causal label is excluded."""
    raw_records = [
        {"annotation_id": "a1", "perturbation_id": "p1", "annotator_id": "u1", "causal_label": "Invalid_Label", "naturalness_rating": 5},
        {"annotation_id": "a2", "perturbation_id": "p1", "annotator_id": "u2", "causal_label": "Faithful", "naturalness_rating": 5},
    ]
    result = evaluator.evaluate(raw_records)
    assert result.eligible_paired_items == 0
    assert any("invalid_record" in exc["reason"] for exc in result.excluded_items)


def test_11_invalid_naturalness_rating_handling(evaluator):
    """Test 11: Annotation with out-of-bounds naturalness rating is excluded."""
    raw_records = [
        {"annotation_id": "a1", "perturbation_id": "p1", "annotator_id": "u1", "causal_label": "Faithful", "naturalness_rating": 10},
        {"annotation_id": "a2", "perturbation_id": "p1", "annotator_id": "u2", "causal_label": "Faithful", "naturalness_rating": 5},
    ]
    result = evaluator.evaluate(raw_records)
    assert result.eligible_paired_items == 0
    assert any("invalid_record" in exc["reason"] for exc in result.excluded_items)


def test_12_disagreement_summary_generation(evaluator):
    """Test 12: Disagreements between annotators are reported with details."""
    records = [
        AnnotationRecord("a1", "p1", "user_a", "Faithful", 5),
        AnnotationRecord("a2", "p1", "user_b", "Weakened", 3),
    ]
    result = evaluator.evaluate(records)
    causal_disagreements = result.causal_classification_agreement["disagreement_summary"]
    naturalness_disagreements = result.naturalness_agreement["disagreement_summary"]

    assert len(causal_disagreements) == 1
    assert causal_disagreements[0]["perturbation_id"] == "p1"
    assert causal_disagreements[0]["label1"] == "Faithful"
    assert causal_disagreements[0]["label2"] == "Weakened"

    assert len(naturalness_disagreements) == 1
    assert naturalness_disagreements[0]["rating1"] == 5
    assert naturalness_disagreements[0]["rating2"] == 3


def test_13_excluded_item_reporting(evaluator):
    """Test 13: Excluded items report original perturbation_id and clear reason."""
    records = [
        AnnotationRecord("a1", "p_single", "u1", "Faithful", 5),  # Insufficient annotators
    ]
    result = evaluator.evaluate(records)
    assert len(result.excluded_items) == 1
    assert result.excluded_items[0]["perturbation_id"] == "p_single"
    assert "insufficient_annotators_count" in result.excluded_items[0]["reason"]


def test_14_json_serialization(evaluator):
    """Test 14: AgreementResult serializes cleanly to JSON and back to dictionary."""
    records = [
        AnnotationRecord("a1", "p1", "u1", "Faithful", 5),
        AnnotationRecord("a2", "p1", "u2", "Faithful", 5),
    ]
    result = evaluator.evaluate(records)
    d = result.to_dict()
    assert d["eligible_paired_items"] == 1

    json_str = result.to_json()
    assert "causal_classification_agreement" in json_str
    reloaded = json.loads(json_str)
    assert reloaded["eligible_paired_items"] == 1
