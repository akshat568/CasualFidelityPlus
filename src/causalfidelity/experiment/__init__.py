"""Experiment module for CausalFidelity+."""

from causalfidelity.experiment.ablation import (
    APPROVED_EXPERIMENT_IDS,
    AblationExperimentDefinition,
    AblationMatrixHarness,
    get_approved_matrix_definitions,
)
from causalfidelity.experiment.balancer import BenchmarkBalancer
from causalfidelity.experiment.config import (
    BenchmarkExpansionConfig,
    DatasetExperimentSettings,
    ExperimentConfig,
    ExperimentRunConfig,
    ParameterSweepConfig,
    load_experiment_config,
    save_experiment_config,
)
from causalfidelity.experiment.runner import (
    ExperimentRunner,
    RunManifest,
    StageExecutionRecord,
)
from causalfidelity.experiment.sampler import BenchmarkExpansionSampler

__all__ = [
    "APPROVED_EXPERIMENT_IDS",
    "AblationExperimentDefinition",
    "AblationMatrixHarness",
    "get_approved_matrix_definitions",
    "BenchmarkBalancer",
    "BenchmarkExpansionConfig",
    "BenchmarkExpansionSampler",
    "DatasetExperimentSettings",
    "ExperimentConfig",
    "ExperimentRunConfig",
    "ParameterSweepConfig",
    "load_experiment_config",
    "save_experiment_config",
    "ExperimentRunner",
    "RunManifest",
    "StageExecutionRecord",
]

