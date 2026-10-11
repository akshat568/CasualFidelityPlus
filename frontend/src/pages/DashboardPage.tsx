import React, { useState, useEffect, useCallback } from 'react';
import { fetchResearchData, invalidateResearchCache, type ParsedResearchData } from '../services/researchService';
import { MetricCard } from '../components/common/MetricCard';
import { AlignmentChart } from '../components/dashboard/AlignmentChart';
import { WeightSensitivityChart } from '../components/dashboard/WeightSensitivityChart';
import { MetricAblationChart } from '../components/dashboard/MetricAblationChart';
import { FlaskConical, Target, CheckCircle, Users, AlertCircle, RefreshCw } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [researchData, setResearchData] = useState<ParsedResearchData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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
      setError(err.message || 'Failed to retrieve research summary artifact from the backend API.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6">
      {/* Page Subtitle Banner */}
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#1F2937]">Research Overview & Baseline Key Findings</h2>
          <p className="text-xs text-[#64748B] mt-1">
            Explore causal relationships, evaluate summarization faithfulness, and analyze the impact of controlled distortions on LLM outputs.
          </p>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={isLoading}
          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#F8FAFC] text-[#1F2937] border border-[#E5E7EB] hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          title="Refresh research metrics from backend"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Data</span>
        </button>
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

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Experiments"
          value={isLoading ? '—' : researchData ? researchData.summary.totalExperiments : 'Unavailable'}
          description={researchData ? researchData.summary.totalExperimentsDesc : 'Ablation study evaluations'}
          badge="Ablation Matrix"
          icon={<FlaskConical className="w-5 h-5" />}
        />
        <MetricCard
          title="Baseline Alignment"
          value={isLoading ? '—' : researchData ? researchData.summary.baselineAlignment.toFixed(4) : 'Unavailable'}
          description={researchData ? researchData.summary.baselineAlignmentDesc : 'Overall mean alignment score'}
          badge="Overall Mean Score"
          icon={<Target className="w-5 h-5" />}
        />
        <MetricCard
          title="Benchmark Agreement"
          value={isLoading ? '—' : researchData ? researchData.summary.benchmarkAgreement : 'Unavailable'}
          description={researchData ? researchData.summary.benchmarkAgreementDesc : 'Controlled benchmark subsample'}
          badge="XSum Subsample"
          icon={<CheckCircle className="w-5 h-5" />}
        />
        <MetricCard
          title="Human Consensus Pairs"
          value={isLoading ? '—' : researchData ? researchData.summary.humanConsensusPairs : 'Unavailable'}
          description={researchData ? researchData.summary.humanConsensusPairsDesc : 'Consensus pairs analyzed'}
          badge="Gold Standard"
          badgeColor="amber"
          icon={<Users className="w-5 h-5" />}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <AlignmentChart
            data={researchData?.alignmentComparison}
            baselineScore={researchData?.summary.baselineAlignment}
            isLoading={isLoading}
          />
        </div>
        <div>
          <WeightSensitivityChart
            data={researchData?.weightSensitivity}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Second Row: Ablation Speedups */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-3">
          <MetricAblationChart
            data={researchData?.metricAblation}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};

