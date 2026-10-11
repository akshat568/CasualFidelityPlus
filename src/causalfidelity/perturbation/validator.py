"""Validation component for controlled causal perturbations."""

from typing import List, Tuple

from causalfidelity.perturbation.schema import PerturbationRecord

SUPPORTED_PERTURBATION_TYPES = {
    "REVERSED",
    "WEAKENED",
    "DROPPED",
    "CAUSE_CHANGED",
    "EFFECT_CHANGED",
}


class PerturbationValidator:
    """Validates PerturbationRecord instances against structural and strategy rules."""

    def validate(self, record: PerturbationRecord) -> Tuple[bool, List[str]]:
        """Validate a PerturbationRecord.

        Args:
            record: PerturbationRecord instance to validate.

        Returns:
            Tuple of (is_valid: bool, validation_errors: List[str]).
        """
        errors: List[str] = []

        if not record.document_id or not record.document_id.strip():
            errors.append("missing_document_id")

        if not record.summary_id or not record.summary_id.strip():
            errors.append("missing_summary_id")

        if not record.original_text or not record.original_text.strip():
            errors.append("empty_original_text")

        if not record.perturbed_text or not record.perturbed_text.strip():
            errors.append("empty_perturbed_text")

        if record.perturbation_type not in SUPPORTED_PERTURBATION_TYPES:
            errors.append(f"unsupported_perturbation_type: '{record.perturbation_type}'")

        orig_rel = record.original_relation or {}
        orig_cause = orig_rel.get("cause", "")
        orig_effect = orig_rel.get("effect", "")

        if not orig_cause or not orig_effect:
            errors.append("invalid_original_relation")

        intended_rel = record.intended_relation or {}
        intended_cause = intended_rel.get("cause", "")
        intended_effect = intended_rel.get("effect", "")

        # Strategy-specific validation rules
        ptype = record.perturbation_type

        if ptype == "REVERSED":
            if intended_cause.lower() != orig_effect.lower():
                errors.append("reversal_intended_cause_mismatch")
            if intended_effect.lower() != orig_cause.lower():
                errors.append("reversal_intended_effect_mismatch")

        elif ptype == "WEAKENED":
            if intended_cause.lower() != orig_cause.lower():
                errors.append("weakening_cause_modified")
            if intended_effect.lower() != orig_effect.lower():
                errors.append("weakening_effect_modified")

        elif ptype == "DROPPED":
            if intended_cause.lower() != orig_cause.lower():
                errors.append("dropped_cause_modified")
            if intended_effect.lower() != orig_effect.lower():
                errors.append("dropped_effect_modified")

        elif ptype == "CAUSE_CHANGED":
            if intended_effect.lower() != orig_effect.lower():
                errors.append("cause_changed_effect_modified")
            if intended_cause.lower() == orig_cause.lower():
                errors.append("cause_changed_cause_unmodified")

        elif ptype == "EFFECT_CHANGED":
            if intended_cause.lower() != orig_cause.lower():
                errors.append("effect_changed_cause_modified")
            if intended_effect.lower() == orig_effect.lower():
                errors.append("effect_changed_effect_unmodified")

        is_valid = len(errors) == 0
        return is_valid, errors
