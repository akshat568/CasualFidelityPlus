import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import type { AlignmentComparisonItem } from '../../services/researchService';

interface AlignmentChartProps {
  data?: AlignmentComparisonItem[];
  baselineScore?: number;
  isLoading?: boolean;
}

export const AlignmentChart: React.FC<AlignmentChartProps> = ({
  data = [],
  baselineScore = 0.3195,
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/3 mb-2" />
        <div className="h-3 bg-slate-100 rounded w-1/2 mb-6" />
        <div className="h-64 bg-slate-50 rounded" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs text-center py-12">
        <h3 className="text-sm font-bold text-[#1F2937] mb-1">Experiment Alignment Comparison</h3>
        <p className="text-xs text-[#64748B]">No experiment alignment data available.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-[#1F2937]">Experiment Alignment Comparison</h3>
          <p className="text-xs text-[#64748B]">Mean causal alignment across ablation configurations</p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
          Baseline = {baselineScore.toFixed(4)}
        </span>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis
              dataKey="experiment"
              tick={{ fontSize: 10, fill: '#64748B' }}
              interval={0}
              angle={-20}
              textAnchor="end"
            />
            <YAxis tick={{ fontSize: 11, fill: '#64748B' }} domain={[0, 0.6]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderColor: '#E5E7EB',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
              formatter={(value: any) => [typeof value === 'number' ? value.toFixed(4) : value, 'Mean Alignment Score']}
            />
            <Bar dataKey="alignment" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={
                    entry.experiment.includes('Equal') || entry.experiment.includes('WEIGHT EQUAL')
                      ? '#D97706' // Amber accent for inflation
                      : entry.experiment.includes('Arg Only') || entry.experiment.includes('WEIGHT ARG ONLY')
                      ? '#F97316' // Coral accent for reduction
                      : '#059669' // Emerald green for baseline & defaults
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

