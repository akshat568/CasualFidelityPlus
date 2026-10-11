"""Phase 5 Summary Input Pipeline coordinator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.config import AppConfig, load_config
from causalfidelity.summary.schema import SummaryRecord, generate_summary_id
from causalfidelity.summary.validator import SummaryValidator
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class SummaryInputPipeline:
    """Pipeline coordinator for creating canonical summary-input artifacts from Phase 2 records."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.validator = SummaryValidator(expected_summary_type="reference")

    def run(
        self,
        input_jsonl: Optional[Path] = None,
        max_documents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 5 summary input pipeline.

        Args:
            input_jsonl: Path to input JSONL file (defaults to data/processed/xsum_dev.jsonl).
            max_documents: Optional limit on maximum records to process.

        Returns:
            Dictionary containing pipeline execution statistics.
        """
        logger.info("Starting Phase 5 Summary Input Pipeline run")
        self.validator.reset()

        root_dir = self.config.paths.root_dir
        if input_jsonl is None:
            input_jsonl = root_dir / self.config.summary_input.input_file
        else:
            input_jsonl = Path(input_jsonl)

        if not input_jsonl.exists():
            raise FileNotFoundError(
                f"Input dataset '{input_jsonl}' not found. Please run Phase 2 pipeline first."
            )

        # Load raw records
        raw_records: List[Dict[str, Any]] = []
        with open(input_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw_records.append(json.loads(line.strip()))

        if max_documents is not None and max_documents > 0:
            raw_records = raw_records[:max_documents]

        records_examined = 0
        valid_summaries_list: List[SummaryRecord] = []
        invalid_summaries_count = 0
        missing_summaries_count = 0
        duplicate_doc_ids_count = 0
        duplicate_sum_ids_count = 0
        rejection_reasons: Dict[str, int] = {}

        for item in raw_records:
            records_examined += 1

            doc_id = item.get("document_id", "")
            source_text = item.get("source_text", "")
            ref_summary = item.get("reference_summary", "")
            meta = item.get("metadata", {})

            # Check for missing summary text or missing source text
            if not ref_summary or not str(ref_summary).strip():
                missing_summaries_count += 1

            # Prepare fields
            summary_text = str(ref_summary).strip() if ref_summary else ""
            summary_type = "reference"
            summary_id = generate_summary_id(doc_id, summary_type) if doc_id else ""

            # Compute word counts
            source_word_count = len(str(source_text).split()) if source_text else 0
            summary_word_count = len(summary_text.split()) if summary_text else 0

            # Compute compression ratio
            if source_word_count > 0:
                compression_ratio = round(summary_word_count / source_word_count, 10)
            else:
                compression_ratio = None

            record = SummaryRecord(
                document_id=doc_id,
                summary_id=summary_id,
                summary_text=summary_text,
                summary_type=summary_type,
                metadata=meta if isinstance(meta, dict) else {},
                source_word_count=source_word_count,
                summary_word_count=summary_word_count,
                compression_ratio=compression_ratio,
            )

            is_valid, reason = self.validator.validate_record(record)
            if not is_valid:
                invalid_summaries_count += 1
                reason_str = reason or "unknown"
                if "duplicate_document_id" in reason_str:
                    duplicate_doc_ids_count += 1
                elif "duplicate_summary_id" in reason_str:
                    duplicate_sum_ids_count += 1

                rejection_reasons[reason_str] = rejection_reasons.get(reason_str, 0) + 1
                logger.warning(f"Record rejected for doc '{doc_id}': {reason_str}")
                continue

            self.validator.register(record)
            valid_summaries_list.append(record)

        # Write output JSONL
        output_jsonl_path = root_dir / self.config.summary_input.output_file
        self._write_jsonl(valid_summaries_list, output_jsonl_path)

        # Calculate statistics
        stats = self._calculate_statistics(
            records_examined=records_examined,
            valid_summaries=valid_summaries_list,
            invalid_summaries=invalid_summaries_count,
            missing_summaries=missing_summaries_count,
            duplicate_doc_ids=duplicate_doc_ids_count,
            duplicate_sum_ids=duplicate_sum_ids_count,
            rejection_reasons=rejection_reasons,
        )

        stats_json_path = root_dir / self.config.summary_input.stats_file
        save_json(stats, stats_json_path)

        # Write inspection sample
        sample_path = root_dir / self.config.summary_input.sample_output_file
        self._write_inspection_sample(valid_summaries_list, sample_path)

        logger.info(
            f"Phase 5 Summary Input Pipeline complete. Processed {len(valid_summaries_list)} valid summaries to '{output_jsonl_path}'."
        )
        return stats

    @staticmethod
    def _write_jsonl(records: List[SummaryRecord], file_path: Path) -> None:
        ensure_dir(file_path.parent)
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _calculate_statistics(
        records_examined: int,
        valid_summaries: List[SummaryRecord],
        invalid_summaries: int,
        missing_summaries: int,
        duplicate_doc_ids: int,
        duplicate_sum_ids: int,
        rejection_reasons: Dict[str, int],
    ) -> Dict[str, Any]:
        source_counts = [r.source_word_count for r in valid_summaries]
        summary_counts = [r.summary_word_count for r in valid_summaries]
        comp_ratios = [r.compression_ratio for r in valid_summaries if r.compression_ratio is not None]

        def compute_int_metrics(vals: List[int]) -> Dict[str, Any]:
            if not vals:
                return {"average": 0.0, "minimum": 0, "maximum": 0}
            return {
                "average": round(sum(vals) / len(vals), 2),
                "minimum": min(vals),
                "maximum": max(vals),
            }

        def compute_float_metrics(vals: List[float]) -> Dict[str, Any]:
            if not vals:
                return {"average": 0.0, "minimum": 0.0, "maximum": 0.0}
            return {
                "average": round(sum(vals) / len(vals), 4),
                "minimum": round(min(vals), 4),
                "maximum": round(max(vals), 4),
            }

        source_stats = compute_int_metrics(source_counts)
        summary_stats = compute_int_metrics(summary_counts)
        comp_stats = compute_float_metrics(comp_ratios)

        return {
            "processing": {
                "records_examined": records_examined,
                "valid_summaries": len(valid_summaries),
                "invalid_summaries": invalid_summaries,
                "missing_summaries": missing_summaries,
                "duplicate_document_ids": duplicate_doc_ids,
                "duplicate_summary_ids": duplicate_sum_ids,
                "rejection_reasons": rejection_reasons,
            },
            "length_statistics": {
                "average_source_word_count": source_stats["average"],
                "minimum_source_word_count": source_stats["minimum"],
                "maximum_source_word_count": source_stats["maximum"],
                "average_summary_word_count": summary_stats["average"],
                "minimum_summary_word_count": summary_stats["minimum"],
                "maximum_summary_word_count": summary_stats["maximum"],
            },
            "compression_statistics": {
                "average_compression_ratio": comp_stats["average"],
                "minimum_compression_ratio": comp_stats["minimum"],
                "maximum_compression_ratio": comp_stats["maximum"],
            },
        }

    @staticmethod
    def _write_inspection_sample(
        records: List[SummaryRecord],
        sample_path: Path,
        max_samples: int = 10,
    ) -> None:
        sample_list = []
        for rec in records[:max_samples]:
            sample_list.append({
                "document_id": rec.document_id,
                "summary_id": rec.summary_id,
                "summary_type": rec.summary_type,
                "summary_text": rec.summary_text,
                "source_word_count": rec.source_word_count,
                "summary_word_count": rec.summary_word_count,
                "compression_ratio": rec.compression_ratio,
            })

        save_json({"summary_sample": sample_list}, sample_path)
