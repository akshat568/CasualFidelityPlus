import React from 'react';
import { useLocation } from 'react-router-dom';
import { Search, User, ChevronRight } from 'lucide-react';

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  '/': {
    title: 'Research Overview',
    subtitle: 'Explore causal fidelity, controlled perturbations, and research findings.'
  },
  '/workbench': {
    title: 'Causal Workbench',
    subtitle: 'Analyze causal relationships and test controlled causal distortions.'
  },
  '/research': {
    title: 'Research Dashboard',
    subtitle: 'Explore the results of controlled causal-distortion experiments.'
  },
  '/experiments': {
    title: 'Experiment Explorer',
    subtitle: 'Search, filter, and inspect completed ablation study runs.'
  },
  '/reports': {
    title: 'Research Reports',
    subtitle: 'Inspect research manifests, summaries, and Markdown deliverables.'
  }
};

interface AppHeaderProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({ searchQuery = '', onSearchChange }) => {
  const location = useLocation();
  const currentRouteInfo = routeTitles[location.pathname] || {
    title: 'Research Workspace',
    subtitle: 'CausalFidelityPlus Analysis Platform'
  };

  return (
    <header className="bg-white border-b border-[#E5E7EB] px-6 py-4 sticky top-0 z-10 flex items-center justify-between shadow-2xs">
      {/* Breadcrumbs & Title */}
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-[#64748B] mb-1 font-medium">
          <span>CausalFidelityPlus</span>
          <ChevronRight className="w-3.5 h-3.5 text-[#94A3B8]" />
          <span className="text-emerald-700 font-semibold">{currentRouteInfo.title}</span>
        </nav>
        <h1 className="text-xl font-bold text-[#1F2937] tracking-tight">{currentRouteInfo.title}</h1>
      </div>

      {/* Right Controls: Search & User Profile */}
      <div className="flex items-center gap-4">
        {/* Search Field */}
        <div className="relative w-64 hidden sm:block">
          <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search experiments, metrics..."
            value={searchQuery}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] focus:bg-white focus:outline-hidden focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all text-[#1F2937]"
          />
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-3 border-l border-[#E5E7EB]">
          <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs border border-emerald-300">
            <User className="w-4 h-4 text-emerald-700" />
          </div>
          <div className="hidden lg:block text-left">
            <p className="text-xs font-semibold text-[#1F2937]">Research Workspace</p>
            <p className="text-[10px] text-[#64748B]">CausalFidelityPlus</p>
          </div>
        </div>
      </div>
    </header>
  );
};
