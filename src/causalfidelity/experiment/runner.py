"""Master Pipeline Orchestrator for individual experiment runs in CausalFidelity+.

Executes existing pipeline stages (Phases 2-10D) in verified dependency order
using isolated run output directories and app configurations.
"""

from datetime import datetime, timezone
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.analysis.pipeline import Phase10DEvaluatorPipeline
from causalfidelity.alignment.pipeline import AlignmentPipeline
from causalfidelity.causal.pipeline import CausalExtractionPipeline
from causalfidelity.data.pipeline import XSumPipeline
from causalfidelity.distortion.pipeline import DistortionDetectionPipeline
from causalfidelity.experiment.config import ExperimentRunConfig
from causalfidelity.graph.pipeline import CausalGraphPipeline
from causalfidelity.metrics.pipeline import (
    Phase10AEvaluatorPipeline,
    Phase10BEvaluatorPipeline,
    Phase10CEvaluatorPipeline,
)
from causalfidelity.perturbation.pipeline import PerturbationPipeline
from causalfidelity.summary.pipeline import SummaryInputPipeline
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger
from causalfidelity.validation.pipeline import PerturbationValidationPipeline

logger = get_logger(__name__)


@dataclass
class StageExecutionRecord:
    """Record of execution status for an individual pipeline stage."""

    stage_name: str
    phase_id: str
    status: str  # "SUCCESS", "FAILED", "SKIPPED", "DRY_RUN"
    start_time: str
    end_time: str
    artifacts: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class RunManifest:
    """Manifest summarizing the complete execution of an experiment run."""

    run_id: str
    experiment_id: str
    status: str  # "SUCCESS", "FAILED", "SKIPPED", "DRY_RUN"
    start_time: str
    end_time: str
    output_dir: str
    stages: List[StageExecutionRecord] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary format."""
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "output_dir": self.output_dir,
            "stages": [asdict(s) for s in self.stages],
            "parameters": self.parameters,
        }


class ExperimentRunner:
    """Master pipeline orchestrator for executing isolated experiment runs."""

    STAGE_ORDER = [
        ("data_preprocessing", "Phase 2"),
        ("causal_extraction", "Phase 3"),
        ("causal_graph", "Phase 4"),
        ("summary_input", "Phase 5"),
        ("perturbation", "Phase 6"),
        ("perturbation_validation", "Phase 7"),
        ("causal_alignment", "Phase 8"),
        ("causal_distortion", "Phase 9"),
        ("metrics_summac", "Phase 10A"),
        ("metrics_factcc", "Phase 10B"),
        ("metrics_bertscore", "Phase 10C"),
        ("research_analysis", "Phase 10D"),
    ]

    def __init__(
        self,
        run_config: ExperimentRunConfig,
        dry_run: bool = False,
        skip_existing: bool = False,
    ):
        """Initialize ExperimentRunner with an isolated run configuration.

        Args:
            run_config: ExperimentRunConfig defining parameters and output path.
            dry_run: If True, validate stages without executing heavy models.
            skip_existing: If True, skip stages whose outputs already exist in run_dir.
        """
        self.run_config = run_config
        self.dry_run = dry_run
        self.skip_existing = skip_existing
        self.app_config = run_config.app_config

        # Guarantee root_dir isolation to the run output directory
        self.app_config.paths.root_dir = run_config.run_output_dir
        self.app_config.paths.processed_data_dir = run_config.run_output_dir / "data" / "processed"
        self.app_config.paths.results_dir = run_config.run_output_dir / "outputs" / "results"
        self.app_config.paths.metrics_dir = run_config.run_output_dir / "outputs" / "metrics"

    def _get_stage_expected_artifacts(self, stage_name: str) -> List[Path]:
        """Return expected artifact paths for a given stage within the isolated run directory."""
        run_dir = self.run_config.run_output_dir
        artifacts_map: Dict[str, List[Path]] = {
            "data_preprocessing": [
                run_dir / "data" / "processed" / "xsum_dev.jsonl",
                run_dir / "data" / "processed" / "xsum_dev_stats.json",
            ],
            "causal_extraction": [
                run_dir / self.app_config.causal_extraction.output_file,
                run_dir / self.app_config.causal_extraction.stats_file,
            ],
            "causal_graph": [
                run_dir / self.app_config.causal_graph.output_file,
                run_dir / self.app_config.causal_graph.stats_file,
            ],
            "summary_input": [
                run_dir / self.app_config.summary_input.output_file,
                run_dir / self.app_config.summary_input.stats_file,
            ],
            "perturbation": [
                run_dir / self.app_config.perturbation.output_path,
                run_dir / self.app_config.perturbation.stats_path,
            ],
            "perturbation_validation": [
                run_dir / self.app_config.validation.output_path,
                run_dir / self.app_config.validation.stats_path,
            ],
            "causal_alignment": [
                run_dir / self.app_config.alignment.output_alignments_path,
                run_dir / self.app_config.alignment.stats_path,
            ],
            "causal_distortion": [
                run_dir / self.app_config.causal_distortion.output_analysis_path,
                run_dir / self.app_config.causal_distortion.stats_path,
            ],
            "metrics_summac": [
                run_dir / self.app_config.metrics.summac.output_analysis_path,
                run_dir / self.app_config.metrics.summac.stats_path,
            ],
            "metrics_factcc": [
                run_dir / self.app_config.metrics.factcc.output_analysis_path,
                run_dir / self.app_config.metrics.factcc.stats_path,
            ],
            "metrics_bertscore": [
                run_dir / self.app_config.metrics.bertscore.output_analysis_path,
                run_dir / self.app_config.metrics.bertscore.stats_path,
            ],
            "research_analysis": [
                run_dir / "data" / "processed" / "phase10d_cross_metric_analysis.jsonl",
                run_dir / "outputs" / "results" / "phase10d_cross_metric_stats.json",
            ],
        }
        return artifacts_map.get(stage_name, [])

    def _execute_stage(self, stage_name: str, phase_id: str) -> StageExecutionRecord:
        """Execute a single pipeline stage or simulate dry-run."""
        start_iso = datetime.now(timezone.utc).isoformat()
        expected_artifacts = self._get_stage_expected_artifacts(stage_name)
        art_paths_str = [str(p) for p in expected_artifacts]

        if self.skip_existing and expected_artifacts and all(p.exists() for p in expected_artifacts):
            end_iso = datetime.now(timezone.utc).isoformat()
            logger.info(f"Skipping stage '{stage_name}' ({phase_id}): outputs already exist.")
            return StageExecutionRecord(
                stage_name=stage_name,
                phase_id=phase_id,
                status="SKIPPED",
                start_time=start_iso,
                end_time=end_iso,
                artifacts=art_paths_str,
                stats={"reason": "Outputs already exist"},
            )

        if self.dry_run:
            end_iso = datetime.now(timezone.utc).isoformat()
            logger.info(f"Dry-run stage '{stage_name}' ({phase_id}): validation successful.")
            return StageExecutionRecord(
                stage_name=stage_name,
                phase_id=phase_id,
                status="DRY_RUN",
                start_time=start_iso,
                end_time=end_iso,
                artifacts=art_paths_str,
                stats={"dry_run": True},
            )

        # Actual execution using stage pipelines initialized with isolated app_config
        try:
            stats: Dict[str, Any] = {}
            if stage_name == "data_preprocessing":
                pipeline = XSumPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "causal_extraction":
                pipeline = CausalExtractionPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "causal_graph":
                pipeline = CausalGraphPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "summary_input":
                pipeline = SummaryInputPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "perturbation":
                pipeline = PerturbationPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "perturbation_validation":
                pipeline = PerturbationValidationPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "causal_alignment":
                pipeline = AlignmentPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "causal_distortion":
                pipeline = DistortionDetectionPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "metrics_summac":
                if not self.app_config.metrics.summac.enabled:
                    logger.info("Skipping stage 'metrics_summac' (Phase 10A): metric is disabled in configuration.")
                    end_iso = datetime.now(timezone.utc).isoformat()
                    return StageExecutionRecord(
                        stage_name=stage_name,
                        phase_id=phase_id,
                        status="SKIPPED",
                        start_time=start_iso,
                        end_time=end_iso,
                        artifacts=art_paths_str,
                        stats={"reason": "Metric disabled in configuration"},
                    )
                pipeline = Phase10AEvaluatorPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "metrics_factcc":
                if not self.app_config.metrics.factcc.enabled:
                    logger.info("Skipping stage 'metrics_factcc' (Phase 10B): metric is disabled in configuration.")
                    end_iso = datetime.now(timezone.utc).isoformat()
                    return StageExecutionRecord(
                        stage_name=stage_name,
                        phase_id=phase_id,
                        status="SKIPPED",
                        start_time=start_iso,
                        end_time=end_iso,
                        artifacts=art_paths_str,
                        stats={"reason": "Metric disabled in configuration"},
                    )
                pipeline = Phase10BEvaluatorPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "metrics_bertscore":
                if not self.app_config.metrics.bertscore.enabled:
                    logger.info("Skipping stage 'metrics_bertscore' (Phase 10C): metric is disabled in configuration.")
                    end_iso = datetime.now(timezone.utc).isoformat()
                    return StageExecutionRecord(
                        stage_name=stage_name,
                        phase_id=phase_id,
                        status="SKIPPED",
                        start_time=start_iso,
                        end_time=end_iso,
                        artifacts=art_paths_str,
                        stats={"reason": "Metric disabled in configuration"},
                    )
                pipeline = Phase10CEvaluatorPipeline(config=self.app_config)
                stats = pipeline.run()

            elif stage_name == "research_analysis":
                pipeline = Phase10DEvaluatorPipeline()
                p9_path = self.app_config.paths.root_dir / self.app_config.causal_distortion.output_analysis_path
                sm_path = self.app_config.paths.root_dir / self.app_config.metrics.summac.output_analysis_path
                fc_path = self.app_config.paths.root_dir / self.app_config.metrics.factcc.output_analysis_path
                bs_path = self.app_config.paths.root_dir / self.app_config.metrics.bertscore.output_analysis_path

                out_analysis_path = self.app_config.paths.root_dir / "data" / "processed" / "phase10d_cross_metric_analysis.jsonl"
                out_stats_path = self.app_config.paths.root_dir / "outputs" / "results" / "phase10d_cross_metric_stats.json"
                out_report_path = self.app_config.paths.root_dir / "outputs" / "results" / "phase10d_cross_metric_summary.md"
                out_fig_dir = self.app_config.paths.root_dir / "outputs" / "results" / "phase10d_figures"

                stats = pipeline.run(
                    p9_analysis_path=p9_path,
                    summac_results_path=sm_path,
                    factcc_results_path=fc_path,
                    bertscore_results_path=bs_path,
                    output_analysis_path=out_analysis_path,
                    output_stats_path=out_stats_path,
                    output_summary_path=out_report_path,
                    output_figures_dir=out_fig_dir,
                )

            end_iso = datetime.now(timezone.utc).isoformat()
            return StageExecutionRecord(
                stage_name=stage_name,
                phase_id=phase_id,
                status="SUCCESS",
                start_time=start_iso,
                end_time=end_iso,
                artifacts=art_paths_str,
                stats=stats if isinstance(stats, dict) else {},
            )

        except Exception as err:
            end_iso = datetime.now(timezone.utc).isoformat()
            logger.error(f"Stage '{stage_name}' ({phase_id}) failed: {err}")
            return StageExecutionRecord(
                stage_name=stage_name,
                phase_id=phase_id,
                status="FAILED",
                start_time=start_iso,
                end_time=end_iso,
                artifacts=art_paths_str,
                error=str(err),
            )

    def run(self) -> RunManifest:
        """Execute all pipeline stages for the experiment run and produce a run manifest."""
        run_dir = self.run_config.run_output_dir
        ensure_dir(run_dir)
        ensure_dir(run_dir / "data" / "processed")
        ensure_dir(run_dir / "outputs" / "results")
        ensure_dir(run_dir / "outputs" / "metrics")

        # Set deterministic random seed
        random.seed(self.run_config.seed)

        start_time = datetime.now(timezone.utc).isoformat()
        stage_records: List[StageExecutionRecord] = []
        overall_status = "DRY_RUN" if self.dry_run else "SUCCESS"

        logger.info(
            f"Starting Experiment Run '{self.run_config.run_id}' (Experiment: '{self.run_config.experiment_id}', Seed: {self.run_config.seed})"
        )

        for stage_name, phase_id in self.STAGE_ORDER:
            stage_rec = self._execute_stage(stage_name, phase_id)
            stage_records.append(stage_rec)

            if stage_rec.status == "FAILED":
                overall_status = "FAILED"
                logger.error(f"Execution halted due to failure in stage '{stage_name}'.")
                break

        end_time = datetime.now(timezone.utc).isoformat()

        manifest = RunManifest(
            run_id=self.run_config.run_id,
            experiment_id=self.run_config.experiment_id,
            status=overall_status,
            start_time=start_time,
            end_time=end_time,
            output_dir=str(run_dir),
            stages=stage_records,
            parameters=self.run_config.parameters,
        )

        manifest_path = run_dir / "run_manifest.json"
        save_json(manifest.to_dict(), manifest_path)
        logger.info(f"Experiment Run '{self.run_config.run_id}' completed with status '{overall_status}'. Manifest saved to {manifest_path}")

        return manifest
