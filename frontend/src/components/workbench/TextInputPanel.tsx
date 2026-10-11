import React from 'react';
import { RotateCcw, Play, FileText } from 'lucide-react';

interface TextInputPanelProps {
  text: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  onClear: () => void;
  onLoadSample: () => void;
  isAnalyzing?: boolean;
}

export const TextInputPanel: React.FC<TextInputPanelProps> = ({
  text,
  onChange,
  onAnalyze,
  onClear,
  onLoadSample,
  isAnalyzing = false
}) => {
  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-emerald-600" />
          <h2 className="text-sm font-bold text-[#1F2937]">Source Text Editor</h2>
        </div>
        <span className="text-xs text-[#64748B] font-mono bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#E5E7EB]">
          {text.length} characters | {text.trim() ? text.trim().split(/\s+/).length : 0} words
        </span>
      </div>

      <textarea
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter or paste source text containing causal statements (e.g., 'X caused Y because Z')..."
        rows={4}
        className="w-full p-3.5 text-sm rounded-lg border border-[#E5E7EB] bg-[#FDFBF7] text-[#1F2937] placeholder-[#94A3B8] focus:bg-white focus:outline-hidden focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-mono leading-relaxed resize-y"
      />

      <div className="flex flex-wrap items-center justify-between gap-3 mt-4 pt-3 border-t border-[#E5E7EB]">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onLoadSample}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            Insert Sample Text
          </button>
          <button
            type="button"
            onClick={onClear}
            disabled={!text}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-[#F8FAFC] text-[#64748B] border border-[#E5E7EB] hover:bg-[#E5E7EB] hover:text-[#1F2937] disabled:opacity-50 transition-colors flex items-center gap-1 cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Clear
          </button>
        </div>

        <button
          type="button"
          onClick={onAnalyze}
          disabled={!text.trim() || isAnalyzing}
          className="px-4 py-2 text-xs font-bold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors flex items-center gap-2 shadow-xs cursor-pointer"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          {isAnalyzing ? 'Extracting Relations...' : 'Extract Causal Relations'}
        </button>
      </div>
    </div>
  );
};
