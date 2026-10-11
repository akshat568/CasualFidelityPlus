"""Summary causal relation extractor reusing Phase 3 extraction architecture."""

from typing import Any, Dict, List

from causalfidelity.alignment.schema import SummaryCausalRelation
from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class SummaryCausalExtractor:
    """Extractor that applies rule-based causal relation extraction to summary texts."""

    def __init__(self, confidence_default: float = 0.90):
        self.extractor = RuleBasedCausalExtractor(confidence_default=confidence_default)

    def extract_from_summary(self, summary_record: Dict[str, Any]) -> List[SummaryCausalRelation]:
        """Extract explicit causal relations from a summary input record.

        Args:
            summary_record: Dictionary containing document_id, summary_id, summary_text, etc.

        Returns:
            List of SummaryCausalRelation objects with deterministic IDs.
        """
        document_id = summary_record.get("document_id", "")
        summary_id = summary_record.get("summary_id", f"{document_id}_summary")
        summary_text = summary_record.get("summary_text", "")

        if not summary_text or not summary_text.strip():
            return []

        extracted_rels = self.extractor.extract_relations(document_id, summary_text)
        summary_relations: List[SummaryCausalRelation] = []

        for idx, rel in enumerate(extracted_rels):
            # Deterministic summary relation ID
            sum_rel_id = f"{summary_id}_rel_{idx + 1:03d}"
            
            sum_rel = SummaryCausalRelation(
                summary_relation_id=sum_rel_id,
                document_id=document_id,
                summary_id=summary_id,
                cause=rel.cause,
                relation=rel.relation,
                effect=rel.effect,
                confidence=rel.confidence,
                source_sentence=rel.source_sentence,
                sentence_index=rel.sentence_index,
                extraction_method=rel.extraction_method,
                text_type="summary",
            )
            summary_relations.append(sum_rel)

        return summary_relations
