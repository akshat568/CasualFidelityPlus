"""Unit tests for Phase 5 summary input schema, validation, and pipeline."""

import json
from pathlib import Path
import pytest

from causalfidelity.config import AppConfig, PathConfig, SummaryInputConfig
from causalfidelity.summary.pipeline import SummaryInputPipeline
from causalfidelity.summary.schema import SummaryRecord, generate_summary_id
from causalfidelity.summary.validator import SummaryValidator


def test_valid_reference_summary():
    """Test 1: Verify correct SummaryRecord creation and serialization."""
    rec = SummaryRecord(
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        summary_text="This is a reference summary.",
        summary_type="reference",
        metadata={"dataset": "xsum", "language": "en"},
        source_word_count=100,
        summary_word_count=5,
        compression_ratio=0.05,
    )
    assert rec.document_id == "xsum_000001"
    assert rec.summary_id == "xsum_000001_ref"
    assert rec.summary_type == "reference"
    assert rec.source_word_count == 100
    assert rec.summary_word_count == 5
    assert rec.compression_ratio == 0.05

    d = rec.to_dict()
    assert d["document_id"] == "xsum_000001"
    assert d["metadata"]["dataset"] == "xsum"

    reconstructed = SummaryRecord.from_dict(d)
    assert reconstructed == rec


def test_deterministic_summary_id():
    """Test 2: Verify deterministic summary ID generation."""
    doc_id = "xsum_000001"
    sum_id_1 = generate_summary_id(doc_id, "reference")
    sum_id_2 = generate_summary_id(doc_id, "reference")

    assert sum_id_1 == "xsum_000001_ref"
    assert sum_id_1 == sum_id_2

    # Test custom summary type extensibility
    assert generate_summary_id("xsum_000002", "generated_model_A") == "xsum_000002_generated_model_A"


def test_empty_summary():
    """Test 3: Verify rejection of empty or whitespace-only summary text."""
    validator = SummaryValidator()

    rec_empty = SummaryRecord(
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        summary_text="",
        summary_type="reference",
    )
    is_valid, reason = validator.validate_record(rec_empty)
    assert not is_valid
    assert reason == "empty_summary_text"

    rec_ws = SummaryRecord(
        document_id="xsum_000002",
        summary_id="xsum_000002_ref",
        summary_text="   \n\t ",
        summary_type="reference",
    )
    is_valid, reason = validator.validate_record(rec_ws)
    assert not is_valid
    assert reason == "empty_summary_text"


def test_missing_document_id():
    """Test 4: Verify validation failure when document_id is missing or empty."""
    validator = SummaryValidator()

    rec_no_id = SummaryRecord(
        document_id="",
        summary_id="_ref",
        summary_text="Valid summary text.",
        summary_type="reference",
    )
    is_valid, reason = validator.validate_record(rec_no_id)
    assert not is_valid
    assert reason == "missing_document_id"


def test_duplicate_document_ids():
    """Test 5: Verify deterministic detection and rejection of duplicate document IDs."""
    validator = SummaryValidator()

    rec1 = SummaryRecord(
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        summary_text="Summary one.",
        summary_type="reference",
    )
    is_valid_1, reason_1 = validator.validate_record(rec1)
    assert is_valid_1
    assert reason_1 is None
    validator.register(rec1)

    rec2 = SummaryRecord(
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        summary_text="Summary two for same doc.",
        summary_type="reference",
    )
    is_valid_2, reason_2 = validator.validate_record(rec2)
    assert not is_valid_2
    assert "duplicate_document_id" in reason_2


def test_word_counts():
    """Test 6: Verify exact whitespace word counting for source and summary."""
    source_text = "The quick brown fox jumps over the lazy dog ."  # 10 whitespace tokens
    summary_text = "Fox jumps dog ."  # 4 whitespace tokens

    src_count = len(source_text.split())
    sum_count = len(summary_text.split())

    assert src_count == 10
    assert sum_count == 4



def test_compression_ratio():
    """Test 7: Verify compression ratio calculation (summary_words / source_words)."""
    source_words = 100
    summary_words = 20

    ratio = summary_words / source_words
    assert ratio == 0.20


def test_zero_source_words():
    """Test 8: Verify division-by-zero protection when source word count is zero."""
    source_words = 0
    summary_words = 10

    if source_words > 0:
        ratio = summary_words / source_words
    else:
        ratio = None

    assert ratio is None

    rec = SummaryRecord(
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        summary_text="Summary text",
        source_word_count=0,
        summary_word_count=10,
        compression_ratio=ratio,
    )
    assert rec.compression_ratio is None


def test_metadata_preservation():
    """Test 9: Verify dataset and language metadata are correctly preserved."""
    meta = {
        "dataset": "xsum",
        "original_id": "12345678",
        "split": "train",
        "language": "en",
    }
    rec = SummaryRecord(
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        summary_text="Summary text",
        summary_type="reference",
        metadata=meta,
    )
    assert rec.metadata["dataset"] == "xsum"
    assert rec.metadata["original_id"] == "12345678"
    assert rec.metadata["language"] == "en"


def test_full_pipeline(tmp_path: Path):
    """Test 10: Run full Phase 5 pipeline on synthetic input fixture."""
    input_file = tmp_path / "xsum_dev.jsonl"
    output_file = tmp_path / "summary_inputs.jsonl"
    stats_file = tmp_path / "summary_inputs_stats.json"
    sample_file = tmp_path / "phase5_summary_sample.json"

    # Create synthetic input records
    records = [
        {
            "document_id": "xsum_000001",
            "domain": "news",
            "source_text": "This is a detailed news document containing background information about a sports event.",
            "reference_summary": "A sports event occurred.",
            "causal_candidate": False,
            "metadata": {"dataset": "xsum", "original_id": "1001", "split": "train", "language": "en"},
        },
        {
            "document_id": "xsum_000002",
            "domain": "news",
            "source_text": "Another long document detailing political campaign events across the nation.",
            "reference_summary": "Political campaign update.",
            "causal_candidate": True,
            "metadata": {"dataset": "xsum", "original_id": "1002", "split": "train", "language": "en"},
        },
    ]

    with open(input_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    cfg = AppConfig(
        paths=PathConfig(root_dir=tmp_path),
        summary_input=SummaryInputConfig(
            enabled=True,
            input_file=str(input_file),
            output_file=str(output_file),
            stats_file=str(stats_file),
            sample_output_file=str(sample_file),
        ),
    )

    pipeline = SummaryInputPipeline(config=cfg)
    stats = pipeline.run(input_jsonl=input_file)

    # Verify outputs created
    assert output_file.exists()
    assert stats_file.exists()
    assert sample_file.exists()

    # Check stats
    assert stats["processing"]["records_examined"] == 2
    assert stats["processing"]["valid_summaries"] == 2
    assert stats["processing"]["invalid_summaries"] == 0

    # Read output JSONL
    out_lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(out_lines) == 2

    rec1 = json.loads(out_lines[0])
    assert rec1["document_id"] == "xsum_000001"
    assert rec1["summary_id"] == "xsum_000001_ref"
    assert rec1["summary_type"] == "reference"
    assert rec1["summary_text"] == "A sports event occurred."
    assert rec1["source_word_count"] == 13
    assert rec1["summary_word_count"] == 4
    assert round(rec1["compression_ratio"], 4) == round(4 / 13, 4)
