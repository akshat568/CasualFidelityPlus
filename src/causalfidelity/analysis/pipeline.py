"""Pipeline coordinator for executing Phase 10D research analysis and cross-metric comparison."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.analysis.cross_metric import CrossMetricAnalyzer
from causalfidelity.utils.io import ensure_dir, save_json

logger = logging.getLogger(__name__)


class Phase10DEvaluatorPipeline:
    """Pipeline coordinator for executing Phase 10D cross-metric analysis and research report generation."""

    def __init__(self, analyzer: Optional[CrossMetricAnalyzer] = None):
        """Initialize Phase 10D evaluator pipeline.

        Args:
            analyzer: Optional CrossMetricAnalyzer instance (or mock for testing).
        """
        self.analyzer = analyzer or CrossMetricAnalyzer()

    def _load_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load records from a JSONL file.

        Args:
            file_path: Path to the JSONL file.

        Returns:
            List of parsed dictionary records.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Required input artifact file not found: {file_path}")
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def _save_jsonl(self, records: List[Dict[str, Any]], file_path: Path) -> None:
        """Save records to a JSONL file.

        Args:
            records: List of dictionary records to write.
            file_path: Target JSONL file path.
        """
        ensure_dir(file_path.parent)
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def run(
        self,
        p9_analysis_path: Optional[Path] = None,
        summac_results_path: Optional[Path] = None,
        factcc_results_path: Optional[Path] = None,
        bertscore_results_path: Optional[Path] = None,
        output_analysis_path: Optional[Path] = None,
        output_stats_path: Optional[Path] = None,
        output_summary_path: Optional[Path] = None,
        output_figures_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 10D cross-metric research analysis pipeline.

        Args:
            p9_analysis_path: Path to Phase 9 distortion analysis JSONL.
            summac_results_path: Path to Phase 10A SummaCConv results JSONL.
            factcc_results_path: Path to Phase 10B FactCC results JSONL.
            bertscore_results_path: Path to Phase 10C BERTScore results JSONL.
            output_analysis_path: Destination path for phase10d combined analysis JSONL.
            output_stats_path: Destination path for phase10d stats JSON.
            output_summary_path: Destination path for phase10d summary Markdown report.
            output_figures_dir: Destination directory for figure images.

        Returns:
            Dictionary containing pipeline execution results and stats.
        """
        base_dir = Path(".")
        p9_path = p9_analysis_path or base_dir / "data" / "processed" / "causal_distortion_analysis.jsonl"
        sm_path = summac_results_path or base_dir / "data" / "processed" / "phase10a_summac_results.jsonl"
        fc_path = factcc_results_path or base_dir / "data" / "processed" / "phase10b_factcc_results.jsonl"
        bs_path = bertscore_results_path or base_dir / "data" / "processed" / "phase10c_bertscore_results.jsonl"

        out_analysis_path = output_analysis_path or base_dir / "data" / "processed" / "phase10d_cross_metric_analysis.jsonl"
        out_stats_path = output_stats_path or base_dir / "outputs" / "results" / "phase10d_cross_metric_stats.json"
        out_summary_path = output_summary_path or base_dir / "outputs" / "results" / "phase10d_cross_metric_summary.md"
        out_fig_dir = output_figures_dir or base_dir / "outputs" / "results" / "phase10d_figures"

        logger.info("Loading input Phase 9 and Phase 10A-10C artifacts for Phase 10D analysis...")
        p9_records = self._load_jsonl(p9_path)
        summac_records = self._load_jsonl(sm_path) if sm_path.exists() else []
        factcc_records = self._load_jsonl(fc_path) if fc_path.exists() else []
        bertscore_records = self._load_jsonl(bs_path) if bs_path.exists() else []

        logger.info("Combining records and verifying lineage...")
        combined_records = self.analyzer.combine_records(
            p9_records=p9_records,
            summac_records=summac_records,
            factcc_records=factcc_records,
            bertscore_records=bertscore_records,
        )

        logger.info("Computing cross-metric descriptive statistics...")
        stats = self.analyzer.compute_statistics(combined_records)

        logger.info("Generating research Markdown report...")
        md_summary = self.analyzer.generate_markdown_report(stats, combined_records)

        logger.info("Generating visualization figures...")
        fig_paths = self.analyzer.generate_figures(combined_records, out_fig_dir)

        logger.info("Saving output artifacts...")
        self._save_jsonl(combined_records, out_analysis_path)
        save_json(stats, out_stats_path, indent=2)

        ensure_dir(out_summary_path.parent)
        with open(out_summary_path, "w", encoding="utf-8") as f:
            f.write(md_summary)

        logger.info("Phase 10D Research Analysis Pipeline completed successfully.")
        return {
            "combined_records_count": len(combined_records),
            "stats": stats,
            "fig_paths": [str(p) for p in fig_paths],
            "output_analysis_path": str(out_analysis_path),
            "output_stats_path": str(out_stats_path),
            "output_summary_path": str(out_summary_path),
        }
