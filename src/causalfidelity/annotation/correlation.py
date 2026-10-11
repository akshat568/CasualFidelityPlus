"""Statistical Correlation and Metric Sensitivity Evaluator for Phase 12.

Calculates Pearson correlation (r), Spearman rank correlation (rho), ROC-AUC,
binary classification sensitivity/specificity/precision/F1, and category-level
metric sensitivity comparing human validation consensus against automated metrics.
"""

from dataclasses import asdict, dataclass, field
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from causalfidelity.annotation.schema import APPROVED_CAUSAL_LABELS, AnnotationRecord
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)

# Documented score direction mapping:
# For faithfulness metrics (SummaC, FactCC, BERTScore, overall_alignment_score),
# higher scores indicate higher faithfulness (lower distortion probability).
FAITHFULNESS_METRIC_KEYS = {
    "summac_score",
    "factcc_score",
    "bertscore_f1",
    "bertscore_precision",
    "bertscore_recall",
    "overall_alignment_score",
    "cause_similarity",
    "effect_similarity",
}


@dataclass
class CorrelationResult:
    """Structured container for statistical correlation and metric sensitivity results."""

    total_human_records: int
    total_metric_records: int
    matched_records_count: int
    unmatched_human_count: int
    unmatched_metric_count: int
    excluded_records: List[Dict[str, Any]] = field(default_factory=list)
    metric_coverage: Dict[str, int] = field(default_factory=dict)
    pearson_correlations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    spearman_correlations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    roc_auc_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    binary_classification_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    category_sensitivity: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    data_quality_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result object to dictionary format."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize result object to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def compute_pearson_r(x: List[float], y: List[float]) -> Dict[str, Any]:
    """Compute Pearson's correlation coefficient r.

    Args:
        x: List of numeric values.
        y: List of numeric values of equal length.

    Returns:
        Dict containing 'r', 'status', 'undefined_reason', and 'n'.
    """
    n = len(x)
    if n < 2:
        return {
            "r": None,
            "status": "undefined",
            "undefined_reason": "insufficient_observations",
            "n": n,
        }

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)

    if var_x < 1e-12 or var_y < 1e-12:
        return {
            "r": None,
            "status": "undefined",
            "undefined_reason": "constant_input",
            "n": n,
        }

    cov_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    r = cov_xy / math.sqrt(var_x * var_y)
    r_clamped = max(-1.0, min(1.0, r))

    return {
        "r": round(r_clamped, 4),
        "status": "calculated",
        "undefined_reason": None,
        "n": n,
    }


def _compute_fractional_ranks(values: List[float]) -> List[float]:
    """Compute fractional ranks for a list of values (handling ties via average rank)."""
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * n

    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1

    return ranks


def compute_spearman_rho(x: List[float], y: List[float]) -> Dict[str, Any]:
    """Compute Spearman's rank correlation coefficient rho.

    Args:
        x: List of numeric values.
        y: List of numeric values of equal length.

    Returns:
        Dict containing 'rho', 'status', 'undefined_reason', and 'n'.
    """
    n = len(x)
    if n < 2:
        return {
            "rho": None,
            "status": "undefined",
            "undefined_reason": "insufficient_observations",
            "n": n,
        }

    ranks_x = _compute_fractional_ranks(x)
    ranks_y = _compute_fractional_ranks(y)

    pearson_res = compute_pearson_r(ranks_x, ranks_y)
    return {
        "rho": pearson_res["r"],
        "status": pearson_res["status"],
        "undefined_reason": pearson_res["undefined_reason"],
        "n": n,
    }


def compute_roc_auc(
    y_true: List[int],
    y_score: List[float],
    is_faithfulness_metric: bool = True,
    binary_mapping_enabled: bool = True,
) -> Dict[str, Any]:
    """Compute ROC-AUC for binary distortion detection.

    Args:
        y_true: Binary ground truth (1 for distorted, 0 for faithful).
        y_score: Continuous prediction score from automated metric.
        is_faithfulness_metric: If True, lower score indicates higher distortion probability.
        binary_mapping_enabled: If False, report ROC-AUC as unavailable due to undefined mapping.

    Returns:
        Dict containing 'roc_auc', 'status', 'undefined_reason', and 'n'.
    """
    n = len(y_true)
    if not binary_mapping_enabled:
        return {
            "roc_auc": None,
            "status": "undefined",
            "undefined_reason": "binary_mapping_undefined",
            "n": n,
        }

    if n < 2:
        return {
            "roc_auc": None,
            "status": "undefined",
            "undefined_reason": "insufficient_observations",
            "n": n,
        }

    n_pos = sum(1 for y in y_true if y == 1)
    n_neg = n - n_pos

    if n_pos == 0 or n_neg == 0:
        return {
            "roc_auc": None,
            "status": "undefined",
            "undefined_reason": "single_class_target",
            "n": n,
        }

    # Transform score so higher values correspond to higher probability of positive class (distortion)
    scores = [-s if is_faithfulness_metric else s for s in y_score]
    paired = sorted(zip(scores, y_true), key=lambda p: p[0], reverse=True)

    points: List[Tuple[float, float]] = [(0.0, 0.0)]
    tp = 0
    fp = 0

    prev_score = None
    for score, label in paired:
        if prev_score is not None and score != prev_score:
            points.append((fp / n_neg, tp / n_pos))
        if label == 1:
            tp += 1
        else:
            fp += 1
        prev_score = score

    points.append((fp / n_neg, tp / n_pos))

    auc = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        auc += (x2 - x1) * (y1 + y2) / 2.0

    auc_clamped = round(max(0.0, min(1.0, auc)), 4)
    return {
        "roc_auc": auc_clamped,
        "status": "calculated",
        "undefined_reason": None,
        "n": n,
    }


def compute_descriptive_stats(values: List[float]) -> Dict[str, Any]:
    """Compute descriptive statistics for a list of floats."""
    n = len(values)
    if n == 0:
        return {"count": 0, "mean": None, "min": None, "max": None, "std": None}

    mean_v = sum(values) / n
    min_v = min(values)
    max_v = max(values)

    if n > 1:
        var = sum((v - mean_v) ** 2 for v in values) / (n - 1)
        std_v = round(math.sqrt(var), 4)
    else:
        std_v = 0.0

    return {
        "count": n,
        "mean": round(mean_v, 4),
        "min": round(min_v, 4),
        "max": round(max_v, 4),
        "std": std_v,
    }


class StatisticalCorrelationEvaluator:
    """Evaluates statistical correlations and category sensitivity between human consensus and automated metrics."""

    @staticmethod
    def aggregate_human_consensus(
        annotation_records: List[Union[AnnotationRecord, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Group human annotation records by perturbation_id and compute consensus values.

        Args:
            annotation_records: List of AnnotationRecord objects or raw dicts.

        Returns:
            List of consensus dictionary records per unique perturbation_id.
        """
        grouped: Dict[str, List[AnnotationRecord]] = {}

        for rec in annotation_records:
            obj = (
                rec
                if isinstance(rec, AnnotationRecord)
                else AnnotationRecord.from_dict(rec)
            )
            if obj.perturbation_id not in grouped:
                grouped[obj.perturbation_id] = []
            grouped[obj.perturbation_id].append(obj)

        consensus_list: List[Dict[str, Any]] = []

        for pert_id, recs in grouped.items():
            # Support pre-aggregated consensus dictionaries
            first_rec = recs[0]
            if isinstance(first_rec, dict) and "consensus_causal_label" in first_rec:
                c_lbl = first_rec["consensus_causal_label"]
                is_unam = first_rec.get("is_unanimous", True)
                m_nat = first_rec.get("mean_naturalness", 0.0)
                is_dist = None if c_lbl == "DISAGREED" else (
                    c_lbl in ("Reversed", "Weakened", "Dropped", "Cause_Changed", "Effect_Changed")
                )
                consensus_list.append(
                    {
                        "perturbation_id": pert_id,
                        "consensus_causal_label": c_lbl,
                        "is_distorted": is_dist,
                        "mean_naturalness": m_nat,
                        "is_unanimous": is_unam,
                        "annotators_count": first_rec.get("annotators_count", len(recs)),
                    }
                )
                continue

            labels = [r.causal_label for r in recs if r.causal_label]
            naturalness_scores = [
                r.naturalness_rating
                for r in recs
                if r.naturalness_rating is not None and isinstance(r.naturalness_rating, (int, float))
            ]

            if labels:
                label_counts: Dict[str, int] = {}
                for lbl in labels:
                    label_counts[lbl] = label_counts.get(lbl, 0) + 1

                sorted_counts = sorted(label_counts.items(), key=lambda item: item[1], reverse=True)
                if len(sorted_counts) == 1:
                    consensus_label = sorted_counts[0][0]
                    is_unanimous = True
                elif len(sorted_counts) > 1 and sorted_counts[0][1] > sorted_counts[1][1]:
                    consensus_label = sorted_counts[0][0]
                    is_unanimous = True
                else:  # Disagreement / Tie
                    consensus_label = "DISAGREED"
                    is_unanimous = False
            else:
                consensus_label = "UNKNOWN"
                is_unanimous = False

            mean_naturalness = (
                round(sum(naturalness_scores) / len(naturalness_scores), 2)
                if naturalness_scores
                else 0.0
            )

            if consensus_label == "DISAGREED":
                is_distorted = None
            else:
                is_distorted = consensus_label in (
                    "Reversed",
                    "Weakened",
                    "Dropped",
                    "Cause_Changed",
                    "Effect_Changed",
                )

            consensus_list.append(
                {
                    "perturbation_id": pert_id,
                    "consensus_causal_label": consensus_label,
                    "is_distorted": is_distorted,
                    "mean_naturalness": mean_naturalness,
                    "is_unanimous": is_unanimous,
                    "annotators_count": len(recs),
                }
            )

        return consensus_list

    def evaluate(
        self,
        human_annotations: List[Union[AnnotationRecord, Dict[str, Any]]],
        automated_metrics: List[Dict[str, Any]],
        binary_mapping_enabled: bool = True,
    ) -> CorrelationResult:
        """Evaluate correlations and metric sensitivity between human consensus and automated metrics.

        Args:
            human_annotations: List of human annotation records or dicts.
            automated_metrics: List of automated metric records (containing perturbation_id and metric scores).
            binary_mapping_enabled: If False, report ROC-AUC as unavailable due to undefined decision boundary.

        Returns:
            CorrelationResult dataclass instance.
        """
        total_human_records = len(human_annotations)
        total_metric_records = len(automated_metrics)

        excluded_records: List[Dict[str, Any]] = []
        warnings: List[str] = []

        consensus_records = self.aggregate_human_consensus(human_annotations)
        consensus_map = {r["perturbation_id"]: r for r in consensus_records}

        # Track duplicates in metric records
        seen_metric_ids: Set[str] = set()
        duplicate_metric_ids: Set[str] = set()
        metrics_map: Dict[str, Dict[str, Any]] = {}

        for m_idx, m_rec in enumerate(automated_metrics):
            if not isinstance(m_rec, dict) or "perturbation_id" not in m_rec:
                excluded_records.append(
                    {
                        "record_index": m_idx,
                        "perturbation_id": m_rec.get("perturbation_id") if isinstance(m_rec, dict) else None,
                        "reason": "missing_metric_score",
                    }
                )
                continue

            pid = str(m_rec["perturbation_id"]).strip()
            if pid in seen_metric_ids:
                duplicate_metric_ids.add(pid)
                excluded_records.append(
                    {
                        "record_index": m_idx,
                        "perturbation_id": pid,
                        "reason": "duplicate_identifier",
                    }
                )
                continue

            seen_metric_ids.add(pid)
            metrics_map[pid] = m_rec

        if duplicate_metric_ids:
            warnings.append(
                f"Detected {len(duplicate_metric_ids)} duplicate metric perturbation_ids."
            )

        # Identification of matched and unmatched IDs
        human_pids = set(consensus_map.keys())
        metric_pids = set(metrics_map.keys())

        matched_pids = sorted(list(human_pids & metric_pids))
        unmatched_human_pids = sorted(list(human_pids - metric_pids))
        unmatched_metric_pids = sorted(list(metric_pids - human_pids))

        for pid in unmatched_human_pids:
            excluded_records.append({"perturbation_id": pid, "reason": "missing_metric_score"})

        for pid in unmatched_metric_pids:
            excluded_records.append({"perturbation_id": pid, "reason": "missing_human_judgment"})

        matched_count = len(matched_pids)

        if matched_count == 0:
            warnings.append("No matched items found between human annotations and automated metrics.")
            return CorrelationResult(
                total_human_records=total_human_records,
                total_metric_records=total_metric_records,
                matched_records_count=0,
                unmatched_human_count=len(unmatched_human_pids),
                unmatched_metric_count=len(unmatched_metric_pids),
                excluded_records=excluded_records,
                metric_coverage={},
                pearson_correlations={},
                spearman_correlations={},
                roc_auc_results={},
                binary_classification_metrics={},
                category_sensitivity={},
                data_quality_warnings=warnings,
            )

        # Detect candidate metric score keys
        sample_m = metrics_map[matched_pids[0]]
        candidate_metric_keys = [
            k
            for k, v in sample_m.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("line_number", "id", "document_id")
        ]

        metric_coverage = {k: matched_count for k in candidate_metric_keys}

        pearson_results: Dict[str, Dict[str, Any]] = {}
        spearman_results: Dict[str, Dict[str, Any]] = {}
        roc_auc_results: Dict[str, Dict[str, Any]] = {}
        binary_metrics: Dict[str, Dict[str, Any]] = {}

        # Separate matched items into valid binary distortion target vs unresolved disagreements
        valid_dist_pids: List[str] = []
        disagreed_pids: List[str] = []

        for pid in matched_pids:
            c_item = consensus_map[pid]
            if c_item.get("is_distorted") is None or c_item.get("consensus_causal_label") == "DISAGREED":
                disagreed_pids.append(pid)
                excluded_records.append(
                    {"perturbation_id": pid, "reason": "unresolved_annotator_disagreement"}
                )
            else:
                valid_dist_pids.append(pid)

        if disagreed_pids:
            warnings.append(
                f"Excluded {len(disagreed_pids)} item(s) from binary distortion analysis due to unresolved annotator disagreement."
            )

        human_is_distorted = [1 if consensus_map[pid]["is_distorted"] else 0 for pid in valid_dist_pids]
        human_naturalness = [consensus_map[pid]["mean_naturalness"] for pid in matched_pids]

        for m_key in candidate_metric_keys:
            is_faithfulness = m_key in FAITHFULNESS_METRIC_KEYS or "score" in m_key.lower() or "f1" in m_key.lower()
            m_values_all = [float(metrics_map[pid][m_key]) for pid in matched_pids]
            m_values_dist = [float(metrics_map[pid][m_key]) for pid in valid_dist_pids]

            # Pearson r
            pearson_results[f"{m_key}_vs_human_distortion"] = compute_pearson_r(human_is_distorted, m_values_dist)
            pearson_results[f"{m_key}_vs_human_naturalness"] = compute_pearson_r(human_naturalness, m_values_all)

            # Spearman rho
            spearman_results[f"{m_key}_vs_human_distortion"] = compute_spearman_rho(human_is_distorted, m_values_dist)
            spearman_results[f"{m_key}_vs_human_naturalness"] = compute_spearman_rho(human_naturalness, m_values_all)

            # ROC-AUC
            roc_auc_res = compute_roc_auc(
                human_is_distorted,
                m_values_dist,
                is_faithfulness_metric=is_faithfulness,
                binary_mapping_enabled=binary_mapping_enabled,
            )
            roc_auc_results[m_key] = roc_auc_res

            # Binary classification metrics (using mean score of valid distortion set as threshold)
            if len(m_values_dist) > 0:
                m_mean = sum(m_values_dist) / len(m_values_dist)
                pred_distorted = [1 if (val < m_mean if is_faithfulness else val >= m_mean) else 0 for val in m_values_dist]

                tp = sum(1 for h, p in zip(human_is_distorted, pred_distorted) if h == 1 and p == 1)
                fp = sum(1 for h, p in zip(human_is_distorted, pred_distorted) if h == 0 and p == 1)
                fn = sum(1 for h, p in zip(human_is_distorted, pred_distorted) if h == 1 and p == 0)
                tn = sum(1 for h, p in zip(human_is_distorted, pred_distorted) if h == 0 and p == 0)

                sensitivity = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
                specificity = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0
                precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
                f1 = round(2 * precision * sensitivity / (precision + sensitivity), 4) if (precision + sensitivity) > 0 else 0.0
            else:
                tp = fp = fn = tn = 0
                sensitivity = specificity = precision = f1 = 0.0

            binary_metrics[m_key] = {
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "sensitivity": sensitivity,
                "specificity": specificity,
                "precision": precision,
                "f1_score": f1,
                "score_direction": "faithfulness_lower_is_distorted" if is_faithfulness else "distortion_higher_is_distorted",
            }

        # Category sensitivity descriptive breakdown
        category_sensitivity: Dict[str, Dict[str, Any]] = {}
        approved_labels = sorted(list(APPROVED_CAUSAL_LABELS))

        for cat in approved_labels:
            cat_pids = [pid for pid in matched_pids if consensus_map[pid]["consensus_causal_label"] == cat]
            cat_count = len(cat_pids)

            cat_stats: Dict[str, Any] = {"count": cat_count, "is_present": cat_count > 0}

            for m_key in candidate_metric_keys:
                if cat_count > 0:
                    cat_m_vals = [float(metrics_map[pid][m_key]) for pid in cat_pids]
                    cat_stats[m_key] = compute_descriptive_stats(cat_m_vals)
                else:
                    cat_stats[m_key] = compute_descriptive_stats([])

            category_sensitivity[cat] = cat_stats

        logger.info(
            f"Correlation evaluation complete: {matched_count} matched items, {len(unmatched_human_pids)} unmatched human, {len(unmatched_metric_pids)} unmatched metric."
        )

        return CorrelationResult(
            total_human_records=total_human_records,
            total_metric_records=total_metric_records,
            matched_records_count=matched_count,
            unmatched_human_count=len(unmatched_human_pids),
            unmatched_metric_count=len(unmatched_metric_pids),
            excluded_records=excluded_records,
            metric_coverage=metric_coverage,
            pearson_correlations=pearson_results,
            spearman_correlations=spearman_results,
            roc_auc_results=roc_auc_results,
            binary_classification_metrics=binary_metrics,
            category_sensitivity=category_sensitivity,
            data_quality_warnings=warnings,
        )
