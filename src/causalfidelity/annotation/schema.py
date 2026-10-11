"""Annotation schema definition for Phase 12 Human Validation."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

APPROVED_CAUSAL_LABELS = {
    "Faithful",
    "Reversed",
    "Weakened",
    "Dropped",
    "Cause_Changed",
    "Effect_Changed",
}


def validate_annotation_dict(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a dictionary of annotation fields against Phase 12 schema rules.

    Args:
        data: Dictionary containing annotation record fields.

    Returns:
        Tuple of (is_valid: bool, errors: List[str]).
    """
    errors: List[str] = []

    # Check annotation_id
    ann_id = data.get("annotation_id")
    if ann_id is None or not isinstance(ann_id, str) or not ann_id.strip():
        errors.append("missing_annotation_id")

    # Check perturbation_id
    pert_id = data.get("perturbation_id")
    if pert_id is None or not isinstance(pert_id, str) or not pert_id.strip():
        errors.append("missing_perturbation_id")

    # Check annotator_id
    ann_user = data.get("annotator_id")
    if ann_user is None or not isinstance(ann_user, str) or not ann_user.strip():
        errors.append("missing_annotator_id")

    # Check causal_label
    label = data.get("causal_label")
    if label is None or not isinstance(label, str) or not label.strip():
        errors.append("missing_causal_label")
    elif label not in APPROVED_CAUSAL_LABELS:
        errors.append(f"invalid_causal_label: '{label}'")

    # Check naturalness_rating
    rating = data.get("naturalness_rating")
    if rating is None or (isinstance(rating, str) and not rating.strip()):
        errors.append("missing_naturalness_rating")
    elif isinstance(rating, bool):
        errors.append("non_integer_naturalness_rating")
    elif isinstance(rating, float):
        errors.append("non_integer_naturalness_rating")
    elif isinstance(rating, int):
        if rating < 1:
            errors.append("naturalness_rating_below_min")
        elif rating > 5:
            errors.append("naturalness_rating_above_max")
    elif isinstance(rating, str):
        # Attempt integer conversion for string inputs (e.g. from CSV)
        try:
            val = float(rating)
            if not val.is_integer():
                errors.append("non_integer_naturalness_rating")
            else:
                ival = int(val)
                if ival < 1:
                    errors.append("naturalness_rating_below_min")
                elif ival > 5:
                    errors.append("naturalness_rating_above_max")
        except ValueError:
            errors.append("non_integer_naturalness_rating")
    else:
        errors.append("non_integer_naturalness_rating")

    is_valid = len(errors) == 0
    return is_valid, errors


@dataclass
class AnnotationRecord:
    """Canonical representation of a human annotation record for Phase 12."""

    annotation_id: str
    perturbation_id: str
    annotator_id: str
    causal_label: str
    naturalness_rating: int
    comments: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.naturalness_rating, str):
            try:
                self.naturalness_rating = int(float(self.naturalness_rating))
            except ValueError:
                pass

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate instance fields against Phase 12 schema rules."""
        return validate_annotation_dict(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnnotationRecord":
        """Construct AnnotationRecord from dictionary representation."""
        raw_rating = data.get("naturalness_rating", 0)
        parsed_rating = raw_rating
        if isinstance(raw_rating, str):
            try:
                parsed_rating = int(float(raw_rating))
            except ValueError:
                parsed_rating = raw_rating

        return cls(
            annotation_id=str(data.get("annotation_id", "")).strip(),
            perturbation_id=str(data.get("perturbation_id", "")).strip(),
            annotator_id=str(data.get("annotator_id", "")).strip(),
            causal_label=str(data.get("causal_label", "")).strip(),
            naturalness_rating=parsed_rating,
            comments=data.get("comments"),
            metadata=data.get("metadata", {}),
        )
