"""Configuration module for CausalFidelity+."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


def get_project_root() -> Path:
    """Return absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class ProjectConfig:
    name: str = "CausalFidelityPlus"
    environment: str = "development"
    seed: int = 42


@dataclass
class CausalFilterConfig:
    enabled: bool = True
    phrases: List[str] = field(
        default_factory=lambda: [
            "caused",
            "causes",
            "causing",
            "led to",
            "resulted in",
            "due to",
            "because",
            "therefore",
            "as a result",
            "resulted from",
            "contributed to",
            "triggered",
            "owing to",
            "since",
        ]
    )


@dataclass
class DatasetConfig:
    name: str = "xsum"
    hf_dataset_path: str = "EdinburghNLP/xsum"
    domain: str = "news"
    language: str = "en"
    split: str = "train"
    development_sample_size: int = 100
    random_seed: int = 42
    streaming: bool = True
    causal_candidate_filter: CausalFilterConfig = field(default_factory=CausalFilterConfig)


@dataclass
class PathConfig:
    root_dir: Path = field(default_factory=get_project_root)
    data_dir: Path = field(default_factory=lambda: get_project_root() / "data")
    raw_data_dir: Path = field(default_factory=lambda: get_project_root() / "data" / "raw")
    processed_data_dir: Path = field(default_factory=lambda: get_project_root() / "data" / "processed")
    annotations_dir: Path = field(default_factory=lambda: get_project_root() / "data" / "annotations")
    output_dir: Path = field(default_factory=lambda: get_project_root() / "outputs")
    metrics_dir: Path = field(default_factory=lambda: get_project_root() / "outputs" / "metrics")
    results_dir: Path = field(default_factory=lambda: get_project_root() / "outputs" / "results")


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = False
    log_file: Optional[Path] = None


@dataclass
class CausalExtractionConfig:
    enabled: bool = True
    method: str = "rule_based"
    confidence_default: float = 0.90
    candidate_only: bool = True
    max_documents: Optional[int] = 100
    output_file: str = "data/processed/causal_relations.jsonl"
    stats_file: str = "data/processed/causal_relations_stats.json"
    sample_output_file: str = "outputs/results/phase3_extraction_sample.json"


@dataclass
class CausalGraphConfig:
    enabled: bool = True
    input_file: str = "data/processed/causal_relations.jsonl"
    output_file: str = "data/processed/causal_graphs.jsonl"
    stats_file: str = "data/processed/causal_graphs_stats.json"
    sample_output_file: str = "outputs/results/phase4_graph_sample.json"


@dataclass
class SummaryInputConfig:
    enabled: bool = True
    input_file: str = "data/processed/xsum_dev.jsonl"
    output_file: str = "data/processed/summary_inputs.jsonl"
    stats_file: str = "data/processed/summary_inputs_stats.json"
    sample_output_file: str = "outputs/results/phase5_summary_sample.json"


@dataclass
class PerturbationConfig:
    enabled: bool = True
    input_summary_path: str = "data/processed/summary_inputs.jsonl"
    input_causal_relations_path: str = "data/processed/causal_relations.jsonl"
    output_path: str = "data/processed/perturbations.jsonl"
    stats_path: str = "data/processed/perturbation_stats.json"
    sample_path: str = "outputs/results/phase6_perturbation_sample.json"


@dataclass
class ValidationConfig:
    enabled: bool = True
    input_path: str = "data/processed/perturbations.jsonl"
    output_path: str = "data/processed/validated_perturbations.jsonl"
    stats_path: str = "data/processed/validation_stats.json"
    sample_path: str = "outputs/results/phase7_validation_sample.json"


@dataclass
class AlignmentConfig:
    enabled: bool = True
    input_source_relations_path: str = "data/processed/causal_relations.jsonl"
    input_summary_path: str = "data/processed/summary_inputs.jsonl"
    output_summary_relations_path: str = "data/processed/summary_causal_relations.jsonl"
    output_alignments_path: str = "data/processed/causal_alignments.jsonl"
    stats_path: str = "data/processed/alignment_stats.json"
    sample_path: str = "outputs/results/phase8_alignment_sample.json"
    embedding_model: str = "all-MiniLM-L6-v2"
    device: str = "cpu"
    cause_threshold: float = 0.50
    effect_threshold: float = 0.50
    overall_threshold: float = 0.60
    ambiguity_margin: float = 0.05
    cause_weight: float = 0.45
    effect_weight: float = 0.45
    relation_weight: float = 0.10
    batch_size: int = 32


@dataclass
class CausalDistortionConfig:
    enabled: bool = True
    input_source_relations_path: str = "data/processed/causal_relations.jsonl"
    input_summary_inputs_path: str = "data/processed/summary_inputs.jsonl"
    input_perturbations_path: str = "data/processed/perturbations.jsonl"
    input_validated_perturbations_path: str = "data/processed/validated_perturbations.jsonl"
    input_summary_relations_path: str = "data/processed/summary_causal_relations.jsonl"
    input_alignments_path: str = "data/processed/causal_alignments.jsonl"
    output_analysis_path: str = "data/processed/causal_distortion_analysis.jsonl"
    stats_path: str = "data/processed/distortion_stats.json"
    sample_path: str = "outputs/results/phase9_distortion_sample.json"
    confusion_matrix_path: str = "outputs/results/phase9_confusion_matrix.json"
    cause_threshold: float = 0.50
    effect_threshold: float = 0.50
    overall_threshold: float = 0.60
    weakened_trigger_words: List[str] = field(
        default_factory=lambda: [
            "associated with",
            "linked to",
            "related to",
            "correlated with",
            "connected to",
            "coinciding with",
            "followed",
        ]
    )



@dataclass
class AppConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    causal_extraction: CausalExtractionConfig = field(default_factory=CausalExtractionConfig)
    causal_graph: CausalGraphConfig = field(default_factory=CausalGraphConfig)
    summary_input: SummaryInputConfig = field(default_factory=SummaryInputConfig)
    perturbation: PerturbationConfig = field(default_factory=PerturbationConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    causal_distortion: CausalDistortionConfig = field(default_factory=CausalDistortionConfig)


def load_config(config_path: Optional[str | Path] = None) -> AppConfig:
    """Load application configuration from YAML file and environment variables.

    Args:
        config_path: Optional path to YAML configuration file. Defaults to configs/base.yaml.

    Returns:
        AppConfig instance containing resolved configuration settings.
    """
    root_dir = get_project_root()
    load_dotenv(root_dir / ".env")

    if config_path is None:
        config_path = root_dir / "configs" / "base.yaml"
    else:
        config_path = Path(config_path)
        if not config_path.is_absolute():
            config_path = root_dir / config_path

    config_dict: Dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

    # Extract project section
    proj_data = config_dict.get("project", {})
    project_cfg = ProjectConfig(
        name=os.getenv("PROJECT_NAME", proj_data.get("name", "CausalFidelityPlus")),
        environment=os.getenv("PROJECT_ENV", proj_data.get("environment", "development")),
        seed=int(os.getenv("RANDOM_SEED", proj_data.get("seed", 42))),
    )

    # Extract dataset section
    dataset_data = config_dict.get("dataset", {})
    filter_data = dataset_data.get("causal_candidate_filter", {})
    filter_cfg = CausalFilterConfig(
        enabled=filter_data.get("enabled", True),
        phrases=filter_data.get("phrases", CausalFilterConfig().phrases),
    )
    dataset_cfg = DatasetConfig(
        name=dataset_data.get("name", "xsum"),
        hf_dataset_path=dataset_data.get("hf_dataset_path", "EdinburghNLP/xsum"),
        domain=dataset_data.get("domain", "news"),
        language=dataset_data.get("language", "en"),
        split=dataset_data.get("split", "train"),
        development_sample_size=dataset_data.get("development_sample_size", 100),
        random_seed=project_cfg.seed,
        streaming=dataset_data.get("streaming", True),
        causal_candidate_filter=filter_cfg,
    )

    # Extract paths section
    paths_data = config_dict.get("paths", {})
    paths_cfg = PathConfig(
        root_dir=root_dir,
        data_dir=root_dir / paths_data.get("data_dir", "data"),
        raw_data_dir=root_dir / paths_data.get("raw_data_dir", "data/raw"),
        processed_data_dir=root_dir / paths_data.get("processed_data_dir", "data/processed"),
        annotations_dir=root_dir / paths_data.get("annotations_dir", "data/annotations"),
        output_dir=root_dir / paths_data.get("output_dir", "outputs"),
        metrics_dir=root_dir / paths_data.get("metrics_dir", "outputs/metrics"),
        results_dir=root_dir / paths_data.get("results_dir", "outputs/results"),
    )

    # Extract logging section
    logging_data = config_dict.get("logging", {})
    log_file_str = logging_data.get("log_file")
    log_file_path = root_dir / log_file_str if log_file_str else None

    logging_cfg = LoggingConfig(
        level=os.getenv("LOG_LEVEL", logging_data.get("level", "INFO")),
        format=logging_data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        log_to_file=logging_data.get("log_to_file", False),
        log_file=log_file_path,
    )

    # Extract causal_extraction section
    causal_data = config_dict.get("causal_extraction", {})
    causal_cfg = CausalExtractionConfig(
        enabled=causal_data.get("enabled", True),
        method=causal_data.get("method", "rule_based"),
        confidence_default=float(causal_data.get("confidence_default", 0.90)),
        candidate_only=causal_data.get("candidate_only", True),
        max_documents=causal_data.get("max_documents", 100),
        output_file=causal_data.get("output_file", "data/processed/causal_relations.jsonl"),
        stats_file=causal_data.get("stats_file", "data/processed/causal_relations_stats.json"),
        sample_output_file=causal_data.get("sample_output_file", "outputs/results/phase3_extraction_sample.json"),
    )

    # Extract causal_graph section
    graph_data = config_dict.get("causal_graph", {})
    graph_cfg = CausalGraphConfig(
        enabled=graph_data.get("enabled", True),
        input_file=graph_data.get("input_file", "data/processed/causal_relations.jsonl"),
        output_file=graph_data.get("output_file", "data/processed/causal_graphs.jsonl"),
        stats_file=graph_data.get("stats_file", "data/processed/causal_graphs_stats.json"),
        sample_output_file=graph_data.get("sample_output_file", "outputs/results/phase4_graph_sample.json"),
    )

    # Extract summary_input section
    summary_data = config_dict.get("summary_input", {})
    summary_cfg = SummaryInputConfig(
        enabled=summary_data.get("enabled", True),
        input_file=summary_data.get("input_file", "data/processed/xsum_dev.jsonl"),
        output_file=summary_data.get("output_file", "data/processed/summary_inputs.jsonl"),
        stats_file=summary_data.get("stats_file", "data/processed/summary_inputs_stats.json"),
        sample_output_file=summary_data.get("sample_output_file", "outputs/results/phase5_summary_sample.json"),
    )

    # Extract perturbation section
    pert_data = config_dict.get("perturbation", {})
    pert_cfg = PerturbationConfig(
        enabled=pert_data.get("enabled", True),
        input_summary_path=pert_data.get("input_summary_path", "data/processed/summary_inputs.jsonl"),
        input_causal_relations_path=pert_data.get("input_causal_relations_path", "data/processed/causal_relations.jsonl"),
        output_path=pert_data.get("output_path", "data/processed/perturbations.jsonl"),
        stats_path=pert_data.get("stats_path", "data/processed/perturbation_stats.json"),
        sample_path=pert_data.get("sample_path", "outputs/results/phase6_perturbation_sample.json"),
    )

    # Extract validation section
    val_data = config_dict.get("validation", {})
    val_cfg = ValidationConfig(
        enabled=val_data.get("enabled", True),
        input_path=val_data.get("input_path", "data/processed/perturbations.jsonl"),
        output_path=val_data.get("output_path", "data/processed/validated_perturbations.jsonl"),
        stats_path=val_data.get("stats_path", "data/processed/validation_stats.json"),
        sample_path=val_data.get("sample_path", "outputs/results/phase7_validation_sample.json"),
    )

    # Extract alignment section
    align_data = config_dict.get("alignment", {})
    align_cfg = AlignmentConfig(
        enabled=align_data.get("enabled", True),
        input_source_relations_path=align_data.get("input_source_relations_path", "data/processed/causal_relations.jsonl"),
        input_summary_path=align_data.get("input_summary_path", "data/processed/summary_inputs.jsonl"),
        output_summary_relations_path=align_data.get("output_summary_relations_path", "data/processed/summary_causal_relations.jsonl"),
        output_alignments_path=align_data.get("output_alignments_path", "data/processed/causal_alignments.jsonl"),
        stats_path=align_data.get("stats_path", "data/processed/alignment_stats.json"),
        sample_path=align_data.get("sample_path", "outputs/results/phase8_alignment_sample.json"),
        embedding_model=align_data.get("embedding_model", "all-MiniLM-L6-v2"),
        device=align_data.get("device", "cpu"),
        cause_threshold=float(align_data.get("cause_threshold", 0.50)),
        effect_threshold=float(align_data.get("effect_threshold", 0.50)),
        overall_threshold=float(align_data.get("overall_threshold", 0.60)),
        ambiguity_margin=float(align_data.get("ambiguity_margin", 0.05)),
        cause_weight=float(align_data.get("cause_weight", 0.45)),
        effect_weight=float(align_data.get("effect_weight", 0.45)),
        relation_weight=float(align_data.get("relation_weight", 0.10)),
        batch_size=int(align_data.get("batch_size", 32)),
    )

    # Extract causal_distortion section
    dist_data = config_dict.get("causal_distortion", {})
    dist_cfg = CausalDistortionConfig(
        enabled=dist_data.get("enabled", True),
        input_source_relations_path=dist_data.get("input_source_relations_path", "data/processed/causal_relations.jsonl"),
        input_summary_inputs_path=dist_data.get("input_summary_inputs_path", "data/processed/summary_inputs.jsonl"),
        input_perturbations_path=dist_data.get("input_perturbations_path", "data/processed/perturbations.jsonl"),
        input_validated_perturbations_path=dist_data.get("input_validated_perturbations_path", "data/processed/validated_perturbations.jsonl"),
        input_summary_relations_path=dist_data.get("input_summary_relations_path", "data/processed/summary_causal_relations.jsonl"),
        input_alignments_path=dist_data.get("input_alignments_path", "data/processed/causal_alignments.jsonl"),
        output_analysis_path=dist_data.get("output_analysis_path", "data/processed/causal_distortion_analysis.jsonl"),
        stats_path=dist_data.get("stats_path", "data/processed/distortion_stats.json"),
        sample_path=dist_data.get("sample_path", "outputs/results/phase9_distortion_sample.json"),
        confusion_matrix_path=dist_data.get("confusion_matrix_path", "outputs/results/phase9_confusion_matrix.json"),
        cause_threshold=float(dist_data.get("cause_threshold", 0.50)),
        effect_threshold=float(dist_data.get("effect_threshold", 0.50)),
        overall_threshold=float(dist_data.get("overall_threshold", 0.60)),
        weakened_trigger_words=dist_data.get("weakened_trigger_words", CausalDistortionConfig().weakened_trigger_words),
    )

    # Extract metrics section
    metrics_data = config_dict.get("metrics", {})
    summac_data = metrics_data.get("summac", {})
    summac_cfg = SummaCMetricConfig(
        enabled=summac_data.get("enabled", True),
        model_type=summac_data.get("model_type", "summac_conv"),
        models=summac_data.get("models", ["vitc"]),
        granularity=summac_data.get("granularity", "sentence"),
        device=summac_data.get("device", "cpu"),
        output_analysis_path=summac_data.get("output_analysis_path", "data/processed/phase10a_summac_results.jsonl"),
        stats_path=summac_data.get("stats_path", "outputs/results/phase10a_summac_stats.json"),
        sample_path=summac_data.get("sample_path", "outputs/results/phase10a_summac_sample.json"),
    )
    factcc_data = metrics_data.get("factcc", {})
    factcc_cfg = FactCCMetricConfig(
        enabled=factcc_data.get("enabled", True),
        model_path=factcc_data.get("model_path", "manueldeprada/FactCC"),
        device=factcc_data.get("device", "cpu"),
        max_length=int(factcc_data.get("max_length", 512)),
        output_analysis_path=factcc_data.get("output_analysis_path", "data/processed/phase10b_factcc_results.jsonl"),
        stats_path=factcc_data.get("stats_path", "outputs/results/phase10b_factcc_stats.json"),
        sample_path=factcc_data.get("sample_path", "outputs/results/phase10b_factcc_sample.json"),
    )
    bertscore_data = metrics_data.get("bertscore", {})
    bertscore_cfg = BERTScoreMetricConfig(
        enabled=bertscore_data.get("enabled", True),
        model_type=bertscore_data.get("model_type", "roberta-large"),
        device=bertscore_data.get("device", "cpu"),
        batch_size=int(bertscore_data.get("batch_size", 16)),
        output_analysis_path=bertscore_data.get("output_analysis_path", "data/processed/phase10c_bertscore_results.jsonl"),
        stats_path=bertscore_data.get("stats_path", "outputs/results/phase10c_bertscore_stats.json"),
        sample_path=bertscore_data.get("sample_path", "outputs/results/phase10c_bertscore_sample.json"),
    )
    metrics_cfg = MetricsConfig(summac=summac_cfg, factcc=factcc_cfg, bertscore=bertscore_cfg)

    return AppConfig(
        project=project_cfg,
        dataset=dataset_cfg,
        paths=paths_cfg,
        logging=logging_cfg,
        causal_extraction=causal_cfg,
        causal_graph=graph_cfg,
        summary_input=summary_cfg,
        perturbation=pert_cfg,
        validation=val_cfg,
        alignment=align_cfg,
        causal_distortion=dist_cfg,
        metrics=metrics_cfg,
    )


@dataclass
class SummaCMetricConfig:
    enabled: bool = True
    model_type: str = "summac_conv"
    models: List[str] = field(default_factory=lambda: ["vitc"])
    granularity: str = "sentence"
    device: str = "cpu"
    output_analysis_path: str = "data/processed/phase10a_summac_results.jsonl"
    stats_path: str = "outputs/results/phase10a_summac_stats.json"
    sample_path: str = "outputs/results/phase10a_summac_sample.json"


@dataclass
class FactCCMetricConfig:
    enabled: bool = True
    model_path: str = "manueldeprada/FactCC"
    device: str = "cpu"
    max_length: int = 512
    output_analysis_path: str = "data/processed/phase10b_factcc_results.jsonl"
    stats_path: str = "outputs/results/phase10b_factcc_stats.json"
    sample_path: str = "outputs/results/phase10b_factcc_sample.json"


@dataclass
class BERTScoreMetricConfig:
    enabled: bool = True
    model_type: str = "roberta-large"
    device: str = "cpu"
    batch_size: int = 16
    output_analysis_path: str = "data/processed/phase10c_bertscore_results.jsonl"
    stats_path: str = "outputs/results/phase10c_bertscore_stats.json"
    sample_path: str = "outputs/results/phase10c_bertscore_sample.json"


@dataclass
class MetricsConfig:
    summac: SummaCMetricConfig = field(default_factory=SummaCMetricConfig)
    factcc: FactCCMetricConfig = field(default_factory=FactCCMetricConfig)
    bertscore: BERTScoreMetricConfig = field(default_factory=BERTScoreMetricConfig)



@dataclass
class AppConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    causal_extraction: CausalExtractionConfig = field(default_factory=CausalExtractionConfig)
    causal_graph: CausalGraphConfig = field(default_factory=CausalGraphConfig)
    summary_input: SummaryInputConfig = field(default_factory=SummaryInputConfig)
    perturbation: PerturbationConfig = field(default_factory=PerturbationConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    causal_distortion: CausalDistortionConfig = field(default_factory=CausalDistortionConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)








