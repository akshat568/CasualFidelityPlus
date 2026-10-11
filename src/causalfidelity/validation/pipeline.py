"""Phase 7 Perturbation Validation & Quality Control pipeline coordinator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.config import AppConfig, load_config
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger
from causalfidelity.validation.schema import ValidationRecord
from causalfidelity.validation.validator import PerturbationQualityValidator

logger = get_logger(__name__)


class PerturbationValidationPipeline:
    """Pipeline coordinator for executing independent quality control validation over Phase 6 perturbations."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.validator = PerturbationQualityValidator()

    def run(
        self,
        input_jsonl: Optional[Path] = None,
        max_records: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 7 validation pipeline.

        Args:
            input_jsonl: Path to perturbations.jsonl (Phase 6 output).
            max_records: Optional limit on records to validate.

        Returns:
            Dictionary of pipeline execution statistics.
        """
        logger.info("Starting Phase 7 Perturbation Validation Pipeline run")
        root_dir = self.config.paths.root_dir

        if input_jsonl is None:
            input_jsonl = root_dir / self.config.validation.input_path
        else:
            input_jsonl = Path(input_jsonl)

        if not input_jsonl.exists():
            raise FileNotFoundError(
                f"Input perturbations file '{input_jsonl}' not found. Please run Phase 6 pipeline first."
            )

        # Load Phase 6 perturbation records (read-only)
        raw_perturbations: List[Dict[str, Any]] = []
        with open(input_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw_perturbations.append(json.loads(line.strip()))

        if max_records is not None and max_records > 0:
            raw_perturbations = raw_perturbations[:max_records]

        records_examined = len(raw_perturbations)
        val_records: List[ValidationRecord] = []
        raw_map: Dict[str, Dict[str, Any]] = {}

        for raw_rec in raw_perturbations:
            pid = raw_rec.get("perturbation_id", "")
            raw_map[pid] = raw_rec

            val_rec = self.validator.validate_record(raw_rec)
            val_records.append(val_rec)

        valid_count = sum(1 for r in val_records if r.validation_status == "valid")
        invalid_count = records_examined - valid_count
        val_rate = round(valid_count / records_examined, 4) if records_examined > 0 else 0.0

        counts_by_type: Dict[str, int] = {}
        status_by_type: Dict[str, Dict[str, int]] = {}
        error_counts: Dict[str, int] = {}
        warning_counts: Dict[str, int] = {}

        for r in val_records:
            ptype = r.perturbation_type or "UNKNOWN"
            counts_by_type[ptype] = counts_by_type.get(ptype, 0) + 1

            if ptype not in status_by_type:
                status_by_type[ptype] = {"valid": 0, "invalid": 0}

            if r.validation_status == "valid":
                status_by_type[ptype]["valid"] += 1
            else:
                status_by_type[ptype]["invalid"] += 1

            for err in r.errors:
                error_counts[err] = error_counts.get(err, 0) + 1
            for warn in r.warnings:
                warning_counts[warn] = warning_counts.get(warn, 0) + 1

        # Write output JSONL
        output_path = root_dir / self.config.validation.output_path
        self._write_jsonl(val_records, output_path)

        # Write statistics JSON
        stats = {
            "pipeline_info": {
                "phase": "Phase 7 — Perturbation Validation & Quality Control",
                "method": "deterministic_rules",
            },
            "counts": {
                "records_examined": records_examined,
                "valid_records": valid_count,
                "invalid_records": invalid_count,
                "validation_rate": val_rate,
            },
            "counts_by_type": counts_by_type,
            "status_by_type": status_by_type,
            "error_counts": error_counts,
            "warning_counts": warning_counts,
        }

        stats_path = root_dir / self.config.validation.stats_path
        save_json(stats, stats_path)

        # Write detailed inspection sample with original vs perturbed texts for manual inspection
        sample_path = root_dir / self.config.validation.sample_path
        self._write_inspection_sample(val_records, raw_map, sample_path)

        logger.info(
            f"Phase 7 Validation Pipeline complete. Validated {records_examined} records: {valid_count} valid ({val_rate * 100:.1f}%), {invalid_count} invalid."
        )
        return stats

    @staticmethod
    def _write_jsonl(records: List[ValidationRecord], file_path: Path) -> None:
        ensure_dir(file_path.parent)
        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _write_inspection_sample(
        val_records: List[ValidationRecord],
        raw_map: Dict[str, Dict[str, Any]],
        sample_path: Path,
    ) -> None:
        # Group by perturbation type to ensure representative samples for all 5 types
        samples_by_type: Dict[str, List[Dict[str, Any]]] = {}

        for val_rec in val_records:
            pid = val_rec.perturbation_id
            raw = raw_map.get(pid, {})
            ptype = val_rec.perturbation_type

            item = {
                "perturbation_id": val_rec.perturbation_id,
                "document_id": val_rec.document_id,
                "summary_id": val_rec.summary_id,
                "perturbation_type": val_rec.perturbation_type,
                "original_text": raw.get("original_text", ""),
                "perturbed_text": raw.get("perturbed_text", ""),
                "validation_status": val_rec.validation_status,
                "checks": val_rec.checks,
                "errors": val_rec.errors,
                "warnings": val_rec.warnings,
            }

            if ptype not in samples_by_type:
                samples_by_type[ptype] = []
            samples_by_type[ptype].append(item)

        sample_list = []
        for ptype, items in samples_by_type.items():
            sample_list.extend(items)

        save_json({"validation_sample": sample_list}, sample_path)
