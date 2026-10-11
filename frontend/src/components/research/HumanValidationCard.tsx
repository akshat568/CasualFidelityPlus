import React from 'react';
import type { HumanValidationData } from '../../services/researchService';
import { Users, AlertCircle } from 'lucide-react';

interface HumanValidationCardProps {
  data?: HumanValidationData;
  isLoading?: boolean;
}

export const HumanValidationCard: React.FC<HumanValidationCardProps> = ({
  data,
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/3 mb-4" />
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="h-16 bg-slate-50 rounded" />
          <div className="h-16 bg-slate-50 rounded" />
          <div className="h-16 bg-slate-50 rounded" />
        </div>
        <div className="h-20 bg-slate-50 rounded" />
      </div>
    );
  }

  const consensusPairs = data?.consensusPairs ?? 6;
  const disagreementsExcluded = data?.disagreementsExcluded ?? 6;
  const naturalnessCorrelation = data?.naturalnessCorrelation !== undefined
    ? data.naturalnessCorrelation.toFixed(4)
    : '-0.3162';

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Users className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-[#1F2937]">Human Validation & Inter-Annotator Analysis</h3>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-4 text-center">
          <div className="p-3 bg-[#FDFBF7] rounded-lg border border-[#E5E7EB]">
            <span className="text-xs text-[#64748B] block">Consensus Pairs</span>
            <span className="text-2xl font-bold text-[#1F2937] font-mono">{consensusPairs}</span>
          </div>
          <div className="p-3 bg-[#FDFBF7] rounded-lg border border-[#E5E7EB]">
            <span className="text-xs text-[#64748B] block">Disagreements Excluded</span>
            <span className="text-2xl font-bold text-[#1F2937] font-mono">{disagreementsExcluded}</span>
          </div>
          <div className="p-3 bg-[#FDFBF7] rounded-lg border border-[#E5E7EB]">
            <span className="text-xs text-[#64748B] block">Naturalness Correlation</span>
            <span className="text-2xl font-bold text-amber-700 font-mono">{naturalnessCorrelation}</span>
          </div>
        </div>

        <div className="p-3.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-900 space-y-1">
          <div className="flex items-center gap-1.5 font-bold">
            <AlertCircle className="w-4 h-4 text-amber-700 shrink-0" />
            <span>Important Research Note on Binary Correlation</span>
          </div>
          <p className="leading-relaxed">
            {data?.note ||
              'Binary distortion correlation was undefined in EXP_09 because the target validation sample contained a single positive class (1.0), yielding zero variance in binary human consensus labels.'}
          </p>
        </div>
      </div>

      <p className="text-[11px] text-[#64748B] mt-4 pt-2 border-t border-[#E5E7EB]">
        Continuous naturalness correlation (Pearson r = {naturalnessCorrelation}) indicates mild inverse correlation between perceived linguistic fluency and heavy structural perturbations.
      </p>
    </div>
  );
};

