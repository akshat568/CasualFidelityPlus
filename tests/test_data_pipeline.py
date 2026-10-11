"""Unit tests for Phase 2 dataset, cleaning, validation, candidate filter, and pipeline."""

import json
import pytest

from causalfidelity.config import AppConfig, DatasetConfig, load_config
from causalfidelity.data.cleaner import TextCleaner
from causalfidelity.data.filter import CausalCandidateFilter
from causalfidelity.data.pipeline import XSumPipeline
from causalfidelity.data.sampler import DeterministicSampler
from causalfidelity.data.schema import CanonicalRecord, RecordMetadata
from causalfidelity.data.validator import DuplicateTracker, RecordValidator


def test_canonical_record_schema():
    """Verify CanonicalRecord serialization and deserialization."""
    record = CanonicalRecord(
        document_id="xsum_000001",
        domain="news",
        source_text="Heavy rainfall caused severe flooding in the valley.",
        reference_summary="Heavy rainfall caused flooding.",
        causal_candidate=True,
        metadata=RecordMetadata(
            dataset="xsum",
            original_id="1001",
            split="train",
            language="en",
        ),
    )

    data_dict = record.to_dict()
    assert data_dict["document_id"] == "xsum_000001"
    assert data_dict["domain"] == "news"
    assert data_dict["causal_candidate"] is True
    assert data_dict["metadata"]["original_id"] == "1001"

    reconstructed = CanonicalRecord.from_dict(data_dict)
    assert reconstructed.document_id == record.document_id
    assert reconstructed.source_text == record.source_text
    assert reconstructed.causal_candidate == record.causal_candidate
    assert reconstructed.metadata.original_id == record.metadata.original_id


def test_text_cleaner():
    """Verify conservative text cleaning and normalization."""
    raw_text = "  Heavy   rainfall\r\ncaused \t flooding.\n\n\n\n  "
    cleaned = TextCleaner.clean_text(raw_text)

    assert "  " not in cleaned
    assert "\r" not in cleaned
    assert cleaned == "Heavy rainfall\ncaused flooding."

    raw_rec = {
        "original_id": "1",
        "source_text": "  Text \t line 1.\r\n  ",
        "reference_summary": " Summary   text.  ",
    }
    cleaned_rec = TextCleaner.clean_raw_record(raw_rec)
    assert cleaned_rec["source_text"] == "Text line 1."
    assert cleaned_rec["reference_summary"] == "Summary text."


def test_record_validator():
    """Verify RecordValidator rules and rejection messages."""
    validator = RecordValidator(expected_domain="news", expected_dataset="xsum", expected_language="en")

    valid_rec = CanonicalRecord(
        document_id="xsum_001",
        domain="news",
        source_text="Valid document source text.",
        reference_summary="Valid summary text.",
        metadata=RecordMetadata(dataset="xsum", original_id="101", language="en"),
    )
    is_valid, reason = validator.validate_record(valid_rec)
    assert is_valid is True
    assert reason is None

    # Empty document test
    empty_doc_rec = CanonicalRecord(
        document_id="xsum_002",
        domain="news",
        source_text="   ",
        reference_summary="Summary.",
        metadata=RecordMetadata(dataset="xsum", original_id="102", language="en"),
    )
    is_valid, reason = validator.validate_record(empty_doc_rec)
    assert is_valid is False
    assert "Empty source_text" in reason


def test_duplicate_tracker():
    """Verify duplicate detection by ID and content hashing."""
    tracker = DuplicateTracker()

    is_dup, _ = tracker.is_duplicate("id_1", "Source text one.", "Summary one.")
    assert is_dup is False

    tracker.register("id_1", "Source text one.", "Summary one.")

    # Same original ID duplicate
    is_dup_id, dup_type = tracker.is_duplicate("id_1", "Different text.", "Different summary.")
    assert is_dup_id is True
    assert dup_type == "duplicate_original_id"

    # Same content duplicate with different ID
    is_dup_content, dup_type_c = tracker.is_duplicate("id_2", "Source text one.", "Summary one.")
    assert is_dup_content is True
    assert dup_type_c == "duplicate_content"


def test_causal_candidate_filter():
    """Verify candidate causal language phrase matching."""
    causal_filter = CausalCandidateFilter(phrases=["caused", "led to", "resulted in", "because"])

    assert causal_filter.is_causal_candidate("Heavy rainfall caused flooding.") is True
    assert causal_filter.is_causal_candidate("Poor maintenance led to engine failure.") is True
    assert causal_filter.is_causal_candidate("The event was cancelled because of snow.") is True

    # Non-causal sentences
    assert causal_filter.is_causal_candidate("The prime minister visited London on Tuesday.") is False
    assert causal_filter.is_causal_candidate("A new art gallery opened in the city center.") is False

    # Check match list
    matches = causal_filter.matched_phrases("Heavy rainfall caused flooding which led to closures.")
    assert "caused" in matches
    assert "led to" in matches


def test_deterministic_sampler():
    """Verify reproducible sampling with fixed seed."""
    items = [f"item_{i}" for i in range(100)]
    sampler1 = DeterministicSampler(seed=42)
    sampler2 = DeterministicSampler(seed=42)
    sampler3 = DeterministicSampler(seed=999)

    sample1 = sampler1.sample(items, sample_size=10)
    sample2 = sampler2.sample(items, sample_size=10)
    sample3 = sampler3.sample(items, sample_size=10)

    assert len(sample1) == 10
    assert sample1 == sample2  # Identical seed yields identical sampling
    assert sample1 != sample3  # Different seed yields different sampling order


def test_pipeline_on_synthetic_fixture(tmp_path):
    """Verify end-to-end pipeline execution on a local synthetic fixture."""
    synthetic_records = [
        {
            "original_id": "orig_1",
            "source_text": "Heavy rainfall caused flooding in the region.",
            "reference_summary": "Rainfall caused flooding.",
        },
        {
            "original_id": "orig_2",
            "source_text": "The government announced a new healthcare initiative.",
            "reference_summary": "Healthcare initiative announced.",
        },
        {
            "original_id": "orig_3",
            "source_text": "High temperatures led to wildfires across the state.",
            "reference_summary": "Wildfires triggered by heat.",
        },
        {
            "original_id": "orig_1",  # Duplicate ID
            "source_text": "Heavy rainfall caused flooding in the region.",
            "reference_summary": "Rainfall caused flooding.",
        },
        {
            "original_id": "orig_5",
            "source_text": "",  # Empty document
            "reference_summary": "Invalid summary.",
        },
    ]

    # Create temporary config
    config = load_config()
    config.paths.processed_data_dir = tmp_path / "processed"
    config.dataset.development_sample_size = 2
    config.dataset.random_seed = 42

    pipeline = XSumPipeline(config=config)
    stats = pipeline.run(raw_stream=synthetic_records)

    assert stats["counts"]["total_records_examined"] == 5
    assert stats["counts"]["total_invalid_records"] == 1
    assert stats["counts"]["total_duplicate_records"] == 1
    assert stats["counts"]["final_development_dataset_size"] == 2

    # Check created output files
    output_jsonl = tmp_path / "processed" / "xsum_dev.jsonl"
    output_stats = tmp_path / "processed" / "xsum_dev_stats.json"

    assert output_jsonl.exists()
    assert output_stats.exists()

    # Inspect JSONL contents
    lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    rec1 = json.loads(lines[0])
    assert rec1["document_id"].startswith("xsum_")
    assert rec1["domain"] == "news"
    assert "metadata" in rec1
