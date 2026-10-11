"""Canonical schema definitions for extracted causal relations."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CausalRelation:
    """Dataclass representing an extracted binary causal relation (cause -> causes -> effect)."""

    relation_id: str
    document_id: str
    cause: str
    relation: str = "causes"
    effect: str = ""
    confidence: float = 0.90
    source_sentence: str = ""
    sentence_index: int = 0
    extraction_method: str = "rule_based"
    cause_start: Optional[int] = None
    cause_end: Optional[int] = None
    effect_start: Optional[int] = None
    effect_end: Optional[int] = None
    pattern_matched: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize relation to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalRelation":
        """Deserialize relation from dictionary representation."""
        return cls(
            relation_id=data.get("relation_id", ""),
            document_id=data.get("document_id", ""),
            cause=data.get("cause", ""),
            relation=data.get("relation", "causes"),
            effect=data.get("effect", ""),
            confidence=float(data.get("confidence", 0.90)),
            source_sentence=data.get("source_sentence", ""),
            sentence_index=int(data.get("sentence_index", 0)),
            extraction_method=data.get("extraction_method", "rule_based"),
            cause_start=data.get("cause_start"),
            cause_end=data.get("cause_end"),
            effect_start=data.get("effect_start"),
            effect_end=data.get("effect_end"),
            pattern_matched=data.get("pattern_matched"),
        )


@dataclass
class DocumentCausalRelations:
    """Container for all extracted causal relations belonging to a document."""

    document_id: str
    relations: List[CausalRelation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize container to dictionary representation."""
        return {
            "document_id": self.document_id,
            "relations": [r.to_dict() for r in self.relations],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentCausalRelations":
        """Deserialize container from dictionary representation."""
        raw_rels = data.get("relations", [])
        rel_objs = [
            r if isinstance(r, CausalRelation) else CausalRelation.from_dict(r)
            for r in raw_rels
        ]
        return cls(
            document_id=data.get("document_id", ""),
            relations=rel_objs,
        )
