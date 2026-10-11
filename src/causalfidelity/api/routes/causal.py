"""Causal extraction and graph routes for CausalFidelityPlus API."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
import networkx as nx

from causalfidelity.api.dependencies import get_causal_extractor, get_graph_builder
from causalfidelity.api.exceptions import InvalidInputException
from causalfidelity.api.schemas import (
    CausalEdgeDTO,
    CausalExtractionRequest,
    CausalExtractionResponse,
    CausalGraphRequest,
    CausalGraphResponse,
    CausalNodeDTO,
    CausalRelationDTO,
)
from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.causal.schema import CausalRelation
from causalfidelity.graph.builder import CausalGraphBuilder

router = APIRouter(prefix="/causal", tags=["Causal Extraction & Graph"])


@router.post("/extract", response_model=CausalExtractionResponse, summary="Extract Causal Relations")
async def extract_causal_relations(
    payload: CausalExtractionRequest,
    extractor: RuleBasedCausalExtractor = Depends(get_causal_extractor),
) -> CausalExtractionResponse:
    """Extract explicit causal relations from input text using the Phase 3 rule-based extractor."""
    doc_id = payload.document_id or "doc_user"
    text = payload.text.strip()
    if not text:
        raise InvalidInputException("Input text cannot be empty.")

    raw_relations: List[CausalRelation] = extractor.extract_relations(doc_id, text)

    dto_relations = [
        CausalRelationDTO(
            relation_id=rel.relation_id,
            document_id=rel.document_id,
            sentence_index=rel.sentence_index,
            cause=rel.cause,
            effect=rel.effect,
            relation=rel.relation,
            connective=rel.relation,
            confidence=rel.confidence,
            source_sentence=rel.source_sentence,
        )
        for rel in raw_relations
    ]

    return CausalExtractionResponse(
        document_id=doc_id,
        relations_count=len(dto_relations),
        relations=dto_relations,
    )


@router.post("/graph", response_model=CausalGraphResponse, summary="Construct Causal DiGraph")
async def build_causal_graph(
    payload: CausalGraphRequest,
    extractor: RuleBasedCausalExtractor = Depends(get_causal_extractor),
    builder: CausalGraphBuilder = Depends(get_graph_builder),
) -> CausalGraphResponse:
    """Construct a NetworkX Causal DiGraph and Mermaid representation from input text or extracted relations."""
    doc_id = payload.document_id or "doc_user"
    relations = payload.relations

    if not relations and payload.text:
        text = payload.text.strip()
        if text:
            extracted_rels = extractor.extract_relations(doc_id, text)
            relations = [rel.to_dict() for rel in extracted_rels]

    if not relations:
        relations = []

    graph_obj = builder.build_graph(doc_id, relations)
    dg = builder.to_networkx(graph_obj)

    node_dtos = [
        CausalNodeDTO(
            node_id=node.node_id,
            text=node.text,
            normalized_text=node.normalized_text,
        )
        for node in graph_obj.nodes
    ]

    edge_dtos = [
        CausalEdgeDTO(
            source=edge.source,
            target=edge.target,
            relation=edge.relation,
            relation_id=edge.relation_id,
            weight=edge.weight,
        )
        for edge in graph_obj.edges
    ]

    # Generate Mermaid diagram string
    mermaid_lines = ["graph TD"]
    for node in node_dtos:
        safe_label = node.text.replace('"', "'")
        mermaid_lines.append(f'  {node.node_id}["{safe_label}"]')
    for edge in edge_dtos:
        safe_rel = edge.relation.replace('"', "'")
        mermaid_lines.append(f'  {edge.source} -->|"{safe_rel}"| {edge.target}')

    mermaid_code = "\n".join(mermaid_lines)

    is_dag = nx.is_directed_acyclic_graph(dg) if len(dg) > 0 else True
    has_cycles = not is_dag

    return CausalGraphResponse(
        document_id=doc_id,
        node_count=len(node_dtos),
        edge_count=len(edge_dtos),
        is_dag=is_dag,
        has_cycles=has_cycles,
        nodes=node_dtos,
        edges=edge_dtos,
        mermaid_code=mermaid_code,
    )
