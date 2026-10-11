"""Validator for Phase 8 summary relations and alignment outputs."""

from typing import List

from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)

VALID_ALIGNMENT_STATUSES = {"aligned", "ambiguous", "below_threshold", "no_candidate"}


class AlignmentValidator:
    """Validation checks for summary relations and alignment schemas."""

    @staticmethod
    def validate_summary_relation(rel: SummaryCausalRelation) -> bool:
        """Validate a SummaryCausalRelation record."""
        if not rel.summary_relation_id:
            raise ValueError("SummaryCausalRelation missing required summary_relation_id")
        if not rel.document_id:
            raise ValueError("SummaryCausalRelation missing required document_id")
        if not rel.summary_id:
            raise ValueError("SummaryCausalRelation missing required summary_id")
        if rel.text_type != "summary":
            raise ValueError(f"SummaryCausalRelation text_type must be 'summary', got '{rel.text_type}'")
        return True

    @staticmethod
    def validate_alignment(alignment: CausalAlignment) -> bool:
        """Validate a CausalAlignment record."""
        if not alignment.alignment_id:
            raise ValueError("CausalAlignment missing required alignment_id")
        if not alignment.document_id:
            raise ValueError("CausalAlignment missing required document_id")
        if not alignment.source_relation_id:
            raise ValueError("CausalAlignment missing required source_relation_id")
        if alignment.alignment_status not in VALID_ALIGNMENT_STATUSES:
            raise ValueError(
                f"Invalid alignment_status '{alignment.alignment_status}'. Expected one of {VALID_ALIGNMENT_STATUSES}"
            )

        for score_name in ["cause_similarity", "effect_similarity", "relation_compatibility", "overall_alignment_score"]:
            score_val = getattr(alignment, score_name)
            if score_val < 0.0 or score_val > 1.0:
                raise ValueError(f"Score '{score_name}' out of bounds [0, 1]: {score_val}")

        return True

    def validate_all_summary_relations(self, summary_rels: List[SummaryCausalRelation]) -> bool:
        """Validate a list of SummaryCausalRelation objects."""
        for rel in summary_rels:
            self.validate_summary_relation(rel)
        return True

    def validate_all_alignments(self, alignments: List[CausalAlignment]) -> bool:
        """Validate a list of CausalAlignment objects."""
        for align in alignments:
            self.validate_alignment(align)
        return True
