"""Phase 6 Controlled Causal Perturbation Engine pipeline coordinator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.causal.schema import CausalRelation, DocumentCausalRelations
from causalfidelity.config import AppConfig, load_config
from causalfidelity.perturbation.generator import PerturbationGenerator
from causalfidelity.perturbation.schema import PerturbationRecord
from causalfidelity.perturbation.validator import PerturbationValidator
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class PerturbationPipeline:
    """Pipeline coordinator for generating and validating controlled causal perturbations."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.generator = PerturbationGenerator()
        self.validator = PerturbationValidator()

    def run(
        self,
        summary_inputs_jsonl: Optional[Path] = None,
        causal_relations_jsonl: Optional[Path] = None,
        max_documents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 6 perturbation pipeline.

        Args:
            summary_inputs_jsonl: Path to summary_inputs.jsonl (Phase 5 output).
            causal_relations_jsonl: Path to causal_relations.jsonl (Phase 3 output).
            max_documents: Optional limit on documents to process.

        Returns:
            Dictionary of pipeline execution statistics.
        """
        logger.info("Starting Phase 6 Controlled Causal Perturbation Pipeline run")
        root_dir = self.config.paths.root_dir

        if summary_inputs_jsonl is None:
            summary_inputs_jsonl = root_dir / self.config.perturbation.input_summary_path
        else:
            summary_inputs_jsonl = Path(summary_inputs_jsonl)

        if causal_relations_jsonl is None:
            causal_relations_jsonl = root_dir / self.config.perturbation.input_causal_relations_path
        else:
            causal_relations_jsonl = Path(causal_relations_jsonl)

        if not summary_inputs_jsonl.exists():
            raise FileNotFoundError(
                f"Summary inputs dataset '{summary_inputs_jsonl}' not found. Please run Phase 5 pipeline first."
            )

        # Load Phase 5 summaries
        summaries: List[Dict[str, Any]] = []
        with open(summary_inputs_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    summaries.append(json.loads(line.strip()))

        # Load Phase 3 document relations map (doc_id -> List[CausalRelation])
        doc_relations_map: Dict[str, List[CausalRelation]] = {}
        if causal_relations_jsonl.exists():
            with open(causal_relations_jsonl, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line.strip())
                        doc_obj = DocumentCausalRelations.from_dict(item)
                        doc_relations_map[doc_obj.document_id] = doc_obj.relations

        if max_documents is not None and max_documents > 0:
            summaries = summaries[:max_documents]

        documents_examined = len(summaries)
        summaries_examined = len(summaries)
        phase3_source_rels_examined = 0
        relations_eligible_for_summary = 0
        relations_skipped_not_present = 0

        all_records: List[PerturbationRecord] = []
        valid_records: List[PerturbationRecord] = []

        generated_counts = {
            "REVERSED": 0,
            "WEAKENED": 0,
            "DROPPED": 0,
            "CAUSE_CHANGED": 0,
            "EFFECT_CHANGED": 0,
        }

        rejection_reasons: Dict[str, int] = {}

        global_counter = 1

        for sum_rec in summaries:
            doc_id = sum_rec.get("document_id", "")
            sum_id = sum_rec.get("summary_id", f"{doc_id}_ref")
            sum_text = sum_rec.get("summary_text", "")

            doc_rels = doc_relations_map.get(doc_id, [])
            phase3_source_rels_examined += len(doc_rels)

            gen_records, gen_stats = self.generator.generate_perturbations(
                document_id=doc_id,
                summary_id=sum_id,
                summary_text=sum_text,
                doc_relations=doc_rels,
                counter_start=global_counter,
            )

            relations_eligible_for_summary += gen_stats["eligible_relations"]
            relations_skipped_not_present += gen_stats["relations_not_present_in_summary"]

            for k, v in gen_stats["rejection_reasons"].items():
                rejection_reasons[k] = rejection_reasons.get(k, 0) + v

            for rec in gen_records:
                global_counter += 1
                all_records.append(rec)
                generated_counts[rec.perturbation_type] += 1

                # Validate
                is_valid, errors = self.validator.validate(rec)
                if is_valid:
                    rec.validation_status = "valid"
                    rec.validation_errors = []
                    valid_records.append(rec)
                else:
                    rec.validation_status = "invalid"
                    rec.validation_errors = errors
                    for err in errors:
                        rejection_reasons[err] = rejection_reasons.get(err, 0) + 1

        valid_count = len(valid_records)
        invalid_count = len(all_records) - valid_count
        skipped_count = relations_skipped_not_present

        # Write output JSONL
        output_path = root_dir / self.config.perturbation.output_path
        self._write_jsonl(all_records, output_path)

        # Write statistics JSON
        stats = {
            "pipeline_info": {
                "phase": "Phase 6 — Controlled Causal Perturbation Engine",
                "method": "rule_based",
            },
            "counts": {
                "documents_examined": documents_examined,
                "summaries_examined": summaries_examined,
                "phase3_source_relations_examined": phase3_source_rels_examined,
                "relations_eligible_for_summary_perturbation": relations_eligible_for_summary,
                "relations_skipped_not_present_in_summary": relations_skipped_not_present,
                "generated_perturbations": len(all_records),
                "valid_perturbations": valid_count,
                "invalid_perturbations": invalid_count,
                "skipped_perturbations": skipped_count,
            },
            "counts_by_type": generated_counts,
            "rejection_reasons": rejection_reasons,
        }

        stats_path = root_dir / self.config.perturbation.stats_path
        save_json(stats, stats_path)

        # Write inspection sample
        sample_path = root_dir / self.config.perturbation.sample_path
        self._write_inspection_sample(valid_records or all_records, sample_path)

        logger.info(
            f"Phase 6 Pipeline complete. Generated {len(all_records)} perturbations ({valid_count} valid) across {documents_examined} documents."
        )
        return stats

    @staticmethod
    def _write_jsonl(records: List[PerturbationRecord], file_path: Path) -> None:
        ensure_dir(file_path.parent)
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _write_inspection_sample(
        records: List[PerturbationRecord],
        sample_path: Path,
        max_samples: int = 10,
    ) -> None:
        sample_list = []
        for rec in records[:max_samples]:
            sample_list.append({
                "perturbation_id": rec.perturbation_id,
                "document_id": rec.document_id,
                "summary_id": rec.summary_id,
                "perturbation_type": rec.perturbation_type,
                "original_text": rec.original_text,
                "perturbed_text": rec.perturbed_text,
                "original_relation": rec.original_relation,
                "intended_relation": rec.intended_relation,
                "changed_span": rec.changed_span,
                "validation_status": rec.validation_status,
                "validation_errors": rec.validation_errors,
            })

        save_json({"perturbation_sample": sample_list}, sample_path)
