import React from 'react';
import type { ResearchReportItem } from '../../types';
import { FileCode, FileText, Eye } from 'lucide-react';

interface ReportCardProps {
  report: ResearchReportItem;
  onViewReport: (report: ResearchReportItem) => void;
}

export const ReportCard: React.FC<ReportCardProps> = ({ report, onViewReport }) => {
  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            {report.format === 'markdown' ? (
              <FileText className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <FileCode className="w-5 h-5 text-amber-600 shrink-0" />
            )}
            <h3 className="text-sm font-bold text-[#1F2937] leading-snug">{report.title}</h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold uppercase">
            {report.format}
          </span>
        </div>

        <div className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 mb-3 truncate">
          {report.artifactLabel || report.title}
        </div>

        <p className="text-xs text-[#64748B] leading-relaxed mb-4">{report.description}</p>

        {report.summaryMetrics && (
          <div className="grid grid-cols-2 gap-2 my-3 p-3 bg-[#FDFBF7] rounded-lg border border-[#E5E7EB] text-xs">
            {Object.entries(report.summaryMetrics).map(([key, val]) => (
              <div key={key}>
                <span className="text-[10px] text-[#64748B] block truncate">{key}</span>
                <span className="font-bold text-[#1F2937] font-mono">{val}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-[#E5E7EB]">
        <button
          type="button"
          onClick={() => onViewReport(report)}
          className="w-full py-2 px-3 text-xs font-bold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
        >
          <Eye className="w-3.5 h-3.5" /> View Report
        </button>
      </div>
    </div>
  );
};
