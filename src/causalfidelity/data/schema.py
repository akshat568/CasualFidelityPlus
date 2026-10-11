"""Canonical dataset schema definition for CausalFidelity+."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass
class RecordMetadata:
    """Metadata container for dataset records."""
    dataset: str = "xsum"
    original_id: str = ""
    split: str = "train"
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordMetadata":
        return cls(
            dataset=data.get("dataset", "xsum"),
            original_id=data.get("original_id", ""),
            split=data.get("split", "train"),
            language=data.get("language", "en"),
        )


@dataclass
class CanonicalRecord:
    """Canonical internal schema representation for source text and reference summary pairs."""
    document_id: str
    domain: str = "news"
    source_text: str = ""
    reference_summary: str = ""
    causal_candidate: bool = False
    metadata: RecordMetadata = field(default_factory=RecordMetadata)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if isinstance(self.metadata, RecordMetadata):
            data["metadata"] = self.metadata.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalRecord":
        meta_data = data.get("metadata", {})
        metadata_obj = RecordMetadata.from_dict(meta_data) if isinstance(meta_data, dict) else meta_data
        return cls(
            document_id=data.get("document_id", ""),
            domain=data.get("domain", "news"),
            source_text=data.get("source_text", ""),
            reference_summary=data.get("reference_summary", ""),
            causal_candidate=data.get("causal_candidate", False),
            metadata=metadata_obj,
        )
