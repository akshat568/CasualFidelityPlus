"""Unit tests for Phase 11 Experimental Configuration module."""

from pathlib import Path
import pytest
import yaml

from causalfidelity.config import AppConfig, load_config
from causalfidelity.experiment.config import (
    DatasetExperimentSettings,
    ExperimentConfig,
    ExperimentRunConfig,
    ParameterSweepConfig,
    load_experiment_config,
    save_experiment_config,
)


def test_1_valid_default_experiment_config():
    """Test 1: Creation and validation of default valid ExperimentConfig."""
    exp = ExperimentConfig(experiment_id="exp_test_001")
    assert exp.experiment_id == "exp_test_001"
    assert exp.random_seed == 42
    assert exp.dataset.name == "xsum"
    assert exp.dataset.development_sample_size == 100
    assert exp.parameter_sweep is None


def test_2_invalid_experiment_id():
    """Test 2: Rejection of empty or invalid experiment IDs."""
    with pytest.raises(ValueError, match="experiment_id must be a non-empty string"):
        ExperimentConfig(experiment_id="")

    with pytest.raises(ValueError, match="must contain only alphanumeric characters"):
        ExperimentConfig(experiment_id="exp 001 invalid!")


def test_3_invalid_sample_size_and_seed():
    """Test 3: Rejection of negative or zero sample sizes and negative seeds."""
    with pytest.raises(ValueError, match="random_seed must be a non-negative integer"):
        ExperimentConfig(experiment_id="exp_001", random_seed=-5)

    with pytest.raises(ValueError, match="development_sample_size must be a positive integer"):
        ds = DatasetExperimentSettings(development_sample_size=-10)
        ds.validate()


def test_4_valid_parameter_sweep_grid():
    """Test 4: Deterministic generation of parameter sweep grid combinations."""
    sweep = ParameterSweepConfig(
        sample_sizes=[50, 100],
        random_seeds=[42, 123],
        cause_thresholds=[0.40, 0.50],
    )
    grid = sweep.get_sweep_grid()
    # 2 sample_sizes * 2 seeds * 2 cause_thresholds = 8 combinations
    assert len(grid) == 8

    # Verify first and last combination items
    assert grid[0] == {
        "development_sample_size": 50,
        "random_seed": 42,
        "cause_threshold": 0.40,
    }
    assert grid[-1] == {
        "development_sample_size": 100,
        "random_seed": 123,
        "cause_threshold": 0.50,
    }


def test_5_invalid_parameter_sweep_values():
    """Test 5: Rejection of invalid sweep parameters."""
    # Out of range threshold
    with pytest.raises(ValueError, match="cause_thresholds elements must be float between 0.0 and 1.0"):
        sweep = ParameterSweepConfig(cause_thresholds=[1.5])
        sweep.validate()

    # Empty list for sample sizes
    with pytest.raises(ValueError, match="sample_sizes must be a non-empty list"):
        sweep = ParameterSweepConfig(sample_sizes=[])
        sweep.validate()

    # Negative seed in sweep
    with pytest.raises(ValueError, match="Random seed must be a non-negative integer"):
        sweep = ParameterSweepConfig(random_seeds=[-1])
        sweep.validate()


def test_6_generate_runs_from_experiment():
    """Test 6: Generation of isolated ExperimentRunConfigs from ExperimentConfig."""
    sweep = ParameterSweepConfig(
        sample_sizes=[10, 20],
        random_seeds=[42],
    )
    exp = ExperimentConfig(
        experiment_id="exp_sweep_001",
        parameter_sweep=sweep,
    )
    runs = exp.generate_runs()
    assert len(runs) == 2

    run1 = runs[0]
    assert run1.run_id == "exp_sweep_001_run_001"
    assert run1.experiment_id == "exp_sweep_001"
    assert run1.run_number == 1
    assert run1.sample_size == 10
    assert run1.seed == 42
    assert "exp_sweep_001_run_001" in str(run1.run_output_dir)
    assert run1.app_config.dataset.development_sample_size == 10

    run2 = runs[1]
    assert run2.run_id == "exp_sweep_001_run_002"
    assert run2.sample_size == 20
    assert run2.app_config.dataset.development_sample_size == 20


def test_7_run_config_validation():
    """Test 7: Validation of individual ExperimentRunConfig objects."""
    app_cfg = load_config()
    with pytest.raises(ValueError, match="run_id must be a non-empty string"):
        ExperimentRunConfig(
            run_id="",
            experiment_id="exp_1",
            run_number=1,
            seed=42,
            sample_size=10,
            parameters={},
            run_output_dir=Path("/tmp"),
            app_config=app_cfg,
        )

    with pytest.raises(ValueError, match="run_number must be a positive integer"):
        ExperimentRunConfig(
            run_id="run_1",
            experiment_id="exp_1",
            run_number=0,
            seed=42,
            sample_size=10,
            parameters={},
            run_output_dir=Path("/tmp"),
            app_config=app_cfg,
        )


def test_8_yaml_serialization_and_deserialization(tmp_path):
    """Test 8: Serialization to YAML and reloading from YAML."""
    sweep = ParameterSweepConfig(
        sample_sizes=[100, 200],
        cause_thresholds=[0.45, 0.55],
    )
    exp_orig = ExperimentConfig(
        experiment_id="exp_yaml_test",
        description="Testing YAML serialization",
        random_seed=123,
        parameter_sweep=sweep,
    )

    yaml_file = tmp_path / "exp_config.yaml"
    save_experiment_config(exp_orig, yaml_file)

    assert yaml_file.exists()

    exp_loaded = load_experiment_config(yaml_file)
    assert exp_loaded.experiment_id == "exp_yaml_test"
    assert exp_loaded.description == "Testing YAML serialization"
    assert exp_loaded.random_seed == 123
    assert exp_loaded.parameter_sweep.sample_sizes == [100, 200]
    assert exp_loaded.parameter_sweep.cause_thresholds == [0.45, 0.55]


def test_9_reproducibility_and_isolation():
    """Test 9: Deterministic behavior and isolation across multiple run generations."""
    sweep = ParameterSweepConfig(
        cause_thresholds=[0.40, 0.60],
        embedding_models=["all-MiniLM-L6-v2"],
    )
    exp = ExperimentConfig(
        experiment_id="exp_repro",
        parameter_sweep=sweep,
    )

    runs_gen1 = exp.generate_runs()
    runs_gen2 = exp.generate_runs()

    assert len(runs_gen1) == len(runs_gen2) == 2
    for r1, r2 in zip(runs_gen1, runs_gen2):
        assert r1.run_id == r2.run_id
        assert r1.to_dict() == r2.to_dict()
        assert r1.app_config.alignment.cause_threshold == r2.app_config.alignment.cause_threshold
        assert r1.app_config.alignment.embedding_model == r2.app_config.alignment.embedding_model


def test_10_missing_yaml_file_error(tmp_path):
    """Test 10: FileNotFoundError when attempting to load missing YAML file."""
    non_existent = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match="Experiment YAML file not found"):
        load_experiment_config(non_existent)
