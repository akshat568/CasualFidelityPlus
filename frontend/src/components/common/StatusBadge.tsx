import React from 'react';

export type StatusType =
  | 'PASSED'
  | 'FAILED'
  | 'COMPLETED'
  | 'RUNNING'
  | 'NOT_EVALUATED'
  | 'ABLATED'
  | 'UNAVAILABLE'
  | 'ACTIVE'
  | 'PERTURBED';

interface StatusBadgeProps {
  status: StatusType | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toUpperCase();

  const getStyle = () => {
    switch (normalized) {
      case 'PASSED':
      case 'COMPLETED':
      case 'ACTIVE':
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 'FAILED':
        return 'bg-rose-50 text-rose-800 border-rose-200';
      case 'RUNNING':
      case 'PERTURBED':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'NOT_EVALUATED':
      case 'ABLATED':
      case 'UNAVAILABLE':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const sizeStyle = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center font-semibold rounded-md border ${getStyle()} ${sizeStyle}`}>
      {status}
    </span>
  );
};
