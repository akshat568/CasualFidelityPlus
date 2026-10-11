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
import type { WeightSensitivityItem } from '../../services/researchService';

interface WeightSensitivityChartProps {
  data?: WeightSensitivityItem[];
  isLoading?: boolean;
}

export const WeightSensitivityChart: React.FC<WeightSensitivityChartProps> = ({
  data = [],
  isLoading = false
}) => {
  if (isLoading) {
    return (
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/3 mb-2" />
        <div className="h-3 bg-slate-100 rounded w-1/2 mb-6" />
        <div className="h-56 bg-slate-50 rounded" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs text-center py-12">
        <h3 className="text-sm font-bold text-[#1F2937] mb-1">Weight Sensitivity Analysis</h3>
        <p className="text-xs text-[#64748B]">No weight sensitivity data available.</p>
      </div>
    );
  }

  const equalWeights = data.find(d => d.name.includes('Equal'));
  const argOnly = data.find(d => d.name.includes('Argument-Only') || d.name.includes('Arg-Only'));

  return (
    <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-[#1F2937]">Weight Sensitivity Analysis</h3>
          <p className="text-xs text-[#64748B]">Impact of component weighting on composite alignment score</p>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} />
            <YAxis tick={{ fontSize: 11, fill: '#64748B' }} domain={[0, 0.6]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderColor: '#E5E7EB',
                borderRadius: '8px',
                fontSize: '12px'
              }}
              formatter={(value: any, _name: any, props: any) => [
                `${typeof value === 'number' ? value.toFixed(4) : value} (${props.payload.delta})`,
                'Composite Alignment Score'
              ]}
            />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={index === 0 ? '#059669' : index === 1 ? '#D97706' : '#F97316'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {(equalWeights || argOnly) && (
        <div className="mt-3 pt-3 border-t border-[#E5E7EB] grid grid-cols-2 gap-2 text-xs">
          {equalWeights && (
            <div className="p-2 bg-amber-50 rounded-lg border border-amber-200">
              <span className="font-bold text-amber-900 block">Equal Weights: {equalWeights.delta}</span>
              <span className="text-[11px] text-amber-800">Over-rewards generic connective matching</span>
            </div>
          )}
          {argOnly && (
            <div className="p-2 bg-orange-50 rounded-lg border border-orange-200">
              <span className="font-bold text-orange-900 block">Arg-Only: {argOnly.delta}</span>
              <span className="text-[11px] text-orange-800">Isolates core cause/effect argument overlap</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

