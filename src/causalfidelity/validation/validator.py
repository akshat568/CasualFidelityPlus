"""Perturbation quality validator orchestrating structural, relational, and consistency checks."""

from typing import Any, Dict, Union

from causalfidelity.perturbation.schema import PerturbationRecord
from causalfidelity.validation.checks import (
    check_consistency,
    check_content_preservation,
    check_structural,
    check_target_transformation,
)
from causalfidelity.validation.schema import ValidationRecord


class PerturbationQualityValidator:
    """Orchestrates independent quality control validation checks on Phase 6 perturbations."""

    def validate_record(self, record: Union[Dict[str, Any], PerturbationRecord]) -> ValidationRecord:
        """Validate a single perturbation record.

        Args:
            record: Dict or PerturbationRecord instance to validate.

        Returns:
            ValidationRecord containing overall status, sub-check statuses, errors, and warnings.
        """
        rec_dict = record.to_dict() if isinstance(record, PerturbationRecord) else record

        pert_id = rec_dict.get("perturbation_id", "")
        doc_id = rec_dict.get("document_id", "")
        sum_id = rec_dict.get("summary_id", "")
        ptype = rec_dict.get("perturbation_type", "")

        # Execute check functions
        s_status, s_errors = check_structural(rec_dict)
        t_status, t_errors = check_target_transformation(rec_dict)
        p_status, p_errors, p_warnings, p_metrics = check_content_preservation(rec_dict)
        c_status, c_errors = check_consistency(rec_dict)

        all_errors = s_errors + t_errors + p_errors + c_errors
        all_warnings = p_warnings

        overall_status = "invalid" if len(all_errors) > 0 else "valid"

        checks_summary = {
            "structural": s_status,
            "target_transformation": t_status,
            "content_preservation": p_status,
            "consistency": c_status,
        }

        return ValidationRecord(
            perturbation_id=pert_id,
            document_id=doc_id,
            summary_id=sum_id,
            perturbation_type=ptype,
            validation_status=overall_status,
            checks=checks_summary,
            errors=all_errors,
            warnings=all_warnings,
        )
