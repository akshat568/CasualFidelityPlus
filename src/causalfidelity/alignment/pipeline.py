"""Phase 8 Summary Causal Extraction + Semantic Alignment Pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, List

from causalfidelity.alignment.embedder import SemanticEmbedder
from causalfidelity.alignment.matcher import CausalMatcher
from causalfidelity.alignment.schema import CausalAlignment, SummaryCausalRelation
from causalfidelity.alignment.scorer import CausalScorer
from causalfidelity.alignment.summary_extractor import SummaryCausalExtractor
from causalfidelity.alignment.validator import AlignmentValidator
from causalfidelity.causal.schema import CausalRelation, DocumentCausalRelations
from causalfidelity.config import AppConfig, load_config
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class AlignmentPipeline:
    """Pipeline orchestrating summary causal extraction, semantic embedding, candidate matching, and stats logging."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.align_cfg = config.alignment

        self.summary_extractor = SummaryCausalExtractor(
            confidence_default=config.causal_extraction.confidence_default
        )
        self.embedder = SemanticEmbedder(
            model_name=self.align_cfg.embedding_model,
            device=self.align_cfg.device,
        )
        self.scorer = CausalScorer(
            cause_weight=self.align_cfg.cause_weight,
            effect_weight=self.align_cfg.effect_weight,
            relation_weight=self.align_cfg.relation_weight,
        )
        self.matcher = CausalMatcher(
            embedder=self.embedder,
            scorer=self.scorer,
            cause_threshold=self.align_cfg.cause_threshold,
            effect_threshold=self.align_cfg.effect_threshold,
            overall_threshold=self.align_cfg.overall_threshold,
            ambiguity_margin=self.align_cfg.ambiguity_margin,
        )
        self.validator = AlignmentValidator()

    def load_source_relations(self, file_path: Path) -> List[CausalRelation]:
        """Load Phase 3 source causal relations from JSONL file."""
        source_relations: List[CausalRelation] = []
        if not file_path.exists():
            logger.warning(f"Source relations file not found at {file_path}")
            return source_relations

        with open(file_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if "relations" in data and isinstance(data["relations"], list):
                        doc_rels = DocumentCausalRelations.from_dict(data)
                        source_relations.extend(doc_rels.relations)
                    else:
                        rel = CausalRelation.from_dict(data)
                        source_relations.append(rel)
                except Exception as e:
                    logger.error(f"Error parsing line {line_idx} in {file_path}: {e}")

        # Ensure deterministic ordering
        source_relations.sort(key=lambda r: (r.document_id, r.relation_id))
        return source_relations

    def load_summary_inputs(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load Phase 5 summary inputs from JSONL file."""
        summaries: List[Dict[str, Any]] = []
        if not file_path.exists():
            logger.warning(f"Summary inputs file not found at {file_path}")
            return summaries

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    summaries.append(data)
                except Exception as e:
                    logger.error(f"Error parsing summary input line: {e}")

        # Ensure deterministic ordering
        summaries.sort(key=lambda s: (s.get("document_id", ""), s.get("summary_id", "")))
        return summaries

    def run(self) -> Dict[str, Any]:
        """Execute Phase 8 summary causal extraction and semantic alignment pipeline.

        Returns:
            Dictionary containing pipeline execution statistics and paths.
        """
        root_dir = self.config.paths.root_dir

        source_path = root_dir / self.align_cfg.input_source_relations_path
        summary_input_path = root_dir / self.align_cfg.input_summary_path
        output_sum_rel_path = root_dir / self.align_cfg.output_summary_relations_path
        output_align_path = root_dir / self.align_cfg.output_alignments_path
        stats_path = root_dir / self.align_cfg.stats_path
        sample_path = root_dir / self.align_cfg.sample_path

        # Create output directories
        output_sum_rel_path.parent.mkdir(parents=True, exist_ok=True)
        output_align_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        sample_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Loading source causal relations from {source_path}")
        source_relations = self.load_source_relations(source_path)

        logger.info(f"Loading summary inputs from {summary_input_path}")
        summary_records = self.load_summary_inputs(summary_input_path)

        # 1. Summary Causal Extraction
        logger.info("Extracting causal relations from summaries...")
        all_summary_relations: List[SummaryCausalRelation] = []
        summary_rels_by_doc: Dict[str, List[SummaryCausalRelation]] = {}

        for sum_rec in summary_records:
            sum_rels = self.summary_extractor.extract_from_summary(sum_rec)
            doc_id = sum_rec.get("document_id", "")
            if doc_id not in summary_rels_by_doc:
                summary_rels_by_doc[doc_id] = []
            summary_rels_by_doc[doc_id].extend(sum_rels)
            all_summary_relations.extend(sum_rels)

        # Write summary_causal_relations.jsonl deterministically
        self.validator.validate_all_summary_relations(all_summary_relations)
        with open(output_sum_rel_path, "w", encoding="utf-8") as f:
            for s_rel in all_summary_relations:
                f.write(json.dumps(s_rel.to_dict(), ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(all_summary_relations)} summary causal relations to {output_sum_rel_path}")

        # 2. Semantic Cause/Effect Alignment & Matching
        logger.info("Performing cause/effect semantic alignment...")
        alignments: List[CausalAlignment] = []

        # Track candidate summary relations that got matched to at least one source relation
        matched_summary_rel_ids = set()

        for src_rel in source_relations:
            doc_id = src_rel.document_id
            candidates = summary_rels_by_doc.get(doc_id, [])

            alignment = self.matcher.match_source_relation(src_rel, candidates)
            alignments.append(alignment)

            if alignment.summary_relation_id:
                matched_summary_rel_ids.add(alignment.summary_relation_id)

        # Validate alignments
        self.validator.validate_all_alignments(alignments)

        # Write causal_alignments.jsonl deterministically
        with open(output_align_path, "w", encoding="utf-8") as f:
            for align in alignments:
                f.write(json.dumps(align.to_dict(), ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(alignments)} causal alignments to {output_align_path}")

        # 3. Compute Summary Statistics
        docs_examined = len({s.get("document_id") for s in summary_records} | {r.document_id for r in source_relations})
        summaries_examined = len(summary_records)
        source_rels_examined = len(source_relations)
        sum_rels_extracted = len(all_summary_relations)

        exact_match_count = sum(1 for a in alignments if a.exact_match)
        aligned_count = sum(1 for a in alignments if a.alignment_status == "aligned")
        ambiguous_count = sum(1 for a in alignments if a.alignment_status == "ambiguous")
        below_thresh_count = sum(1 for a in alignments if a.alignment_status == "below_threshold")
        no_cand_count = sum(1 for a in alignments if a.alignment_status == "no_candidate")

        unmatched_sources = sum(1 for a in alignments if a.alignment_status in ("below_threshold", "no_candidate"))
        all_sum_rel_ids = {r.summary_relation_id for r in all_summary_relations}
        unmatched_summaries = len(all_sum_rel_ids - matched_summary_rel_ids)

        cause_sims = [a.cause_similarity for a in alignments if a.candidate_rank is not None]
        effect_sims = [a.effect_similarity for a in alignments if a.candidate_rank is not None]
        overall_scores = [a.overall_alignment_score for a in alignments if a.candidate_rank is not None]

        mean_cause_sim = round(float(sum(cause_sims) / len(cause_sims)), 4) if cause_sims else 0.0
        mean_effect_sim = round(float(sum(effect_sims) / len(effect_sims)), 4) if effect_sims else 0.0
        mean_overall = round(float(sum(overall_scores) / len(overall_scores)), 4) if overall_scores else 0.0

        stats: Dict[str, Any] = {
            "documents_examined": docs_examined,
            "summaries_examined": summaries_examined,
            "source_relations_examined": source_rels_examined,
            "summary_relations_extracted": sum_rels_extracted,
            "source_relations_with_exact_matches": exact_match_count,
            "aligned_count": aligned_count,
            "ambiguous_count": ambiguous_count,
            "below_threshold_count": below_thresh_count,
            "no_candidate_count": no_cand_count,
            "unmatched_source_relations": unmatched_sources,
            "unmatched_summary_relations": unmatched_summaries,
            "similarity_statistics": {
                "mean_cause_similarity": mean_cause_sim,
                "mean_effect_similarity": mean_effect_sim,
                "mean_overall_alignment_score": mean_overall,
            },
            "configuration": {
                "embedding_model": self.align_cfg.embedding_model,
                "device": self.align_cfg.device,
                "cause_threshold": self.align_cfg.cause_threshold,
                "effect_threshold": self.align_cfg.effect_threshold,
                "overall_threshold": self.align_cfg.overall_threshold,
                "ambiguity_margin": self.align_cfg.ambiguity_margin,
                "cause_weight": self.align_cfg.cause_weight,
                "effect_weight": self.align_cfg.effect_weight,
                "relation_weight": self.align_cfg.relation_weight,
            },
        }

        # Write alignment_stats.json deterministically
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote alignment statistics to {stats_path}")

        # 4. Save Sample Output
        sample_alignments = [a.to_dict() for a in alignments[:5]]
        sample_data = {
            "sample_count": len(sample_alignments),
            "alignments": sample_alignments,
        }
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote sample alignments to {sample_path}")

        return stats


def main():
    """CLI entrypoint for running Phase 8 alignment pipeline."""
    config = load_config()
    pipeline = AlignmentPipeline(config)
    stats = pipeline.run()
    print("Phase 8 Pipeline execution completed successfully.")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
