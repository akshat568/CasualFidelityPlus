"""Lightweight candidate causal-language filter for document prescreening.

IMPORTANT RESEARCH BOUNDARY NOTE:
This module only performs prescreening to identify documents containing explicit causal signal terms.
It does NOT extract causal relations, verify causal semantics, or generate causal graphs (which are deferred to Phase 3 and Phase 4).
"""

import re
from typing import List, Optional, Set


class CausalCandidateFilter:
    """Filter to identify documents containing candidate causal language phrases."""

    DEFAULT_PHRASES = [
        "caused",
        "causes",
        "causing",
        "led to",
        "resulted in",
        "due to",
        "because",
        "therefore",
        "as a result",
        "resulted from",
        "contributed to",
        "triggered",
        "owing to",
        "since",
    ]

    def __init__(self, phrases: Optional[List[str]] = None, enabled: bool = True):
        self.enabled = enabled
        self.phrases: List[str] = phrases if phrases is not None else self.DEFAULT_PHRASES
        self._regex_pattern = self._build_regex_pattern(self.phrases)

    @staticmethod
    def _build_regex_pattern(phrases: List[str]) -> Optional[re.Pattern]:
        if not phrases:
            return None
        # Escape phrases and wrap each in word boundaries \b
        escaped_phrases = [re.escape(phrase.strip()) for phrase in phrases if phrase.strip()]
        if not escaped_phrases:
            return None
        pattern_str = r"\b(" + "|".join(escaped_phrases) + r")\b"
        return re.compile(pattern_str, re.IGNORECASE)

    def is_causal_candidate(self, source_text: str) -> bool:
        """Check if source text contains any candidate causal language signals.

        Args:
            source_text: Cleaned document text to inspect.

        Returns:
            True if candidate causal language is detected or if filter disabled; False otherwise.
        """
        if not self.enabled or self._regex_pattern is None:
            return True

        if not source_text:
            return False

        return bool(self._regex_pattern.search(source_text))

    def matched_phrases(self, source_text: str) -> Set[str]:
        """Return the set of causal signal phrases detected in the source text."""
        if not source_text or self._regex_pattern is None:
            return set()

        matches = self._regex_pattern.findall(source_text)
        return {m.lower() for m in matches}
