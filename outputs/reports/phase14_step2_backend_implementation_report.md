# Phase 14 — Step 2: FastAPI Backend Implementation Report

## Executive Summary
This report documents the implementation and validation of **Phase 14 Step 2: FastAPI Backend** for the **CausalFidelityPlus** research platform.

The FastAPI backend exposes the complete causal extraction, DiGraph construction, controlled perturbation generation, perturbation quality control, and causal fidelity metric evaluation pipeline (Phases 1–13) through a structured REST API under `/api/v1`. All endpoints rely strictly on canonical pipeline interfaces with thread-safe lazy singleton model loading for heavy neural metrics (SummaC, FactCC, BERTScore).

All 22 new API unit tests passed cleanly, and existing Phases 1–13 source code and research artifacts remain 100% untouched and preserved.

---

## 1. Directory & Package Structure

The backend package was created inside `src/causalfidelity/api/` as specified in the Phase 14 architecture plan:

```
src/causalfidelity/api/
├── __init__.py           # Package initialization & public exports
├── main.py               # FastAPI application instance, CORS, middleware, dev runner
├── dependencies.py       # Thread-safe lazy singleton dependencies & model status checks
├── schemas.py            # Pydantic v2 DTOs for requests and responses
├── exceptions.py         # Custom exception hierarchy & global HTTP exception handlers
└── routes/
    ├── __init__.py       # Route package initialization
    ├── health.py         # Light weight GET /api/v1/health check endpoint
    ├── causal.py         # POST /api/v1/causal/extract & POST /api/v1/causal/graph
    ├── perturbation.py   # POST /api/v1/perturbation/generate & POST /api/v1/perturbation/validate
    ├── evaluation.py     # POST /api/v1/evaluation/fidelity
    ├── pipeline.py       # POST /api/v1/pipeline/analyze
    └── reports.py        # GET /api/v1/reports/{report_type}
```

Unit tests were created under `tests/api/`:
- `tests/api/test_health_and_startup.py`
- `tests/api/test_causal_api.py`
- `tests/api/test_perturbation_api.py`
- `tests/api/test_evaluation_api.py`
- `tests/api/test_pipeline_api.py`
- `tests/api/test_reports_api.py`

---

## 2. API Endpoint Specifications

| Method | Endpoint | Description | Pipeline Integration |
|---|---|---|---|
| `GET` | `/api/v1/health` | Health check, component availability & model load status | `dependencies.check_models_loaded()` |
| `POST` | `/api/v1/causal/extract` | Rule-based causal relation extraction from source text | `RuleBasedCausalExtractor` |
| `POST` | `/api/v1/causal/graph` | Causal DiGraph construction & Mermaid visualization | `CausalGraphBuilder`, NetworkX |
| `POST` | `/api/v1/perturbation/generate` | Controlled causal perturbation generation | `PerturbationGenerator` |
| `POST` | `/api/v1/perturbation/validate` | Perturbation quality control & checks | `PerturbationQualityValidator` |
| `POST` | `/api/v1/evaluation/fidelity` | Causal faithfulness metric evaluation (SummaC, FactCC, BERTScore) | `SummaCConvMetric`, `FactCCMetric`, `BERTScoreMetric` |
| `POST` | `/api/v1/pipeline/analyze` | End-to-end multi-stage pipeline execution | Full pipeline orchestration |
| `GET` | `/api/v1/reports/{report_type}` | Strict allowlisted Phase 13 research report retrieval | Path-traversal-safe file loader |

---

## 3. Integrated Research Modules & Signatures

The API directly integrates with existing source packages without modifying underlying implementation logic:
- **Causal Extraction**: `src/causalfidelity/causal/rule_based.py` (`RuleBasedCausalExtractor.extract_relations`)
- **Graph Construction**: `src/causalfidelity/graph/builder.py` (`CausalGraphBuilder.build_graph`, `to_networkx`)
- **Perturbation Generation**: `src/causalfidelity/perturbation/generator.py` (`PerturbationGenerator.generate_perturbations`)
- **Quality Control**: `src/causalfidelity/validation/validator.py` (`PerturbationQualityValidator.validate_record`)
- **Fidelity Metrics**:
  - `src/causalfidelity/metrics/summac_conv.py` (`SummaCConvMetric.score`)
  - `src/causalfidelity/metrics/factcc_metric.py` (`FactCCMetric.score`)
  - `src/causalfidelity/metrics/bertscore_metric.py` (`BERTScoreMetric.score_detailed`)
- **Phase 13 Artifacts**:
  - `outputs/results/phase13_final_research_report.md`
  - `outputs/results/phase13_final_research_summary.json`
  - `outputs/results/ablation_execution_master_manifest.json`
  - `outputs/results/phase13_step4_results_analysis.md`

---

## 4. Lazy Model Loading & Dependency Strategy

To fulfill the constraint that light operations (health checks, causal relation extraction, graph generation, reports) must start instantly without downloading or initializing heavy neural models (transformers, torch, spacy, summac, factcc):

1. **Lazy Singleton Instantiation**: Heavy metric singletons (`_summac_instance`, `_factcc_instance`, `_bertscore_instance`) remain `None` until an explicit request to `/api/v1/evaluation/fidelity` or `/api/v1/pipeline/analyze` requires them.
2. **Thread Safety**: All getters (`get_summac_metric()`, `get_factcc_metric()`, `get_bertscore_metric()`) use a module-level `threading.Lock()` to prevent race conditions or duplicate parallel loads.
3. **Graceful Handling of Optional / Missing Dependencies**: If `transformers` or `torch` is not installed or model loading fails, `ModelNotAvailableException` is caught and returned in the JSON payload with `status: "UNAVAILABLE"` and an explicit error explanation without crashing the API or masking errors as zero.
4. **Metric Ablation**: Passing an empty list `enabled_metrics: []` explicitly marks metrics as `status: "ABLATED"` without loading any models.

---

## 5. Environment & Installed Dependencies

Existing project dependencies satisfied all FastAPI backend requirements:
- `fastapi` == 0.141.1
- `uvicorn` == 0.52.4
- `pydantic` == 2.13.5
- `httpx` == 0.28.1

No existing packages were upgraded or altered.

---

## 6. API Startup Instructions

To launch the FastAPI development server locally:

```bash
# Set PYTHONPATH to src directory
set PYTHONPATH=src

# Run uvicorn server
python -m causalfidelity.api.main
```

Alternatively using uvicorn directly:

```bash
uvicorn causalfidelity.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON Schema: `http://localhost:8000/api/v1/openapi.json`

---

## 7. Test Verification Results

### Summary Table
| Suite | Total Tests | Passed | Failed | Skipped | Duration |
|---|---|---|---|---|---|
| API Unit Tests (`tests/api/`) | 22 | 22 | 0 | 0 | ~1.25s |
| Complete Project Suite (`tests/`) | 291 | 291 | 0 | 0 | ~147.75s |

### API Test Suite Results (`tests/api/`)
- **Total API Tests**: 22
- **Passed**: 22
- **Failed**: 0
- **Skipped**: 0
- **Duration**: ~1.25s

Key tests verified:
1. `test_heavy_models_not_loaded_on_startup`: Confirms zero neural models loaded at startup.
2. `test_health_endpoint_success`: Validates status and component reporting.
3. `test_openapi_schema_generation`: Confirms valid OpenAPI JSON generation.
4. `test_extract_causal_relations_success`: Verifies rule-based relation extraction.
5. `test_build_causal_graph_from_text`: Verifies DiGraph and Mermaid syntax output.
6. `test_generate_perturbations_success`: Verifies 5-strategy perturbation generation.
7. `test_validate_perturbations_success`: Verifies quality control checks.
8. `test_fidelity_evaluation_ablated_metrics`: Verifies metric ablation behavior.
9. `test_fidelity_evaluation_mocked_metrics`: Verifies metric scoring and deltas.
10. `test_get_report_path_traversal_protection`: Verifies security against `../` path traversal.

### Full Test Suite Results
- **Baseline Tests (Phases 1–13)**: 269 passed
- **New API Tests (Phase 14 Step 2)**: 22 passed
- **Total Passing Tests**: 291 / 291 (100% pass rate)

---

## 8. Confirmations & Preservation Verification

1. **Phases 1–13 Source Code**: 100% UNTOUCHED. No edits made to any existing logic outside `src/causalfidelity/api/`.
2. **Phase 13 Research Artifacts**: 100% UNTOUCHED. All reports and manifests in `outputs/results/` remain unmodified.
3. **Frontend Isolation**: No React or frontend code was created in Step 2.
4. **Model Training / Benchmark Matrix**: No models retrained; no benchmark matrix re-runs.

---

## 9. Conclusion & Next Steps

Phase 14 Step 2 (FastAPI Backend) is fully implemented, verified, and complete.

**Status**: Ready for User Review & Approval before proceeding to **Phase 14 Step 3 (React Frontend Implementation)**.
