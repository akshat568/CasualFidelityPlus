import React from 'react';
import type { FidelityMetricScore } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { Cpu, Zap } from 'lucide-react';

interface FidelityPanelProps {
  metrics: FidelityMetricScore[];
  onEvaluate?: () => void;
  isEvaluating?: boolean;
}

export const FidelityPanel: React.FC<FidelityPanelProps> = ({
  metrics,
  onEvaluate,
  isEvaluating = false
}) => {
  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
      <div className="p-4 border-b border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-[#1F2937]">Causal Fidelity Metric Evaluation</h3>
        </div>
        <button
          type="button"
          onClick={onEvaluate}
          disabled={isEvaluating}
          className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer"
        >
          <Zap className="w-3.5 h-3.5 fill-current" />
          {isEvaluating ? 'Triggering Neural Models...' : 'Evaluate Metrics'}
        </button>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((metric) => (
          <div
            key={metric.name}
            className="bg-[#FDFBF7] rounded-xl border border-[#E5E7EB] p-4 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-sm font-bold text-[#1F2937]">{metric.name}</span>
                <StatusBadge status={metric.status} size="sm" />
              </div>

              <div className="my-3 py-2 px-3 bg-white rounded-lg border border-[#E5E7EB] text-center">
                <span className="text-xs text-[#64748B] block mb-1">Faithfulness Score</span>
                <span className="text-xl font-extrabold text-[#1F2937] font-mono">
                  {metric.originalScore !== undefined ? metric.originalScore.toFixed(4) : '—'}
                </span>
                {metric.delta !== undefined && (
                  <span
                    className={`block text-[11px] font-semibold mt-0.5 ${
                      metric.delta >= 0 ? 'text-emerald-700' : 'text-amber-700'
                    }`}
                  >
                    Delta: {metric.delta > 0 ? `+${metric.delta}` : metric.delta}
                  </span>
                )}
              </div>
            </div>

            <div>
              <p className="text-xs text-[#64748B] leading-relaxed">{metric.description}</p>
              {metric.details && (
                <p className="text-[11px] text-emerald-800 mt-2 font-mono bg-emerald-50 p-1.5 rounded border border-emerald-200">
                  {metric.details}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
