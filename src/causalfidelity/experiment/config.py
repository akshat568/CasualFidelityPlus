"""Experimental configuration module for CausalFidelity+.

Defines reproducible experiment runs, parameter sweeps (grid search),
isolated run output paths, benchmark expansion settings, and configuration validation.
"""

import copy
import itertools
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from causalfidelity.config import AppConfig, get_project_root, load_config
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DatasetExperimentSettings:
    """Dataset settings for experimental runs."""

    name: str = "xsum"
    hf_dataset_path: str = "EdinburghNLP/xsum"
    domain: str = "news"
    language: str = "en"
    split: str = "train"
    development_sample_size: int = 100
    streaming: bool = True

    def validate(self) -> None:
        """Validate dataset configuration settings."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Dataset name must be a non-empty string.")
        if not isinstance(self.development_sample_size, int) or self.development_sample_size <= 0:
            raise ValueError(
                f"development_sample_size must be a positive integer, got: {self.development_sample_size}"
            )


@dataclass
class BenchmarkExpansionConfig:
    """Configuration for benchmark dataset expansion and balancing."""

    target_quota_per_category: int = 10
    max_documents_to_process: int = 500
    sampling_seed: int = 42
    categories: List[str] = field(
        default_factory=lambda: [
            "REVERSED",
            "WEAKENED",
            "DROPPED",
            "CAUSE_CHANGED",
            "EFFECT_CHANGED",
        ]
    )
    expanded_output_file: str = "data/processed/expanded_benchmark.jsonl"
    balanced_output_file: str = "data/processed/balanced_benchmark.jsonl"
    expansion_stats_file: str = "outputs/results/benchmark_expansion_stats.json"
    balance_stats_file: str = "outputs/results/benchmark_balance_stats.json"
    summary_report_file: str = "outputs/results/benchmark_expansion_summary.md"

    def validate(self) -> None:
        """Validate benchmark expansion parameters."""
        if not isinstance(self.target_quota_per_category, int) or self.target_quota_per_category <= 0:
            raise ValueError(
                f"target_quota_per_category must be a positive integer, got: {self.target_quota_per_category}"
            )
        if not isinstance(self.max_documents_to_process, int) or self.max_documents_to_process <= 0:
            raise ValueError(
                f"max_documents_to_process must be a positive integer, got: {self.max_documents_to_process}"
            )
        if not isinstance(self.sampling_seed, int) or self.sampling_seed < 0:
            raise ValueError(f"sampling_seed must be a non-negative integer, got: {self.sampling_seed}")
        if not isinstance(self.categories, list) or len(self.categories) == 0:
            raise ValueError("categories must be a non-empty list of strings.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dict."""
        return {
            "target_quota_per_category": self.target_quota_per_category,
            "max_documents_to_process": self.max_documents_to_process,
            "sampling_seed": self.sampling_seed,
            "categories": self.categories,
            "expanded_output_file": self.expanded_output_file,
            "balanced_output_file": self.balanced_output_file,
            "expansion_stats_file": self.expansion_stats_file,
            "balance_stats_file": self.balance_stats_file,
            "summary_report_file": self.summary_report_file,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkExpansionConfig":
        """Construct BenchmarkExpansionConfig from dictionary."""
        return cls(
            target_quota_per_category=data.get("target_quota_per_category", 10),
            max_documents_to_process=data.get("max_documents_to_process", 500),
            sampling_seed=data.get("sampling_seed", 42),
            categories=data.get(
                "categories",
                ["REVERSED", "WEAKENED", "DROPPED", "CAUSE_CHANGED", "EFFECT_CHANGED"],
            ),
            expanded_output_file=data.get("expanded_output_file", "data/processed/expanded_benchmark.jsonl"),
            balanced_output_file=data.get("balanced_output_file", "data/processed/balanced_benchmark.jsonl"),
            expansion_stats_file=data.get("expansion_stats_file", "outputs/results/benchmark_expansion_stats.json"),
            balance_stats_file=data.get("balance_stats_file", "outputs/results/benchmark_balance_stats.json"),
            summary_report_file=data.get("summary_report_file", "outputs/results/benchmark_expansion_summary.md"),
        )


@dataclass
class ParameterSweepConfig:
    """Configuration for multi-parameter sweeps (grid search)."""

    sample_sizes: Optional[List[int]] = None
    random_seeds: Optional[List[int]] = None
    cause_thresholds: Optional[List[float]] = None
    effect_thresholds: Optional[List[float]] = None
    overall_thresholds: Optional[List[float]] = None
    embedding_models: Optional[List[str]] = None

    def validate(self) -> None:
        """Validate parameter sweep ranges and types."""
        if self.sample_sizes is not None:
            if not isinstance(self.sample_sizes, list) or len(self.sample_sizes) == 0:
                raise ValueError("sample_sizes must be a non-empty list of integers.")
            for sz in self.sample_sizes:
                if not isinstance(sz, int) or sz <= 0:
                    raise ValueError(f"Sample size must be a positive integer, got: {sz}")

        if self.random_seeds is not None:
            if not isinstance(self.random_seeds, list) or len(self.random_seeds) == 0:
                raise ValueError("random_seeds must be a non-empty list of integers.")
            for seed in self.random_seeds:
                if not isinstance(seed, int) or seed < 0:
                    raise ValueError(f"Random seed must be a non-negative integer, got: {seed}")

        for name, thresh_list in [
            ("cause_thresholds", self.cause_thresholds),
            ("effect_thresholds", self.effect_thresholds),
            ("overall_thresholds", self.overall_thresholds),
        ]:
            if thresh_list is not None:
                if not isinstance(thresh_list, list) or len(thresh_list) == 0:
                    raise ValueError(f"{name} must be a non-empty list of numbers.")
                for t in thresh_list:
                    if not isinstance(t, (int, float)) or not (0.0 <= t <= 1.0):
                        raise ValueError(f"{name} elements must be float between 0.0 and 1.0, got: {t}")

        if self.embedding_models is not None:
            if not isinstance(self.embedding_models, list) or len(self.embedding_models) == 0:
                raise ValueError("embedding_models must be a non-empty list of strings.")
            for model_name in self.embedding_models:
                if not isinstance(model_name, str) or not model_name.strip():
                    raise ValueError(f"Embedding model name must be a non-empty string, got: {model_name}")

    def get_sweep_grid(self) -> List[Dict[str, Any]]:
        """Generate deterministic combinations of all specified sweep parameters."""
        self.validate()

        grid_dims: Dict[str, List[Any]] = {}
        if self.sample_sizes is not None:
            grid_dims["development_sample_size"] = self.sample_sizes
        if self.random_seeds is not None:
            grid_dims["random_seed"] = self.random_seeds
        if self.cause_thresholds is not None:
            grid_dims["cause_threshold"] = self.cause_thresholds
        if self.effect_thresholds is not None:
            grid_dims["effect_threshold"] = self.effect_thresholds
        if self.overall_thresholds is not None:
            grid_dims["overall_threshold"] = self.overall_thresholds
        if self.embedding_models is not None:
            grid_dims["embedding_model"] = self.embedding_models

        if not grid_dims:
            return [{}]

        keys = list(grid_dims.keys())
        values = list(grid_dims.values())

        combinations: List[Dict[str, Any]] = []
        for combo in itertools.product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)

        return combinations

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter sweep config to dictionary."""
        return {
            "sample_sizes": self.sample_sizes,
            "random_seeds": self.random_seeds,
            "cause_thresholds": self.cause_thresholds,
            "effect_thresholds": self.effect_thresholds,
            "overall_thresholds": self.overall_thresholds,
            "embedding_models": self.embedding_models,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterSweepConfig":
        """Construct ParameterSweepConfig from dictionary."""
        return cls(
            sample_sizes=data.get("sample_sizes"),
            random_seeds=data.get("random_seeds"),
            cause_thresholds=data.get("cause_thresholds"),
            effect_thresholds=data.get("effect_thresholds"),
            overall_thresholds=data.get("overall_thresholds"),
            embedding_models=data.get("embedding_models"),
        )


@dataclass
class ExperimentConfig:
    """Master configuration for an experiment run or sweep suite."""

    experiment_id: str
    description: str = "Experimental framework evaluation run"
    dataset: DatasetExperimentSettings = field(default_factory=DatasetExperimentSettings)
    random_seed: int = 42
    output_dir: Path = field(default_factory=lambda: get_project_root() / "outputs" / "experiments")
    pipeline_config: Optional[AppConfig] = None
    parameter_sweep: Optional[ParameterSweepConfig] = None
    benchmark_expansion: Optional[BenchmarkExpansionConfig] = None

    def __post_init__(self):
        if self.pipeline_config is None:
            self.pipeline_config = load_config()
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        self.validate()

    def validate(self) -> None:
        """Validate experiment configuration parameters."""
        if not self.experiment_id or not isinstance(self.experiment_id, str):
            raise ValueError("experiment_id must be a non-empty string.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", self.experiment_id):
            raise ValueError(
                f"experiment_id '{self.experiment_id}' must contain only alphanumeric characters, underscores, or hyphens."
            )
        if not isinstance(self.random_seed, int) or self.random_seed < 0:
            raise ValueError(f"random_seed must be a non-negative integer, got: {self.random_seed}")

        if self.dataset:
            self.dataset.validate()

        if self.parameter_sweep:
            self.parameter_sweep.validate()

        if self.benchmark_expansion:
            self.benchmark_expansion.validate()

    def generate_runs(self) -> List["ExperimentRunConfig"]:
        """Generate deterministic run configurations for each parameter combination in the sweep."""
        self.validate()

        grid = self.parameter_sweep.get_sweep_grid() if self.parameter_sweep else [{}]
        runs: List[ExperimentRunConfig] = []

        for idx, param_comb in enumerate(grid, start=1):
            run_id = f"{self.experiment_id}_run_{idx:03d}"
            run_seed = param_comb.get("random_seed", self.random_seed)
            sample_sz = param_comb.get("development_sample_size", self.dataset.development_sample_size)

            run_dir = self.output_dir / self.experiment_id / "runs" / run_id

            # Deep copy AppConfig and apply overrides cleanly
            app_cfg = copy.deepcopy(self.pipeline_config)
            app_cfg.project.seed = run_seed
            app_cfg.dataset.random_seed = run_seed
            app_cfg.dataset.development_sample_size = sample_sz

            # Apply threshold and model overrides if present
            if "cause_threshold" in param_comb:
                app_cfg.alignment.cause_threshold = param_comb["cause_threshold"]
                app_cfg.causal_distortion.cause_threshold = param_comb["cause_threshold"]
            if "effect_threshold" in param_comb:
                app_cfg.alignment.effect_threshold = param_comb["effect_threshold"]
                app_cfg.causal_distortion.effect_threshold = param_comb["effect_threshold"]
            if "overall_threshold" in param_comb:
                app_cfg.alignment.overall_threshold = param_comb["overall_threshold"]
                app_cfg.causal_distortion.overall_threshold = param_comb["overall_threshold"]
            if "embedding_model" in param_comb:
                app_cfg.alignment.embedding_model = param_comb["embedding_model"]

            # Set isolated output paths for the run
            app_cfg.paths.output_dir = run_dir
            app_cfg.paths.processed_data_dir = run_dir / "data"

            run_cfg = ExperimentRunConfig(
                run_id=run_id,
                experiment_id=self.experiment_id,
                run_number=idx,
                seed=run_seed,
                sample_size=sample_sz,
                parameters=param_comb,
                run_output_dir=run_dir,
                app_config=app_cfg,
            )
            runs.append(run_cfg)

        return runs

    def to_dict(self) -> Dict[str, Any]:
        """Convert experiment configuration to dictionary format."""
        return {
            "experiment_id": self.experiment_id,
            "description": self.description,
            "dataset": asdict(self.dataset),
            "random_seed": self.random_seed,
            "output_dir": str(self.output_dir),
            "parameter_sweep": self.parameter_sweep.to_dict() if self.parameter_sweep else None,
            "benchmark_expansion": self.benchmark_expansion.to_dict() if self.benchmark_expansion else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], pipeline_config: Optional[AppConfig] = None) -> "ExperimentConfig":
        """Construct ExperimentConfig from dictionary."""
        ds_data = data.get("dataset", {})
        ds_settings = DatasetExperimentSettings(
            name=ds_data.get("name", "xsum"),
            hf_dataset_path=ds_data.get("hf_dataset_path", "EdinburghNLP/xsum"),
            domain=ds_data.get("domain", "news"),
            language=ds_data.get("language", "en"),
            split=ds_data.get("split", "train"),
            development_sample_size=ds_data.get("development_sample_size", 100),
            streaming=ds_data.get("streaming", True),
        )

        sweep_data = data.get("parameter_sweep")
        sweep_cfg = ParameterSweepConfig.from_dict(sweep_data) if sweep_data else None

        exp_data = data.get("benchmark_expansion")
        exp_cfg = BenchmarkExpansionConfig.from_dict(exp_data) if exp_data else None

        out_dir = Path(data.get("output_dir", get_project_root() / "outputs" / "experiments"))

        return cls(
            experiment_id=data["experiment_id"],
            description=data.get("description", "Experimental framework evaluation run"),
            dataset=ds_settings,
            random_seed=data.get("random_seed", 42),
            output_dir=out_dir,
            pipeline_config=pipeline_config,
            parameter_sweep=sweep_cfg,
            benchmark_expansion=exp_cfg,
        )


@dataclass
class ExperimentRunConfig:
    """Configuration for an isolated, individual experiment run within a sweep."""

    run_id: str
    experiment_id: str
    run_number: int
    seed: int
    sample_size: int
    parameters: Dict[str, Any]
    run_output_dir: Path
    app_config: AppConfig

    def __post_init__(self):
        if isinstance(self.run_output_dir, str):
            self.run_output_dir = Path(self.run_output_dir)
        self.validate()

    def validate(self) -> None:
        """Validate run parameters and isolated output path."""
        if not self.run_id or not isinstance(self.run_id, str):
            raise ValueError("run_id must be a non-empty string.")
        if not self.experiment_id or not isinstance(self.experiment_id, str):
            raise ValueError("experiment_id must be a non-empty string.")
        if not isinstance(self.run_number, int) or self.run_number <= 0:
            raise ValueError(f"run_number must be a positive integer, got: {self.run_number}")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError(f"seed must be a non-negative integer, got: {self.seed}")
        if not isinstance(self.sample_size, int) or self.sample_size <= 0:
            raise ValueError(f"sample_size must be a positive integer, got: {self.sample_size}")
        if self.app_config is None:
            raise ValueError("app_config cannot be None.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert run configuration to dictionary."""
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "run_number": self.run_number,
            "seed": self.seed,
            "sample_size": self.sample_size,
            "parameters": self.parameters,
            "run_output_dir": str(self.run_output_dir),
        }


def load_experiment_config(yaml_path: Union[str, Path]) -> ExperimentConfig:
    """Load experiment configuration from YAML file.

    Args:
        yaml_path: Path to YAML configuration file.

    Returns:
        Validated ExperimentConfig instance.
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Experiment YAML file not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return ExperimentConfig.from_dict(data)


def save_experiment_config(config: ExperimentConfig, yaml_path: Union[str, Path]) -> None:
    """Save experiment configuration to YAML file.

    Args:
        config: ExperimentConfig instance.
        yaml_path: Destination YAML path.
    """
    yaml_path = Path(yaml_path)
    ensure_dir(yaml_path.parent)

    data = config.to_dict()
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
