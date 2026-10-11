"""Unit tests for Phase 6 controlled causal perturbation engine."""

import json
from pathlib import Path
import pytest

from causalfidelity.causal.schema import CausalRelation
from causalfidelity.config import AppConfig, PathConfig, PerturbationConfig
from causalfidelity.perturbation.generator import PerturbationGenerator
from causalfidelity.perturbation.pipeline import PerturbationPipeline
from causalfidelity.perturbation.schema import PerturbationRecord, generate_perturbation_id
from causalfidelity.perturbation.strategies import (
    CauseSubstitutionStrategy,
    DeletionStrategy,
    EffectSubstitutionStrategy,
    ReversalStrategy,
    WeakeningStrategy,
)
from causalfidelity.perturbation.validator import PerturbationValidator


def test_valid_perturbation_schema():
    """Test 1: Verify correct PerturbationRecord creation and serialization."""
    rec = PerturbationRecord(
        perturbation_id="xsum_000001_pert_000001",
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        perturbation_type="REVERSED",
        original_text="Heavy rainfall caused flooding.",
        perturbed_text="Flooding caused heavy rainfall.",
        original_relation={"cause": "heavy rainfall", "relation": "causes", "effect": "flooding"},
        intended_relation={"cause": "flooding", "relation": "causes", "effect": "heavy rainfall"},
        changed_span={"original": "Heavy rainfall caused flooding.", "perturbed": "Flooding caused heavy rainfall."},
        generation_method="rule_based",
        validation_status="valid",
        validation_errors=[],
    )
    assert rec.perturbation_id == "xsum_000001_pert_000001"
    assert rec.perturbation_type == "REVERSED"

    d = rec.to_dict()
    assert d["perturbation_id"] == "xsum_000001_pert_000001"
    assert d["intended_relation"]["cause"] == "flooding"

    reconstructed = PerturbationRecord.from_dict(d)
    assert reconstructed == rec


def test_deterministic_perturbation_id():
    """Test 2: Verify deterministic perturbation ID generation."""
    p_id_1 = generate_perturbation_id("xsum_000001", 1)
    p_id_2 = generate_perturbation_id("xsum_000001", 1)

    assert p_id_1 == "xsum_000001_pert_000001"
    assert p_id_1 == p_id_2
    assert generate_perturbation_id("xsum_000042", 15) == "xsum_000042_pert_000015"


def test_reversal_strategy():
    """Test 3: Verify ReversalStrategy cause/effect swap."""
    strategy = ReversalStrategy()
    text = "Heavy rainfall caused flooding in the valley."
    res = strategy.apply(text, cause="heavy rainfall", relation="causes", effect="flooding")

    assert res is not None
    perturbed_text, intended_rel, span_dict = res

    assert "flooding caused heavy rainfall" in perturbed_text.lower()
    assert intended_rel["cause"] == "flooding"
    assert intended_rel["effect"] == "heavy rainfall"


def test_weakening_strategy():
    """Test 4: Verify WeakeningStrategy replaces strong causal trigger with associative phrase."""
    strategy = WeakeningStrategy()
    text = "Heavy rainfall caused flooding in the valley."
    res = strategy.apply(text, cause="heavy rainfall", relation="causes", effect="flooding")

    assert res is not None
    perturbed_text, intended_rel, span_dict = res

    assert "was associated with" in perturbed_text.lower()
    assert intended_rel["relation"] == "weakened"


def test_deletion_strategy():
    """Test 5: Verify DeletionStrategy removes explicit causal trigger (DROPPED)."""
    strategy = DeletionStrategy()
    text = "Heavy rainfall caused flooding in the valley."
    res = strategy.apply(text, cause="heavy rainfall", relation="causes", effect="flooding")

    assert res is not None
    perturbed_text, intended_rel, span_dict = res

    assert intended_rel["relation"] == "none"
    assert "heavy rainfall" in perturbed_text.lower()
    assert "flooding" in perturbed_text.lower()


def test_cause_substitution():
    """Test 6: Verify CauseSubstitutionStrategy using valid context candidate."""
    strategy = CauseSubstitutionStrategy()
    text = "Heavy rainfall caused flooding in the region."
    context = {"candidate_causes": ["Strong winds", "Severe storm"]}

    res = strategy.apply(text, cause="heavy rainfall", relation="causes", effect="flooding", context_candidates=context)

    assert res is not None
    perturbed_text, intended_rel, span_dict = res

    assert "Strong winds caused flooding" in perturbed_text
    assert intended_rel["cause"] == "Strong winds"
    assert intended_rel["effect"] == "flooding"


def test_effect_substitution():
    """Test 7: Verify EffectSubstitutionStrategy using valid context candidate."""
    strategy = EffectSubstitutionStrategy()
    text = "Heavy rainfall caused flooding in the region."
    context = {"candidate_effects": ["landslides", "power outages"]}

    res = strategy.apply(text, cause="heavy rainfall", relation="causes", effect="flooding", context_candidates=context)

    assert res is not None
    perturbed_text, intended_rel, span_dict = res

    assert "Heavy rainfall caused landslides" in perturbed_text
    assert intended_rel["cause"] == "heavy rainfall"
    assert intended_rel["effect"] == "landslides"


def test_invalid_perturbation_rejection():
    """Test 8: Verify PerturbationValidator rejects invalid records."""
    validator = PerturbationValidator()

    # Missing document_id
    rec_bad = PerturbationRecord(
        perturbation_id="pert_001",
        document_id="",
        summary_id="sum_001",
        perturbation_type="REVERSED",
        original_text="A caused B",
        perturbed_text="B caused A",
        original_relation={"cause": "A", "relation": "causes", "effect": "B"},
        intended_relation={"cause": "B", "relation": "causes", "effect": "A"},
    )
    is_valid, errors = validator.validate(rec_bad)
    assert not is_valid
    assert "missing_document_id" in errors


def test_missing_replacement_candidate():
    """Test 9: Verify Cause/Effect substitution returns None when context candidates are missing."""
    cause_strat = CauseSubstitutionStrategy()
    effect_strat = EffectSubstitutionStrategy()

    text = "Heavy rainfall caused flooding."
    empty_context = {"candidate_causes": [], "candidate_effects": []}

    res_cause = cause_strat.apply(text, cause="heavy rainfall", relation="causes", effect="flooding", context_candidates=empty_context)
    res_effect = effect_strat.apply(text, cause="heavy rainfall", relation="causes", effect="flooding", context_candidates=empty_context)

    assert res_cause is None
    assert res_effect is None


def test_validation_errors():
    """Test 10: Verify specific error code collection in validator."""
    validator = PerturbationValidator()

    # REVERSED type where cause/effect swap was not performed correctly
    rec_bad_reversal = PerturbationRecord(
        perturbation_id="xsum_000001_pert_000001",
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        perturbation_type="REVERSED",
        original_text="A caused B",
        perturbed_text="A caused B",
        original_relation={"cause": "A", "relation": "causes", "effect": "B"},
        intended_relation={"cause": "A", "relation": "causes", "effect": "B"},
    )
    is_valid, errors = validator.validate(rec_bad_reversal)
    assert not is_valid
    assert "reversal_intended_cause_mismatch" in errors
    assert "reversal_intended_effect_mismatch" in errors


def test_summary_eligibility_matching():
    """Test 11: Verify summary-level eligibility matching logic."""
    generator = PerturbationGenerator()

    summary_text = "Flooding was caused by heavy rainfall in the western district."

    rel_present = CausalRelation(
        relation_id="rel_01",
        document_id="xsum_000001",
        cause="heavy rainfall",
        relation="causes",
        effect="flooding",
    )

    rel_absent = CausalRelation(
        relation_id="rel_02",
        document_id="xsum_000001",
        cause="volcanic eruption",
        relation="causes",
        effect="earthquake",
    )

    assert generator.is_relation_explicitly_in_summary(summary_text, rel_present) is True
    assert generator.is_relation_explicitly_in_summary(summary_text, rel_absent) is False


def test_deterministic_pipeline(tmp_path: Path):
    """Test 12: Verify pipeline determinism across multiple runs."""
    sum_file = tmp_path / "summary_inputs.jsonl"
    causal_file = tmp_path / "causal_relations.jsonl"
    out_file = tmp_path / "perturbations.jsonl"
    stats_file = tmp_path / "perturbation_stats.json"

    # Write dummy summary input
    sum_data = {
        "document_id": "xsum_000001",
        "summary_id": "xsum_000001_ref",
        "summary_text": "Flooding caused major road closures in the city.",
        "summary_type": "reference",
        "metadata": {"dataset": "xsum"},
        "source_word_count": 50,
        "summary_word_count": 8,
        "compression_ratio": 0.16,
    }
    sum_file.write_text(json.dumps(sum_data) + "\n", encoding="utf-8")

    # Write dummy causal relation
    causal_data = {
        "document_id": "xsum_000001",
        "relations": [
            {
                "relation_id": "rel_000001",
                "document_id": "xsum_000001",
                "cause": "flooding",
                "relation": "causes",
                "effect": "major road closures",
                "pattern_matched": "caused",
            }
        ],
    }
    causal_file.write_text(json.dumps(causal_data) + "\n", encoding="utf-8")

    cfg = AppConfig(
        paths=PathConfig(root_dir=tmp_path),
        perturbation=PerturbationConfig(
            enabled=True,
            input_summary_path=str(sum_file),
            input_causal_relations_path=str(causal_file),
            output_path=str(out_file),
            stats_path=str(stats_file),
            sample_path=str(tmp_path / "sample.json"),
        ),
    )

    pipe = PerturbationPipeline(config=cfg)

    # Run 1
    pipe.run(summary_inputs_jsonl=sum_file, causal_relations_jsonl=causal_file)
    bytes1 = out_file.read_bytes()
    stats1 = stats_file.read_bytes()

    # Run 2
    pipe.run(summary_inputs_jsonl=sum_file, causal_relations_jsonl=causal_file)
    bytes2 = out_file.read_bytes()
    stats2 = stats_file.read_bytes()

    assert bytes1 == bytes2
    assert stats1 == stats2


def test_output_serialization():
    """Test 13: Verify JSONL output record serialization."""
    rec = PerturbationRecord(
        perturbation_id="xsum_000001_pert_000001",
        document_id="xsum_000001",
        summary_id="xsum_000001_ref",
        perturbation_type="WEAKENED",
        original_text="A caused B.",
        perturbed_text="A was associated with B.",
    )
    dumped = json.dumps(rec.to_dict())
    loaded = json.loads(dumped)
    assert loaded["perturbation_id"] == "xsum_000001_pert_000001"
    assert loaded["perturbation_type"] == "WEAKENED"


def test_unsupported_causal_construction():
    """Test 14: Verify strategy returning None for text without expected entity match."""
    strategy = ReversalStrategy()
    res = strategy.apply("Unrelated sentence about weather.", cause="heavy rainfall", relation="causes", effect="flooding")
    assert res is None


def test_statistics_generation():
    """Test 15: Verify required key metrics in statistics generation."""
    generator = PerturbationGenerator()
    rel = CausalRelation(
        relation_id="r1",
        document_id="doc1",
        cause="unrelated cause",
        relation="causes",
        effect="unrelated effect",
    )
    records, stats = generator.generate_perturbations("doc1", "sum1", "Text without cause or effect.", [rel])

    assert "source_relations_examined" in stats
    assert "relations_not_present_in_summary" in stats
    assert stats["relations_not_present_in_summary"] == 1


def test_full_pipeline_end_to_end(tmp_path: Path):
    """Test 16: Verify full pipeline end-to-end execution on synthetic fixture."""
    sum_file = tmp_path / "summary_inputs.jsonl"
    causal_file = tmp_path / "causal_relations.jsonl"
    out_file = tmp_path / "perturbations.jsonl"
    stats_file = tmp_path / "perturbation_stats.json"
    sample_file = tmp_path / "sample.json"

    sum_data = {
        "document_id": "xsum_000001",
        "summary_id": "xsum_000001_ref",
        "summary_text": "A grade II-listed bridge was blamed for causing severe floods.",
        "summary_type": "reference",
    }
    sum_file.write_text(json.dumps(sum_data) + "\n", encoding="utf-8")

    causal_data = {
        "document_id": "xsum_000001",
        "relations": [
            {
                "relation_id": "r1",
                "document_id": "xsum_000001",
                "cause": "A grade II-listed bridge",
                "relation": "causes",
                "effect": "severe floods",
                "pattern_matched": "caused",
            }
        ],
    }
    causal_file.write_text(json.dumps(causal_data) + "\n", encoding="utf-8")

    cfg = AppConfig(
        paths=PathConfig(root_dir=tmp_path),
        perturbation=PerturbationConfig(
            enabled=True,
            input_summary_path=str(sum_file),
            input_causal_relations_path=str(causal_file),
            output_path=str(out_file),
            stats_path=str(stats_file),
            sample_path=str(sample_file),
        ),
    )

    pipeline = PerturbationPipeline(config=cfg)
    stats = pipeline.run(summary_inputs_jsonl=sum_file, causal_relations_jsonl=causal_file)

    assert out_file.exists()
    assert stats_file.exists()
    assert sample_file.exists()

    assert stats["counts"]["documents_examined"] == 1
    assert stats["counts"]["generated_perturbations"] > 0


def test_single_relation_cause_and_effect_changed():
    """Test 17: Verify CAUSE_CHANGED and EFFECT_CHANGED produce valid perturbations on a single relation input."""
    generator = PerturbationGenerator()

    summary_text = (
        "Heavy rainfall caused the river to overflow. As a result, nearby roads were flooded, "
        "which delayed emergency response teams."
    )
    rel = CausalRelation(
        relation_id="rel_000001",
        document_id="doc_user",
        sentence_index=0,
        cause="Heavy rainfall",
        relation="causes",
        effect="the river to overflow",
    )

    records, stats = generator.generate_perturbations("doc_user", "sum_user", summary_text, [rel])

    cause_changed_recs = [r for r in records if r.perturbation_type == "CAUSE_CHANGED"]
    effect_changed_recs = [r for r in records if r.perturbation_type == "EFFECT_CHANGED"]
    reversed_recs = [r for r in records if r.perturbation_type == "REVERSED"]
    weakened_recs = [r for r in records if r.perturbation_type == "WEAKENED"]
    dropped_recs = [r for r in records if r.perturbation_type == "DROPPED"]

    # Verify CAUSE_CHANGED generates at least one valid record
    assert len(cause_changed_recs) >= 1
    c_rec = cause_changed_recs[0]
    assert c_rec.intended_relation["cause"].lower() != "heavy rainfall"
    assert c_rec.intended_relation["effect"].lower() == "the river to overflow"
    assert c_rec.perturbed_text != summary_text

    # Verify EFFECT_CHANGED generates at least one valid record
    assert len(effect_changed_recs) >= 1
    e_rec = effect_changed_recs[0]
    assert e_rec.intended_relation["effect"].lower() != "the river to overflow"
    assert e_rec.intended_relation["cause"].lower() == "heavy rainfall"
    assert e_rec.perturbed_text != summary_text

    # Verify REVERSED, WEAKENED, DROPPED generated records remain intact
    assert len(reversed_recs) >= 1
    assert len(weakened_recs) >= 1
    assert len(dropped_recs) >= 1

