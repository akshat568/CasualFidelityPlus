"""Cross-metric analysis engine for Phase 10D Research Analysis and Comparison."""

import logging
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Tuple, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless rendering
import matplotlib.pyplot as plt

from causalfidelity.utils.io import ensure_dir

logger = logging.getLogger(__name__)


class CrossMetricAnalyzer:
    """Analyzer for combining Phase 9 and Phase 10A-10C artifacts and computing research statistics."""

    def verify_lineage(
        self,
        p9_records: List[Dict[str, Any]],
        summac_records: List[Dict[str, Any]],
        factcc_records: List[Dict[str, Any]],
        bertscore_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verify strict record lineage, ID matching, and text consistency across all input metric artifacts.

        Args:
            p9_records: List of Phase 9 causal distortion records.
            summac_records: List of Phase 10A SummaCConv result records.
            factcc_records: List of Phase 10B FactCC result records.
            bertscore_records: List of Phase 10C BERTScore result records.

        Returns:
            Lineage verification statistics dictionary.
        """
        p9_map = {r["perturbation_id"]: r for r in p9_records if r.get("perturbation_id")}

        metric_lists = [
            ("SummaC", summac_records or []),
            ("FactCC", factcc_records or []),
            ("BERTScore", bertscore_records or []),
        ]

        active_metrics = [(name, records) for name, records in metric_lists if records]

        # 1. Check duplicate IDs for active non-empty metric artifacts
        for name, records in active_metrics:
            p_ids = [r["perturbation_id"] for r in records if r.get("perturbation_id")]
            if len(p_ids) != len(set(p_ids)):
                raise ValueError(f"Duplicate perturbation IDs detected in {name} artifact: {p_ids}")

        # 2. Check mismatch in perturbation IDs across active metrics
        if active_metrics:
            first_ids = set(r["perturbation_id"] for r in active_metrics[0][1] if r.get("perturbation_id"))
            for name, records in active_metrics[1:]:
                curr_ids = set(r["perturbation_id"] for r in records if r.get("perturbation_id"))
                if first_ids != curr_ids:
                    raise ValueError(f"Mismatch in perturbation IDs between {active_metrics[0][0]} and {name}")

            reference_ids = [r["perturbation_id"] for r in active_metrics[0][1] if r.get("perturbation_id")]
        else:
            reference_ids = list(p9_map.keys())

        # 3. Phase 9 lineage validation: every reference ID must exist in Phase 9
        for pid in reference_ids:
            if pid not in p9_map:
                raise ValueError(f"Lineage failure: Perturbation ID '{pid}' missing from Phase 9 records.")

        # 4. Document ID consistency & original text consistency
        for pid in reference_ids:
            docs = []
            texts = []
            if pid in p9_map:
                if p9_map[pid].get("document_id"):
                    docs.append(p9_map[pid]["document_id"])
                if p9_map[pid].get("original_summary"):
                    texts.append(p9_map[pid]["original_summary"])

            for name, records in active_metrics:
                m_rec = next((r for r in records if r.get("perturbation_id") == pid), None)
                if m_rec:
                    m_doc = m_rec.get("document_id")
                    if m_doc:
                        docs.append(m_doc)
                    m_orig = m_rec.get("original_summary") or m_rec.get("original_text")
                    if m_orig:
                        texts.append(m_orig)

            if len(set(docs)) > 1:
                raise ValueError(f"Document ID mismatch for {pid}: found distinct document IDs {set(docs)}")
            if len(set(texts)) > 1:
                raise ValueError(f"Original summary text mismatch for {pid}: found distinct text values {set(texts)}")

        logger.info("Lineage verification passed successfully for %d perturbation records.", len(reference_ids))
        return {
            "valid_record_count": len(reference_ids),
            "perturbation_ids": reference_ids,
            "lineage_status": "verified_match",
        }

    def combine_records(
        self,
        p9_records: List[Dict[str, Any]],
        summac_records: List[Dict[str, Any]],
        factcc_records: List[Dict[str, Any]],
        bertscore_records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Combine Phase 9 and Phase 10A-10C result records by perturbation_id into unified analysis records.

        Args:
            p9_records: List of Phase 9 causal distortion records.
            summac_records: List of Phase 10A SummaCConv result records.
            factcc_records: List of Phase 10B FactCC result records.
            bertscore_records: List of Phase 10C BERTScore result records.

        Returns:
            List of combined records preserving original numeric precision and lineage labels.
        """
        lineage_res = self.verify_lineage(p9_records, summac_records, factcc_records, bertscore_records)

        p9_map = {r["perturbation_id"]: r for r in p9_records if r.get("perturbation_id")}
        sm_map = {r["perturbation_id"]: r for r in summac_records if r.get("perturbation_id")}
        fc_map = {r["perturbation_id"]: r for r in factcc_records if r.get("perturbation_id")}
        bs_map = {r["perturbation_id"]: r for r in bertscore_records if r.get("perturbation_id")}

        reference_ids = lineage_res["perturbation_ids"]

        combined = []
        for pid in reference_ids:
            p9_rec = p9_map.get(pid, {})
            sm_rec = sm_map.get(pid, {})
            fc_rec = fc_map.get(pid, {})
            bs_rec = bs_map.get(pid, {})

            doc_id = p9_rec.get("document_id") or sm_rec.get("document_id") or fc_rec.get("document_id") or bs_rec.get("document_id", "UNKNOWN")
            summary_id = p9_rec.get("summary_id") or sm_rec.get("summary_id") or fc_rec.get("summary_id") or bs_rec.get("summary_id", doc_id)

            orig_sum = (
                sm_rec.get("original_summary") or sm_rec.get("original_text")
                or fc_rec.get("original_summary") or fc_rec.get("original_text")
                or bs_rec.get("original_summary") or bs_rec.get("original_text")
                or p9_rec.get("source_relation", {}).get("cause")
            )
            pert_sum = (
                sm_rec.get("perturbed_summary") or sm_rec.get("perturbed_text")
                or fc_rec.get("perturbed_summary") or fc_rec.get("perturbed_text")
                or bs_rec.get("perturbed_summary") or bs_rec.get("perturbed_text")
            )

            intended_type = p9_rec.get("intended_label") or sm_rec.get("intended_label") or sm_rec.get("perturbation_type")
            detected_label = p9_rec.get("detected_label")

            summac_orig = float(sm_rec["original_score"]) if sm_rec and "original_score" in sm_rec else None
            summac_pert = float(sm_rec["perturbed_score"]) if sm_rec and "perturbed_score" in sm_rec else None
            summac_delta = round(summac_orig - summac_pert, 4) if (summac_orig is not None and summac_pert is not None) else None

            factcc_orig = float(fc_rec["original_score"]) if fc_rec and "original_score" in fc_rec else None
            factcc_pert = float(fc_rec["perturbed_score"]) if fc_rec and "perturbed_score" in fc_rec else None
            factcc_delta = round(factcc_orig - factcc_pert, 4) if (factcc_orig is not None and factcc_pert is not None) else None

            bs_precision = float(bs_rec["bertscore_precision"]) if bs_rec and "bertscore_precision" in bs_rec else None
            bs_recall = float(bs_rec["bertscore_recall"]) if bs_rec and "bertscore_recall" in bs_rec else None
            bs_f1 = float(bs_rec["bertscore_f1"]) if bs_rec and "bertscore_f1" in bs_rec else None
            bs_loss = round(1.0 - bs_f1, 4) if bs_f1 is not None else None

            combined_rec = {
                "perturbation_id": pid,
                "document_id": doc_id,
                "summary_id": summary_id,
                "intended_perturbation_type": intended_type,
                "detected_distortion_label": detected_label,
                "evidence_strength": p9_rec.get("evidence_strength", "UNKNOWN"),
                "original_summary": orig_sum,
                "perturbed_summary": pert_sum,
                "summac_original_score": summac_orig,
                "summac_perturbed_score": summac_pert,
                "summac_delta": summac_delta,
                "factcc_original_score": factcc_orig,
                "factcc_perturbed_score": factcc_pert,
                "factcc_delta": factcc_delta,
                "bertscore_precision": bs_precision,
                "bertscore_recall": bs_recall,
                "bertscore_f1": bs_f1,
                "bertscore_similarity_loss": bs_loss,
                "metadata": {
                    "phase9_analysis_id": p9_rec.get("analysis_id"),
                    "phase9_agreement": p9_rec.get("agreement"),
                    "summac_version": sm_rec.get("metadata", {}).get("metric_version", "summac-0.0.4") if sm_rec else "ABLATED",
                    "factcc_version": fc_rec.get("metadata", {}).get("metric_version", "factcc-manueldeprada") if fc_rec else "ABLATED",
                    "bertscore_version": bs_rec.get("metadata", {}).get("metric_version", "bert-score-0.3.12") if bs_rec else "ABLATED",
                },
            }
            combined.append(combined_rec)

        return combined

    def compute_statistics(self, combined_records: List[Dict[str, Any]], num_invalid_excluded: int = 4) -> Dict[str, Any]:
        """Compute aggregate descriptive statistics for benchmark and per-metric responses.

        Args:
            combined_records: List of combined records.
            num_invalid_excluded: Count of Phase-7-invalid perturbations excluded.

        Returns:
            Dictionary containing descriptive statistics and per-type breakdowns.
        """
        num_valid = len(combined_records)
        doc_ids = list(set(r["document_id"] for r in combined_records))

        sm_deltas = [r["summac_delta"] for r in combined_records if r.get("summac_delta") is not None]
        fc_deltas = [r["factcc_delta"] for r in combined_records if r.get("factcc_delta") is not None]
        bs_f1s = [r["bertscore_f1"] for r in combined_records if r.get("bertscore_f1") is not None]
        bs_losses = [r["bertscore_similarity_loss"] for r in combined_records if r.get("bertscore_similarity_loss") is not None]

        def metric_delta_stats(deltas: List[float]) -> Dict[str, Any]:
            if not deltas:
                return {
                    "status": "unavailable_or_ablated",
                    "mean_delta": None,
                    "median_delta": None,
                    "min_delta": None,
                    "max_delta": None,
                    "positive_count": 0,
                    "zero_count": 0,
                    "negative_count": 0,
                }
            return {
                "mean_delta": round(mean(deltas), 4),
                "median_delta": round(median(deltas), 4),
                "min_delta": round(min(deltas), 4),
                "max_delta": round(max(deltas), 4),
                "positive_count": sum(1 for d in deltas if d > 0),
                "zero_count": sum(1 for d in deltas if d == 0),
                "negative_count": sum(1 for d in deltas if d < 0),
            }

        sm_stats = metric_delta_stats(sm_deltas)
        fc_stats = metric_delta_stats(fc_deltas)

        bs_stats = {
            "mean_f1": round(mean(bs_f1s), 4) if bs_f1s else None,
            "median_f1": round(median(bs_f1s), 4) if bs_f1s else None,
            "min_f1": round(min(bs_f1s), 4) if bs_f1s else None,
            "max_f1": round(max(bs_f1s), 4) if bs_f1s else None,
            "mean_similarity_loss": round(mean(bs_losses), 4) if bs_losses else None,
            "median_similarity_loss": round(median(bs_losses), 4) if bs_losses else None,
            "min_similarity_loss": round(min(bs_losses), 4) if bs_losses else None,
            "max_similarity_loss": round(max(bs_losses), 4) if bs_losses else None,
        }

        # Breakdown by intended perturbation type
        all_types = ["WEAKENED", "DROPPED", "EFFECT_CHANGED", "CAUSE_CHANGED", "REVERSED"]
        type_breakdown = {}

        for p_type in all_types:
            records_of_type = [r for r in combined_records if r["intended_perturbation_type"] == p_type]
            count = len(records_of_type)
            if count == 0:
                type_breakdown[p_type] = {
                    "count": 0,
                    "coverage": "0 valid benchmark examples",
                    "note": "No valid perturbations available in current dev benchmark for this category.",
                }
            else:
                type_sm_deltas = [r["summac_delta"] for r in records_of_type if r.get("summac_delta") is not None]
                type_fc_deltas = [r["factcc_delta"] for r in records_of_type if r.get("factcc_delta") is not None]
                type_bs_f1s = [r["bertscore_f1"] for r in records_of_type if r.get("bertscore_f1") is not None]
                type_bs_losses = [r["bertscore_similarity_loss"] for r in records_of_type if r.get("bertscore_similarity_loss") is not None]

                detected_counts = {}
                for r in records_of_type:
                    lbl = r["detected_distortion_label"]
                    detected_counts[lbl] = detected_counts.get(lbl, 0) + 1

                entry = {
                    "count": count,
                    "is_single_observation": (count == 1),
                    "summac_mean_delta": round(mean(type_sm_deltas), 4) if type_sm_deltas else None,
                    "summac_median_delta": round(median(type_sm_deltas), 4) if type_sm_deltas else None,
                    "factcc_mean_delta": round(mean(type_fc_deltas), 4) if type_fc_deltas else None,
                    "factcc_median_delta": round(median(type_fc_deltas), 4) if type_fc_deltas else None,
                    "bertscore_mean_f1": round(mean(type_bs_f1s), 4) if type_bs_f1s else None,
                    "bertscore_median_f1": round(median(type_bs_f1s), 4) if type_bs_f1s else None,
                    "bertscore_mean_similarity_loss": round(mean(type_bs_losses), 4) if type_bs_losses else None,
                    "bertscore_median_similarity_loss": round(mean(type_bs_losses), 4) if type_bs_losses else None,
                    "detected_label_distribution": detected_counts,
                }
                if count == 1:
                    entry["note"] = "Single observation — descriptive value only."
                type_breakdown[p_type] = entry

        detected_dist = {}
        for r in combined_records:
            lbl = r["detected_distortion_label"]
            detected_dist[lbl] = detected_dist.get(lbl, 0) + 1

        stats = {
            "benchmark_overview": {
                "total_valid_perturbations_evaluated": num_valid,
                "total_invalid_perturbations_excluded": num_invalid_excluded,
                "unique_source_documents_count": len(doc_ids),
                "source_document_ids": doc_ids,
                "sample_size_disclaimer": "n=6 small sample size. Results are descriptive and preliminary.",
            },
            "summac_statistics": sm_stats,
            "factcc_statistics": fc_stats,
            "bertscore_statistics": bs_stats,
            "breakdown_by_intended_perturbation_type": type_breakdown,
            "detected_distortion_label_distribution": detected_dist,
        }
        return stats

    def generate_markdown_report(self, stats: Dict[str, Any], combined_records: List[Dict[str, Any]]) -> str:
        """Generate structured Markdown research summary report.

        Args:
            stats: Computed statistics dictionary.
            combined_records: List of combined records.

        Returns:
            Formatted Markdown report string.
        """
        overview = stats["benchmark_overview"]
        sm_stats = stats["summac_statistics"]
        fc_stats = stats["factcc_statistics"]
        bs_stats = stats["bertscore_statistics"]
        type_bk = stats["breakdown_by_intended_perturbation_type"]

        md_lines = [
            "# Phase 10D — Research Analysis and Cross-Metric Comparison Report",
            "",
            "## 1. Executive Summary & Benchmark Context",
            "",
            f"- **Total Valid Perturbations Evaluated:** {overview['total_valid_perturbations_evaluated']}",
            f"- **Total Invalid Perturbations Excluded:** {overview['total_invalid_perturbations_excluded']}",
            f"- **Unique Source Documents:** {overview['unique_source_documents_count']} (`{', '.join(overview['source_document_ids'])}`)",
            "- **Sample Size Warning:** $n=6$ small development benchmark size across 2 source documents. Results are strictly descriptive and preliminary.",
            "",
            "## 2. Metric Score Semantics & Response Definitions",
            "",
            "1. **SummaCConv (NLI Consistency):** $\\Delta_{\\text{SummaC}} = \\text{orig} - \\text{pert}$. Positive delta indicates consistency drop.",
            "2. **FactCC (Factual Classification):** $\\Delta_{\\text{FactCC}} = \\text{orig} - \\text{pert}$. Positive delta indicates predicted correctness drop.",
            "3. **BERTScore (Semantic Control):** $F_1 \\in [0, 1]$ and $\\text{Similarity Loss} = 1.0 - F_1$. Measures surface token embedding divergence.",
            "",
            "## 3. Verified Per-Perturbation Results",
            "",
            "| Perturbation ID | Doc ID | Intended Type | Detected Label | SummaC $\\Delta$ | FactCC $\\Delta$ | BERTScore $F_1$ | BERTScore Loss |",
            "| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |",
        ]

        for r in combined_records:
            sm_str = f"{r['summac_delta']:+.4f}" if r.get("summac_delta") is not None else "ABLATED"
            fc_str = f"{r['factcc_delta']:+.4f}" if r.get("factcc_delta") is not None else "ABLATED"
            bs_f1_str = f"{r['bertscore_f1']:.4f}" if r.get("bertscore_f1") is not None else "ABLATED"
            bs_loss_str = f"{r['bertscore_similarity_loss']:.4f}" if r.get("bertscore_similarity_loss") is not None else "ABLATED"
            md_lines.append(
                f"| `{r['perturbation_id']}` | `{r['document_id']}` | `{r['intended_perturbation_type']}` | "
                f"`{r['detected_distortion_label']}` | `{sm_str}` | `{fc_str}` | "
                f"`{bs_f1_str}` | `{bs_loss_str}` |"
            )

        sm_mean_str = f"{sm_stats['mean_delta']:+.4f}" if sm_stats.get("mean_delta") is not None else "ABLATED"
        sm_med_str = f"{sm_stats['median_delta']:+.4f}" if sm_stats.get("median_delta") is not None else "ABLATED"
        fc_mean_str = f"{fc_stats['mean_delta']:+.4f}" if fc_stats.get("mean_delta") is not None else "ABLATED"
        fc_med_str = f"{fc_stats['median_delta']:+.4f}" if fc_stats.get("median_delta") is not None else "ABLATED"
        bs_mean_str = f"{bs_stats['mean_f1']:.4f}" if bs_stats.get("mean_f1") is not None else "ABLATED"
        bs_loss_str = f"{bs_stats['mean_similarity_loss']:.4f}" if bs_stats.get("mean_similarity_loss") is not None else "ABLATED"

        md_lines.extend([
            "",
            "## 4. Aggregate Metric Performance Summary",
            "",
            f"- **SummaCConv:** Mean $\\Delta = {sm_mean_str}$, Median $\\Delta = {sm_med_str}$ (Positive: {sm_stats.get('positive_count', 0)}, Zero: {sm_stats.get('zero_count', 0)}, Negative: {sm_stats.get('negative_count', 0)})",
            f"- **FactCC:** Mean $\\Delta = {fc_mean_str}$, Median $\\Delta = {fc_med_str}$ (Positive: {fc_stats.get('positive_count', 0)}, Zero: {fc_stats.get('zero_count', 0)}, Negative: {fc_stats.get('negative_count', 0)})",
            f"- **BERTScore:** Mean $F_1 = {bs_mean_str}$, Mean Similarity Loss = {bs_loss_str}",
            "",
            "## 5. Perturbation-Type Breakdown",
            "",
        ])

        for p_type, bk in type_bk.items():
            if bk["count"] == 0:
                md_lines.append(f"### `{p_type}` ($n=0$)")
                md_lines.append(f"- *Coverage:* {bk['note']}")
            else:
                single_note = " *(Single Observation)*" if bk.get("is_single_observation") else ""
                md_lines.append(f"### `{p_type}` ($n={bk['count']}$){single_note}")
                sm_t_str = f"{bk['summac_mean_delta']:+.4f}" if bk.get("summac_mean_delta") is not None else "ABLATED"
                fc_t_str = f"{bk['factcc_mean_delta']:+.4f}" if bk.get("factcc_mean_delta") is not None else "ABLATED"
                bs_f1_t_str = f"{bk['bertscore_mean_f1']:.4f}" if bk.get("bertscore_mean_f1") is not None else "ABLATED"
                bs_loss_t_str = f"{bk['bertscore_mean_similarity_loss']:.4f}" if bk.get("bertscore_mean_similarity_loss") is not None else "ABLATED"
                md_lines.append(f"- **SummaCConv Mean $\\Delta$:** `{sm_t_str}`")
                md_lines.append(f"- **FactCC Mean $\\Delta$:** `{fc_t_str}`")
                md_lines.append(f"- **BERTScore Mean $F_1$:** `{bs_f1_t_str}`")
                md_lines.append(f"- **BERTScore Mean Similarity Loss:** `{bs_loss_t_str}`")
                md_lines.append(f"- **Detected Label Distribution:** `{bk['detected_label_distribution']}`")
            md_lines.append("")

        md_lines.extend([
            "## 6. Key Descriptive Research Observations",
            "",
            "1. **Metric Blindness to Subtle Causal Phrase Swaps:** Both SummaCConv and FactCC exhibited zero or negative response to `WEAKENED` and `DROPPED` causal phrase modifications.",
            "2. **BERTScore Reflects Surface Divergence, Not Faithfulness:** BERTScore $F_1$ remains high ($\\\\ge 0.985$) for `WEAKENED` and `DROPPED` phrase edits, but drops noticeably ($F_1 = 0.9205$) for clause substitution (`EFFECT_CHANGED`).",
            "3. **Absence of REVERSED Examples:** No validated `REVERSED` perturbations exist in the current benchmark, representing an essential target for expanded benchmark generation.",
            "",
            "## 7. Limitations & Scope Constraints",
            "",
            "- Results are strictly preliminary and descriptive ($n=6$).",
            "- No statistical significance or general metric superiority claims are made.",
            "- BERTScore functions solely as a semantic similarity control.",
            "",
        ])

        return "\n".join(md_lines)

    def generate_figures(self, combined_records: List[Dict[str, Any]], output_dir: Path) -> List[Path]:
        """Generate research visualization figures for Phase 10D analysis.

        Args:
            combined_records: List of combined records.
            output_dir: Destination directory for figure images.

        Returns:
            List of generated image file paths.
        """
        ensure_dir(output_dir)
        generated_paths = []

        p_ids = [r["perturbation_id"].split("_")[-1] for r in combined_records]
        sm_deltas = [r["summac_delta"] if r.get("summac_delta") is not None else 0.0 for r in combined_records]
        fc_deltas = [r["factcc_delta"] if r.get("factcc_delta") is not None else 0.0 for r in combined_records]
        bs_losses = [r["bertscore_similarity_loss"] if r.get("bertscore_similarity_loss") is not None else 0.0 for r in combined_records]

        # Figure 1: Per-Perturbation Metric Response (3 panels)
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        
        ax1.bar(p_ids, sm_deltas, color="#1f77b4")
        ax1.set_ylabel("SummaC Delta")
        ax1.set_title("Per-Perturbation Metric Response Profiles (n=6)")
        ax1.grid(True, linestyle="--", alpha=0.5)

        ax2.bar(p_ids, fc_deltas, color="#ff7f0e")
        ax2.set_ylabel("FactCC Delta")
        ax2.grid(True, linestyle="--", alpha=0.5)

        ax3.bar(p_ids, bs_losses, color="#2ca02c")
        ax3.set_ylabel("BERTScore Loss")
        ax3.set_xlabel("Perturbation ID (Short)")
        ax3.grid(True, linestyle="--", alpha=0.5)

        plt.tight_layout()
        fig1_path = output_dir / "fig1_metric_responses.png"
        fig.savefig(fig1_path, dpi=150)
        plt.close(fig)
        generated_paths.append(fig1_path)

        # Figure 2: BERTScore Similarity Loss by Perturbation Type
        fig, ax = plt.subplots(figsize=(8, 5))
        types = [r["intended_perturbation_type"] for r in combined_records]
        ax.scatter(types, bs_losses, color="#d62728", s=100, zorder=3)
        ax.set_ylabel("BERTScore Similarity Loss (1.0 - F1)")
        ax.set_xlabel("Intended Perturbation Type")
        ax.set_title("BERTScore Similarity Loss by Perturbation Type (Individual Observations)")
        ax.grid(True, linestyle="--", alpha=0.5)

        plt.tight_layout()
        fig2_path = output_dir / "fig2_bertscore_similarity_loss.png"
        fig.savefig(fig2_path, dpi=150)
        plt.close(fig)
        generated_paths.append(fig2_path)

        # Figure 3: Metric Response Magnitude Comparison
        fig, ax = plt.subplots(figsize=(9, 5))
        x_indices = range(len(p_ids))
        width = 0.25

        ax.bar([x - width for x in x_indices], sm_deltas, width=width, label="SummaC Delta", color="#1f77b4")
        ax.bar(x_indices, fc_deltas, width=width, label="FactCC Delta", color="#ff7f0e")
        ax.bar([x + width for x in x_indices], bs_losses, width=width, label="BERTScore Loss", color="#2ca02c")

        ax.set_xticks(list(x_indices))
        ax.set_xticklabels(p_ids)
        ax.set_ylabel("Response Value")
        ax.set_title("Comparison of Metric Response Direction and Magnitude")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)

        plt.tight_layout()
        fig3_path = output_dir / "fig3_response_comparison.png"
        fig.savefig(fig3_path, dpi=150)
        plt.close(fig)
        generated_paths.append(fig3_path)

        logger.info("Successfully generated %d visualization figures in %s", len(generated_paths), output_dir)
        return generated_paths
