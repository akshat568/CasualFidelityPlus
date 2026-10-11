import React from 'react';
import type { PerturbationStrategy } from '../../types';
import { Sliders, Sparkles } from 'lucide-react';

interface PerturbationPanelProps {
  selectedStrategy: PerturbationStrategy;
  onStrategyChange: (strategy: PerturbationStrategy) => void;
  onGenerate: () => void;
  isGenerating?: boolean;
}

const STRATEGY_DESCRIPTIONS: Record<PerturbationStrategy, string> = {
  REVERSED: 'Inverts cause and effect roles (X → Y becomes Y → X)',
  WEAKENED: 'Replaces deterministic connective with correlation or probabilistic phrasing',
  DROPPED: 'Removes target causal connective and relation structure entirely',
  CAUSE_CHANGED: 'Replaces the cause argument with a counterfactual entity',
  EFFECT_CHANGED: 'Replaces the effect argument with a counterfactual outcome'
};

export const PerturbationPanel: React.FC<PerturbationPanelProps> = ({
  selectedStrategy,
  onStrategyChange,
  onGenerate,
  isGenerating = false
}) => {
  const strategies: PerturbationStrategy[] = [
    'REVERSED',
    'WEAKENED',
    'DROPPED',
    'CAUSE_CHANGED',
    'EFFECT_CHANGED'
  ];

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs">
      <div className="flex items-center gap-2 mb-3">
        <Sliders className="w-4 h-4 text-emerald-600" />
        <h3 className="text-sm font-bold text-[#1F2937]">Controlled Perturbation Engine</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        <div className="md:col-span-2">
          <label className="block text-xs font-semibold text-[#64748B] mb-1.5 uppercase tracking-wider">
            Select Distortion Strategy
          </label>
          <select
            value={selectedStrategy}
            onChange={(e) => onStrategyChange(e.target.value as PerturbationStrategy)}
            className="w-full p-2.5 text-xs font-semibold rounded-lg border border-[#E5E7EB] bg-[#FDFBF7] text-[#1F2937] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all cursor-pointer"
          >
            {strategies.map((strat) => (
              <option key={strat} value={strat}>
                {strat} — {STRATEGY_DESCRIPTIONS[strat]}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-[#64748B] mt-1.5 italic">
            {STRATEGY_DESCRIPTIONS[selectedStrategy]}
          </p>
        </div>

        <div>
          <button
            type="button"
            onClick={onGenerate}
            disabled={isGenerating}
            className="w-full py-2.5 px-4 text-xs font-bold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            {isGenerating ? 'Applying Distortion...' : 'Generate Perturbation'}
          </button>
        </div>
      </div>
    </div>
  );
};
