"""Unit and integration test suite for Phase 8 Summary Causal Extraction and Semantic Alignment."""

import json
from pathlib import Path
import numpy as np
import pytest

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.matcher import CausalMatcher
from causalfidelity.alignment.normalizer import check_exact_match, compute_relation_compatibility, normalize_text
from causalfidelity.alignment.pipeline import AlignmentPipeline
from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.alignment.scorer import CausalScorer
from causalfidelity.alignment.summary_extractor import SummaryCausalExtractor
from causalfidelity.alignment.validator import AlignmentValidator
from causalfidelity.causal.schema import CausalRelation
from causalfidelity.config import AppConfig, AlignmentConfig


@pytest.fixture
def sample_summary_record():
    return {
        "document_id": "doc_test_100",
        "summary_id": "doc_test_100_ref",
        "summary_text": "Heavy rainfall caused severe flooding in the city, which led to road closures.",
        "summary_type": "reference",
    }


@pytest.fixture
def sample_source_relation():
    return CausalRelation(
        relation_id="rel_src_100",
        document_id="doc_test_100",
        cause="Heavy rainfall",
        relation="causes",
        effect="severe flooding",
        confidence=0.95,
        source_sentence="Heavy rainfall caused severe flooding in the city.",
        sentence_index=0,
        extraction_method="rule_based",
    )


@pytest.fixture
def embedder():
    return SemanticEmbedder(model_name="all-MiniLM-L6-v2", device="cpu")


@pytest.fixture
def scorer():
    return CausalScorer(cause_weight=0.45, effect_weight=0.45, relation_weight=0.10)


@pytest.fixture
def matcher(embedder, scorer):
    return CausalMatcher(
        embedder=embedder,
        scorer=scorer,
        cause_threshold=0.50,
        effect_threshold=0.50,
        overall_threshold=0.60,
        ambiguity_margin=0.05,
    )


# 1. Summary Causal Extraction
def test_summary_causal_extraction(sample_summary_record):
    extractor = SummaryCausalExtractor()
    sum_rels = extractor.extract_from_summary(sample_summary_record)

    assert len(sum_rels) >= 1
    rel = sum_rels[0]
    assert isinstance(rel, SummaryCausalRelation)
    assert rel.document_id == "doc_test_100"
    assert rel.summary_id == "doc_test_100_ref"
    assert "rainfall" in rel.cause.lower()
    assert "flooding" in rel.effect.lower()
    assert rel.text_type == "summary"


# 2. Empty Summary Handling
def test_empty_summary_handling():
    extractor = SummaryCausalExtractor()
    assert extractor.extract_from_summary({}) == []
    assert extractor.extract_from_summary({"summary_text": ""}) == []
    assert extractor.extract_from_summary({"summary_text": "   \n\t  "}) == []


# 3. Multiple Summary Relations
def test_multiple_summary_relations():
    extractor = SummaryCausalExtractor()
    record = {
        "document_id": "doc_multi",
        "summary_id": "doc_multi_ref",
        "summary_text": "Heavy rainfall caused flooding. High winds triggered power outages.",
    }
    sum_rels = extractor.extract_from_summary(record)
    assert len(sum_rels) == 2
    assert sum_rels[0].cause != sum_rels[1].cause


# 4. Deterministic Summary Relation IDs
def test_deterministic_summary_relation_ids(sample_summary_record):
    extractor = SummaryCausalExtractor()
    res1 = extractor.extract_from_summary(sample_summary_record)
    res2 = extractor.extract_from_summary(sample_summary_record)

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.summary_relation_id == r2.summary_relation_id
        assert r1.summary_relation_id.startswith("doc_test_100_ref_rel_")


# 5. Embedding Generation
def test_embedding_generation(embedder):
    vecs = embedder.embed(["heavy rainfall", "severe flooding"])
    assert vecs.ndim == 2
    assert vecs.shape[0] == 2
    # Check L2 normalization (unit magnitude)
    norm0 = np.linalg.norm(vecs[0])
    norm1 = np.linalg.norm(vecs[1])
    assert pytest.approx(norm0, abs=1e-4) == 1.0
    assert pytest.approx(norm1, abs=1e-4) == 1.0


# 6. Cosine Similarity
def test_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert pytest.approx(SemanticEmbedder.cosine_similarity(v1, v2), abs=1e-4) == 1.0
    assert pytest.approx(SemanticEmbedder.cosine_similarity(v1, v3), abs=1e-4) == 0.0


# 7. Identical Text Produces High Similarity
def test_identical_text_produces_high_similarity(embedder):
    v1 = embedder.embed("heavy rainfall caused flooding")[0]
    v2 = embedder.embed("heavy rainfall caused flooding")[0]
    sim = SemanticEmbedder.cosine_similarity(v1, v2)
    assert sim >= 0.99


# 8. Unrelated Text Produces Lower Similarity
def test_unrelated_text_produces_lower_similarity(embedder):
    v1 = embedder.embed("heavy rainfall caused flash flooding")[0]
    v2 = embedder.embed("stock market indices surged in early trading")[0]
    sim = SemanticEmbedder.cosine_similarity(v1, v2)
    assert sim < 0.40


# 9. Cause and Effect are Scored Independently
def test_cause_and_effect_scored_independently(embedder, scorer):
    v_src_cause = embedder.embed("heavy rainfall")[0]
    v_src_effect = embedder.embed("severe flooding")[0]

    v_sum_cause = embedder.embed("torrential rain")[0]  # Similar to cause
    v_sum_effect_similar = embedder.embed("city inundation")[0]  # Similar to effect
    v_sum_effect_unrelated = embedder.embed("stock market growth")[0]  # Unrelated effect

    c_sim1, e_sim1, _, _ = scorer.score_candidate(v_src_cause, v_src_effect, v_sum_cause, v_sum_effect_similar)
    c_sim2, e_sim2, _, _ = scorer.score_candidate(v_src_cause, v_src_effect, v_sum_cause, v_sum_effect_unrelated)

    # Cause similarity should be identical regardless of effect change
    assert pytest.approx(c_sim1, abs=1e-3) == pytest.approx(c_sim2, abs=1e-3)
    # Effect similarity should be significantly lower for unrelated effect
    assert e_sim1 > e_sim2 + 0.30


# 10. Candidate Ranking
def test_candidate_ranking(matcher, sample_source_relation):
    cand1 = SummaryCausalRelation(
        summary_relation_id="sum_rel_001",
        document_id="doc_test_100",
        summary_id="sum_1",
        cause="Heavy rainfall",
        relation="causes",
        effect="severe flooding",
    )
    cand2 = SummaryCausalRelation(
        summary_relation_id="sum_rel_002",
        document_id="doc_test_100",
        summary_id="sum_1",
        cause="Minor moisture",
        relation="causes",
        effect="dry weather",
    )

    alignment = matcher.match_source_relation(sample_source_relation, [cand2, cand1])

    # Best candidate (cand1) should be selected as top rank
    assert alignment.summary_relation_id == "sum_rel_001"
    assert alignment.candidate_rank == 1
    assert alignment.alignment_status == "aligned"


# 11. Ambiguity Handling
def test_ambiguity_handling(embedder, scorer, sample_source_relation):
    # Create matcher with ambiguity margin = 0.10
    matcher_amb = CausalMatcher(
        embedder=embedder,
        scorer=scorer,
        cause_threshold=0.30,
        effect_threshold=0.30,
        overall_threshold=0.30,
        ambiguity_margin=0.10,
    )

    cand1 = SummaryCausalRelation(
        summary_relation_id="sum_rel_001",
        document_id="doc_test_100",
        summary_id="sum_1",
        cause="Heavy rainfall",
        relation="causes",
        effect="severe flooding",
    )
    cand2 = SummaryCausalRelation(
        summary_relation_id="sum_rel_002",
        document_id="doc_test_100",
        summary_id="sum_1",
        cause="Heavy rain",
        relation="causes",
        effect="severe flooding",
    )

    alignment = matcher_amb.match_source_relation(sample_source_relation, [cand1, cand2])
    assert alignment.alignment_status == "ambiguous"


# 12. Threshold Configuration
def test_threshold_configuration(embedder, scorer, sample_source_relation):
    matcher_strict = CausalMatcher(
        embedder=embedder,
        scorer=scorer,
        cause_threshold=0.99,
        effect_threshold=0.99,
        overall_threshold=0.99,
        ambiguity_margin=0.05,
    )

    cand = SummaryCausalRelation(
        summary_relation_id="sum_rel_001",
        document_id="doc_test_100",
        summary_id="sum_1",
        cause="Rain",
        relation="causes",
        effect="floods",
    )

    alignment = matcher_strict.match_source_relation(sample_source_relation, [cand])
    assert alignment.alignment_status == "below_threshold"


# 13. Relation Compatibility
def test_relation_compatibility():
    # Explicit strong causal triggers
    assert compute_relation_compatibility("caused", "led to") == 1.0
    assert compute_relation_compatibility("resulted in", "causes") == 1.0

    # Associative language is NOT equivalent to strong causal relation
    assert compute_relation_compatibility("caused", "associated with") == 0.0
    assert compute_relation_compatibility("linked to", "led to") == 0.0


# 14. Direction Preservation
def test_direction_preservation(embedder, scorer):
    v_sc = embedder.embed("heavy rainfall")[0]
    v_se = embedder.embed("severe flooding")[0]

    # Matching direction: summary cause="heavy rainfall", effect="severe flooding"
    c_sim_normal, e_sim_normal, _, score_normal = scorer.score_candidate(v_sc, v_se, v_sc, v_se)

    # Reversed direction: summary cause="severe flooding", effect="heavy rainfall"
    c_sim_rev, e_sim_rev, _, score_rev = scorer.score_candidate(v_sc, v_se, v_se, v_sc)

    # Raw cause & effect similarity scores differ when order is reversed
    assert c_sim_normal > c_sim_rev + 0.30
    assert e_sim_normal > e_sim_rev + 0.30


# 15. Exact Match Indicator
def test_exact_match_indicator():
    assert check_exact_match("Heavy rainfall", "severe flooding!", "heavy rainfall", "severe flooding") is True
    assert check_exact_match("Heavy rainfall", "severe flooding", "Torrential rain", "flooding") is False


# 16. Deterministic Repeated Runs
def test_deterministic_repeated_runs(matcher, sample_source_relation):
    cand = SummaryCausalRelation(
        summary_relation_id="sum_rel_001",
        document_id="doc_test_100",
        summary_id="sum_1",
        cause="Heavy rainfall",
        relation="causes",
        effect="severe flooding",
    )

    align1 = matcher.match_source_relation(sample_source_relation, [cand])
    align2 = matcher.match_source_relation(sample_source_relation, [cand])

    assert align1.to_dict() == align2.to_dict()


# 17. Malformed Input
def test_malformed_input_handling():
    validator = AlignmentValidator()

    # Missing summary_relation_id
    with pytest.raises(ValueError, match="summary_relation_id"):
        validator.validate_summary_relation(SummaryCausalRelation(
            summary_relation_id="",
            document_id="d1",
            summary_id="s1",
            cause="c",
            effect="e",
        ))

    # Invalid status
    with pytest.raises(ValueError, match="alignment_status"):
        validator.validate_alignment(CausalAlignment(
            alignment_id="a1",
            document_id="d1",
            source_relation_id="sr1",
            summary_id="s1",
            summary_relation_id="sr1",
            source_relation={},
            summary_relation={},
            cause_similarity=0.5,
            effect_similarity=0.5,
            relation_compatibility=0.5,
            overall_alignment_score=0.5,
            candidate_rank=1,
            alignment_status="INVALID_STATUS",
            exact_match=False,
        ))


# 18. Full Phase 8 Pipeline
def test_full_phase8_pipeline(tmp_path):
    root_dir = tmp_path
    data_dir = root_dir / "data" / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)

    src_rel_file = data_dir / "causal_relations.jsonl"
    sum_input_file = data_dir / "summary_inputs.jsonl"

    # Write dummy source relations
    src_data = [
        {
            "document_id": "doc_pipe_1",
            "relations": [
                {
                    "relation_id": "rel_src_01",
                    "document_id": "doc_pipe_1",
                    "cause": "Heavy rain",
                    "relation": "causes",
                    "effect": "flooding",
                    "confidence": 0.9,
                    "source_sentence": "Heavy rain caused flooding.",
                    "sentence_index": 0,
                    "extraction_method": "rule_based",
                }
            ],
        }
    ]
    with open(src_rel_file, "w", encoding="utf-8") as f:
        for item in src_data:
            f.write(json.dumps(item) + "\n")

    # Write dummy summary inputs
    sum_data = [
        {
            "document_id": "doc_pipe_1",
            "summary_id": "doc_pipe_1_ref",
            "summary_text": "Heavy rain resulted in city flooding.",
            "summary_type": "reference",
        }
    ]
    with open(sum_input_file, "w", encoding="utf-8") as f:
        for item in sum_data:
            f.write(json.dumps(item) + "\n")

    config = AppConfig()
    config.paths.root_dir = root_dir
    config.alignment.input_source_relations_path = "data/processed/causal_relations.jsonl"
    config.alignment.input_summary_path = "data/processed/summary_inputs.jsonl"
    config.alignment.output_summary_relations_path = "data/processed/summary_causal_relations.jsonl"
    config.alignment.output_alignments_path = "data/processed/causal_alignments.jsonl"
    config.alignment.stats_path = "data/processed/alignment_stats.json"
    config.alignment.sample_path = "outputs/results/phase8_alignment_sample.json"

    pipeline = AlignmentPipeline(config)
    stats = pipeline.run()

    assert stats["source_relations_examined"] == 1
    assert stats["summary_relations_extracted"] == 1
    assert stats["aligned_count"] == 1

    assert (root_dir / config.alignment.output_summary_relations_path).exists()
    assert (root_dir / config.alignment.output_alignments_path).exists()
    assert (root_dir / config.alignment.stats_path).exists()
    assert (root_dir / config.alignment.sample_path).exists()
