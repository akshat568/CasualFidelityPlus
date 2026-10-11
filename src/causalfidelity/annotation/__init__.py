"""Phase 12 Human Validation & Statistical Analysis package - Annotation module."""

from causalfidelity.annotation.agreement import (
    AgreementResult,
    InterAnnotatorAgreementEvaluator,
)
from causalfidelity.annotation.config import Phase12Config
from causalfidelity.annotation.correlation import (
    CorrelationResult,
    StatisticalCorrelationEvaluator,
    compute_pearson_r,
    compute_roc_auc,
    compute_spearman_rho,
)
from causalfidelity.annotation.loader import AnnotationLoader, IngestionResult
from causalfidelity.annotation.pipeline import Phase12HumanValidationPipeline
from causalfidelity.annotation.schema import (
    APPROVED_CAUSAL_LABELS,
    AnnotationRecord,
    validate_annotation_dict,
)

__all__ = [
    "APPROVED_CAUSAL_LABELS",
    "AnnotationRecord",
    "validate_annotation_dict",
    "AnnotationLoader",
    "IngestionResult",
    "InterAnnotatorAgreementEvaluator",
    "AgreementResult",
    "StatisticalCorrelationEvaluator",
    "CorrelationResult",
    "compute_pearson_r",
    "compute_spearman_rho",
    "compute_roc_auc",
    "Phase12Config",
    "Phase12HumanValidationPipeline",
]
