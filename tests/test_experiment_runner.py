"""Unit tests for Phase 11 Master Pipeline Orchestrator (ExperimentRunner)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from causalfidelity.config import load_config
from causalfidelity.experiment.config import ExperimentConfig, ExperimentRunConfig
from causalfidelity.experiment.runner import (
    ExperimentRunner,
    RunManifest,
    StageExecutionRecord,
)


@pytest.fixture
def sample_run_config(tmp_path):
    """Create sample isolated ExperimentRunConfig for testing."""
    app_cfg = load_config()
    run_dir = tmp_path / "exp_001" / "runs" / "exp_001_run_001"
    
    return ExperimentRunConfig(
        run_id="exp_001_run_001",
        experiment_id="exp_001",
        run_number=1,
        seed=42,
        sample_size=10,
        parameters={"cause_threshold": 0.45},
        run_output_dir=run_dir,
        app_config=app_cfg,
    )


def test_1_stage_dependency_order():
    """Test 1: Verify correct stage dependency order (Phases 2 through 10D)."""
    stages = [stage_name for stage_name, _ in ExperimentRunner.STAGE_ORDER]
    expected_order = [
        "data_preprocessing",
        "causal_extraction",
        "causal_graph",
        "summary_input",
        "perturbation",
        "perturbation_validation",
        "causal_alignment",
        "causal_distortion",
        "metrics_summac",
        "metrics_factcc",
        "metrics_bertscore",
        "research_analysis",
    ]
    assert stages == expected_order


def test_2_dry_run_execution(sample_run_config):
    """Test 2: Dry-run execution generates manifest without calling real pipelines."""
    runner = ExperimentRunner(run_config=sample_run_config, dry_run=True)
    manifest = runner.run()

    assert manifest.status == "DRY_RUN"
    assert manifest.run_id == "exp_001_run_001"
    assert manifest.experiment_id == "exp_001"
    assert len(manifest.stages) == 12

    for stage_rec in manifest.stages:
        assert stage_rec.status == "DRY_RUN"
        assert len(stage_rec.artifacts) > 0

    manifest_file = sample_run_config.run_output_dir / "run_manifest.json"
    assert manifest_file.exists()


def test_3_run_manifest_serialization(sample_run_config):
    """Test 3: Correct JSON serialization and content of RunManifest."""
    runner = ExperimentRunner(run_config=sample_run_config, dry_run=True)
    manifest = runner.run()
    manifest_dict = manifest.to_dict()

    assert manifest_dict["run_id"] == "exp_001_run_001"
    assert manifest_dict["status"] == "DRY_RUN"
    assert manifest_dict["parameters"] == {"cause_threshold": 0.45}
    assert isinstance(manifest_dict["stages"], list)
    assert len(manifest_dict["stages"]) == 12


def test_4_stage_failure_handling(sample_run_config):
    """Test 4: Halting run execution on stage failure and updating manifest status."""
    runner = ExperimentRunner(run_config=sample_run_config, dry_run=False)

    # Mock Stage 1 (data_preprocessing) to succeed, and Stage 2 (causal_extraction) to fail
    with patch("causalfidelity.experiment.runner.XSumPipeline") as mock_xsum, \
         patch("causalfidelity.experiment.runner.CausalExtractionPipeline") as mock_causal:
        
        mock_xsum.return_value.run.return_value = {"processed": 10}
        mock_causal.return_value.run.side_effect = RuntimeError("Extraction engine error")

        manifest = runner.run()

    assert manifest.status == "FAILED"
    # Execution should halt after Stage 2 (2 stages total)
    assert len(manifest.stages) == 2
    assert manifest.stages[0].status == "SUCCESS"
    assert manifest.stages[1].status == "FAILED"
    assert manifest.stages[1].error == "Extraction engine error"

    manifest_file = sample_run_config.run_output_dir / "run_manifest.json"
    assert manifest_file.exists()


def test_5_output_path_isolation(sample_run_config):
    """Test 5: Verify all outputs are contained inside run_output_dir."""
    runner = ExperimentRunner(run_config=sample_run_config, dry_run=True)
    manifest = runner.run()

    run_dir_str = str(sample_run_config.run_output_dir)
    assert manifest.output_dir == run_dir_str

    for stage in manifest.stages:
        for artifact_path in stage.artifacts:
            assert artifact_path.startswith(run_dir_str)


def test_6_mocked_full_pipeline_execution(sample_run_config):
    """Test 6: Full pipeline execution using test doubles (mocks) for all stages."""
    runner = ExperimentRunner(run_config=sample_run_config, dry_run=False)

    with patch("causalfidelity.experiment.runner.XSumPipeline") as m2, \
         patch("causalfidelity.experiment.runner.CausalExtractionPipeline") as m3, \
         patch("causalfidelity.experiment.runner.CausalGraphPipeline") as m4, \
         patch("causalfidelity.experiment.runner.SummaryInputPipeline") as m5, \
         patch("causalfidelity.experiment.runner.PerturbationPipeline") as m6, \
         patch("causalfidelity.experiment.runner.PerturbationValidationPipeline") as m7, \
         patch("causalfidelity.experiment.runner.AlignmentPipeline") as m8, \
         patch("causalfidelity.experiment.runner.DistortionDetectionPipeline") as m9, \
         patch("causalfidelity.experiment.runner.Phase10AEvaluatorPipeline") as m10a, \
         patch("causalfidelity.experiment.runner.Phase10BEvaluatorPipeline") as m10b, \
         patch("causalfidelity.experiment.runner.Phase10CEvaluatorPipeline") as m10c, \
         patch("causalfidelity.experiment.runner.Phase10DEvaluatorPipeline") as m10d:

        for m in [m2, m3, m4, m5, m6, m7, m8, m9, m10a, m10b, m10c, m10d]:
            m.return_value.run.return_value = {"mock_stat": 1.0}

        manifest = runner.run()

    assert manifest.status == "SUCCESS"
    assert len(manifest.stages) == 12
    for s in manifest.stages:
        assert s.status == "SUCCESS"
        assert s.stats == {"mock_stat": 1.0}


def test_7_skip_existing_stages(sample_run_config):
    """Test 7: Skipping stages when expected artifact outputs already exist."""
    run_dir = sample_run_config.run_output_dir
    data_dir = run_dir / "data" / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy artifacts for stage 1 (data_preprocessing)
    (data_dir / "xsum_dev.jsonl").write_text("{}\n", encoding="utf-8")
    (data_dir / "xsum_dev_stats.json").write_text("{}", encoding="utf-8")

    runner = ExperimentRunner(run_config=sample_run_config, dry_run=False, skip_existing=True)

    with patch("causalfidelity.experiment.runner.XSumPipeline") as m2, \
         patch("causalfidelity.experiment.runner.CausalExtractionPipeline") as m3, \
         patch("causalfidelity.experiment.runner.CausalGraphPipeline") as m4, \
         patch("causalfidelity.experiment.runner.SummaryInputPipeline") as m5, \
         patch("causalfidelity.experiment.runner.PerturbationPipeline") as m6, \
         patch("causalfidelity.experiment.runner.PerturbationValidationPipeline") as m7, \
         patch("causalfidelity.experiment.runner.AlignmentPipeline") as m8, \
         patch("causalfidelity.experiment.runner.DistortionDetectionPipeline") as m9, \
         patch("causalfidelity.experiment.runner.Phase10AEvaluatorPipeline") as m10a, \
         patch("causalfidelity.experiment.runner.Phase10BEvaluatorPipeline") as m10b, \
         patch("causalfidelity.experiment.runner.Phase10CEvaluatorPipeline") as m10c, \
         patch("causalfidelity.experiment.runner.Phase10DEvaluatorPipeline") as m10d:

        for m in [m3, m4, m5, m6, m7, m8, m9, m10a, m10b, m10c, m10d]:
            m.return_value.run.return_value = {"mock_stat": 1.0}

        manifest = runner.run()

    # Stage 1 should be SKIPPED without calling m2.run()
    assert manifest.stages[0].status == "SKIPPED"
    m2.return_value.run.assert_not_called()
