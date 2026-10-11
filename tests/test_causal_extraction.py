"""Unit tests for Phase 3 causal relation extraction."""

import json
import pytest

from causalfidelity.causal.pipeline import CausalExtractionPipeline
from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.causal.schema import CausalRelation, DocumentCausalRelations
from causalfidelity.causal.validator import CausalRelationValidator
from causalfidelity.config import load_config


def test_simple_causal_sentence():
    """Verify simple forward causal pattern extraction ('caused')."""
    extractor = RuleBasedCausalExtractor()
    text = "Heavy rainfall caused flooding."
    relations = extractor.extract_relations("doc_1", text)

    assert len(relations) == 1
    rel = relations[0]
    assert rel.cause == "Heavy rainfall"
    assert rel.relation == "causes"
    assert rel.effect == "flooding"
    assert rel.confidence == 0.90
    assert rel.source_sentence == "Heavy rainfall caused flooding."


def test_reverse_grammatical_construction():
    """Verify reverse passive causal construction ('resulted from')."""
    extractor = RuleBasedCausalExtractor()
    text = "Flooding resulted from heavy rainfall."
    relations = extractor.extract_relations("doc_2", text)

    assert len(relations) == 1
    rel = relations[0]
    assert rel.cause == "heavy rainfall"
    assert rel.relation == "causes"
    assert rel.effect == "Flooding"


def test_led_to_construction():
    """Verify 'led to' causal pattern extraction."""
    extractor = RuleBasedCausalExtractor()
    text = "The storm led to widespread flooding."
    relations = extractor.extract_relations("doc_3", text)

    assert len(relations) == 1
    rel = relations[0]
    assert rel.cause == "The storm"
    assert rel.relation == "causes"
    assert rel.effect == "widespread flooding"


def test_due_to_construction():
    """Verify 'due to' causal pattern extraction."""
    extractor = RuleBasedCausalExtractor()
    text = "The disruption was due to the storm."
    relations = extractor.extract_relations("doc_4", text)

    assert len(relations) == 1
    rel = relations[0]
    assert rel.cause == "the storm"
    assert rel.relation == "causes"
    assert rel.effect == "The disruption"


def test_because_construction():
    """Verify 'because of' causal pattern extraction."""
    extractor = RuleBasedCausalExtractor()
    text = "The match was delayed because of heavy rain."
    relations = extractor.extract_relations("doc_5", text)

    assert len(relations) == 1
    rel = relations[0]
    assert rel.cause == "heavy rain"
    assert rel.relation == "causes"
    assert rel.effect == "The match was delayed"


def test_temporal_since_false_positive():
    """Verify that purely temporal 'since' statements do NOT produce a causal relation."""
    extractor = RuleBasedCausalExtractor()
    text = "Since Tuesday, the team has worked."
    relations = extractor.extract_relations("doc_6", text)

    assert len(relations) == 0


def test_negated_causal_statement():
    """Verify that negated causal statements are filtered out."""
    extractor = RuleBasedCausalExtractor()
    text = "There was no evidence that rainfall caused flooding."
    relations = extractor.extract_relations("doc_7", text)

    assert len(relations) == 0


def test_empty_invalid_relation_validation():
    """Verify validator rejection of invalid/empty relations."""
    validator = CausalRelationValidator()

    # Empty cause
    invalid_rel = CausalRelation(
        relation_id="rel_01",
        document_id="doc_8",
        cause="",
        relation="causes",
        effect="flooding",
        source_sentence="Invalid cause test.",
    )
    is_valid, reason = validator.validate_relation(invalid_rel)
    assert is_valid is False
    assert "Empty cause text" in reason

    # Invalid relation verb
    invalid_rel_verb = CausalRelation(
        relation_id="rel_02",
        document_id="doc_8",
        cause="Rain",
        relation="associated_with",
        effect="flooding",
        source_sentence="Rain caused flooding.",
    )
    is_valid, reason = validator.validate_relation(invalid_rel_verb)
    assert is_valid is False
    assert "Invalid relation" in reason


def test_multiple_relations_in_sentence():
    """Verify extraction of multiple causal relations within a compound sentence."""
    extractor = RuleBasedCausalExtractor()
    text = "Heavy rainfall caused flooding, which led to road closures."
    relations = extractor.extract_relations("doc_9", text)

    assert len(relations) >= 2
    rel1 = relations[0]
    rel2 = relations[1]

    assert rel1.cause == "Heavy rainfall"
    assert rel1.effect == "flooding"
    assert rel2.cause == "flooding"
    assert rel2.effect == "road closures"


def test_pipeline_on_synthetic_dataset(tmp_path):
    """Verify end-to-end Phase 3 pipeline on a synthetic Phase 2 fixture."""
    dev_records = [
        {
            "document_id": "xsum_000001",
            "domain": "news",
            "source_text": "Heavy rainfall caused flooding in the valley.",
            "reference_summary": "Rainfall caused flooding.",
            "causal_candidate": True,
        },
        {
            "document_id": "xsum_000002",
            "domain": "news",
            "source_text": "Since Tuesday, the committee has been holding interviews.",
            "reference_summary": "Committee held interviews.",
            "causal_candidate": True,
        },
    ]

    input_jsonl = tmp_path / "xsum_dev.jsonl"
    with open(input_jsonl, "w", encoding="utf-8") as f:
        for rec in dev_records:
            f.write(json.dumps(rec) + "\n")

    config = load_config()
    config.paths.root_dir = tmp_path
    config.causal_extraction.output_file = "data/processed/causal_relations.jsonl"
    config.causal_extraction.stats_file = "data/processed/causal_relations_stats.json"
    config.causal_extraction.sample_output_file = "outputs/results/phase3_extraction_sample.json"

    pipeline = CausalExtractionPipeline(config=config)
    stats = pipeline.run(input_jsonl=input_jsonl)

    assert stats["counts"]["total_documents_processed"] == 2
    assert stats["counts"]["documents_with_relations"] == 1
    assert stats["counts"]["documents_with_zero_relations"] == 1
    assert stats["counts"]["total_relations_extracted"] == 1

    # Check output files creation
    output_jsonl = tmp_path / "data/processed/causal_relations.jsonl"
    output_stats = tmp_path / "data/processed/causal_relations_stats.json"
    output_sample = tmp_path / "outputs/results/phase3_extraction_sample.json"

    assert output_jsonl.exists()
    assert output_stats.exists()
    assert output_sample.exists()

    # Verify JSONL lines preserve both documents
    lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    doc1_data = json.loads(lines[0])
    doc2_data = json.loads(lines[1])

    assert doc1_data["document_id"] == "xsum_000001"
    assert len(doc1_data["relations"]) == 1
    assert doc1_data["relations"][0]["relation_id"] == "rel_000001"

    assert doc2_data["document_id"] == "xsum_000002"
    assert len(doc2_data["relations"]) == 0
