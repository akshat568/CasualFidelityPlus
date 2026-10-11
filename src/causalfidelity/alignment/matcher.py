"""Candidate ranking, thresholding, exact matching baseline, and ambiguity handling matcher."""

from typing import Any, Dict, List, Optional
import numpy as np

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.normalizer import check_exact_match
from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.alignment.scorer import CausalScorer
from causalfidelity.causal.schema import CausalRelation
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class CausalMatcher:
    """Matcher that scores, ranks, and categorizes candidate summary relations for a source relation."""

    def __init__(
        self,
        embedder: SemanticEmbedder,
        scorer: CausalScorer,
        cause_threshold: float = 0.50,
        effect_threshold: float = 0.50,
        overall_threshold: float = 0.60,
        ambiguity_margin: float = 0.05,
    ):
        self.embedder = embedder
        self.scorer = scorer
        self.cause_threshold = cause_threshold
        self.effect_threshold = effect_threshold
        self.overall_threshold = overall_threshold
        self.ambiguity_margin = ambiguity_margin

    def match_source_relation(
        self,
        source_rel: CausalRelation,
        candidate_summary_rels: List[SummaryCausalRelation],
    ) -> CausalAlignment:
        """Find best candidate summary relation for a source relation and evaluate alignment status.

        Args:
            source_rel: Source CausalRelation object.
            candidate_summary_rels: List of candidate SummaryCausalRelation objects from the same document.

        Returns:
            CausalAlignment object with rank, scores, exact_match, and alignment_status.
        """
        doc_id = source_rel.document_id
        src_id = source_rel.relation_id or f"{doc_id}_src"
        align_id = f"align_{src_id}"

        source_rel_dict = {
            "cause": source_rel.cause,
            "relation": source_rel.relation,
            "effect": source_rel.effect,
        }

        meta = {
            "embedding_model": self.embedder.model_name,
            "device": self.embedder.device,
            **self.scorer.get_weights_metadata(),
            "cause_threshold": self.cause_threshold,
            "effect_threshold": self.effect_threshold,
            "overall_threshold": self.overall_threshold,
            "ambiguity_margin": self.ambiguity_margin,
        }

        # Case 1: No candidate summary relations exist for this document
        if not candidate_summary_rels:
            return CausalAlignment(
                alignment_id=align_id,
                document_id=doc_id,
                source_relation_id=src_id,
                summary_id=None,
                summary_relation_id=None,
                source_relation=source_rel_dict,
                summary_relation=None,
                cause_similarity=0.0,
                effect_similarity=0.0,
                relation_compatibility=0.0,
                overall_alignment_score=0.0,
                candidate_rank=None,
                alignment_status="no_candidate",
                exact_match=False,
                metadata=meta,
            )

        # Embed source cause and effect
        source_cause_vec = self.embedder.embed(source_rel.cause)[0]
        source_effect_vec = self.embedder.embed(source_rel.effect)[0]

        # Embed all candidate summary causes and effects
        cand_causes = [c.cause for c in candidate_summary_rels]
        cand_effects = [c.effect for c in candidate_summary_rels]

        cand_cause_vecs = self.embedder.embed(cand_causes)
        cand_effect_vecs = self.embedder.embed(cand_effects)

        scored_candidates: List[Dict[str, Any]] = []

        for idx, cand_rel in enumerate(candidate_summary_rels):
            c_cause_vec = cand_cause_vecs[idx]
            c_effect_vec = cand_effect_vecs[idx]

            cause_sim, effect_sim, rel_compat, overall_score = self.scorer.score_candidate(
                source_cause_vec=source_cause_vec,
                source_effect_vec=source_effect_vec,
                summary_cause_vec=c_cause_vec,
                summary_effect_vec=c_effect_vec,
                source_relation_trigger=source_rel.relation,
                summary_relation_trigger=cand_rel.relation,
            )

            exact = check_exact_match(
                source_cause=source_rel.cause,
                source_effect=source_rel.effect,
                summary_cause=cand_rel.cause,
                summary_effect=cand_rel.effect,
            )

            scored_candidates.append({
                "candidate": cand_rel,
                "cause_similarity": cause_sim,
                "effect_similarity": effect_sim,
                "relation_compatibility": rel_compat,
                "overall_alignment_score": overall_score,
                "exact_match": exact,
            })

        # Rank candidates by overall_alignment_score descending with stable secondary sort on ID for determinism
        scored_candidates.sort(
            key=lambda x: (x["overall_alignment_score"], x["candidate"].summary_relation_id),
            reverse=True,
        )

        top_cand = scored_candidates[0]
        top_summary_rel = top_cand["candidate"]
        top_score = top_cand["overall_alignment_score"]
        top_cause_sim = top_cand["cause_similarity"]
        top_effect_sim = top_cand["effect_similarity"]

        # Ambiguity and threshold evaluation
        if (
            top_score < self.overall_threshold
            or top_cause_sim < self.cause_threshold
            or top_effect_sim < self.effect_threshold
        ):
            status = "below_threshold"
        elif len(scored_candidates) > 1:
            second_score = scored_candidates[1]["overall_alignment_score"]
            if (top_score - second_score) < self.ambiguity_margin:
                status = "ambiguous"
            else:
                status = "aligned"
        else:
            status = "aligned"

        summary_rel_dict = {
            "cause": top_summary_rel.cause,
            "relation": top_summary_rel.relation,
            "effect": top_summary_rel.effect,
        }

        return CausalAlignment(
            alignment_id=align_id,
            document_id=doc_id,
            source_relation_id=src_id,
            summary_id=top_summary_rel.summary_id,
            summary_relation_id=top_summary_rel.summary_relation_id,
            source_relation=source_rel_dict,
            summary_relation=summary_rel_dict,
            cause_similarity=round(float(top_cand["cause_similarity"]), 4),
            effect_similarity=round(float(top_cand["effect_similarity"]), 4),
            relation_compatibility=round(float(top_cand["relation_compatibility"]), 4),
            overall_alignment_score=round(float(top_cand["overall_alignment_score"]), 4),
            candidate_rank=1,
            alignment_status=status,
            exact_match=top_cand["exact_match"],
            metadata=meta,
        )
