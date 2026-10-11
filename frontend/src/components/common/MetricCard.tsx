import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  description: string;
  badge?: string;
  badgeColor?: 'emerald' | 'amber' | 'neutral';
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  description,
  badge,
  badgeColor = 'emerald',
  icon
}) => {
  const badgeStyles = {
    emerald: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    neutral: 'bg-slate-50 text-slate-700 border-slate-200'
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-[#E5E7EB] shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">{title}</span>
          {icon && <div className="text-emerald-600">{icon}</div>}
        </div>
        <div className="text-3xl font-extrabold text-[#1F2937] tracking-tight mb-1">{value}</div>
      </div>
      <div>
        <p className="text-xs text-[#64748B] mt-2 font-normal leading-relaxed">{description}</p>
        {badge && (
          <span className={`inline-block mt-3 px-2 py-0.5 text-[11px] font-medium rounded-md border ${badgeStyles[badgeColor]}`}>
            {badge}
          </span>
        )}
      </div>
    </div>
  );
};
