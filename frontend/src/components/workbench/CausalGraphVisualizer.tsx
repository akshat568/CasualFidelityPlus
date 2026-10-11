import React, { useState } from 'react';
import type { CausalGraphData } from '../../types';
import { Network, ArrowRight, Code } from 'lucide-react';

interface CausalGraphVisualizerProps {
  graphData: CausalGraphData;
}

export const CausalGraphVisualizer: React.FC<CausalGraphVisualizerProps> = ({ graphData }) => {
  const [activeView, setActiveView] = useState<'visual' | 'code'>('visual');

  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
      <div className="p-4 border-b border-[#E5E7EB] bg-[#F8FAFC] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-[#1F2937]">Causal DiGraph Visualization</h3>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
            {graphData.isDag ? 'Directed Acyclic Graph (DAG)' : 'Graph'}
          </span>
          <div className="flex bg-[#E5E7EB] p-0.5 rounded-lg text-xs font-medium">
            <button
              onClick={() => setActiveView('visual')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                activeView === 'visual' ? 'bg-white text-emerald-800 font-bold shadow-2xs' : 'text-[#64748B]'
              }`}
            >
              Node Flow
            </button>
            <button
              onClick={() => setActiveView('code')}
              className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 cursor-pointer ${
                activeView === 'code' ? 'bg-white text-emerald-800 font-bold shadow-2xs' : 'text-[#64748B]'
              }`}
            >
              <Code className="w-3 h-3" /> Mermaid Code
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 bg-[#FDFBF7] min-h-48 flex items-center justify-center">
        {activeView === 'visual' ? (
          <div className="w-full space-y-4">
            <div className="flex flex-wrap items-center justify-center gap-3">
              {graphData.nodes.map((node, index) => {
                const outgoingEdge = graphData.edges.find((e) => e.source === node.id);
                return (
                  <React.Fragment key={node.id}>
                    {/* Node Card */}
                    <div className="bg-white px-4 py-3 rounded-xl border-2 border-emerald-500 shadow-xs flex flex-col items-center text-center min-w-36 max-w-48">
                      <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider mb-0.5">
                        {node.type || 'Node'} {index + 1}
                      </span>
                      <span className="text-xs font-bold text-[#1F2937] leading-snug">{node.label}</span>
                    </div>

                    {/* Edge Connector */}
                    {outgoingEdge && (
                      <div className="flex flex-col items-center px-1 text-center">
                        <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 mb-1">
                          {outgoingEdge.label}
                        </span>
                        <ArrowRight className="w-5 h-5 text-emerald-600 animate-pulse" />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
            <p className="text-center text-xs text-[#64748B] pt-2">
              Directed causal chain constructed via NetworkX DiGraph builder
            </p>
          </div>
        ) : (
          <div className="w-full">
            <pre className="p-4 bg-[#1F2937] text-emerald-400 font-mono text-xs rounded-xl overflow-x-auto">
              {graphData.mermaidCode}
            </pre>
            <p className="text-xs text-[#64748B] mt-2">
              Valid Mermaid.js graph definition exported directly from python `CausalGraphBuilder`.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
