"""Inter-Annotator Agreement Evaluator for Phase 12 Human Validation."""

from collections import defaultdict
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from causalfidelity.annotation.schema import (
    APPROVED_CAUSAL_LABELS,
    AnnotationRecord,
    validate_annotation_dict,
)
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)

NATURALNESS_RATINGS = [1, 2, 3, 4, 5]


@dataclass
class AgreementResult:
    """Structured result container for inter-annotator agreement evaluation."""

    total_input_records: int
    total_unique_items: int
    eligible_paired_items: int
    excluded_items_count: int
    excluded_items: List[Dict[str, Any]] = field(default_factory=list)
    annotators: List[str] = field(default_factory=list)
    causal_classification_agreement: Dict[str, Any] = field(default_factory=dict)
    naturalness_agreement: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result object to dictionary format."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize result object to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class InterAnnotatorAgreementEvaluator:
    """Evaluates inter-annotator agreement using standard unweighted Cohen's Kappa."""

    @staticmethod
    def calculate_cohens_kappa(
        paired_values: List[Tuple[Any, Any]],
        categories: List[Any],
    ) -> Dict[str, Any]:
        """Calculate unweighted Cohen's Kappa for paired ratings across categories.

        Args:
            paired_values: List of (rating_ann1, rating_ann2) tuples for matched items.
            categories: List of all valid category labels/values.

        Returns:
            Dictionary containing Kappa statistics, observed/expected agreement, and confusion matrix.
        """
        N = len(paired_values)
        cat_list = list(categories)

        # Initialize confusion matrix and frequency maps
        confusion_matrix = {str(c1): {str(c2): 0 for c2 in cat_list} for c1 in cat_list}
        count_ann1 = {str(c): 0 for c in cat_list}
        count_ann2 = {str(c): 0 for c in cat_list}

        if N == 0:
            return {
                "categories": [str(c) for c in cat_list],
                "matched_pairs_count": 0,
                "observed_agreement": 0.0,
                "expected_agreement": 0.0,
                "cohens_kappa": None,
                "kappa_status": "undefined",
                "undefined_reason": "no_eligible_annotation_pairs",
                "disagreement_summary": [],
                "confusion_matrix": confusion_matrix,
            }

        observed_matches = 0
        disagreements = []

        for item_idx, (val1, val2) in enumerate(paired_values):
            s_val1 = str(val1)
            s_val2 = str(val2)

            if s_val1 in count_ann1:
                count_ann1[s_val1] += 1
            else:
                count_ann1[s_val1] = 1

            if s_val2 in count_ann2:
                count_ann2[s_val2] += 1
            else:
                count_ann2[s_val2] = 1

            if s_val1 in confusion_matrix and s_val2 in confusion_matrix[s_val1]:
                confusion_matrix[s_val1][s_val2] += 1

            if s_val1 == s_val2:
                observed_matches += 1

        p_o = round(observed_matches / N, 4)

        # Expected agreement P_e = sum_k (p_1k * p_2k)
        p_e_raw = sum(
            (count_ann1.get(str(c), 0) / N) * (count_ann2.get(str(c), 0) / N)
            for c in cat_list
        )
        p_e = round(p_e_raw, 4)

        # Kappa calculation: (P_o - P_e) / (1 - P_e)
        if abs(1.0 - p_e_raw) < 1e-12:
            cohens_kappa = None
            kappa_status = "undefined"
            undefined_reason = "zero_variance_expected_agreement_equals_one"
        else:
            kappa_val = (p_o - p_e) / (1.0 - p_e)
            cohens_kappa = round(kappa_val, 4)
            kappa_status = "calculated"
            undefined_reason = None

        return {
            "categories": [str(c) for c in cat_list],
            "matched_pairs_count": N,
            "observed_agreement": p_o,
            "expected_agreement": p_e,
            "cohens_kappa": cohens_kappa,
            "kappa_status": kappa_status,
            "undefined_reason": undefined_reason,
            "confusion_matrix": confusion_matrix,
        }

    def evaluate(
        self, records: List[Union[AnnotationRecord, Dict[str, Any]]]
    ) -> AgreementResult:
        """Evaluate inter-annotator agreement on a set of annotation records.

        Args:
            records: List of AnnotationRecord objects or raw dictionary records.

        Returns:
            AgreementResult dataclass instance.
        """
        total_input_records = len(records)
        all_annotators: Set[str] = set()

        # Step 1: Group records by perturbation_id
        items_map: Dict[str, List[AnnotationRecord]] = defaultdict(list)
        invalid_item_reasons: Dict[str, str] = {}

        for rec_idx, rec in enumerate(records):
            if isinstance(rec, dict):
                is_valid, errors = validate_annotation_dict(rec)
                if not is_valid:
                    pert_id = str(rec.get("perturbation_id", f"invalid_rec_{rec_idx}")).strip()
                    invalid_item_reasons[pert_id] = f"invalid_record: {', '.join(errors)}"
                    continue
                record_obj = AnnotationRecord.from_dict(rec)
            elif isinstance(rec, AnnotationRecord):
                is_valid, errors = rec.validate()
                if not is_valid:
                    invalid_item_reasons[rec.perturbation_id] = f"invalid_record: {', '.join(errors)}"
                    continue
                record_obj = rec
            else:
                invalid_item_reasons[f"unknown_type_{rec_idx}"] = "unsupported_record_type"
                continue

            items_map[record_obj.perturbation_id].append(record_obj)
            if record_obj.annotator_id:
                all_annotators.add(record_obj.annotator_id)

        total_unique_items = len(items_map)
        eligible_pairs: List[Tuple[AnnotationRecord, AnnotationRecord]] = []
        excluded_items: List[Dict[str, Any]] = []

        # Include pre-flagged invalid items in excluded_items
        for bad_id, reason in invalid_item_reasons.items():
            excluded_items.append(
                {
                    "perturbation_id": bad_id,
                    "reason": reason,
                    "records_count": 0,
                }
            )

        # Step 2: Validate pairing eligibility for each item
        for pert_id in sorted(items_map.keys()):
            recs_list = items_map[pert_id]

            # Check for duplicate annotators on the same item
            annotator_ids = [r.annotator_id for r in recs_list]
            if len(annotator_ids) != len(set(annotator_ids)):
                excluded_items.append(
                    {
                        "perturbation_id": pert_id,
                        "reason": "duplicate_annotator_for_item",
                        "records_count": len(recs_list),
                    }
                )
                continue

            # Check exact 2 annotators condition
            if len(recs_list) < 2:
                excluded_items.append(
                    {
                        "perturbation_id": pert_id,
                        "reason": f"insufficient_annotators_count: {len(recs_list)}",
                        "records_count": len(recs_list),
                    }
                )
                continue
            elif len(recs_list) > 2:
                excluded_items.append(
                    {
                        "perturbation_id": pert_id,
                        "reason": f"excess_annotators_count: {len(recs_list)}",
                        "records_count": len(recs_list),
                    }
                )
                continue

            # Exactly 2 distinct annotators -> sort deterministically by annotator_id
            sorted_recs = sorted(recs_list, key=lambda r: r.annotator_id)
            eligible_pairs.append((sorted_recs[0], sorted_recs[1]))

        eligible_count = len(eligible_pairs)
        excluded_count = len(excluded_items)

        # Step 3: Extract paired values for causal labels and naturalness ratings
        causal_paired_labels: List[Tuple[str, str]] = []
        naturalness_paired_ratings: List[Tuple[int, int]] = []
        causal_disagreements: List[Dict[str, Any]] = []
        naturalness_disagreements: List[Dict[str, Any]] = []

        approved_labels_sorted = sorted(list(APPROVED_CAUSAL_LABELS))

        for rec1, rec2 in eligible_pairs:
            causal_paired_labels.append((rec1.causal_label, rec2.causal_label))
            naturalness_paired_ratings.append((rec1.naturalness_rating, rec2.naturalness_rating))

            if rec1.causal_label != rec2.causal_label:
                causal_disagreements.append(
                    {
                        "perturbation_id": rec1.perturbation_id,
                        "annotator1_id": rec1.annotator_id,
                        "annotator2_id": rec2.annotator_id,
                        "label1": rec1.causal_label,
                        "label2": rec2.causal_label,
                    }
                )

            if rec1.naturalness_rating != rec2.naturalness_rating:
                naturalness_disagreements.append(
                    {
                        "perturbation_id": rec1.perturbation_id,
                        "annotator1_id": rec1.annotator_id,
                        "annotator2_id": rec2.annotator_id,
                        "rating1": rec1.naturalness_rating,
                        "rating2": rec2.naturalness_rating,
                    }
                )

        # Step 4: Calculate Cohen's Kappa for both dimensions
        causal_agree_stats = self.calculate_cohens_kappa(
            causal_paired_labels, approved_labels_sorted
        )
        causal_agree_stats["disagreement_summary"] = causal_disagreements

        naturalness_agree_stats = self.calculate_cohens_kappa(
            naturalness_paired_ratings, NATURALNESS_RATINGS
        )
        naturalness_agree_stats["disagreement_summary"] = naturalness_disagreements

        logger.info(
            f"Agreement evaluation complete: {eligible_count} eligible pairs out of {total_unique_items} items. "
            f"Causal Kappa: {causal_agree_stats['cohens_kappa']}, Naturalness Kappa: {naturalness_agree_stats['cohens_kappa']}"
        )

        return AgreementResult(
            total_input_records=total_input_records,
            total_unique_items=total_unique_items,
            eligible_paired_items=eligible_count,
            excluded_items_count=excluded_count,
            excluded_items=excluded_items,
            annotators=sorted(list(all_annotators)),
            causal_classification_agreement=causal_agree_stats,
            naturalness_agreement=naturalness_agree_stats,
        )
