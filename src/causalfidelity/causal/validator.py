"""Validation utilities for extracted causal relations."""

from typing import Optional, Tuple

from causalfidelity.causal.schema import CausalRelation


class CausalRelationValidator:
    """Validates structural and semantic sanity constraints of extracted CausalRelation objects."""

    @staticmethod
    def validate_relation(relation: CausalRelation) -> Tuple[bool, Optional[str]]:
        """Validate a CausalRelation instance.

        Returns:
            Tuple of (is_valid: bool, rejection_reason: Optional[str])
        """
        if not relation:
            return False, "Relation object is None"

        if not relation.document_id or not relation.document_id.strip():
            return False, "Missing document_id"

        if not relation.cause or not relation.cause.strip():
            return False, "Empty cause text"

        if len(relation.cause.strip()) < 2:
            return False, "Cause text too short"

        if not relation.effect or not relation.effect.strip():
            return False, "Empty effect text"

        if len(relation.effect.strip()) < 2:
            return False, "Effect text too short"

        if relation.relation != "causes":
            return False, f"Invalid relation '{relation.relation}' (expected 'causes')"

        if not relation.source_sentence or not relation.source_sentence.strip():
            return False, "Empty source_sentence"

        if not (0.0 <= relation.confidence <= 1.0):
            return False, f"Invalid confidence value {relation.confidence}"

        # Substring/relevance check: ensure cause and effect originate from source sentence
        sent_lower = relation.source_sentence.lower()
        cause_lower = relation.cause.lower()
        effect_lower = relation.effect.lower()

        if cause_lower not in sent_lower:
            # Fallback: check if major words in cause are in sentence
            cause_words = [w for w in cause_lower.split() if len(w) > 3]
            if cause_words and not any(w in sent_lower for w in cause_words):
                return False, f"Cause '{relation.cause}' not found in source sentence"

        if effect_lower not in sent_lower:
            effect_words = [w for w in effect_lower.split() if len(w) > 3]
            if effect_words and not any(w in sent_lower for w in effect_words):
                return False, f"Effect '{relation.effect}' not found in source sentence"

        return True, None
