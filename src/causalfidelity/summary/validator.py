"""Validation component for summary input records."""

from typing import Optional, Set, Tuple

from causalfidelity.summary.schema import SummaryRecord, generate_summary_id


class SummaryValidator:
    """Validates SummaryRecord instances according to Phase 5 canonical constraints."""

    def __init__(self, expected_summary_type: str = "reference"):
        self.expected_summary_type = expected_summary_type
        self.seen_document_ids: Set[str] = set()
        self.seen_summary_ids: Set[str] = set()

    def reset(self) -> None:
        """Reset internal duplicate tracking state."""
        self.seen_document_ids.clear()
        self.seen_summary_ids.clear()

    def validate_record(self, record: SummaryRecord) -> Tuple[bool, Optional[str]]:
        """Validate a SummaryRecord instance.

        Args:
            record: SummaryRecord to validate.

        Returns:
            Tuple of (is_valid: bool, rejection_reason: Optional[str]).
        """
        if not isinstance(record.document_id, str) or not record.document_id.strip():
            return False, "missing_document_id"

        if not isinstance(record.summary_text, str) or not record.summary_text.strip():
            return False, "empty_summary_text"

        if not isinstance(record.summary_id, str) or not record.summary_id.strip():
            return False, "missing_summary_id"

        expected_id = generate_summary_id(record.document_id, record.summary_type)
        if record.summary_id != expected_id:
            return False, f"non_deterministic_summary_id: got '{record.summary_id}', expected '{expected_id}'"

        if not isinstance(record.summary_type, str) or not record.summary_type.strip():
            return False, "missing_summary_type"

        if record.summary_type != self.expected_summary_type:
            return False, f"invalid_summary_type: got '{record.summary_type}', expected '{self.expected_summary_type}'"

        if record.document_id in self.seen_document_ids:
            return False, f"duplicate_document_id: '{record.document_id}'"

        if record.summary_id in self.seen_summary_ids:
            return False, f"duplicate_summary_id: '{record.summary_id}'"

        return True, None

    def register(self, record: SummaryRecord) -> None:
        """Register valid record identifiers into duplicate tracking state."""
        self.seen_document_ids.add(record.document_id)
        self.seen_summary_ids.add(record.summary_id)
