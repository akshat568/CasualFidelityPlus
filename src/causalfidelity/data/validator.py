"""Validation and duplicate detection for dataset records."""

import hashlib
from typing import Dict, Optional, Set, Tuple

from causalfidelity.data.schema import CanonicalRecord


class RecordValidator:
    """Validates records according to canonical schema constraints."""

    def __init__(self, expected_domain: str = "news", expected_dataset: str = "xsum", expected_language: str = "en"):
        self.expected_domain = expected_domain
        self.expected_dataset = expected_dataset
        self.expected_language = expected_language

    def validate_record(self, record: CanonicalRecord) -> Tuple[bool, Optional[str]]:
        """Validate a CanonicalRecord instance.

        Returns:
            Tuple of (is_valid: bool, rejection_reason: Optional[str])
        """
        if not record.source_text or not record.source_text.strip():
            return False, "Empty source_text"

        if not record.reference_summary or not record.reference_summary.strip():
            return False, "Empty reference_summary"

        if record.domain != self.expected_domain:
            return False, f"Invalid domain '{record.domain}' (expected '{self.expected_domain}')"

        if not record.metadata:
            return False, "Missing metadata"

        if record.metadata.dataset != self.expected_dataset:
            return False, f"Invalid dataset '{record.metadata.dataset}' (expected '{self.expected_dataset}')"

        if record.metadata.language != self.expected_language:
            return False, f"Invalid language '{record.metadata.language}' (expected '{self.expected_language}')"

        if not record.metadata.original_id:
            return False, "Missing original_id in metadata"

        return True, None


class DuplicateTracker:
    """Tracks seen record identifiers and content hashes for duplicate detection."""

    def __init__(self):
        self.seen_original_ids: Set[str] = set()
        self.seen_content_hashes: Set[str] = set()

    @staticmethod
    def compute_content_hash(source_text: str, reference_summary: str) -> str:
        """Compute SHA256 content hash of normalized source text and reference summary."""
        content = f"{source_text.strip().lower()}|||{reference_summary.strip().lower()}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_duplicate(self, original_id: str, source_text: str, reference_summary: str) -> Tuple[bool, Optional[str]]:
        """Check if a record is a duplicate by original ID or content hash.

        Returns:
            Tuple of (is_dup: bool, duplicate_type: Optional[str])
        """
        if original_id in self.seen_original_ids:
            return True, "duplicate_original_id"

        content_hash = self.compute_content_hash(source_text, reference_summary)
        if content_hash in self.seen_content_hashes:
            return True, "duplicate_content"

        return False, None

    def register(self, original_id: str, source_text: str, reference_summary: str) -> None:
        """Register a unique record in the duplicate tracker."""
        self.seen_original_ids.add(original_id)
        content_hash = self.compute_content_hash(source_text, reference_summary)
        self.seen_content_hashes.add(content_hash)
