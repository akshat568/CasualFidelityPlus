"""Phase 8 Summary Causal Extraction and Semantic Alignment Module."""

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.matcher import CausalMatcher
from causalfidelity.alignment.normalizer import check_exact_match, compute_relation_compatibility, normalize_text
from causalfidelity.alignment.pipeline import AlignmentPipeline
from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.alignment.scorer import CausalScorer
from causalfidelity.alignment.summary_extractor import SummaryCausalExtractor
from causalfidelity.alignment.validator import AlignmentValidator

__all__ = [
    "SummaryCausalRelation",
    "CausalAlignment",
    "SummaryCausalExtractor",
    "normalize_text",
    "check_exact_match",
    "compute_relation_compatibility",
    "SemanticEmbedder",
    "CausalScorer",
    "CausalMatcher",
    "AlignmentValidator",
    "AlignmentPipeline",
]
