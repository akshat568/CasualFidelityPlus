"""Research report and artifact retrieval routes for FastAPI API."""

import json
from pathlib import Path
from fastapi import APIRouter
from causalfidelity.api.exceptions import InvalidInputException, ResourceNotFoundException
from causalfidelity.api.schemas import ReportResponse

router = APIRouter(prefix="/reports", tags=["Research Reports & Artifacts"])

# Strict allowlist of approved report types mapped to absolute path relative to project root
REPORT_ALLOWLIST = {
    "phase13_report": {
        "title": "Final Research Report (Markdown)",
        "file_path": Path("outputs/results/phase13_final_research_report.md"),
        "content_type": "text/markdown",
    },
    "phase13_summary": {
        "title": "Final Research Summary (JSON)",
        "file_path": Path("outputs/results/phase13_final_research_summary.json"),
        "content_type": "application/json",
    },
    "ablation_manifest": {
        "title": "Ablation Execution Master Manifest (JSON)",
        "file_path": Path("outputs/results/ablation_execution_master_manifest.json"),
        "content_type": "application/json",
    },
    "step4_analysis": {
        "title": "Research Findings Analysis (Markdown)",
        "file_path": Path("outputs/results/phase13_step4_results_analysis.md"),
        "content_type": "text/markdown",
    },
}


@router.get("/{report_type}", response_model=ReportResponse, summary="Retrieve Research Artifact")
async def get_report(report_type: str) -> ReportResponse:
    """Retrieve research reports, summaries, or master manifests using strict allowlist path protection."""
    clean_type = report_type.strip().lower()

    # Path traversal protection: disallow slash or dotdot
    if "/" in clean_type or "\\" in clean_type or ".." in clean_type:
        raise InvalidInputException("Invalid report type specified. Path traversal is strictly prohibited.")

    if clean_type not in REPORT_ALLOWLIST:
        supported = sorted(list(REPORT_ALLOWLIST.keys()))
        raise InvalidInputException(
            f"Unsupported report type '{report_type}'. Supported report types are: {supported}"
        )

    info = REPORT_ALLOWLIST[clean_type]
    file_path = info["file_path"]

    if not file_path.exists():
        raise ResourceNotFoundException(f"Report artifact file '{file_path}' does not exist on server.")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if info["content_type"] == "application/json":
                data = json.load(f)
            else:
                data = f.read()
    except Exception as err:
        raise ResourceNotFoundException(f"Failed to read report file '{file_path}': {err}")

    return ReportResponse(
        report_type=clean_type,
        title=info["title"],
        file_name=file_path.name,
        content_type=info["content_type"],
        data=data,
    )
