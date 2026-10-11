"""Fidelity evaluation routes for FastAPI API."""

from typing import Dict
from fastapi import APIRouter
from causalfidelity.api.dependencies import (
    get_bertscore_metric,
    get_factcc_metric,
    get_summac_metric,
)
from causalfidelity.api.exceptions import InvalidInputException, ModelNotAvailableException
from causalfidelity.api.schemas import (
    FidelityEvaluationRequest,
    FidelityEvaluationResponse,
    MetricScoreDTO,
)

router = APIRouter(prefix="/evaluation", tags=["Causal Fidelity Evaluation"])

SUPPORTED_METRICS = {"summac", "factcc", "bertscore"}


@router.post("/fidelity", response_model=FidelityEvaluationResponse, summary="Evaluate Causal Faithfulness Metrics")
async def evaluate_fidelity(payload: FidelityEvaluationRequest) -> FidelityEvaluationResponse:
    """Evaluate NLI and embedding faithfulness metrics (SummaC, FactCC, BERTScore) using lazy singleton model loading."""
    source_text = payload.source_text.strip()
    original_summary = payload.original_summary.strip()
    perturbed_summary = payload.perturbed_summary.strip()

    if not source_text or not original_summary or not perturbed_summary:
        raise InvalidInputException("Source text, original summary, and perturbed summary must all be non-empty.")

    enabled = set(payload.enabled_metrics) if payload.enabled_metrics is not None else {"summac", "factcc", "bertscore"}
    unsupported = enabled - SUPPORTED_METRICS
    if unsupported:
        raise InvalidInputException(
            f"Unsupported metric names requested: {sorted(list(unsupported))}. "
            f"Supported metrics are: {sorted(list(SUPPORTED_METRICS))}"
        )

    results: Dict[str, MetricScoreDTO] = {}

    # 1. SummaCConv Metric Evaluation
    if "summac" in enabled:
        try:
            summac_m = get_summac_metric()
            orig_s = summac_m.score(source_text, original_summary)
            pert_s = summac_m.score(source_text, perturbed_summary)
            delta = round(orig_s - pert_s, 4)
            results["summac"] = MetricScoreDTO(
                metric_name="SummaCConv",
                status="SUCCESS",
                original_score=round(orig_s, 4),
                perturbed_score=round(pert_s, 4),
                score_delta=delta,
                metadata=summac_m.get_metadata() if hasattr(summac_m, "get_metadata") else None,
            )
        except ModelNotAvailableException as err:
            results["summac"] = MetricScoreDTO(
                metric_name="SummaCConv",
                status="UNAVAILABLE",
                metadata={"reason": err.message},
            )
        except Exception as err:
            results["summac"] = MetricScoreDTO(
                metric_name="SummaCConv",
                status="FAILED",
                metadata={"error": str(err)},
            )
    else:
        results["summac"] = MetricScoreDTO(metric_name="SummaCConv", status="ABLATED")

    # 2. FactCC Metric Evaluation
    if "factcc" in enabled:
        try:
            factcc_m = get_factcc_metric()
            orig_f = factcc_m.score(source_text, original_summary)
            pert_f = factcc_m.score(source_text, perturbed_summary)
            delta_f = round(orig_f - pert_f, 4)
            results["factcc"] = MetricScoreDTO(
                metric_name="FactCC",
                status="SUCCESS",
                original_score=round(orig_f, 4),
                perturbed_score=round(pert_f, 4),
                score_delta=delta_f,
                metadata=factcc_m.get_metadata() if hasattr(factcc_m, "get_metadata") else None,
            )
        except ModelNotAvailableException as err:
            results["factcc"] = MetricScoreDTO(
                metric_name="FactCC",
                status="UNAVAILABLE",
                metadata={"reason": err.message},
            )
        except Exception as err:
            results["factcc"] = MetricScoreDTO(
                metric_name="FactCC",
                status="FAILED",
                metadata={"error": str(err)},
            )
    else:
        results["factcc"] = MetricScoreDTO(metric_name="FactCC", status="ABLATED")

    # 3. BERTScore Metric Evaluation
    if "bertscore" in enabled:
        try:
            bertscore_m = get_bertscore_metric()
            bs_res = bertscore_m.score_detailed(original_summary, perturbed_summary)
            results["bertscore"] = MetricScoreDTO(
                metric_name="BERTScore",
                status="SUCCESS",
                bertscore_precision=round(bs_res.get("bertscore_precision", 0.0), 4),
                bertscore_recall=round(bs_res.get("bertscore_recall", 0.0), 4),
                bertscore_f1=round(bs_res.get("bertscore_f1", 0.0), 4),
                similarity_loss=round(bs_res.get("similarity_loss", 0.0), 4),
                metadata=bertscore_m.get_metadata() if hasattr(bertscore_m, "get_metadata") else None,
            )
        except ModelNotAvailableException as err:
            results["bertscore"] = MetricScoreDTO(
                metric_name="BERTScore",
                status="UNAVAILABLE",
                metadata={"reason": err.message},
            )
        except Exception as err:
            results["bertscore"] = MetricScoreDTO(
                metric_name="BERTScore",
                status="FAILED",
                metadata={"error": str(err)},
            )
    else:
        results["bertscore"] = MetricScoreDTO(metric_name="BERTScore", status="ABLATED")

    return FidelityEvaluationResponse(
        source_text=source_text,
        original_summary=original_summary,
        perturbed_summary=perturbed_summary,
        metrics=results,
    )
