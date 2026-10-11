"""Controlled causal perturbation and validation routes for FastAPI API."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends

from causalfidelity.api.dependencies import (
    get_causal_extractor,
    get_perturbation_generator,
    get_quality_validator,
)
from causalfidelity.api.exceptions import InvalidInputException
from causalfidelity.api.schemas import (
    PerturbationDTO,
    PerturbationGenerationRequest,
    PerturbationGenerationResponse,
    PerturbationValidationRequest,
    PerturbationValidationResponse,
    ValidationResultDTO,
)
from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.causal.schema import CausalRelation
from causalfidelity.perturbation.generator import PerturbationGenerator
from causalfidelity.validation.validator import PerturbationQualityValidator

router = APIRouter(prefix="/perturbation", tags=["Controlled Perturbation & Quality Control"])

SUPPORTED_STRATEGIES = {"REVERSED", "WEAKENED", "DROPPED", "CAUSE_CHANGED", "EFFECT_CHANGED"}


@router.post("/generate", response_model=PerturbationGenerationResponse, summary="Generate Controlled Perturbations")
async def generate_perturbations(
    payload: PerturbationGenerationRequest,
    extractor: RuleBasedCausalExtractor = Depends(get_causal_extractor),
    generator: PerturbationGenerator = Depends(get_perturbation_generator),
) -> PerturbationGenerationResponse:
    """Generate controlled causal perturbations on summary text using Phase 6 perturbation strategies."""
    doc_id = payload.document_id or "doc_user"
    sum_id = payload.summary_id or "sum_user"
    summary_text = payload.summary_text.strip()
    if not summary_text:
        raise InvalidInputException("Summary text cannot be empty.")

    # Validate selected strategies if provided
    if payload.selected_strategies:
        unsupported = set(payload.selected_strategies) - SUPPORTED_STRATEGIES
        if unsupported:
            raise InvalidInputException(
                f"Unsupported perturbation strategy: {sorted(list(unsupported))}. "
                f"Supported strategies are: {sorted(list(SUPPORTED_STRATEGIES))}"
            )

    # Convert payload source_relations or extract relations from summary
    if payload.source_relations:
        doc_rels = [CausalRelation.from_dict(r) if isinstance(r, dict) else r for r in payload.source_relations]
    else:
        doc_rels = extractor.extract_relations(doc_id, summary_text)

    records, stats = generator.generate_perturbations(
        document_id=doc_id,
        summary_id=sum_id,
        summary_text=summary_text,
        doc_relations=doc_rels,
    )

    # Filter by selected strategies if specified
    if payload.selected_strategies:
        strats = set(payload.selected_strategies)
        records = [r for r in records if r.perturbation_type in strats]

    dto_records = [
        PerturbationDTO(
            perturbation_id=r.perturbation_id,
            document_id=r.document_id,
            summary_id=r.summary_id,
            strategy=r.perturbation_type,
            perturbation_type=r.perturbation_type,
            original_text=r.original_text,
            perturbed_text=r.perturbed_text,
            original_relation=r.original_relation,
            intended_relation=r.intended_relation,
            changed_span=r.changed_span,
            generation_method=r.generation_method,
            target_relation=r.intended_relation or r.original_relation,
        )
        for r in records
    ]

    return PerturbationGenerationResponse(
        document_id=doc_id,
        summary_id=sum_id,
        perturbations_count=len(dto_records),
        perturbations=dto_records,
        stats=stats,
    )


@router.post("/validate", response_model=PerturbationValidationResponse, summary="Validate Perturbation Quality")
async def validate_perturbations(
    payload: PerturbationValidationRequest,
    validator: PerturbationQualityValidator = Depends(get_quality_validator),
) -> PerturbationValidationResponse:
    """Validate quality control criteria for generated perturbation records using Phase 7 rules."""
    records = payload.records
    if not records:
        raise InvalidInputException("Records list for validation cannot be empty.")

    results: List[ValidationResultDTO] = []
    valid_count = 0
    invalid_count = 0

    for rec in records:
        v_rec = validator.validate_record(rec)
        is_valid = (v_rec.validation_status == "valid")
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        results.append(
            ValidationResultDTO(
                perturbation_id=v_rec.perturbation_id,
                is_valid=is_valid,
                validation_status=v_rec.validation_status,
                quality_score=1.0 if is_valid else 0.0,
                error_flags=v_rec.errors,
                warning_flags=v_rec.warnings,
                metrics=v_rec.checks,
            )
        )

    total = len(results)
    rate = round(valid_count / total, 4) if total > 0 else 0.0

    return PerturbationValidationResponse(
        total_examined=total,
        valid_count=valid_count,
        invalid_count=invalid_count,
        validation_rate=rate,
        results=results,
    )
