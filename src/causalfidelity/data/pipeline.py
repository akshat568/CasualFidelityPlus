"""XSum dataset preprocessing pipeline coordinator for CausalFidelity+."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.config import AppConfig, load_config
from causalfidelity.data.cleaner import TextCleaner
from causalfidelity.data.filter import CausalCandidateFilter
from causalfidelity.data.loader import XSumLoader
from causalfidelity.data.sampler import DeterministicSampler
from causalfidelity.data.schema import CanonicalRecord, RecordMetadata
from causalfidelity.data.validator import DuplicateTracker, RecordValidator
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class XSumPipeline:
    """End-to-end dataset preprocessing pipeline for XSum news summarization dataset."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.cleaner = TextCleaner()
        self.validator = RecordValidator(
            expected_domain=self.config.dataset.domain,
            expected_dataset=self.config.dataset.name,
            expected_language=self.config.dataset.language,
        )
        self.duplicate_tracker = DuplicateTracker()
        self.causal_filter = CausalCandidateFilter(
            phrases=self.config.dataset.causal_candidate_filter.phrases,
            enabled=self.config.dataset.causal_candidate_filter.enabled,
        )
        self.sampler = DeterministicSampler(seed=self.config.dataset.random_seed)

    def run(
        self,
        raw_stream: Optional[List[Dict[str, Any]]] = None,
        max_examine: Optional[int] = 500,
    ) -> Dict[str, Any]:
        """Execute preprocessing pipeline over raw XSum records.

        Args:
            raw_stream: Optional explicit list of raw records (for testing). If None, stream from HF loader.
            max_examine: Maximum raw records to pull from dataset before sampling. Defaults to 500.

        Returns:
            Dictionary containing pipeline execution statistics.
        """
        logger.info(
            f"Starting XSum Pipeline run (target sample size: {self.config.dataset.development_sample_size})"
        )

        # Dataset stream source
        if raw_stream is not None:
            record_iterator = XSumLoader.load_from_list(raw_stream)
        else:
            loader = XSumLoader(
                dataset_path=self.config.dataset.hf_dataset_path,
                split=self.config.dataset.split,
                streaming=self.config.dataset.streaming,
            )
            record_iterator = loader.stream_raw_records(limit=max_examine)

        total_examined = 0
        total_invalid = 0
        total_duplicates = 0
        empty_documents = 0
        empty_summaries = 0

        validated_records: List[CanonicalRecord] = []

        for raw_item in record_iterator:
            total_examined += 1

            # Step 1: Conservative text cleaning
            cleaned_item = self.cleaner.clean_raw_record(raw_item)
            src_text = cleaned_item["source_text"]
            ref_sum = cleaned_item["reference_summary"]
            orig_id = cleaned_item["original_id"]

            if not src_text:
                empty_documents += 1
            if not ref_sum:
                empty_summaries += 1

            # Build candidate CanonicalRecord
            record = CanonicalRecord(
                document_id="",  # Assigned post-sampling
                domain=self.config.dataset.domain,
                source_text=src_text,
                reference_summary=ref_sum,
                causal_candidate=False,
                metadata=RecordMetadata(
                    dataset=self.config.dataset.name,
                    original_id=orig_id,
                    split=self.config.dataset.split,
                    language=self.config.dataset.language,
                ),
            )

            # Step 2: Record validation
            is_valid, reason = self.validator.validate_record(record)
            if not is_valid:
                total_invalid += 1
                continue

            # Step 3: Duplicate detection
            is_dup, dup_type = self.duplicate_tracker.is_duplicate(orig_id, src_text, ref_sum)
            if is_dup:
                total_duplicates += 1
                continue

            self.duplicate_tracker.register(orig_id, src_text, ref_sum)

            # Step 4: Causal-candidate filtering (prescreening)
            record.causal_candidate = self.causal_filter.is_causal_candidate(src_text)

            validated_records.append(record)

        # Step 5: Deterministic sampling for development subset
        target_size = self.config.dataset.development_sample_size
        sampled_records = self.sampler.sample(validated_records, target_size)

        # Assign clean, sequential document IDs
        for idx, rec in enumerate(sampled_records, start=1):
            rec.document_id = f"xsum_{idx:06d}"

        # Step 6: Save output dataset to JSONL
        processed_dir = ensure_dir(self.config.paths.processed_data_dir)
        output_jsonl = processed_dir / "xsum_dev.jsonl"
        self._write_jsonl(sampled_records, output_jsonl)

        # Step 7: Calculate empirical statistics
        stats = self._calculate_statistics(
            total_examined=total_examined,
            total_invalid=total_invalid,
            total_duplicates=total_duplicates,
            empty_documents=empty_documents,
            empty_summaries=empty_summaries,
            records=sampled_records,
        )

        stats_json = processed_dir / "xsum_dev_stats.json"
        save_json(stats, stats_json)

        logger.info(
            f"Pipeline complete. Processed {len(sampled_records)} records to '{output_jsonl}'"
        )
        return stats

    @staticmethod
    def _write_jsonl(records: List[CanonicalRecord], file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _calculate_statistics(
        total_examined: int,
        total_invalid: int,
        total_duplicates: int,
        empty_documents: int,
        empty_summaries: int,
        records: List[CanonicalRecord],
    ) -> Dict[str, Any]:
        causal_candidates = sum(1 for r in records if r.causal_candidate)
        non_candidates = len(records) - causal_candidates

        doc_char_lens = [len(r.source_text) for r in records]
        doc_word_lens = [len(r.source_text.split()) for r in records]
        sum_char_lens = [len(r.reference_summary) for r in records]
        sum_word_lens = [len(r.reference_summary.split()) for r in records]

        def compute_metrics(values: List[int]) -> Dict[str, float]:
            if not values:
                return {"mean": 0.0, "min": 0, "max": 0}
            return {
                "mean": round(sum(values) / len(values), 2),
                "min": min(values),
                "max": max(values),
            }

        return {
            "dataset_info": {
                "name": "xsum",
                "domain": "news",
                "language": "en",
            },
            "counts": {
                "total_records_examined": total_examined,
                "total_invalid_records": total_invalid,
                "total_duplicate_records": total_duplicates,
                "empty_documents": empty_documents,
                "empty_summaries": empty_summaries,
                "final_development_dataset_size": len(records),
                "causal_candidates_count": causal_candidates,
                "non_causal_candidates_count": non_candidates,
            },
            "length_statistics": {
                "document_length_characters": compute_metrics(doc_char_lens),
                "document_length_words": compute_metrics(doc_word_lens),
                "summary_length_characters": compute_metrics(sum_char_lens),
                "summary_length_words": compute_metrics(sum_word_lens),
            },
        }
