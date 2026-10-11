"""Phase 10A Evaluation Pipeline for SummaCConv on controlled causal perturbations."""

import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Optional

from causalfidelity.config import AppConfig, load_config
from causalfidelity.metrics.summac import SummaCConvMetric
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class Phase10AEvaluatorPipeline:
    """Pipeline coordinator for executing Phase 10A SummaCConv metric evaluation."""

    def __init__(self, config: Optional[AppConfig] = None, metric: Optional[SummaCConvMetric] = None):
        """Initialize Phase 10A evaluator pipeline.

        Args:
            config: Optional AppConfig instance.
            metric: Optional SummaCConvMetric instance (for DI / testing).
        """
        self.config = config or load_config()
        self.metric = metric or SummaCConvMetric(self.config.metrics.summac)

    def _load_source_documents(self, dev_file_path: Path) -> Dict[str, str]:
        """Load mapping of document_id -> source_text from xsum_dev.jsonl."""
        doc_map = {}
        if not dev_file_path.exists():
            raise FileNotFoundError(f"Source document file not found at: {dev_file_path}")
        with open(dev_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    doc_id = item.get("document_id")
                    src_txt = item.get("source_text")
                    if doc_id and src_txt:
                        doc_map[doc_id] = src_txt
        return doc_map

    def _load_phase9_records(self, phase9_file_path: Path) -> Dict[str, Dict[str, Any]]:
        """Load Phase 9 causal distortion analysis records indexed by perturbation_id."""
        phase9_map = {}
        if not phase9_file_path.exists():
            raise FileNotFoundError(f"Phase 9 analysis file not found at: {phase9_file_path}")
        with open(phase9_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    p_id = item.get("perturbation_id")
                    if p_id:
                        phase9_map[p_id] = item
        return phase9_map

    def run(
        self,
        validated_pert_path: Optional[Path] = None,
        pert_path: Optional[Path] = None,
        source_doc_path: Optional[Path] = None,
        phase9_analysis_path: Optional[Path] = None,
        output_results_path: Optional[Path] = None,
        output_stats_path: Optional[Path] = None,
        output_sample_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 10A SummaCConv evaluation pipeline.

        Args:
            validated_pert_path: Path to validated perturbations JSONL.
            pert_path: Path to perturbations JSONL (containing text spans).
            source_doc_path: Path to xsum_dev.jsonl.
            phase9_analysis_path: Path to Phase 9 distortion analysis JSONL.
            output_results_path: Destination path for phase10a results JSONL.
            output_stats_path: Destination path for stats JSON.
            output_sample_path: Destination path for sample JSON.

        Returns:
            Dictionary containing pipeline execution statistics.
        """
        root_dir = self.config.paths.root_dir

        val_path = validated_pert_path or (root_dir / self.config.validation.output_path)
        p_path = pert_path or (root_dir / self.config.perturbation.output_path)
        src_path = source_doc_path or (root_dir / "data" / "processed" / "xsum_dev.jsonl")
        p9_path = phase9_analysis_path or (root_dir / self.config.causal_distortion.output_analysis_path)

        out_results = output_results_path or (root_dir / self.config.metrics.summac.output_analysis_path)
        out_stats = output_stats_path or (root_dir / self.config.metrics.summac.stats_path)
        out_sample = output_sample_path or (root_dir / self.config.metrics.summac.sample_path)

        logger.info("Phase 10A Pipeline: Loading source documents from %s", src_path)
        doc_map = self._load_source_documents(src_path)

        logger.info("Phase 10A Pipeline: Loading Phase 9 distortion records from %s", p9_path)
        phase9_map = self._load_phase9_records(p9_path)

        # Build perturbation detail map (for text spans)
        pert_details = {}
        if p_path.exists():
            with open(p_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        pert_details[item["perturbation_id"]] = item

        # Load valid perturbations from validated_perturbations.jsonl
        valid_perts = []
        if not val_path.exists():
            raise FileNotFoundError(f"Validated perturbations file not found at: {val_path}")
        with open(val_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("validation_status") == "valid":
                        valid_perts.append(item)

        logger.info("Phase 10A Pipeline: Found %d Phase-7-valid perturbations for evaluation", len(valid_perts))

        # Perform strict Phase 9 alignment validation
        missing_phase9_ids = []
        for vp in valid_perts:
            pid = vp["perturbation_id"]
            if pid not in phase9_map:
                missing_phase9_ids.append(pid)

        if missing_phase9_ids:
            raise ValueError(
                f"Phase 9 Lineage Failure: Matching Phase 9 records missing for perturbation IDs: {missing_phase9_ids}"
            )

        results = []
        original_scores = []
        perturbed_scores = []
        score_deltas = []
        type_deltas: Dict[str, List[float]] = {}

        for vp in valid_perts:
            pid = vp["perturbation_id"]
            doc_id = vp["document_id"]
            detail = pert_details.get(pid, {})
            p9_record = phase9_map[pid]

            source_text = doc_map.get(doc_id)
            if not source_text:
                raise ValueError(f"Missing source_text in xsum_dev.jsonl for document_id: {doc_id}")

            original_summary = detail.get("original_text") or detail.get("original_summary")
            perturbed_summary = detail.get("perturbed_text") or detail.get("perturbed_summary")

            if not original_summary or not perturbed_summary:
                raise ValueError(f"Missing summary text in perturbation record for perturbation_id: {pid}")

            intended_label = p9_record.get("intended_label") or detail.get("perturbation_type")
            detected_label = p9_record.get("detected_label")

            # Evaluate SummaCConv on original and perturbed summaries using identical source document
            orig_score = float(self.metric.score(source_text, original_summary))
            pert_score = float(self.metric.score(source_text, perturbed_summary))
            delta = round(orig_score - pert_score, 4)

            original_scores.append(orig_score)
            perturbed_scores.append(pert_score)
            score_deltas.append(delta)

            if intended_label:
                type_deltas.setdefault(intended_label, []).append(delta)

            record = {
                "perturbation_id": pid,
                "document_id": doc_id,
                "intended_label": intended_label,
                "detected_label": detected_label,
                "original_summary": original_summary,
                "perturbed_summary": perturbed_summary,
                "metric_name": self.metric.name,
                "original_score": orig_score,
                "perturbed_score": pert_score,
                "score_delta": delta,
                "metadata": {
                    "phase9_analysis_id": p9_record.get("analysis_id"),
                    "phase9_evidence_strength": p9_record.get("evidence_strength"),
                    "phase9_agreement": p9_record.get("agreement"),
                    "metric_version": self.metric.version,
                    "metric_metadata": self.metric.get_metadata(),
                },
            }
            results.append(record)

        # Write results JSONL
        ensure_dir(out_results.parent)
        with open(out_results, "w", encoding="utf-8") as f:
            for rec in results:
                f.write(json.dumps(rec) + "\n")

        # Compute summary statistics
        num_evaluated = len(results)
        stats = {
            "metric_name": self.metric.name,
            "metric_version": self.metric.version,
            "total_valid_perturbations_evaluated": num_evaluated,
            "mean_original_score": round(mean(original_scores), 4) if original_scores else 0.0,
            "median_original_score": round(median(original_scores), 4) if original_scores else 0.0,
            "mean_perturbed_score": round(mean(perturbed_scores), 4) if perturbed_scores else 0.0,
            "median_perturbed_score": round(median(perturbed_scores), 4) if perturbed_scores else 0.0,
            "mean_score_delta": round(mean(score_deltas), 4) if score_deltas else 0.0,
            "median_score_delta": round(median(score_deltas), 4) if score_deltas else 0.0,
            "breakdown_by_intended_label": {
                label: {
                    "count": len(deltas),
                    "mean_delta": round(mean(deltas), 4),
                    "median_delta": round(median(deltas), 4),
                }
                for label, deltas in type_deltas.items()
            },
        }

        save_json(stats, out_stats)
        save_json(results[:3], out_sample)

        logger.info(
            "Phase 10A Pipeline completed successfully. Evaluated %d records. Mean delta: %.4f",
            num_evaluated,
            stats["mean_score_delta"],
        )
        return stats


class Phase10BEvaluatorPipeline:
    """Pipeline coordinator for executing Phase 10B FactCC metric evaluation."""

    def __init__(self, config: Optional[AppConfig] = None, metric: Optional[Any] = None):
        """Initialize Phase 10B evaluator pipeline.

        Args:
            config: Optional AppConfig instance.
            metric: Optional FactCCMetric instance (or BaseMetric mock for testing).
        """
        self.config = config or load_config()
        if metric is None:
            from causalfidelity.metrics.factcc import FactCCMetric

            self.metric = FactCCMetric(self.config.metrics.factcc)
        else:
            self.metric = metric

    def _load_source_documents(self, dev_file_path: Path) -> Dict[str, str]:
        """Load mapping of document_id -> source_text from xsum_dev.jsonl."""
        doc_map = {}
        if not dev_file_path.exists():
            raise FileNotFoundError(f"Source document file not found at: {dev_file_path}")
        with open(dev_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    doc_id = item.get("document_id")
                    src_txt = item.get("source_text")
                    if doc_id and src_txt:
                        doc_map[doc_id] = src_txt
        return doc_map

    def _load_phase9_records(self, phase9_file_path: Path) -> Dict[str, Dict[str, Any]]:
        """Load Phase 9 causal distortion analysis records indexed by perturbation_id."""
        phase9_map = {}
        if not phase9_file_path.exists():
            raise FileNotFoundError(f"Phase 9 analysis file not found at: {phase9_file_path}")
        with open(phase9_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    p_id = item.get("perturbation_id")
                    if p_id:
                        phase9_map[p_id] = item
        return phase9_map

    def run(
        self,
        validated_pert_path: Optional[Path] = None,
        pert_path: Optional[Path] = None,
        source_doc_path: Optional[Path] = None,
        phase9_analysis_path: Optional[Path] = None,
        output_results_path: Optional[Path] = None,
        output_stats_path: Optional[Path] = None,
        output_sample_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 10B FactCC evaluation pipeline.

        Args:
            validated_pert_path: Path to validated perturbations JSONL.
            pert_path: Path to perturbations JSONL (containing text spans).
            source_doc_path: Path to xsum_dev.jsonl.
            phase9_analysis_path: Path to Phase 9 distortion analysis JSONL.
            output_results_path: Destination path for phase10b results JSONL.
            output_stats_path: Destination path for stats JSON.
            output_sample_path: Destination path for sample JSON.

        Returns:
            Dictionary containing pipeline execution statistics.
        """
        root_dir = self.config.paths.root_dir

        val_path = validated_pert_path or (root_dir / self.config.validation.output_path)
        p_path = pert_path or (root_dir / self.config.perturbation.output_path)
        src_path = source_doc_path or (root_dir / "data" / "processed" / "xsum_dev.jsonl")
        p9_path = phase9_analysis_path or (root_dir / self.config.causal_distortion.output_analysis_path)

        out_results = output_results_path or (root_dir / self.config.metrics.factcc.output_analysis_path)
        out_stats = output_stats_path or (root_dir / self.config.metrics.factcc.stats_path)
        out_sample = output_sample_path or (root_dir / self.config.metrics.factcc.sample_path)

        logger.info("Phase 10B Pipeline: Loading source documents from %s", src_path)
        doc_map = self._load_source_documents(src_path)

        logger.info("Phase 10B Pipeline: Loading Phase 9 distortion records from %s", p9_path)
        phase9_map = self._load_phase9_records(p9_path)

        # Build perturbation detail map
        pert_details = {}
        if p_path.exists():
            with open(p_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        pert_details[item["perturbation_id"]] = item

        # Load valid perturbations from validated_perturbations.jsonl
        valid_perts = []
        if not val_path.exists():
            raise FileNotFoundError(f"Validated perturbations file not found at: {val_path}")
        with open(val_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("validation_status") == "valid":
                        valid_perts.append(item)

        logger.info("Phase 10B Pipeline: Found %d Phase-7-valid perturbations for evaluation", len(valid_perts))

        # Perform strict Phase 9 alignment validation
        missing_phase9_ids = []
        for vp in valid_perts:
            pid = vp["perturbation_id"]
            if pid not in phase9_map:
                missing_phase9_ids.append(pid)

        if missing_phase9_ids:
            raise ValueError(
                f"Phase 9 Lineage Failure: Matching Phase 9 records missing for perturbation IDs: {missing_phase9_ids}"
            )

        results = []
        original_scores = []
        perturbed_scores = []
        score_deltas = []
        type_deltas: Dict[str, List[float]] = {}

        for vp in valid_perts:
            pid = vp["perturbation_id"]
            doc_id = vp["document_id"]
            detail = pert_details.get(pid, {})
            summary_id = vp.get("summary_id") or detail.get("summary_id", doc_id)
            p9_record = phase9_map[pid]

            source_text = doc_map.get(doc_id)
            if not source_text:
                raise ValueError(f"Missing source_text in xsum_dev.jsonl for document_id: {doc_id}")

            original_summary = detail.get("original_text") or detail.get("original_summary")
            perturbed_summary = detail.get("perturbed_text") or detail.get("perturbed_summary")

            if not original_summary or not perturbed_summary:
                raise ValueError(f"Missing summary text in perturbation record for perturbation_id: {pid}")

            intended_label = p9_record.get("intended_label") or detail.get("perturbation_type")
            detected_label = p9_record.get("detected_label")

            # Evaluate FactCC on original and perturbed summaries using identical source document
            orig_score = float(self.metric.score(source_text, original_summary))
            pert_score = float(self.metric.score(source_text, perturbed_summary))
            delta = round(orig_score - pert_score, 4)

            original_scores.append(orig_score)
            perturbed_scores.append(pert_score)
            score_deltas.append(delta)

            if intended_label:
                type_deltas.setdefault(intended_label, []).append(delta)

            record = {
                "perturbation_id": pid,
                "document_id": doc_id,
                "summary_id": summary_id,
                "perturbation_type": intended_label,
                "intended_label": intended_label,
                "detected_label": detected_label,
                "original_text": original_summary,
                "perturbed_text": perturbed_summary,
                "original_summary": original_summary,
                "perturbed_summary": perturbed_summary,
                "metric_name": self.metric.name,
                "original_score": orig_score,
                "perturbed_score": pert_score,
                "score_delta": delta,
                "metric_metadata": self.metric.get_metadata(),
                "metadata": {
                    "phase9_analysis_id": p9_record.get("analysis_id"),
                    "phase9_evidence_strength": p9_record.get("evidence_strength"),
                    "phase9_agreement": p9_record.get("agreement"),
                    "metric_version": self.metric.version,
                    "metric_metadata": self.metric.get_metadata(),
                },
            }
            results.append(record)

        # Write results JSONL
        ensure_dir(out_results.parent)
        with open(out_results, "w", encoding="utf-8") as f:
            for rec in results:
                f.write(json.dumps(rec) + "\n")

        # Compute summary statistics
        num_evaluated = len(results)
        stats = {
            "metric_name": self.metric.name,
            "metric_version": self.metric.version,
            "total_valid_perturbations_evaluated": num_evaluated,
            "mean_original_score": round(mean(original_scores), 4) if original_scores else 0.0,
            "median_original_score": round(median(original_scores), 4) if original_scores else 0.0,
            "mean_perturbed_score": round(mean(perturbed_scores), 4) if perturbed_scores else 0.0,
            "median_perturbed_score": round(median(perturbed_scores), 4) if perturbed_scores else 0.0,
            "mean_score_delta": round(mean(score_deltas), 4) if score_deltas else 0.0,
            "median_score_delta": round(median(score_deltas), 4) if score_deltas else 0.0,
            "breakdown_by_intended_label": {
                label: {
                    "count": len(deltas),
                    "mean_delta": round(mean(deltas), 4),
                    "median_delta": round(median(deltas), 4),
                }
                for label, deltas in type_deltas.items()
            },
        }

        save_json(stats, out_stats)
        save_json(results[:3], out_sample)

        logger.info(
            "Phase 10B Pipeline completed successfully. Evaluated %d records. Mean delta: %.4f",
            num_evaluated,
            stats["mean_score_delta"],
        )
        return stats


class Phase10CEvaluatorPipeline:
    """Pipeline coordinator for executing Phase 10C BERTScore semantic-similarity metric evaluation."""

    def __init__(self, config: Optional[AppConfig] = None, metric: Optional[Any] = None):
        """Initialize Phase 10C evaluator pipeline.

        Args:
            config: Optional AppConfig instance.
            metric: Optional BERTScoreMetric instance (or BaseMetric mock for testing).
        """
        self.config = config or load_config()
        if metric is None:
            from causalfidelity.metrics.bertscore import BERTScoreMetric

            self.metric = BERTScoreMetric(self.config.metrics.bertscore)
        else:
            self.metric = metric

    def _load_source_documents(self, dev_file_path: Path) -> Dict[str, str]:
        """Load mapping of document_id -> source_text from xsum_dev.jsonl."""
        doc_map = {}
        if not dev_file_path.exists():
            raise FileNotFoundError(f"Source document file not found at: {dev_file_path}")
        with open(dev_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    doc_id = item.get("document_id")
                    src_txt = item.get("source_text")
                    if doc_id and src_txt:
                        doc_map[doc_id] = src_txt
        return doc_map

    def _load_phase9_records(self, phase9_file_path: Path) -> Dict[str, Dict[str, Any]]:
        """Load Phase 9 causal distortion analysis records indexed by perturbation_id."""
        phase9_map = {}
        if not phase9_file_path.exists():
            raise FileNotFoundError(f"Phase 9 analysis file not found at: {phase9_file_path}")
        with open(phase9_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    p_id = item.get("perturbation_id")
                    if p_id:
                        phase9_map[p_id] = item
        return phase9_map

    def run(
        self,
        validated_pert_path: Optional[Path] = None,
        pert_path: Optional[Path] = None,
        source_doc_path: Optional[Path] = None,
        phase9_analysis_path: Optional[Path] = None,
        output_results_path: Optional[Path] = None,
        output_stats_path: Optional[Path] = None,
        output_sample_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 10C BERTScore evaluation pipeline.

        Args:
            validated_pert_path: Path to validated perturbations JSONL.
            pert_path: Path to perturbations JSONL (containing text spans).
            source_doc_path: Path to xsum_dev.jsonl.
            phase9_analysis_path: Path to Phase 9 distortion analysis JSONL.
            output_results_path: Destination path for phase10c results JSONL.
            output_stats_path: Destination path for stats JSON.
            output_sample_path: Destination path for sample JSON.

        Returns:
            Dictionary containing pipeline execution statistics.
        """
        root_dir = self.config.paths.root_dir

        val_path = validated_pert_path or (root_dir / self.config.validation.output_path)
        p_path = pert_path or (root_dir / self.config.perturbation.output_path)
        src_path = source_doc_path or (root_dir / "data" / "processed" / "xsum_dev.jsonl")
        p9_path = phase9_analysis_path or (root_dir / self.config.causal_distortion.output_analysis_path)

        out_results = output_results_path or (root_dir / self.config.metrics.bertscore.output_analysis_path)
        out_stats = output_stats_path or (root_dir / self.config.metrics.bertscore.stats_path)
        out_sample = output_sample_path or (root_dir / self.config.metrics.bertscore.sample_path)

        logger.info("Phase 10C Pipeline: Loading source documents from %s", src_path)
        doc_map = self._load_source_documents(src_path)

        logger.info("Phase 10C Pipeline: Loading Phase 9 distortion records from %s", p9_path)
        phase9_map = self._load_phase9_records(p9_path)

        # Build perturbation detail map
        pert_details = {}
        if p_path.exists():
            with open(p_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        pert_details[item["perturbation_id"]] = item

        # Load valid perturbations and count invalid perturbations
        valid_perts = []
        num_invalid_excluded = 0
        if not val_path.exists():
            raise FileNotFoundError(f"Validated perturbations file not found at: {val_path}")
        with open(val_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("validation_status") == "valid":
                        valid_perts.append(item)
                    else:
                        num_invalid_excluded += 1

        logger.info(
            "Phase 10C Pipeline: Found %d valid perturbations (%d invalid excluded)",
            len(valid_perts),
            num_invalid_excluded,
        )

        # Perform strict Phase 9 alignment validation
        missing_phase9_ids = []
        for vp in valid_perts:
            pid = vp["perturbation_id"]
            if pid not in phase9_map:
                missing_phase9_ids.append(pid)

        if missing_phase9_ids:
            raise ValueError(
                f"Phase 9 Lineage Failure: Matching Phase 9 records missing for perturbation IDs: {missing_phase9_ids}"
            )

        # Prepare batches for BERTScore calculation
        reference_summaries = []
        candidate_summaries = []
        perturbation_metadata_list = []

        for vp in valid_perts:
            pid = vp["perturbation_id"]
            doc_id = vp["document_id"]
            detail = pert_details.get(pid, {})
            p9_record = phase9_map[pid]
            summary_id = vp.get("summary_id") or detail.get("summary_id", doc_id)

            source_text = doc_map.get(doc_id)
            if not source_text:
                raise ValueError(f"Missing source_text in xsum_dev.jsonl for document_id: {doc_id}")

            original_summary = detail.get("original_text") or detail.get("original_summary")
            perturbed_summary = detail.get("perturbed_text") or detail.get("perturbed_summary")

            if not original_summary or not perturbed_summary:
                raise ValueError(f"Missing summary text in perturbation record for perturbation_id: {pid}")

            intended_label = p9_record.get("intended_label") or detail.get("perturbation_type")
            detected_label = p9_record.get("detected_label")

            reference_summaries.append(original_summary)
            candidate_summaries.append(perturbed_summary)
            perturbation_metadata_list.append({
                "pid": pid,
                "doc_id": doc_id,
                "summary_id": summary_id,
                "detail": detail,
                "p9_record": p9_record,
                "original_summary": original_summary,
                "perturbed_summary": perturbed_summary,
                "intended_label": intended_label,
                "detected_label": detected_label,
            })

        # Calculate BERTScore on batch (reference: original_summary, candidate: perturbed_summary)
        if hasattr(self.metric, "score_detailed_batch"):
            detailed_scores = self.metric.score_detailed_batch(reference_summaries, candidate_summaries)
        else:
            # Fallback for generic BaseMetric mock
            f1_scores = self.metric.score_batch(reference_summaries, candidate_summaries)
            detailed_scores = [{"precision": round(s, 4), "recall": round(s, 4), "f1": round(s, 4)} for s in f1_scores]

        results = []
        f1_list = []
        precision_list = []
        recall_list = []
        similarity_loss_list = []
        type_f1s: Dict[str, List[float]] = {}

        for meta_item, bscore in zip(perturbation_metadata_list, detailed_scores):
            pid = meta_item["pid"]
            doc_id = meta_item["doc_id"]
            summary_id = meta_item["summary_id"]
            orig_sum = meta_item["original_summary"]
            pert_sum = meta_item["perturbed_summary"]
            intended_label = meta_item["intended_label"]
            detected_label = meta_item["detected_label"]
            p9_record = meta_item["p9_record"]

            p_val = bscore["precision"]
            r_val = bscore["recall"]
            f1_val = bscore["f1"]
            sim_loss = round(1.0 - f1_val, 4)

            precision_list.append(p_val)
            recall_list.append(r_val)
            f1_list.append(f1_val)
            similarity_loss_list.append(sim_loss)

            if intended_label:
                type_f1s.setdefault(intended_label, []).append(f1_val)

            record = {
                "perturbation_id": pid,
                "document_id": doc_id,
                "summary_id": summary_id,
                "perturbation_type": intended_label,
                "intended_label": intended_label,
                "detected_label": detected_label,
                "detected_distortion_label": detected_label,
                "original_text": orig_sum,
                "perturbed_text": pert_sum,
                "original_summary": orig_sum,
                "perturbed_summary": pert_sum,
                "metric_name": self.metric.name,
                "bertscore_precision": p_val,
                "bertscore_recall": r_val,
                "bertscore_f1": f1_val,
                "original_vs_perturbed_f1": f1_val,
                "similarity_loss": sim_loss,
                "metric_metadata": self.metric.get_metadata(),
                "metadata": {
                    "phase9_analysis_id": p9_record.get("analysis_id"),
                    "phase9_evidence_strength": p9_record.get("evidence_strength"),
                    "phase9_agreement": p9_record.get("agreement"),
                    "metric_version": self.metric.version,
                    "metric_metadata": self.metric.get_metadata(),
                },
            }
            results.append(record)

        # Write results JSONL
        ensure_dir(out_results.parent)
        with open(out_results, "w", encoding="utf-8") as f:
            for rec in results:
                f.write(json.dumps(rec) + "\n")

        # Compute summary statistics
        num_evaluated = len(results)
        stats = {
            "metric_name": self.metric.name,
            "metric_version": self.metric.version,
            "total_valid_perturbations_evaluated": num_evaluated,
            "total_invalid_perturbations_excluded": num_invalid_excluded,
            "mean_bertscore_f1": round(mean(f1_list), 4) if f1_list else 0.0,
            "median_bertscore_f1": round(median(f1_list), 4) if f1_list else 0.0,
            "min_bertscore_f1": round(min(f1_list), 4) if f1_list else 0.0,
            "max_bertscore_f1": round(max(f1_list), 4) if f1_list else 0.0,
            "mean_bertscore_precision": round(mean(precision_list), 4) if precision_list else 0.0,
            "mean_bertscore_recall": round(mean(recall_list), 4) if recall_list else 0.0,
            "mean_similarity_loss": round(mean(similarity_loss_list), 4) if similarity_loss_list else 0.0,
            "breakdown_by_intended_label": {
                label: {
                    "count": len(f1s),
                    "mean_f1": round(mean(f1s), 4),
                    "median_f1": round(median(f1s), 4),
                    "mean_similarity_loss": round(mean([1.0 - s for s in f1s]), 4),
                }
                for label, f1s in type_f1s.items()
            },
            "configuration": self.metric.get_metadata(),
        }

        save_json(stats, out_stats)
        save_json(results[:3], out_sample)

        logger.info(
            "Phase 10C Pipeline completed successfully. Evaluated %d records. Mean F1: %.4f",
            num_evaluated,
            stats["mean_bertscore_f1"],
        )
        return stats


