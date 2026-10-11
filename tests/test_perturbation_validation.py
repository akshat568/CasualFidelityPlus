"""Unit tests for Phase 7 perturbation validation & quality control."""

import json
from pathlib import Path
import pytest

from causalfidelity.config import AppConfig, PathConfig, ValidationConfig
from causalfidelity.validation.checks import (
    check_consistency,
    check_content_preservation,
    check_structural,
    check_target_transformation,
)
from causalfidelity.validation.pipeline import PerturbationValidationPipeline
from causalfidelity.validation.schema import ValidationRecord
from causalfidelity.validation.validator import PerturbationQualityValidator


def test_valid_validation_schema():
    """Test 1: Verify correct ValidationRecord creation."""
    rec = ValidationRecord(
        perturbation_id="xsum_000001_pert_000001",
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        perturbation_type="REVERSED",
        validation_status="valid",
        checks={"structural": "passed", "target_transformation": "passed"},
        errors=[],
        warnings=[],
    )
    assert rec.perturbation_id == "xsum_000001_pert_000001"
    assert rec.validation_status == "valid"
    assert rec.checks["structural"] == "passed"


def test_validation_record_serialization():
    """Test 2: Verify to_dict() and from_dict() roundtrip."""
    rec = ValidationRecord(
        perturbation_id="xsum_000001_pert_000001",
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        perturbation_type="WEAKENED",
        validation_status="valid",
    )
    d = rec.to_dict()
    assert d["perturbation_type"] == "WEAKENED"

    reconstructed = ValidationRecord.from_dict(d)
    assert reconstructed == rec


def test_structural_validation_success():
    """Test 3: Verify check_structural passes for valid record."""
    rec_dict = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "s1",
        "perturbation_type": "REVERSED",
        "original_text": "Flooding caused damage.",
        "perturbed_text": "Damage caused flooding.",
        "original_relation": {"cause": "flooding", "relation": "causes", "effect": "damage"},
        "intended_relation": {"cause": "damage", "relation": "causes", "effect": "flooding"},
        "changed_span": {"original": "Flooding caused damage", "perturbed": "Damage caused flooding"},
        "generation_method": "rule_based",
    }
    status, errors = check_structural(rec_dict)
    assert status == "passed"
    assert len(errors) == 0


def test_structural_missing_required_field():
    """Test 4: Verify check_structural fails on missing summary_id."""
    rec_dict = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "",
        "perturbation_type": "REVERSED",
        "original_text": "A caused B",
        "perturbed_text": "B caused A",
    }
    status, errors = check_structural(rec_dict)
    assert status == "failed"
    assert "missing_summary_id" in errors


def test_invalid_perturbation_type():
    """Test 5: Verify check_structural fails on unknown perturbation_type."""
    rec_dict = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "s1",
        "perturbation_type": "UNKNOWN_TYPE",
        "original_text": "A caused B",
        "perturbed_text": "B caused A",
    }
    status, errors = check_structural(rec_dict)
    assert status == "failed"
    assert any("invalid_perturbation_type" in e for e in errors)


def test_valid_reversed_validation():
    """Test 6: Verify check_target_transformation passes for valid REVERSED."""
    rec_dict = {
        "perturbation_type": "REVERSED",
        "original_relation": {"cause": "flooding", "relation": "causes", "effect": "road closures"},
        "intended_relation": {"cause": "road closures", "relation": "causes", "effect": "flooding"},
        "perturbed_text": "Road closures caused flooding.",
    }
    status, errors = check_target_transformation(rec_dict)
    assert status == "passed"
    assert len(errors) == 0


def test_invalid_reversed_validation():
    """Test 7: Verify check_target_transformation fails for invalid REVERSED."""
    rec_dict = {
        "perturbation_type": "REVERSED",
        "original_relation": {"cause": "flooding", "relation": "causes", "effect": "road closures"},
        "intended_relation": {"cause": "flooding", "relation": "causes", "effect": "road closures"},
        "perturbed_text": "Flooding caused road closures.",
    }
    status, errors = check_target_transformation(rec_dict)
    assert status == "failed"
    assert "reversal_intended_cause_mismatch" in errors


def test_valid_weakened_validation():
    """Test 8: Verify WEAKENED target transformation check."""
    rec_dict = {
        "perturbation_type": "WEAKENED",
        "original_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
        "intended_relation": {"cause": "rain", "relation": "weakened", "effect": "floods"},
        "perturbed_text": "Rain was associated with floods.",
    }
    status, errors = check_target_transformation(rec_dict)
    assert status == "passed"
    assert len(errors) == 0


def test_valid_dropped_validation():
    """Test 9: Verify DROPPED target transformation check."""
    rec_dict = {
        "perturbation_type": "DROPPED",
        "original_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
        "intended_relation": {"cause": "rain", "relation": "none", "effect": "floods"},
        "perturbed_text": "Rain and floods.",
    }
    status, errors = check_target_transformation(rec_dict)
    assert status == "passed"
    assert len(errors) == 0


def test_valid_cause_changed_validation():
    """Test 10: Verify CAUSE_CHANGED target transformation check."""
    rec_dict = {
        "perturbation_type": "CAUSE_CHANGED",
        "original_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
        "intended_relation": {"cause": "wind", "relation": "causes", "effect": "floods"},
        "perturbed_text": "Wind caused floods.",
    }
    status, errors = check_target_transformation(rec_dict)
    assert status == "passed"
    assert len(errors) == 0


def test_valid_effect_changed_validation():
    """Test 11: Verify EFFECT_CHANGED target transformation check."""
    rec_dict = {
        "perturbation_type": "EFFECT_CHANGED",
        "original_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
        "intended_relation": {"cause": "rain", "relation": "causes", "effect": "landslides"},
        "perturbed_text": "Rain caused landslides.",
    }
    status, errors = check_target_transformation(rec_dict)
    assert status == "passed"
    assert len(errors) == 0


def test_consistency_check_failure():
    """Test 12: Verify check_consistency fails when CAUSE_CHANGED has unchanged cause."""
    rec_dict = {
        "perturbation_type": "CAUSE_CHANGED",
        "original_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
        "intended_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
    }
    status, errors = check_consistency(rec_dict)
    assert status == "failed"
    assert "inconsistent_cause_unchanged" in errors


def test_deterministic_validation():
    """Test 13: Verify validator is strictly deterministic."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "s1",
        "perturbation_type": "REVERSED",
        "original_text": "Flooding caused damage.",
        "perturbed_text": "Damage caused flooding.",
        "original_relation": {"cause": "flooding", "relation": "causes", "effect": "damage"},
        "intended_relation": {"cause": "damage", "relation": "causes", "effect": "flooding"},
        "changed_span": {"original": "Flooding caused damage", "perturbed": "Damage caused flooding"},
        "generation_method": "rule_based",
    }
    res1 = validator.validate_record(rec_dict)
    res2 = validator.validate_record(rec_dict)

    assert res1 == res2


def test_large_unrelated_rewrite_must_be_invalid():
    """Test 14: Verify large unrelated context rewrite is flagged as error and invalidates record."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "s1",
        "perturbation_type": "CAUSE_CHANGED",
        "original_text": "Heavy rainfall caused flooding in the valley.",
        "perturbed_text": "The government announced major tax reforms after long debates caused flooding in the valley.",
        "original_relation": {"cause": "heavy rainfall", "relation": "causes", "effect": "flooding"},
        "intended_relation": {"cause": "tax reforms", "relation": "causes", "effect": "flooding"},
        "changed_span": {"original": "heavy rainfall", "perturbed": "The government announced major tax reforms after long debates"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "invalid"
    assert any(e in ("uncontrolled_context_rewrite", "excessive_unrelated_edit") for e in val_rec.errors)


def test_effect_changed_with_large_context_rewrite_must_be_invalid():
    """Test 15: Verify EFFECT_CHANGED with large context rewrite is invalid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "xsum_000074_pert_000010",
        "document_id": "xsum_000074",
        "summary_id": "xsum_000074_ref",
        "perturbation_type": "EFFECT_CHANGED",
        "original_text": "Work has started on a footbridge at the site of a £10m railway station where construction efforts stalled due to concerns over rare great crested newts.",
        "perturbed_text": "Ilkeston in Derbyshire is one of the largest towns in the UK without a rail station after its previous one closed in 1967 due to concerns over rare great crested newts.",
        "original_relation": {"cause": "concerns over rare great crested newts", "relation": "causes", "effect": "Work has started... stalled"},
        "intended_relation": {"cause": "concerns over rare great crested newts", "relation": "causes", "effect": "Ilkeston... closed in 1967"},
        "changed_span": {"original": "Work has started on a footbridge at the site of a £10m railway station where construction efforts stalled", "perturbed": "Ilkeston in Derbyshire is one of the largest towns in the UK without a rail station after its previous one closed in 1967"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "invalid"
    assert "excessive_unrelated_edit" in val_rec.errors or "uncontrolled_context_rewrite" in val_rec.errors


def test_cause_changed_with_large_context_rewrite_must_be_invalid():
    """Test 16: Verify CAUSE_CHANGED with large context rewrite is invalid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "xsum_000038_pert_000004",
        "document_id": "xsum_000038",
        "summary_id": "xsum_000038_ref",
        "perturbation_type": "CAUSE_CHANGED",
        "original_text": "A grade II-listed bridge in Dorset that was blamed for causing severe floods is to be dismantled and replaced.",
        "perturbed_text": "its historic status, but authorities agreed its small arches restricted the flow of the River Cerne causing severe floods is to be dismantled and replaced.",
        "original_relation": {"cause": "A grade II-listed bridge", "relation": "causes", "effect": "severe floods"},
        "intended_relation": {"cause": "small arches restricted flow", "relation": "causes", "effect": "severe floods"},
        "changed_span": {"original": "A grade II-listed bridge in Dorset that was blamed for", "perturbed": "its historic status, but authorities agreed its small arches restricted the flow of the River Cerne"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "invalid"
    assert any(e in ("uncontrolled_context_rewrite", "excessive_unrelated_edit") for e in val_rec.errors)


def test_localized_cause_substitution_remains_valid():
    """Test 17: Verify localized cause substitution remains valid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "xsum_000074_pert_000009",
        "document_id": "xsum_000074",
        "summary_id": "xsum_000074_ref",
        "perturbation_type": "CAUSE_CHANGED",
        "original_text": "Work has started on a footbridge at the site of a £10m railway station where construction efforts stalled due to concerns over rare great crested newts.",
        "perturbed_text": "Work has started on a footbridge at the site of a £10m railway station where construction efforts stalled due to Dr Beeching's cuts.",
        "original_relation": {"cause": "concerns over rare great crested newts", "relation": "causes", "effect": "Work has started on a footbridge at the site of a £10m railway station where construction efforts stalled"},
        "intended_relation": {"cause": "Dr Beeching's cuts", "relation": "causes", "effect": "Work has started on a footbridge at the site of a £10m railway station where construction efforts stalled"},
        "changed_span": {"original": "concerns over rare great crested newts", "perturbed": "Dr Beeching's cuts"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "valid"
    assert len(val_rec.errors) == 0


def test_localized_effect_substitution_remains_valid():
    """Test 18: Verify localized effect substitution remains valid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "s1",
        "perturbation_type": "EFFECT_CHANGED",
        "original_text": "Heavy rainfall caused flooding in the region.",
        "perturbed_text": "Heavy rainfall caused landslides in the region.",
        "original_relation": {"cause": "heavy rainfall", "relation": "causes", "effect": "flooding"},
        "intended_relation": {"cause": "heavy rainfall", "relation": "causes", "effect": "landslides"},
        "changed_span": {"original": "flooding", "perturbed": "landslides"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "valid"
    assert len(val_rec.errors) == 0


def test_malformed_reversal_must_be_invalid():
    """Test 19: Verify malformed reversal syntax is marked invalid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "xsum_000038_pert_000001",
        "document_id": "xsum_000038",
        "summary_id": "xsum_000038_ref",
        "perturbation_type": "REVERSED",
        "original_text": "A grade II-listed bridge in Dorset that was blamed for causing severe floods is to be dismantled and replaced.",
        "perturbed_text": "Severe floods is to be dismantled and replaced causing a grade II-listed bridge in Dorset that was blamed for.",
        "original_relation": {"cause": "A grade II-listed bridge in Dorset that was blamed for", "relation": "causes", "effect": "severe floods is to be dismantled and replaced"},
        "intended_relation": {"cause": "severe floods is to be dismantled and replaced", "relation": "causes", "effect": "A grade II-listed bridge in Dorset that was blamed for"},
        "changed_span": {"original": "A grade II-listed bridge in Dorset that was blamed for causing severe floods is to be dismantled and replaced", "perturbed": "Severe floods is to be dismantled and replaced causing a grade II-listed bridge in Dorset that was blamed for"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "invalid"
    assert "malformed_reversal_structure" in val_rec.errors


def test_localized_weakening_remains_valid():
    """Test 20: Verify localized weakening transformation remains valid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "xsum_000038_pert_000002",
        "document_id": "xsum_000038",
        "summary_id": "xsum_000038_ref",
        "perturbation_type": "WEAKENED",
        "original_text": "A grade II-listed bridge in Dorset that was blamed for causing severe floods is to be dismantled and replaced.",
        "perturbed_text": "A grade II-listed bridge in Dorset that was linked to severe floods is to be dismantled and replaced.",
        "original_relation": {"cause": "A grade II-listed bridge in Dorset that was blamed for", "relation": "causes", "effect": "severe floods is to be dismantled and replaced"},
        "intended_relation": {"cause": "A grade II-listed bridge in Dorset that was blamed for", "relation": "weakened", "effect": "severe floods is to be dismantled and replaced"},
        "changed_span": {"original": "was blamed for causing", "perturbed": "was linked to"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "valid"
    assert len(val_rec.errors) == 0


def test_localized_deletion_remains_valid():
    """Test 21: Verify localized deletion (DROPPED) transformation remains valid."""
    validator = PerturbationQualityValidator()
    rec_dict = {
        "perturbation_id": "xsum_000038_pert_000003",
        "document_id": "xsum_000038",
        "summary_id": "xsum_000038_ref",
        "perturbation_type": "DROPPED",
        "original_text": "A grade II-listed bridge in Dorset that was blamed for causing severe floods is to be dismantled and replaced.",
        "perturbed_text": "A grade II-listed bridge in Dorset that was associated with severe floods is to be dismantled and replaced.",
        "original_relation": {"cause": "A grade II-listed bridge in Dorset that was blamed for", "relation": "causes", "effect": "severe floods is to be dismantled and replaced"},
        "intended_relation": {"cause": "A grade II-listed bridge in Dorset that was blamed for", "relation": "none", "effect": "severe floods is to be dismantled and replaced"},
        "changed_span": {"original": "was blamed for causing", "perturbed": "was associated with"},
        "generation_method": "rule_based",
    }
    val_rec = validator.validate_record(rec_dict)
    assert val_rec.validation_status == "valid"
    assert len(val_rec.errors) == 0


def test_full_validation_pipeline(tmp_path: Path):
    """Test 22: Run full validation pipeline on synthetic fixture."""
    input_file = tmp_path / "perturbations.jsonl"
    out_file = tmp_path / "validated_perturbations.jsonl"
    stats_file = tmp_path / "validation_stats.json"
    sample_file = tmp_path / "sample.json"

    dummy_p1 = {
        "perturbation_id": "p1",
        "document_id": "d1",
        "summary_id": "s1",
        "perturbation_type": "WEAKENED",
        "original_text": "Rain caused floods.",
        "perturbed_text": "Rain was associated with floods.",
        "original_relation": {"cause": "rain", "relation": "causes", "effect": "floods"},
        "intended_relation": {"cause": "rain", "relation": "weakened", "effect": "floods"},
        "changed_span": {"original": "caused", "perturbed": "was associated with"},
        "generation_method": "rule_based",
        "validation_status": "valid",
        "validation_errors": [],
    }

    input_file.write_text(json.dumps(dummy_p1) + "\n", encoding="utf-8")

    cfg = AppConfig(
        paths=PathConfig(root_dir=tmp_path),
        validation=ValidationConfig(
            enabled=True,
            input_path=str(input_file),
            output_path=str(out_file),
            stats_path=str(stats_file),
            sample_path=str(sample_file),
        ),
    )

    pipeline = PerturbationValidationPipeline(config=cfg)
    stats = pipeline.run(input_jsonl=input_file)

    assert out_file.exists()
    assert stats_file.exists()
    assert sample_file.exists()

    assert stats["counts"]["records_examined"] == 1
    assert stats["counts"]["valid_records"] == 1
    assert stats["counts"]["validation_rate"] == 1.0
