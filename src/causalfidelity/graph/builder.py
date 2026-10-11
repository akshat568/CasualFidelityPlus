"""Causal graph builder and NetworkX conversion engine."""

import re
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from causalfidelity.causal.schema import CausalRelation
from causalfidelity.graph.schema import CausalEdge, CausalGraph, CausalNode
from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class CausalGraphBuilder:
    """Builder engine for constructing directed CausalGraph objects and NetworkX DiGraph instances."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Apply conservative deterministic text normalization for node identity matching."""
        if not text:
            return ""
        # Collapse whitespace and lowercase
        cleaned = re.sub(r"\s+", " ", text.strip())
        return cleaned.lower()

    def build_graph(
        self,
        document_id: str,
        relations: List[CausalRelation | Dict[str, Any]],
    ) -> CausalGraph:
        """Construct a CausalGraph from a list of Phase 3 causal relations.

        Args:
            document_id: Canonical document identifier.
            relations: List of CausalRelation dataclass instances or relation dictionaries.

        Returns:
            Constructed CausalGraph dataclass instance.
        """
        # Node lookup maps
        norm_to_node_id: Dict[str, str] = {}
        nodes_list: List[CausalNode] = []
        node_counter = 1

        def get_or_create_node(raw_text: str) -> str:
            nonlocal node_counter
            norm = self.normalize_text(raw_text)
            if norm in norm_to_node_id:
                return norm_to_node_id[norm]

            node_id = f"node_{node_counter:06d}"
            node_counter += 1
            node_obj = CausalNode(node_id=node_id, text=raw_text.strip(), normalized_text=norm)
            norm_to_node_id[norm] = node_id
            nodes_list.append(node_obj)
            return node_id

        # Edge lookup map to collapse duplicates into DiGraph structural edges
        edge_map: Dict[Tuple[str, str], CausalEdge] = {}

        for item in relations:
            if isinstance(item, dict):
                rel_obj = CausalRelation.from_dict(item)
            else:
                rel_obj = item

            cause_text = rel_obj.cause
            effect_text = rel_obj.effect

            if not cause_text or not effect_text:
                continue

            src_id = get_or_create_node(cause_text)
            tgt_id = get_or_create_node(effect_text)

            edge_key = (src_id, tgt_id)
            rel_id = rel_obj.relation_id or None

            if edge_key in edge_map:
                existing_edge = edge_map[edge_key]
                existing_edge.weight += 1
                if rel_id and rel_id not in existing_edge.provenance_relation_ids:
                    existing_edge.provenance_relation_ids.append(rel_id)
            else:
                prov = [rel_id] if rel_id else []
                new_edge = CausalEdge(
                    source=src_id,
                    target=tgt_id,
                    relation="causes",
                    relation_id=rel_id,
                    provenance_relation_ids=prov,
                    weight=1,
                )
                edge_map[edge_key] = new_edge

        edges_list = list(edge_map.values())
        causal_graph = CausalGraph(document_id=document_id, nodes=nodes_list, edges=edges_list)

        # Compute graph metrics via NetworkX
        dg = self.to_networkx(causal_graph)
        stats = self.compute_statistics(dg, causal_graph)
        causal_graph.statistics = stats

        return causal_graph

    @staticmethod
    def to_networkx(graph: CausalGraph) -> nx.DiGraph:
        """Convert a CausalGraph instance to a networkx.DiGraph."""
        dg = nx.DiGraph()
        for node in graph.nodes:
            dg.add_node(node.node_id, text=node.text, normalized_text=node.normalized_text)
        for edge in graph.edges:
            dg.add_edge(
                edge.source,
                edge.target,
                relation=edge.relation,
                relation_id=edge.relation_id,
                provenance_relation_ids=edge.provenance_relation_ids,
                weight=edge.weight,
            )
        return dg

    @staticmethod
    def compute_statistics(dg: nx.DiGraph, graph: CausalGraph) -> Dict[str, Any]:
        """Compute document-level metrics over networkx.DiGraph."""
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
        is_empty = node_count == 0

        if is_empty:
            return {
                "node_count": 0,
                "edge_count": 0,
                "is_empty": True,
                "is_dag": True,
                "cycle_count": 0,
                "weakly_connected_components": 0,
                "isolated_node_count": 0,
                "max_causal_chain_length": 0,
            }

        is_dag = nx.is_directed_acyclic_graph(dg)
        cycles = list(nx.simple_cycles(dg))
        cycle_count = len(cycles)
        components = nx.number_weakly_connected_components(dg)
        isolated_nodes = sum(1 for n in dg.nodes if dg.degree(n) == 0)

        max_chain_len: Optional[int]
        if is_dag:
            max_chain_len = nx.dag_longest_path_length(dg) if edge_count > 0 else 0
        else:
            max_chain_len = None

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "is_empty": False,
            "is_dag": is_dag,
            "cycle_count": cycle_count,
            "weakly_connected_components": components,
            "isolated_node_count": isolated_nodes,
            "max_causal_chain_length": max_chain_len,
        }
