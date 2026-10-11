"""Deterministic perturbation strategies for controlled causal modifications."""

import re
from typing import Any, Dict, Optional, Tuple


def _find_phrase_span(text: str, phrase: str) -> Optional[Tuple[int, int, str]]:
    """Find start index, end index, and exact matched text of phrase in text (case-insensitive)."""
    if not text or not phrase:
        return None
    match = re.search(re.escape(phrase), text, re.IGNORECASE)
    if not match:
        return None
    return match.start(), match.end(), match.group(0)


class PerturbationStrategy:
    """Base class for deterministic causal perturbation strategies."""

    perturbation_type: str = "BASE"

    def apply(
        self,
        text: str,
        cause: str,
        relation: str,
        effect: str,
        pattern_matched: Optional[str] = None,
        context_candidates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        """Apply perturbation transformation to input text.

        Returns:
            Tuple of (perturbed_text, intended_relation_dict, changed_span_dict) or None if ineligible.
        """
        raise NotImplementedError


class ReversalStrategy(PerturbationStrategy):
    """Reverses causal direction by swapping cause and effect."""

    perturbation_type: str = "REVERSED"

    def apply(
        self,
        text: str,
        cause: str,
        relation: str,
        effect: str,
        pattern_matched: Optional[str] = None,
        context_candidates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        c_span = _find_phrase_span(text, cause)
        e_span = _find_phrase_span(text, effect)

        if not c_span or not e_span:
            return None

        c_start, c_end, exact_c = c_span
        e_start, e_end, exact_e = e_span

        start_idx = min(c_start, e_start)
        end_idx = max(c_end, e_end)
        orig_span = text[start_idx:end_idx]

        def match_case(target: str, reference: str) -> str:
            if reference and reference[0].isupper():
                return target[0].upper() + target[1:] if len(target) > 1 else target.upper()
            return target[0].lower() + target[1:] if len(target) > 1 else target.lower()

        new_cause_str = match_case(effect, exact_c)
        new_effect_str = match_case(cause, exact_e)

        if c_start < e_start:
            new_span = orig_span.replace(exact_c, "___PLACEHOLDER___").replace(exact_e, new_effect_str).replace("___PLACEHOLDER___", new_cause_str)
        else:
            new_span = orig_span.replace(exact_e, "___PLACEHOLDER___").replace(exact_c, new_cause_str).replace("___PLACEHOLDER___", new_effect_str)

        perturbed_text = text[:start_idx] + new_span + text[end_idx:]

        intended_relation = {
            "cause": effect,
            "relation": "causes",
            "effect": cause,
        }
        changed_span = {
            "original": orig_span,
            "perturbed": new_span,
        }
        return perturbed_text, intended_relation, changed_span


class WeakeningStrategy(PerturbationStrategy):
    """Weakens an explicit causal relation into a weaker associative relation."""

    perturbation_type: str = "WEAKENED"

    TRIGGER_REPLACEMENTS = [
        (r"\bwas\s+caused\s+by\b", "was associated with"),
        (r"\bis\s+caused\s+by\b", "is associated with"),
        (r"\bwere\s+caused\s+by\b", "were associated with"),
        (r"\bblamed\s+for\s+causing\b", "linked to"),
        (r"\bcaused\b", "was associated with"),
        (r"\bcauses\b", "is associated with"),
        (r"\bcausing\b", "associating with"),
        (r"\bled\s+to\b", "was associated with"),
        (r"\bleads\s+to\b", "is associated with"),
        (r"\bresulted\s+in\b", "was associated with"),
        (r"\bresults\s+in\b", "is associated with"),
        (r"\btriggered\b", "coincided with"),
        (r"\bdue\s+to\b", "coinciding with"),
        (r"\bbecause\s+of\b", "alongside"),
        (r"\bbecause\b", "while"),
    ]

    def apply(
        self,
        text: str,
        cause: str,
        relation: str,
        effect: str,
        pattern_matched: Optional[str] = None,
        context_candidates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        c_span = _find_phrase_span(text, cause)
        e_span = _find_phrase_span(text, effect)

        if not c_span or not e_span:
            return None

        c_start, c_end, _ = c_span
        e_start, e_end, _ = e_span

        start_idx = min(c_start, e_start)
        end_idx = max(c_end, e_end)
        orig_span = text[start_idx:end_idx]

        new_span = orig_span
        replaced = False

        for pattern, replacement in self.TRIGGER_REPLACEMENTS:
            if re.search(pattern, new_span, re.IGNORECASE):
                new_span = re.sub(pattern, replacement, new_span, count=1, flags=re.IGNORECASE)
                replaced = True
                break

        if not replaced or new_span == orig_span:
            return None

        perturbed_text = text[:start_idx] + new_span + text[end_idx:]

        intended_relation = {
            "cause": cause,
            "relation": "weakened",
            "effect": effect,
        }
        changed_span = {
            "original": orig_span,
            "perturbed": new_span,
        }
        return perturbed_text, intended_relation, changed_span


class DeletionStrategy(PerturbationStrategy):
    """Removes the explicit causal relationship while preserving cause and effect entities (DROPPED)."""

    perturbation_type: str = "DROPPED"

    TRIGGER_DELETIONS = [
        (r"\bwas\s+caused\s+by\b", "and"),
        (r"\bis\s+caused\s+by\b", "and"),
        (r"\bwere\s+caused\s+by\b", "and"),
        (r"\bblamed\s+for\s+causing\b", "associated with"),
        (r"\bcaused\b", "occurred and"),
        (r"\bcauses\b", "and"),
        (r"\bcausing\b", "and"),
        (r"\bled\s+to\b", "and"),
        (r"\bleads\s+to\b", "and"),
        (r"\bresulted\s+in\b", "and"),
        (r"\bresults\s+in\b", "and"),
        (r"\btriggered\b", "and"),
        (r"\bdue\s+to\b", "alongside"),
        (r"\bbecause\s+of\b", "alongside"),
        (r"\bbecause\b", "and"),
    ]

    def apply(
        self,
        text: str,
        cause: str,
        relation: str,
        effect: str,
        pattern_matched: Optional[str] = None,
        context_candidates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        c_span = _find_phrase_span(text, cause)
        e_span = _find_phrase_span(text, effect)

        if not c_span or not e_span:
            return None

        c_start, c_end, _ = c_span
        e_start, e_end, _ = e_span

        start_idx = min(c_start, e_start)
        end_idx = max(c_end, e_end)
        orig_span = text[start_idx:end_idx]

        new_span = orig_span
        replaced = False

        for pattern, replacement in self.TRIGGER_DELETIONS:
            if re.search(pattern, new_span, re.IGNORECASE):
                new_span = re.sub(pattern, replacement, new_span, count=1, flags=re.IGNORECASE)
                replaced = True
                break

        if not replaced or new_span == orig_span:
            return None

        perturbed_text = text[:start_idx] + new_span + text[end_idx:]

        intended_relation = {
            "cause": cause,
            "relation": "none",
            "effect": effect,
        }
        changed_span = {
            "original": orig_span,
            "perturbed": new_span,
        }
        return perturbed_text, intended_relation, changed_span


class CauseSubstitutionStrategy(PerturbationStrategy):
    """Replaces original cause with a candidate cause from the same source document context."""

    perturbation_type: str = "CAUSE_CHANGED"

    def apply(
        self,
        text: str,
        cause: str,
        relation: str,
        effect: str,
        pattern_matched: Optional[str] = None,
        context_candidates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        c_span = _find_phrase_span(text, cause)
        if not c_span:
            return None

        c_start, c_end, exact_c = c_span

        candidates = (context_candidates or {}).get("candidate_causes", [])
        valid_replacement = None

        for cand in candidates:
            if cand and isinstance(cand, str):
                cand_clean = cand.strip()
                if cand_clean and cand_clean.lower() != cause.lower() and cand_clean.lower() != effect.lower():
                    valid_replacement = cand_clean
                    break

        if not valid_replacement:
            return None

        orig_span = exact_c
        new_span = valid_replacement

        perturbed_text = text[:c_start] + new_span + text[c_end:]

        intended_relation = {
            "cause": valid_replacement,
            "relation": "causes",
            "effect": effect,
        }
        changed_span = {
            "original": orig_span,
            "perturbed": new_span,
        }
        return perturbed_text, intended_relation, changed_span


class EffectSubstitutionStrategy(PerturbationStrategy):
    """Replaces original effect with a candidate effect from the same source document context."""

    perturbation_type: str = "EFFECT_CHANGED"

    def apply(
        self,
        text: str,
        cause: str,
        relation: str,
        effect: str,
        pattern_matched: Optional[str] = None,
        context_candidates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        e_span = _find_phrase_span(text, effect)
        if not e_span:
            return None

        e_start, e_end, exact_e = e_span

        candidates = (context_candidates or {}).get("candidate_effects", [])
        valid_replacement = None

        for cand in candidates:
            if cand and isinstance(cand, str):
                cand_clean = cand.strip()
                if cand_clean and cand_clean.lower() != effect.lower() and cand_clean.lower() != cause.lower():
                    valid_replacement = cand_clean
                    break

        if not valid_replacement:
            return None

        orig_span = exact_e
        new_span = valid_replacement

        perturbed_text = text[:e_start] + new_span + text[e_end:]

        intended_relation = {
            "cause": cause,
            "relation": "causes",
            "effect": valid_replacement,
        }
        changed_span = {
            "original": orig_span,
            "perturbed": new_span,
        }
        return perturbed_text, intended_relation, changed_span
