"""Canonical summary schema definitions for CausalFidelity+."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


def generate_summary_id(document_id: str, summary_type: str = "reference") -> str:
    """Generate a deterministic summary ID based on document_id and summary_type.

    Args:
        document_id: Canonical document identifier (e.g., 'xsum_000001').
        summary_type: Type of summary (e.g., 'reference', 'generated_model_A').

    Returns:
        Deterministic summary ID string.
    """
    if summary_type == "reference":
        return f"{document_id}_ref"
    return f"{document_id}_{summary_type}"


@dataclass
class SummaryRecord:
    """Canonical representation of a summary artifact for causal evaluation."""

    document_id: str
    summary_id: str
    summary_text: str
    summary_type: str = "reference"
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_word_count: int = 0
    summary_word_count: int = 0
    compression_ratio: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SummaryRecord":
        """Deserialize record from dictionary representation."""
        comp_ratio = data.get("compression_ratio")
        return cls(
            document_id=data.get("document_id", ""),
            summary_id=data.get("summary_id", ""),
            summary_text=data.get("summary_text", ""),
            summary_type=data.get("summary_type", "reference"),
            metadata=data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {},
            source_word_count=int(data.get("source_word_count", 0)),
            summary_word_count=int(data.get("summary_word_count", 0)),
            compression_ratio=float(comp_ratio) if comp_ratio is not None else None,
        )
