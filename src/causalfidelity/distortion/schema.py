"""Schema definitions for Phase 9 Causal Distortion Detection."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


class DistortionLabel:
    """Supported causal distortion classification categories."""

    PRESERVED = "PRESERVED"
    REVERSED = "REVERSED"
    WEAKENED = "WEAKENED"
    DROPPED = "DROPPED"
    CAUSE_CHANGED = "CAUSE_CHANGED"
    EFFECT_CHANGED = "EFFECT_CHANGED"
    DISTORTED = "DISTORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

    ALL_LABELS = [
        PRESERVED,
        REVERSED,
        WEAKENED,
        DROPPED,
        CAUSE_CHANGED,
        EFFECT_CHANGED,
        DISTORTED,
        INSUFFICIENT_EVIDENCE,
    ]

    DISTORTION_ONLY_LABELS = [
        PRESERVED,
        REVERSED,
        WEAKENED,
        DROPPED,
        CAUSE_CHANGED,
        EFFECT_CHANGED,
        DISTORTED,
    ]


class EvidenceStrength:
    """Categorical ratings for evidence strength."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class SummaryEvidenceRecord:
    """Sub-record representing gathered summary evidence."""

    summary_relation_id: Optional[str] = None
    cause: Optional[str] = None
    relation: Optional[str] = None
    effect: Optional[str] = None
    cause_similarity: Optional[float] = None
    effect_similarity: Optional[float] = None
    relation_compatibility: Optional[float] = None
    overall_alignment_score: Optional[float] = None
    alignment_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize summary evidence record."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SummaryEvidenceRecord":
        """Deserialize summary evidence record."""
        if not data:
            return cls()
        return cls(
            summary_relation_id=data.get("summary_relation_id"),
            cause=data.get("cause"),
            relation=data.get("relation"),
            effect=data.get("effect"),
            cause_similarity=data.get("cause_similarity"),
            effect_similarity=data.get("effect_similarity"),
            relation_compatibility=data.get("relation_compatibility"),
            overall_alignment_score=data.get("overall_alignment_score"),
            alignment_status=data.get("alignment_status"),
        )


@dataclass
class DistortionAnalysisRecord:
    """Dataclass representing a Phase 9 causal distortion analysis record."""

    analysis_id: str
    document_id: str
    summary_id: str
    source_relation_id: str
    source_relation: Dict[str, str]
    summary_evidence: SummaryEvidenceRecord
    detected_label: str = DistortionLabel.INSUFFICIENT_EVIDENCE
    evidence_strength: str = EvidenceStrength.INSUFFICIENT
    perturbation_id: Optional[str] = None
    intended_label: Optional[str] = None
    agreement: Optional[bool] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=lambda: {"analysis_method": "deterministic_rule_based", "phase": 9})

    def to_dict(self) -> Dict[str, Any]:
        """Serialize distortion record to dictionary representation preserving null values."""
        res = {
            "analysis_id": self.analysis_id,
            "document_id": self.document_id,
            "summary_id": self.summary_id,
            "perturbation_id": self.perturbation_id,
            "source_relation_id": self.source_relation_id,
            "source_relation": self.source_relation,
            "summary_evidence": self.summary_evidence.to_dict() if isinstance(self.summary_evidence, SummaryEvidenceRecord) else self.summary_evidence,
            "detected_label": self.detected_label,
            "evidence_strength": self.evidence_strength,
            "intended_label": self.intended_label,
            "agreement": self.agreement,
            "reason": self.reason,
            "metadata": self.metadata,
        }
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DistortionAnalysisRecord":
        """Deserialize distortion record from dictionary representation."""
        raw_evidence = data.get("summary_evidence")
        ev_obj = (
            SummaryEvidenceRecord.from_dict(raw_evidence)
            if isinstance(raw_evidence, dict)
            else SummaryEvidenceRecord()
        )
        return cls(
            analysis_id=data.get("analysis_id", ""),
            document_id=data.get("document_id", ""),
            summary_id=data.get("summary_id", ""),
            perturbation_id=data.get("perturbation_id"),
            source_relation_id=data.get("source_relation_id", ""),
            source_relation=data.get("source_relation", {}),
            summary_evidence=ev_obj,
            detected_label=data.get("detected_label", DistortionLabel.INSUFFICIENT_EVIDENCE),
            evidence_strength=data.get("evidence_strength", EvidenceStrength.INSUFFICIENT),
            intended_label=data.get("intended_label"),
            agreement=data.get("agreement"),
            reason=data.get("reason", ""),
            metadata=dict(data.get("metadata", {})),
        )
