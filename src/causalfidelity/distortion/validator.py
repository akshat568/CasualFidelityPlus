"""Benchmark validator and evaluator for Phase 7 controlled perturbations."""

from typing import Any, Dict, List, Tuple

from causalfidelity.distortion.schema import DistortionAnalysisRecord, DistortionLabel
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class DistortionBenchmarkFilter:
    """Filter and evaluator for Phase 7 controlled perturbation benchmark."""

    @staticmethod
    def filter_valid_perturbations(
        validation_records: List[Dict[str, Any]],
        perturbation_records: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Filter perturbations retaining only Phase 7 valid records.

        Args:
            validation_records: Raw Phase 7 validation records.
            perturbation_records: Phase 6/7 perturbation content records.

        Returns:
            Tuple of (valid_perturbation_list, rejected_perturbation_list).
        """
        valid_ids = set()
        for v in validation_records:
            status = str(v.get("validation_status", "")).lower()
            if status == "valid":
                valid_ids.add(v.get("perturbation_id"))

        pert_by_id = {p.get("perturbation_id"): p for p in perturbation_records}

        valid_pert_list = []
        rejected_pert_list = []

        for p_id, p in pert_by_id.items():
            if p_id in valid_ids:
                valid_pert_list.append(p)
            else:
                rejected_pert_list.append(p)

        # Sort deterministically by perturbation_id
        valid_pert_list.sort(key=lambda x: str(x.get("perturbation_id")))
        rejected_pert_list.sort(key=lambda x: str(x.get("perturbation_id")))

        return valid_pert_list, rejected_pert_list

    @staticmethod
    def calculate_benchmark_stats(
        analysis_records: List[DistortionAnalysisRecord],
        valid_count: int,
        rejected_count: int,
    ) -> Dict[str, Any]:
        """Calculate evaluation statistics over valid benchmark perturbation analyses.

        Args:
            analysis_records: List of DistortionAnalysisRecord results for benchmark perturbations.
            valid_count: Total valid perturbation count.
            rejected_count: Total rejected perturbation count.

        Returns:
            Dictionary containing evaluation metrics and distributions.
        """
        eval_count = len(analysis_records)
        agreement_count = sum(1 for r in analysis_records if r.agreement is True)
        insufficient_count = sum(1 for r in analysis_records if r.detected_label == DistortionLabel.INSUFFICIENT_EVIDENCE)

        agreement_rate = float(agreement_count / eval_count) if eval_count > 0 else 0.0

        intended_dist: Dict[str, int] = {}
        detected_dist: Dict[str, int] = {}

        for r in analysis_records:
            if r.intended_label:
                intended_dist[r.intended_label] = intended_dist.get(r.intended_label, 0) + 1
            detected_dist[r.detected_label] = detected_dist.get(r.detected_label, 0) + 1

        valid_reversed_count = intended_dist.get(DistortionLabel.REVERSED, 0)

        reversed_note = (
            "No validated REVERSED perturbations are currently available for benchmark evaluation."
            if valid_reversed_count == 0
            else f"{valid_reversed_count} validated REVERSED perturbations evaluated."
        )

        valid_ids = sorted([r.perturbation_id for r in analysis_records if r.perturbation_id])

        stats = {
            "total_valid_perturbations": valid_count,
            "total_rejected_perturbations": rejected_count,
            "evaluated_count": eval_count,
            "agreement_count": agreement_count,
            "agreement_rate": round(agreement_rate, 4),
            "insufficient_evidence_count": insufficient_count,
            "valid_reversed_count": valid_reversed_count,
            "intended_label_distribution": intended_dist,
            "detected_label_distribution": detected_dist,
            "valid_perturbation_ids": valid_ids,
            "benchmark_limitation_note": reversed_note,
            "sample_size_warning": f"Small sample size (n={eval_count}). Results are descriptive and not statistically significant.",
        }

        return stats

    @staticmethod
    def generate_confusion_matrix(analysis_records: List[DistortionAnalysisRecord]) -> Dict[str, Any]:
        """Generate confusion matrix structure for controlled perturbations.

        Args:
            analysis_records: Evaluation records for benchmark perturbations.

        Returns:
            Dictionary containing matrix counts and metadata.
        """
        matrix: Dict[str, Dict[str, int]] = {}

        labels = DistortionLabel.ALL_LABELS

        for row_label in labels:
            matrix[row_label] = {col_label: 0 for col_label in labels}

        for r in analysis_records:
            intended = r.intended_label or DistortionLabel.INSUFFICIENT_EVIDENCE
            detected = r.detected_label
            if intended in matrix and detected in matrix[intended]:
                matrix[intended][detected] += 1

        return {
            "sample_size": len(analysis_records),
            "labels": labels,
            "matrix": matrix,
            "metadata": {
                "description": "Confusion matrix mapping Phase 6 intended perturbation labels to Phase 9 independently detected labels.",
                "note": "Evaluated on Phase 7 valid perturbations only.",
            },
        }
