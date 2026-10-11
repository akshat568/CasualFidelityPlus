"""Unit tests for Phase 9 Causal Distortion Detection."""

import json
from pathlib import Path
import pytest

from causalfidelity.config import AppConfig, CausalDistortionConfig, load_config
from causalfidelity.distortion.classifier import DistortionClassifier
from causalfidelity.distortion.evidence import DistortionEvidenceCollector, EvidenceBundle
from causalfidelity.distortion.pipeline import DistortionDetectionPipeline, compute_file_sha256
from causalfidelity.distortion.schema import (
    DistortionAnalysisRecord,
    DistortionLabel,
    EvidenceStrength,
    SummaryEvidenceRecord,
)
from causalfidelity.distortion.validator import DistortionBenchmarkFilter


@pytest.fixture
def classifier():
    return DistortionClassifier(config=CausalDistortionConfig())


@pytest.fixture
def evidence_collector():
    return DistortionEvidenceCollector(config=CausalDistortionConfig())


def test_1_preserved_detection(classifier):
    """Test 1: PRESERVED detection when cause and effect align with strong causal relation."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="torrential rain caused major flooding",
        summary_relation_id="sum_rel_001",
        summary_cause="torrential rain",
        summary_relation="caused",
        summary_effect="major flooding",
        cause_sim=0.85,
        effect_sim=0.85,
        relation_compat=1.0,
        overall_score=0.85,
        has_explicit_summary_relation=True,
        cause_present_in_summary=True,
        effect_present_in_summary=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.PRESERVED
    assert record.evidence_strength in [EvidenceStrength.HIGH, EvidenceStrength.MEDIUM]


def test_2_reversed_detection(classifier):
    """Test 2: REVERSED detection when direction is swapped explicitly."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="flooding caused rainfall",
        summary_relation_id="sum_rel_001",
        summary_cause="flooding",
        summary_relation="caused",
        summary_effect="rainfall",
        cause_sim=0.1,
        effect_sim=0.1,
        reverse_cause_sim=0.9,
        reverse_effect_sim=0.9,
        has_explicit_summary_relation=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.REVERSED


def test_3_weakened_detection(classifier):
    """Test 3: WEAKENED detection when relation uses associative phrasing."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="heavy rainfall was associated with flooding",
        summary_relation="was associated with",
        cause_sim=0.9,
        effect_sim=0.9,
        cause_present_in_summary=True,
        effect_present_in_summary=True,
        has_weakened_language=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.WEAKENED


def test_4_dropped_detection(classifier):
    """Test 4: DROPPED detection when arguments are present without causal link."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="Heavy rainfall occurred and flooding followed in the area.",
        cause_sim=0.9,
        effect_sim=0.9,
        cause_present_in_summary=True,
        effect_present_in_summary=True,
        has_explicit_summary_relation=False,
        has_weakened_language=False,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.DROPPED


def test_5_cause_changed_detection(classifier):
    """Test 5: CAUSE_CHANGED detection when cause is replaced."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="dam failure caused flooding",
        summary_relation_id="sum_rel_001",
        summary_cause="dam failure",
        summary_relation="caused",
        summary_effect="flooding",
        cause_sim=0.1,
        effect_sim=0.9,
        has_explicit_summary_relation=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.CAUSE_CHANGED


def test_6_effect_changed_detection(classifier):
    """Test 6: EFFECT_CHANGED detection when effect is replaced."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="heavy rainfall caused road closures",
        summary_relation_id="sum_rel_001",
        summary_cause="heavy rainfall",
        summary_relation="caused",
        summary_effect="road closures",
        cause_sim=0.9,
        effect_sim=0.1,
        has_explicit_summary_relation=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.EFFECT_CHANGED


def test_7_distorted_detection(classifier):
    """Test 7: DISTORTED detection when generic mismatch exists."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="heavy rainfall partially affected regional flooding issues",
        summary_relation_id="sum_rel_001",
        summary_cause="precipitation",
        summary_relation="affected",
        summary_effect="regional issues",
        cause_sim=0.4,
        effect_sim=0.4,
        overall_score=0.45,
        has_explicit_summary_relation=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.DISTORTED



def test_8_insufficient_evidence(classifier):
    """Test 8: INSUFFICIENT_EVIDENCE returned when evidence is missing/low."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="heavy rainfall",
        source_relation="causes",
        source_effect="flooding",
        summary_id="sum_001",
        summary_text="The local economy grew by three percent.",
        cause_sim=0.0,
        effect_sim=0.0,
        has_explicit_summary_relation=False,
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.INSUFFICIENT_EVIDENCE
    assert record.evidence_strength == EvidenceStrength.INSUFFICIENT


def test_9_missing_summary_relation(classifier):
    """Test 9: Missing summary relation leading to INSUFFICIENT_EVIDENCE if arguments missing."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="A",
        source_relation="causes",
        source_effect="B",
        summary_id="sum_001",
        summary_text="Unrelated text.",
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.INSUFFICIENT_EVIDENCE


def test_10_ambiguous_alignment(classifier):
    """Test 10: Ambiguous alignment handled without forcing distortion label."""
    bundle = EvidenceBundle(
        source_relation_id="rel_001",
        source_cause="A",
        source_relation="causes",
        source_effect="B",
        summary_id="sum_001",
        summary_text="Ambiguous text.",
        cause_sim=0.4,
        effect_sim=0.4,
        alignment_status="ambiguous",
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.INSUFFICIENT_EVIDENCE


def test_11_direction_preservation(evidence_collector):
    """Test 11: Direction preservation evaluation."""
    source_rel = {"relation_id": "r1", "cause": "heavy rain", "relation": "causes", "effect": "floods"}
    sum_rec = {"summary_id": "s1", "summary_text": "heavy rain causes floods"}
    bundle = evidence_collector.collect_from_phase8_alignment(
        source_rel=source_rel,
        alignment=None,
        summary_record=sum_rec,
    )
    assert bundle.cause_present_in_summary is True
    assert bundle.effect_present_in_summary is True


def test_12_direction_reversal(evidence_collector):
    """Test 12: Direction reversal evaluation."""
    source_rel = {"relation_id": "r1", "cause": "heavy rain", "relation": "causes", "effect": "floods"}
    pert = {
        "perturbation_id": "p1",
        "perturbation_type": "REVERSED",
        "summary_id": "s1",
        "perturbed_text": "floods caused heavy rain",
    }
    bundle = evidence_collector.collect_from_perturbation(perturbation=pert, source_rel=source_rel)
    assert bundle.reverse_cause_sim > 0.5 or bundle.reverse_effect_sim > 0.5 or bundle.has_explicit_summary_relation


def test_13_cause_only_alignment(classifier):
    """Test 13: Cause-only alignment does not wrongly label PRESERVED."""
    bundle = EvidenceBundle(
        source_relation_id="r1",
        source_cause="rain",
        source_relation="causes",
        source_effect="floods",
        summary_id="s1",
        summary_text="rain occurred in Dorset",
        cause_sim=0.9,
        effect_sim=0.0,
        cause_present_in_summary=True,
        effect_present_in_summary=False,
    )
    record = classifier.classify(bundle)
    assert record.detected_label != DistortionLabel.PRESERVED


def test_14_effect_only_alignment(classifier):
    """Test 14: Effect-only alignment does not wrongly label PRESERVED."""
    bundle = EvidenceBundle(
        source_relation_id="r1",
        source_cause="rain",
        source_relation="causes",
        source_effect="floods",
        summary_id="s1",
        summary_text="floods happened in Dorset",
        cause_sim=0.0,
        effect_sim=0.9,
        cause_present_in_summary=False,
        effect_present_in_summary=True,
    )
    record = classifier.classify(bundle)
    assert record.detected_label != DistortionLabel.PRESERVED


def test_15_intended_vs_detected_label_separation(classifier):
    """Test 15: Intended and detected labels remain separate."""
    bundle = EvidenceBundle(
        source_relation_id="r1",
        source_cause="rain",
        source_relation="causes",
        source_effect="floods",
        summary_id="s1",
        summary_text="rain and floods happened",
        perturbation_id="p1",
        intended_label="WEAKENED",
        cause_sim=0.9,
        effect_sim=0.9,
        cause_present_in_summary=True,
        effect_present_in_summary=True,
        has_explicit_summary_relation=False,
    )
    record = classifier.classify(bundle)
    assert record.intended_label == "WEAKENED"
    assert record.detected_label == "DROPPED"
    assert record.agreement is False


def test_16_validated_perturbation_filtering():
    """Test 16: Validated perturbations filtered strictly for status=='valid'."""
    val_records = [
        {"perturbation_id": "p1", "validation_status": "valid"},
        {"perturbation_id": "p2", "validation_status": "invalid"},
    ]
    pert_records = [
        {"perturbation_id": "p1", "perturbed_text": "valid text"},
        {"perturbation_id": "p2", "perturbed_text": "invalid text"},
    ]
    valid_list, rejected_list = DistortionBenchmarkFilter.filter_valid_perturbations(val_records, pert_records)
    assert len(valid_list) == 1
    assert valid_list[0]["perturbation_id"] == "p1"
    assert len(rejected_list) == 1
    assert rejected_list[0]["perturbation_id"] == "p2"


def test_17_rejected_perturbations_excluded():
    """Test 17: Rejected perturbations are excluded from benchmark set."""
    val_records = [{"perturbation_id": "p1", "validation_status": "invalid"}]
    pert_records = [{"perturbation_id": "p1", "perturbed_text": "text"}]
    valid_list, rejected_list = DistortionBenchmarkFilter.filter_valid_perturbations(val_records, pert_records)
    assert len(valid_list) == 0
    assert len(rejected_list) == 1


def test_18_null_evidence_serialization():
    """Test 18: Null evidence serialization preserves null values."""
    ev = SummaryEvidenceRecord()
    d = ev.to_dict()
    assert d["summary_relation_id"] is None
    assert d["cause"] is None
    assert d["cause_similarity"] is None

    rec = DistortionAnalysisRecord(
        analysis_id="a1",
        document_id="d1",
        summary_id="s1",
        source_relation_id="sr1",
        source_relation={"cause": "c", "relation": "r", "effect": "e"},
        summary_evidence=ev,
    )
    rec_d = rec.to_dict()
    assert rec_d["perturbation_id"] is None
    assert rec_d["intended_label"] is None
    assert rec_d["agreement"] is None


def test_19_deterministic_ids():
    """Test 19: Deterministic analysis IDs."""
    b1 = EvidenceBundle("sr1", "c", "r", "e", "s1", "txt", perturbation_id="p1")
    b2 = EvidenceBundle("sr1", "c", "r", "e", "s1", "txt", perturbation_id="p1")
    cf = DistortionClassifier()
    r1 = cf.classify(b1)
    r2 = cf.classify(b2)
    assert r1.analysis_id == r2.analysis_id == "dist_pert_p1"


def test_20_deterministic_repeated_pipeline_execution(tmp_path):
    """Test 20: Deterministic repeated pipeline execution producing identical SHA256 hashes."""
    cfg = load_config()
    pipeline = DistortionDetectionPipeline(config=cfg)
    res1 = pipeline.run()
    res2 = pipeline.run()
    assert res1["sha256"] == res2["sha256"]


def test_21_malformed_input_handling(classifier):
    """Test 21: Malformed input handling returns INSUFFICIENT_EVIDENCE safely."""
    bundle = EvidenceBundle(
        source_relation_id="",
        source_cause="",
        source_relation="",
        source_effect="",
        summary_id="",
        summary_text="",
    )
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.INSUFFICIENT_EVIDENCE


def test_22_full_pipeline_integration():
    """Test 22: Full pipeline integration executes and creates output artifacts."""
    cfg = load_config()
    pipeline = DistortionDetectionPipeline(config=cfg)
    res = pipeline.run()
    assert res["status"] == "success"
    assert Path(res["analysis_path"]).exists()
    assert Path(res["stats_path"]).exists()
    assert Path(res["sample_path"]).exists()
    assert Path(res["confusion_matrix_path"]).exists()


def test_group_a_trigger_coverage(evidence_collector):
    """Test Group A: Verify trigger coverage for weakened phrases."""
    source_rel = {"relation_id": "r1", "cause": "rain", "relation": "causes", "effect": "floods"}

    # 1. linked to
    pert1 = {"perturbation_id": "p1", "summary_id": "s1", "perturbed_text": "rain was linked to floods"}
    b1 = evidence_collector.collect_from_perturbation(pert1, source_rel)
    assert b1.has_weakened_language is True

    # 2. coinciding with
    pert2 = {"perturbation_id": "p2", "summary_id": "s2", "perturbed_text": "rain was coinciding with floods"}
    b2 = evidence_collector.collect_from_perturbation(pert2, source_rel)
    assert b2.has_weakened_language is True

    # 3. associated with
    pert3 = {"perturbation_id": "p3", "summary_id": "s3", "perturbed_text": "rain was associated with floods"}
    b3 = evidence_collector.collect_from_perturbation(pert3, source_rel)
    assert b3.has_weakened_language is True

    # 4. after (must NOT be automatically classified as weakened)
    pert4 = {"perturbation_id": "p4", "summary_id": "s4", "perturbed_text": "floods happened after rain"}
    b4 = evidence_collector.collect_from_perturbation(pert4, source_rel)
    assert b4.has_weakened_language is False


def test_group_b_semantic_argument_fallback(evidence_collector, classifier):
    """Test Group B: Verify semantic argument fallback when exact source cause substring matching fails."""
    source_rel = {
        "relation_id": "rel_bridge",
        "cause": "A grade II-listed bridge in Dorset that was blamed for",
        "relation": "causes",
        "effect": "severe floods is to be dismantled and replaced",
    }
    pert = {
        "perturbation_id": "pert_bridge",
        "summary_id": "xsum_000038_ref",
        "perturbation_type": "WEAKENED",
        "perturbed_text": "A grade II-listed bridge in Dorset that was linked to severe floods is to be dismantled and replaced.",
    }

    # Collect evidence using Phase 8 embedding scorer
    bundle = evidence_collector.collect_from_perturbation(pert, source_rel)

    # Exact substring match for cause fails due to 'was blamed for' -> 'was linked to'
    # But semantic similarity meets threshold, establishing cause alignment
    assert bundle.cause_sim >= 0.50 or bundle.cause_present_in_summary
    assert bundle.has_weakened_language is True

    # Classifier detects WEAKENED
    record = classifier.classify(bundle)
    assert record.detected_label == DistortionLabel.WEAKENED

