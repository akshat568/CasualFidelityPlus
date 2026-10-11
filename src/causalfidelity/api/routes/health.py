"""Health check route for CausalFidelityPlus API."""

from datetime import datetime, timezone
from fastapi import APIRouter
from causalfidelity.api import __version__
from causalfidelity.api.dependencies import check_models_loaded
from causalfidelity.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="API Health Check")
async def health_check() -> HealthResponse:
    """Return system operational status and model availability without loading neural models."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        components_available={
            "causal_extractor": True,
            "graph_builder": True,
            "perturbation_generator": True,
            "quality_validator": True,
        },
        models_loaded=check_models_loaded(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
