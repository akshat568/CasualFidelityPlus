import React, { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, Search, Eye, ListTree } from 'lucide-react';

interface JsonTreeViewerProps {
  data: any;
}

interface JsonNodeProps {
  name?: string;
  value: any;
  depth?: number;
  searchTerm?: string;
  isExpandedInitial?: boolean;
}

const JsonNode: React.FC<JsonNodeProps> = ({
  name,
  value,
  depth = 0,
  searchTerm = '',
  isExpandedInitial = true
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(isExpandedInitial || depth < 2);

  const isObject = value !== null && typeof value === 'object' && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const isComplex = isObject || isArray;

  // Filter check
  const matchesSearch = useMemo(() => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    if (name && name.toLowerCase().includes(term)) return true;
    if (!isComplex && String(value).toLowerCase().includes(term)) return true;
    return false;
  }, [name, value, isComplex, searchTerm]);

  const renderValuePrimitive = (val: any) => {
    if (val === null) {
      return <span className="text-slate-400 italic font-mono">null</span>;
    }
    if (typeof val === 'boolean') {
      return <span className="text-purple-600 font-semibold font-mono">{val ? 'true' : 'false'}</span>;
    }
    if (typeof val === 'number') {
      return <span className="text-amber-600 font-bold font-mono">{val}</span>;
    }
    if (typeof val === 'string') {
      return <span className="text-sky-700 font-mono select-text">"{val}"</span>;
    }
    return <span className="text-[#1F2937] font-mono select-text">{String(val)}</span>;
  };

  if (!matchesSearch && depth > 0) {
    // If complex, check if any children match
    if (isComplex) {
      const stringified = JSON.stringify(value).toLowerCase();
      if (!stringified.includes(searchTerm.toLowerCase())) {
        return null;
      }
    } else {
      return null;
    }
  }

  if (!isComplex) {
    return (
      <div className="flex items-start gap-1.5 py-0.5 hover:bg-slate-50/80 px-1 rounded transition-colors text-xs font-mono">
        {name !== undefined && (
          <span className="text-emerald-800 font-semibold shrink-0 select-text">
            {name}:
          </span>
        )}
        <div className="break-all">{renderValuePrimitive(value)}</div>
      </div>
    );
  }

  const entries: [string, any][] = isArray
    ? (value as any[]).map((item: any, idx: number): [string, any] => [String(idx), item])
    : Object.entries(value);

  const countBadge = isArray ? `[${entries.length}]` : `{${entries.length}}`;

  return (
    <div className="text-xs font-mono select-none">
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 py-1 px-1 rounded hover:bg-emerald-50/60 cursor-pointer text-[#1F2937] transition-colors group"
      >
        <span className="p-0.5 rounded text-slate-400 group-hover:text-emerald-700 transition-colors">
          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </span>
        {name !== undefined && (
          <span className="font-bold text-emerald-900 group-hover:text-emerald-700">
            {name}:
          </span>
        )}
        <span className="text-[10px] text-[#64748B] font-medium bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
          {countBadge}
        </span>
        {!isExpanded && (
          <span className="text-[11px] text-[#94A3B8] italic truncate">
            {isArray ? '[ … ]' : '{ … }'}
          </span>
        )}
      </div>

      {isExpanded && (
        <div className="pl-4 ml-2 border-l border-emerald-100/80 space-y-0.5 my-0.5">
          {entries.map(([childKey, childVal]: [string, any]) => (
            <JsonNode
              key={childKey}
              name={childKey}
              value={childVal}
              depth={depth + 1}
              searchTerm={searchTerm}
              isExpandedInitial={isExpandedInitial}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const JsonTreeViewer: React.FC<JsonTreeViewerProps> = ({ data }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'tree' | 'formatted'>('tree');
  const [expandAllKey, setExpandAllKey] = useState<number>(0);

  const parsedData = useMemo(() => {
    if (typeof data === 'string') {
      try {
        return JSON.parse(data);
      } catch (e) {
        return data;
      }
    }
    return data;
  }, [data]);

  const formattedJsonString = useMemo(() => {
    try {
      return JSON.stringify(parsedData, null, 2);
    } catch {
      return String(parsedData);
    }
  }, [parsedData]);

  if (typeof parsedData !== 'object' || parsedData === null) {
    return (
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-700">
        {String(parsedData)}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 p-2.5 bg-[#F8FAFC] rounded-xl border border-[#E5E7EB] text-xs">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Filter keys or values..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-[#E5E7EB] bg-white text-[#1F2937] focus:outline-hidden focus:border-emerald-500 font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          {viewMode === 'tree' && (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setExpandAllKey((prev) => prev + 1)}
                className="px-2.5 py-1 text-[11px] font-semibold text-[#64748B] hover:text-emerald-700 bg-white hover:bg-emerald-50 border border-[#E5E7EB] rounded-lg transition-colors cursor-pointer"
              >
                Reset / Expand
              </button>
            </div>
          )}

          <div className="flex items-center bg-white border border-[#E5E7EB] rounded-lg p-0.5">
            <button
              type="button"
              onClick={() => setViewMode('tree')}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md flex items-center gap-1 transition-colors cursor-pointer ${
                viewMode === 'tree'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'text-[#64748B] hover:text-[#1F2937]'
              }`}
            >
              <ListTree className="w-3 h-3" /> Tree View
            </button>
            <button
              type="button"
              onClick={() => setViewMode('formatted')}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md flex items-center gap-1 transition-colors cursor-pointer ${
                viewMode === 'formatted'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'text-[#64748B] hover:text-[#1F2937]'
              }`}
            >
              <Eye className="w-3 h-3" /> Formatted Text
            </button>
          </div>
        </div>
      </div>

      {/* Content Container */}
      {viewMode === 'tree' ? (
        <div
          key={expandAllKey}
          className="p-4 bg-white rounded-xl border border-[#E5E7EB] max-h-[55vh] overflow-y-auto space-y-1 shadow-2xs select-text"
        >
          <JsonNode value={parsedData} searchTerm={searchTerm} isExpandedInitial={true} />
        </div>
      ) : (
        <div className="p-4 bg-[#F8FAFC] rounded-xl border border-[#E5E7EB] max-h-[55vh] overflow-y-auto shadow-2xs">
          <pre className="text-xs font-mono text-[#1E293B] leading-relaxed select-text whitespace-pre-wrap break-all">
            {formattedJsonString}
          </pre>
        </div>
      )}
    </div>
  );
};
