import React, { useState, useEffect, useCallback } from 'react';
import { fetchResearchData, invalidateResearchCache, type ParsedResearchData } from '../services/researchService';
import type { ResearchExperiment } from '../types';
import { ExperimentSummaryTable } from '../components/research/ExperimentSummaryTable';
import { HumanValidationCard } from '../components/research/HumanValidationCard';
import { ResearchLimitationsCard } from '../components/research/ResearchLimitationsCard';
import { WeightSensitivityChart } from '../components/dashboard/WeightSensitivityChart';
import { MetricAblationChart } from '../components/dashboard/MetricAblationChart';
import { Modal } from '../components/common/Modal';
import { StatusBadge } from '../components/common/StatusBadge';
import { BarChart3, FlaskConical, AlertCircle, RefreshCw } from 'lucide-react';

export const ResearchPage: React.FC = () => {
  const [researchData, setResearchData] = useState<ParsedResearchData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedExp, setSelectedExp] = useState<ResearchExperiment | null>(null);

  const loadData = useCallback(async (forceRefresh = false) => {
    setIsLoading(true);
    setError(null);
    try {
      if (forceRefresh) {
        invalidateResearchCache();
      }
      const data = await fetchResearchData(forceRefresh);
      setResearchData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve research findings from the backend API.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6">
      {/* Page Header Banner */}
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#1F2937]">Causal Fidelity Research Dashboard</h2>
          <p className="text-xs text-[#64748B]">
            Explore experimental results, evaluate metric sensitivity, and analyze human validation findings for causal faithfulness in LLM summarization.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
            <BarChart3 className="w-4 h-4 text-emerald-600" />
            <span>Research Analysis Complete</span>
          </div>
          <button
            onClick={() => loadData(true)}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#F8FAFC] text-[#1F2937] border border-[#E5E7EB] hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Refresh research matrix from backend"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error State Banner with Retry */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-900 flex items-start justify-between gap-3 shadow-xs">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-sm block mb-0.5">Research Data Unavailable</span>
              <p className="text-rose-800 leading-relaxed">{error}</p>
              <p className="text-[11px] text-rose-700 mt-1">
                Please verify that the FastAPI backend server is running and accessible at the configured API base URL.
              </p>
            </div>
          </div>
          <button
            onClick={() => loadData(true)}
            className="px-3 py-1.5 text-xs font-bold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition-colors shrink-0 cursor-pointer shadow-xs"
          >
            Retry Request
          </button>
        </div>
      )}

      {/* Section A — Experiment Summary Table */}
      <ExperimentSummaryTable
        experiments={researchData?.experiments || []}
        isLoading={isLoading}
        onSelectExperiment={(exp) => setSelectedExp(exp)}
      />

      {/* Section B & C — Weight Sensitivity & Metric Ablation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-bold text-[#1F2937] mb-3 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-emerald-600" /> Weight Model Sensitivity Analysis
          </h3>
          <WeightSensitivityChart
            data={researchData?.weightSensitivity}
            isLoading={isLoading}
          />
        </div>
        <div>
          <h3 className="text-sm font-bold text-[#1F2937] mb-3 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-emerald-600" /> Metric Ablation Computational Cost
          </h3>
          <MetricAblationChart
            data={researchData?.metricAblation}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Section D — Human Validation Analysis */}
      <HumanValidationCard
        data={researchData?.humanValidation}
        isLoading={isLoading}
      />

      {/* Section E — Research Limitations */}
      <ResearchLimitationsCard
        limitations={researchData?.limitations}
        isLoading={isLoading}
      />

      {/* Experiment Detail Modal */}
      <Modal
        isOpen={selectedExp !== null}
        onClose={() => setSelectedExp(null)}
        title={selectedExp ? `${selectedExp.id}: ${selectedExp.name}` : 'Experiment Details'}
      >
        {selectedExp && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-[#F8FAFC] p-3 rounded-lg border border-[#E5E7EB]">
              <div>
                <span className="text-xs text-[#64748B] block">Experiment Type</span>
                <span className="font-bold text-[#1F2937]">{selectedExp.type}</span>
              </div>
              <StatusBadge status={selectedExp.status} />
            </div>

            <div>
              <h4 className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-1">Description</h4>
              <p className="text-xs text-[#1F2937] bg-[#FDFBF7] p-3 rounded-lg border border-[#E5E7EB]">
                {selectedExp.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB]">
                <span className="text-[#64748B] block">Mean Alignment Score</span>
                <span className="font-bold font-mono text-emerald-700 text-sm">
                  {selectedExp.meanAlignment !== undefined ? selectedExp.meanAlignment.toFixed(4) : 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB]">
                <span className="text-[#64748B] block">Runtime Duration</span>
                <span className="font-bold font-mono text-slate-800 text-sm">
                  {selectedExp.runtimeSeconds !== undefined ? `${selectedExp.runtimeSeconds.toFixed(1)}s` : 'N/A'}
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-1">Available Metrics</h4>
              <div className="flex flex-wrap gap-1.5">
                {selectedExp.availableMetrics.map((m: string) => (
                  <span key={m} className="px-2 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
                    {m}
                  </span>
                ))}
              </div>
            </div>

            {selectedExp.notes && (
              <div>
                <h4 className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-1">Findings Note</h4>
                <p className="text-xs text-amber-900 bg-amber-50 p-3 rounded-lg border border-amber-200 leading-relaxed">
                  {selectedExp.notes}
                </p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

