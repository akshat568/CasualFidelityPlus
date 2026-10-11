# Phase 14: Comprehensive Mock-Data and Placeholder Audit & Real Data Integration Report

**Project**: CausalFidelityPlus — LLM Causal Distortion Research Platform  
**Phase**: Phase 14 (Data Integrity, Genuine Artifact Grounding & Live API Integration)  
**Date**: October 11, 2026  
**Status**: Completed & Verified  

---

## 1. Executive Summary

This audit establishes **complete data integrity** across the entire CausalFidelityPlus platform by eliminating fabricated, hardcoded, simulated, or silent-fallback demonstration data from the production application. Every page, metric card, chart visualization, data table, configuration modal, interactive workflow, and report viewer is now coupled directly to:
1. **The Live FastAPI Backend Server** (`/api/v1/*` endpoints) for causal extraction, DiGraph construction, controlled perturbation generation, quality validation, fidelity evaluation, system diagnostics, and artifact serving.
2. **Authoritative Phase 13 Research Artifacts** (`phase13_final_research_summary.json`, `phase13_controlled_distortion_stress_test_report.md`, `phase13_ablation_manifest.json`, and `step4_phase13_findings_analysis.json`) for empirical metrics, ablation matrices, sensitivity curves, human validation findings, and scientific boundaries.

Zero production components import from mock data files. When API endpoints or research artifacts are unavailable, the application renders explicit, honest error banners and retry mechanisms rather than silently falling back to simulated values.

---

## 2. Audit Scope & Mock-Data Elimination

A global search and systematic audit was conducted across the codebase covering:
- **`frontend/src/mock/mockData.ts`**: Formerly imported by 5 production pages and 4 dashboard/research chart components.
- **Hardcoded metrics**: Fabricated alignment scores, runtimes, and validation status flags.
- **Static chart series**: Static arrays presented as experimental results.
- **Silent fallback logic**: Catch blocks substituting mock data on network errors.
- **Mock images and assets**: Audited for placeholder screenshots or synthetic illustrations.

### Key Changes Made
1. **Zero Production Imports**: All production components (`DashboardPage`, `ResearchPage`, `ExplorerPage`, `ReportsPage`, `WorkbenchPage`, `AlignmentChart`, `WeightSensitivityChart`, `MetricAblationChart`, `ResearchLimitationsCard`, and `ExperimentSummaryTable`) were decoupled from `mockData.ts`.
2. **Prop-Driven Visualizations**: All charts and summary cards were refactored into prop-driven components that accept genuine data with native loading skeletons and empty states.
3. **No Silent Fallback**: Handlers now propagate authentic errors with user-facing retry actions. If the backend is offline, the interface explicitly displays "Research Data Unavailable" or "Connection Failed" rather than faking success.
4. **Authentic Artifact Serving**: The Reports page no longer renders hardcoded `contentPreview` strings. It calls `/api/v1/reports/{report_type}` to stream verified Phase 13 Markdown and JSON deliverables directly from disk.
5. **Test Fixture Isolation**: `frontend/src/mock/mockData.ts` was marked `@deprecated`, `IS_MOCK_MODE` was set to `false`, and the file was isolated strictly for offline unit test reference.

---

## 3. Data Source Traceability Matrix

| Page / Route | Component / Feature | Previous State | Current Authentic Data Source | API Endpoint or Artifact Path | Real Data Values / Contract |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dashboard** (`/`) | Total Experiments Card | Static `9` | `report_metadata.total_experiments` | `GET /api/v1/reports/phase13_summary` | `9` (Matrix runs: EXP_01–EXP_09) |
| **Dashboard** (`/`) | Baseline Alignment Card | Static `0.3195` | `EXP_01_BASELINE.metrics.mean_overall_alignment_score` | `GET /api/v1/reports/phase13_summary` | `0.3195` (XSum causal benchmark) |
| **Dashboard** (`/`) | Benchmark Agreement Card | Static `83.33%` | `EXP_01_BASELINE.metrics.benchmark_agreement_rate` | `GET /api/v1/reports/phase13_summary` | `83.33%` (5 of 6 examples agreement) |
| **Dashboard** (`/`) | Human Consensus Pairs Card | Static `6` | `EXP_09_HUMAN_CORRELATION.human_validation_results.consensus_records_analyzed` | `GET /api/v1/reports/phase13_summary` | `6` pairs (6 disagreement excluded) |
| **Dashboard** (`/`) | Alignment Comparison Chart | Static fixture array | Derived from matrix entries `EXP_01`–`EXP_09` | `GET /api/v1/reports/phase13_summary` | Real alignment values (0.3195, 0.5010, 0.2525, etc.) |
| **Dashboard** (`/`) | Weight Sensitivity Chart | Static fixture array | Real scores from `EXP_01`, `EXP_04`, `EXP_05` | `GET /api/v1/reports/phase13_summary` | Equal: `+56.81%`, Arg-only: `-20.97%` |
| **Dashboard** (`/`) | Metric Ablation Runtime Chart | Static fixture array | Runtimes from `EXP_06`, `EXP_07`, `EXP_08` vs total | `GET /api/v1/reports/phase13_summary` | SummaC ablated: `147.3s` (`-79.17%`, 4.8x faster) |
| **Workbench** (`/workbench`) | Causal Relation Extraction | Default text | Extraction Engine via spaCy & connective matcher | `POST /api/v1/causal/extract` | Live cause, effect, connective & confidence scores |
| **Workbench** (`/workbench`) | Causal DiGraph Visualizer | None / Empty | NetworkX DiGraph builder | `POST /api/v1/causal/graph` | Live nodes, edges, DAG cycle check, Mermaid syntax |
| **Workbench** (`/workbench`) | Perturbation Generator | Simulated text | Controlled perturbation strategies | `POST /api/v1/perturbation/generate` | Live mutated sentences & word-level diffs |
| **Workbench** (`/workbench`) | Quality Validation Panel | Hardcoded 'PASSED' | Rule-based quality validator | `POST /api/v1/perturbation/validate` | Structural, relational, content preservation flags |
| **Workbench** (`/workbench`) | Causal Fidelity Evaluator | Hardcoded mock | Lazy neural evaluation models | `POST /api/v1/evaluation/fidelity` | SummaC, FactCC, BERTScore original/perturbed deltas |
| **Research Dashboard** (`/research`) | Ablation Experiments Table | Static array | Full matrix entries (`EXP_01`–`EXP_09`) | `GET /api/v1/reports/phase13_summary` | 9 real runs with runtimes and alignment |
| **Research Dashboard** (`/research`) | Human Validation Analysis | Static card | `EXP_09` human validation data | `GET /api/v1/reports/phase13_summary` | Pearson $r = -0.3162$, n=6 consensus pairs |
| **Research Dashboard** (`/research`) | Research Limitations & Scope | Static list | `confirmed_limitations` array | `GET /api/v1/reports/phase13_summary` | 5 authoritative documented scientific constraints |
| **Explorer** (`/experiments`) | Experiment Search & Filter | Static array | Live filter over matrix records | `GET /api/v1/reports/phase13_summary` | Dynamic filtering across 9 genuine experiment runs |
| **Explorer** (`/experiments`) | Inspect Modal | Static single record | Dynamically selected experiment entity | `GET /api/v1/reports/phase13_summary` | Specific config, active metrics, alignment & runtime |
| **Reports** (`/reports`) | Report Catalog & Inspection | Hardcoded previews | Real filesystem artifacts served via FastAPI | `GET /api/v1/reports/{report_type}` | Full Phase 13 Markdown and JSON payloads |
| **Settings** (`/settings`) | API Health & Submodule Status | Hardcoded 'Connected' | Live health probe | `GET /api/v1/health` | FastAPI version, timestamps, 4 component states |

---

## 4. Architecture of the Real Data Pipeline

### 4.1 Research Service (`frontend/src/services/researchService.ts`)
A dedicated service connects all analytical views directly to the FastAPI `/api/v1/reports/phase13_summary` endpoint.
- **Atomic Caching & Request Coalescing**: Prevents redundant HTTP fetches across route switches while ensuring in-flight requests are reused.
- **In-Memory Cache Invalidation**: Provides explicit `forceRefresh` and `invalidateResearchCache()` hooks powered by the "Refresh" buttons on the Dashboard, Research, and Explorer pages.
- **Fail-Fast Error Handling**: Throws `ApiError` on network or server failure. Never defaults or falls back to synthetic data.

### 4.2 Reports Service (`frontend/src/services/api.ts` & `ReportsPage.tsx`)
The backend provides a secure allowlist in `src/causalfidelity/api/routes/reports.py` mapping report identifiers to verified files in `outputs/results/` and `outputs/reports/`:
- `phase13_report`: `outputs/reports/phase13_controlled_distortion_stress_test_report.md`
- `phase13_summary`: `outputs/results/phase13_final_research_summary.json`
- `ablation_manifest`: `outputs/results/phase13_ablation_manifest.json`
- `step4_analysis`: `outputs/results/step4_phase13_findings_analysis.json`

The frontend loads these payloads asynchronously on click, rendering full markdown or indented JSON with clipboard export and live source traceability.

---

## 5. Visual Asset & Media Audit

- **Zero Mock Images**: A complete repository audit confirmed **0** mock images, placeholder `.png`/`.jpg` screenshots, or synthetic diagrams in the production code.
- **Native SVG & Dynamic Charting**:
  - UI icons are rendered dynamically via `lucide-react`.
  - Analytical charts are drawn via Recharts SVGs driven directly by genuine numerical scores.
  - Causal graph flow diagrams are rendered via NetworkX node-link data structures with Mermaid integration.

---

## 6. Files Inspected and Modified

| File | Change Category | Description of Modification |
| :--- | :--- | :--- |
| `frontend/src/services/researchService.ts` | **New Service** | Implemented service to fetch and parse `/api/v1/reports/phase13_summary`, providing strongly typed structures for dashboard, matrix, sensitivity, ablation, and human validation. |
| `frontend/src/components/dashboard/AlignmentChart.tsx` | **Refactoring** | Decoupled from `mockData.ts`. Added props `data?: AlignmentComparisonItem[]`, `baselineScore?: number`, and `isLoading?: boolean` with empty/skeleton states. |
| `frontend/src/components/dashboard/WeightSensitivityChart.tsx` | **Refactoring** | Decoupled from `mockData.ts`. Added props `data?: WeightSensitivityItem[]` and `isLoading?: boolean` with dynamic callouts for Equal and Arg-Only weights. |
| `frontend/src/components/dashboard/MetricAblationChart.tsx` | **Refactoring** | Decoupled from `mockData.ts`. Added props `data?: MetricAblationItem[]` and `isLoading?: boolean` rendering actual execution savings. |
| `frontend/src/components/research/HumanValidationCard.tsx` | **Refactoring** | Added props `data?: HumanValidationData` and `isLoading?: boolean`. Dynamically renders consensus pairs, disagreement exclusions, and naturalness correlation. |
| `frontend/src/components/research/ResearchLimitationsCard.tsx` | **Refactoring** | Decoupled from `mockData.ts`. Added props `limitations?: ResearchLimitationItem[]` and `isLoading?: boolean`. |
| `frontend/src/components/research/ExperimentSummaryTable.tsx` | **Refactoring** | Added `isLoading?: boolean` prop and empty table states for real data loading. |
| `frontend/src/pages/DashboardPage.tsx` | **Data Integration** | Decoupled from `mockData.ts`. Wired to `fetchResearchData()`, with loading skeletons, error banner with retry, and dynamic chart props. |
| `frontend/src/pages/ResearchPage.tsx` | **Data Integration** | Decoupled from `mockData.ts`. Wired to `fetchResearchData()`, passing real matrix, sensitivity, and human validation findings. |
| `frontend/src/pages/ExplorerPage.tsx` | **Data Integration** | Decoupled from `mockData.ts`. Filters and inspects genuine experiment runs loaded from `researchService.ts`. |
| `frontend/src/pages/ReportsPage.tsx` | **Data Integration** | Decoupled from `mockData.ts`. Implemented on-demand live fetching via `getReport(id)` for full markdown and JSON artifact inspection. |
| `frontend/src/pages/WorkbenchPage.tsx` | **Decoupling** | Removed `mockData.ts` import. Defined initial benchmark test prompt locally; preserved existing live FastAPI endpoints. |
| `frontend/src/types/index.ts` | **Type Update** | Made `contentPreview?: string` optional on `ResearchReportItem` to reflect on-demand live loading. |
| `frontend/src/mock/mockData.ts` | **Isolation** | Marked `@deprecated`, set `IS_MOCK_MODE = false`, and added explicit warnings preventing future production imports. |

---

## 7. Verification Results

### 7.1 Frontend Production Build
```bash
> tsc -b && vite build
✓ 2493 modules transformed.
dist/index.html                   0.89 kB │ gzip:   0.52 kB
dist/assets/index-BxUnYxj2.css   31.90 kB │ gzip:   6.70 kB
dist/assets/index-BTogS-p_.js   722.71 kB │ gzip: 209.86 kB
✓ built in 1.14s
Exit code: 0
```
- **Result**: Production bundle generated cleanly with zero TypeScript errors.

### 7.2 Backend & Research Unit Test Suite
```bash
$env:PYTHONPATH="src"; pytest
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collected 292 items

tests\api\test_causal_api.py ....                                        [  1%]
tests\api\test_evaluation_api.py ...                                     [  2%]
tests\api\test_health_and_startup.py ...                                 [  3%]
tests\api\test_perturbation_api.py ....                                  [  4%]
tests\api\test_pipeline_api.py ..                                        [  5%]
tests\api\test_reports_api.py ......                                     [  7%]
tests\test_ablation_harness.py ...........                               [ 11%]
tests\test_alignment.py ..................                               [ 17%]
tests\test_benchmark_expansion.py ..............                         [ 22%]
tests\test_causal_extraction.py ..........                               [ 25%]
tests\test_causal_graph.py ..........                                    [ 29%]
tests\test_data_pipeline.py .......                                      [ 31%]
tests\test_distortion_detection.py ........................              [ 39%]
tests\test_experiment_config.py ..........                               [ 43%]
tests\test_experiment_runner.py .......                                  [ 45%]
tests\test_perturbation.py .................                             [ 51%]
tests\test_perturbation_validation.py ......................             [ 58%]
tests\test_phase10a_summac.py .......                                    [ 61%]
tests\test_phase10b_factcc.py .........                                  [ 64%]
tests\test_phase10c_bertscore.py ............                            [ 68%]
tests\test_phase10d_analysis.py ..................                       [ 74%]
tests\test_phase12_agreement.py ..............                           [ 79%]
tests\test_phase12_annotation.py ..............                          [ 84%]
tests\test_phase12_correlation.py ..................                     [ 90%]
tests\test_phase12_pipeline.py ..............                            [ 95%]
tests\test_setup.py ....                                                 [ 96%]
tests\test_summary_input.py ..........                                   [100%]

================ 292 passed, 18 warnings in 145.05s (0:02:25) =================
Exit code: 0
```
- **Result**: **292 of 292 tests passed** (100% pass rate). All core algorithms, ablation harness, metric calculators, and FastAPI routes remain intact.

### 7.3 Multi-Route Visual & Interactive Verification
A complete end-to-end browser verification verified all 6 routes:
1. **`/` (Dashboard Overview)**: Verified 4 metric cards (`9` experiments, `0.3195` baseline, `83.33%` agreement, `6` consensus pairs) and 3 Recharts SVGs.
2. **`/workbench` (Interactive Causal Workbench)**: Extracted relation (`Heavy rainfall` $\rightarrow$ `river overflow`, confidence `90%`), verified DiGraph DAG render, confirmed initial/empty evaluation states.
3. **`/research` (Research Dashboard)**: Verified 9 matrix rows; opened `EXP_01_BASELINE` detail modal confirming runtime (`707.0s`) and mean alignment (`0.3195`).
4. **`/experiments` (Experiment Explorer)**: Filtered live table by `EXP_06`; opened inspection modal confirming SummaC ablation metrics (runtime reduction `79.17%`, 4.8x speedup).
5. **`/reports` (Research Reports)**: Opened `phase13_controlled_distortion_stress_test_report.md` in live modal, verifying full markdown payload served live via FastAPI.
6. **`/settings` (System Settings)**: Verified live health probe returned `CONNECTED` with green indicator, `v1.0.0`, and all 4 submodules (`extraction`, `perturbation`, `validation`, `evaluation`) marked `READY`.

---

## 8. Remaining Gaps & Research Boundaries

In accordance with scientific integrity guidelines, the following authentic system boundaries are documented:
1. **Lazy Neural Model Startup Latency**:
   - The interactive workbench evaluates RoBERTa-large (SummaC), FactCC, and BERTScore on demand via PyTorch/HuggingFace. First-time evaluations incur lazy neural model loading latency. The UI accurately displays `NOT_EVALUATED` until the user explicitly requests evaluation.
2. **Zero-Variance Vector in Human Validation**:
   - As documented in `EXP_09`, binary distortion correlation is mathematically undefined because the curated human consensus sample possessed a constant target vector (all positive label `1.0`). Continuous naturalness correlation ($r = -0.3162$) is faithfully displayed instead.
3. **Explicit Connective Parsing Boundary**:
   - The causal extraction engine detects overt discourse connectives (`because`, `caused`, `as a result`, `which delayed`). Subtle implicit causal relations without overt lexical markers remain outside the scope of Phase 13 rule-based extraction, as documented in the research limitations card.

---

## 9. Conclusion

The CausalFidelityPlus platform is now fully certified as a **genuine research software product**:
- Zero fabricated, simulated, or hardcoded mock data in production views.
- No silent fallbacks to static fixtures upon network errors.
- Real-time reactivity to backend health and artifact availability.
- Total preservation of Phase 1–13 scientific findings and full regression test suite (292/292 passing).
