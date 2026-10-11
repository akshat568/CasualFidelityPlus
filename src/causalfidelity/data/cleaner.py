"""Conservative text cleaning utilities for dataset preprocessing."""

import re
import unicodedata
from typing import Any, Dict


class TextCleaner:
    """Conservative text cleaning helper for document and summary texts."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Apply conservative cleaning to text without modifying semantic content.

        Performs:
        - Unicode normalization (NFC)
        - CRLF newline normalization
        - Removal of unprintable control characters (excluding standard whitespace)
        - Trimming leading and trailing whitespace
        """
        if not text or not isinstance(text, str):
            return ""

        # Normalize Unicode characters (NFC form)
        normalized = unicodedata.normalize("NFC", text)

        # Normalize line endings
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Strip non-printable control characters except tab and newline
        cleaned_chars = [
            ch for ch in normalized
            if ch in ("\n", "\t") or not unicodedata.category(ch).startswith("C")
        ]
        cleaned = "".join(cleaned_chars)

        # Collapse multiple inline spaces/tabs (preserve newlines)
        lines = cleaned.split("\n")
        cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
        
        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0
        for line in cleaned_lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        return "\n".join(result_lines).strip()

    @classmethod
    def clean_raw_record(cls, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean source_text and reference_summary in a raw record dictionary."""
        cleaned_record = dict(raw_record)
        cleaned_record["source_text"] = cls.clean_text(raw_record.get("source_text", ""))
        cleaned_record["reference_summary"] = cls.clean_text(raw_record.get("reference_summary", ""))
        return cleaned_record
