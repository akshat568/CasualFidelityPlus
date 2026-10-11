"""Phase 3 Causal Relation Extraction Pipeline coordinator."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.causal.schema import CausalRelation, DocumentCausalRelations
from causalfidelity.causal.validator import CausalRelationValidator
from causalfidelity.config import AppConfig, load_config
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class CausalExtractionPipeline:
    """Pipeline orchestrator for extracting explicit causal relations from dataset records."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.extractor = RuleBasedCausalExtractor(
            confidence_default=self.config.causal_extraction.confidence_default
        )
        self.validator = CausalRelationValidator()

    def run(
        self,
        input_jsonl: Optional[Path] = None,
        max_documents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 3 extraction pipeline over processed Phase 2 dataset.

        Args:
            input_jsonl: Path to input JSONL file (defaults to data/processed/xsum_dev.jsonl).
            max_documents: Optional limit on number of documents to process.

        Returns:
            Dictionary of computed extraction statistics.
        """
        logger.info("Starting Phase 3 Causal Extraction Pipeline run")

        root_dir = self.config.paths.root_dir
        if input_jsonl is None:
            input_jsonl = root_dir / "data" / "processed" / "xsum_dev.jsonl"
        else:
            input_jsonl = Path(input_jsonl)

        if not input_jsonl.exists():
            raise FileNotFoundError(
                f"Input dataset '{input_jsonl}' not found. Please run Phase 2 pipeline first."
            )

        # Load records
        records = []
        with open(input_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line.strip()))

        limit = max_documents or self.config.causal_extraction.max_documents
        if limit is not None and limit > 0:
            records = records[:limit]

        global_rel_counter = 1
        doc_results: List[DocumentCausalRelations] = []

        total_docs = len(records)
        docs_with_rels = 0
        docs_zero_rels = 0
        total_sentences_examined = 0
        candidate_sentences_examined = 0
        total_relations_extracted = 0
        validation_rejections = 0
        rejection_reasons: Counter[str] = Counter()
        trigger_counts: Counter[str] = Counter()

        for rec in records:
            doc_id = rec.get("document_id", "")
            source_text = rec.get("source_text", "")
            is_candidate = rec.get("causal_candidate", False)

            # Sentence segmentation statistics
            sentences = self.extractor.split_sentences(source_text)
            total_sentences_examined += len(sentences)

            # Extract relations
            raw_relations = self.extractor.extract_relations(doc_id, source_text)

            valid_doc_rels: List[CausalRelation] = []
            for rel in raw_relations:
                is_valid, reason = self.validator.validate_relation(rel)
                if not is_valid:
                    validation_rejections += 1
                    rejection_reasons[reason or "unknown"] += 1
                    continue

                # Assign sequential global relation ID
                rel.relation_id = f"rel_{global_rel_counter:06d}"
                global_rel_counter += 1

                valid_doc_rels.append(rel)
                total_relations_extracted += 1
                if rel.pattern_matched:
                    trigger_counts[rel.pattern_matched] += 1

            if valid_doc_rels:
                docs_with_rels += 1
            else:
                docs_zero_rels += 1

            doc_results.append(
                DocumentCausalRelations(document_id=doc_id, relations=valid_doc_rels)
            )

        # Save output JSONL
        processed_dir = ensure_dir(self.config.paths.processed_data_dir)
        output_jsonl_path = root_dir / self.config.causal_extraction.output_file
        self._write_relations_jsonl(doc_results, output_jsonl_path)

        # Compute statistics
        avg_rels_per_doc = round(total_relations_extracted / total_docs, 2) if total_docs > 0 else 0.0

        stats = {
            "pipeline_info": {
                "phase": "Phase 3 — Causal Relation Extraction",
                "method": self.config.causal_extraction.method,
            },
            "counts": {
                "total_documents_processed": total_docs,
                "documents_with_relations": docs_with_rels,
                "documents_with_zero_relations": docs_zero_rels,
                "total_sentences_examined": total_sentences_examined,
                "candidate_sentences_examined": candidate_sentences_examined,
                "total_relations_extracted": total_relations_extracted,
                "average_relations_per_document": avg_rels_per_doc,
                "validation_rejections": validation_rejections,
            },
            "trigger_counts": dict(trigger_counts.most_common()),
            "validation_rejections_breakdown": dict(rejection_reasons.most_common()),
        }

        stats_json_path = root_dir / self.config.causal_extraction.stats_file
        save_json(stats, stats_json_path)

        # Save inspection sample
        sample_path = root_dir / self.config.causal_extraction.sample_output_file
        self._write_inspection_sample(doc_results, sample_path)

        logger.info(
            f"Phase 3 Pipeline complete. Extracted {total_relations_extracted} relations across {total_docs} documents."
        )
        return stats

    @staticmethod
    def _write_relations_jsonl(doc_results: List[DocumentCausalRelations], file_path: Path) -> None:
        ensure_dir(file_path.parent)
        with open(file_path, "w", encoding="utf-8") as f:
            for item in doc_results:
                f.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _write_inspection_sample(doc_results: List[DocumentCausalRelations], sample_path: Path, max_samples: int = 15) -> None:
        sample_list = []
        for doc in doc_results:
            for rel in doc.relations:
                sample_list.append({
                    "document_id": rel.document_id,
                    "relation_id": rel.relation_id,
                    "source_sentence": rel.source_sentence,
                    "cause": rel.cause,
                    "relation": rel.relation,
                    "effect": rel.effect,
                    "confidence": rel.confidence,
                    "extraction_method": rel.extraction_method,
                    "pattern_matched": rel.pattern_matched,
                })
                if len(sample_list) >= max_samples:
                    break
            if len(sample_list) >= max_samples:
                break

        save_json({"extracted_sample": sample_list}, sample_path)
