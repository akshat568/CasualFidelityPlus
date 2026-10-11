"""Quota-driven streaming benchmark expansion sampler for CausalFidelity+."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.config import AppConfig, load_config
from causalfidelity.data.cleaner import TextCleaner
from causalfidelity.data.loader import XSumLoader
from causalfidelity.data.schema import CanonicalRecord, RecordMetadata
from causalfidelity.data.validator import DuplicateTracker, RecordValidator
from causalfidelity.perturbation.generator import PerturbationGenerator
from causalfidelity.perturbation.schema import PerturbationRecord
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger
from causalfidelity.validation.validator import PerturbationQualityValidator

logger = get_logger(__name__)

ALL_DISTORTION_CATEGORIES = [
    "REVERSED",
    "WEAKENED",
    "DROPPED",
    "CAUSE_CHANGED",
    "EFFECT_CHANGED",
]


class BenchmarkExpansionSampler:
    """Quota-driven streaming sampler for expanding and collecting validated causal perturbations."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        target_quota_per_category: int = 10,
        max_documents_to_process: int = 500,
        sampling_seed: int = 42,
        output_dir: Optional[Path] = None,
    ):
        """Initialize BenchmarkExpansionSampler.

        Args:
            config: Optional AppConfig instance.
            target_quota_per_category: Target valid perturbation count per category.
            max_documents_to_process: Maximum documents to examine before stopping.
            sampling_seed: Random seed for deterministic processing.
            output_dir: Destination output directory (defaults to run output path).
        """
        self.config = config or load_config()
        self.target_quota_per_category = target_quota_per_category
        self.max_documents_to_process = max_documents_to_process
        self.sampling_seed = sampling_seed

        if output_dir is not None:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.config.paths.root_dir / "data" / "processed"

        self.cleaner = TextCleaner()
        self.validator = RecordValidator(
            expected_domain=self.config.dataset.domain,
            expected_dataset=self.config.dataset.name,
            expected_language=self.config.dataset.language,
        )
        self.duplicate_tracker = DuplicateTracker()
        self.causal_extractor = RuleBasedCausalExtractor()
        self.perturbation_generator = PerturbationGenerator()
        self.quality_validator = PerturbationQualityValidator()

    def _all_quotas_reached(self, valid_counts: Dict[str, int]) -> bool:
        """Check if all distortion category quotas have been satisfied."""
        return all(
            valid_counts.get(cat, 0) >= self.target_quota_per_category
            for cat in ALL_DISTORTION_CATEGORIES
        )

    def sample_and_expand(
        self, raw_stream: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Stream documents, generate perturbations, validate quality, and collect valid records.

        Args:
            raw_stream: Optional explicit list of raw records (for testing).

        Returns:
            Tuple of (list_of_valid_perturbation_dicts, expansion_statistics_dict).
        """
        logger.info(
            f"Starting Benchmark Expansion Sampler (Target Quota: {self.target_quota_per_category}/category, Max Docs: {self.max_documents_to_process})"
        )

        if raw_stream is not None:
            iterator = XSumLoader.load_from_list(raw_stream)
        else:
            loader = XSumLoader(
                dataset_path=self.config.dataset.hf_dataset_path,
                split=self.config.dataset.split,
                streaming=self.config.dataset.streaming,
            )
            iterator = loader.stream_raw_records()

        valid_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []

        valid_counts = {cat: 0 for cat in ALL_DISTORTION_CATEGORIES}
        invalid_counts = {cat: 0 for cat in ALL_DISTORTION_CATEGORIES}
        rejection_reasons: Dict[str, int] = {}

        documents_examined = 0
        documents_processed = 0
        total_candidates_generated = 0
        stop_reason = "exhausted_stream"

        pert_counter = 1

        for raw_item in iterator:
            if documents_processed >= self.max_documents_to_process:
                stop_reason = "max_documents_reached"
                break

            if self._all_quotas_reached(valid_counts):
                stop_reason = "all_quotas_satisfied"
                break

            documents_examined += 1

            orig_id = str(raw_item.get("id", raw_item.get("original_id", f"doc_{documents_examined}")))
            src_text = self.cleaner.clean_text(raw_item.get("document", raw_item.get("source_text", "")))
            ref_sum = self.cleaner.clean_text(raw_item.get("summary", raw_item.get("reference_summary", "")))

            record = CanonicalRecord(
                document_id=f"xsum_exp_{documents_processed + 1:06d}",
                domain=self.config.dataset.domain,
                source_text=src_text,
                reference_summary=ref_sum,
                causal_candidate=True,
                metadata=RecordMetadata(
                    dataset=self.config.dataset.name,
                    original_id=orig_id,
                    split=self.config.dataset.split,
                    language=self.config.dataset.language,
                ),
            )

            is_valid, _ = self.validator.validate_record(record)
            if not is_valid:
                continue

            is_dup, _ = self.duplicate_tracker.is_duplicate(orig_id, src_text, ref_sum)
            if is_dup:
                continue

            self.duplicate_tracker.register(orig_id, src_text, ref_sum)
            documents_processed += 1

            doc_id = record.document_id
            sum_id = f"sum_{doc_id}"

            # Extract source causal relations
            doc_relations = self.causal_extractor.extract_relations(doc_id, src_text)

            # Generate candidate perturbations
            candidates, _ = self.perturbation_generator.generate_perturbations(
                document_id=doc_id,
                summary_id=sum_id,
                summary_text=ref_sum,
                doc_relations=doc_relations,
                counter_start=pert_counter,
            )

            pert_counter += len(candidates)
            total_candidates_generated += len(candidates)

            # Validate each candidate using Phase 7 validator
            for cand in candidates:
                cand_dict = cand.to_dict()
                ptype = cand_dict.get("perturbation_type", "UNKNOWN")

                val_rec = self.quality_validator.validate_record(cand_dict)
                cand_dict["validation_status"] = val_rec.validation_status
                cand_dict["checks"] = val_rec.checks
                cand_dict["errors"] = val_rec.errors
                cand_dict["warnings"] = val_rec.warnings

                if val_rec.validation_status == "valid":
                    valid_records.append(cand_dict)
                    valid_counts[ptype] = valid_counts.get(ptype, 0) + 1
                else:
                    invalid_records.append(cand_dict)
                    invalid_counts[ptype] = invalid_counts.get(ptype, 0) + 1
                    for err in val_rec.errors:
                        rejection_reasons[err] = rejection_reasons.get(err, 0) + 1

        if self._all_quotas_reached(valid_counts):
            stop_reason = "all_quotas_satisfied"

        stats = {
            "expansion_info": {
                "sampling_seed": self.sampling_seed,
                "target_quota_per_category": self.target_quota_per_category,
                "max_documents_to_process": self.max_documents_to_process,
                "stop_reason": stop_reason,
            },
            "counts": {
                "documents_examined": documents_examined,
                "documents_processed": documents_processed,
                "total_candidates_generated": total_candidates_generated,
                "valid_candidates_total": len(valid_records),
                "invalid_candidates_total": len(invalid_records),
            },
            "valid_counts_by_category": valid_counts,
            "invalid_counts_by_category": invalid_counts,
            "rejection_reasons": rejection_reasons,
        }

        # Write output expanded_benchmark.jsonl
        ensure_dir(self.output_dir)
        output_jsonl = self.output_dir / "expanded_benchmark.jsonl"
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for rec in valid_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        if "processed" in str(self.output_dir):
            primary_stats = self.output_dir.parent.parent / "outputs" / "results" / "benchmark_expansion_stats.json" if (self.output_dir.parent.parent / "outputs").exists() else self.output_dir.parent / "results" / "benchmark_expansion_stats.json"
            save_json(stats, primary_stats)
            secondary_stats = self.output_dir.parent / "results" / "benchmark_expansion_stats.json"
            save_json(stats, secondary_stats)
        else:
            save_json(stats, self.output_dir / "benchmark_expansion_stats.json")

        logger.info(
            f"Expansion sampler complete. Stop reason: '{stop_reason}'. Valid perturbations collected: {len(valid_records)}"
        )
        return valid_records, stats
