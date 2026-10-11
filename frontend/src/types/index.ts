// TypeScript interfaces for CausalFidelityPlus
export * from './api';

export type PerturbationStrategy = 'REVERSED' | 'WEAKENED' | 'DROPPED' | 'CAUSE_CHANGED' | 'EFFECT_CHANGED';

export interface CausalRelation {
  id: string;
  cause: string;
  effect: string;
  connective: string;
  confidence: number;
  sentence?: string;
  status?: 'ACTIVE' | 'PERTURBED' | 'DROPPED';
}

export interface CausalGraphNode {
  id: string;
  label: string;
  type?: 'cause' | 'effect' | 'intermediate';
}

export interface CausalGraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface CausalGraphData {
  nodes: CausalGraphNode[];
  edges: CausalGraphEdge[];
  isDag: boolean;
  mermaidCode?: string;
}

export interface PerturbationResult {
  id: string;
  strategy: PerturbationStrategy;
  originalText: string;
  perturbedText: string;
  diffHighlights?: { type: 'added' | 'removed' | 'same'; text: string }[];
  targetRelationId?: string;
}

export interface ValidationCheckResult {
  category: 'Structural' | 'Relational' | 'Content';
  checkName: string;
  status: 'PASSED' | 'FAILED' | 'NOT_EVALUATED';
  details: string;
}

export interface PerturbationValidation {
  isValid: boolean;
  qualityScore: number;
  checks: ValidationCheckResult[];
}

export interface FidelityMetricScore {
  name: string;
  originalScore?: number;
  perturbedScore?: number;
  delta?: number;
  status: 'EVALUATED' | 'NOT_EVALUATED' | 'ABLATED' | 'UNAVAILABLE' | 'FAILED';
  description: string;
  details?: string;
}

export interface ResearchExperiment {
  id: string;
  name: string;
  type: string;
  status: 'COMPLETED' | 'RUNNING' | 'FAILED';
  description: string;
  availableMetrics: string[];
  meanAlignment?: number;
  runtimeSeconds?: number;
  notes?: string;
}

export interface ResearchReportItem {
  id: string;
  title: string;
  fileName: string;
  filePath: string;
  description: string;
  format: 'markdown' | 'json';
  summaryMetrics?: Record<string, string | number>;
  contentPreview?: string;
  artifactLabel?: string;
}

export interface AppSettings {
  apiBaseUrl: string;
  theme: 'Light';
  appVersion: string;
  appName: string;
}
