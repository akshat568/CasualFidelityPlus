import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { fetchResearchData, invalidateResearchCache } from '../services/researchService';
import type { ResearchExperiment } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';
import { Search, Filter, ArrowUpDown, ExternalLink, FlaskConical, FileCode, AlertCircle, RefreshCw } from 'lucide-react';

export const ExplorerPage: React.FC = () => {
  const [experiments, setExperiments] = useState<ResearchExperiment[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'id' | 'meanAlignment' | 'runtimeSeconds'>('id');
  const [sortAsc, setSortAsc] = useState<boolean>(true);
  const [selectedExp, setSelectedExp] = useState<ResearchExperiment | null>(null);

  const experimentTypes = ['ALL', 'Baseline', 'Threshold Sensitivity', 'Weight Sensitivity', 'Metric Ablation', 'Human Validation'];

  const loadData = useCallback(async (forceRefresh = false) => {
    setIsLoading(true);
    setError(null);
    try {
      if (forceRefresh) {
        invalidateResearchCache();
      }
      const data = await fetchResearchData(forceRefresh);
      setExperiments(data.experiments);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve experiment runs from backend artifact.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredExperiments = useMemo(() => {
    return experiments.filter((exp) => {
      const matchesSearch =
        exp.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exp.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = selectedType === 'ALL' || exp.type === selectedType;
      return matchesSearch && matchesType;
    }).sort((a, b) => {
      let valA: any = a[sortField];
      let valB: any = b[sortField];
      if (valA === undefined) valA = sortAsc ? Infinity : -Infinity;
      if (valB === undefined) valB = sortAsc ? Infinity : -Infinity;

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [experiments, searchTerm, selectedType, sortField, sortAsc]);

  const toggleSort = (field: 'id' | 'meanAlignment' | 'runtimeSeconds') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white p-5 rounded-xl border border-[#E5E7EB] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#1F2937]">Experiment Explorer</h2>
          <p className="text-xs text-[#64748B]">
            Filter, search, and inspect completed ablation study runs and configurations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono">
            {isLoading ? 'Loading runs…' : `Showing ${filteredExperiments.length} of ${experiments.length} runs`}
          </span>
          <button
            onClick={() => loadData(true)}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#F8FAFC] text-[#1F2937] border border-[#E5E7EB] hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 transition-colors inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Refresh experiments from backend"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error State Banner with Retry */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-900 flex items-start justify-between gap-3 shadow-xs">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-sm block mb-0.5">Experiments Unavailable</span>
              <p className="text-rose-800 leading-relaxed">{error}</p>
              <p className="text-[11px] text-rose-700 mt-1">
                Please verify that the FastAPI backend server is running and accessible.
              </p>
            </div>
          </div>
          <button
            onClick={() => loadData(true)}
            className="px-3 py-1.5 text-xs font-bold rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition-colors shrink-0 cursor-pointer shadow-xs"
          >
            Retry Request
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-[#E5E7EB] shadow-xs flex flex-wrap items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by ID (e.g. EXP_04) or keyword..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#E5E7EB] bg-[#FDFBF7] text-[#1F2937] focus:bg-white focus:outline-hidden focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-mono"
          />
        </div>

        {/* Type Filter Dropdown */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-[#64748B]" />
          <span className="text-xs font-semibold text-[#64748B]">Filter Type:</span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="p-2 text-xs font-medium rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] text-[#1F2937] focus:border-emerald-500 focus:outline-hidden cursor-pointer"
          >
            {experimentTypes.map((t) => (
              <option key={t} value={t}>
                {t === 'ALL' ? 'All Experiment Types' : t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Experiment Data Table */}
      <div className="bg-white rounded-xl border border-[#E5E7EB] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E5E7EB] font-semibold uppercase text-[10px] tracking-wider select-none">
                <th className="p-3 cursor-pointer hover:text-emerald-700" onClick={() => toggleSort('id')}>
                  <div className="flex items-center gap-1">
                    Experiment ID <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3">Experiment Name & Type</th>
                <th className="p-3">Status</th>
                <th className="p-3">Available Metrics</th>
                <th className="p-3 cursor-pointer hover:text-emerald-700" onClick={() => toggleSort('meanAlignment')}>
                  <div className="flex items-center gap-1">
                    Mean Alignment <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3 cursor-pointer hover:text-emerald-700" onClick={() => toggleSort('runtimeSeconds')}>
                  <div className="flex items-center gap-1">
                    Runtime (s) <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E7EB]">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[#64748B]">
                    Loading genuine experiment runs from backend matrix artifact…
                  </td>
                </tr>
              ) : filteredExperiments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[#64748B]">
                    No experiments matched your search criteria.
                  </td>
                </tr>
              ) : (
                filteredExperiments.map((exp) => (
                  <tr key={exp.id} className="hover:bg-emerald-50/40 transition-colors">
                    <td className="p-3 font-mono font-bold text-emerald-700">{exp.id}</td>
                    <td className="p-3">
                      <div className="font-semibold text-[#1F2937]">{exp.name}</div>
                      <div className="text-[11px] text-[#64748B]">{exp.type}</div>
                    </td>
                    <td className="p-3">
                      <StatusBadge status={exp.status} size="sm" />
                    </td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1">
                        {exp.availableMetrics.map((m) => (
                          <span key={m} className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-mono">
                            {m}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="p-3 font-mono font-semibold text-[#1F2937]">
                      {exp.meanAlignment !== undefined ? exp.meanAlignment.toFixed(4) : 'N/A'}
                    </td>
                    <td className="p-3 font-mono text-[#64748B]">
                      {exp.runtimeSeconds !== undefined ? `${exp.runtimeSeconds.toFixed(1)}s` : '—'}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => setSelectedExp(exp)}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors inline-flex items-center gap-1 cursor-pointer"
                      >
                        Inspect <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Experiment Detail Modal */}
      <Modal
        isOpen={selectedExp !== null}
        onClose={() => setSelectedExp(null)}
        title={selectedExp ? `Inspect ${selectedExp.id}` : 'Experiment Configuration'}
      >
        {selectedExp && (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB]">
              <div>
                <h4 className="font-bold text-[#1F2937] text-sm">{selectedExp.name}</h4>
                <p className="text-xs text-[#64748B]">{selectedExp.type}</p>
              </div>
              <StatusBadge status={selectedExp.status} />
            </div>

            <div>
              <h5 className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-1">Configuration Overview</h5>
              <p className="text-xs text-[#1F2937] bg-[#FDFBF7] p-3 rounded-lg border border-[#E5E7EB] leading-relaxed">
                {selectedExp.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB]">
                <span className="text-[#64748B] block">Mean Alignment Result</span>
                <span className="font-bold font-mono text-emerald-700 text-sm">
                  {selectedExp.meanAlignment !== undefined ? selectedExp.meanAlignment.toFixed(4) : 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB]">
                <span className="text-[#64748B] block">Total Runtime</span>
                <span className="font-bold font-mono text-slate-800 text-sm">
                  {selectedExp.runtimeSeconds !== undefined ? `${selectedExp.runtimeSeconds.toFixed(1)}s` : 'N/A'}
                </span>
              </div>
            </div>

            <div>
              <h5 className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-1.5">Experiment Artifacts</h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB] space-y-1.5">
                  <div className="flex items-center gap-2 text-[#1F2937] font-semibold">
                    <FileCode className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>Configuration Spec</span>
                  </div>
                  <div className="text-[11px] text-[#64748B] space-y-0.5">
                    <div>
                      Category: <span className="font-semibold text-[#1F2937]">{selectedExp.type}</span>
                    </div>
                    <div>
                      Identifier: <span className="font-mono text-emerald-800 bg-emerald-50 px-1 py-0.5 rounded text-[10px]">{selectedExp.id}</span>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-[#F8FAFC] rounded-lg border border-[#E5E7EB] space-y-1.5">
                  <div className="flex items-center gap-2 text-[#1F2937] font-semibold">
                    <FlaskConical className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>Results Summary</span>
                  </div>
                  <div className="text-[11px] text-[#64748B] space-y-1">
                    <div>
                      Active Metrics ({selectedExp.availableMetrics.length}):
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {selectedExp.availableMetrics.map((m) => (
                        <span key={m} className="px-1.5 py-0.5 rounded bg-white text-slate-700 border border-[#E5E7EB] text-[10px] font-mono">
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {selectedExp.notes && (
              <div>
                <h5 className="text-xs font-bold text-[#64748B] uppercase tracking-wider mb-1">Empirical Notes</h5>
                <p className="text-xs text-emerald-900 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                  {selectedExp.notes}
                </p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

