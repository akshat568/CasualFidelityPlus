"""Unit and integration tests for Phase 12 Master Pipeline Orchestrator."""

import json
from pathlib import Path
import pytest

from causalfidelity.annotation.agreement import AgreementResult, InterAnnotatorAgreementEvaluator
from causalfidelity.annotation.config import Phase12Config
from causalfidelity.annotation.correlation import CorrelationResult, StatisticalCorrelationEvaluator
from causalfidelity.annotation.loader import AnnotationLoader, IngestionResult
from causalfidelity.annotation.pipeline import Phase12HumanValidationPipeline
from causalfidelity.annotation.schema import AnnotationRecord


@pytest.fixture
def temp_dir(tmp_path):
    """Fixture providing temporary directory for test artifacts."""
    return tmp_path


@pytest.fixture
def sample_valid_annotations():
    """Fixture providing 6 valid annotation dicts (3 items x 2 annotators)."""
    return [
        {
            "annotation_id": "ann_001",
            "perturbation_id": "pert_101",
            "annotator_id": "user_a",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "ann_002",
            "perturbation_id": "pert_101",
            "annotator_id": "user_b",
            "causal_label": "Reversed",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "ann_003",
            "perturbation_id": "pert_102",
            "annotator_id": "user_a",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "ann_004",
            "perturbation_id": "pert_102",
            "annotator_id": "user_b",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
        {
            "annotation_id": "ann_005",
            "perturbation_id": "pert_103",
            "annotator_id": "user_a",
            "causal_label": "Weakened",
            "naturalness_rating": 3,
        },
        {
            "annotation_id": "ann_006",
            "perturbation_id": "pert_103",
            "annotator_id": "user_b",
            "causal_label": "Weakened",
            "naturalness_rating": 4,
        },
    ]


@pytest.fixture
def sample_metrics():
    """Fixture providing automated metric evaluation records for the 3 items."""
    return [
        {
            "perturbation_id": "pert_101",
            "summac_score": 0.2,
            "factcc_score": 0.1,
            "overall_alignment_score": 0.25,
        },
        {
            "perturbation_id": "pert_102",
            "summac_score": 0.9,
            "factcc_score": 0.95,
            "overall_alignment_score": 0.92,
        },
        {
            "perturbation_id": "pert_103",
            "summac_score": 0.4,
            "factcc_score": 0.45,
            "overall_alignment_score": 0.42,
        },
    ]


# -----------------------------------------------------------------------------
# Test 1: Valid End-to-End Orchestration
# -----------------------------------------------------------------------------
def test_valid_end_to_end_orchestration(temp_dir, sample_valid_annotations, sample_metrics):
    """Test full 7-stage pipeline orchestration with valid inputs."""
    ann_file = temp_dir / "annotations.jsonl"
    with open(ann_file, "w", encoding="utf-8") as f:
        for rec in sample_valid_annotations:
            f.write(json.dumps(rec) + "\n")

    metric_file = temp_dir / "metrics.jsonl"
    with open(metric_file, "w", encoding="utf-8") as f:
        for m in sample_metrics:
            f.write(json.dumps(m) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[metric_file],
        output_dir=temp_dir / "results",
        human_annotations_output_path=temp_dir / "out_annotations.jsonl",
        human_validation_results_output_path=temp_dir / "out_validation.jsonl",
        inter_annotator_stats_output_path=temp_dir / "out_agreement.json",
        statistical_analysis_stats_output_path=temp_dir / "out_stats.json",
        allow_overwrite=True,
    )

    pipeline = Phase12HumanValidationPipeline(config)
    res = pipeline.run()

    assert res["status"] == "success"
    assert res["consensus_records_count"] == 3
    assert res["unresolved_disagreements_count"] == 0
    assert res["insufficient_coverage_count"] == 0

    # Verify files created on disk
    for key, path_str in res["output_files"].items():
        assert Path(path_str).exists()


# -----------------------------------------------------------------------------
# Test 2: Missing Annotation Input
# -----------------------------------------------------------------------------
def test_missing_annotation_input(temp_dir):
    """Test that missing annotation input file raises FileNotFoundError."""
    missing_file = temp_dir / "non_existent.jsonl"
    config = Phase12Config(annotation_input_path=missing_file)
    pipeline = Phase12HumanValidationPipeline(config)

    with pytest.raises(FileNotFoundError, match="Annotation input file not found"):
        pipeline.run()


# -----------------------------------------------------------------------------
# Test 3: Invalid Annotation Records
# -----------------------------------------------------------------------------
def test_invalid_annotation_records(temp_dir):
    """Test invalid annotation records handling under report vs strict mode."""
    ann_file = temp_dir / "invalid_annotations.jsonl"
    invalid_data = [
        {
            "annotation_id": "ann_001",
            "perturbation_id": "pert_101",
            "annotator_id": "user_a",
            "causal_label": "INVALID_LABEL",  # Invalid label
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "ann_002",
            "perturbation_id": "pert_101",
            "annotator_id": "user_b",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        },
    ]
    with open(ann_file, "w", encoding="utf-8") as f:
        for d in invalid_data:
            f.write(json.dumps(d) + "\n")

    # Mode 1: report behavior (processes valid, reports invalid)
    config_report = Phase12Config(
        annotation_input_path=ann_file,
        output_dir=temp_dir / "out1",
        human_annotations_output_path=temp_dir / "ann1.jsonl",
        human_validation_results_output_path=temp_dir / "val1.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr1.json",
        statistical_analysis_stats_output_path=temp_dir / "stat1.json",
        validation_behavior="report",
        allow_overwrite=True,
    )
    res_report = Phase12HumanValidationPipeline(config_report).run()
    assert res_report["ingestion_summary"]["invalid_records_count"] == 1
    assert res_report["ingestion_summary"]["valid_records_count"] == 1

    # Mode 2: strict behavior (raises ValueError)
    config_strict = Phase12Config(
        annotation_input_path=ann_file,
        validation_behavior="strict",
    )
    with pytest.raises(ValueError, match="Strict validation failed"):
        Phase12HumanValidationPipeline(config_strict).run()


# -----------------------------------------------------------------------------
# Test 4: Missing Metric Files
# -----------------------------------------------------------------------------
def test_missing_metric_files(temp_dir, sample_valid_annotations):
    """Test missing metric file handling in report vs strict mode."""
    ann_file = temp_dir / "ann.jsonl"
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in sample_valid_annotations:
            f.write(json.dumps(r) + "\n")

    missing_metric = temp_dir / "no_metrics.jsonl"

    # Report mode logs missing metric file and completes
    cfg_report = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[missing_metric],
        output_dir=temp_dir / "out_report",
        human_annotations_output_path=temp_dir / "ann_r.jsonl",
        human_validation_results_output_path=temp_dir / "val_r.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_r.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_r.json",
        validation_behavior="report",
        allow_overwrite=True,
    )
    res = Phase12HumanValidationPipeline(cfg_report).run()
    assert res["status"] == "success"
    assert str(missing_metric) in res["missing_metric_files"]

    # Strict mode raises FileNotFoundError
    cfg_strict = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[missing_metric],
        validation_behavior="strict",
    )
    with pytest.raises(FileNotFoundError, match="Automated metric input file not found"):
        Phase12HumanValidationPipeline(cfg_strict).run()


# -----------------------------------------------------------------------------
# Test 5: Duplicate Annotation Handling
# -----------------------------------------------------------------------------
def test_duplicate_annotation_handling(temp_dir):
    """Test detection and exclusion of duplicate annotation IDs or user-item pairs."""
    ann_file = temp_dir / "dups.jsonl"
    dups = [
        {
            "annotation_id": "ann_dup",
            "perturbation_id": "pert_101",
            "annotator_id": "user_a",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "ann_dup",  # Duplicate annotation_id
            "perturbation_id": "pert_101",
            "annotator_id": "user_b",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
    ]
    with open(ann_file, "w", encoding="utf-8") as f:
        for d in dups:
            f.write(json.dumps(d) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        output_dir=temp_dir / "out_dup",
        human_annotations_output_path=temp_dir / "ann_d.jsonl",
        human_validation_results_output_path=temp_dir / "val_d.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_d.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_d.json",
        allow_overwrite=True,
    )
    res = Phase12HumanValidationPipeline(config).run()
    assert res["ingestion_summary"]["duplicate_annotation_ids"] == 1
    assert res["ingestion_summary"]["valid_records_count"] == 1


# -----------------------------------------------------------------------------
# Test 6: Insufficient Annotator Coverage
# -----------------------------------------------------------------------------
def test_insufficient_annotator_coverage(temp_dir):
    """Test explicit reporting of items with fewer than 2 annotators."""
    ann_file = temp_dir / "single.jsonl"
    single = [
        {
            "annotation_id": "ann_single",
            "perturbation_id": "pert_single",
            "annotator_id": "user_a",
            "causal_label": "Faithful",
            "naturalness_rating": 5,
        }
    ]
    with open(ann_file, "w", encoding="utf-8") as f:
        for d in single:
            f.write(json.dumps(d) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        output_dir=temp_dir / "out_single",
        human_annotations_output_path=temp_dir / "ann_s.jsonl",
        human_validation_results_output_path=temp_dir / "val_s.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_s.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_s.json",
        allow_overwrite=True,
    )
    res = Phase12HumanValidationPipeline(config).run()

    assert res["insufficient_coverage_count"] == 1
    assert res["insufficient_coverage_items"][0]["perturbation_id"] == "pert_single"
    assert res["agreement_results"]["eligible_paired_items"] == 0
    assert res["agreement_results"]["excluded_items_count"] == 1


# -----------------------------------------------------------------------------
# Test 7: Consensus Generation Behavior
# -----------------------------------------------------------------------------
def test_consensus_generation_behavior(temp_dir):
    """Test unanimous consensus label calculation and mean naturalness rating."""
    ann_file = temp_dir / "consensus.jsonl"
    recs = [
        {
            "annotation_id": "ann_1",
            "perturbation_id": "pert_c1",
            "annotator_id": "user_a",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "ann_2",
            "perturbation_id": "pert_c1",
            "annotator_id": "user_b",
            "causal_label": "Reversed",
            "naturalness_rating": 5,
        },
    ]
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        output_dir=temp_dir / "out_c",
        human_annotations_output_path=temp_dir / "ann_c.jsonl",
        human_validation_results_output_path=temp_dir / "val_c.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_c.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_c.json",
        allow_overwrite=True,
    )
    res = Phase12HumanValidationPipeline(config).run()

    val_path = Path(res["output_files"]["human_validation_results"])
    with open(val_path, "r", encoding="utf-8") as f:
        consensus_obj = json.loads(f.readline())

    assert consensus_obj["perturbation_id"] == "pert_c1"
    assert consensus_obj["consensus_causal_label"] == "Reversed"
    assert consensus_obj["is_distorted"] is True
    assert consensus_obj["is_unanimous"] is True
    assert consensus_obj["mean_naturalness"] == 4.5


# -----------------------------------------------------------------------------
# Test 8: Unresolved Disagreements
# -----------------------------------------------------------------------------
def test_unresolved_disagreements(temp_dir):
    """Test that annotator disagreements set label to DISAGREED and record summary."""
    ann_file = temp_dir / "disagree.jsonl"
    recs = [
        {
            "annotation_id": "ann_d1",
            "perturbation_id": "pert_disagree",
            "annotator_id": "user_a",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "ann_d2",
            "perturbation_id": "pert_disagree",
            "annotator_id": "user_b",
            "causal_label": "Faithful",
            "naturalness_rating": 4,
        },
    ]
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        output_dir=temp_dir / "out_disagree",
        human_annotations_output_path=temp_dir / "ann_dis.jsonl",
        human_validation_results_output_path=temp_dir / "val_dis.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_dis.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_dis.json",
        allow_overwrite=True,
    )
    res = Phase12HumanValidationPipeline(config).run()

    assert res["unresolved_disagreements_count"] == 1
    dis_item = res["unresolved_disagreements"][0]
    assert dis_item["perturbation_id"] == "pert_disagree"
    assert set(dis_item["observed_labels"]) == {"Reversed", "Faithful"}

    val_path = Path(res["output_files"]["human_validation_results"])
    with open(val_path, "r", encoding="utf-8") as f:
        consensus_obj = json.loads(f.readline())

    assert consensus_obj["consensus_causal_label"] == "DISAGREED"
    assert consensus_obj["is_unanimous"] is False
    assert consensus_obj["is_distorted"] is None


# -----------------------------------------------------------------------------
# Test 9: Output Serialization
# -----------------------------------------------------------------------------
def test_output_serialization(temp_dir, sample_valid_annotations, sample_metrics):
    """Test valid JSON and JSONL structure of generated output artifacts."""
    ann_file = temp_dir / "ann_ser.jsonl"
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in sample_valid_annotations:
            f.write(json.dumps(r) + "\n")

    metric_file = temp_dir / "met_ser.jsonl"
    with open(metric_file, "w", encoding="utf-8") as f:
        for m in sample_metrics:
            f.write(json.dumps(m) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[metric_file],
        output_dir=temp_dir / "out_ser",
        human_annotations_output_path=temp_dir / "human_annotations.jsonl",
        human_validation_results_output_path=temp_dir / "human_validation_results.jsonl",
        inter_annotator_stats_output_path=temp_dir / "phase12_inter_annotator_stats.json",
        statistical_analysis_stats_output_path=temp_dir / "phase12_statistical_analysis_stats.json",
        allow_overwrite=True,
    )
    res = Phase12HumanValidationPipeline(config).run()

    # Verify JSONL lines format
    with open(res["output_files"]["human_annotations"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 6

    with open(res["output_files"]["human_validation_results"], "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 3

    # Verify JSON objects format
    with open(res["output_files"]["inter_annotator_stats"], "r", encoding="utf-8") as f:
        agr_json = json.load(f)
        assert "causal_classification_agreement" in agr_json

    with open(res["output_files"]["statistical_analysis_stats"], "r", encoding="utf-8") as f:
        stat_json = json.load(f)
        assert "pearson_correlations" in stat_json


# -----------------------------------------------------------------------------
# Test 10: Output Overwrite Protection
# -----------------------------------------------------------------------------
def test_output_overwrite_protection(temp_dir, sample_valid_annotations):
    """Test that existing output files trigger FileExistsError when allow_overwrite=False."""
    ann_file = temp_dir / "ann_ow.jsonl"
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in sample_valid_annotations:
            f.write(json.dumps(r) + "\n")

    out_ann = temp_dir / "existing_ann.jsonl"
    out_ann.touch()

    config = Phase12Config(
        annotation_input_path=ann_file,
        human_annotations_output_path=out_ann,
        human_validation_results_output_path=temp_dir / "val_ow.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_ow.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_ow.json",
        allow_overwrite=False,
    )

    pipeline = Phase12HumanValidationPipeline(config)
    with pytest.raises(FileExistsError, match="Output file already exists"):
        pipeline.run()

    # When allow_overwrite=True, execution succeeds
    config.allow_overwrite = True
    res = Phase12HumanValidationPipeline(config).run()
    assert res["status"] == "success"


# -----------------------------------------------------------------------------
# Test 11: Configuration Validation
# -----------------------------------------------------------------------------
def test_configuration_validation():
    """Test configuration parameter validation checks."""
    # Invalid validation_behavior
    with pytest.raises(ValueError, match="Invalid validation_behavior"):
        Phase12Config(annotation_input_path="dummy.jsonl", validation_behavior="invalid_mode")

    # Invalid input_format
    with pytest.raises(ValueError, match="Invalid input_format"):
        Phase12Config(annotation_input_path="dummy.jsonl", input_format="xml")

    # Empty annotation_input_path
    with pytest.raises(ValueError, match="annotation_input_path must be specified"):
        Phase12Config(annotation_input_path="")


# -----------------------------------------------------------------------------
# Test 12: Preservation of Existing Step 1–3 Functionality
# -----------------------------------------------------------------------------
def test_preservation_of_existing_step1_3_functionality(sample_valid_annotations):
    """Verify that Step 1-3 modules operate independently without regressions."""
    # Step 1: Schema & Loader
    loader = AnnotationLoader()
    ingest_res = loader.load_from_list(sample_valid_annotations)
    assert len(ingest_res.valid_records) == 6

    # Step 2: Agreement Evaluator
    agree_eval = InterAnnotatorAgreementEvaluator()
    agree_res = agree_eval.evaluate(ingest_res.valid_records)
    assert agree_res.eligible_paired_items == 3
    assert agree_res.causal_classification_agreement["cohens_kappa"] == 1.0

    # Step 3: Statistical Correlation Evaluator
    stat_eval = StatisticalCorrelationEvaluator()
    metrics = [
        {"perturbation_id": "pert_101", "score": 0.2},
        {"perturbation_id": "pert_102", "score": 0.9},
        {"perturbation_id": "pert_103", "score": 0.4},
    ]
    corr_res = stat_eval.evaluate(ingest_res.valid_records, metrics)
    assert corr_res.matched_records_count == 3


# -----------------------------------------------------------------------------
# Test 13: Disagreement Exclusion from Statistical Calculations
# -----------------------------------------------------------------------------
def test_13_disagreement_exclusion_from_statistical_calculations(temp_dir):
    """Verify that items with unresolved disagreements are excluded from binary distortion target vectors."""
    ann_file = temp_dir / "disagree_stats.jsonl"
    recs = [
        {
            "annotation_id": "a1",
            "perturbation_id": "p_agree",
            "annotator_id": "u1",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "a2",
            "perturbation_id": "p_agree",
            "annotator_id": "u2",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "a3",
            "perturbation_id": "p_disagree",
            "annotator_id": "u1",
            "causal_label": "Reversed",
            "naturalness_rating": 4,
        },
        {
            "annotation_id": "a4",
            "perturbation_id": "p_disagree",
            "annotator_id": "u2",
            "causal_label": "Faithful",
            "naturalness_rating": 4,
        },
    ]
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")

    metric_file = temp_dir / "m_stats.jsonl"
    metrics = [
        {"perturbation_id": "p_agree", "summac_score": 0.1},
        {"perturbation_id": "p_disagree", "summac_score": 0.5},
    ]
    with open(metric_file, "w", encoding="utf-8") as f:
        for m in metrics:
            f.write(json.dumps(m) + "\n")

    config = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[metric_file],
        output_dir=temp_dir / "out_reg",
        human_annotations_output_path=temp_dir / "a_reg.jsonl",
        human_validation_results_output_path=temp_dir / "v_reg.jsonl",
        inter_annotator_stats_output_path=temp_dir / "agr_reg.json",
        statistical_analysis_stats_output_path=temp_dir / "stat_reg.json",
        allow_overwrite=True,
    )

    res = Phase12HumanValidationPipeline(config).run()

    corr_stats = res["correlation_results"]
    assert corr_stats["matched_records_count"] == 2
    # Disagreed item is logged in excluded_records under unresolved_annotator_disagreement
    assert any(
        exc.get("reason") == "unresolved_annotator_disagreement" and exc.get("perturbation_id") == "p_disagree"
        for exc in corr_stats["excluded_records"]
    )
    # Excluded from binary target, so n=1 for binary distortion pearson
    p_dist = corr_stats["pearson_correlations"]["summac_score_vs_human_distortion"]
    assert p_dist["n"] == 1


# -----------------------------------------------------------------------------
# Test 14: Deterministic Pipeline Execution
# -----------------------------------------------------------------------------
def test_14_deterministic_pipeline_execution(temp_dir, sample_valid_annotations, sample_metrics):
    """Verify that repeated pipeline runs with identical inputs produce bit-exact identical output files."""
    ann_file = temp_dir / "det_ann.jsonl"
    with open(ann_file, "w", encoding="utf-8") as f:
        for r in sample_valid_annotations:
            f.write(json.dumps(r) + "\n")

    metric_file = temp_dir / "det_met.jsonl"
    with open(metric_file, "w", encoding="utf-8") as f:
        for m in sample_metrics:
            f.write(json.dumps(m) + "\n")

    run1_dir = temp_dir / "run1"
    config1 = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[metric_file],
        output_dir=run1_dir,
        human_annotations_output_path=run1_dir / "ann.jsonl",
        human_validation_results_output_path=run1_dir / "val.jsonl",
        inter_annotator_stats_output_path=run1_dir / "agr.json",
        statistical_analysis_stats_output_path=run1_dir / "stat.json",
        allow_overwrite=True,
    )
    res1 = Phase12HumanValidationPipeline(config1).run()

    run2_dir = temp_dir / "run2"
    config2 = Phase12Config(
        annotation_input_path=ann_file,
        metric_input_paths=[metric_file],
        output_dir=run2_dir,
        human_annotations_output_path=run2_dir / "ann.jsonl",
        human_validation_results_output_path=run2_dir / "val.jsonl",
        inter_annotator_stats_output_path=run2_dir / "agr.json",
        statistical_analysis_stats_output_path=run2_dir / "stat.json",
        allow_overwrite=True,
    )
    res2 = Phase12HumanValidationPipeline(config2).run()

    # Verify identical content in generated json files
    for k in ["human_annotations", "human_validation_results", "inter_annotator_stats", "statistical_analysis_stats"]:
        c1 = Path(res1["output_files"][k]).read_text(encoding="utf-8")
        c2 = Path(res2["output_files"][k]).read_text(encoding="utf-8")
        assert c1 == c2

