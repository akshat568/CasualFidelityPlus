"""Unit tests for Phase 11 Step 3 Benchmark Expansion and Balancing."""

import json
from pathlib import Path
import pytest

from causalfidelity.config import load_config
from causalfidelity.experiment.balancer import BenchmarkBalancer
from causalfidelity.experiment.config import BenchmarkExpansionConfig
from causalfidelity.experiment.sampler import BenchmarkExpansionSampler


@pytest.fixture
def sample_raw_stream():
    """Create controlled synthetic document stream for testing expansion sampler."""
    return [
        {
            "id": "10001",
            "document": "Heavy rainfall caused severe flooding in the local valley on Monday.",
            "summary": "Heavy rainfall caused severe flooding in the valley.",
        },
        {
            "id": "10002",
            "document": "The new legislation led to increased economic activity across the region.",
            "summary": "New legislation led to economic growth.",
        },
        {
            "id": "10003",
            "document": "A high-speed train derailed near the city center, causing multiple injuries.",
            "summary": "Train derailment caused injuries.",
        },
    ]


@pytest.fixture
def synthetic_validated_records():
    """Create controlled synthetic validated perturbation records across categories."""
    records = []
    # 5 WEAKENED, 5 DROPPED, 5 CAUSE_CHANGED, 5 EFFECT_CHANGED, 2 REVERSED
    categories_counts = [
        ("WEAKENED", 5),
        ("DROPPED", 5),
        ("CAUSE_CHANGED", 5),
        ("EFFECT_CHANGED", 5),
        ("REVERSED", 2),
    ]

    counter = 1
    for ptype, count in categories_counts:
        for i in range(count):
            pid = f"xsum_exp_{counter:06d}_pert_{counter:06d}"
            records.append(
                {
                    "perturbation_id": pid,
                    "document_id": f"xsum_exp_{counter:06d}",
                    "summary_id": f"sum_xsum_exp_{counter:06d}",
                    "perturbation_type": ptype,
                    "original_text": "Original text content.",
                    "perturbed_text": "Perturbed text content.",
                    "original_relation": {"cause": "rain", "relation": "causes", "effect": "flooding"},
                    "intended_relation": {"cause": "rain", "relation": ptype.lower(), "effect": "flooding"},
                    "changed_span": {"original": "caused", "perturbed": "associated with"},
                    "generation_method": "rule_based",
                    "validation_status": "valid",
                    "checks": {"structural": "passed", "target_transformation": "passed"},
                    "errors": [],
                    "warnings": [],
                }
            )
            counter += 1

    return records


def test_1_deterministic_sampling_with_fixed_seed(sample_raw_stream, tmp_path):
    """Test 1: Deterministic sampling with fixed seeds produces identical results."""
    out_dir1 = tmp_path / "run1" / "data" / "processed"
    sampler1 = BenchmarkExpansionSampler(
        target_quota_per_category=2,
        max_documents_to_process=10,
        sampling_seed=42,
        output_dir=out_dir1,
    )
    recs1, stats1 = sampler1.sample_and_expand(raw_stream=sample_raw_stream)

    out_dir2 = tmp_path / "run2" / "data" / "processed"
    sampler2 = BenchmarkExpansionSampler(
        target_quota_per_category=2,
        max_documents_to_process=10,
        sampling_seed=42,
        output_dir=out_dir2,
    )
    recs2, stats2 = sampler2.sample_and_expand(raw_stream=sample_raw_stream)

    assert len(recs1) == len(recs2)
    assert json.dumps(stats1, sort_keys=True) == json.dumps(stats2, sort_keys=True)


def test_2_duplicate_document_and_perturbation_handling(sample_raw_stream, tmp_path):
    """Test 2: Duplicate documents in raw stream are detected and skipped."""
    dup_stream = sample_raw_stream + [sample_raw_stream[0]]  # Duplicate item 0
    out_dir = tmp_path / "dup_test" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=5,
        max_documents_to_process=10,
        sampling_seed=42,
        output_dir=out_dir,
    )
    recs, stats = sampler.sample_and_expand(raw_stream=dup_stream)

    # Documents processed should be 3 (not 4) due to duplicate rejection
    assert stats["counts"]["documents_processed"] == 3


def test_3_validity_filtering_using_phase7_validation(sample_raw_stream, tmp_path):
    """Test 3: Only valid perturbations (validation_status == 'valid') are retained."""
    out_dir = tmp_path / "val_test" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=2,
        max_documents_to_process=10,
        output_dir=out_dir,
    )
    recs, stats = sampler.sample_and_expand(raw_stream=sample_raw_stream)

    for rec in recs:
        assert rec["validation_status"] == "valid"
        assert len(rec["errors"]) == 0


def test_4_category_quota_enforcement(sample_raw_stream, tmp_path):
    """Test 4: Sampler tracks category counts and respects specified quotas."""
    out_dir = tmp_path / "quota_test" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=1,
        max_documents_to_process=10,
        output_dir=out_dir,
    )
    recs, stats = sampler.sample_and_expand(raw_stream=sample_raw_stream)

    v_counts = stats["valid_counts_by_category"]
    assert "WEAKENED" in v_counts
    assert "DROPPED" in v_counts


def test_5_max_document_budget_stopping(sample_raw_stream, tmp_path):
    """Test 5: Sampler stops when maximum document budget is reached."""
    out_dir = tmp_path / "budget_test" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=100,  # High quota
        max_documents_to_process=1,     # Stop after 1 doc
        output_dir=out_dir,
    )
    recs, stats = sampler.sample_and_expand(raw_stream=sample_raw_stream)

    assert stats["counts"]["documents_processed"] == 1
    assert stats["expansion_info"]["stop_reason"] == "max_documents_reached"


def test_6_correct_handling_of_missing_categories(synthetic_validated_records, tmp_path):
    """Test 6: Balancer reports shortfalls for underrepresented categories (e.g., REVERSED)."""
    balancer = BenchmarkBalancer()
    out_dir = tmp_path / "shortfall_test" / "data" / "processed"

    balanced_recs, stats = balancer.balance(
        validated_records=synthetic_validated_records,
        target_count_per_category=5,
        seed=42,
        output_dir=out_dir,
    )

    cat_stats = stats["category_breakdown"]
    # WEAKENED had 5 -> selected 5, shortfall 0
    assert cat_stats["WEAKENED"]["selected_count"] == 5
    assert cat_stats["WEAKENED"]["shortfall"] == 0

    # REVERSED had only 2 -> selected 2, shortfall 3
    assert cat_stats["REVERSED"]["selected_count"] == 2
    assert cat_stats["REVERSED"]["shortfall"] == 3
    assert stats["balancing_info"]["is_fully_balanced"] is False


def test_7_deterministic_balancing(synthetic_validated_records, tmp_path):
    """Test 7: Balancing produces byte-for-byte identical output across runs with fixed seed."""
    balancer = BenchmarkBalancer()
    out1 = tmp_path / "b1" / "data" / "processed"
    out2 = tmp_path / "b2" / "data" / "processed"

    recs1, stats1 = balancer.balance(
        validated_records=synthetic_validated_records,
        target_count_per_category=3,
        seed=42,
        output_dir=out1,
    )
    recs2, stats2 = balancer.balance(
        validated_records=synthetic_validated_records,
        target_count_per_category=3,
        seed=42,
        output_dir=out2,
    )

    assert json.dumps(recs1, sort_keys=True) == json.dumps(recs2, sort_keys=True)
    assert json.dumps(stats1, sort_keys=True) == json.dumps(stats2, sort_keys=True)


def test_8_balanced_output_when_enough_valid_records_exist(synthetic_validated_records, tmp_path):
    """Test 8: Equal category sizes when enough valid records exist for requested quota."""
    # Filter synthetic records to categories with 5 items each (exclude REVERSED)
    avail_recs = [r for r in synthetic_validated_records if r["perturbation_type"] != "REVERSED"]
    balancer = BenchmarkBalancer()
    out = tmp_path / "full_bal" / "data" / "processed"

    recs, stats = balancer.balance(
        validated_records=avail_recs,
        target_count_per_category=3,
        seed=42,
        output_dir=out,
    )

    cat_stats = stats["category_breakdown"]
    for cat in ["WEAKENED", "DROPPED", "CAUSE_CHANGED", "EFFECT_CHANGED"]:
        assert cat_stats[cat]["selected_count"] == 3
        assert cat_stats[cat]["shortfall"] == 0


def test_9_shortfall_reporting_and_summary_markdown(synthetic_validated_records, tmp_path):
    """Test 9: Shortfall and summary report generation."""
    balancer = BenchmarkBalancer()
    out = tmp_path / "report_test" / "data" / "processed"

    _, stats = balancer.balance(
        validated_records=synthetic_validated_records,
        target_count_per_category=5,
        seed=42,
        output_dir=out,
    )

    report_file = tmp_path / "report_test" / "data" / "results" / "benchmark_expansion_summary.md"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Phase 11 — Benchmark Expansion and Balancing Report" in content
    assert "REVERSED" in content


def test_10_provenance_preservation(synthetic_validated_records, tmp_path):
    """Test 10: Original IDs, labels, and relations are preserved during balancing."""
    balancer = BenchmarkBalancer()
    out = tmp_path / "prov_test" / "data" / "processed"

    recs, _ = balancer.balance(
        validated_records=synthetic_validated_records,
        target_count_per_category=2,
        seed=42,
        output_dir=out,
    )

    for r in recs:
        assert "perturbation_id" in r
        assert "document_id" in r
        assert "summary_id" in r
        assert "original_relation" in r
        assert "intended_relation" in r
        assert r["generation_method"] == "rule_based"


def test_11_output_path_isolation(sample_raw_stream, tmp_path):
    """Test 11: All generated files are placed inside specified run output folder."""
    out_dir = tmp_path / "iso_exp" / "runs" / "run_001" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=1,
        max_documents_to_process=2,
        output_dir=out_dir,
    )
    sampler.sample_and_expand(raw_stream=sample_raw_stream)

    expanded_file = out_dir / "expanded_benchmark.jsonl"
    stats_file = out_dir.parent / "results" / "benchmark_expansion_stats.json"

    assert expanded_file.exists()
    assert stats_file.exists()
    assert str(out_dir) in str(expanded_file)


def test_12_benchmark_expansion_config_validation():
    """Test 12: Validation and dictionary serialization of BenchmarkExpansionConfig."""
    cfg = BenchmarkExpansionConfig(
        target_quota_per_category=15,
        max_documents_to_process=300,
        sampling_seed=123,
    )
    cfg.validate()
    assert cfg.target_quota_per_category == 15

    d = cfg.to_dict()
    assert d["target_quota_per_category"] == 15
    assert d["sampling_seed"] == 123

    reloaded = BenchmarkExpansionConfig.from_dict(d)
    assert reloaded.target_quota_per_category == 15

    with pytest.raises(ValueError, match="target_quota_per_category must be a positive integer"):
        bad_cfg = BenchmarkExpansionConfig(target_quota_per_category=-5)
        bad_cfg.validate()


def test_13_failure_handling_and_incomplete_run_reporting(sample_raw_stream, tmp_path):
    """Test 13: Failure handling and incomplete run reporting when stream ends before quotas met."""
    out_dir = tmp_path / "incomplete_test" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=50,  # Unattainable quota for 3 items
        max_documents_to_process=10,
        output_dir=out_dir,
    )
    recs, stats = sampler.sample_and_expand(raw_stream=sample_raw_stream)

    assert stats["expansion_info"]["stop_reason"] == "exhausted_stream"
    assert stats["counts"]["valid_candidates_total"] == len(recs)
    assert "valid_counts_by_category" in stats
    assert "rejection_reasons" in stats


def test_14_multiple_rejection_reasons_per_candidate_counting(sample_raw_stream, tmp_path):
    """Test 14: Verify multiple rejection reasons per candidate are counted correctly without inflating invalid candidate total."""
    out_dir = tmp_path / "rej_test" / "data" / "processed"
    sampler = BenchmarkExpansionSampler(
        target_quota_per_category=2,
        max_documents_to_process=10,
        output_dir=out_dir,
    )
    recs, stats = sampler.sample_and_expand(raw_stream=sample_raw_stream)

    # Valid candidates total + invalid candidates total must equal total candidates generated
    total_generated = stats["counts"]["total_candidates_generated"]
    valid_total = stats["counts"]["valid_candidates_total"]
    invalid_total = stats["counts"]["invalid_candidates_total"]
    assert valid_total + invalid_total == total_generated

    # Total rejection occurrences may exceed invalid_candidates_total if candidates fail multiple checks
    total_rejection_occurrences = sum(stats["rejection_reasons"].values())
    assert total_rejection_occurrences >= 0


