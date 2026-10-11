import React, { useState } from 'react';
import { TextInputPanel } from '../components/workbench/TextInputPanel';
import { CausalRelationTable } from '../components/workbench/CausalRelationTable';
import { CausalGraphVisualizer } from '../components/workbench/CausalGraphVisualizer';
import { PerturbationPanel } from '../components/workbench/PerturbationPanel';
import { DiffViewer } from '../components/workbench/DiffViewer';
import { ValidationPanel } from '../components/workbench/ValidationPanel';
import { FidelityPanel } from '../components/workbench/FidelityPanel';
import {
  extractCausalRelations,
  buildCausalGraph,
  generatePerturbation,
  validatePerturbation,
  evaluateFidelity
} from '../services/api';

const DEFAULT_BENCHMARK_PROMPT =
  "Heavy rainfall caused the river to overflow. As a result, nearby roads were flooded, which delayed emergency response teams.";
import { computeWordDiff, type DiffPart } from '../utils/diff';
import type {
  CausalRelation,
  CausalGraphData,
  PerturbationStrategy,
  FidelityMetricScore,
  ValidationCheckResult,
  CausalRelationDTO,
  PerturbationDTO,
  ValidationResultDTO
} from '../types';
import { Sparkles, AlertCircle } from 'lucide-react';

const INITIAL_METRICS: FidelityMetricScore[] = [
  {
    name: 'SummaC',
    status: 'NOT_EVALUATED',
    description: 'NLI-based consistency matrix model (RoBERTa-large)',
    details: 'Click "Evaluate Metrics" to trigger lazy neural evaluation'
  },
  {
    name: 'FactCC',
    status: 'NOT_EVALUATED',
    description: 'Binary factual consistency classifier',
    details: 'Click "Evaluate Metrics" to trigger lazy neural evaluation'
  },
  {
    name: 'BERTScore',
    status: 'NOT_EVALUATED',
    description: 'Contextual embedding similarity precision, recall & F1',
    details: 'Click "Evaluate Metrics" to trigger lazy neural evaluation'
  }
];

const INITIAL_VALIDATION_CHECKS: ValidationCheckResult[] = [
  {
    category: 'Structural',
    checkName: 'Parse Tree Integrity & Edit Distance',
    status: 'NOT_EVALUATED',
    details: 'Awaiting perturbation generation'
  },
  {
    category: 'Relational',
    checkName: 'Causal Connective Mutation',
    status: 'NOT_EVALUATED',
    details: 'Awaiting perturbation generation'
  },
  {
    category: 'Content',
    checkName: 'Content Preservation & Consistency',
    status: 'NOT_EVALUATED',
    details: 'Awaiting perturbation generation'
  }
];

export const WorkbenchPage: React.FC = () => {
  // Input State
  const [sourceText, setSourceText] = useState<string>(DEFAULT_BENCHMARK_PROMPT);

  // Causal Extraction & Graph State
  const [relations, setRelations] = useState<CausalRelation[]>([]);
  const [rawRelationsDTO, setRawRelationsDTO] = useState<CausalRelationDTO[]>([]);
  const [graphData, setGraphData] = useState<CausalGraphData>({
    nodes: [],
    edges: [],
    isDag: true,
    mermaidCode: 'graph TD'
  });

  // Perturbation State
  const [selectedStrategy, setSelectedStrategy] = useState<PerturbationStrategy>('REVERSED');
  const [generatedPerturbation, setGeneratedPerturbation] = useState<{
    id: string;
    perturbedText: string;
    activeStrategy: PerturbationStrategy;
    diffs: DiffPart[];
    rawDTO?: PerturbationDTO;
  } | null>(null);

  // Quality Validation State
  const [validationResult, setValidationResult] = useState<{
    isValid: boolean;
    checks: ValidationCheckResult[];
    rawDTO?: ValidationResultDTO;
  } | null>(null);

  // Fidelity Evaluation State
  const [metrics, setMetrics] = useState<FidelityMetricScore[]>(INITIAL_METRICS);

  // UI Loading & Error States
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // === Handler 1: Extract Causal Relations ===
  const handleAnalyze = async () => {
    if (!sourceText.trim()) return;
    setIsAnalyzing(true);
    setApiError(null);

    try {
      const extractRes = await extractCausalRelations(sourceText);
      const dtoRels = extractRes.relations;
      setRawRelationsDTO(dtoRels);

      const uiRels: CausalRelation[] = dtoRels.map((rel) => ({
        id: rel.relation_id,
        cause: rel.cause,
        effect: rel.effect,
        connective: rel.connective,
        confidence: rel.confidence,
        sentence: rel.source_sentence,
        status: 'ACTIVE'
      }));
      setRelations(uiRels);

      // Build Causal DiGraph using backend endpoint
      const graphRes = await buildCausalGraph({
        document_id: extractRes.document_id,
        relations: dtoRels.length > 0 ? (dtoRels as any) : undefined,
        text: dtoRels.length === 0 ? sourceText : undefined
      });

      setGraphData({
        nodes: graphRes.nodes.map((node, index) => ({
          id: node.node_id,
          label: node.text,
          type: index === 0 ? 'cause' : (index === graphRes.nodes.length - 1 ? 'effect' : 'intermediate')
        })),
        edges: graphRes.edges.map((edge) => ({
          id: edge.relation_id || `${edge.source}->${edge.target}`,
          source: edge.source,
          target: edge.target,
          label: edge.relation
        })),
        isDag: graphRes.is_dag,
        mermaidCode: graphRes.mermaid_code
      });
    } catch (err: any) {
      setApiError(err.message || 'Causal relation extraction failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleClear = () => {
    setSourceText('');
    setRelations([]);
    setRawRelationsDTO([]);
    setGraphData({ nodes: [], edges: [], isDag: true, mermaidCode: 'graph TD' });
    setGeneratedPerturbation(null);
    setValidationResult(null);
    setMetrics(INITIAL_METRICS);
    setApiError(null);
  };

  const handleLoadSample = () => {
    setSourceText(DEFAULT_BENCHMARK_PROMPT);
    setRelations([]);
    setRawRelationsDTO([]);
    setGraphData({ nodes: [], edges: [], isDag: true, mermaidCode: 'graph TD' });
    setGeneratedPerturbation(null);
    setValidationResult(null);
    setMetrics(INITIAL_METRICS);
    setApiError(null);
  };

  // === Handler 2: Generate Controlled Perturbation ===
  const handleGenerate = async () => {
    if (!sourceText.trim()) {
      setApiError('Please enter source text before generating a perturbation.');
      return;
    }
    setIsGenerating(true);
    setApiError(null);

    try {
      const pertRes = await generatePerturbation({
        summary_text: sourceText,
        source_relations: rawRelationsDTO.length > 0 ? (rawRelationsDTO as any) : undefined,
        selected_strategies: [selectedStrategy]
      });

      if (!pertRes.perturbations || pertRes.perturbations.length === 0) {
        throw new Error(`No perturbation returned by engine for strategy ${selectedStrategy}.`);
      }

      const targetPert = pertRes.perturbations[0];
      const diffs = computeWordDiff(sourceText, targetPert.perturbed_text);

      setGeneratedPerturbation({
        id: targetPert.perturbation_id,
        perturbedText: targetPert.perturbed_text,
        activeStrategy: (targetPert.strategy || selectedStrategy) as PerturbationStrategy,
        diffs,
        rawDTO: targetPert
      });

      // Reset stale metrics since new perturbation was created
      setMetrics(INITIAL_METRICS);

      // Validate Quality Control for newly generated perturbation
      try {
        const valRes = await validatePerturbation({
          records: [targetPert as any]
        });

        if (valRes.results && valRes.results.length > 0) {
          const vResult = valRes.results[0];
          const uiChecks: ValidationCheckResult[] = [
            {
              category: 'Structural',
              checkName: 'Parse Tree Integrity & Edit Distance',
              status: vResult.metrics?.structural === 'passed' ? 'PASSED' : 'FAILED',
              details: vResult.metrics?.structural === 'passed'
                ? 'Sentence structure & character edit distance within bounds.'
                : (vResult.error_flags.find((e) => e.toLowerCase().includes('structural') || e.toLowerCase().includes('edit')) || 'Structural validation failed.')
            },
            {
              category: 'Relational',
              checkName: 'Causal Connective Mutation',
              status: vResult.metrics?.target_transformation === 'passed' ? 'PASSED' : 'FAILED',
              details: vResult.metrics?.target_transformation === 'passed'
                ? `Target connective modified according to ${selectedStrategy} strategy.`
                : (vResult.error_flags.find((e) => e.toLowerCase().includes('target') || e.toLowerCase().includes('mutation')) || 'Relational target transformation failed.')
            },
            {
              category: 'Content',
              checkName: 'Content Preservation & Consistency',
              status: (vResult.metrics?.content_preservation === 'passed' && vResult.metrics?.consistency === 'passed') ? 'PASSED' : 'FAILED',
              details: (vResult.metrics?.content_preservation === 'passed' && vResult.metrics?.consistency === 'passed')
                ? 'Length ratio, non-target causal links, and entity consistency preserved.'
                : (vResult.error_flags.find((e) => e.toLowerCase().includes('preservation') || e.toLowerCase().includes('content') || e.toLowerCase().includes('consistency') || e.toLowerCase().includes('rewrite') || e.toLowerCase().includes('edit')) || 'Content preservation validation failed.')
            }
          ];

          setValidationResult({
            isValid: vResult.is_valid,
            checks: uiChecks,
            rawDTO: vResult
          });
        }
      } catch (valErr: any) {
        console.warn('Perturbation validation request failed:', valErr);
      }
    } catch (err: any) {
      setApiError(err.message || 'Perturbation generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  // === Handler 3: Evaluate Causal Fidelity Metrics ===
  const handleEvaluateMetrics = async () => {
    if (!generatedPerturbation || !generatedPerturbation.perturbedText) {
      setApiError('Please click "Generate Perturbation" first to produce a perturbed summary before evaluating metrics.');
      return;
    }
    if (!sourceText.trim()) {
      setApiError('Source text is empty.');
      return;
    }

    setIsEvaluating(true);
    setApiError(null);

    try {
      const fidRes = await evaluateFidelity({
        source_text: sourceText,
        original_summary: sourceText,
        perturbed_summary: generatedPerturbation.perturbedText
      });

      const summacObj = fidRes.metrics.summac;
      const factccObj = fidRes.metrics.factcc;
      const bertscoreObj = fidRes.metrics.bertscore;

      const evaluatedMetrics: FidelityMetricScore[] = [
        {
          name: 'SummaC',
          originalScore: summacObj?.original_score,
          perturbedScore: summacObj?.perturbed_score,
          delta: summacObj?.score_delta,
          status: summacObj?.status === 'SUCCESS' ? 'EVALUATED' : (summacObj?.status === 'UNAVAILABLE' ? 'UNAVAILABLE' : (summacObj?.status === 'ABLATED' ? 'ABLATED' : 'FAILED')),
          description: 'NLI-based consistency matrix model (RoBERTa-large)',
          details: summacObj?.status === 'SUCCESS'
            ? `Evaluation complete (SummaC delta = ${summacObj.score_delta})`
            : (summacObj?.metadata?.reason || summacObj?.metadata?.error || 'SummaC model unavailable')
        },
        {
          name: 'FactCC',
          originalScore: factccObj?.original_score,
          perturbedScore: factccObj?.perturbed_score,
          delta: factccObj?.score_delta,
          status: factccObj?.status === 'SUCCESS' ? 'EVALUATED' : (factccObj?.status === 'UNAVAILABLE' ? 'UNAVAILABLE' : (factccObj?.status === 'ABLATED' ? 'ABLATED' : 'FAILED')),
          description: 'Binary factual consistency classifier',
          details: factccObj?.status === 'SUCCESS'
            ? `Evaluation complete (FactCC delta = ${factccObj.score_delta})`
            : (factccObj?.metadata?.reason || factccObj?.metadata?.error || 'FactCC model unavailable')
        },
        {
          name: 'BERTScore',
          originalScore: bertscoreObj?.bertscore_f1,
          perturbedScore: bertscoreObj?.bertscore_f1 !== undefined && bertscoreObj?.similarity_loss !== undefined
            ? Number((bertscoreObj.bertscore_f1 - bertscoreObj.similarity_loss).toFixed(4))
            : undefined,
          delta: bertscoreObj?.similarity_loss !== undefined ? -bertscoreObj.similarity_loss : undefined,
          status: bertscoreObj?.status === 'SUCCESS' ? 'EVALUATED' : (bertscoreObj?.status === 'UNAVAILABLE' ? 'UNAVAILABLE' : (bertscoreObj?.status === 'ABLATED' ? 'ABLATED' : 'FAILED')),
          description: 'Contextual embedding similarity precision, recall & F1',
          details: bertscoreObj?.status === 'SUCCESS'
            ? `BERTScore F1 = ${bertscoreObj.bertscore_f1} (Similarity loss = ${bertscoreObj.similarity_loss})`
            : (bertscoreObj?.metadata?.reason || bertscoreObj?.metadata?.error || 'BERTScore model unavailable')
        }
      ];

      setMetrics(evaluatedMetrics);
    } catch (err: any) {
      setApiError(err.message || 'Fidelity metric evaluation failed.');
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#1F2937]">Interactive Causal Workbench</h2>
          <p className="text-xs text-[#64748B]">
            Extract relations, construct DiGraphs, generate controlled perturbations, and evaluate fidelity against the FastAPI backend.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>Causal Analysis Ready</span>
        </div>
      </div>

      {/* API Error Alert Banner */}
      {apiError && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-900 flex items-start gap-2.5 shadow-xs animate-fade-in">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold text-sm block mb-0.5">API Request Error</span>
            <span>{apiError}</span>
          </div>
          <button
            onClick={() => setApiError(null)}
            className="text-rose-600 font-bold hover:text-rose-800 cursor-pointer text-sm"
          >
            ✕
          </button>
        </div>
      )}

      {/* Section A — Source Text Input */}
      <TextInputPanel
        text={sourceText}
        onChange={setSourceText}
        onAnalyze={handleAnalyze}
        onClear={handleClear}
        onLoadSample={handleLoadSample}
        isAnalyzing={isAnalyzing}
      />

      {/* Section B & C — Extracted Relations and Causal Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CausalRelationTable relations={relations} />
        <CausalGraphVisualizer graphData={graphData} />
      </div>

      {/* Section D — Perturbation Controls */}
      <PerturbationPanel
        selectedStrategy={selectedStrategy}
        onStrategyChange={setSelectedStrategy}
        onGenerate={handleGenerate}
        isGenerating={isGenerating}
      />

      {/* Section E — Original vs Perturbed Text */}
      <DiffViewer
        originalText={sourceText}
        perturbedText={generatedPerturbation?.perturbedText || ''}
        diffs={generatedPerturbation?.diffs || []}
        strategy={selectedStrategy}
        activeStrategy={generatedPerturbation?.activeStrategy}
      />

      {/* Section F — Quality Validation Results */}
      <ValidationPanel
        checks={validationResult ? validationResult.checks : INITIAL_VALIDATION_CHECKS}
        isValid={validationResult ? validationResult.isValid : true}
        isEvaluated={Boolean(validationResult)}
      />

      {/* Section G — Fidelity Evaluation */}
      <FidelityPanel
        metrics={metrics}
        onEvaluate={handleEvaluateMetrics}
        isEvaluating={isEvaluating}
      />
    </div>
  );
};
