import React from 'react';
import type { CausalRelation } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { GitCommit } from 'lucide-react';

interface CausalRelationTableProps {
  relations: CausalRelation[];
}

export const CausalRelationTable: React.FC<CausalRelationTableProps> = ({ relations }) => {
  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
      <div className="p-4 border-b border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-[#1F2937]">Extracted Causal Relations</h3>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
          {relations.length} relations found
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E5E7EB] font-semibold uppercase text-[10px] tracking-wider">
              <th className="p-3">Relation ID</th>
              <th className="p-3">Cause Node</th>
              <th className="p-3">Effect Node</th>
              <th className="p-3">Connective</th>
              <th className="p-3">Confidence</th>
              <th className="p-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E7EB]">
            {relations.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-[#64748B] bg-white">
                  No causal relations extracted yet. Enter source text above and click "Extract Causal Relations".
                </td>
              </tr>
            ) : (
              relations.map((rel) => (
                <tr key={rel.id} className="hover:bg-emerald-50/40 transition-colors">
                  <td className="p-3 font-mono font-semibold text-emerald-700">{rel.id}</td>
                  <td className="p-3 font-medium text-[#1F2937] max-w-xs">{rel.cause}</td>
                  <td className="p-3 font-medium text-[#1F2937] max-w-xs">{rel.effect}</td>
                  <td className="p-3 font-mono bg-[#F8FAFC] rounded text-emerald-800 border border-[#E5E7EB] inline-block my-2">
                    {rel.connective}
                  </td>
                  <td className="p-3">
                    <span className="font-semibold text-slate-700">{(rel.confidence * 100).toFixed(0)}%</span>
                  </td>
                  <td className="p-3 text-right">
                    <StatusBadge status={rel.status || 'ACTIVE'} size="sm" />
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
