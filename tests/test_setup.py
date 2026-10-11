"""Basic setup and configuration tests for CausalFidelity+."""

import logging
from pathlib import Path

import pytest

import causalfidelity
from causalfidelity.config import AppConfig, load_config
from causalfidelity.utils.io import ensure_dir, load_json, load_yaml, save_json, save_yaml
from causalfidelity.utils.logging import get_logger, setup_logging


def test_package_import_and_version():
    """Verify package importability and version declaration."""
    assert hasattr(causalfidelity, "__version__")
    assert causalfidelity.__version__ == "0.1.0"


def test_load_default_config():
    """Verify loading default base.yaml configuration."""
    config = load_config()

    assert isinstance(config, AppConfig)
    assert config.project.name == "CausalFidelityPlus"
    assert config.project.environment == "development"
    assert config.project.seed == 42

    # Check path object types and structure
    assert isinstance(config.paths.root_dir, Path)
    assert isinstance(config.paths.data_dir, Path)
    assert isinstance(config.paths.output_dir, Path)
    assert config.paths.data_dir.name == "data"
    assert config.paths.output_dir.name == "outputs"


def test_logging_setup(tmp_path):
    """Verify logging configuration and logger instance generation."""
    log_file = tmp_path / "test_run.log"
    setup_logging(level="DEBUG", log_file=log_file)

    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    logger.debug("Debug message test for setup")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Debug message test for setup" in content


def test_io_utilities(tmp_path):
    """Verify directory creation, YAML, and JSON read/write helpers."""
    test_dir = tmp_path / "sub_folder"
    ensured = ensure_dir(test_dir)
    assert ensured.exists()
    assert ensured.is_dir()

    # YAML I/O
    yaml_file = test_dir / "sample.yaml"
    sample_data = {"key": "value", "numbers": [1, 2, 3]}
    save_yaml(sample_data, yaml_file)
    assert yaml_file.exists()
    loaded_yaml = load_yaml(yaml_file)
    assert loaded_yaml == sample_data

    # JSON I/O
    json_file = test_dir / "sample.json"
    save_json(sample_data, json_file)
    assert json_file.exists()
    loaded_json = load_json(json_file)
    assert loaded_json == sample_data
