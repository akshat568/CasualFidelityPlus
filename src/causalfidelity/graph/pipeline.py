"""Phase 4 Causal Graph Construction Pipeline coordinator."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from causalfidelity.config import AppConfig, load_config
from causalfidelity.graph.builder import CausalGraphBuilder
from causalfidelity.graph.schema import CausalGraph
from causalfidelity.graph.validator import CausalGraphValidator
from causalfidelity.utils.io import ensure_dir, save_json
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class CausalGraphPipeline:
    """Pipeline orchestrator for converting Phase 3 causal relations into directed CausalGraph objects."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.builder = CausalGraphBuilder()
        self.validator = CausalGraphValidator()

    def run(
        self,
        input_jsonl: Optional[Path] = None,
        max_documents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 4 graph construction pipeline.

        Args:
            input_jsonl: Path to Phase 3 causal_relations.jsonl input file.
            max_documents: Optional document processing limit.

        Returns:
            Dictionary of computed dataset-level graph statistics.
        """
        logger.info("Starting Phase 4 Causal Graph Pipeline run")

        root_dir = self.config.paths.root_dir
        if input_jsonl is None:
            input_jsonl = root_dir / self.config.causal_graph.input_file
        else:
            input_jsonl = Path(input_jsonl)

        if not input_jsonl.exists():
            raise FileNotFoundError(
                f"Input Phase 3 dataset '{input_jsonl}' not found. Please run Phase 3 pipeline first."
            )

        # Load Phase 3 records
        records = []
        with open(input_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line.strip()))

        if max_documents is not None and max_documents > 0:
            records = records[:max_documents]

        graphs: List[CausalGraph] = []

        total_docs = len(records)
        non_empty_docs = 0
        empty_docs = 0
        total_nodes = 0
        total_edges = 0
        total_cycles = 0
        dags_count = 0
        non_dags_count = 0

        for rec in records:
            doc_id = rec.get("document_id", "")
            relations = rec.get("relations", [])

            graph = self.builder.build_graph(doc_id, relations)

            # Validate graph
            is_valid, reason = self.validator.validate_graph(graph, source_relations=relations)
            if not is_valid:
                logger.warning(f"Graph validation error for document '{doc_id}': {reason}")

            graphs.append(graph)

            # Accumulate statistics
            st = graph.statistics
            n_count = st.get("node_count", 0)
            e_count = st.get("edge_count", 0)

            total_nodes += n_count
            total_edges += e_count

            if n_count > 0:
                non_empty_docs += 1
            else:
                empty_docs += 1

            if st.get("is_dag", True):
                dags_count += 1
            else:
                non_dags_count += 1

            total_cycles += st.get("cycle_count", 0)

        # Save output JSONL
        output_jsonl_path = root_dir / self.config.causal_graph.output_file
        self._write_graphs_jsonl(graphs, output_jsonl_path)

        # Compute aggregate dataset statistics
        avg_nodes = round(total_nodes / total_docs, 2) if total_docs > 0 else 0.0
        avg_edges = round(total_edges / total_docs, 2) if total_docs > 0 else 0.0
        max_nodes = max((g.statistics.get("node_count", 0) for g in graphs), default=0)
        max_edges = max((g.statistics.get("edge_count", 0) for g in graphs), default=0)

        stats = {
            "pipeline_info": {
                "phase": "Phase 4 — Causal Representation & Graph Construction",
                "graph_type": "networkx.DiGraph",
            },
            "counts": {
                "documents_processed": total_docs,
                "documents_with_non_empty_graphs": non_empty_docs,
                "documents_with_empty_graphs": empty_docs,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "average_nodes_per_document": avg_nodes,
                "average_edges_per_document": avg_edges,
                "max_nodes_in_document": max_nodes,
                "max_edges_in_document": max_edges,
                "total_detected_cycles": total_cycles,
                "number_of_dags": dags_count,
                "number_of_non_dags": non_dags_count,
            },
        }

        stats_json_path = root_dir / self.config.causal_graph.stats_file
        save_json(stats, stats_json_path)

        # Save inspection sample
        sample_path = root_dir / self.config.causal_graph.sample_output_file
        self._write_inspection_sample(graphs, sample_path)

        logger.info(
            f"Phase 4 Pipeline complete. Built {total_docs} graphs ({non_empty_docs} non-empty, {total_edges} total edges)."
        )
        return stats

    @staticmethod
    def _write_graphs_jsonl(graphs: List[CausalGraph], file_path: Path) -> None:
        ensure_dir(file_path.parent)
        with open(file_path, "w", encoding="utf-8") as f:
            for g in graphs:
                f.write(json.dumps(g.to_dict(), ensure_ascii=False) + "\n")

    @staticmethod
    def _write_inspection_sample(graphs: List[CausalGraph], sample_path: Path, max_samples: int = 15) -> None:
        sample_list = []
        for g in graphs:
            if not g.statistics.get("is_empty", True):
                sample_list.append({
                    "document_id": g.document_id,
                    "nodes": [n.to_dict() for n in g.nodes],
                    "edges": [e.to_dict() for e in g.edges],
                    "statistics": g.statistics,
                })
                if len(sample_list) >= max_samples:
                    break

        save_json({"graph_sample": sample_list}, sample_path)
