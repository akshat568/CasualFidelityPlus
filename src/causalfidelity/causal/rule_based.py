"""Rule-based causal relation extractor for explicit causal language."""

import re
from typing import List, Optional, Tuple

from causalfidelity.causal.extractor import CausalExtractor
from causalfidelity.causal.schema import CausalRelation
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class RuleBasedCausalExtractor(CausalExtractor):
    """Deterministic rule-based extractor for explicit causal constructions."""

    NEGATION_PATTERNS = [
        re.compile(r"\b(no|little|without)\s+evidence\b", re.IGNORECASE),
        re.compile(
            r"\b(did\s+not|does\s+not|do\s+not|will\s+not|would\s+not|could\s+not|cannot|has\s+not|have\s+not|had\s+not|was\s+not|were\s+not|is\s+not|are\s+not)\s+(cause|lead|result|trigger|contribute)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(not\s+caused\s+by|not\s+triggered\s+by|not\s+due\s+to|never\s+led\s+to|denied\s+that)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bwithout\s+(causing|leading|triggering|resulting)\b", re.IGNORECASE),
        re.compile(r"\bno\s+(link|connection|causal\s+relationship)\s+(between|to|with)\b", re.IGNORECASE),
    ]

    TEMPORAL_SINCE_PATTERN = re.compile(
        r"\bsince\s+(the\s+)?(january|february|march|april|may|june|july|august|september|october|november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday|19\d\d|20\d\d|last|early|late|mid|then|yesterday|today|the\s+start|the\s+beginning|the\s+launch|taking|becoming)\b",
        re.IGNORECASE,
    )

    def __init__(self, confidence_default: float = 0.90):
        self.confidence_default = confidence_default

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text into sentences handling standard English punctuation and abbreviations."""
        if not text or not text.strip():
            return []

        # Replace known abbreviations temporarily to prevent bad sentence breaks
        protected = text
        protected = re.sub(r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|e\.g|i\.e|U\.S|U\.K|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.", r"\1_DOT_", protected)
        protected = re.sub(r"\b([A-Z])\.", r"\1_DOT_", protected)

        raw_sentences = re.split(r"(?<=[.!?])\s+", protected)
        sentences = []
        for s in raw_sentences:
            cleaned = s.replace("_DOT_", ".").strip()
            if cleaned:
                sentences.append(cleaned)
        return sentences

    def is_negated(self, sentence: str) -> bool:
        """Check if a sentence contains active negation of causal relationships."""
        for pattern in self.NEGATION_PATTERNS:
            if pattern.search(sentence):
                return True
        return False

    def is_temporal_since(self, sentence: str) -> bool:
        """Check if 'since' in sentence is temporal rather than causal."""
        if "since" not in sentence.lower():
            return False
        return bool(self.TEMPORAL_SINCE_PATTERN.search(sentence))

    @staticmethod
    def _clean_phrase(phrase: str) -> str:
        """Clean extracted cause or effect text string."""
        if not phrase:
            return ""
        cleaned = phrase.strip()
        # Strip leading/trailing punctuation (including periods) and relative connectors
        cleaned = re.sub(r"^(which|that|and|also|subsequently|furthermore|consequently|so),?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^[,\s\-:\;\.]+|[,\s\-:\;\.]+$", "", cleaned)
        return cleaned.strip()

    def _extract_from_sentence(self, sentence: str, sentence_index: int, document_id: str) -> List[CausalRelation]:
        """Extract causal relations from a single sentence."""
        relations: List[CausalRelation] = []

        if not sentence or self.is_negated(sentence):
            return relations

        # Handle 'since' temporal false-positive check
        if "since" in sentence.lower() and self.is_temporal_since(sentence):
            # If the sentence only has temporal since and no other causal triggers, return empty
            other_triggers = ["caused", "causes", "causing", "led to", "leads to", "resulted in", "results in", "triggered", "due to", "because of"]
            if not any(t in sentence.lower() for t in other_triggers):
                return relations

        # Clause splitting for compound sentences (e.g. "rainfall caused flooding, which led to closures")
        clause_parts = re.split(r",\s*(?:which|and\s+this|and\s+that)\s+", sentence, flags=re.IGNORECASE)

        # Process clauses
        for part_idx, clause in enumerate(clause_parts):
            extracted = self._parse_single_clause(clause, sentence, sentence_index, document_id)
            for rel in extracted:
                # If this is a chained clause (part_idx > 0) and cause is empty or relative pronoun, chain from previous effect
                if part_idx > 0 and relations and (not rel.cause or rel.cause.lower() in ("which", "that", "it", "this")):
                    prev_effect = relations[-1].effect
                    rel.cause = prev_effect
                    rel.cause_start = sentence.find(prev_effect)
                    rel.cause_end = rel.cause_start + len(prev_effect) if rel.cause_start != -1 else None
                if rel.cause and rel.effect:
                    relations.append(rel)

        return relations

    def _parse_single_clause(self, clause: str, source_sentence: str, sentence_index: int, document_id: str) -> List[CausalRelation]:
        """Parse a single clause for forward, reverse, and subordinate causal patterns."""
        results: List[CausalRelation] = []

        # 1. Forward Active Patterns (CAUSE -> verb -> EFFECT)
        forward_patterns = [
            (r"^(?P<cause>.+?)\s+\b(caused|causes|causing)\b\s+(?P<effect>.+)$", "caused", self.confidence_default),
            (r"^(?P<cause>.+?)\s+\b(led\s+to|leads\s+to|leading\s+to)\b\s+(?P<effect>.+)$", "led to", self.confidence_default),
            (r"^(?P<cause>.+?)\s+\b(resulted\s+in|results\s+in|resulting\s+in)\b\s+(?P<effect>.+)$", "resulted in", self.confidence_default),
            (r"^(?P<cause>.+?)\s+\b(triggered|triggers|triggering)\b\s+(?P<effect>.+)$", "triggered", self.confidence_default),
            (r"^(?P<cause>.+?)\s+\b(contributed\s+to|contributes\s+to)\b\s+(?P<effect>.+)$", "contributed to", 0.85),
            # Leading verb for chained relative clauses (e.g. "led to road closures")
            (r"^\s*\b(led\s+to|leads\s+to|leading\s+to|caused|causes|causing|triggered|triggers|resulting\s+in|resulted\s+in)\b\s+(?P<effect>.+)$", "chained_lead", self.confidence_default),
        ]

        for pattern, pat_name, conf in forward_patterns:
            m = re.search(pattern, clause, re.IGNORECASE)
            if m:
                raw_cause = m.groupdict().get("cause", "")
                raw_effect = m.group("effect")
                cause = self._clean_phrase(raw_cause) if raw_cause else ""
                effect = self._clean_phrase(raw_effect)

                if effect and len(effect) >= 2:
                    c_start = source_sentence.find(cause) if cause else None
                    c_end = c_start + len(cause) if (c_start is not None and c_start != -1) else None
                    e_start = source_sentence.find(effect)
                    e_end = e_start + len(effect) if e_start != -1 else None

                    rel = CausalRelation(
                        relation_id="",  # Assigned globally by pipeline
                        document_id=document_id,
                        cause=cause,
                        relation="causes",
                        effect=effect,
                        confidence=conf,
                        source_sentence=source_sentence,
                        sentence_index=sentence_index,
                        extraction_method="rule_based",
                        cause_start=c_start if (c_start is not None and c_start != -1) else None,
                        cause_end=c_end,
                        effect_start=e_start if e_start != -1 else None,
                        effect_end=e_end,
                        pattern_matched=pat_name,
                    )
                    results.append(rel)
                    return results  # Matched primary pattern


        # 2. Reverse Passive / Source Patterns (EFFECT -> verb -> CAUSE)
        reverse_patterns = [
            (r"^(?P<effect>.+?)\s+\b(resulted\s+from|results\s+from)\b\s+(?P<cause>.+)$", "resulted from", self.confidence_default),
            (r"^(?P<effect>.+?)\s+\b(was\s+due\s+to|is\s+due\s+to|were\s+due\s+to|due\s+to)\b\s+(?P<cause>.+)$", "due to", self.confidence_default),
            (r"^(?P<effect>.+?)\s+\b(was\s+caused\s+by|is\s+caused\s+by|were\s+caused\s+by)\b\s+(?P<cause>.+)$", "caused by", self.confidence_default),
            (r"^(?P<effect>.+?)\s+\b(was\s+triggered\s+by|is\s+triggered\s+by)\b\s+(?P<cause>.+)$", "triggered by", self.confidence_default),
        ]

        for pattern, pat_name, conf in reverse_patterns:
            m = re.search(pattern, clause, re.IGNORECASE)
            if m:
                raw_cause = m.group("cause")
                raw_effect = m.group("effect")
                cause = self._clean_phrase(raw_cause)
                effect = self._clean_phrase(raw_effect)

                if cause and effect and len(cause) >= 2 and len(effect) >= 2:
                    c_start = source_sentence.find(cause)
                    c_end = c_start + len(cause) if c_start != -1 else None
                    e_start = source_sentence.find(effect)
                    e_end = e_start + len(effect) if e_start != -1 else None

                    rel = CausalRelation(
                        relation_id="",
                        document_id=document_id,
                        cause=cause,
                        relation="causes",
                        effect=effect,
                        confidence=conf,
                        source_sentence=source_sentence,
                        sentence_index=sentence_index,
                        extraction_method="rule_based",
                        cause_start=c_start if c_start != -1 else None,
                        cause_end=c_end,
                        effect_start=e_start if e_start != -1 else None,
                        effect_end=e_end,
                        pattern_matched=pat_name,
                    )
                    results.append(rel)
                    return results

        # 3. Subordinate / Conjunction Patterns ("EFFECT because of CAUSE" / "EFFECT because CAUSE")
        sub_patterns = [
            (r"^(?P<effect>.+?)\s+\b(because\s+of|owing\s+to)\b\s+(?P<cause>.+)$", "because of", self.confidence_default),
            (r"^(?P<effect>.+?)\s+\b(because)\b\s+(?P<cause>.+)$", "because", 0.85),
            (r"^\s*\b(because|owing\s+to)\b\s+(?P<cause>.+?),\s*(?P<effect>.+)$", "because_leading", 0.85),
        ]

        for pattern, pat_name, conf in sub_patterns:
            m = re.search(pattern, clause, re.IGNORECASE)
            if m:
                raw_cause = m.group("cause")
                raw_effect = m.group("effect")
                cause = self._clean_phrase(raw_cause)
                effect = self._clean_phrase(raw_effect)

                if cause and effect and len(cause) >= 2 and len(effect) >= 2:
                    c_start = source_sentence.find(cause)
                    c_end = c_start + len(cause) if c_start != -1 else None
                    e_start = source_sentence.find(effect)
                    e_end = e_start + len(effect) if e_start != -1 else None

                    rel = CausalRelation(
                        relation_id="",
                        document_id=document_id,
                        cause=cause,
                        relation="causes",
                        effect=effect,
                        confidence=conf,
                        source_sentence=source_sentence,
                        sentence_index=sentence_index,
                        extraction_method="rule_based",
                        cause_start=c_start if c_start != -1 else None,
                        cause_end=c_end,
                        effect_start=e_start if e_start != -1 else None,
                        effect_end=e_end,
                        pattern_matched=pat_name,
                    )
                    results.append(rel)
                    return results

        return results

    def extract_relations(self, document_id: str, text: str) -> List[CausalRelation]:
        """Extract structured causal relations from text across segmented sentences."""
        all_relations: List[CausalRelation] = []
        sentences = self.split_sentences(text)

        for sent_idx, sentence in enumerate(sentences):
            extracted = self._extract_from_sentence(sentence, sent_idx, document_id)
            all_relations.extend(extracted)

        return all_relations
