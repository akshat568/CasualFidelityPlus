import React from 'react';
import type { ResearchExperiment } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { ExternalLink } from 'lucide-react';

interface ExperimentSummaryTableProps {
  experiments: ResearchExperiment[];
  isLoading?: boolean;
  onSelectExperiment?: (exp: ResearchExperiment) => void;
}

export const ExperimentSummaryTable: React.FC<ExperimentSummaryTableProps> = ({
  experiments = [],
  isLoading = false,
  onSelectExperiment
}) => {
  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
      <div className="p-4 border-b border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
        <h3 className="text-sm font-bold text-[#1F2937]">
          Ablation Experiments ({isLoading ? '…' : `${experiments.length} Total`})
        </h3>
        <span className="text-xs font-mono text-[#64748B]">
          {isLoading ? 'Loading matrix…' : `${experiments.filter(e => e.status === 'COMPLETED').length} of ${experiments.length} completed`}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E5E7EB] font-semibold uppercase text-[10px] tracking-wider">
              <th className="p-3">Experiment ID</th>
              <th className="p-3">Experiment Type</th>
              <th className="p-3">Status</th>
              <th className="p-3">Available Metrics</th>
              <th className="p-3">Mean Alignment</th>
              <th className="p-3">Runtime</th>
              <th className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E7EB]">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-[#64748B]">
                  Loading experiment records from backend artifact…
                </td>
              </tr>
            ) : experiments.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-[#64748B]">
                  No experiment records found in research matrix.
                </td>
              </tr>
            ) : (
              experiments.map((exp) => (
                <tr key={exp.id} className="hover:bg-emerald-50/40 transition-colors">
                  <td className="p-3 font-mono font-bold text-emerald-700">{exp.id}</td>
                  <td className="p-3 font-medium text-[#1F2937]">{exp.type}</td>
                  <td className="p-3">
                    <StatusBadge status={exp.status} size="sm" />
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {exp.availableMetrics.map((m) => (
                        <span key={m} className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-mono">
                          {m}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-3 font-mono font-semibold text-[#1F2937]">
                    {exp.meanAlignment !== undefined ? exp.meanAlignment.toFixed(4) : 'N/A'}
                  </td>
                  <td className="p-3 font-mono text-[#64748B]">
                    {exp.runtimeSeconds !== undefined ? `${exp.runtimeSeconds.toFixed(1)}s` : '—'}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => onSelectExperiment?.(exp)}
                      className="px-2.5 py-1 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100 rounded transition-colors inline-flex items-center gap-1 cursor-pointer"
                    >
                      Details <ExternalLink className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

