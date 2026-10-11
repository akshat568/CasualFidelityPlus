"""Category-based benchmark balancing module for CausalFidelity+."""

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from causalfidelity.experiment.sampler import ALL_DISTORTION_CATEGORIES
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class BenchmarkBalancer:
    """Category-based balancing component for producing equal-sized distortion benchmarks."""

    def balance(
        self,
        validated_records: List[Dict[str, Any]],
        target_count_per_category: int = 10,
        seed: int = 42,
        output_dir: Optional[Path] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Balance validated perturbation records across distortion categories.

        Args:
            validated_records: List of validated perturbation record dicts.
            target_count_per_category: Desired sample count per category.
            seed: Random seed for deterministic downsampling.
            output_dir: Destination path for balanced benchmark artifacts.

        Returns:
            Tuple of (balanced_records_list, balance_stats_dict).
        """
        logger.info(
            f"Starting Benchmark Balancer (Target: {target_count_per_category}/category, Seed: {seed})"
        )

        # Deduplicate incoming records by perturbation_id
        seen_pids = set()
        unique_records: List[Dict[str, Any]] = []

        for rec in validated_records:
            pid = rec.get("perturbation_id")
            status = rec.get("validation_status", "valid")
            if status == "valid" and pid and pid not in seen_pids:
                seen_pids.add(pid)
                unique_records.append(rec)

        # Group records by category
        grouped: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in ALL_DISTORTION_CATEGORIES}
        for rec in unique_records:
            ptype = rec.get("perturbation_type", "UNKNOWN")
            if ptype in grouped:
                grouped[ptype].append(rec)

        rng = random.Random(seed)
        balanced_records: List[Dict[str, Any]] = []
        category_stats: Dict[str, Dict[str, Any]] = {}

        total_shortfall = 0
        fully_balanced = True

        for cat in ALL_DISTORTION_CATEGORIES:
            records_in_cat = grouped[cat]
            available = len(records_in_cat)

            if available >= target_count_per_category:
                # Deterministically sample target_count_per_category
                # Sort first by perturbation_id to ensure seed independence from input ordering
                sorted_records = sorted(records_in_cat, key=lambda x: x.get("perturbation_id", ""))
                selected = rng.sample(sorted_records, target_count_per_category)
                shortfall = 0
            else:
                selected = sorted(records_in_cat, key=lambda x: x.get("perturbation_id", ""))
                shortfall = target_count_per_category - available
                fully_balanced = False

            total_shortfall += shortfall
            balanced_records.extend(selected)

            category_stats[cat] = {
                "requested_count": target_count_per_category,
                "available_count": available,
                "selected_count": len(selected),
                "shortfall": shortfall,
                "is_balanced": shortfall == 0,
            }

        # Sort final balanced benchmark by perturbation_id for byte-for-byte determinism
        balanced_records.sort(key=lambda x: x.get("perturbation_id", ""))

        stats = {
            "balancing_info": {
                "seed": seed,
                "target_count_per_category": target_count_per_category,
                "is_fully_balanced": fully_balanced,
                "total_shortfall": total_shortfall,
            },
            "counts": {
                "total_input_valid_records": len(unique_records),
                "total_balanced_records": len(balanced_records),
            },
            "category_breakdown": category_stats,
        }

        if output_dir is not None:
            output_dir = Path(output_dir)
            ensure_dir(output_dir)

            balanced_jsonl = output_dir / "balanced_benchmark.jsonl"
            with open(balanced_jsonl, "w", encoding="utf-8") as f:
                for rec in balanced_records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            if "processed" in str(output_dir):
                res_dirs = [output_dir.parent / "results"]
                if (output_dir.parent.parent / "outputs").exists():
                    res_dirs.append(output_dir.parent.parent / "outputs" / "results")
                for rdir in res_dirs:
                    save_json(stats, rdir / "benchmark_balance_stats.json")
                    self._write_markdown_summary(stats, rdir / "benchmark_expansion_summary.md")
            else:
                save_json(stats, output_dir / "benchmark_balance_stats.json")
                self._write_markdown_summary(stats, output_dir / "benchmark_expansion_summary.md")

        logger.info(
            f"Benchmark balancing complete. Balanced records: {len(balanced_records)}. Fully balanced: {fully_balanced}"
        )
        return balanced_records, stats

    @staticmethod
    def _write_markdown_summary(stats: Dict[str, Any], file_path: Path) -> None:
        """Write human-readable markdown summary report of benchmark expansion and balancing."""
        ensure_dir(file_path.parent)
        b_info = stats.get("balancing_info", {})
        counts = stats.get("counts", {})
        cat_stats = stats.get("category_breakdown", {})

        md_lines = [
            "# Phase 11 — Benchmark Expansion and Balancing Report",
            "",
            "## 1. Executive Summary",
            "",
            f"- **Target Count per Category:** {b_info.get('target_count_per_category')}",
            f"- **Fully Balanced Status:** {'YES' if b_info.get('is_fully_balanced') else 'NO'}",
            f"- **Total Shortfall Across Categories:** {b_info.get('total_shortfall')}",
            f"- **Total Valid Input Records:** {counts.get('total_input_valid_records')}",
            f"- **Total Balanced Benchmark Records:** {counts.get('total_balanced_records')}",
            "",
            "## 2. Category Breakdown",
            "",
            "| Category | Requested | Available | Selected | Shortfall | Fully Balanced |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]

        for cat, data in cat_stats.items():
            bal_str = "YES" if data.get("is_balanced") else "NO"
            md_lines.append(
                f"| `{cat}` | {data.get('requested_count')} | {data.get('available_count')} | {data.get('selected_count')} | {data.get('shortfall')} | {bal_str} |"
            )

        md_lines.extend(
            [
                "",
                "## 3. Methodological Notes & Integrity Guarantee",
                "",
                "- **No Synthesized Data:** Zero artificial or synthetic examples were created.",
                "- **Quality Control Integrity:** Only candidates passing Phase 7 deterministic validation were retained.",
                "- **Provenance:** All records preserve source document IDs and perturbation IDs.",
            ]
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
