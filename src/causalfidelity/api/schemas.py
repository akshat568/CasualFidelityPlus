"""Pydantic request and response schemas for CausalFidelityPlus API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Health Schemas ---
class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str = Field(..., description="API operational status")
    version: str = Field(..., description="API semantic version")
    components_available: Dict[str, bool] = Field(..., description="Availability of core pipeline components")
    models_loaded: Dict[str, bool] = Field(..., description="Neural model initialization status")
    timestamp: str = Field(..., description="ISO 8601 server timestamp")


# --- Causal Extraction Schemas ---
class CausalExtractionRequest(BaseModel):
    """Request payload for causal relation extraction."""

    text: str = Field(..., min_length=1, max_length=20000, description="Source text to extract causal relations from")
    document_id: Optional[str] = Field("doc_user", description="Optional document identifier")


class CausalRelationDTO(BaseModel):
    """Data transfer object for a single causal relation."""

    relation_id: str
    document_id: str
    sentence_index: int = 0
    cause: str
    effect: str
    relation: str = "causes"
    connective: str = "causes"
    confidence: float = 1.0
    source_sentence: str = ""


class CausalExtractionResponse(BaseModel):
    """Response payload for causal relation extraction."""

    document_id: str
    relations_count: int
    relations: List[CausalRelationDTO]


# --- Causal Graph Schemas ---
class CausalGraphRequest(BaseModel):
    """Request payload for causal graph construction."""

    document_id: Optional[str] = Field("doc_user", description="Optional document identifier")
    text: Optional[str] = Field(None, max_length=20000, description="Optional raw text to extract relations from")
    relations: Optional[List[Dict[str, Any]]] = Field(None, description="Optional pre-extracted relations list")


class CausalNodeDTO(BaseModel):
    """Data transfer object for a causal graph node."""

    node_id: str
    text: str
    normalized_text: str = ""


class CausalEdgeDTO(BaseModel):
    """Data transfer object for a causal graph edge."""

    source: str
    target: str
    relation: str = "causes"
    relation_id: Optional[str] = None
    weight: int = 1


class CausalGraphResponse(BaseModel):
    """Response payload for causal graph construction."""

    document_id: str
    node_count: int
    edge_count: int
    is_dag: bool
    has_cycles: bool
    nodes: List[CausalNodeDTO]
    edges: List[CausalEdgeDTO]
    mermaid_code: str


# --- Perturbation Schemas ---
class PerturbationGenerationRequest(BaseModel):
    """Request payload for controlled causal perturbation generation."""

    summary_text: str = Field(..., min_length=1, max_length=10000, description="Summary text to generate perturbations for")
    document_id: Optional[str] = Field("doc_user", description="Optional document identifier")
    summary_id: Optional[str] = Field("sum_user", description="Optional summary identifier")
    source_relations: Optional[List[Dict[str, Any]]] = Field(None, description="Optional source document relations list")
    selected_strategies: Optional[List[str]] = Field(
        None,
        description="Optional list of perturbation strategies to apply ('REVERSED', 'WEAKENED', 'DROPPED', 'CAUSE_CHANGED', 'EFFECT_CHANGED')",
    )


class PerturbationDTO(BaseModel):
    """Data transfer object for a single generated perturbation."""

    perturbation_id: str
    document_id: str
    summary_id: str
    strategy: str
    perturbation_type: str = ""
    original_text: str
    perturbed_text: str
    original_relation: Dict[str, Any] = Field(default_factory=dict)
    intended_relation: Dict[str, Any] = Field(default_factory=dict)
    changed_span: Dict[str, Any] = Field(default_factory=dict)
    generation_method: str = "rule_based"
    target_relation: Optional[Dict[str, Any]] = None


class PerturbationGenerationResponse(BaseModel):
    """Response payload for perturbation generation."""

    document_id: str
    summary_id: str
    perturbations_count: int
    perturbations: List[PerturbationDTO]
    stats: Dict[str, Any]


# --- Validation Schemas ---
class PerturbationValidationRequest(BaseModel):
    """Request payload for perturbation quality validation."""

    records: List[Dict[str, Any]] = Field(..., min_length=1, description="List of perturbation records to validate")


class ValidationResultDTO(BaseModel):
    """Data transfer object for a single validation record result."""

    perturbation_id: str
    is_valid: bool
    validation_status: str
    quality_score: float
    error_flags: List[str]
    warning_flags: List[str]
    metrics: Dict[str, Any]


class PerturbationValidationResponse(BaseModel):
    """Response payload for perturbation validation."""

    total_examined: int
    valid_count: int
    invalid_count: int
    validation_rate: float
    results: List[ValidationResultDTO]


# --- Fidelity Evaluation Schemas ---
class FidelityEvaluationRequest(BaseModel):
    """Request payload for causal fidelity metric evaluation."""

    source_text: str = Field(..., min_length=1, max_length=20000, description="Original source document text")
    original_summary: str = Field(..., min_length=1, max_length=10000, description="Original reference summary text")
    perturbed_summary: str = Field(..., min_length=1, max_length=10000, description="Perturbed summary text")
    enabled_metrics: Optional[List[str]] = Field(
        None,
        description="List of metrics to enable ('summac', 'factcc', 'bertscore'). Defaults to all if None.",
    )


class MetricScoreDTO(BaseModel):
    """Data transfer object for a metric evaluation score."""

    metric_name: str
    status: str
    original_score: Optional[float] = None
    perturbed_score: Optional[float] = None
    score_delta: Optional[float] = None
    bertscore_f1: Optional[float] = None
    bertscore_precision: Optional[float] = None
    bertscore_recall: Optional[float] = None
    similarity_loss: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class FidelityEvaluationResponse(BaseModel):
    """Response payload for fidelity evaluation."""

    source_text: str
    original_summary: str
    perturbed_summary: str
    metrics: Dict[str, MetricScoreDTO]


# --- Complete Pipeline Analyze Schemas ---
class PipelineAnalyzeRequest(BaseModel):
    """Request payload for end-to-end interactive pipeline execution."""

    source_text: str = Field(..., min_length=1, max_length=20000, description="Source document text")
    summary_text: str = Field(..., min_length=1, max_length=10000, description="Summary text")
    document_id: Optional[str] = Field("doc_interactive", description="Document ID")
    selected_strategies: Optional[List[str]] = Field(None, description="Selected perturbation strategies")
    enabled_metrics: Optional[List[str]] = Field(["summac", "factcc", "bertscore"], description="Metrics to evaluate")


class PipelineAnalyzeResponse(BaseModel):
    """Response payload for end-to-end pipeline execution."""

    document_id: str
    status: str
    extraction: CausalExtractionResponse
    graph: CausalGraphResponse
    perturbations: PerturbationGenerationResponse
    validation: PerturbationValidationResponse
    fidelity: FidelityEvaluationResponse


# --- Report Schemas ---
class ReportResponse(BaseModel):
    """Response payload for research report and summary retrieval."""

    report_type: str
    title: str
    file_name: str
    content_type: str
    data: Any
