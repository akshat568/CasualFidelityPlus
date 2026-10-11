"""Unit tests for Phase 4 causal representation and graph construction."""

import json
import pytest

from causalfidelity.causal.schema import CausalRelation
from causalfidelity.config import load_config
from causalfidelity.graph.builder import CausalGraphBuilder
from causalfidelity.graph.pipeline import CausalGraphPipeline
from causalfidelity.graph.schema import CausalGraph, CausalNode, CausalEdge
from causalfidelity.graph.validator import CausalGraphValidator


def test_simple_relation():
    """Verify graph construction for a single relation (A causes B)."""
    builder = CausalGraphBuilder()
    rel = CausalRelation(
        relation_id="rel_01",
        document_id="doc_1",
        cause="Heavy rainfall",
        relation="causes",
        effect="flooding",
    )
    graph = builder.build_graph("doc_1", [rel])

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes[0].text == "Heavy rainfall"
    assert graph.nodes[1].text == "flooding"
    assert graph.edges[0].source == graph.nodes[0].node_id
    assert graph.edges[0].target == graph.nodes[1].node_id
    assert graph.edges[0].relation == "causes"


def test_direction_preservation():
    """Verify strict causal direction preservation (A -> B exists, B -> A does not)."""
    builder = CausalGraphBuilder()
    rel = CausalRelation(
        relation_id="rel_01",
        document_id="doc_2",
        cause="Heavy rainfall",
        relation="causes",
        effect="flooding",
    )
    graph = builder.build_graph("doc_2", [rel])
    dg = builder.to_networkx(graph)

    src_id = graph.nodes[0].node_id  # Heavy rainfall
    tgt_id = graph.nodes[1].node_id  # flooding

    assert dg.has_edge(src_id, tgt_id) is True
    assert dg.has_edge(tgt_id, src_id) is False


def test_causal_chain():
    """Verify causal chain construction (A -> B -> C) and longest path length."""
    builder = CausalGraphBuilder()
    rels = [
        CausalRelation(relation_id="r1", document_id="doc_3", cause="Heavy rainfall", relation="causes", effect="flooding"),
        CausalRelation(relation_id="r2", document_id="doc_3", cause="flooding", relation="causes", effect="road closures"),
    ]
    graph = builder.build_graph("doc_3", rels)

    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.statistics["is_dag"] is True
    assert graph.statistics["max_causal_chain_length"] == 2


def test_shared_cause():
    """Verify shared cause structure (A -> B and A -> C)."""
    builder = CausalGraphBuilder()
    rels = [
        CausalRelation(relation_id="r1", document_id="doc_4", cause="Heavy rainfall", relation="causes", effect="flooding"),
        CausalRelation(relation_id="r2", document_id="doc_4", cause="Heavy rainfall", relation="causes", effect="landslides"),
    ]
    graph = builder.build_graph("doc_4", rels)

    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.edges[0].source == graph.edges[1].source


def test_shared_effect():
    """Verify shared effect structure (A -> C and B -> C)."""
    builder = CausalGraphBuilder()
    rels = [
        CausalRelation(relation_id="r1", document_id="doc_5", cause="Heavy rainfall", relation="causes", effect="flooding"),
        CausalRelation(relation_id="r2", document_id="doc_5", cause="River overflow", relation="causes", effect="flooding"),
    ]
    graph = builder.build_graph("doc_5", rels)

    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.edges[0].target == graph.edges[1].target


def test_duplicate_relation_collapsing():
    """Verify that duplicate parallel relations collapse into a single structural edge."""
    builder = CausalGraphBuilder()
    rels = [
        CausalRelation(relation_id="r1", document_id="doc_6", cause="Heavy rainfall", relation="causes", effect="flooding"),
        CausalRelation(relation_id="r2", document_id="doc_6", cause="Heavy rainfall", relation="causes", effect="flooding"),
    ]
    graph = builder.build_graph("doc_6", rels)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].weight == 2
    assert set(graph.edges[0].provenance_relation_ids) == {"r1", "r2"}


def test_empty_relation_list():
    """Verify handling of empty relation list resulting in a valid empty graph."""
    builder = CausalGraphBuilder()
    graph = builder.build_graph("doc_7", [])

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
    assert graph.statistics["is_empty"] is True
    assert graph.statistics["is_dag"] is True
    assert graph.statistics["max_causal_chain_length"] == 0


def test_cycle_detection():
    """Verify detection of cycles (A -> B and B -> A) and DAG flag."""
    builder = CausalGraphBuilder()
    rels = [
        CausalRelation(relation_id="r1", document_id="doc_8", cause="A", relation="causes", effect="B"),
        CausalRelation(relation_id="r2", document_id="doc_8", cause="B", relation="causes", effect="A"),
    ]
    graph = builder.build_graph("doc_8", rels)

    assert graph.statistics["is_dag"] is False
    assert graph.statistics["cycle_count"] == 1
    assert graph.statistics["max_causal_chain_length"] is None


def test_deterministic_node_ids():
    """Verify that running graph construction twice yields identical node IDs and serialization."""
    builder = CausalGraphBuilder()
    rels = [
        CausalRelation(relation_id="r1", document_id="doc_9", cause="Heavy rainfall", relation="causes", effect="flooding"),
        CausalRelation(relation_id="r2", document_id="doc_9", cause="flooding", relation="causes", effect="closures"),
    ]

    g1 = builder.build_graph("doc_9", rels)
    g2 = builder.build_graph("doc_9", rels)

    assert g1.to_dict() == g2.to_dict()
    assert g1.nodes[0].node_id == "node_000001"
    assert g1.nodes[1].node_id == "node_000002"


def test_pipeline_on_synthetic_fixture(tmp_path):
    """Verify Phase 4 graph pipeline execution on a synthetic fixture."""
    synthetic_relations = [
        {
            "document_id": "xsum_000001",
            "relations": [
                {
                    "relation_id": "rel_000001",
                    "document_id": "xsum_000001",
                    "cause": "Heavy rainfall",
                    "relation": "causes",
                    "effect": "flooding",
                    "confidence": 0.9,
                    "source_sentence": "Heavy rainfall caused flooding.",
                }
            ],
        },
        {
            "document_id": "xsum_000002",
            "relations": [],
        },
    ]

    input_jsonl = tmp_path / "causal_relations.jsonl"
    with open(input_jsonl, "w", encoding="utf-8") as f:
        for rec in synthetic_relations:
            f.write(json.dumps(rec) + "\n")

    config = load_config()
    config.paths.root_dir = tmp_path
    config.causal_graph.input_file = "causal_relations.jsonl"
    config.causal_graph.output_file = "data/processed/causal_graphs.jsonl"
    config.causal_graph.stats_file = "data/processed/causal_graphs_stats.json"
    config.causal_graph.sample_output_file = "outputs/results/phase4_graph_sample.json"

    pipeline = CausalGraphPipeline(config=config)
    stats = pipeline.run(input_jsonl=input_jsonl)

    assert stats["counts"]["documents_processed"] == 2
    assert stats["counts"]["documents_with_non_empty_graphs"] == 1
    assert stats["counts"]["documents_with_empty_graphs"] == 1
    assert stats["counts"]["total_nodes"] == 2
    assert stats["counts"]["total_edges"] == 1

    output_jsonl = tmp_path / "data/processed/causal_graphs.jsonl"
    output_stats = tmp_path / "data/processed/causal_graphs_stats.json"
    output_sample = tmp_path / "outputs/results/phase4_graph_sample.json"

    assert output_jsonl.exists()
    assert output_stats.exists()
    assert output_sample.exists()

    lines = output_jsonl.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    g1_data = json.loads(lines[0])
    g2_data = json.loads(lines[1])

    assert g1_data["document_id"] == "xsum_000001"
    assert len(g1_data["nodes"]) == 2
    assert len(g1_data["edges"]) == 1

    assert g2_data["document_id"] == "xsum_000002"
    assert len(g2_data["nodes"]) == 0
    assert len(g2_data["edges"]) == 0
