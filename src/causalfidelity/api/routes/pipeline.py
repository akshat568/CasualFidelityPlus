"""End-to-end interactive pipeline analysis route for FastAPI API."""

from fastapi import APIRouter, Depends
from causalfidelity.api.dependencies import (
    get_causal_extractor,
    get_graph_builder,
    get_perturbation_generator,
    get_quality_validator,
)
from causalfidelity.api.exceptions import InvalidInputException
from causalfidelity.api.routes.causal import build_causal_graph, extract_causal_relations
from causalfidelity.api.routes.evaluation import evaluate_fidelity
from causalfidelity.api.routes.perturbation import generate_perturbations, validate_perturbations
from causalfidelity.api.schemas import (
    CausalExtractionRequest,
    CausalGraphRequest,
    FidelityEvaluationRequest,
    PerturbationGenerationRequest,
    PerturbationValidationRequest,
    PipelineAnalyzeRequest,
    PipelineAnalyzeResponse,
)
from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.graph.builder import CausalGraphBuilder
from causalfidelity.perturbation.generator import PerturbationGenerator
from causalfidelity.validation.validator import PerturbationQualityValidator

router = APIRouter(prefix="/pipeline", tags=["Interactive End-to-End Pipeline"])


@router.post("/analyze", response_model=PipelineAnalyzeResponse, summary="Execute Interactive Pipeline Analysis")
async def analyze_pipeline(
    payload: PipelineAnalyzeRequest,
    extractor: RuleBasedCausalExtractor = Depends(get_causal_extractor),
    builder: CausalGraphBuilder = Depends(get_graph_builder),
    generator: PerturbationGenerator = Depends(get_perturbation_generator),
    validator: PerturbationQualityValidator = Depends(get_quality_validator),
) -> PipelineAnalyzeResponse:
    """Execute end-to-end causal extraction, graph construction, controlled perturbation, quality validation, and metric evaluation."""
    doc_id = payload.document_id or "doc_interactive"
    src_text = payload.source_text.strip()
    sum_text = payload.summary_text.strip()

    if not src_text or not sum_text:
        raise InvalidInputException("Source text and summary text cannot be empty.")

    # Stage 1: Causal Extraction
    extract_resp = await extract_causal_relations(
        payload=CausalExtractionRequest(text=src_text, document_id=doc_id),
        extractor=extractor,
    )

    # Stage 2: Causal Graph
    graph_resp = await build_causal_graph(
        payload=CausalGraphRequest(
            document_id=doc_id,
            relations=[r.model_dump() for r in extract_resp.relations],
        ),
        extractor=extractor,
        builder=builder,
    )

    # Stage 3: Perturbation Generation
    pert_resp = await generate_perturbations(
        payload=PerturbationGenerationRequest(
            document_id=doc_id,
            summary_id=f"{doc_id}_sum",
            summary_text=sum_text,
            source_relations=[r.model_dump() for r in extract_resp.relations],
            selected_strategies=payload.selected_strategies,
        ),
        extractor=extractor,
        generator=generator,
    )

    # Stage 4: Perturbation Validation
    val_records = [p.model_dump() for p in pert_resp.perturbations]
    if val_records:
        val_resp = await validate_perturbations(
            payload=PerturbationValidationRequest(records=val_records),
            validator=validator,
        )
    else:
        val_resp = {
            "total_examined": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "validation_rate": 0.0,
            "results": [],
        }

    # Stage 5: Fidelity Evaluation (using first valid perturbed summary if available)
    first_pert_text = sum_text
    if pert_resp.perturbations:
        first_pert_text = pert_resp.perturbations[0].perturbed_text

    fidelity_resp = await evaluate_fidelity(
        payload=FidelityEvaluationRequest(
            source_text=src_text,
            original_summary=sum_text,
            perturbed_summary=first_pert_text,
            enabled_metrics=payload.enabled_metrics,
        )
    )

    return PipelineAnalyzeResponse(
        document_id=doc_id,
        status="SUCCESS",
        extraction=extract_resp,
        graph=graph_resp,
        perturbations=pert_resp,
        validation=val_resp,
        fidelity=fidelity_resp,
    )
