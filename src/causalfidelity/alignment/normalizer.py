"""Normalizer utilities for exact string matching and relation trigger compatibility."""

import re
from typing import Set

# Explicit strong causal triggers
STRONG_CAUSAL_TRIGGERS: Set[str] = {
    "causes",
    "caused",
    "causing",
    "led to",
    "leads to",
    "leading to",
    "resulted in",
    "results in",
    "resulting in",
    "triggered",
    "triggers",
    "triggering",
    "due to",
    "because",
    "because of",
    "contributed to",
    "contributes to",
    "resulted from",
    "results from",
}

# Associative non-causal or weak correlation triggers
ASSOCIATIVE_TRIGGERS: Set[str] = {
    "associated with",
    "linked to",
    "correlated with",
    "related to",
    "connected to",
}


def normalize_text(text: str) -> str:
    """Normalize text string for exact matching baseline.

    Lowercases string, removes non-alphanumeric characters except spaces, and collapses whitespace.
    """
    if not text:
        return ""
    lowered = text.lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    normalized = re.sub(r"\s+", " ", cleaned).strip()
    return normalized


def check_exact_match(source_cause: str, source_effect: str, summary_cause: str, summary_effect: str) -> bool:
    """Check if normalized cause and effect text correspond exactly."""
    norm_sc = normalize_text(source_cause)
    norm_se = normalize_text(source_effect)
    norm_mc = normalize_text(summary_cause)
    norm_me = normalize_text(summary_effect)

    if not norm_sc or not norm_se or not norm_mc or not norm_me:
        return False

    return norm_sc == norm_mc and norm_se == norm_me


def compute_relation_compatibility(source_trigger: str, summary_trigger: str) -> float:
    """Compute relation trigger compatibility score.

    Explicit causal triggers map to high compatibility (1.0).
    Associative triggers do NOT map to strong causal relations (0.0 or 0.2).

    Args:
        source_trigger: Trigger phrase or relation name of source relation.
        summary_trigger: Trigger phrase or relation name of summary relation.

    Returns:
        Float compatibility score in range [0.0, 1.0].
    """
    st_norm = normalize_text(source_trigger)
    su_norm = normalize_text(summary_trigger)

    # Check for associative language
    is_source_assoc = any(assoc in st_norm for assoc in ASSOCIATIVE_TRIGGERS)
    is_summary_assoc = any(assoc in su_norm for assoc in ASSOCIATIVE_TRIGGERS)

    if is_source_assoc or is_summary_assoc:
        # Explicit directive: associative language is NOT equivalent to strong causal relation
        return 0.0

    # Default extracted relation label in schema is 'causes'
    is_source_causal = (st_norm in STRONG_CAUSAL_TRIGGERS) or ("cause" in st_norm) or ("led" in st_norm) or ("result" in st_norm) or ("trigger" in st_norm)
    is_summary_causal = (su_norm in STRONG_CAUSAL_TRIGGERS) or ("cause" in su_norm) or ("led" in su_norm) or ("result" in su_norm) or ("trigger" in su_norm)

    if is_source_causal and is_summary_causal:
        return 1.0
    elif is_source_causal or is_summary_causal:
        return 0.5
    else:
        return 0.2
