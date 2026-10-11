"""Canonical schema definition for perturbation validation records."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ValidationRecord:
    """Canonical representation of a Phase 7 perturbation validation result."""

    perturbation_id: str
    document_id: str
    summary_id: str
    perturbation_type: str
    validation_status: str = "valid"
    checks: Dict[str, str] = field(
        default_factory=lambda: {
            "structural": "passed",
            "target_transformation": "passed",
            "content_preservation": "passed",
            "consistency": "passed",
        }
    )
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize validation record to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationRecord":
        """Deserialize validation record from dictionary representation."""
        default_checks = {
            "structural": "passed",
            "target_transformation": "passed",
            "content_preservation": "passed",
            "consistency": "passed",
        }
        raw_checks = data.get("checks", {})
        checks_dict = default_checks.copy()
        if isinstance(raw_checks, dict):
            checks_dict.update(raw_checks)

        return cls(
            perturbation_id=data.get("perturbation_id", ""),
            document_id=data.get("document_id", ""),
            summary_id=data.get("summary_id", ""),
            perturbation_type=data.get("perturbation_type", ""),
            validation_status=data.get("validation_status", "valid"),
            checks=checks_dict,
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )
