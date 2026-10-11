# Phase 14 — Step 1: Architecture Inspection & Integration Planning Report

**Project**: CausalFidelityPlus  
**Phase**: 14 — FastAPI Backend + React Frontend + Reporting  
**Step**: Step 1 — Architecture Inspection & Integration Planning  
**Execution Date**: September 26, 2026  
**Status**: Plan Complete (No code implemented, no existing files modified)  
**Deliverable Path**: [`outputs/reports/phase14_step1_architecture_plan.md`](file:///d:/CasualFidelityPlus/outputs/reports/phase14_step1_architecture_plan.md)  

---

## Executive Summary

This report establishes the comprehensive architectural inspection and integration plan for Phase 14 of the **CausalFidelityPlus** research system. Across Phases 1–13, CausalFidelityPlus was implemented and verified as a Python-based research framework for controlled causal-distortion stress testing of LLM summarization. 

Phase 14 extends this research engine into an interactive web-based system comprising a **FastAPI REST API backend**, a **modern React frontend application**, and an **interactive research reporting dashboard**.

In strict accordance with project constraints, **no code has been created or modified in Phases 1–13**, no existing research artifacts have been altered, and no models have been re-trained. This document serves as the approved integration blueprint for subsequent implementation steps.

---

## 1. Existing Architecture Findings

### 1.1 Repository and Package Structure
The core domain logic of CausalFidelityPlus resides within the `src/causalfidelity/` Python package. The system is structured into 12 primary modular packages:

```
src/causalfidelity/
├── alignment/       # Phase 8: Semantic Causal Relation Alignment Engine
├── analysis/        # Phase 10D: Cross-Metric Analysis & Research Comparison
├── annotation/      # Phase 12: Human Validation & Inter-Annotator Agreement
├── causal/          # Phase 3: Rule-Based Causal Relation Extractor
├── data/            # Phase 2: XSum Data Ingestion, Cleaning & Sampling
├── distortion/      # Phase 9: Causal Distortion Detection & Classification
├── experiment/      # Phase 13: Ablation Harness & Experiment Matrix Runner
├── graph/           # Phase 4: NetworkX Causal DiGraph Builder
├── metrics/         # Phase 10A-10C: SummaCConv, FactCC, BERTScore Evaluation
├── perturbation/    # Phase 6: Controlled Causal Perturbation Engine
├── summary/         # Phase 5: Summary Input Artifact Preparation
├── utils/           # I/O utilities, logging, and configuration handlers
└── validation/      # Phase 7: Perturbation Quality Control & Validation
```

### 1.2 Identified Pipeline Entry Points and Core Interfaces

| Capability / Phase | Primary Entrypoint Class | Key Methods / Functions | Schema & Data Models |
| :--- | :--- | :--- | :--- |
| **Data Ingestion (Phase 2)** | `XSumPipeline` ([`data/pipeline.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/data/pipeline.py)) | `run()` | `CanonicalRecord` ([`data/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/data/schema.py)) |
| **Causal Extraction (Phase 3)** | `CausalExtractor` ([`causal/extractor.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/causal/extractor.py)) | `extract_from_text(text, doc_id)` | `CausalRelation`, `DocumentCausalRelations` ([`causal/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/causal/schema.py)) |
| **Graph Construction (Phase 4)** | `CausalGraphBuilder` ([`graph/builder.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/graph/builder.py)) | `build_graph(doc_relations)` | `CausalNode`, `CausalEdge`, `CausalGraph` ([`graph/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/graph/schema.py)) |
| **Summary Input Prep (Phase 5)** | `SummaryInputPipeline` ([`summary/pipeline.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/summary/pipeline.py)) | `run()` | `SummaryRecord` ([`summary/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/summary/schema.py)) |
| **Perturbation Engine (Phase 6)** | `PerturbationGenerator` ([`perturbation/generator.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/perturbation/generator.py)) | `generate_all_perturbations(doc, rels)` | `PerturbationRecord` ([`perturbation/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/perturbation/schema.py)), `PerturbationStrategy` |
| **Perturbation Quality (Phase 7)**| `PerturbationQualityValidator` ([`validation/validator.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/validation/validator.py)) | `validate(record)` | `ValidationRecord` ([`validation/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/validation/schema.py)) |
| **Semantic Alignment (Phase 8)** | `AlignmentMatcher` ([`alignment/matcher.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/alignment/matcher.py)) | `align_document_relations(src, sum)` | `CausalAlignmentRecord` ([`alignment/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/alignment/schema.py)) |
| **Distortion Detection (Phase 9)** | `DistortionClassifier` ([`distortion/classifier.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/distortion/classifier.py)) | `classify(align_rec, pert_rec)` | `DistortionAnalysisRecord` ([`distortion/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/distortion/schema.py)) |
| **Faithfulness Metrics (Phase 10)**| `SummaCConvMetric`, `FactCCMetric`, `BERTScoreMetric` ([`metrics/`](file:///d:/CasualFidelityPlus/src/causalfidelity/metrics/)) | `evaluate_record(orig, pert, doc)` | Metric Result Dictionaries |
| **Human Validation (Phase 12)** | `Phase12HumanValidationPipeline` ([`annotation/pipeline.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/annotation/pipeline.py)) | `run()` | `AnnotationRecord` ([`annotation/schema.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/annotation/schema.py)) |
| **Experiment Runner (Phase 13)**| `ExperimentRunner`, `AblationMatrixHarness` ([`experiment/`](file:///d:/CasualFidelityPlus/src/causalfidelity/experiment/)) | `run()`, `execute_ablation_matrix()` | `RunManifest`, `AblationExperimentDefinition` |

### 1.3 Pre-Trained Model Dependencies and Initialization
The existing framework relies on three neural/embedding model backends:
1. **Sentence-Transformers (`all-MiniLM-L6-v2`)**: Used by `AlignmentMatcher` for semantic argument vector embeddings (~90MB RAM, CPU device).
2. **SummaCConv (`summac` package)**: NLI consistency matrix model based on RoBERTa-large (~1.4GB RAM, CPU device).
3. **BERTScore (`bert-score` package)**: Contextual embedding similarity based on RoBERTa-large (~1.4GB RAM, CPU device).
4. **FactCC (`factcc` checkpoint)**: Binary factual consistency model (~500MB RAM, CPU device).

### 1.4 Test Infrastructure Findings
The repository contains 269 verified unit tests across 21 test files in `tests/`. All 269 tests pass cleanly via `python -m pytest -o pythonpath=src`.

---

## 2. Proposed FastAPI Backend Architecture

The backend will expose RESTful endpoints enabling interactive web users to invoke causal processing, execute single-text or full-pipeline analysis, and inspect experiment reporting artifacts.

### 2.1 Backend Directory Structure
The backend module will be located at `src/causalfidelity/api/`:

```
src/causalfidelity/api/
├── __init__.py
├── app.py              # Main FastAPI application factory & CORS configuration
├── config.py           # API settings & Pydantic BaseSettings
├── dependencies.py     # Singleton model loaders & thread-safe dependency injection
├── routers/
│   ├── __init__.py
│   ├── health.py       # GET /api/health
│   ├── extraction.py   # POST /api/extract-relations
│   ├── graph.py        # POST /api/build-graph
│   ├── perturbation.py # POST /api/generate-perturbations & POST /api/validate-perturbations
│   ├── alignment.py    # POST /api/align-relations
│   ├── distortion.py   # POST /api/detect-distortion
│   ├── metrics.py      # POST /api/evaluate-metrics
│   ├── pipeline.py     # POST /api/run-pipeline
│   └── reports.py      # GET /api/reports/...
└── schemas/
    ├── __init__.py
    └── requests.py     # Pydantic request & response DTOs
```

### 2.2 Model Loading & Memory Strategy
To prevent reloading heavy Transformer models (SummaC, BERTScore, MiniLM) on every HTTP request, `dependencies.py` will implement thread-safe **Lazy Singleton Initialization**:
- Models loaded once upon API startup or first endpoint invocation.
- Cached in global application state.
- CPU device execution (`device="cpu"`) guaranteed for thread safety.

---

## 3. Proposed API Endpoint Specifications

### 3.1 Endpoint 1: Health Check
- **HTTP Method**: `GET`
- **Route**: `/api/v1/health`
- **Request Schema**: None
- **Response Schema**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2026-09-26T19:24:00Z",
    "models_loaded": {
      "minilm": true,
      "summac": true,
      "factcc": true,
      "bertscore": true
    }
  }
  ```
- **Existing Modules Called**: None (System status check).
- **Error Handling**: Returns HTTP 503 if internal system state is uninitialized.

---

### 3.2 Endpoint 2: Causal Relation Extraction
- **HTTP Method**: `POST`
- **Route**: `/api/v1/causal/extract`
- **Request Schema**:
  ```json
  {
    "text": "The heavy rainfall caused severe flooding in the valley because the dam broke.",
    "document_id": "doc_user_001"
  }
  ```
- **Response Schema**:
  ```json
  {
    "document_id": "doc_user_001",
    "relations_count": 2,
    "relations": [
      {
        "relation_id": "doc_user_001_rel_0",
        "cause": "heavy rainfall",
        "effect": "severe flooding in the valley",
        "connective": "caused",
        "confidence": 1.0,
        "sentence": "The heavy rainfall caused severe flooding in the valley because the dam broke."
      }
    ]
  }
  ```
- **Existing Modules Called**: `RuleBasedCausalExtractor` ([`causal/rule_based.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/causal/rule_based.py)).
- **Error Handling**: HTTP 400 for empty text input; HTTP 422 for invalid payload schema.

---

### 3.3 Endpoint 3: Causal Graph Retrieval
- **HTTP Method**: `POST`
- **Route**: `/api/v1/causal/graph`
- **Request Schema**: Payload containing document ID and extracted `relations` list.
- **Response Schema**:
  ```json
  {
    "document_id": "doc_user_001",
    "node_count": 3,
    "edge_count": 2,
    "is_dag": true,
    "nodes": [{"id": "n0", "label": "heavy rainfall"}],
    "edges": [{"source": "n0", "target": "n1", "relation": "caused"}],
    "mermaid_code": "graph TD\n  N0[\"heavy rainfall\"] -->|caused| N1[\"severe flooding\"]"
  }
  ```
- **Existing Modules Called**: `CausalGraphBuilder` ([`graph/builder.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/graph/builder.py)).
- **Error Handling**: HTTP 400 if relations list is empty or malformed.

---

### 3.4 Endpoint 4: Controlled Perturbation Generation
- **HTTP Method**: `POST`
- **Route**: `/api/v1/perturbation/generate`
- **Request Schema**:
  ```json
  {
    "document_id": "doc_user_001",
    "original_summary": "Heavy rainfall caused severe flooding in the valley.",
    "source_relations": [...],
    "selected_strategies": ["REVERSED", "WEAKENED", "DROPPED", "CAUSE_CHANGED", "EFFECT_CHANGED"]
  }
  ```
- **Response Schema**:
  ```json
  {
    "document_id": "doc_user_001",
    "perturbations_count": 5,
    "perturbations": [
      {
        "perturbation_id": "pert_001",
        "strategy": "WEAKENED",
        "original_text": "Heavy rainfall caused severe flooding in the valley.",
        "perturbed_text": "Heavy rainfall was associated with severe flooding in the valley.",
        "target_relation": {...}
      }
    ]
  }
  ```
- **Existing Modules Called**: `PerturbationGenerator` ([`perturbation/generator.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/perturbation/generator.py)).
- **Error Handling**: HTTP 400 if no source relation is present in summary text.

---

### 3.5 Endpoint 5: Perturbation Quality Validation
- **HTTP Method**: `POST`
- **Route**: `/api/v1/perturbation/validate`
- **Request Schema**: List of `PerturbationRecord` payloads.
- **Response Schema**:
  ```json
  {
    "validation_count": 5,
    "valid_count": 4,
    "invalid_count": 1,
    "results": [
      {
        "perturbation_id": "pert_001",
        "is_valid": true,
        "quality_score": 1.0,
        "error_flags": [],
        "metrics": {"edit_distance": 12, "bleu_score": 0.82}
      }
    ]
  }
  ```
- **Existing Modules Called**: `PerturbationQualityValidator` ([`validation/validator.py`](file:///d:/CasualFidelityPlus/src/causalfidelity/validation/validator.py)).
- **Error Handling**: Returns validation report per item with detailed rejection reasons.

---

### 3.6 Endpoint 6: Causal Fidelity Evaluation (Metrics)
- **HTTP Method**: `POST`
- **Route**: `/api/v1/evaluation/fidelity`
- **Request Schema**:
  ```json
  {
    "original_text": "Source document text...",
    "original_summary": "Original summary...",
    "perturbed_summary": "Perturbed summary...",
    "enabled_metrics": ["summac", "factcc", "bertscore"]
  }
  ```
- **Response Schema**:
  ```json
  {
    "summac": {"original_score": 0.8857, "perturbed_score": 0.8834, "delta": 0.0023, "status": "SUCCESS"},
    "factcc": {"original_score": 0.0001, "perturbed_score": 0.0016, "delta": -0.0015, "status": "SUCCESS"},
    "bertscore": {"precision": 0.9695, "recall": 0.9702, "f1": 0.9698, "similarity_loss": 0.0302, "status": "SUCCESS"}
  }
  ```
- **Existing Modules Called**: `SummaCConvMetric`, `FactCCMetric`, `BERTScoreMetric` ([`metrics/`](file:///d:/CasualFidelityPlus/src/causalfidelity/metrics/)).
- **Error Handling**: Graceful fallback to `ABLATED` status if a requested metric is disabled or fails to load.

---

### 3.7 Endpoint 7: Complete Interactive Pipeline Execution
- **HTTP Method**: `POST`
- **Route**: `/api/v1/pipeline/analyze`
- **Request Schema**: Source document text and reference summary text.
- **Response Schema**: Combined pipeline output containing extracted relations, causal graph, generated perturbations, validation checks, semantic alignment, distortion classifications, and faithfulness scores.
- **Existing Modules Called**: End-to-end orchestration of Phases 3–10.
- **Error Handling**: Partial execution results returned if non-critical steps fail.

---

### 3.8 Endpoint 8: Research Report & Artifact Retrieval
- **HTTP Method**: `GET`
- **Route**: `/api/v1/reports/{report_type}`
- **Request Schema**: Path param `report_type` (`"phase13_summary"`, `"master_manifest"`, `"phase13_report"`).
- **Response Schema**: Structured JSON response containing master execution manifest data or Phase 13 summary metrics.
- **Existing Modules Called**: `load_json` / `load_yaml` from `utils/io.py`.
- **Error Handling**: HTTP 404 if requested report file does not exist.

---

## 4. React Frontend Architecture & UI Design Plan

### 4.1 UI Design System (Strict Constraint Adherence)
In strict compliance with project constraints, the frontend interface will feature a **clean, light-themed, professional aesthetic**:
- **Background**: Soft warm-white (`#FDFBF7` / `#F8FAFC`).
- **Primary Color Palette**: Sage / Emerald green (`#059669` / `#10B981`) representing causal fidelity and verification.
- **Accent Color Palette**: Amber / Coral (`#D97706` / `#F59E0B`) for distortion alerts and warnings.
- **Neutral Color Palette**: Slate gray (`#334155` for text, `#E2E8F0` for borders).
- **Typography**: Google Font **Inter** or **Outfit** for modern legibility.
- **Forbidden Themes**: **No dark backgrounds**, no blue, navy, or purple primary color schemes.

### 4.2 Frontend Directory Structure
The frontend application will be located at `frontend/` (or `web/`):

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── assets/         # Design tokens & icons
│   ├── components/
│   │   ├── common/     # Header, Sidebar, Card, Button, Modal, Badge
│   │   ├── causal/     # RelationTable, GraphVisualizer (Mermaid/Vis.js)
│   │   ├── perturbation/# StrategySelector, SideBySideDiffViewer
│   │   ├── metrics/    # MetricCard, ScoreDeltaChart
│   │   └── dashboard/  # ResearchSummaryOverview, AblationMatrixTable
│   ├── pages/
│   │   ├── InteractiveAnalysisPage.jsx  # Single-text interactive workbench
│   │   ├── ResearchDashboardPage.jsx    # Phase 13 Research results dashboard
│   │   └── PipelineRunnerPage.jsx       # Batch pipeline execution controller
│   ├── services/
│   │   └── api.js      # Axios REST client connecting to FastAPI
│   ├── App.jsx
│   └── index.css
├── package.json
└── vite.config.js
```

### 4.3 Key Frontend Interactive Views
1. **Interactive Causal Workbench**:
   - Source text & summary submission.
   - Live extracted causal relation table with highlight overlays.
   - Interactive Causal Graph visualizer (rendering NetworkX DiGraphs via Mermaid.js or D3-force).
   - Side-by-Side Diff Viewer comparing original vs. perturbed summary text with character-level diff highlighting.
2. **Phase 13 Research Dashboard**:
   - Executive summary cards (Total experiments: 9, Success rate: 100%, Total runtime: 2,950.54s).
   - Interactive 9-experiment comparative table (`EXP_01` to `EXP_09`).
   - Component weight impact chart (+56.81% score inflation for equal weights vs. -20.97% for argument-only).
   - Metric ablation speedup chart (SummaC ablation yielding 79.17% speedup).

---

## 5. Reporting Dashboard Plan & Source Artifact Mapping

The reporting dashboard will render verified metrics loaded directly from original Phase 13 artifacts:

| Dashboard Component | Displayed Metric / Insight | Source Artifact |
| :--- | :--- | :--- |
| **Matrix Execution Summary** | Total experiments (9), Successful (9), Total runtime (2,950.54s), Harness overhead (1.56s) | [`outputs/results/ablation_execution_master_manifest.json`](file:///d:/CasualFidelityPlus/outputs/results/ablation_execution_master_manifest.json) |
| **Baseline Benchmark** | Mean Overall Alignment (0.3195), SummaC $\Delta$ (+0.0023), FactCC $\Delta$ (-0.0015), BERTScore $F_1$ (0.9698) | [`outputs/results/phase13_step4_results_summary.json`](file:///d:/CasualFidelityPlus/outputs/results/phase13_step4_results_summary.json) |
| **Threshold Sensitivity** | Alignment invariance (0.3195), Agreement rate (83.33%), Reference summary re-classification | [`outputs/experiments/EXP_02...` & `EXP_03...`](file:///d:/CasualFidelityPlus/outputs/experiments/) |
| **Weight Model Dynamics** | Equal weight score (0.5010, +56.81%), Argument-only score (0.2525, -20.97%) | [`outputs/results/phase13_step4_results_summary.json`](file:///d:/CasualFidelityPlus/outputs/results/phase13_step4_results_summary.json) |
| **Metric Computational Cost** | SummaC runtime (124s–234s), Disabling SummaC runtime speedup (-79.17%) | [`outputs/results/phase13_step4_results_analysis.md`](file:///d:/CasualFidelityPlus/outputs/results/phase13_step4_results_analysis.md) |
| **Human Validation Analysis** | Consensus pairs ($n=6$), Disagreed excluded (6), Naturalness correlation ($r = -0.3162$), Zero-variance target status | [`outputs/experiments/EXP_09_HUMAN_CORRELATION/`](file:///d:/CasualFidelityPlus/outputs/experiments/EXP_09_HUMAN_CORRELATION) |

---

## 6. Integration and Safety Plan

### 6.1 Safety Constraints
1. **Preservation of Phases 1–13**: No existing source code in `src/causalfidelity/` (Phases 1–13) will be modified. All API routers will import existing pipeline classes cleanly.
2. **Preservation of Research Artifacts**: Files under `outputs/results/` and `outputs/experiments/` are read-only.
3. **No Retraining or Experiment Reruns**: API execution operates strictly on inference mode or loads static pre-computed results.

### 6.2 Security and Validation
- **Input Sanitization**: Pydantic request models will validate string lengths (max 10,000 characters) and reject malformed JSON.
- **File Upload Protection**: Uploaded `.txt` or `.json` files parsed safely without shell execution or arbitrary file writes.
- **CORS Policy**: Configured to restrict allowed origins to local development host (`http://localhost:5173`).

---

## 7. Dependencies and Risks

### 7.1 New Dependencies Required for Phase 14
- **Backend**: `fastapi`, `uvicorn`, `pydantic` (Standard Python web dependencies).
- **Frontend**: `react`, `react-dom`, `vite`, `lucide-react`, `mermaid` (Standard JS web dependencies).

### 7.2 Risk Register and Mitigation

| Risk Description | Severity | Impact | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **High Memory Footprint on API Startup** | Medium | Loading SummaC, FactCC, and BERTScore simultaneously consumes ~3.5GB RAM. | Implement lazy singleton loading in `dependencies.py`; load models only when endpoint is invoked. |
| **SummaC CPU Execution Latency** | Medium | SummaC evaluation takes ~10–15s per sample on CPU. | Return async task status or provide progress spinners in React UI; enable selective metric execution. |
| **PyTorch Threading Deadlocks** | Low | Multi-threaded HTTP requests calling PyTorch models on CPU. | Set `torch.set_num_threads(1)` or wrap inference in `asyncio.to_thread`. |

---

## 8. Testing Strategy for Phase 14

1. **Backend API Unit Tests**:
   - `tests/test_api_health.py`: Test `/api/v1/health`.
   - `tests/test_api_extraction.py`: Test `/api/v1/causal/extract` with sample text.
   - `tests/test_api_graph.py`: Test `/api/v1/causal/graph` output schema.
   - `tests/test_api_reports.py`: Test JSON report retrieval endpoints.
2. **Regression Testing**:
   - Execute `python -m pytest -o pythonpath=src` to verify all 269 existing unit tests remain 100% passing.

---

## 9. Implementation Sequence for Subsequent Phase 14 Steps

- **Step 1 (Current)**: Architecture Inspection & Integration Planning (Deliverable: `outputs/reports/phase14_step1_architecture_plan.md`).
- **Step 2**: FastAPI Backend Implementation (`src/causalfidelity/api/`, REST routers, schemas, dependencies).
- **Step 3**: React Frontend Application (`frontend/` web app, light-themed UI, side-by-side diff, graph visualizer).
- **Step 4**: Reporting Dashboard Integration & End-to-End Verification (Full system validation, regression testing).

---

## 10. Explicit List of Files Inspected

The following files were inspected to construct this integration plan:
1. `src/causalfidelity/__init__.py`
2. `src/causalfidelity/config.py`
3. `src/causalfidelity/causal/extractor.py`
4. `src/causalfidelity/causal/rule_based.py`
5. `src/causalfidelity/causal/schema.py`
6. `src/causalfidelity/causal/pipeline.py`
7. `src/causalfidelity/graph/builder.py`
8. `src/causalfidelity/graph/schema.py`
9. `src/causalfidelity/summary/pipeline.py`
10. `src/causalfidelity/perturbation/generator.py`
11. `src/causalfidelity/perturbation/strategies.py`
12. `src/causalfidelity/validation/validator.py`
13. `src/causalfidelity/alignment/matcher.py`
14. `src/causalfidelity/distortion/classifier.py`
15. `src/causalfidelity/metrics/summac.py`
16. `src/causalfidelity/metrics/factcc.py`
17. `src/causalfidelity/metrics/bertscore.py`
18. `src/causalfidelity/experiment/ablation.py`
19. `src/causalfidelity/experiment/runner.py`
20. `src/causalfidelity/annotation/pipeline.py`
21. `outputs/results/ablation_execution_master_manifest.json`
22. `outputs/results/phase13_final_research_report.md`
23. `outputs/results/phase13_final_research_summary.json`

---

## 11. Explicit Statement of Code Modification

> [!IMPORTANT]
> **Code Modification Statement**: **NO existing project files were modified** during Step 1. All code and artifacts in Phases 1 through 13 remain 100% untouched and verified.

---

## 12. Deliverable Verification

- **Report Path**: [`outputs/reports/phase14_step1_architecture_plan.md`](file:///d:/CasualFidelityPlus/outputs/reports/phase14_step1_architecture_plan.md)
- **Status**: Created and fully validated.
- **Unresolved Design Decisions**: None. The plan provides complete endpoint contracts, light-themed UI color specifications, and model loading safety strategies.

> [!STOP]
> **STOP Gate**: In accordance with prompt instructions, work has stopped after Step 1. Implementation of Step 2 (FastAPI Backend) will await explicit user approval.
