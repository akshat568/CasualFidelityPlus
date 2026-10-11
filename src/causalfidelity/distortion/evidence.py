"""Evidence collection module reusing Phase 8 alignment scores and utilities."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.normalizer import (
    ASSOCIATIVE_TRIGGERS,
    STRONG_CAUSAL_TRIGGERS,
    compute_relation_compatibility,
    normalize_text,
)
from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.alignment.scorer import CausalScorer
from causalfidelity.alignment.summary_extractor import SummaryCausalExtractor
from causalfidelity.config import CausalDistortionConfig
from causalfidelity.distortion.schema import SummaryEvidenceRecord
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvidenceBundle:
    """Container holding gathered causal and argument evidence for classification."""

    source_relation_id: str
    source_cause: str
    source_relation: str
    source_effect: str
    summary_id: str
    summary_text: str

    # Extracted or matched summary relation (if available)
    summary_relation_id: Optional[str] = None
    summary_cause: Optional[str] = None
    summary_relation: Optional[str] = None
    summary_effect: Optional[str] = None

    # Forward similarity & alignment metrics (cause->cause, effect->effect)
    cause_sim: float = 0.0
    effect_sim: float = 0.0
    relation_compat: float = 0.0
    overall_score: float = 0.0
    alignment_status: str = "no_candidate"

    # Reversal similarity & alignment metrics (cause->effect, effect->cause)
    reverse_cause_sim: float = 0.0
    reverse_effect_sim: float = 0.0

    # Presence flags
    cause_present_in_summary: bool = False
    effect_present_in_summary: bool = False
    has_explicit_summary_relation: bool = False
    has_associative_trigger: bool = False
    has_weakened_language: bool = False

    # Intended perturbation context (if evaluated on controlled perturbation)
    perturbation_id: Optional[str] = None
    intended_label: Optional[str] = None


class DistortionEvidenceCollector:
    """Collector that gathers directional argument and relation evidence for Phase 9 analysis."""

    def __init__(self, config: Optional[CausalDistortionConfig] = None, embedder: Optional[SemanticEmbedder] = None):
        self.config = config or CausalDistortionConfig()
        self.scorer = CausalScorer(cause_weight=0.45, effect_weight=0.45, relation_weight=0.10)
        self.summary_extractor = SummaryCausalExtractor()
        self.embedder = embedder

    def _get_embedder(self) -> SemanticEmbedder:
        if self.embedder is None:
            self.embedder = SemanticEmbedder(model_name="all-MiniLM-L6-v2", device="cpu")
        return self.embedder

    def collect_from_phase8_alignment(
        self,
        source_rel: Dict[str, Any],
        alignment: Optional[CausalAlignment],
        summary_record: Dict[str, Any],
        summary_rel: Optional[SummaryCausalRelation] = None,
    ) -> EvidenceBundle:
        """Gather evidence reusing Phase 8 alignment score records directly.

        Args:
            source_rel: Source relation dictionary.
            alignment: Precomputed CausalAlignment from Phase 8.
            summary_record: Summary input record containing summary_text.
            summary_rel: Summary relation object from Phase 8 if matched.

        Returns:
            EvidenceBundle containing compiled evidence.
        """
        src_id = source_rel.get("relation_id", "")
        src_cause = source_rel.get("cause", "")
        src_relation = source_rel.get("relation", "causes")
        src_effect = source_rel.get("effect", "")

        sum_id = summary_record.get("summary_id", f"{source_rel.get('document_id', '')}_summary")
        sum_text = summary_record.get("summary_text", "")

        norm_sc = normalize_text(src_cause)
        norm_se = normalize_text(src_effect)
        norm_st = normalize_text(sum_text)

        cause_present = (len(norm_sc) > 3 and norm_sc in norm_st) or (
            alignment is not None and alignment.cause_similarity >= self.config.cause_threshold
        )
        effect_present = (len(norm_se) > 3 and norm_se in norm_st) or (
            alignment is not None and alignment.effect_similarity >= self.config.effect_threshold
        )

        bundle = EvidenceBundle(
            source_relation_id=src_id,
            source_cause=src_cause,
            source_relation=src_relation,
            source_effect=src_effect,
            summary_id=sum_id,
            summary_text=sum_text,
            cause_present_in_summary=cause_present,
            effect_present_in_summary=effect_present,
        )

        if alignment is not None:
            bundle.cause_sim = alignment.cause_similarity
            bundle.effect_sim = alignment.effect_similarity
            bundle.relation_compat = alignment.relation_compatibility
            bundle.overall_score = alignment.overall_alignment_score
            bundle.alignment_status = alignment.alignment_status

            if alignment.summary_relation:
                bundle.summary_relation_id = alignment.summary_relation_id
                bundle.summary_cause = alignment.summary_relation.get("cause")
                bundle.summary_relation = alignment.summary_relation.get("relation")
                bundle.summary_effect = alignment.summary_relation.get("effect")
                bundle.has_explicit_summary_relation = True
            elif summary_rel:
                bundle.summary_relation_id = summary_rel.summary_relation_id
                bundle.summary_cause = summary_rel.cause
                bundle.summary_relation = summary_rel.relation
                bundle.summary_effect = summary_rel.effect
                bundle.has_explicit_summary_relation = True

        if bundle.summary_relation:
            sum_rel_norm = normalize_text(bundle.summary_relation)
            if any(word in sum_rel_norm for word in self.config.weakened_trigger_words) or any(
                assoc in sum_rel_norm for assoc in ASSOCIATIVE_TRIGGERS
            ):
                bundle.has_weakened_language = True
                bundle.has_associative_trigger = True

        # Compute reverse alignment check if both source arguments exist
        if src_cause and src_effect and sum_text:
            emb = self._get_embedder()
            sc_vec = emb.embed(src_cause)[0]
            se_vec = emb.embed(src_effect)[0]

            if bundle.summary_cause and bundle.summary_effect:
                mc_vec = emb.embed(bundle.summary_cause)[0]
                me_vec = emb.embed(bundle.summary_effect)[0]
                bundle.reverse_cause_sim = max(0.0, SemanticEmbedder.cosine_similarity(sc_vec, me_vec))
                bundle.reverse_effect_sim = max(0.0, SemanticEmbedder.cosine_similarity(se_vec, mc_vec))
            else:
                bundle.reverse_cause_sim = 0.0
                bundle.reverse_effect_sim = 0.0

        return bundle

    def collect_from_perturbation(
        self,
        perturbation: Dict[str, Any],
        source_rel: Dict[str, Any],
    ) -> EvidenceBundle:
        """Gather evidence for a controlled perturbation using Phase 8 extraction & scoring rules.

        Args:
            perturbation: Phase 6/7 perturbation record containing perturbed_text, intended_relation, etc.
            source_rel: Original source relation dictionary.

        Returns:
            EvidenceBundle containing collected evidence on perturbed text.
        """
        src_id = source_rel.get("relation_id", "")
        src_cause = source_rel.get("cause", "")
        src_relation = source_rel.get("relation", "causes")
        src_effect = source_rel.get("effect", "")

        pert_id = perturbation.get("perturbation_id")
        intended_type = perturbation.get("perturbation_type", perturbation.get("intended_label"))
        sum_id = perturbation.get("summary_id", "")
        pert_text = perturbation.get("perturbed_text", "")

        norm_sc = normalize_text(src_cause)
        norm_se = normalize_text(src_effect)
        norm_pt = normalize_text(pert_text)

        cause_present = (len(norm_sc) > 3 and norm_sc in norm_pt)
        effect_present = (len(norm_se) > 3 and norm_se in norm_pt)

        bundle = EvidenceBundle(
            source_relation_id=src_id,
            source_cause=src_cause,
            source_relation=src_relation,
            source_effect=src_effect,
            summary_id=sum_id,
            summary_text=pert_text,
            cause_present_in_summary=cause_present,
            effect_present_in_summary=effect_present,
            perturbation_id=pert_id,
            intended_label=intended_type,
        )

        # Extract explicit summary relations from perturbed text using Phase 8 SummaryCausalExtractor
        extracted_sum_rels = self.summary_extractor.extract_from_summary(
            {"document_id": perturbation.get("document_id", ""), "summary_id": sum_id, "summary_text": pert_text}
        )

        emb = self._get_embedder()
        sc_vec = emb.embed(src_cause)[0] if src_cause else np.zeros(384, dtype=np.float32)
        se_vec = emb.embed(src_effect)[0] if src_effect else np.zeros(384, dtype=np.float32)

        best_score = -1.0
        best_sum_rel: Optional[SummaryCausalRelation] = None

        for sum_rel in extracted_sum_rels:
            mc_vec = emb.embed(sum_rel.cause)[0]
            me_vec = emb.embed(sum_rel.effect)[0]

            c_sim, e_sim, r_compat, o_score = self.scorer.score_candidate(
                source_cause_vec=sc_vec,
                source_effect_vec=se_vec,
                summary_cause_vec=mc_vec,
                summary_effect_vec=me_vec,
                source_relation_trigger=src_relation,
                summary_relation_trigger=sum_rel.relation,
            )

            if o_score > best_score:
                best_score = o_score
                best_sum_rel = sum_rel
                bundle.cause_sim = c_sim
                bundle.effect_sim = e_sim
                bundle.relation_compat = r_compat
                bundle.overall_score = o_score

                # Reversal scores
                bundle.reverse_cause_sim = max(0.0, SemanticEmbedder.cosine_similarity(sc_vec, me_vec))
                bundle.reverse_effect_sim = max(0.0, SemanticEmbedder.cosine_similarity(se_vec, mc_vec))

        if best_sum_rel:
            bundle.summary_relation_id = best_sum_rel.summary_relation_id
            bundle.summary_cause = best_sum_rel.cause
            bundle.summary_relation = best_sum_rel.relation
            bundle.summary_effect = best_sum_rel.effect
            bundle.has_explicit_summary_relation = True
            bundle.alignment_status = "aligned" if bundle.overall_score >= self.config.overall_threshold else "below_threshold"
            if cause_present or bundle.cause_sim >= self.config.cause_threshold:
                bundle.cause_present_in_summary = True
            if effect_present or bundle.effect_sim >= self.config.effect_threshold:
                bundle.effect_present_in_summary = True
        else:
            bundle.alignment_status = "no_candidate"
            # If no extracted candidate relation, evaluate direct text argument alignment via embeddings
            if pert_text:
                pt_vec = emb.embed(pert_text)[0]
                c_sim = max(0.0, SemanticEmbedder.cosine_similarity(sc_vec, pt_vec))
                e_sim = max(0.0, SemanticEmbedder.cosine_similarity(se_vec, pt_vec))
                bundle.cause_sim = c_sim
                bundle.effect_sim = e_sim
                if cause_present or c_sim >= self.config.cause_threshold:
                    bundle.cause_present_in_summary = True
                if effect_present or e_sim >= self.config.effect_threshold:
                    bundle.effect_present_in_summary = True



        # Check for weakened/associative triggers in summary text or summary relation
        text_norm = norm_pt
        if bundle.summary_relation:
            text_norm += " " + normalize_text(bundle.summary_relation)

        if any(word in text_norm for word in self.config.weakened_trigger_words) or any(
            assoc in text_norm for assoc in ASSOCIATIVE_TRIGGERS
        ):
            bundle.has_weakened_language = True
            bundle.has_associative_trigger = True

        return bundle
