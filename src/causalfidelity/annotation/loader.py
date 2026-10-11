"""Batch ingestion pipeline for Phase 12 human annotations (JSONL and CSV)."""

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from causalfidelity.annotation.schema import AnnotationRecord, validate_annotation_dict
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)

REQUIRED_CSV_COLUMNS = {
    "annotation_id",
    "perturbation_id",
    "annotator_id",
    "causal_label",
    "naturalness_rating",
}


@dataclass
class IngestionResult:
    """Result container for batch annotation ingestion."""

    valid_records: List[AnnotationRecord] = field(default_factory=list)
    invalid_records: List[Dict[str, Any]] = field(default_factory=list)
    errors_by_line: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class AnnotationLoader:
    """Loader and validator for batch human annotation files in JSONL or CSV format."""

    def load_file(self, file_path: Union[str, Path]) -> IngestionResult:
        """Load and validate annotations from file, auto-detecting format from extension.

        Args:
            file_path: Path to JSONL or CSV file.

        Returns:
            IngestionResult containing valid records, invalid records, and summary.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Annotation file not found: {path}")

        ext = path.suffix.lower()
        if ext in (".jsonl", ".json"):
            return self.load_jsonl(path)
        elif ext == ".csv":
            return self.load_csv(path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Expected '.jsonl' or '.csv'.")

    def load_from_list(self, raw_records: List[Dict[str, Any]]) -> IngestionResult:
        """Load and validate an in-memory list of raw annotation dictionaries.

        Args:
            raw_records: List of dictionary records.

        Returns:
            IngestionResult instance.
        """
        seen_ann_ids: Set[str] = set()
        seen_pairs: Set[Tuple[str, str]] = set()

        valid_records: List[AnnotationRecord] = []
        invalid_records: List[Dict[str, Any]] = []
        errors_by_line: List[Dict[str, Any]] = []

        dup_ann_count = 0
        dup_pair_count = 0

        for idx, raw_dict in enumerate(raw_records, start=1):
            if not isinstance(raw_dict, dict):
                err = {
                    "line_number": idx,
                    "errors": ["invalid_record_format"],
                    "raw_data": raw_dict,
                }
                invalid_records.append(err)
                errors_by_line.append(err)
                continue

            is_valid, errors = validate_annotation_dict(raw_dict)
            ann_id = str(raw_dict.get("annotation_id", "")).strip()
            user_id = str(raw_dict.get("annotator_id", "")).strip()
            item_id = str(raw_dict.get("perturbation_id", "")).strip()
            pair = (user_id, item_id)

            if ann_id and ann_id in seen_ann_ids:
                errors.append(f"duplicate_annotation_id: '{ann_id}'")
                dup_ann_count += 1

            if user_id and item_id and pair in seen_pairs:
                errors.append(f"duplicate_annotator_item_pair: '{user_id}' -> '{item_id}'")
                dup_pair_count += 1

            if is_valid and not any(e.startswith("duplicate_") for e in errors):
                rec = AnnotationRecord.from_dict(raw_dict)
                valid_records.append(rec)
                seen_ann_ids.add(ann_id)
                seen_pairs.add(pair)
            else:
                record_entry = {
                    "line_number": idx,
                    "errors": errors,
                    "raw_data": raw_dict,
                }
                invalid_records.append(record_entry)
                errors_by_line.append(record_entry)

        summary = {
            "total_records_processed": len(raw_records),
            "valid_records_count": len(valid_records),
            "invalid_records_count": len(invalid_records),
            "duplicate_annotation_ids": dup_ann_count,
            "duplicate_annotator_item_pairs": dup_pair_count,
            "file_path": None,
        }

        return IngestionResult(
            valid_records=valid_records,
            invalid_records=invalid_records,
            errors_by_line=errors_by_line,
            summary=summary,
        )

    def load_jsonl(self, file_path: Union[str, Path]) -> IngestionResult:
        """Ingest and validate annotation records from a JSONL file.

        Args:
            file_path: Path to JSONL file.

        Returns:
            IngestionResult instance.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSONL file not found: {path}")

        seen_ann_ids: Set[str] = set()
        seen_pairs: Set[Tuple[str, str]] = set()

        valid_records: List[AnnotationRecord] = []
        invalid_records: List[Dict[str, Any]] = []
        errors_by_line: List[Dict[str, Any]] = []

        dup_ann_count = 0
        dup_pair_count = 0
        total_processed = 0

        with open(path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue  # Ignore empty lines cleanly

                total_processed += 1

                try:
                    raw_dict = json.loads(line_str)
                except json.JSONDecodeError as err:
                    record_entry = {
                        "line_number": line_idx,
                        "errors": [f"malformed_json_syntax: {str(err)}"],
                        "raw_data": line_str,
                    }
                    invalid_records.append(record_entry)
                    errors_by_line.append(record_entry)
                    continue

                if not isinstance(raw_dict, dict):
                    record_entry = {
                        "line_number": line_idx,
                        "errors": ["invalid_record_format"],
                        "raw_data": raw_dict,
                    }
                    invalid_records.append(record_entry)
                    errors_by_line.append(record_entry)
                    continue

                is_valid, errors = validate_annotation_dict(raw_dict)
                ann_id = str(raw_dict.get("annotation_id", "")).strip()
                user_id = str(raw_dict.get("annotator_id", "")).strip()
                item_id = str(raw_dict.get("perturbation_id", "")).strip()
                pair = (user_id, item_id)

                if ann_id and ann_id in seen_ann_ids:
                    errors.append(f"duplicate_annotation_id: '{ann_id}'")
                    dup_ann_count += 1

                if user_id and item_id and pair in seen_pairs:
                    errors.append(f"duplicate_annotator_item_pair: '{user_id}' -> '{item_id}'")
                    dup_pair_count += 1

                if is_valid and not any(e.startswith("duplicate_") for e in errors):
                    rec = AnnotationRecord.from_dict(raw_dict)
                    valid_records.append(rec)
                    seen_ann_ids.add(ann_id)
                    seen_pairs.add(pair)
                else:
                    record_entry = {
                        "line_number": line_idx,
                        "errors": errors,
                        "raw_data": raw_dict,
                    }
                    invalid_records.append(record_entry)
                    errors_by_line.append(record_entry)

        summary = {
            "total_records_processed": total_processed,
            "valid_records_count": len(valid_records),
            "invalid_records_count": len(invalid_records),
            "duplicate_annotation_ids": dup_ann_count,
            "duplicate_annotator_item_pairs": dup_pair_count,
            "file_path": str(path),
        }

        logger.info(
            f"Ingested JSONL '{path.name}': {len(valid_records)} valid, {len(invalid_records)} invalid (Total: {total_processed})"
        )

        return IngestionResult(
            valid_records=valid_records,
            invalid_records=invalid_records,
            errors_by_line=errors_by_line,
            summary=summary,
        )

    def load_csv(self, file_path: Union[str, Path]) -> IngestionResult:
        """Ingest and validate annotation records from a CSV file.

        Args:
            file_path: Path to CSV file.

        Returns:
            IngestionResult instance.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        seen_ann_ids: Set[str] = set()
        seen_pairs: Set[Tuple[str, str]] = set()

        valid_records: List[AnnotationRecord] = []
        invalid_records: List[Dict[str, Any]] = []
        errors_by_line: List[Dict[str, Any]] = []

        dup_ann_count = 0
        dup_pair_count = 0
        total_processed = 0

        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])

            missing_cols = REQUIRED_CSV_COLUMNS - headers
            if missing_cols:
                err_msg = f"missing_csv_columns: {sorted(list(missing_cols))}"
                summary = {
                    "total_records_processed": 0,
                    "valid_records_count": 0,
                    "invalid_records_count": 1,
                    "duplicate_annotation_ids": 0,
                    "duplicate_annotator_item_pairs": 0,
                    "file_path": str(path),
                    "header_error": err_msg,
                }
                err_entry = {"line_number": 1, "errors": [err_msg], "raw_data": None}
                return IngestionResult(
                    valid_records=[],
                    invalid_records=[err_entry],
                    errors_by_line=[err_entry],
                    summary=summary,
                )

            for row_idx, row in enumerate(reader, start=2):  # Row 1 is header
                total_processed += 1
                raw_dict = dict(row)

                is_valid, errors = validate_annotation_dict(raw_dict)
                ann_id = str(raw_dict.get("annotation_id", "")).strip()
                user_id = str(raw_dict.get("annotator_id", "")).strip()
                item_id = str(raw_dict.get("perturbation_id", "")).strip()
                pair = (user_id, item_id)

                if ann_id and ann_id in seen_ann_ids:
                    errors.append(f"duplicate_annotation_id: '{ann_id}'")
                    dup_ann_count += 1

                if user_id and item_id and pair in seen_pairs:
                    errors.append(f"duplicate_annotator_item_pair: '{user_id}' -> '{item_id}'")
                    dup_pair_count += 1

                if is_valid and not any(e.startswith("duplicate_") for e in errors):
                    rec = AnnotationRecord.from_dict(raw_dict)
                    valid_records.append(rec)
                    seen_ann_ids.add(ann_id)
                    seen_pairs.add(pair)
                else:
                    record_entry = {
                        "line_number": row_idx,
                        "errors": errors,
                        "raw_data": raw_dict,
                    }
                    invalid_records.append(record_entry)
                    errors_by_line.append(record_entry)

        summary = {
            "total_records_processed": total_processed,
            "valid_records_count": len(valid_records),
            "invalid_records_count": len(invalid_records),
            "duplicate_annotation_ids": dup_ann_count,
            "duplicate_annotator_item_pairs": dup_pair_count,
            "file_path": str(path),
        }

        logger.info(
            f"Ingested CSV '{path.name}': {len(valid_records)} valid, {len(invalid_records)} invalid (Total: {total_processed})"
        )

        return IngestionResult(
            valid_records=valid_records,
            invalid_records=invalid_records,
            errors_by_line=errors_by_line,
            summary=summary,
        )
