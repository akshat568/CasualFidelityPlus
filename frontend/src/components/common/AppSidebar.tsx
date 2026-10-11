import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitFork,
  BarChart3,
  FlaskConical,
  FileText,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  SlidersHorizontal,
  X,
  Server
} from 'lucide-react';
import { healthCheck } from '../../services/api';
import type { HealthResponse } from '../../types/api';

interface AppSidebarProps {
  apiBaseUrl: string;
  isApiConnected: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'checking';
  onUpdateApiUrl?: (newUrl: string) => void;
  onRefreshConnection?: () => void;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  apiBaseUrl,
  isApiConnected,
  connectionStatus,
  onUpdateApiUrl,
  onRefreshConnection
}) => {
  const [isPopoverOpen, setIsPopoverOpen] = useState<boolean>(false);
  const [editedUrl, setEditedUrl] = useState<string>(apiBaseUrl);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{
    status: 'CONNECTED' | 'FAILED';
    message: string;
    details?: HealthResponse;
  } | null>(null);

  const popoverRef = useRef<HTMLDivElement>(null);

  // Sync editedUrl with prop when prop changes
  useEffect(() => {
    setEditedUrl(apiBaseUrl);
  }, [apiBaseUrl]);

  // Click outside listener to close popover
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsPopoverOpen(false);
      }
    };

    if (isPopoverOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isPopoverOpen]);

  // 5 primary navigation items
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Causal Workbench', path: '/workbench', icon: GitFork },
    { name: 'Research Dashboard', path: '/research', icon: BarChart3 },
    { name: 'Experiment Explorer', path: '/experiments', icon: FlaskConical },
    { name: 'Reports', path: '/reports', icon: FileText }
  ];

  const handleTestConnection = async (urlToTest: string) => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const response = await healthCheck(urlToTest);
      setIsTesting(false);
      setTestResult({
        status: 'CONNECTED',
        message: `Connected to API v${response.version || '1.0.0'} (${response.status})`,
        details: response
      });
    } catch (err: any) {
      setIsTesting(false);
      setTestResult({
        status: 'FAILED',
        message: err.message || 'Connection failed. Verify the server is running.'
      });
    }
  };

  const handleSaveUrl = () => {
    if (onUpdateApiUrl && editedUrl.trim()) {
      onUpdateApiUrl(editedUrl.trim());
      handleTestConnection(editedUrl.trim());
    }
  };

  const handleResetDefault = () => {
    const defaultUrl = 'http://localhost:8000/api/v1';
    setEditedUrl(defaultUrl);
    if (onUpdateApiUrl) {
      onUpdateApiUrl(defaultUrl);
      handleTestConnection(defaultUrl);
    }
  };

  return (
    <aside className="w-64 bg-[#FDFBF7] border-r border-[#E5E7EB] flex flex-col shrink-0 h-screen sticky top-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-[#E5E7EB] flex items-center gap-3 shrink-0">
        <div className="w-10 h-10 rounded-lg bg-emerald-600 flex items-center justify-center text-white shadow-xs">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-bold text-lg text-[#1F2937] tracking-tight flex items-center gap-1.5">
            CausalFidelity<span className="text-emerald-600 font-extrabold">+</span>
          </h1>
          <p className="text-xs text-[#64748B] font-medium">LLM Causal Stress Testing</p>
        </div>
      </div>

      {/* Primary Navigation Items */}
      <nav className="p-3 space-y-1 flex-1 overflow-y-auto min-h-0">
        <div className="px-3 py-2 text-[11px] font-semibold text-[#64748B] uppercase tracking-wider">
          Research Workbench
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-800 font-semibold shadow-xs border-l-4 border-emerald-600'
                    : 'text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1F2937]'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Improved Sidebar Footer: Project Identity & API Status */}
      <div className="p-3.5 border-t border-[#E5E7EB] bg-white/70 shrink-0 space-y-2.5 relative">
        {/* Project Identity */}
        <div className="flex items-center gap-2.5 px-0.5">
          <div className="w-7 h-7 rounded-md bg-emerald-600 flex items-center justify-center text-white shadow-2xs shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-[#1F2937] tracking-tight leading-tight">
              CausalFidelityPlus
            </div>
            <p className="text-[10px] text-[#64748B] leading-tight truncate">
              Research & Evaluation Platform
            </p>
          </div>
        </div>

        {/* Compact API Status Trigger */}
        <button
          type="button"
          onClick={() => {
            setIsPopoverOpen(!isPopoverOpen);
            if (!isPopoverOpen) {
              setEditedUrl(apiBaseUrl);
              setTestResult(null);
            }
          }}
          className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg bg-[#F8FAFC] hover:bg-emerald-50/50 border border-[#E5E7EB] hover:border-emerald-300 text-xs transition-all cursor-pointer group text-left"
          title="Click to view API connection status and configuration"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                connectionStatus === 'connected'
                  ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]'
                  : connectionStatus === 'checking'
                  ? 'bg-sky-500 animate-pulse'
                  : 'bg-amber-500'
              }`}
            />
            <span
              className={`text-[11px] font-medium flex items-center gap-1.5 truncate ${
                connectionStatus === 'connected'
                  ? 'text-emerald-800 font-semibold'
                  : connectionStatus === 'checking'
                  ? 'text-sky-800'
                  : 'text-amber-800'
              }`}
            >
              {connectionStatus === 'connected' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>API Connected</span>
                </>
              ) : connectionStatus === 'checking' ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 text-sky-600 animate-spin shrink-0" />
                  <span>Checking API...</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>API Offline</span>
                </>
              )}
            </span>
          </div>
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#94A3B8] group-hover:text-emerald-700 transition-colors shrink-0" />
        </button>

        {/* API Connection Popover */}
        {isPopoverOpen && (
          <div
            ref={popoverRef}
            className="absolute bottom-full left-2 right-2 mb-2 p-4 bg-white rounded-xl border border-[#E5E7EB] shadow-xl z-50 animate-scale-in text-xs space-y-3"
            style={{ minWidth: '260px' }}
          >
            {/* Popover Header */}
            <div className="flex items-center justify-between pb-2 border-b border-[#E5E7EB]">
              <div className="flex items-center gap-1.5 font-bold text-[#1F2937]">
                <Server className="w-4 h-4 text-emerald-600" />
                <span>Backend Connection</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => {
                    onRefreshConnection?.();
                    handleTestConnection(editedUrl);
                  }}
                  disabled={isTesting}
                  className="p-1 text-slate-400 hover:text-emerald-700 rounded cursor-pointer transition-colors disabled:opacity-50"
                  title="Re-check connection"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
                </button>
                <button
                  type="button"
                  onClick={() => setIsPopoverOpen(false)}
                  className="p-1 text-slate-400 hover:text-slate-700 rounded cursor-pointer"
                  aria-label="Close"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Current Status Pill */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#F8FAFC] border border-[#E5E7EB]">
              <span className="text-[11px] text-[#64748B] font-medium">Status</span>
              <span
                className={`text-[11px] font-bold flex items-center gap-1 ${
                  isApiConnected ? 'text-emerald-700' : 'text-amber-700'
                }`}
              >
                {isApiConnected ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Active & Healthy</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                    <span>Disconnected</span>
                  </>
                )}
              </span>
            </div>

            {/* Endpoint Input */}
            <div className="space-y-1">
              <label htmlFor="api-endpoint-input" className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider block">
                API Base URL
              </label>
              <input
                id="api-endpoint-input"
                type="text"
                value={editedUrl}
                onChange={(e) => setEditedUrl(e.target.value)}
                placeholder="http://localhost:8000/api/v1"
                className="w-full px-2.5 py-1.5 text-xs font-mono bg-white border border-[#CBD5E1] rounded-lg focus:outline-hidden focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 text-[#1F2937]"
              />
            </div>

            {/* Test Result Message */}
            {testResult && (
              <div
                className={`p-2 rounded-lg text-[11px] border ${
                  testResult.status === 'CONNECTED'
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}
              >
                {testResult.message}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between pt-1 gap-2">
              <button
                type="button"
                onClick={() => handleTestConnection(editedUrl)}
                disabled={isTesting}
                className="px-2.5 py-1 text-[11px] font-semibold text-[#475569] bg-slate-100 hover:bg-slate-200 rounded-md transition-colors cursor-pointer flex items-center gap-1 disabled:opacity-50"
              >
                {isTesting ? <RefreshCw className="w-3 h-3 animate-spin" /> : null}
                <span>Test</span>
              </button>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleResetDefault}
                  className="px-2 py-1 text-[11px] font-medium text-[#64748B] hover:text-[#1F2937] hover:underline cursor-pointer"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={handleSaveUrl}
                  className="px-3 py-1 text-[11px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition-colors cursor-pointer shadow-xs"
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
