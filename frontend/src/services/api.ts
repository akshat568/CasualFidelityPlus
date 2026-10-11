import type {
  HealthResponse,
  CausalExtractionRequest,
  CausalExtractionResponse,
  CausalGraphRequest,
  CausalGraphResponse,
  PerturbationGenerationRequest,
  PerturbationGenerationResponse,
  PerturbationValidationRequest,
  PerturbationValidationResponse,
  FidelityEvaluationRequest,
  FidelityEvaluationResponse,
  PipelineAnalyzeRequest,
  PipelineAnalyzeResponse,
  ReportResponse
} from '../types/api';

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1';

export function getApiBaseUrl(): string {
  const stored = localStorage.getItem('causalfidelity_api_base_url');
  if (stored && stored.trim()) {
    return stored.trim();
  }
  if (import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  return DEFAULT_BASE_URL;
}

export function setApiBaseUrl(url: string): void {
  if (url && url.trim()) {
    localStorage.setItem('causalfidelity_api_base_url', url.trim());
  } else {
    localStorage.removeItem('causalfidelity_api_base_url');
  }
}

export class ApiError extends Error {
  status?: number;
  details?: any;

  constructor(message: string, status?: number, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}, customBaseUrl?: string): Promise<T> {
  const baseUrl = customBaseUrl ? customBaseUrl.replace(/\/+$/, '') : getApiBaseUrl().replace(/\/+$/, '');
  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      let errorMessage = `API request failed with status ${response.status} ${response.statusText}`;
      let errorDetails = null;

      try {
        const errorData = await response.json();
        errorDetails = errorData;
        if (errorData.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (errorData.detail.message) {
            errorMessage = errorData.detail.message;
          } else if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail.map((err: any) => err.msg || JSON.stringify(err)).join('; ');
          }
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      } catch {
        // Response body was not JSON
      }

      throw new ApiError(errorMessage, response.status, errorDetails);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      `Unable to connect to the CausalFidelityPlus API. Please verify that the FastAPI server is running. (${err.message || 'Network error'})`
    );
  }
}

// === Centralized API Client Endpoint Functions ===

/**
 * Health check endpoint: GET /api/v1/health
 */
export async function healthCheck(customBaseUrl?: string): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { method: 'GET' }, customBaseUrl);
}

/**
 * Causal extraction endpoint: POST /api/v1/causal/extract
 */
export async function extractCausalRelations(
  text: string,
  documentId: string = 'doc_user'
): Promise<CausalExtractionResponse> {
  const payload: CausalExtractionRequest = { text, document_id: documentId };
  return request<CausalExtractionResponse>('/causal/extract', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Causal graph construction endpoint: POST /api/v1/causal/graph
 */
export async function buildCausalGraph(
  payload: CausalGraphRequest
): Promise<CausalGraphResponse> {
  return request<CausalGraphResponse>('/causal/graph', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Controlled perturbation generation endpoint: POST /api/v1/perturbation/generate
 */
export async function generatePerturbation(
  payload: PerturbationGenerationRequest
): Promise<PerturbationGenerationResponse> {
  return request<PerturbationGenerationResponse>('/perturbation/generate', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Perturbation quality validation endpoint: POST /api/v1/perturbation/validate
 */
export async function validatePerturbation(
  payload: PerturbationValidationRequest
): Promise<PerturbationValidationResponse> {
  return request<PerturbationValidationResponse>('/perturbation/validate', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Causal fidelity evaluation endpoint: POST /api/v1/evaluation/fidelity
 */
export async function evaluateFidelity(
  payload: FidelityEvaluationRequest
): Promise<FidelityEvaluationResponse> {
  return request<FidelityEvaluationResponse>('/evaluation/fidelity', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * End-to-end interactive pipeline analysis endpoint: POST /api/v1/pipeline/analyze
 */
export async function analyzePipeline(
  payload: PipelineAnalyzeRequest
): Promise<PipelineAnalyzeResponse> {
  return request<PipelineAnalyzeResponse>('/pipeline/analyze', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Research report retrieval endpoint: GET /api/v1/reports/{report_type}
 */
export async function getReport(reportType: string): Promise<ReportResponse> {
  return request<ReportResponse>(`/reports/${encodeURIComponent(reportType)}`, {
    method: 'GET'
  });
}
