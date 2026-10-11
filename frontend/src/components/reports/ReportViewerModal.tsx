import React, { useState } from 'react';
import type { ResearchReportItem } from '../../types';
import { MarkdownDocumentViewer } from './MarkdownDocumentViewer';
import { JsonTreeViewer } from './JsonTreeViewer';
import { X, Copy, Check, RefreshCw, AlertCircle, FileText, FileCode, CheckCircle2 } from 'lucide-react';

interface ReportViewerModalProps {
  report: ResearchReportItem | null;
  content: string | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
  onRetry: () => void;
}

const DOCUMENT_BADGE_STYLES: Record<string, { badge: string; color: string; formatLabel: string }> = {
  phase13_report: {
    badge: 'RESEARCH REPORT',
    color: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    formatLabel: 'Markdown Research Document'
  },
  phase13_summary: {
    badge: 'JSON SUMMARY',
    color: 'bg-sky-50 text-sky-800 border-sky-200',
    formatLabel: 'Structured JSON Aggregate'
  },
  ablation_manifest: {
    badge: 'EXECUTION MANIFEST',
    color: 'bg-indigo-50 text-indigo-800 border-indigo-200',
    formatLabel: 'Execution Parameter Manifest'
  },
  step4_analysis: {
    badge: 'ANALYTICAL REPORT',
    color: 'bg-purple-50 text-purple-800 border-purple-200',
    formatLabel: 'Comparative Analysis Synthesis'
  }
};

export const ReportViewerModal: React.FC<ReportViewerModalProps> = ({
  report,
  content,
  isLoading,
  error,
  onClose,
  onRetry
}) => {
  const [isCopied, setIsCopied] = useState<boolean>(false);

  if (!report) return null;

  const isMarkdown = report.format === 'markdown';
  const badgeInfo = DOCUMENT_BADGE_STYLES[report.id] || {
    badge: isMarkdown ? 'RESEARCH REPORT' : 'JSON SUMMARY',
    color: isMarkdown
      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
      : 'bg-sky-50 text-sky-800 border-sky-200',
    formatLabel: isMarkdown ? 'Markdown Document' : 'JSON Data'
  };

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const copyButtonLabel = isMarkdown ? 'Copy Report Text' : 'Copy JSON Data';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
      <div className="bg-white rounded-2xl border border-[#E5E7EB] shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-scale-in">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E5E7EB] flex items-center justify-between bg-white">
          <div className="flex items-center gap-3 min-w-0 pr-4">
            <div className={`p-2 rounded-xl border shrink-0 ${isMarkdown ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-sky-50 border-sky-200 text-sky-700'}`}>
              {isMarkdown ? <FileText className="w-5 h-5" /> : <FileCode className="w-5 h-5" />}
            </div>
            <div className="min-w-0">
              <h3 className="text-base sm:text-lg font-bold text-[#111827] truncate leading-tight">
                {report.title}
              </h3>
              <p className="text-xs text-[#64748B] truncate mt-0.5">
                {report.description}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#1F2937] transition-colors cursor-pointer shrink-0"
            aria-label="Close report viewer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Professional Metadata & Action Bar */}
        <div className="px-6 py-2.5 bg-[#FDFBF7] border-b border-[#E5E7EB] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border font-mono ${badgeInfo.color}`}>
              {badgeInfo.badge}
            </span>
            <span className="font-semibold text-[#1F2937]">
              {report.artifactLabel || 'Research Findings'}
            </span>
            <span className="text-slate-300 hidden sm:inline">•</span>
            <span className="text-[#64748B] text-xs hidden sm:inline">
              {badgeInfo.formatLabel}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={!content || isLoading}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs disabled:opacity-50 ${
                isCopied
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                  : 'bg-white text-[#374151] border-[#E5E7EB] hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200'
              }`}
              title={copyButtonLabel}
            >
              {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{isCopied ? 'Copied!' : copyButtonLabel}</span>
            </button>
          </div>
        </div>

        {/* Compact Summary Metrics Strip (if available) */}
        {report.summaryMetrics && (
          <div className="px-6 py-2.5 bg-[#F8FAFC] border-b border-[#E5E7EB]">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
              {Object.entries(report.summaryMetrics).map(([key, val]) => (
                <div key={key} className="bg-white p-2 rounded-lg border border-[#E5E7EB] shadow-2xs">
                  <span className="text-[10px] text-[#64748B] font-medium block truncate uppercase tracking-wider">
                    {key}
                  </span>
                  <span className="font-bold text-[#1F2937] font-mono text-xs">
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Document Body Area */}
        <div className="p-6 overflow-y-auto flex-1 bg-white">
          {isLoading ? (
            <div className="py-16 text-center space-y-3">
              <RefreshCw className="w-6 h-6 animate-spin text-emerald-600 mx-auto" />
              <p className="text-xs font-semibold text-[#64748B]">
                Loading report artifact from backend server...
              </p>
            </div>
          ) : error ? (
            <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 space-y-3 my-4">
              <div className="flex items-center gap-2 font-bold text-sm">
                <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
                <span>Artifact Currently Unavailable</span>
              </div>
              <p className="text-rose-800 leading-relaxed">{error}</p>
              <div className="pt-2">
                <button
                  onClick={onRetry}
                  className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition-colors cursor-pointer shadow-xs"
                >
                  Retry Request
                </button>
              </div>
            </div>
          ) : content ? (
            isMarkdown ? (
              <div className="prose-container max-w-4xl mx-auto py-1">
                <MarkdownDocumentViewer content={content} />
              </div>
            ) : (
              <div className="max-w-4xl mx-auto py-1">
                <JsonTreeViewer data={content} />
              </div>
            )
          ) : (
            <div className="py-16 text-center text-xs text-[#94A3B8]">
              No content available for this report artifact.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-[#64748B]">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Authoritative research artifact</span>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleCopy}
              disabled={!content || isLoading}
              className="px-3 py-1.5 text-xs font-semibold text-[#4B5563] bg-white border border-[#E5E7EB] hover:bg-slate-50 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
            >
              {isCopied ? 'Copied!' : copyButtonLabel}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors cursor-pointer shadow-xs"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
