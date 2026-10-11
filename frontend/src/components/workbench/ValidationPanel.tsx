import React from 'react';
import type { ValidationCheckResult } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { ShieldCheck, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-react';

interface ValidationPanelProps {
  checks: ValidationCheckResult[];
  isValid?: boolean;
  isEvaluated?: boolean;
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  checks,
  isValid = true,
  isEvaluated = false
}) => {
  const getIcon = (status: string) => {
    switch (status) {
      case 'PASSED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />;
      case 'FAILED':
        return <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />;
      default:
        return <HelpCircle className="w-4 h-4 text-slate-400 shrink-0" />;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
      <div className="p-4 border-b border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-[#1F2937]">Perturbation Quality Control Validation</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#64748B] font-medium">Validation Status:</span>
          {isEvaluated ? (
            <StatusBadge status={isValid ? 'PASSED' : 'FAILED'} />
          ) : (
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
              Not Evaluated
            </span>
          )}
        </div>
      </div>

      <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        {['Structural', 'Relational', 'Content'].map((category) => {
          const categoryChecks = checks.filter((c) => c.category === category);
          return (
            <div key={category} className="bg-[#FDFBF7] p-4 rounded-xl border border-[#E5E7EB]">
              <h4 className="text-xs font-bold text-[#1F2937] uppercase tracking-wider mb-3 pb-2 border-b border-[#E5E7EB]">
                {category} Checks
              </h4>
              <div className="space-y-3">
                {categoryChecks.length === 0 ? (
                  <p className="text-xs text-[#64748B] italic">No checks evaluated in this category.</p>
                ) : (
                  categoryChecks.map((check, idx) => (
                    <div key={idx} className="flex items-start gap-2 bg-white p-2.5 rounded-lg border border-[#E5E7EB]">
                      {getIcon(check.status)}
                      <div className="flex-1">
                        <div className="flex items-center justify-between gap-1 mb-0.5">
                          <span className="text-xs font-bold text-[#1F2937]">{check.checkName}</span>
                          <StatusBadge status={check.status} size="sm" />
                        </div>
                        <p className="text-[11px] text-[#64748B] leading-tight">{check.details}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
