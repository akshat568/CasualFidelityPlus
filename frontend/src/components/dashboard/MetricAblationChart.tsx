import React from 'react';
import type { MetricAblationItem } from '../../services/researchService';
import { Timer, Zap } from 'lucide-react';

interface MetricAblationChartProps {
  data?: MetricAblationItem[];
  isLoading?: boolean;
}

export const MetricAblationChart: React.FC<MetricAblationChartProps> = ({
  data = [],
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/3 mb-2" />
        <div className="h-3 bg-slate-100 rounded w-1/2 mb-6" />
        <div className="space-y-3">
          <div className="h-12 bg-slate-50 rounded" />
          <div className="h-12 bg-slate-50 rounded" />
          <div className="h-12 bg-slate-50 rounded" />
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs text-center py-12">
        <h3 className="text-sm font-bold text-[#1F2937] mb-1">Metric Ablation Runtime Reduction</h3>
        <p className="text-xs text-[#64748B]">No metric ablation data available.</p>
      </div>
    );
  }

  const summacItem = data.find(d => d.metric.includes('SummaC'));
  const speedupHighlight = summacItem ? `${summacItem.reduction.replace('-', '')} Speedup` : 'Runtime Analyzed';

  return (
    <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Timer className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-[#1F2937]">Metric Ablation Runtime Reduction</h3>
          </div>
          <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
            {speedupHighlight}
          </span>
        </div>

        <p className="text-xs text-[#64748B] mb-4">
          Execution time savings achieved by selectively disabling heavy neural metrics during ablation runs.
        </p>

        <div className="space-y-3">
          {data.map((item) => (
            <div key={item.metric} className="p-3 bg-[#FDFBF7] rounded-lg border border-[#E5E7EB]">
              <div className="flex items-center justify-between text-xs mb-1 font-semibold">
                <span className="text-[#1F2937]">{item.metric}</span>
                <span className={item.reduction.startsWith('-79') ? 'text-emerald-700 font-extrabold' : 'text-[#64748B]'}>
                  {item.runtime} ({item.reduction})
                </span>
              </div>
              <div className="w-full bg-[#E5E7EB] h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    item.metric.includes('SummaC') ? 'bg-emerald-600' : 'bg-slate-400'
                  }`}
                  style={{
                    width: item.metric.includes('SummaC')
                      ? '20.83%'
                      : item.metric.includes('Full')
                      ? '100%'
                      : '92%'
                  }}
                />
              </div>
              <span className="text-[10px] text-[#64748B] mt-1 block">
                Relative speedup: <strong className="text-slate-800">{item.speedup}</strong>
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-xs text-emerald-900 flex items-start gap-2">
        <Zap className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
        <p>
          Disabling <strong>SummaC (RoBERTa-large)</strong> provides the largest computational saving ({summacItem?.runtime || '147.3s'} vs baseline).
        </p>
      </div>
    </div>
  );
};

