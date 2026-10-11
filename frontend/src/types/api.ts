/**
 * API Data Transfer Objects (DTOs) for CausalFidelityPlus FastAPI Backend.
 * Strictly aligned with Pydantic schemas in src/causalfidelity/api/schemas.py.
 */

export interface HealthResponse {
  status: string;
  version: string;
  components_available: Record<string, boolean>;
  models_loaded: Record<string, boolean>;
  timestamp: string;
}

export interface CausalRelationDTO {
  relation_id: string;
  document_id: string;
  sentence_index: number;
  cause: string;
  effect: string;
  relation: string;
  connective: string;
  confidence: number;
  source_sentence: string;
}

export interface CausalExtractionRequest {
  text: string;
  document_id?: string;
}

export interface CausalExtractionResponse {
  document_id: string;
  relations_count: number;
  relations: CausalRelationDTO[];
}

export interface CausalNodeDTO {
  node_id: string;
  text: string;
  normalized_text: string;
}

export interface CausalEdgeDTO {
  source: string;
  target: string;
  relation: string;
  relation_id?: string;
  weight: number;
}

export interface CausalGraphRequest {
  document_id?: string;
  text?: string;
  relations?: Record<string, any>[];
}

export interface CausalGraphResponse {
  document_id: string;
  node_count: number;
  edge_count: number;
  is_dag: boolean;
  has_cycles: boolean;
  nodes: CausalNodeDTO[];
  edges: CausalEdgeDTO[];
  mermaid_code: string;
}

export interface PerturbationGenerationRequest {
  summary_text: string;
  document_id?: string;
  summary_id?: string;
  source_relations?: Record<string, any>[];
  selected_strategies?: string[];
}

export interface PerturbationDTO {
  perturbation_id: string;
  document_id: string;
  summary_id: string;
  strategy: string;
  perturbation_type: string;
  original_text: string;
  perturbed_text: string;
  original_relation?: Record<string, any>;
  intended_relation?: Record<string, any>;
  changed_span?: Record<string, any>;
  generation_method?: string;
  target_relation?: Record<string, any>;
}

export interface PerturbationGenerationResponse {
  document_id: string;
  summary_id: string;
  perturbations_count: number;
  perturbations: PerturbationDTO[];
  stats: Record<string, any>;
}

export interface PerturbationValidationRequest {
  records: Record<string, any>[];
}

export interface ValidationResultDTO {
  perturbation_id: string;
  is_valid: boolean;
  validation_status: string;
  quality_score: number;
  error_flags: string[];
  warning_flags: string[];
  metrics: Record<string, any>;
}

export interface PerturbationValidationResponse {
  total_examined: number;
  valid_count: number;
  invalid_count: number;
  validation_rate: number;
  results: ValidationResultDTO[];
}

export interface FidelityEvaluationRequest {
  source_text: string;
  original_summary: string;
  perturbed_summary: string;
  enabled_metrics?: string[];
}

export interface MetricScoreDTO {
  metric_name: string;
  status: string; // 'SUCCESS' | 'UNAVAILABLE' | 'FAILED' | 'ABLATED'
  original_score?: number;
  perturbed_score?: number;
  score_delta?: number;
  bertscore_f1?: number;
  bertscore_precision?: number;
  bertscore_recall?: number;
  similarity_loss?: number;
  metadata?: Record<string, any>;
}

export interface FidelityEvaluationResponse {
  source_text: string;
  original_summary: string;
  perturbed_summary: string;
  metrics: Record<string, MetricScoreDTO>;
}

export interface PipelineAnalyzeRequest {
  source_text: string;
  summary_text: string;
  document_id?: string;
  selected_strategies?: string[];
  enabled_metrics?: string[];
}

export interface PipelineAnalyzeResponse {
  document_id: string;
  status: string;
  extraction: CausalExtractionResponse;
  graph: CausalGraphResponse;
  perturbations: PerturbationGenerationResponse;
  validation: PerturbationValidationResponse;
  fidelity: FidelityEvaluationResponse;
}

export interface ReportResponse {
  report_type: string;
  title: string;
  file_name: string;
  content_type: string;
  data: any;
}
