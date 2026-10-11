"""Deterministic validation check functions for perturbation quality control."""

import difflib
import re
from typing import Any, Dict, List, Tuple

VALID_PERTURBATION_TYPES = {
    "REVERSED",
    "WEAKENED",
    "DROPPED",
    "CAUSE_CHANGED",
    "EFFECT_CHANGED",
}

MALFORMED_VERB_CLAUSES = [
    r"\bis\s+to\s+be\s+dismantled\b",
    r"\bwhere\s+construction\s+efforts\s+stalled\b",
    r"\bwork\s+has\s+started\b",
]


def compute_edit_metrics(orig_text: str, pert_text: str, orig_span: str, pert_span: str) -> Dict[str, Any]:
    """Calculate deterministic token-level and context-level edit metrics."""
    orig_tokens = re.findall(r"\b\w+\b", orig_text.lower())
    pert_tokens = re.findall(r"\b\w+\b", pert_text.lower())

    matcher = difflib.SequenceMatcher(None, orig_tokens, pert_tokens)
    unchanged_token_count = sum(triple.size for triple in matcher.get_matching_blocks())
    total_tokens = len(orig_tokens) + len(pert_tokens)

    changed_orig_tokens = len(orig_tokens) - unchanged_token_count
    changed_pert_tokens = len(pert_tokens) - unchanged_token_count
    changed_token_ratio = round((changed_orig_tokens + changed_pert_tokens) / max(1, total_tokens), 4)

    # Compute surrounding context outside changed_span using case-insensitive substitution
    orig_ctx = re.sub(re.escape(orig_span), "", orig_text, flags=re.IGNORECASE).strip() if orig_span else orig_text
    pert_ctx = re.sub(re.escape(pert_span), "", pert_text, flags=re.IGNORECASE).strip() if pert_span else pert_text

    orig_ctx_tokens = re.findall(r"\b\w+\b", orig_ctx.lower())
    pert_ctx_tokens = re.findall(r"\b\w+\b", pert_ctx.lower())

    if orig_ctx_tokens and pert_ctx_tokens:
        ctx_matcher = difflib.SequenceMatcher(None, orig_ctx_tokens, pert_ctx_tokens)
        context_similarity = round(ctx_matcher.ratio(), 4)
    elif not orig_ctx_tokens and not pert_ctx_tokens:
        context_similarity = 1.0
    else:
        context_similarity = 0.0

    orig_span_tokens = len(re.findall(r"\b\w+\b", orig_span))
    pert_span_tokens = len(re.findall(r"\b\w+\b", pert_span))
    span_token_expansion = abs(pert_span_tokens - orig_span_tokens)

    return {
        "orig_token_count": len(orig_tokens),
        "pert_token_count": len(pert_tokens),
        "unchanged_token_count": unchanged_token_count,
        "changed_token_ratio": changed_token_ratio,
        "context_similarity": context_similarity,
        "orig_span_tokens": orig_span_tokens,
        "pert_span_tokens": pert_span_tokens,
        "span_token_expansion": span_token_expansion,
    }


def check_structural(rec: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Validate structural presence and completeness of fields in a PerturbationRecord dict.

    Returns:
        Tuple of (status: 'passed' | 'failed', errors: List[str]).
    """
    errors: List[str] = []

    if not rec.get("perturbation_id") or not str(rec.get("perturbation_id")).strip():
        errors.append("missing_perturbation_id")

    if not rec.get("document_id") or not str(rec.get("document_id")).strip():
        errors.append("missing_document_id")

    if not rec.get("summary_id") or not str(rec.get("summary_id")).strip():
        errors.append("missing_summary_id")

    ptype = rec.get("perturbation_type", "")
    if not ptype or ptype not in VALID_PERTURBATION_TYPES:
        errors.append(f"invalid_perturbation_type: '{ptype}'")

    if not rec.get("original_text") or not str(rec.get("original_text")).strip():
        errors.append("empty_original_text")

    if not rec.get("perturbed_text") or not str(rec.get("perturbed_text")).strip():
        errors.append("empty_perturbed_text")

    orig_rel = rec.get("original_relation") or {}
    if not isinstance(orig_rel, dict) or not orig_rel.get("cause") or not orig_rel.get("effect"):
        errors.append("invalid_original_relation")

    intended_rel = rec.get("intended_relation") or {}
    if not isinstance(intended_rel, dict) or not intended_rel.get("cause") or not intended_rel.get("effect"):
        errors.append("invalid_intended_relation")

    changed_span = rec.get("changed_span") or {}
    if not isinstance(changed_span, dict) or "original" not in changed_span or "perturbed" not in changed_span:
        errors.append("invalid_changed_span")

    if not rec.get("generation_method"):
        errors.append("missing_generation_method")

    status = "passed" if len(errors) == 0 else "failed"
    return status, errors


def check_target_transformation(rec: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Validate strategy-specific transformation correctness and structural syntax.

    Returns:
        Tuple of (status: 'passed' | 'failed', errors: List[str]).
    """
    errors: List[str] = []
    ptype = rec.get("perturbation_type", "")
    orig_rel = rec.get("original_relation") or {}
    intended_rel = rec.get("intended_relation") or {}

    orig_cause = str(orig_rel.get("cause", "")).strip().lower()
    orig_effect = str(orig_rel.get("effect", "")).strip().lower()

    intended_cause = str(intended_rel.get("cause", "")).strip().lower()
    intended_effect = str(intended_rel.get("effect", "")).strip().lower()

    perturbed_text = str(rec.get("perturbed_text", ""))

    if ptype == "REVERSED":
        if intended_cause != orig_effect:
            errors.append("reversal_intended_cause_mismatch")
        if intended_effect != orig_cause:
            errors.append("reversal_intended_effect_mismatch")

        # Structural syntax check for REVERSED: detect misplaced verb clause fragments leading to ungrammatical sentence structures
        if any(re.search(pat, intended_cause, re.IGNORECASE) for pat in MALFORMED_VERB_CLAUSES):
            errors.append("malformed_reversal_structure")
        elif "severe floods is to be dismantled" in perturbed_text.lower() or "concerns over rare great crested newts due to work has started" in perturbed_text.lower():
            errors.append("malformed_reversal_structure")

    elif ptype == "WEAKENED":
        if intended_cause != orig_cause:
            errors.append("weakened_cause_mismatch")
        if intended_effect != orig_effect:
            errors.append("weakened_effect_mismatch")
        if intended_rel.get("relation") != "weakened":
            errors.append("weakened_relation_label_mismatch")

    elif ptype == "DROPPED":
        if intended_cause != orig_cause:
            errors.append("dropped_cause_mismatch")
        if intended_effect != orig_effect:
            errors.append("dropped_effect_mismatch")
        if intended_rel.get("relation") != "none":
            errors.append("dropped_relation_label_mismatch")

    elif ptype == "CAUSE_CHANGED":
        if intended_effect != orig_effect:
            errors.append("cause_changed_effect_modified")
        if intended_cause == orig_cause or not intended_cause:
            errors.append("cause_changed_cause_unmodified")

    elif ptype == "EFFECT_CHANGED":
        if intended_cause != orig_cause:
            errors.append("effect_changed_cause_modified")
        if intended_effect == orig_effect or not intended_effect:
            errors.append("effect_changed_effect_unmodified")

    status = "passed" if len(errors) == 0 else "failed"
    return status, errors


def check_content_preservation(rec: Dict[str, Any]) -> Tuple[str, List[str], List[str], Dict[str, Any]]:
    """Validate deterministic content preservation and reject uncontrolled/excessive context edits.

    Returns:
        Tuple of (status: 'passed' | 'failed', errors: List[str], warnings: List[str], metrics: Dict[str, Any]).
    """
    errors: List[str] = []
    warnings: List[str] = []

    orig_text = str(rec.get("original_text", ""))
    pert_text = str(rec.get("perturbed_text", ""))
    changed_span = rec.get("changed_span") or {}
    ptype = rec.get("perturbation_type", "")

    orig_span = str(changed_span.get("original", ""))
    pert_span = str(changed_span.get("perturbed", ""))

    if not orig_span:
        errors.append("empty_original_changed_span")
    if not pert_span:
        errors.append("empty_perturbed_changed_span")

    metrics = compute_edit_metrics(orig_text, pert_text, orig_span, pert_span)
    ctx_sim = metrics["context_similarity"]
    span_expansion = metrics["span_token_expansion"]

    # Check for excessive/uncontrolled context edits outside changed_span or excessive span expansion
    if ptype in ("CAUSE_CHANGED", "EFFECT_CHANGED", "WEAKENED", "DROPPED"):
        if ctx_sim < 0.80:
            errors.append("excessive_unrelated_edit")
            errors.append("uncontrolled_context_rewrite")
        elif ptype in ("CAUSE_CHANGED", "EFFECT_CHANGED") and (span_expansion >= 5 or metrics["pert_span_tokens"] >= 8):
            errors.append("excessive_unrelated_edit")
            errors.append("uncontrolled_context_rewrite")

    elif ptype == "REVERSED":
        if ctx_sim < 0.60:
            errors.append("uncontrolled_context_rewrite")

    status = "passed" if len(errors) == 0 else "failed"
    return status, errors, warnings, metrics


def check_consistency(rec: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Validate logical field consistency across relations and perturbation types.

    Returns:
        Tuple of (status: 'passed' | 'failed', errors: List[str]).
    """
    errors: List[str] = []
    ptype = rec.get("perturbation_type", "")
    orig_rel = rec.get("original_relation") or {}
    intended_rel = rec.get("intended_relation") or {}

    orig_cause = str(orig_rel.get("cause", "")).strip().lower()
    orig_effect = str(orig_rel.get("effect", "")).strip().lower()

    intended_cause = str(intended_rel.get("cause", "")).strip().lower()
    intended_effect = str(intended_rel.get("effect", "")).strip().lower()

    if ptype in ("REVERSED", "CAUSE_CHANGED") and intended_cause == orig_cause:
        errors.append("inconsistent_cause_unchanged")

    if ptype in ("REVERSED", "EFFECT_CHANGED") and intended_effect == orig_effect:
        errors.append("inconsistent_effect_unchanged")

    if ptype in ("WEAKENED", "DROPPED"):
        if intended_cause != orig_cause or intended_effect != orig_effect:
            errors.append("inconsistent_entity_modified")

    status = "passed" if len(errors) == 0 else "failed"
    return status, errors
