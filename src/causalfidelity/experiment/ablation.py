"""Ablation Experiment Execution Harness and Matrix Generator for Phase 13.

Defines the approved 9-experiment matrix, validates configuration overrides,
generates isolated run configurations, enforces output path safety, and provides
deterministic matrix serialization.
"""

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from causalfidelity.config import AppConfig, get_project_root, load_config
from causalfidelity.experiment.config import (
    BenchmarkExpansionConfig,
    DatasetExperimentSettings,
    ExperimentConfig,
    ExperimentRunConfig,
    ParameterSweepConfig,
)
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)

# List of the 9 approved experiment IDs in deterministic order
APPROVED_EXPERIMENT_IDS: List[str] = [
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


@dataclass
class AblationExperimentDefinition:
    """Structured definition of a single ablation experiment in the matrix."""

    experiment_id: str
    category: str
    description: str
    parameter_overrides: Dict[str, Any] = field(default_factory=dict)
    controlled_variables: Dict[str, Any] = field(default_factory=dict)
    dataset_settings: Dict[str, Any] = field(default_factory=dict)
    evaluation_metrics: List[str] = field(default_factory=list)
    required_input_artifacts: List[str] = field(default_factory=list)
    expected_output_artifacts: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate experiment definition parameters and override constraints."""
        if not self.experiment_id or not isinstance(self.experiment_id, str):
            raise ValueError("experiment_id must be a non-empty string.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", self.experiment_id):
            raise ValueError(
                f"experiment_id '{self.experiment_id}' must contain only alphanumeric characters, underscores, or hyphens."
            )
        if self.experiment_id not in APPROVED_EXPERIMENT_IDS:
            raise ValueError(
                f"Unrecognized experiment_id '{self.experiment_id}'. Must be one of approved IDs: {APPROVED_EXPERIMENT_IDS}"
            )
        if not self.category or not isinstance(self.category, str):
            raise ValueError("category must be a non-empty string.")
        if not self.description or not isinstance(self.description, str):
            raise ValueError("description must be a non-empty string.")

        # Validate parameter overrides if present
        for key, val in self.parameter_overrides.items():
            if key in ("cause_threshold", "effect_threshold", "overall_threshold", "ambiguity_margin"):
                if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
                    raise ValueError(f"Override '{key}' must be a float between 0.0 and 1.0, got: {val}")
            elif key in ("cause_weight", "effect_weight", "relation_weight"):
                if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
                    raise ValueError(f"Override '{key}' must be a float between 0.0 and 1.0, got: {val}")
            elif key in ("summac_enabled", "factcc_enabled", "bertscore_enabled"):
                if not isinstance(val, bool):
                    raise ValueError(f"Override '{key}' must be a boolean, got: {type(val).__name__}")
            elif key in ("seed", "random_seed"):
                if not isinstance(val, int) or val < 0:
                    raise ValueError(f"Override '{key}' must be a non-negative integer, got: {val}")
            elif key in ("development_sample_size", "sample_size"):
                if not isinstance(val, int) or val <= 0:
                    raise ValueError(f"Override '{key}' must be a positive integer, got: {val}")

        # Validate weighting sum if all three weights are specified
        weights = [self.parameter_overrides.get(k) for k in ("cause_weight", "effect_weight", "relation_weight")]
        if all(w is not None for w in weights):
            w_sum = sum(weights)
            if abs(w_sum - 1.0) > 0.01:
                raise ValueError(
                    f"Alignment weights cause_weight ({weights[0]}), effect_weight ({weights[1]}), relation_weight ({weights[2]}) must sum to 1.0, got sum={w_sum:.4f}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert experiment definition to dictionary format with sorted keys."""
        return {
            "experiment_id": self.experiment_id,
            "category": self.category,
            "description": self.description,
            "parameter_overrides": self.parameter_overrides,
            "controlled_variables": self.controlled_variables,
            "dataset_settings": self.dataset_settings,
            "evaluation_metrics": self.evaluation_metrics,
            "required_input_artifacts": self.required_input_artifacts,
            "expected_output_artifacts": self.expected_output_artifacts,
            "notes": self.notes,
        }


def get_approved_matrix_definitions() -> Dict[str, AblationExperimentDefinition]:
    """Construct and return dictionary of the 9 approved ablation experiment definitions.

    Returns:
        Dict mapping experiment_id to AblationExperimentDefinition.
    """
    matrix: Dict[str, AblationExperimentDefinition] = {}

    # EXP_01_BASELINE
    matrix["EXP_01_BASELINE"] = AblationExperimentDefinition(
        experiment_id="EXP_01_BASELINE",
        category="Baseline",
        description="Baseline evaluation run with standard default thresholds, weights, and all metrics enabled.",
        parameter_overrides={},
        controlled_variables={
            "seed": 42,
            "sample_size": 100,
            "cause_threshold": 0.50,
            "effect_threshold": 0.50,
            "overall_threshold": 0.60,
            "cause_weight": 0.45,
            "effect_weight": 0.45,
            "relation_weight": 0.10,
        },
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "FactCC", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/causal_distortion_analysis.jsonl",
            "data/processed/phase10a_summac_results.jsonl",
            "data/processed/phase10b_factcc_results.jsonl",
            "data/processed/phase10c_bertscore_results.jsonl",
            "data/processed/phase10d_cross_metric_analysis.jsonl",
        ],
        notes="Serves as control baseline for all threshold, weight, and component ablations.",
    )

    # EXP_02_THRESH_PERMISSIVE
    matrix["EXP_02_THRESH_PERMISSIVE"] = AblationExperimentDefinition(
        experiment_id="EXP_02_THRESH_PERMISSIVE",
        category="Similarity Threshold Ablation",
        description="Permissive similarity thresholds (cause=0.35, effect=0.35, overall=0.45) to analyze false positive behavior.",
        parameter_overrides={
            "cause_threshold": 0.35,
            "effect_threshold": 0.35,
            "overall_threshold": 0.45,
        },
        controlled_variables={
            "seed": 42,
            "sample_size": 100,
            "cause_weight": 0.45,
            "effect_weight": 0.45,
            "relation_weight": 0.10,
        },
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "FactCC", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/causal_distortion_analysis.jsonl",
            "outputs/results/distortion_stats.json",
        ],
        notes="Evaluates precision loss and false alignment candidate acceptance under low similarity bounds.",
    )

    # EXP_03_THRESH_STRICT
    matrix["EXP_03_THRESH_STRICT"] = AblationExperimentDefinition(
        experiment_id="EXP_03_THRESH_STRICT",
        category="Similarity Threshold Ablation",
        description="Strict similarity thresholds (cause=0.65, effect=0.65, overall=0.75) to evaluate recall impact.",
        parameter_overrides={
            "cause_threshold": 0.65,
            "effect_threshold": 0.65,
            "overall_threshold": 0.75,
        },
        controlled_variables={
            "seed": 42,
            "sample_size": 100,
            "cause_weight": 0.45,
            "effect_weight": 0.45,
            "relation_weight": 0.10,
        },
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "FactCC", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/causal_distortion_analysis.jsonl",
            "outputs/results/distortion_stats.json",
        ],
        notes="Evaluates false negative rate increase and fallback to INSUFFICIENT_EVIDENCE under strict bounds.",
    )

    # EXP_04_WEIGHT_EQUAL
    matrix["EXP_04_WEIGHT_EQUAL"] = AblationExperimentDefinition(
        experiment_id="EXP_04_WEIGHT_EQUAL",
        category="Weighting Model Ablation",
        description="Equal weighting distribution across cause, effect, and relation trigger (cause=0.33, effect=0.33, relation=0.34).",
        parameter_overrides={
            "cause_weight": 0.33,
            "effect_weight": 0.33,
            "relation_weight": 0.34,
        },
        controlled_variables={
            "seed": 42,
            "sample_size": 100,
            "cause_threshold": 0.50,
            "effect_threshold": 0.50,
            "overall_threshold": 0.60,
        },
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "FactCC", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/causal_alignments.jsonl",
            "data/processed/causal_distortion_analysis.jsonl",
        ],
        notes="Evaluates impact of increasing relation trigger syntax weighting relative to argument semantics.",
    )

    # EXP_05_WEIGHT_ARG_ONLY
    matrix["EXP_05_WEIGHT_ARG_ONLY"] = AblationExperimentDefinition(
        experiment_id="EXP_05_WEIGHT_ARG_ONLY",
        category="Weighting Model Ablation",
        description="Pure argument semantic weighting ignoring relation trigger text (cause=0.50, effect=0.50, relation=0.00).",
        parameter_overrides={
            "cause_weight": 0.50,
            "effect_weight": 0.50,
            "relation_weight": 0.00,
        },
        controlled_variables={
            "seed": 42,
            "sample_size": 100,
            "cause_threshold": 0.50,
            "effect_threshold": 0.50,
            "overall_threshold": 0.60,
        },
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "FactCC", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/causal_alignments.jsonl",
            "data/processed/causal_distortion_analysis.jsonl",
        ],
        notes="Isolates cause and effect vector similarity without trigger word compatibility filtering.",
    )

    # EXP_06_ABLATE_SUMMAC
    matrix["EXP_06_ABLATE_SUMMAC"] = AblationExperimentDefinition(
        experiment_id="EXP_06_ABLATE_SUMMAC",
        category="Individual Component Ablation",
        description="Component ablation disabling Phase 10A SummaCConv evaluation (summac_enabled=False).",
        parameter_overrides={"summac_enabled": False},
        controlled_variables={"seed": 42, "sample_size": 100},
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "FactCC", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/phase10b_factcc_results.jsonl",
            "data/processed/phase10c_bertscore_results.jsonl",
        ],
        notes="Verifies framework safety and downstream execution when NLI consistency metric SummaC is disabled.",
    )

    # EXP_07_ABLATE_FACTCC
    matrix["EXP_07_ABLATE_FACTCC"] = AblationExperimentDefinition(
        experiment_id="EXP_07_ABLATE_FACTCC",
        category="Individual Component Ablation",
        description="Component ablation disabling Phase 10B FactCC evaluation (factcc_enabled=False).",
        parameter_overrides={"factcc_enabled": False},
        controlled_variables={"seed": 42, "sample_size": 100},
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "BERTScore"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/phase10a_summac_results.jsonl",
            "data/processed/phase10c_bertscore_results.jsonl",
        ],
        notes="Verifies framework safety and downstream execution when BERT classifier FactCC is disabled.",
    )

    # EXP_08_ABLATE_BERTSCORE
    matrix["EXP_08_ABLATE_BERTSCORE"] = AblationExperimentDefinition(
        experiment_id="EXP_08_ABLATE_BERTSCORE",
        category="Individual Component Ablation",
        description="Component ablation disabling Phase 10C BERTScore evaluation (bertscore_enabled=False).",
        parameter_overrides={"bertscore_enabled": False},
        controlled_variables={"seed": 42, "sample_size": 100},
        dataset_settings={"name": "xsum", "sample_size": 100, "split": "train"},
        evaluation_metrics=["CausalDistortion", "SummaCConv", "FactCC"],
        required_input_artifacts=["data/processed/xsum_dev.jsonl"],
        expected_output_artifacts=[
            "data/processed/phase10a_summac_results.jsonl",
            "data/processed/phase10b_factcc_results.jsonl",
        ],
        notes="Verifies framework safety and downstream execution when BERTScore embedding similarity control is disabled.",
    )

    # EXP_09_HUMAN_CORRELATION
    matrix["EXP_09_HUMAN_CORRELATION"] = AblationExperimentDefinition(
        experiment_id="EXP_09_HUMAN_CORRELATION",
        category="Evaluation Metric Comparison",
        description="Statistical correlation evaluation comparing baseline automated metric scores against Phase 12 human consensus annotations.",
        parameter_overrides={},
        controlled_variables={"seed": 42, "binary_mapping_enabled": True},
        dataset_settings={"name": "human_annotations", "source": "data/annotations/human_annotations.jsonl"},
        evaluation_metrics=[
            "Pearson_r",
            "Spearman_rho",
            "ROC_AUC",
            "InterAnnotatorAgreement",
            "CategorySensitivity",
        ],
        required_input_artifacts=[
            "data/annotations/human_annotations.jsonl",
            "data/processed/causal_distortion_analysis.jsonl",
            "data/processed/phase10a_summac_results.jsonl",
            "data/processed/phase10b_factcc_results.jsonl",
            "data/processed/phase10c_bertscore_results.jsonl",
        ],
        expected_output_artifacts=[
            "data/processed/human_validation_results.jsonl",
            "outputs/results/phase12_inter_annotator_stats.json",
            "outputs/results/phase12_statistical_analysis_stats.json",
        ],
        notes="Evaluates statistical alignment (Pearson r, Spearman rho, ROC-AUC) against Phase 12 human consensus labels. Explicitly excludes unresolved annotator disagreements from binary distortion targets.",
    )

    return matrix


class AblationMatrixHarness:
    """Master harness for building, validating, and managing the Phase 13 experimental matrix."""

    def __init__(
        self,
        base_config: Optional[AppConfig] = None,
        base_output_dir: Optional[Union[str, Path]] = None,
    ):
        """Initialize AblationMatrixHarness.

        Args:
            base_config: Optional AppConfig instance (defaults to loaded base.yaml).
            base_output_dir: Optional path for experiment output root (defaults to outputs/experiments).
        """
        self.base_config = copy.deepcopy(base_config) if base_config else load_config()
        root_proj = get_project_root()
        self.base_output_dir = Path(base_output_dir) if base_output_dir else (root_proj / "outputs" / "experiments")
        self._matrix_definitions = get_approved_matrix_definitions()

    def list_experiment_ids(self) -> List[str]:
        """Return list of all 9 approved experiment IDs in deterministic order."""
        return list(APPROVED_EXPERIMENT_IDS)

    def get_experiment_definition(self, experiment_id: str) -> AblationExperimentDefinition:
        """Retrieve definition for a specific experiment ID.

        Args:
            experiment_id: Approved experiment ID string.

        Returns:
            AblationExperimentDefinition instance.
        """
        if experiment_id not in self._matrix_definitions:
            raise KeyError(
                f"Experiment ID '{experiment_id}' not found in matrix. Available IDs: {self.list_experiment_ids()}"
            )
        return copy.deepcopy(self._matrix_definitions[experiment_id])

    def get_all_experiment_definitions(self) -> Dict[str, AblationExperimentDefinition]:
        """Return dictionary of all matrix experiment definitions."""
        return copy.deepcopy(self._matrix_definitions)

    def apply_overrides(self, app_config: AppConfig, overrides: Dict[str, Any]) -> AppConfig:
        """Apply parameter overrides cleanly onto a deep copy of AppConfig.

        Args:
            app_config: AppConfig instance to modify.
            overrides: Parameter override dictionary.

        Returns:
            Updated AppConfig instance.
        """
        cfg = copy.deepcopy(app_config)

        # Threshold overrides (update both alignment and distortion configs)
        if "cause_threshold" in overrides:
            cfg.alignment.cause_threshold = float(overrides["cause_threshold"])
            cfg.causal_distortion.cause_threshold = float(overrides["cause_threshold"])
        if "effect_threshold" in overrides:
            cfg.alignment.effect_threshold = float(overrides["effect_threshold"])
            cfg.causal_distortion.effect_threshold = float(overrides["effect_threshold"])
        if "overall_threshold" in overrides:
            cfg.alignment.overall_threshold = float(overrides["overall_threshold"])
            cfg.causal_distortion.overall_threshold = float(overrides["overall_threshold"])
        if "ambiguity_margin" in overrides:
            cfg.alignment.ambiguity_margin = float(overrides["ambiguity_margin"])

        # Weight overrides
        if "cause_weight" in overrides:
            cfg.alignment.cause_weight = float(overrides["cause_weight"])
        if "effect_weight" in overrides:
            cfg.alignment.effect_weight = float(overrides["effect_weight"])
        if "relation_weight" in overrides:
            cfg.alignment.relation_weight = float(overrides["relation_weight"])

        # Model & toggle overrides
        if "embedding_model" in overrides:
            cfg.alignment.embedding_model = str(overrides["embedding_model"])
        if "summac_enabled" in overrides:
            cfg.metrics.summac.enabled = bool(overrides["summac_enabled"])
        if "factcc_enabled" in overrides:
            cfg.metrics.factcc.enabled = bool(overrides["factcc_enabled"])
        if "bertscore_enabled" in overrides:
            cfg.metrics.bertscore.enabled = bool(overrides["bertscore_enabled"])

        # Seed & sample size overrides
        if "seed" in overrides or "random_seed" in overrides:
            s_val = int(overrides.get("seed", overrides.get("random_seed")))
            cfg.project.seed = s_val
            cfg.dataset.random_seed = s_val
        if "development_sample_size" in overrides or "sample_size" in overrides:
            sz_val = int(overrides.get("development_sample_size", overrides.get("sample_size")))
            cfg.dataset.development_sample_size = sz_val

        return cfg

    def create_app_config_for_experiment(self, experiment_id: str) -> AppConfig:
        """Generate isolated AppConfig instance for a specific experiment ID.

        Args:
            experiment_id: Approved experiment ID.

        Returns:
            AppConfig configured with experiment overrides and isolated output paths.
        """
        defn = self.get_experiment_definition(experiment_id)
        exp_dir = self.base_output_dir / experiment_id

        # Deep copy base config and apply overrides
        app_cfg = self.apply_overrides(self.base_config, defn.parameter_overrides)

        # Enforce strict path isolation
        app_cfg.paths.root_dir = exp_dir
        app_cfg.paths.data_dir = exp_dir / "data"
        app_cfg.paths.processed_data_dir = exp_dir / "data" / "processed"
        app_cfg.paths.output_dir = exp_dir / "outputs"
        app_cfg.paths.results_dir = exp_dir / "outputs" / "results"
        app_cfg.paths.metrics_dir = exp_dir / "outputs" / "metrics"

        return app_cfg

    def create_experiment_run_config(
        self, experiment_id: str, run_number: int = 1
    ) -> ExperimentRunConfig:
        """Create isolated ExperimentRunConfig for an experiment.

        Args:
            experiment_id: Approved experiment ID.
            run_number: Integer run number (default 1).

        Returns:
            ExperimentRunConfig object ready for execution.
        """
        defn = self.get_experiment_definition(experiment_id)
        run_id = f"{experiment_id}_run_{run_number:03d}"
        run_dir = self.base_output_dir / experiment_id / "runs" / run_id

        app_cfg = self.create_app_config_for_experiment(experiment_id)
        # Update run-specific paths
        app_cfg.paths.root_dir = run_dir
        app_cfg.paths.processed_data_dir = run_dir / "data" / "processed"
        app_cfg.paths.output_dir = run_dir / "outputs"
        app_cfg.paths.results_dir = run_dir / "outputs" / "results"
        app_cfg.paths.metrics_dir = run_dir / "outputs" / "metrics"

        seed_val = defn.controlled_variables.get("seed", 42)
        sample_sz = defn.dataset_settings.get("sample_size", 100)

        return ExperimentRunConfig(
            run_id=run_id,
            experiment_id=experiment_id,
            run_number=run_number,
            seed=seed_val,
            sample_size=sample_sz,
            parameters=defn.parameter_overrides,
            run_output_dir=run_dir,
            app_config=app_cfg,
        )

    def create_master_experiment_config(self, experiment_id: str) -> ExperimentConfig:
        """Create master ExperimentConfig instance for an experiment.

        Args:
            experiment_id: Approved experiment ID.

        Returns:
            ExperimentConfig object.
        """
        defn = self.get_experiment_definition(experiment_id)
        app_cfg = self.create_app_config_for_experiment(experiment_id)
        exp_dir = self.base_output_dir / experiment_id

        ds_settings = DatasetExperimentSettings(
            name=defn.dataset_settings.get("name", "xsum"),
            development_sample_size=defn.dataset_settings.get("sample_size", 100),
            split=defn.dataset_settings.get("split", "train"),
        )

        return ExperimentConfig(
            experiment_id=experiment_id,
            description=defn.description,
            dataset=ds_settings,
            random_seed=defn.controlled_variables.get("seed", 42),
            output_dir=exp_dir,
            pipeline_config=app_cfg,
        )

    def check_output_safety(
        self, experiment_id: str, allow_overwrite: bool = False
    ) -> Dict[str, Any]:
        """Verify output path safety and prevent accidental overwriting of existing run results.

        Args:
            experiment_id: Approved experiment ID.
            allow_overwrite: If True, permit overwriting existing experiment outputs.

        Returns:
            Dict containing safety evaluation details.
        """
        exp_dir = self.base_output_dir / experiment_id
        manifest_file = exp_dir / "run_manifest.json"

        exists = exp_dir.exists()
        has_manifest = manifest_file.exists()

        if has_manifest and not allow_overwrite:
            raise FileExistsError(
                f"Existing experiment results found at '{exp_dir}' (manifest: {manifest_file}). "
                "Set allow_overwrite=True to enable overwriting existing experiment outputs."
            )

        return {
            "experiment_id": experiment_id,
            "output_dir": str(exp_dir),
            "directory_exists": exists,
            "manifest_exists": has_manifest,
            "safety_status": "overwrite_permitted" if allow_overwrite else "safe_to_write",
        }

    def validate_matrix(self) -> Dict[str, Any]:
        """Validate all 9 approved experiment definitions and configuration applications.

        Returns:
            Dictionary containing matrix validation results.
        """
        results: Dict[str, Any] = {
            "total_experiments": len(APPROVED_EXPERIMENT_IDS),
            "approved_experiment_ids": APPROVED_EXPERIMENT_IDS,
            "validated_count": 0,
            "experiments": {},
            "status": "VALID",
        }

        for exp_id in APPROVED_EXPERIMENT_IDS:
            defn = self.get_experiment_definition(exp_id)
            app_cfg = self.create_app_config_for_experiment(exp_id)
            run_cfg = self.create_experiment_run_config(exp_id)

            results["experiments"][exp_id] = {
                "category": defn.category,
                "overrides_count": len(defn.parameter_overrides),
                "parameter_overrides": defn.parameter_overrides,
                "app_config_cause_threshold": app_cfg.alignment.cause_threshold,
                "app_config_cause_weight": app_cfg.alignment.cause_weight,
                "app_config_summac_enabled": app_cfg.metrics.summac.enabled,
                "run_output_dir": str(run_cfg.run_output_dir),
                "status": "VALID",
            }
            results["validated_count"] += 1

        logger.info(
            f"Ablation Matrix Validation Complete. Successfully validated {results['validated_count']}/{len(APPROVED_EXPERIMENT_IDS)} experiments."
        )
        return results

    def export_matrix_manifest(
        self, destination_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """Export deterministic JSON manifest of all 9 experiment definitions.

        Args:
            destination_path: Optional output file path. Defaults to outputs/results/ablation_matrix_manifest.json.

        Returns:
            Path to written JSON manifest file.
        """
        root_proj = get_project_root()
        out_path = Path(destination_path) if destination_path else (root_proj / "outputs" / "results" / "ablation_matrix_manifest.json")
        ensure_dir(out_path.parent)

        manifest_data = {
            "matrix_name": "Phase 13 Ablation Study Experimental Matrix",
            "version": "1.0",
            "total_experiments": len(APPROVED_EXPERIMENT_IDS),
            "experiment_ids": APPROVED_EXPERIMENT_IDS,
            "experiments": {
                exp_id: self.get_experiment_definition(exp_id).to_dict()
                for exp_id in APPROVED_EXPERIMENT_IDS
            },
        }

        save_json(manifest_data, out_path, indent=2)
        logger.info(f"Exported ablation matrix manifest to {out_path}")
        return out_path
