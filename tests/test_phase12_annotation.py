"""Unit tests for Phase 12 Step 1 Annotation Schema & Batch Ingestion Pipeline."""

import csv
import json
import pytest
from pathlib import Path

from causalfidelity.annotation.schema import (
    APPROVED_CAUSAL_LABELS,
    AnnotationRecord,
    validate_annotation_dict,
)
from causalfidelity.annotation.loader import AnnotationLoader, IngestionResult


def test_1_valid_annotation_record():
    """Test 1: Valid annotation record passes schema validation."""
    data = {
        "annotation_id": "ann_001",
        "perturbation_id": "xsum_000001_pert_000001",
        "annotator_id": "user_a",
        "causal_label": "Reversed",
        "naturalness_rating": 4,
        "comments": "Accurate reversal label.",
    }
    is_valid, errors = validate_annotation_dict(data)
    assert is_valid is True
    assert len(errors) == 0

    record = AnnotationRecord.from_dict(data)
    assert record.annotation_id == "ann_001"
    assert record.causal_label == "Reversed"
    assert record.naturalness_rating == 4


def test_2_missing_required_fields():
    """Test 2: Validation fails when required fields are missing or empty."""
    data_no_ann_id = {
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "Faithful",
        "naturalness_rating": 5,
    }
    is_valid, errors = validate_annotation_dict(data_no_ann_id)
    assert is_valid is False
    assert "missing_annotation_id" in errors

    data_empty_pert_id = {
        "annotation_id": "ann_002",
        "perturbation_id": "   ",
        "annotator_id": "user_a",
        "causal_label": "Weakened",
        "naturalness_rating": 3,
    }
    is_valid, errors = validate_annotation_dict(data_empty_pert_id)
    assert is_valid is False
    assert "missing_perturbation_id" in errors


def test_3_invalid_causal_label():
    """Test 3: Unapproved or mis-cased causal labels are rejected."""
    data_bad_label = {
        "annotation_id": "ann_003",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "InvalidLabel",
        "naturalness_rating": 3,
    }
    is_valid, errors = validate_annotation_dict(data_bad_label)
    assert is_valid is False
    assert any("invalid_causal_label" in e for e in errors)

    data_case_sensitive = {
        "annotation_id": "ann_004",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "reversed",  # Lowercase is unapproved
        "naturalness_rating": 4,
    }
    is_valid, errors = validate_annotation_dict(data_case_sensitive)
    assert is_valid is False
    assert any("invalid_causal_label" in e for e in errors)


def test_4_naturalness_rating_below_1():
    """Test 4: Naturalness ratings < 1 are rejected."""
    data = {
        "annotation_id": "ann_005",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "Faithful",
        "naturalness_rating": 0,
    }
    is_valid, errors = validate_annotation_dict(data)
    assert is_valid is False
    assert "naturalness_rating_below_min" in errors


def test_5_naturalness_rating_above_5():
    """Test 5: Naturalness ratings > 5 are rejected."""
    data = {
        "annotation_id": "ann_006",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "Dropped",
        "naturalness_rating": 6,
    }
    is_valid, errors = validate_annotation_dict(data)
    assert is_valid is False
    assert "naturalness_rating_above_max" in errors


def test_6_non_integer_naturalness_rating():
    """Test 6: Non-integer naturalness ratings (floats, non-numeric strings, bools) are rejected."""
    data_float = {
        "annotation_id": "ann_007",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "Cause_Changed",
        "naturalness_rating": 3.5,
    }
    is_valid, errors = validate_annotation_dict(data_float)
    assert is_valid is False
    assert "non_integer_naturalness_rating" in errors

    data_string_float = {
        "annotation_id": "ann_008",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "Effect_Changed",
        "naturalness_rating": "3.5",
    }
    is_valid, errors = validate_annotation_dict(data_string_float)
    assert is_valid is False
    assert "non_integer_naturalness_rating" in errors

    data_bool = {
        "annotation_id": "ann_009",
        "perturbation_id": "pert_001",
        "annotator_id": "user_a",
        "causal_label": "Faithful",
        "naturalness_rating": True,
    }
    is_valid, errors = validate_annotation_dict(data_bool)
    assert is_valid is False
    assert "non_integer_naturalness_rating" in errors


def test_7_valid_jsonl_ingestion(tmp_path):
    """Test 7: JSONL ingestion parses and validates valid records correctly."""
    records = [
        {
            "annotation_id": "ann_jsonl_001",
            "perturbation_id": "pert_001",
            "annotator_id": "user_a",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "ann_jsonl_002",
            "perturbation_id": "pert_001",
            "annotator_id": "user_b",
            "causal_label": "Weakened",
            "naturalness_rating": 4,
        },
    ]
    file_path = tmp_path / "valid.jsonl"
    with open(file_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    loader = AnnotationLoader()
    result = loader.load_jsonl(file_path)

    assert len(result.valid_records) == 2
    assert len(result.invalid_records) == 0
    assert result.summary["valid_records_count"] == 2
    assert result.valid_records[0].annotation_id == "ann_jsonl_001"
    assert result.valid_records[1].causal_label == "Weakened"


def test_8_valid_csv_ingestion(tmp_path):
    """Test 8: CSV ingestion parses and validates valid records correctly."""
    fieldnames = ["annotation_id", "perturbation_id", "annotator_id", "causal_label", "naturalness_rating", "comments"]
    records = [
        {
            "annotation_id": "ann_csv_001",
            "perturbation_id": "pert_002",
            "annotator_id": "user_a",
            "causal_label": "Dropped",
            "naturalness_rating": "3",
            "comments": "Good non-causal rewrite",
        },
        {
            "annotation_id": "ann_csv_002",
            "perturbation_id": "pert_002",
            "annotator_id": "user_b",
            "causal_label": "Dropped",
            "naturalness_rating": "4",
            "comments": "Concur with user_a",
        },
    ]

    file_path = tmp_path / "valid.csv"
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    loader = AnnotationLoader()
    result = loader.load_csv(file_path)

    assert len(result.valid_records) == 2
    assert len(result.invalid_records) == 0
    assert result.summary["valid_records_count"] == 2
    assert result.valid_records[0].naturalness_rating == 3


def test_9_malformed_jsonl_record(tmp_path):
    """Test 9: Malformed JSON syntax in JSONL is reported with line number."""
    file_path = tmp_path / "malformed.jsonl"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('{"annotation_id": "ann_010", "perturbation_id": "p1", "annotator_id": "u1", "causal_label": "Faithful", "naturalness_rating": 5}\n')
        f.write('{bad json syntax line 2\n')

    loader = AnnotationLoader()
    result = loader.load_jsonl(file_path)

    assert len(result.valid_records) == 1
    assert len(result.invalid_records) == 1
    assert result.invalid_records[0]["line_number"] == 2
    assert any("malformed_json_syntax" in e for e in result.invalid_records[0]["errors"])


def test_10_missing_csv_fields(tmp_path):
    """Test 10: Missing required CSV columns are detected and reported in summary."""
    file_path = tmp_path / "bad_headers.csv"
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["annotation_id", "perturbation_id"])  # Missing annotator_id, causal_label, naturalness_rating
        writer.writerow(["ann_011", "pert_001"])

    loader = AnnotationLoader()
    result = loader.load_csv(file_path)

    assert len(result.valid_records) == 0
    assert len(result.invalid_records) == 1
    assert any("missing_csv_columns" in e for e in result.invalid_records[0]["errors"])


def test_11_duplicate_annotation_ids(tmp_path):
    """Test 11: Duplicate annotation_id in batch is flagged as error."""
    records = [
        {
            "annotation_id": "dup_ann_001",
            "perturbation_id": "pert_001",
            "annotator_id": "user_a",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "dup_ann_001",  # Same annotation_id
            "perturbation_id": "pert_002",
            "annotator_id": "user_b",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
    ]
    file_path = tmp_path / "dup_id.jsonl"
    with open(file_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    loader = AnnotationLoader()
    result = loader.load_jsonl(file_path)

    assert len(result.valid_records) == 1
    assert len(result.invalid_records) == 1
    assert result.summary["duplicate_annotation_ids"] == 1
    assert any("duplicate_annotation_id" in e for e in result.invalid_records[0]["errors"])


def test_12_duplicate_annotator_item_combinations(tmp_path):
    """Test 12: Duplicate (annotator_id, perturbation_id) pair in batch is flagged as error."""
    records = [
        {
            "annotation_id": "ann_101",
            "perturbation_id": "pert_001",
            "annotator_id": "user_a",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "ann_102",
            "perturbation_id": "pert_001",
            "annotator_id": "user_a",  # Same annotator + pert_id combination
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
    ]
    file_path = tmp_path / "dup_pair.jsonl"
    with open(file_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    loader = AnnotationLoader()
    result = loader.load_jsonl(file_path)

    assert len(result.valid_records) == 1
    assert len(result.invalid_records) == 1
    assert result.summary["duplicate_annotator_item_pairs"] == 1
    assert any("duplicate_annotator_item_pair" in e for e in result.invalid_records[0]["errors"])


def test_13_mixed_valid_and_invalid_records(tmp_path):
    """Test 13: Ingestion preserves valid records while logging all invalid records."""
    records = [
        {
            "annotation_id": "ann_201",
            "perturbation_id": "pert_001",
            "annotator_id": "user_a",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "ann_202",
            "perturbation_id": "pert_001",
            "annotator_id": "user_b",
            "causal_label": "Invalid_Label",  # Invalid
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "ann_203",
            "perturbation_id": "pert_002",
            "annotator_id": "user_a",
            "causal_label": "Weakened",
            "naturalness_rating": 10,  # Invalid
        },
    ]
    file_path = tmp_path / "mixed.jsonl"
    with open(file_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    loader = AnnotationLoader()
    result = loader.load_jsonl(file_path)

    assert len(result.valid_records) == 1
    assert len(result.invalid_records) == 2
    assert result.valid_records[0].annotation_id == "ann_201"
    assert result.invalid_records[0]["line_number"] == 2
    assert result.invalid_records[1]["line_number"] == 3


def test_14_empty_input_files(tmp_path):
    """Test 14: Empty JSONL and CSV files return empty IngestionResult without errors."""
    empty_jsonl = tmp_path / "empty.jsonl"
    empty_jsonl.write_text("", encoding="utf-8")

    loader = AnnotationLoader()
    res_jsonl = loader.load_jsonl(empty_jsonl)
    assert len(res_jsonl.valid_records) == 0
    assert len(res_jsonl.invalid_records) == 0
    assert res_jsonl.summary["total_records_processed"] == 0

    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")

    res_csv = loader.load_csv(empty_csv)
    assert len(res_csv.valid_records) == 0
    assert res_csv.summary["total_records_processed"] == 0
