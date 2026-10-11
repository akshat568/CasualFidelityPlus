"""Master Pipeline Orchestrator for Phase 12 Human Validation & Statistical Analysis.

Coordinates the 7-stage workflow:
Stage 1: Load human annotations using AnnotationLoader.
Stage 2: Validate annotation records and report invalid records.
Stage 3: Calculate inter-annotator agreement using InterAnnotatorAgreementEvaluator.
Stage 4: Consolidate human annotations into consensus records (preserving disagreements).
Stage 5: Align consensus records with automated metric outputs.
Stage 6: Run statistical correlation and metric sensitivity analysis using StatisticalCorrelationEvaluator.
Stage 7: Generate structured output artifacts with overwrite protection.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from causalfidelity.annotation.agreement import AgreementResult, InterAnnotatorAgreementEvaluator
from causalfidelity.annotation.config import Phase12Config
from causalfidelity.annotation.correlation import CorrelationResult, StatisticalCorrelationEvaluator
from causalfidelity.annotation.loader import AnnotationLoader, IngestionResult
from causalfidelity.annotation.schema import AnnotationRecord
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class Phase12HumanValidationPipeline:
    """Master pipeline orchestrator for Phase 12 Human Validation & Statistical Analysis."""

    def __init__(self, config: Phase12Config):
        self.config = config
        self.config.validate()
        self.loader = AnnotationLoader()
        self.agreement_evaluator = InterAnnotatorAgreementEvaluator()
        self.correlation_evaluator = StatisticalCorrelationEvaluator()

    def _load_metric_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load automated metric scores from JSONL or CSV file."""
        records: List[Dict[str, Any]] = []
        ext = file_path.suffix.lower()

        if ext in (".jsonl", ".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        if isinstance(data, dict):
                            records.append(data)
                    except json.JSONDecodeError as err:
                        logger.warning(f"Malformed JSON on line {line_idx} in '{file_path}': {err}")
        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rec: Dict[str, Any] = dict(row)
                    # Convert numeric string fields to floats if possible
                    for k, v in rec.items():
                        if isinstance(v, str):
                            try:
                                val = float(v)
                                rec[k] = int(val) if val.is_integer() else val
                            except ValueError:
                                pass
                    records.append(rec)
        else:
            raise ValueError(f"Unsupported metric file format '{ext}' for path '{file_path}'.")

        return records

    def run(self) -> Dict[str, Any]:
        """Execute Phase 12 master pipeline workflow.

        Returns:
            Dictionary containing pipeline execution status, stage results, and output paths.
        """
        logger.info("Starting Phase 12 Human Validation & Statistical Analysis Pipeline...")

        # ---------------------------------------------------------------------
        # Stage 1: Load Human Annotations
        # ---------------------------------------------------------------------
        ann_path = Path(self.config.annotation_input_path)
        if not ann_path.exists():
            raise FileNotFoundError(f"Annotation input file not found: {ann_path}")

        logger.info(f"Stage 1: Loading human annotations from '{ann_path}'...")
        if self.config.input_format:
            fmt = str(self.config.input_format).lower()
            if fmt in ("jsonl", "json"):
                ingestion_result: IngestionResult = self.loader.load_jsonl(ann_path)
            elif fmt == "csv":
                ingestion_result = self.loader.load_csv(ann_path)
            else:
                ingestion_result = self.loader.load_file(ann_path)
        else:
            ingestion_result = self.loader.load_file(ann_path)

        # ---------------------------------------------------------------------
        # Stage 2: Validate Annotation Records & Report Invalid Records
        # ---------------------------------------------------------------------
        logger.info(
            f"Stage 2: Validation check. Processed: {ingestion_result.summary.get('total_records_processed')}, "
            f"Valid: {len(ingestion_result.valid_records)}, Invalid: {len(ingestion_result.invalid_records)}"
        )

        if self.config.validation_behavior == "strict" and ingestion_result.invalid_records:
            err_msg = (
                f"Strict validation failed: found {len(ingestion_result.invalid_records)} invalid annotation records in '{ann_path}'."
            )
            logger.error(err_msg)
            raise ValueError(err_msg)

        valid_records = ingestion_result.valid_records

        # ---------------------------------------------------------------------
        # Stage 3: Calculate Inter-Annotator Agreement
        # ---------------------------------------------------------------------
        logger.info("Stage 3: Evaluating inter-annotator agreement...")
        agreement_result: AgreementResult = self.agreement_evaluator.evaluate(valid_records)

        # ---------------------------------------------------------------------
        # Stage 4: Consolidate Human Annotations into Consensus Records
        # ---------------------------------------------------------------------
        logger.info("Stage 4: Consolidating human annotations into consensus records...")
        grouped_records: Dict[str, List[AnnotationRecord]] = defaultdict(list)
        for rec in valid_records:
            grouped_records[rec.perturbation_id].append(rec)

        consensus_records: List[Dict[str, Any]] = []
        unresolved_disagreements: List[Dict[str, Any]] = []
        insufficient_coverage_items: List[Dict[str, Any]] = []

        for pert_id in sorted(grouped_records.keys()):
            recs = grouped_records[pert_id]
            labels = [r.causal_label for r in recs if r.causal_label]
            naturalness_ratings = [
                r.naturalness_rating
                for r in recs
                if r.naturalness_rating is not None and isinstance(r.naturalness_rating, (int, float))
            ]

            annotator_ids = [r.annotator_id for r in recs]
            distinct_labels = set(labels)

            # Consensus determination: preserve disagreements deterministically
            if len(distinct_labels) == 1:
                consensus_label = labels[0]
                is_unanimous = True
                is_distorted = consensus_label in (
                    "Reversed",
                    "Weakened",
                    "Dropped",
                    "Cause_Changed",
                    "Effect_Changed",
                )
                disagreement_status = "unanimous"
            else:
                consensus_label = "DISAGREED"
                is_unanimous = False
                is_distorted = None
                disagreement_status = "disagreed"
                unresolved_disagreements.append(
                    {
                        "perturbation_id": pert_id,
                        "annotator_ids": annotator_ids,
                        "observed_labels": labels,
                        "reason": "annotators_assigned_different_causal_labels",
                    }
                )

            if len(recs) < 2:
                coverage_status = "insufficient_coverage"
                insufficient_coverage_items.append(
                    {
                        "perturbation_id": pert_id,
                        "annotator_ids": annotator_ids,
                        "records_count": len(recs),
                    }
                )
            elif len(recs) == 2:
                coverage_status = "standard_coverage"
            else:
                coverage_status = "excess_coverage"

            mean_naturalness = (
                round(sum(naturalness_ratings) / len(naturalness_ratings), 2)
                if naturalness_ratings
                else 0.0
            )

            consensus_records.append(
                {
                    "perturbation_id": pert_id,
                    "consensus_causal_label": consensus_label,
                    "is_distorted": is_distorted,
                    "mean_naturalness": mean_naturalness,
                    "is_unanimous": is_unanimous,
                    "disagreement_status": disagreement_status,
                    "coverage_status": coverage_status,
                    "annotators_count": len(recs),
                    "annotator_ids": annotator_ids,
                    "annotations": [r.to_dict() for r in recs],
                }
            )

        # ---------------------------------------------------------------------
        # Stage 5: Align Consensus Records with Automated Metric Outputs
        # ---------------------------------------------------------------------
        logger.info("Stage 5: Aligning consensus records with automated metric outputs...")
        automated_metrics: List[Dict[str, Any]] = []
        missing_metric_files: List[str] = []

        if self.config.metric_input_paths:
            metric_paths: List[Path] = []
            if isinstance(self.config.metric_input_paths, list):
                metric_paths = self.config.metric_input_paths
            elif isinstance(self.config.metric_input_paths, dict):
                metric_paths = list(self.config.metric_input_paths.values())

            for m_path in metric_paths:
                p = Path(m_path)
                if not p.exists():
                    if self.config.validation_behavior == "strict":
                        raise FileNotFoundError(f"Automated metric input file not found: {p}")
                    else:
                        logger.warning(f"Automated metric input file not found: '{p}'")
                        missing_metric_files.append(str(p))
                else:
                    file_recs = self._load_metric_file(p)
                    automated_metrics.extend(file_recs)

        # ---------------------------------------------------------------------
        # Stage 6: Run Statistical Correlation & Metric Sensitivity Analysis
        # ---------------------------------------------------------------------
        logger.info("Stage 6: Running statistical correlation and metric sensitivity analysis...")
        correlation_result: CorrelationResult = self.correlation_evaluator.evaluate(
            human_annotations=valid_records,
            automated_metrics=automated_metrics,
            binary_mapping_enabled=self.config.binary_mapping_enabled,
        )

        # ---------------------------------------------------------------------
        # Stage 7: Generate Structured Output Artifacts
        # ---------------------------------------------------------------------
        logger.info("Stage 7: Writing output artifacts with overwrite protection...")
        output_files: Dict[str, str] = {}

        output_paths_to_write = [
            ("human_annotations", self.config.human_annotations_output_path),
            ("human_validation_results", self.config.human_validation_results_output_path),
            ("inter_annotator_stats", self.config.inter_annotator_stats_output_path),
            ("statistical_analysis_stats", self.config.statistical_analysis_stats_output_path),
        ]

        # Overwrite safety check before creating/writing any file
        for name, out_path in output_paths_to_write:
            if out_path is not None:
                p = Path(out_path)
                if p.exists() and not self.config.allow_overwrite:
                    err_msg = (
                        f"Output file already exists and allow_overwrite is False: '{p}'. "
                        "Set allow_overwrite=True to enable overwriting existing output artifacts."
                    )
                    logger.error(err_msg)
                    raise FileExistsError(err_msg)

        # Write data/annotations/human_annotations.jsonl
        if self.config.human_annotations_output_path is not None:
            p = Path(self.config.human_annotations_output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                for rec in valid_records:
                    f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
            output_files["human_annotations"] = str(p)

        # Write data/processed/human_validation_results.jsonl
        if self.config.human_validation_results_output_path is not None:
            p = Path(self.config.human_validation_results_output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                for c_rec in consensus_records:
                    f.write(json.dumps(c_rec, ensure_ascii=False) + "\n")
            output_files["human_validation_results"] = str(p)

        # Write outputs/results/phase12_inter_annotator_stats.json
        if self.config.inter_annotator_stats_output_path is not None:
            p = Path(self.config.inter_annotator_stats_output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(agreement_result.to_json(indent=2) + "\n")
            output_files["inter_annotator_stats"] = str(p)

        # Write outputs/results/phase12_statistical_analysis_stats.json
        if self.config.statistical_analysis_stats_output_path is not None:
            p = Path(self.config.statistical_analysis_stats_output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(correlation_result.to_json(indent=2) + "\n")
            output_files["statistical_analysis_stats"] = str(p)

        logger.info(
            f"Phase 12 pipeline execution completed successfully. "
            f"Consensus records: {len(consensus_records)}, Unresolved disagreements: {len(unresolved_disagreements)}, "
            f"Artifacts written: {len(output_files)}"
        )

        return {
            "status": "success",
            "ingestion_summary": ingestion_result.summary,
            "agreement_results": agreement_result.to_dict(),
            "correlation_results": correlation_result.to_dict(),
            "consensus_records_count": len(consensus_records),
            "unresolved_disagreements_count": len(unresolved_disagreements),
            "unresolved_disagreements": unresolved_disagreements,
            "insufficient_coverage_count": len(insufficient_coverage_items),
            "insufficient_coverage_items": insufficient_coverage_items,
            "missing_metric_files": missing_metric_files,
            "output_files": output_files,
            "config": self.config.to_dict(),
        }
