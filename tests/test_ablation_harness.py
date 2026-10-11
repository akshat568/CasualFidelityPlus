"""Unit tests for Phase 13 Step 2 Ablation Experiment Execution Harness."""

import json
from pathlib import Path
import pytest

from causalfidelity.config import load_config
from causalfidelity.experiment.ablation import (
    APPROVED_EXPERIMENT_IDS,
    AblationExperimentDefinition,
    AblationMatrixHarness,
    get_approved_matrix_definitions,
)
from causalfidelity.experiment.config import ExperimentConfig, ExperimentRunConfig


def test_1_matrix_contains_all_approved_ids():
    """Test 1: Verify harness contains all 9 approved experiment IDs in exact deterministic order."""
    expected_ids = [
        "EXP_01_BASELINE",
        "EXP_02_THRESH_PERMISSIVE",
        "EXP_03_THRESH_STRICT",
        "EXP_04_WEIGHT_EQUAL",
        "EXP_05_WEIGHT_ARG_ONLY",
        "EXP_06_ABLATE_SUMMAC",
        "EXP_07_ABLATE_FACTCC",
        "EXP_08_ABLATE_BERTSCORE",
        "EXP_09_HUMAN_CORRELATION",
    ]
    assert APPROVED_EXPERIMENT_IDS == expected_ids
    assert len(APPROVED_EXPERIMENT_IDS) == 9

    harness = AblationMatrixHarness()
    matrix_ids = harness.list_experiment_ids()
    assert matrix_ids == expected_ids


def test_2_experiment_ids_are_unique():
    """Test 2: Verify all experiment IDs are unique and no duplicates exist."""
    assert len(APPROVED_EXPERIMENT_IDS) == len(set(APPROVED_EXPERIMENT_IDS))

    defs = get_approved_matrix_definitions()
    assert len(defs) == 9
    for exp_id in APPROVED_EXPERIMENT_IDS:
        assert exp_id in defs


def test_3_configuration_overrides_are_valid():
    """Test 3: Verify configuration overrides for each of the 9 experiments pass validation rules."""
    harness = AblationMatrixHarness()
    validation_results = harness.validate_matrix()

    assert validation_results["status"] == "VALID"
    assert validation_results["validated_count"] == 9

    # Verify EXP_02 permissive thresholds
    exp2_cfg = harness.create_app_config_for_experiment("EXP_02_THRESH_PERMISSIVE")
    assert exp2_cfg.alignment.cause_threshold == 0.35
    assert exp2_cfg.alignment.effect_threshold == 0.35
    assert exp2_cfg.alignment.overall_threshold == 0.45
    assert exp2_cfg.causal_distortion.cause_threshold == 0.35

    # Verify EXP_03 strict thresholds
    exp3_cfg = harness.create_app_config_for_experiment("EXP_03_THRESH_STRICT")
    assert exp3_cfg.alignment.cause_threshold == 0.65
    assert exp3_cfg.causal_distortion.cause_threshold == 0.65

    # Verify EXP_04 equal weights
    exp4_cfg = harness.create_app_config_for_experiment("EXP_04_WEIGHT_EQUAL")
    assert exp4_cfg.alignment.cause_weight == 0.33
    assert exp4_cfg.alignment.effect_weight == 0.33
    assert exp4_cfg.alignment.relation_weight == 0.34

    # Verify EXP_05 argument-only weights
    exp5_cfg = harness.create_app_config_for_experiment("EXP_05_WEIGHT_ARG_ONLY")
    assert exp5_cfg.alignment.cause_weight == 0.50
    assert exp5_cfg.alignment.effect_weight == 0.50
    assert exp5_cfg.alignment.relation_weight == 0.00

    # Verify component ablations (EXP_06, EXP_07, EXP_08)
    exp6_cfg = harness.create_app_config_for_experiment("EXP_06_ABLATE_SUMMAC")
    assert exp6_cfg.metrics.summac.enabled is False
    assert exp6_cfg.metrics.factcc.enabled is True

    exp7_cfg = harness.create_app_config_for_experiment("EXP_07_ABLATE_FACTCC")
    assert exp7_cfg.metrics.factcc.enabled is False

    exp8_cfg = harness.create_app_config_for_experiment("EXP_08_ABLATE_BERTSCORE")
    assert exp8_cfg.metrics.bertscore.enabled is False


def test_4_baseline_configuration_remains_unchanged():
    """Test 4: Verify global base AppConfig is not mutated when generating experiment configs."""
    base_cfg = load_config()
    orig_cause_thresh = base_cfg.alignment.cause_threshold
    orig_cause_weight = base_cfg.alignment.cause_weight
    orig_summac_enabled = base_cfg.metrics.summac.enabled

    harness = AblationMatrixHarness(base_config=base_cfg)
    
    # Generate configs with overrides
    harness.create_app_config_for_experiment("EXP_02_THRESH_PERMISSIVE")
    harness.create_app_config_for_experiment("EXP_04_WEIGHT_EQUAL")
    harness.create_app_config_for_experiment("EXP_06_ABLATE_SUMMAC")

    # Base config must remain unchanged
    assert base_cfg.alignment.cause_threshold == orig_cause_thresh
    assert base_cfg.alignment.cause_weight == orig_cause_weight
    assert base_cfg.metrics.summac.enabled == orig_summac_enabled


def test_5_run_configurations_are_isolated(tmp_path):
    """Test 5: Verify isolated output paths for experiment run configs."""
    harness = AblationMatrixHarness(base_output_dir=tmp_path / "experiments")

    run_cfg = harness.create_experiment_run_config("EXP_02_THRESH_PERMISSIVE", run_number=1)

    expected_run_dir = tmp_path / "experiments" / "EXP_02_THRESH_PERMISSIVE" / "runs" / "EXP_02_THRESH_PERMISSIVE_run_001"
    assert run_cfg.run_output_dir == expected_run_dir
    assert run_cfg.app_config.paths.root_dir == expected_run_dir
    assert str(run_cfg.app_config.paths.processed_data_dir).startswith(str(expected_run_dir))


def test_6_output_directories_follow_expected_convention(tmp_path):
    """Test 6: Verify output directory layout follows project convention."""
    harness = AblationMatrixHarness(base_output_dir=tmp_path / "outputs" / "experiments")

    for exp_id in APPROVED_EXPERIMENT_IDS:
        master_cfg = harness.create_master_experiment_config(exp_id)
        expected_dir = tmp_path / "outputs" / "experiments" / exp_id
        assert master_cfg.output_dir == expected_dir


def test_7_invalid_configurations_produce_clear_errors():
    """Test 7: Verify clear exceptions when invalid threshold, invalid ID, or invalid weight sum are provided."""
    # Invalid experiment ID
    with pytest.raises(ValueError, match="Unrecognized experiment_id"):
        AblationExperimentDefinition(
            experiment_id="INVALID_EXP_NAME",
            category="Invalid",
            description="Testing invalid ID",
        )

    # Invalid threshold > 1.0
    with pytest.raises(ValueError, match="must be a float between 0.0 and 1.0"):
        AblationExperimentDefinition(
            experiment_id="EXP_02_THRESH_PERMISSIVE",
            category="Threshold",
            description="Testing invalid threshold",
            parameter_overrides={"cause_threshold": 1.5},
        )

    # Invalid weights sum != 1.0
    with pytest.raises(ValueError, match="must sum to 1.0"):
        AblationExperimentDefinition(
            experiment_id="EXP_04_WEIGHT_EQUAL",
            category="Weighting",
            description="Testing invalid weights sum",
            parameter_overrides={"cause_weight": 0.5, "effect_weight": 0.5, "relation_weight": 0.5},
        )


def test_8_serialization_is_deterministic(tmp_path):
    """Test 8: Verify matrix manifest export and dictionary serialization are deterministic."""
    harness = AblationMatrixHarness()
    out_manifest = tmp_path / "ablation_matrix_manifest.json"

    written_path = harness.export_matrix_manifest(out_manifest)
    assert written_path.exists()

    with open(written_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_experiments"] == 9
    assert data["experiment_ids"] == APPROVED_EXPERIMENT_IDS
    assert "EXP_01_BASELINE" in data["experiments"]
    assert "EXP_09_HUMAN_CORRELATION" in data["experiments"]


def test_9_existing_outputs_are_protected(tmp_path):
    """Test 9: Verify output safety check prevents overwriting existing experiment manifests unless permitted."""
    exp_dir = tmp_path / "experiments" / "EXP_01_BASELINE"
    exp_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = exp_dir / "run_manifest.json"
    manifest_path.write_text("{\"status\": \"SUCCESS\"}\n", encoding="utf-8")

    harness = AblationMatrixHarness(base_output_dir=tmp_path / "experiments")

    # Should raise FileExistsError when allow_overwrite=False
    with pytest.raises(FileExistsError, match="Existing experiment results found"):
        harness.check_output_safety("EXP_01_BASELINE", allow_overwrite=False)

    # Should pass when allow_overwrite=True
    res = harness.check_output_safety("EXP_01_BASELINE", allow_overwrite=True)
    assert res["safety_status"] == "overwrite_permitted"


def test_10_unsupported_experiments_reported_clearly():
    """Test 10: Verify clear KeyError when requesting an unsupported experiment ID from harness."""
    harness = AblationMatrixHarness()

    with pytest.raises(KeyError, match="not found in matrix"):
        harness.get_experiment_definition("EXP_99_NONEXISTENT")


def test_11_existing_experiment_functionality_remains_intact(tmp_path):
    """Test 11: Verify compatibility with existing ExperimentConfig and ExperimentRunner infrastructure."""
    harness = AblationMatrixHarness(base_output_dir=tmp_path / "experiments")
    run_cfg = harness.create_experiment_run_config("EXP_01_BASELINE", run_number=1)

    assert run_cfg.experiment_id == "EXP_01_BASELINE"
    assert run_cfg.run_id == "EXP_01_BASELINE_run_001"
    assert run_cfg.seed == 42
    assert run_cfg.sample_size == 100
    assert run_cfg.app_config.paths.root_dir == run_cfg.run_output_dir
