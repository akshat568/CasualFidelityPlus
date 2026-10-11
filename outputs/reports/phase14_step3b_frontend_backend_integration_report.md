# Phase 14 Step 3B — Frontend & Backend Integration Report

## 1. Executive Summary
Phase 14 Step 3B connects the existing React frontend (Step 3A) to the existing FastAPI backend (Step 2). The Causal Workbench and Settings pages have been fully refactored from static mock handlers to consume real REST endpoints via a single centralized API client (`src/services/api.ts`). Crucially, state management bugs in the Workbench—where perturbations were generated automatically on page load or strategy dropdown changes—have been fixed.

- **Frontend API Client**: Implemented in `frontend/src/services/api.ts` with configurable base URL (defaulting to `http://localhost:8000/api/v1` or `VITE_API_BASE_URL` or `localStorage`).
- **Workbench Actions**: "Extract Causal Relations", "Generate Perturbation", and "Evaluate Metrics" now execute live HTTP requests strictly upon user button interaction.
- **Settings Page**: Integrated "Test Connection" button calling `GET /api/v1/health` with live operational status and model availability diagnostics.
- **Verification**: 291 backend pytest tests passed (22 API route unit tests passed), TypeScript build succeeded (`npm run build`), and live end-to-end HTTP integration tests against running uvicorn server succeeded across all endpoints.

---

## 2. Files Inspected & Changed

### Files Inspected:
- **Backend**:
  - `src/causalfidelity/api/main.py`
  - `src/causalfidelity/api/schemas.py`
  - `src/causalfidelity/api/dependencies.py`
  - `src/causalfidelity/api/exceptions.py`
  - `src/causalfidelity/api/routes/health.py`
  - `src/causalfidelity/api/routes/causal.py`
  - `src/causalfidelity/api/routes/perturbation.py`
  - `src/causalfidelity/api/routes/evaluation.py`
  - `src/causalfidelity/api/routes/pipeline.py`
  - `src/causalfidelity/api/routes/reports.py`
  - `src/causalfidelity/validation/validator.py`
- **Frontend**:
  - `frontend/src/App.tsx`
  - `frontend/src/types/index.ts`
  - `frontend/src/pages/WorkbenchPage.tsx`
  - `frontend/src/pages/SettingsPage.tsx`
  - `frontend/src/components/common/AppSidebar.tsx`
  - `frontend/src/components/workbench/TextInputPanel.tsx`
  - `frontend/src/components/workbench/CausalRelationTable.tsx`
  - `frontend/src/components/workbench/CausalGraphVisualizer.tsx`
  - `frontend/src/components/workbench/PerturbationPanel.tsx`
  - `frontend/src/components/workbench/DiffViewer.tsx`
  - `frontend/src/components/workbench/ValidationPanel.tsx`
  - `frontend/src/components/workbench/FidelityPanel.tsx`
  - `frontend/src/mock/mockData.ts`

### Files Created/Modified:
- **Created**:
  - `frontend/src/types/api.ts` (Typed interfaces matching FastAPI Pydantic schemas)
  - `frontend/src/services/api.ts` (Centralized HTTP API client helper functions)
  - `frontend/src/utils/diff.ts` (Word-level diff computation algorithm for original vs perturbed text)
  - `outputs/reports/phase14_step3b_frontend_backend_integration_report.md` (This report)
- **Modified**:
  - `frontend/src/types/index.ts` (Exported API DTOs alongside UI interfaces)
  - `frontend/src/pages/WorkbenchPage.tsx` (Refactored to live API client with decoupled states)
  - `frontend/src/pages/SettingsPage.tsx` (Connected to live `/health` endpoint and persistent API URL)
  - `frontend/src/App.tsx` (Maintained live API health state and connection status)
  - `frontend/src/components/common/AppSidebar.tsx` (Updated live connection status indicator)
  - `frontend/src/components/workbench/DiffViewer.tsx` (Handled pending/un-generated states)
  - `frontend/src/components/workbench/ValidationPanel.tsx` (Handled un-evaluated validation states)

---

## 3. Discovered FastAPI API Contracts

The following 8 endpoints in the FastAPI backend (`/api/v1`) were identified and integrated:

| Method | Endpoint Path | Request Schema | Response Schema | Purpose |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | None | `HealthResponse` | Operational status, version, component availability |
| `POST` | `/api/v1/causal/extract` | `CausalExtractionRequest(text, document_id?)` | `CausalExtractionResponse` | Rule-based causal relation extraction |
| `POST` | `/api/v1/causal/graph` | `CausalGraphRequest(document_id?, text?, relations?)` | `CausalGraphResponse` | NetworkX DiGraph & Mermaid.js code generation |
| `POST` | `/api/v1/perturbation/generate` | `PerturbationGenerationRequest(summary_text, source_relations?, selected_strategies?)` | `PerturbationGenerationResponse` | Controlled causal perturbation generation |
| `POST` | `/api/v1/perturbation/validate` | `PerturbationValidationRequest(records)` | `PerturbationValidationResponse` | Quality control checks (structural, relational, content) |
| `POST` | `/api/v1/evaluation/fidelity` | `FidelityEvaluationRequest(source_text, original_summary, perturbed_summary, enabled_metrics?)` | `FidelityEvaluationResponse` | SummaC, FactCC, and BERTScore metric evaluation |
| `POST` | `/api/v1/pipeline/analyze` | `PipelineAnalyzeRequest(...)` | `PipelineAnalyzeResponse` | End-to-end pipeline execution |
| `GET` | `/api/v1/reports/{report_type}` | Path param | `ReportResponse` | Phase 13 research report/summary retrieval |

---

## 4. Centralized API Client Implementation

The centralized API client in `frontend/src/services/api.ts` provides typed async methods:
- `healthCheck(customBaseUrl?: string): Promise<HealthResponse>`
- `extractCausalRelations(text: string, documentId?: string): Promise<CausalExtractionResponse>`
- `buildCausalGraph(payload: CausalGraphRequest): Promise<CausalGraphResponse>`
- `generatePerturbation(payload: PerturbationGenerationRequest): Promise<PerturbationGenerationResponse>`
- `validatePerturbation(payload: PerturbationValidationRequest): Promise<PerturbationValidationResponse>`
- `evaluateFidelity(payload: FidelityEvaluationRequest): Promise<FidelityEvaluationResponse>`
- `analyzePipeline(payload: PipelineAnalyzeRequest): Promise<PipelineAnalyzeResponse>`
- `getReport(reportType: string): Promise<ReportResponse>`

### Base URL Resolution Hierarchy:
1. `localStorage.getItem('causalfidelity_api_base_url')`
2. `import.meta.env.VITE_API_BASE_URL`
3. Fallback default: `http://localhost:8000/api/v1`

---

## 5. Workbench Integration & State Isolation Details

The previous Workbench implementation incorrectly updated perturbed text and evaluated metrics automatically on dropdown selection or initial page load.

### Refactored State Architecture:
1. **Initial State**:
   - `relations`: `[]` (Empty)
   - `graphData`: `{ nodes: [], edges: [], isDag: true, mermaidCode: 'graph TD' }`
   - `selectedStrategy`: `'REVERSED'` (Dropdown selection state only)
   - `generatedPerturbation`: `null` (No perturbed text displayed)
   - `validationResult`: `null` (Not evaluated)
   - `metrics`: Initial placeholders with status `'NOT_EVALUATED'`
   - **No automatic API calls on page mount.**
2. **Strategy Dropdown Change**:
   - Updates `selectedStrategy` variable ONLY.
   - Does NOT trigger `generatePerturbation` API call.
   - Does NOT alter the displayed perturbed text or validation/fidelity cards.
3. **"Extract Causal Relations" Click**:
   - Triggers `extractCausalRelations(sourceText)`.
   - Populates extracted relations table.
   - Automatically constructs NetworkX DiGraph via `buildCausalGraph`.
4. **"Generate Perturbation" Click**:
   - Triggers `generatePerturbation(sourceText, relations, selectedStrategy)`.
   - Updates `generatedPerturbation` with returned perturbed text and highlights word diffs.
   - Automatically validates perturbation quality via `validatePerturbation`.
   - Resets stale fidelity metrics to `'NOT_EVALUATED'`.
5. **"Evaluate Metrics" Click**:
   - Requires an active generated perturbation.
   - Triggers `evaluateFidelity(sourceText, sourceText, perturbedText)`.
   - Displays real backend scores for SummaCConv, FactCC, and BERTScore.

---

## 6. Removal of Mock Data from Live Workflows

- Live Workbench workflows (Extraction, Graph, Perturbation, Validation, Evaluation) no longer use mock fallbacks.
- Static research pages (Research Dashboard, Experiment Explorer, Reports) continue to utilize Phase 13 findings without interfering with live Workbench operations.
- API network or backend errors present structured error banners (`ApiError`) rather than falling back to fake responses.

---

## 7. CORS Verification

Backend CORS configuration in `src/causalfidelity/api/main.py`:
```python
def get_cors_origins() -> List[str]:
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
```
This permits standard local development origins (`http://localhost:5173`, `http://127.0.0.1:5173`) with full credential and method support without using `allow_origins=["*"]`.

---

## 8. Verification Results & Test Execution Summary

### A. TypeScript Build Verification
Command: `npm run build` (in `frontend/`)
- Status: **PASSED (Exit code 0)**
- Modules transformed: 2,493
- Output bundles generated: `dist/assets/index-lrLR1NsP.js` (711 kB), `dist/assets/index-D1i14Rfp.css` (29.8 kB).

### B. Automated Backend Test Suite
Command: `$env:PYTHONPATH="src"; python -m pytest`
- Status: **PASSED (Exit code 0)**
- Results: **291 passed, 0 failures, 18 warnings in 115.99s**
- API Route Unit Tests (`tests/api/`): **22 passed, 0 failures in 1.09s**

### C. Live FastAPI HTTP Integration Testing
A live uvicorn process was started on `http://127.0.0.1:8000`, and an end-to-end integration client script was executed against the running backend server.

| Step | Operation | Endpoint | Status | Result / Output |
|---|---|---|---|---|
| 1 | Health Check | `GET /api/v1/health` | **200 OK** | `status: "healthy", version: "1.0.0"` |
| 2 | Causal Extraction | `POST /api/v1/causal/extract` | **200 OK** | `1 relation extracted ("Heavy rainfall" -> causes -> "the river to overflow")` |
| 3 | Graph Construction | `POST /api/v1/causal/graph` | **200 OK** | `node_count: 2, edge_count: 1, is_dag: True, Mermaid code generated` |
| 4 | Perturbation Generation | `POST /api/v1/perturbation/generate` | **200 OK** | `1 REVERSED perturbation ("The river to overflow caused heavy rainfall...")` |
| 5 | Quality Validation | `POST /api/v1/perturbation/validate` | **200 OK** | `Sub-checks evaluated (target_transformation: passed)` |
| 6 | Fidelity Evaluation | `POST /api/v1/evaluation/fidelity` | **200 OK** | `SummaC (orig=0.4500, pert=0.4509), FactCC (orig=0.9999, pert=0.9996), BERTScore evaluated` |
| 7 | Report Retrieval | `GET /api/v1/reports/phase13_report` | **200 OK** | `Retrieved 23,628 char markdown report` |

---

## 9. Preservation of Prior Artifacts
All Phase 1–13 scientific logic, experimental manifests, baseline datasets, and research report artifacts in `outputs/results/` remain untouched and intact.

---

## 10. Conclusion
Phase 14 Step 3B integration is complete and verified. The React frontend is fully connected to the FastAPI backend with clean state isolation and robust error handling.
