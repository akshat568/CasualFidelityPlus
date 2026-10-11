"""Phase 12 Human Validation Pipeline Configuration.

Defines configuration parameters for orchestrating human annotation ingestion,
inter-annotator agreement calculation, consensus building, metric alignment,
statistical correlation analysis, and structured output artifact generation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class Phase12Config:
    """Master configuration for Phase 12 Human Validation & Statistical Analysis pipeline."""

    annotation_input_path: Union[str, Path]
    metric_input_paths: Optional[Union[str, Path, List[Union[str, Path]], Dict[str, Union[str, Path]]]] = None
    output_dir: Union[str, Path] = field(default_factory=lambda: Path("outputs/results"))
    human_annotations_output_path: Optional[Union[str, Path]] = field(
        default_factory=lambda: Path("data/annotations/human_annotations.jsonl")
    )
    human_validation_results_output_path: Optional[Union[str, Path]] = field(
        default_factory=lambda: Path("data/processed/human_validation_results.jsonl")
    )
    inter_annotator_stats_output_path: Optional[Union[str, Path]] = field(
        default_factory=lambda: Path("outputs/results/phase12_inter_annotator_stats.json")
    )
    statistical_analysis_stats_output_path: Optional[Union[str, Path]] = field(
        default_factory=lambda: Path("outputs/results/phase12_statistical_analysis_stats.json")
    )
    input_format: Optional[str] = None  # None (auto-detect), 'jsonl', 'csv'
    validation_behavior: str = "report"  # 'report', 'strict', 'skip'
    binary_mapping_enabled: bool = True
    allow_overwrite: bool = False

    def __post_init__(self):
        if isinstance(self.annotation_input_path, str) and not self.annotation_input_path.strip():
            raise ValueError("annotation_input_path must be specified.")

        if self.annotation_input_path is not None:
            self.annotation_input_path = Path(self.annotation_input_path)

        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        if isinstance(self.human_annotations_output_path, str):
            self.human_annotations_output_path = Path(self.human_annotations_output_path)

        if isinstance(self.human_validation_results_output_path, str):
            self.human_validation_results_output_path = Path(self.human_validation_results_output_path)

        if isinstance(self.inter_annotator_stats_output_path, str):
            self.inter_annotator_stats_output_path = Path(self.inter_annotator_stats_output_path)

        if isinstance(self.statistical_analysis_stats_output_path, str):
            self.statistical_analysis_stats_output_path = Path(self.statistical_analysis_stats_output_path)

        if self.metric_input_paths is not None:
            if isinstance(self.metric_input_paths, (str, Path)):
                self.metric_input_paths = [Path(self.metric_input_paths)]
            elif isinstance(self.metric_input_paths, list):
                self.metric_input_paths = [Path(p) for p in self.metric_input_paths]
            elif isinstance(self.metric_input_paths, dict):
                self.metric_input_paths = {k: Path(v) for k, v in self.metric_input_paths.items()}

        self.validate()

    def validate(self) -> None:
        """Validate pipeline configuration parameters."""
        if self.annotation_input_path is None or not str(self.annotation_input_path).strip():
            raise ValueError("annotation_input_path must be specified.")

        valid_behaviors = {"report", "strict", "skip"}
        if self.validation_behavior not in valid_behaviors:
            raise ValueError(
                f"Invalid validation_behavior '{self.validation_behavior}'. Expected one of {sorted(list(valid_behaviors))}."
            )

        if self.input_format is not None:
            valid_formats = {"jsonl", "json", "csv"}
            fmt = str(self.input_format).lower()
            if fmt not in valid_formats:
                raise ValueError(
                    f"Invalid input_format '{self.input_format}'. Expected one of {sorted(list(valid_formats))} or None."
                )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary representation."""
        metrics_serialized: Any = None
        if self.metric_input_paths is not None:
            if isinstance(self.metric_input_paths, list):
                metrics_serialized = [str(p) for p in self.metric_input_paths]
            elif isinstance(self.metric_input_paths, dict):
                metrics_serialized = {k: str(v) for k, v in self.metric_input_paths.items()}

        return {
            "annotation_input_path": str(self.annotation_input_path) if self.annotation_input_path else None,
            "metric_input_paths": metrics_serialized,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "human_annotations_output_path": (
                str(self.human_annotations_output_path) if self.human_annotations_output_path else None
            ),
            "human_validation_results_output_path": (
                str(self.human_validation_results_output_path) if self.human_validation_results_output_path else None
            ),
            "inter_annotator_stats_output_path": (
                str(self.inter_annotator_stats_output_path) if self.inter_annotator_stats_output_path else None
            ),
            "statistical_analysis_stats_output_path": (
                str(self.statistical_analysis_stats_output_path) if self.statistical_analysis_stats_output_path else None
            ),
            "input_format": self.input_format,
            "validation_behavior": self.validation_behavior,
            "binary_mapping_enabled": self.binary_mapping_enabled,
            "allow_overwrite": self.allow_overwrite,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Phase12Config":
        """Construct Phase12Config from dictionary."""
        return cls(
            annotation_input_path=data["annotation_input_path"],
            metric_input_paths=data.get("metric_input_paths"),
            output_dir=data.get("output_dir", "outputs/results"),
            human_annotations_output_path=data.get(
                "human_annotations_output_path", "data/annotations/human_annotations.jsonl"
            ),
            human_validation_results_output_path=data.get(
                "human_validation_results_output_path", "data/processed/human_validation_results.jsonl"
            ),
            inter_annotator_stats_output_path=data.get(
                "inter_annotator_stats_output_path", "outputs/results/phase12_inter_annotator_stats.json"
            ),
            statistical_analysis_stats_output_path=data.get(
                "statistical_analysis_stats_output_path", "outputs/results/phase12_statistical_analysis_stats.json"
            ),
            input_format=data.get("input_format"),
            validation_behavior=data.get("validation_behavior", "report"),
            binary_mapping_enabled=data.get("binary_mapping_enabled", True),
            allow_overwrite=data.get("allow_overwrite", False),
        )
