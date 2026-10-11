import React from 'react';
import { Columns, ArrowRight } from 'lucide-react';
import type { PerturbationStrategy } from '../../types';

interface DiffViewerProps {
  originalText: string;
  perturbedText: string;
  diffs?: { type: 'added' | 'removed' | 'same'; text: string }[];
  strategy: PerturbationStrategy;
  activeStrategy?: PerturbationStrategy | null;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  originalText,
  perturbedText,
  diffs = [],
  strategy,
  activeStrategy
}) => {
  const displayStrategy = activeStrategy || strategy;
  const isGenerated = Boolean(perturbedText && perturbedText.trim());

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
      <div className="p-4 border-b border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Columns className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-[#1F2937]">Original vs. Perturbed Text Analysis</h3>
        </div>
        <span
          className={`text-xs font-semibold px-2.5 py-1 rounded border ${
            isGenerated
              ? 'bg-amber-100 text-amber-900 border-amber-200'
              : 'bg-slate-100 text-slate-600 border-slate-200'
          }`}
        >
          {isGenerated ? `Strategy Active: ${displayStrategy}` : `Selected: ${strategy} (Not Generated)`}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[#E5E7EB]">
        {/* Original Text Panel */}
        <div className="p-5 bg-white">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider">Original Text</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 font-mono text-slate-700">Reference</span>
          </div>
          <p className="text-sm text-[#1F2937] leading-relaxed font-mono bg-[#FDFBF7] p-4 rounded-lg border border-[#E5E7EB] min-h-24">
            {originalText || '(No source text entered)'}
          </p>
        </div>

        {/* Perturbed Text Panel */}
        <div className="p-5 bg-[#F8FAFC]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1">
              Perturbed Text <ArrowRight className="w-3.5 h-3.5 text-amber-600" />
            </span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                isGenerated ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-600'
              }`}
            >
              {isGenerated ? 'Distorted' : 'Awaiting Generation'}
            </span>
          </div>

          <div className="text-sm leading-relaxed font-mono bg-white p-4 rounded-lg border border-amber-200 text-[#1F2937] min-h-24">
            {!isGenerated ? (
              <span className="text-slate-400 italic font-sans text-xs">
                No perturbation generated yet. Select a strategy above and click "Generate Perturbation".
              </span>
            ) : diffs.length > 0 ? (
              diffs.map((part, index) => {
                if (part.type === 'removed') {
                  return (
                    <span
                      key={index}
                      className="bg-rose-100 text-rose-900 font-bold px-1 py-0.5 rounded line-through mx-0.5"
                    >
                      {part.text}
                    </span>
                  );
                }
                if (part.type === 'added') {
                  return (
                    <span
                      key={index}
                      className="bg-emerald-100 text-emerald-900 font-bold px-1 py-0.5 rounded mx-0.5 border-b-2 border-emerald-600"
                    >
                      {part.text}
                    </span>
                  );
                }
                return <span key={index}>{part.text}</span>;
              })
            ) : (
              <span>{perturbedText}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
