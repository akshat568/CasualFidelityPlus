"""Perturbation generator and summary eligibility component."""

import re
from typing import Any, Dict, List, Optional, Tuple

from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.causal.schema import CausalRelation
from causalfidelity.perturbation.schema import PerturbationRecord, generate_perturbation_id
from causalfidelity.perturbation.strategies import (
    CauseSubstitutionStrategy,
    DeletionStrategy,
    EffectSubstitutionStrategy,
    PerturbationStrategy,
    ReversalStrategy,
    WeakeningStrategy,
)


DEFAULT_FALLBACK_CAUSES = [
    "An earthquake",
    "A power outage",
    "Severe weather",
    "A technical failure",
]

DEFAULT_FALLBACK_EFFECTS = [
    "power grid failures",
    "structural damage",
    "service disruptions",
    "system outages",
]


class PerturbationGenerator:
    """Coordinates summary-level causal eligibility checks and strategy application."""

    def __init__(self):
        self.strategies: List[PerturbationStrategy] = [
            ReversalStrategy(),
            WeakeningStrategy(),
            DeletionStrategy(),
            CauseSubstitutionStrategy(),
            EffectSubstitutionStrategy(),
        ]
        self.extractor = RuleBasedCausalExtractor()

    @staticmethod
    def is_relation_explicitly_in_summary(summary_text: str, relation: CausalRelation) -> bool:
        """Check if cause and effect of a Phase 3 relation are explicitly represented in summary text.

        Uses deterministic exact/normalized lowercased string matching.
        """
        if not summary_text or not relation.cause or not relation.effect:
            return False

        sum_lower = summary_text.lower()
        cause_clean = relation.cause.strip().lower()
        effect_clean = relation.effect.strip().lower()

        # Direct string presence check
        if cause_clean in sum_lower and effect_clean in sum_lower:
            return True

        stopwords = {"cause", "causes", "effect", "effects", "result", "results", "because", "this", "that", "there", "which", "where", "with", "from", "unrelated"}

        c_words = [w for w in re.findall(r"\b[a-z]{3,}\b", cause_clean) if w not in stopwords]
        e_words = [w for w in re.findall(r"\b[a-z]{3,}\b", effect_clean) if w not in stopwords]

        if not c_words or not e_words:
            return False

        c_match = all(w in sum_lower for w in c_words) or (len(c_words) >= 2 and sum(1 for w in c_words if w in sum_lower) >= len(c_words) * 0.7)
        e_match = all(w in sum_lower for w in e_words) or (len(e_words) >= 2 and sum(1 for w in e_words if w in sum_lower) >= len(e_words) * 0.7)

        return c_match and e_match

    def extract_direct_summary_relations(self, document_id: str, summary_text: str) -> List[CausalRelation]:
        """Extract explicit causal relations directly from reference summary text using Phase 3 extractor."""
        return self.extractor.extract_relations(document_id, summary_text)

    def generate_perturbations(
        self,
        document_id: str,
        summary_id: str,
        summary_text: str,
        doc_relations: List[CausalRelation],
        counter_start: int = 1,
    ) -> Tuple[List[PerturbationRecord], Dict[str, Any]]:
        """Generate candidate perturbations for a summary record.

        Returns:
            Tuple of (list_of_candidate_records, generation_stats_dict).
        """
        records: List[PerturbationRecord] = []

        stats = {
            "source_relations_examined": len(doc_relations),
            "eligible_relations": 0,
            "relations_not_present_in_summary": 0,
            "generated_by_type": {
                "REVERSED": 0,
                "WEAKENED": 0,
                "DROPPED": 0,
                "CAUSE_CHANGED": 0,
                "EFFECT_CHANGED": 0,
            },
            "rejection_reasons": {},
        }

        # Step 1: Collect direct summary relations AND eligible source relations
        summary_direct_rels = self.extract_direct_summary_relations(document_id, summary_text)

        eligible_relations: List[Tuple[CausalRelation, str]] = []

        for s_rel in summary_direct_rels:
            eligible_relations.append((s_rel, summary_text))

        for d_rel in doc_relations:
            if self.is_relation_explicitly_in_summary(summary_text, d_rel):
                # Avoid duplicate if already present in eligible_relations
                if not any(r.cause.lower() == d_rel.cause.lower() and r.effect.lower() == d_rel.effect.lower() for r, _ in eligible_relations):
                    eligible_relations.append((d_rel, summary_text))

        num_eligible = len(eligible_relations)
        num_source_rels = len(doc_relations)
        not_present_count = max(0, num_source_rels - num_eligible)

        stats["eligible_relations"] = num_eligible
        stats["relations_not_present_in_summary"] = not_present_count

        if not_present_count > 0:
            reason = "relation_not_explicitly_present_in_summary"
            stats["rejection_reasons"][reason] = not_present_count

        if not eligible_relations:
            return records, stats

        # Step 2: Build context candidates for CAUSE_CHANGED and EFFECT_CHANGED from all available context relations
        all_context_rels = list(doc_relations) + [r for r, _ in eligible_relations]

        candidate_causes = list(dict.fromkeys([r.cause for r in all_context_rels if r.cause]))
        candidate_effects = list(dict.fromkeys([r.effect for r in all_context_rels if r.effect]))

        for fb_cause in DEFAULT_FALLBACK_CAUSES:
            if fb_cause not in candidate_causes:
                candidate_causes.append(fb_cause)

        for fb_effect in DEFAULT_FALLBACK_EFFECTS:
            if fb_effect not in candidate_effects:
                candidate_effects.append(fb_effect)

        context_candidates = {
            "candidate_causes": candidate_causes,
            "candidate_effects": candidate_effects,
        }

        current_counter = counter_start

        # Step 3: Apply each strategy to each eligible relation
        for rel, target_text in eligible_relations:
            orig_rel_dict = {
                "cause": rel.cause,
                "relation": rel.relation,
                "effect": rel.effect,
                "pattern_matched": rel.pattern_matched,
            }

            for strategy in self.strategies:
                res = strategy.apply(
                    text=target_text,
                    cause=rel.cause,
                    relation=rel.relation,
                    effect=rel.effect,
                    pattern_matched=rel.pattern_matched,
                    context_candidates=context_candidates,
                )

                if res is None:
                    # Strategy-level skip
                    if strategy.perturbation_type == "CAUSE_CHANGED":
                        s_reason = "missing_candidate_cause"
                    elif strategy.perturbation_type == "EFFECT_CHANGED":
                        s_reason = "missing_candidate_effect"
                    else:
                        s_reason = f"unsupported_{strategy.perturbation_type.lower()}_pattern"
                    stats["rejection_reasons"][s_reason] = stats["rejection_reasons"].get(s_reason, 0) + 1
                    continue

                perturbed_text, intended_rel_dict, changed_span_dict = res

                pert_id = generate_perturbation_id(document_id, current_counter)
                current_counter += 1

                record = PerturbationRecord(
                    perturbation_id=pert_id,
                    document_id=document_id,
                    summary_id=summary_id,
                    perturbation_type=strategy.perturbation_type,
                    original_text=target_text,
                    perturbed_text=perturbed_text,
                    original_relation=orig_rel_dict,
                    intended_relation=intended_rel_dict,
                    changed_span=changed_span_dict,
                    generation_method="rule_based",
                    validation_status="pending",
                    validation_errors=[],
                )
                records.append(record)
                stats["generated_by_type"][strategy.perturbation_type] += 1

        return records, stats
