"""Phase 9 Causal Distortion Detection Pipeline."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.config import AppConfig, load_config
from causalfidelity.distortion.classifier import DistortionClassifier
from causalfidelity.distortion.evidence import DistortionEvidenceCollector
from causalfidelity.distortion.schema import DistortionAnalysisRecord
from causalfidelity.distortion.validator import DistortionBenchmarkFilter
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file for determinism verification."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


class DistortionDetectionPipeline:
    """Pipeline orchestrating Phase 9 Causal Distortion Detection."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.dist_cfg = self.config.causal_distortion
        self.embedder: Optional[SemanticEmbedder] = None

    def _get_embedder(self) -> SemanticEmbedder:
        if self.embedder is None:
            self.embedder = SemanticEmbedder(
                model_name=self.config.alignment.embedding_model,
                device=self.config.alignment.device,
            )
        return self.embedder

    def run(self) -> Dict[str, Any]:
        """Execute Phase 9 distortion detection pipeline.

        Returns:
            Dictionary of execution statistics and output paths.
        """
        logger.info("Initializing Phase 9 Causal Distortion Detection Pipeline...")
        root_dir = self.config.paths.root_dir

        # 1. Load Phase 3 Source Relations
        src_path = root_dir / self.dist_cfg.input_source_relations_path
        source_relations: List[Dict[str, Any]] = []
        if src_path.exists():
            with open(src_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if "relations" in data and isinstance(data["relations"], list):
                            source_relations.extend(data["relations"])
                        elif "relation_id" in data:
                            source_relations.append(data)

        source_rel_by_id = {r.get("relation_id"): r for r in source_relations}


        # 2. Load Phase 5 Summary Inputs
        sum_path = root_dir / self.dist_cfg.input_summary_inputs_path
        summary_inputs: List[Dict[str, Any]] = []
        if sum_path.exists():
            with open(sum_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        summary_inputs.append(json.loads(line))

        summary_by_doc = {s.get("document_id"): s for s in summary_inputs}

        # 3. Load Phase 6 Perturbations & Phase 7 Validations
        pert_path = root_dir / self.dist_cfg.input_perturbations_path
        val_path = root_dir / self.dist_cfg.input_validated_perturbations_path

        perturbations: List[Dict[str, Any]] = []
        if pert_path.exists():
            with open(pert_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        perturbations.append(json.loads(line))

        validations: List[Dict[str, Any]] = []
        if val_path.exists():
            with open(val_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        validations.append(json.loads(line))

        # 4. Load Phase 8 Summary Relations & Alignments
        sum_rel_path = root_dir / self.dist_cfg.input_summary_relations_path
        summary_relations: List[SummaryCausalRelation] = []
        if sum_rel_path.exists():
            with open(sum_rel_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        summary_relations.append(SummaryCausalRelation.from_dict(json.loads(line)))

        sum_rel_by_doc = {}
        for sr in summary_relations:
            sum_rel_by_doc.setdefault(sr.document_id, []).append(sr)

        align_path = root_dir / self.dist_cfg.input_alignments_path
        alignments: List[CausalAlignment] = []
        if align_path.exists():
            with open(align_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        alignments.append(CausalAlignment.from_dict(json.loads(line)))

        align_by_src_id = {a.source_relation_id: a for a in alignments}

        # Initialize evidence collector & classifier
        collector = DistortionEvidenceCollector(config=self.dist_cfg, embedder=self._get_embedder())
        classifier = DistortionClassifier(config=self.dist_cfg)

        # 5. Evaluate Phase 7 Valid Perturbations (Controlled Benchmark)
        valid_perts, rejected_perts = DistortionBenchmarkFilter.filter_valid_perturbations(
            validation_records=validations,
            perturbation_records=perturbations,
        )

        benchmark_records: List[DistortionAnalysisRecord] = []
        for pert in valid_perts:
            orig_rel_dict = pert.get("original_relation", {})
            src_rel_id = orig_rel_dict.get("relation_id")
            source_rel = source_rel_by_id.get(src_rel_id, orig_rel_dict)

            bundle = collector.collect_from_perturbation(perturbation=pert, source_rel=source_rel)
            record = classifier.classify(bundle)
            benchmark_records.append(record)

        # Sort benchmark records deterministically
        benchmark_records.sort(key=lambda r: r.analysis_id)

        benchmark_stats = DistortionBenchmarkFilter.calculate_benchmark_stats(
            analysis_records=benchmark_records,
            valid_count=len(valid_perts),
            rejected_count=len(rejected_perts),
        )

        confusion_matrix = DistortionBenchmarkFilter.generate_confusion_matrix(benchmark_records)

        # 6. Evaluate Reference Summaries (Phase 8 Evidence)
        reference_records: List[DistortionAnalysisRecord] = []
        for src_rel in source_relations:
            src_id = src_rel.get("relation_id", "")
            doc_id = src_rel.get("document_id", "")
            sum_rec = summary_by_doc.get(doc_id, {"document_id": doc_id, "summary_text": ""})
            alignment = align_by_src_id.get(src_id)
            sum_rels = sum_rel_by_doc.get(doc_id, [])
            matched_sum_rel = sum_rels[0] if sum_rels else None

            bundle = collector.collect_from_phase8_alignment(
                source_rel=src_rel,
                alignment=alignment,
                summary_record=sum_rec,
                summary_rel=matched_sum_rel,
            )
            record = classifier.classify(bundle)
            reference_records.append(record)

        # Sort reference records deterministically
        reference_records.sort(key=lambda r: r.analysis_id)

        all_records = benchmark_records + reference_records

        # 7. Write Output Artifacts
        out_analysis_path = root_dir / self.dist_cfg.output_analysis_path
        out_stats_path = root_dir / self.dist_cfg.stats_path
        out_sample_path = root_dir / self.dist_cfg.sample_path
        out_cm_path = root_dir / self.dist_cfg.confusion_matrix_path

        out_analysis_path.parent.mkdir(parents=True, exist_ok=True)
        out_sample_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_analysis_path, "w", encoding="utf-8") as f:
            for rec in all_records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

        ref_detected_dist: Dict[str, int] = {}
        for r in reference_records:
            ref_detected_dist[r.detected_label] = ref_detected_dist.get(r.detected_label, 0) + 1

        overall_stats = {
            "controlled_benchmark_stats": benchmark_stats,
            "reference_summary_stats": {
                "total_source_relations_analyzed": len(reference_records),
                "detected_label_distribution": ref_detected_dist,
                "insufficient_evidence_count": ref_detected_dist.get("INSUFFICIENT_EVIDENCE", 0),
                "disclaimer": "Reference summary labels are automatically detected from available Phase 8 evidence and are NOT human-validated ground truth.",
            },
            "configuration": {
                "cause_threshold": self.dist_cfg.cause_threshold,
                "effect_threshold": self.dist_cfg.effect_threshold,
                "overall_threshold": self.dist_cfg.overall_threshold,
                "weakened_trigger_words": self.dist_cfg.weakened_trigger_words,
            },
        }

        with open(out_stats_path, "w", encoding="utf-8") as f:
            json.dump(overall_stats, f, indent=2, ensure_ascii=False)

        # Sample output for sample_path artifact (max 10 records)
        sample_data = {
            "metadata": {
                "description": "Sample output records for Phase 9 Causal Distortion Detection.",
                "total_records_generated": len(all_records),
                "benchmark_records_count": len(benchmark_records),
                "reference_records_count": len(reference_records),
            },
            "benchmark_samples": [r.to_dict() for r in benchmark_records[:5]],
            "reference_samples": [r.to_dict() for r in reference_records[:5]],
        }

        with open(out_sample_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)

        with open(out_cm_path, "w", encoding="utf-8") as f:
            json.dump(confusion_matrix, f, indent=2, ensure_ascii=False)

        logger.info(f"Phase 9 execution completed successfully. Wrote {len(all_records)} analysis records.")

        return {
            "status": "success",
            "records_written": len(all_records),
            "benchmark_eval_count": len(benchmark_records),
            "analysis_path": str(out_analysis_path),
            "stats_path": str(out_stats_path),
            "sample_path": str(out_sample_path),
            "confusion_matrix_path": str(out_cm_path),
            "sha256": compute_file_sha256(out_analysis_path),
        }
