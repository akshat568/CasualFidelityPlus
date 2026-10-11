"""Scorer for independent cause/effect semantic alignment and overall compatibility."""

from typing import Any, Dict, Tuple
import numpy as np

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.normalizer import compute_relation_compatibility
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class CausalScorer:
    """Calculates cause similarity, effect similarity, relation compatibility, and overall score."""

    def __init__(
        self,
        cause_weight: float = 0.45,
        effect_weight: float = 0.45,
        relation_weight: float = 0.10,
    ):
        self.cause_weight = cause_weight
        self.effect_weight = effect_weight
        self.relation_weight = relation_weight
        self._total_weight = cause_weight + effect_weight + relation_weight

    def score_candidate(
        self,
        source_cause_vec: np.ndarray,
        source_effect_vec: np.ndarray,
        summary_cause_vec: np.ndarray,
        summary_effect_vec: np.ndarray,
        source_relation_trigger: str = "causes",
        summary_relation_trigger: str = "causes",
    ) -> Tuple[float, float, float, float]:
        """Score candidate pair preserving directional argument identity (cause->effect).

        Args:
            source_cause_vec: Vector for source cause.
            source_effect_vec: Vector for source effect.
            summary_cause_vec: Vector for summary cause.
            summary_effect_vec: Vector for summary effect.
            source_relation_trigger: Trigger text for source relation.
            summary_relation_trigger: Trigger text for summary relation.

        Returns:
            Tuple of (cause_similarity, effect_similarity, relation_compatibility, overall_score).
        """
        # Calculate cause similarity independently
        cause_sim = SemanticEmbedder.cosine_similarity(source_cause_vec, summary_cause_vec)
        
        # Calculate effect similarity independently
        effect_sim = SemanticEmbedder.cosine_similarity(source_effect_vec, summary_effect_vec)

        # Calculate relation compatibility
        rel_compat = compute_relation_compatibility(source_relation_trigger, summary_relation_trigger)

        # Compute overall weighted alignment score
        if self._total_weight > 0:
            weighted_sum = (
                self.cause_weight * cause_sim
                + self.effect_weight * effect_sim
                + self.relation_weight * rel_compat
            )
            overall_score = weighted_sum / self._total_weight
        else:
            overall_score = 0.0

        # Clip scores to [0.0, 1.0] for safety
        cause_sim = max(0.0, cause_sim)
        effect_sim = max(0.0, effect_sim)
        overall_score = max(0.0, min(1.0, overall_score))

        return cause_sim, effect_sim, rel_compat, overall_score

    def get_weights_metadata(self) -> Dict[str, float]:
        """Return configuration metadata of scoring weights."""
        return {
            "cause_weight": self.cause_weight,
            "effect_weight": self.effect_weight,
            "relation_weight": self.relation_weight,
        }
