"""Validation utilities for directed CausalGraph objects."""

from typing import Any, Dict, List, Optional, Tuple

from causalfidelity.causal.schema import CausalRelation
from causalfidelity.graph.builder import CausalGraphBuilder
from causalfidelity.graph.schema import CausalGraph


class CausalGraphValidator:
    """Validates structural and directional sanity constraints of CausalGraph instances."""

    @staticmethod
    def validate_graph(
        graph: CausalGraph,
        source_relations: Optional[List[CausalRelation | Dict[str, Any]]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate structural and direction integrity of a CausalGraph.

        Args:
            graph: CausalGraph dataclass instance to inspect.
            source_relations: Optional list of Phase 3 CausalRelations used to build graph.

        Returns:
            Tuple of (is_valid: bool, rejection_reason: Optional[str])
        """
        if not graph:
            return False, "Graph object is None"

        if not graph.document_id:
            return False, "Missing document_id"

        node_ids = {n.node_id for n in graph.nodes}

        # Check nodes
        for node in graph.nodes:
            if not node.node_id or not node.node_id.strip():
                return False, "Node missing node_id"
            if not node.text or not node.text.strip():
                return False, f"Node '{node.node_id}' has empty text"

        # Check edges
        edge_pairs = set()
        for edge in graph.edges:
            if not edge.source or edge.source not in node_ids:
                return False, f"Edge source '{edge.source}' not found in node set"
            if not edge.target or edge.target not in node_ids:
                return False, f"Edge target '{edge.target}' not found in node set"
            if edge.source == edge.target:
                return False, f"Self-loop edge on node '{edge.source}' detected"
            if edge.relation != "causes":
                return False, f"Invalid edge relation '{edge.relation}' (expected 'causes')"

            edge_pairs.add((edge.source, edge.target))

        # Check direction validity against source relations if provided
        if source_relations is not None:
            norm_map = {
                CausalGraphBuilder.normalize_text(n.text): n.node_id for n in graph.nodes
            }
            for rel_item in source_relations:
                rel = rel_item if isinstance(rel_item, CausalRelation) else CausalRelation.from_dict(rel_item)
                cause_norm = CausalGraphBuilder.normalize_text(rel.cause)
                effect_norm = CausalGraphBuilder.normalize_text(rel.effect)

                if cause_norm in norm_map and effect_norm in norm_map:
                    src = norm_map[cause_norm]
                    tgt = norm_map[effect_norm]
                    if (src, tgt) not in edge_pairs:
                        return False, f"Direction mismatch: relation '{rel.cause} -> {rel.effect}' missing directed edge '{src} -> {tgt}'"

        return True, None
