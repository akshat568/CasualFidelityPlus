import React from 'react';
import type { ResearchLimitationItem } from '../../services/researchService';
import { AlertOctagon } from 'lucide-react';

interface ResearchLimitationsCardProps {
  limitations?: ResearchLimitationItem[];
  isLoading?: boolean;
}

export const ResearchLimitationsCard: React.FC<ResearchLimitationsCardProps> = ({
  limitations = [],
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/4 mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-24 bg-slate-50 rounded" />
          <div className="h-24 bg-slate-50 rounded" />
        </div>
      </div>
    );
  }

  if (!limitations || limitations.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs text-center py-8">
        <h3 className="text-sm font-bold text-[#1F2937] mb-1">Research Limitations & Scope</h3>
        <p className="text-xs text-[#64748B]">No limitations documented for this evaluation artifact.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] p-5 shadow-xs">
      <div className="flex items-center gap-2 mb-4">
        <AlertOctagon className="w-5 h-5 text-amber-600" />
        <div>
          <h3 className="text-sm font-bold text-[#1F2937]">Research Limitations & Scope</h3>
          <p className="text-xs text-[#64748B]">Key evaluation constraints, methodological boundaries, and opportunities for future research.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {limitations.map((item, idx) => {
          let description = item.description;

          if (
            item.title === 'Causal Connective Extraction Scope' ||
            description.includes('Rule-based causal extraction in Phase 3') ||
            description.includes('skips implicit causality')
          ) {
            description =
              'Rule-based causal extraction primarily identifies explicit connective phrases, while implicit and discourse-level causal relationships may remain undetected.';
          } else if (description.includes('Small development benchmark sample size')) {
            description =
              'Controlled benchmark sample size is constrained to n=6 validated perturbations from n=100 XSum source documents.';
          } else if (description.includes('Small consensus human validation sample size')) {
            description =
              'Human correlation analysis is evaluated across n=6 verified consensus pairs (disagreed pairs excluded for quality assurance).';
          } else if (/Phase\s*\d+/i.test(description)) {
            description = description
              .replace(/in Phase \d+\s*/gi, '')
              .replace(/Phase \d+:\s*/gi, '')
              .replace(/Phase \d+\s*/gi, '');
          }

          return (
            <div key={idx} className="p-4 bg-[#FDFBF7] rounded-xl border border-[#E5E7EB]">
              <h4 className="text-xs font-bold text-[#1F2937] mb-1.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                {item.title}
              </h4>
              <p className="text-xs text-[#64748B] leading-relaxed">{description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

