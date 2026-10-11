"""Schema definitions for Phase 8 summary causal relations and causal alignments."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SummaryCausalRelation:
    """Dataclass representing an explicit binary causal relation extracted from summary text."""

    summary_relation_id: str
    document_id: str
    summary_id: str
    cause: str
    relation: str = "causes"
    effect: str = ""
    confidence: float = 0.90
    source_sentence: str = ""
    sentence_index: int = 0
    extraction_method: str = "rule_based"
    text_type: str = "summary"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize summary relation to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SummaryCausalRelation":
        """Deserialize summary relation from dictionary representation."""
        return cls(
            summary_relation_id=data.get("summary_relation_id", ""),
            document_id=data.get("document_id", ""),
            summary_id=data.get("summary_id", ""),
            cause=data.get("cause", ""),
            relation=data.get("relation", "causes"),
            effect=data.get("effect", ""),
            confidence=float(data.get("confidence", 0.90)),
            source_sentence=data.get("source_sentence", ""),
            sentence_index=int(data.get("sentence_index", 0)),
            extraction_method=data.get("extraction_method", "rule_based"),
            text_type=data.get("text_type", "summary"),
        )


@dataclass
class CausalAlignment:
    """Dataclass representing candidate alignment between a source causal relation and summary relation."""

    alignment_id: str
    document_id: str
    source_relation_id: str
    summary_id: Optional[str]
    summary_relation_id: Optional[str]
    source_relation: Dict[str, str]
    summary_relation: Optional[Dict[str, str]]
    cause_similarity: float
    effect_similarity: float
    relation_compatibility: float
    overall_alignment_score: float
    candidate_rank: Optional[int]
    alignment_status: str  # aligned, ambiguous, below_threshold, no_candidate
    exact_match: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize causal alignment to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalAlignment":
        """Deserialize causal alignment from dictionary representation."""
        return cls(
            alignment_id=data.get("alignment_id", ""),
            document_id=data.get("document_id", ""),
            source_relation_id=data.get("source_relation_id", ""),
            summary_id=data.get("summary_id"),
            summary_relation_id=data.get("summary_relation_id"),
            source_relation=data.get("source_relation", {}),
            summary_relation=data.get("summary_relation"),
            cause_similarity=float(data.get("cause_similarity", 0.0)),
            effect_similarity=float(data.get("effect_similarity", 0.0)),
            relation_compatibility=float(data.get("relation_compatibility", 0.0)),
            overall_alignment_score=float(data.get("overall_alignment_score", 0.0)),
            candidate_rank=data.get("candidate_rank"),
            alignment_status=data.get("alignment_status", "no_candidate"),
            exact_match=bool(data.get("exact_match", False)),
            metadata=dict(data.get("metadata", {})),
        )
