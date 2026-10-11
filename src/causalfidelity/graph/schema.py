"""Canonical dataclass models for directed causal graphs."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CausalNode:
    """Dataclass representing a node in a causal graph."""

    node_id: str
    text: str
    normalized_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to dictionary representation."""
        return {
            "node_id": self.node_id,
            "text": self.text,
            "normalized_text": self.normalized_text or self.text.strip().lower(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalNode":
        """Deserialize node from dictionary representation."""
        return cls(
            node_id=data.get("node_id", ""),
            text=data.get("text", ""),
            normalized_text=data.get("normalized_text", ""),
        )


@dataclass
class CausalEdge:
    """Dataclass representing a directed causal edge (source -> target)."""

    source: str
    target: str
    relation: str = "causes"
    relation_id: Optional[str] = None
    provenance_relation_ids: List[str] = field(default_factory=list)
    weight: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize edge to dictionary representation."""
        res: Dict[str, Any] = {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }
        if self.relation_id is not None:
            res["relation_id"] = self.relation_id
        if self.provenance_relation_ids:
            res["provenance_relation_ids"] = self.provenance_relation_ids
        if self.weight > 1:
            res["weight"] = self.weight
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalEdge":
        """Deserialize edge from dictionary representation."""
        prov = data.get("provenance_relation_ids", [])
        rel_id = data.get("relation_id")
        if rel_id and not prov:
            prov = [rel_id]
        return cls(
            source=data.get("source", ""),
            target=data.get("target", ""),
            relation=data.get("relation", "causes"),
            relation_id=rel_id,
            provenance_relation_ids=prov,
            weight=int(data.get("weight", 1)),
        )


@dataclass
class CausalGraph:
    """Dataclass container representing a document's full directed causal graph."""

    document_id: str
    nodes: List[CausalNode] = field(default_factory=list)
    edges: List[CausalEdge] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize causal graph to dictionary representation."""
        return {
            "document_id": self.document_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "statistics": self.statistics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalGraph":
        """Deserialize causal graph from dictionary representation."""
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])
        nodes = [n if isinstance(n, CausalNode) else CausalNode.from_dict(n) for n in raw_nodes]
        edges = [e if isinstance(e, CausalEdge) else CausalEdge.from_dict(e) for e in raw_edges]
        return cls(
            document_id=data.get("document_id", ""),
            nodes=nodes,
            edges=edges,
            statistics=data.get("statistics", {}),
        )
