"""Independent, rule-based classifier for Causal Distortion Detection."""

from typing import Any, Dict, Optional, Tuple

from causalfidelity.config import CausalDistortionConfig
from causalfidelity.distortion.evidence import EvidenceBundle
from causalfidelity.distortion.schema import (
    DistortionAnalysisRecord,
    DistortionLabel,
    EvidenceStrength,
    SummaryEvidenceRecord,
)
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class DistortionClassifier:
    """Rule-based classifier enforcing evidence hierarchy for causal distortion detection."""

    def __init__(self, config: Optional[CausalDistortionConfig] = None):
        self.config = config or CausalDistortionConfig()

    def classify(self, bundle: EvidenceBundle) -> DistortionAnalysisRecord:
        """Classify causal relationship between source relation and summary evidence.

        Args:
            bundle: EvidenceBundle containing collected evidence metrics.

        Returns:
            DistortionAnalysisRecord containing detected_label, evidence_strength, reason, etc.
        """
        src_rel_dict = {
            "cause": bundle.source_cause,
            "relation": bundle.source_relation,
            "effect": bundle.source_effect,
        }

        sum_ev_record = SummaryEvidenceRecord(
            summary_relation_id=bundle.summary_relation_id,
            cause=bundle.summary_cause,
            relation=bundle.summary_relation,
            effect=bundle.summary_effect,
            cause_similarity=bundle.cause_sim if bundle.cause_sim > 0 else None,
            effect_similarity=bundle.effect_sim if bundle.effect_sim > 0 else None,
            relation_compatibility=bundle.relation_compat if bundle.summary_relation else None,
            overall_alignment_score=bundle.overall_score if bundle.overall_score > 0 else None,
            alignment_status=bundle.alignment_status if bundle.alignment_status != "no_candidate" else None,
        )

        detected_label, strength, reason = self._apply_decision_tree(bundle)

        intended_label = bundle.intended_label
        agreement = (detected_label == intended_label) if intended_label else None

        # Build deterministic analysis_id
        if bundle.perturbation_id:
            analysis_id = f"dist_pert_{bundle.perturbation_id}"
        else:
            analysis_id = f"dist_{bundle.source_relation_id}_{bundle.summary_id}"

        record = DistortionAnalysisRecord(
            analysis_id=analysis_id,
            document_id=bundle.summary_id.split("_ref")[0] if "_ref" in bundle.summary_id else bundle.summary_id,
            summary_id=bundle.summary_id,
            perturbation_id=bundle.perturbation_id,
            source_relation_id=bundle.source_relation_id,
            source_relation=src_rel_dict,
            summary_evidence=sum_ev_record,
            detected_label=detected_label,
            evidence_strength=strength,
            intended_label=intended_label,
            agreement=agreement,
            reason=reason,
            metadata={
                "analysis_method": "deterministic_rule_based",
                "phase": 9,
                "cause_threshold": self.config.cause_threshold,
                "effect_threshold": self.config.effect_threshold,
                "overall_threshold": self.config.overall_threshold,
            },
        )

        return record

    def _apply_decision_tree(self, bundle: EvidenceBundle) -> Tuple[str, str, str]:
        """Apply deterministic evidence hierarchy decision tree."""

        # 1. REVERSED Check:
        # Requires explicit evidence of directional swap (cause->effect and effect->cause)
        if (
            bundle.reverse_cause_sim >= self.config.cause_threshold
            and bundle.reverse_effect_sim >= self.config.effect_threshold
            and bundle.has_explicit_summary_relation
        ):
            return (
                DistortionLabel.REVERSED,
                EvidenceStrength.HIGH if (bundle.reverse_cause_sim >= 0.7 and bundle.reverse_effect_sim >= 0.7) else EvidenceStrength.MEDIUM,
                "explicit reversal of cause and effect in summary causal relation",
            )

        # 2. PRESERVED Check:
        # Requires source cause & effect alignment + explicit compatible strong causal relation in summary
        if (
            bundle.cause_sim >= self.config.cause_threshold
            and bundle.effect_sim >= self.config.effect_threshold
            and bundle.has_explicit_summary_relation
            and bundle.relation_compat >= 0.8
            and not bundle.has_weakened_language
        ):
            strength = EvidenceStrength.HIGH if bundle.overall_score >= 0.7 else EvidenceStrength.MEDIUM
            return (
                DistortionLabel.PRESERVED,
                strength,
                "aligned cause and effect arguments with explicit compatible causal relation",
            )

        # 3. WEAKENED Check:
        # Cause & effect align, but relation trigger is associative or weakened (e.g., 'associated with', 'linked to')
        if (
            (bundle.cause_sim >= self.config.cause_threshold or bundle.cause_present_in_summary)
            and (bundle.effect_sim >= self.config.effect_threshold or bundle.effect_present_in_summary)
            and bundle.has_weakened_language
        ):
            return (
                DistortionLabel.WEAKENED,
                EvidenceStrength.HIGH if bundle.has_explicit_summary_relation else EvidenceStrength.MEDIUM,
                "cause and effect aligned but summary relation weakened from explicit causation to associative language",
            )

        # 4. CAUSE_CHANGED Check:
        # Effect aligns with summary effect, but summary cause differs and is associated with the effect in an explicit relation
        if (
            bundle.effect_sim >= self.config.effect_threshold
            and bundle.cause_sim < self.config.cause_threshold
            and bundle.has_explicit_summary_relation
            and bundle.summary_cause
            and bundle.summary_cause != bundle.source_cause
        ):
            return (
                DistortionLabel.CAUSE_CHANGED,
                EvidenceStrength.HIGH if bundle.effect_sim >= 0.7 else EvidenceStrength.MEDIUM,
                "effect aligned but summary explicitly associates a different cause",
            )

        # 5. EFFECT_CHANGED Check:
        # Cause aligns with summary cause, but summary effect differs and is associated with the cause in an explicit relation
        if (
            bundle.cause_sim >= self.config.cause_threshold
            and bundle.effect_sim < self.config.effect_threshold
            and bundle.has_explicit_summary_relation
            and bundle.summary_effect
            and bundle.summary_effect != bundle.source_effect
        ):
            return (
                DistortionLabel.EFFECT_CHANGED,
                EvidenceStrength.HIGH if bundle.cause_sim >= 0.7 else EvidenceStrength.MEDIUM,
                "cause aligned but summary explicitly associates a different effect",
            )

        # 6. DROPPED Check:
        # Cause and effect arguments are represented/present in summary, but causal relationship itself is absent (no explicit summary relation)
        if (
            bundle.cause_present_in_summary
            and bundle.effect_present_in_summary
            and not bundle.has_explicit_summary_relation
            and not bundle.has_weakened_language
        ):
            return (
                DistortionLabel.DROPPED,
                EvidenceStrength.MEDIUM,
                "relevant source cause and effect present in summary but causal relationship deleted",
            )

        # 7. DISTORTED Check:
        # Explicit summary relation exists with partial alignment or mismatch that doesn't fit standard categories
        if (
            bundle.has_explicit_summary_relation
            and bundle.overall_score > 0.3
            and bundle.overall_score < self.config.overall_threshold
        ):
            return (
                DistortionLabel.DISTORTED,
                EvidenceStrength.MEDIUM,
                "explicit summary relation present with structural/causal mismatch",
            )

        # 8. INSUFFICIENT_EVIDENCE Fallback:
        # Default for missing relations, missing arguments, low similarity, extraction failure, ambiguous evidence
        return (
            DistortionLabel.INSUFFICIENT_EVIDENCE,
            EvidenceStrength.INSUFFICIENT,
            "no explicit summary causal relation and insufficient argument evidence",
        )
