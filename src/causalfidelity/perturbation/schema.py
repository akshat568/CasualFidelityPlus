"""Canonical schema definition for controlled causal perturbations."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


def generate_perturbation_id(document_id: str, counter: int) -> str:
    """Generate a deterministic perturbation ID string.

    Args:
        document_id: Canonical document identifier (e.g., 'xsum_000001').
        counter: Sequential integer counter for perturbations within document.

    Returns:
        Deterministic perturbation ID string (e.g., 'xsum_000001_pert_000001').
    """
    return f"{document_id}_pert_{counter:06d}"


@dataclass
class PerturbationRecord:
    """Canonical representation of a controlled causal perturbation record."""

    perturbation_id: str
    document_id: str
    summary_id: str
    perturbation_type: str
    original_text: str
    perturbed_text: str
    original_relation: Dict[str, Any] = field(default_factory=dict)
    intended_relation: Dict[str, Any] = field(default_factory=dict)
    changed_span: Dict[str, str] = field(default_factory=dict)
    generation_method: str = "rule_based"
    validation_status: str = "pending"
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerturbationRecord":
        """Deserialize record from dictionary representation."""
        return cls(
            perturbation_id=data.get("perturbation_id", ""),
            document_id=data.get("document_id", ""),
            summary_id=data.get("summary_id", ""),
            perturbation_type=data.get("perturbation_type", ""),
            original_text=data.get("original_text", ""),
            perturbed_text=data.get("perturbed_text", ""),
            original_relation=data.get("original_relation", {}),
            intended_relation=data.get("intended_relation", {}),
            changed_span=data.get("changed_span", {}),
            generation_method=data.get("generation_method", "rule_based"),
            validation_status=data.get("validation_status", "pending"),
            validation_errors=data.get("validation_errors", []),
            metadata=data.get("metadata", {}),
        )
