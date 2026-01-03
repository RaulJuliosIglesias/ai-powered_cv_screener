import { useState, useEffect } from 'react';
import { BarChart3, X, Clock, Zap, Search, Brain, Shield, AlertTriangle, DollarSign, Trash2, ChevronDown, ChevronUp, Database, Cloud } from 'lucide-react';

const STORAGE_KEY = 'cv-screener-metrics-history';
const MAX_HISTORY = 50;

// Estimated costs per 1M tokens (approximate OpenRouter pricing)
const COST_ESTIMATES = {
  'embed': 0.02,      // per 1M tokens
  'llm_input': 0.15,  // per 1M tokens (avg)
  'llm_output': 0.60, // per 1M tokens (avg)
};

export function getMetricsHistory() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

export function saveMetricEntry(entry) {
  try {
    const history = getMetricsHistory();
    history.unshift({
      ...entry,
      id: Date.now(),
      timestamp: new Date().toISOString(),
    });
    // Keep only last MAX_HISTORY entries
    const trimmed = history.slice(0, MAX_HISTORY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    return trimmed;
  } catch (e) {
    console.error('Failed to save metrics:', e);
    return [];
  }
}

export function clearMetricsHistory() {
  localStorage.removeItem(STORAGE_KEY);
}

function formatMs(ms) {
  if (ms === undefined || ms === null) return '-';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatCost(tokens, type = 'llm_input') {
  if (!tokens) return '-';
  const costPer1M = COST_ESTIMATES[type] || 0.15;
  const cost = (tokens / 1000000) * costPer1M;
  if (cost < 0.0001) return '<$0.0001';
  return `$${cost.toFixed(4)}`;
}

function MetricRow({ icon: Icon, label, value, subValue, color = 'text-gray-400' }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-700/50 last:border-0">
      <div className="flex items-center gap-2">
        <Icon size={14} className={color} />
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <div className="text-right">
        <span className="text-xs font-mono text-white">{value}</span>
        {subValue && <span className="text-[10px] text-gray-500 ml-1">{subValue}</span>}
      </div>
    </div>
  );
}

function QueryEntry({ entry, isExpanded, onToggle }) {
  const metrics = entry.metrics || {};
  const confidence = entry.confidence_score;
  const guardrail = entry.guardrail_passed;
  
  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const truncateQuery = (q, max = 40) => {
    if (!q || q.length <= max) return q;
    return q.substring(0, max) + '...';
  };

  return (
    <div className="bg-gray-800/50 rounded-lg mb-2 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {entry.mode === 'cloud' ? (
            <Cloud size={12} className="text-blue-400 flex-shrink-0" />
          ) : (
            <Database size={12} className="text-green-400 flex-shrink-0" />
          )}
          <span className="text-xs text-gray-300 truncate">{truncateQuery(entry.query)}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <span className="text-[10px] text-gray-500">{formatMs(metrics.total_ms || metrics.llm_ms)}</span>
          {confidence !== undefined && (
            <span className={`text-[10px] font-mono ${getConfidenceColor(confidence)}`}>
              {Math.round(confidence * 100)}%
            </span>
          )}
          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </button>
      
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-700/50">
          <div className="grid grid-cols-2 gap-x-4">
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Latencies</div>
              <MetricRow icon={Zap} label="Embed" value={formatMs(metrics.embed_ms)} color="text-purple-400" />
              <MetricRow icon={Search} label="Search" value={formatMs(metrics.search_ms)} color="text-blue-400" />
              <MetricRow icon={Brain} label="LLM" value={formatMs(metrics.llm_ms)} color="text-amber-400" />
              <MetricRow icon={Clock} label="Total" value={formatMs(metrics.total_ms)} color="text-white" />
            </div>
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Quality</div>
              <MetricRow 
                icon={Shield} 
                label="Guardrail" 
                value={guardrail === undefined ? '-' : guardrail ? '✓ Pass' : '✗ Blocked'} 
                color={guardrail ? 'text-green-400' : 'text-red-400'} 
              />
              <MetricRow 
                icon={AlertTriangle} 
                label="Confidence" 
                value={confidence !== undefined ? `${Math.round(confidence * 100)}%` : '-'} 
                color={getConfidenceColor(confidence)} 
              />
              <MetricRow 
                icon={DollarSign} 
                label="Est. Cost" 
                value={formatCost(metrics.tokens_used || 500)} 
                color="text-emerald-400" 
              />
            </div>
          </div>
          
          {entry.query_understanding && (
            <div className="mt-2 pt-2 border-t border-gray-700/50">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Query Understanding</div>
              <div className="text-xs text-gray-300 bg-gray-900/50 rounded p-2">
                <div className="flex gap-2 mb-1">
                  <span className="text-gray-500">Type:</span>
                  <span className="text-cyan-400">{entry.query_understanding.query_type || 'general'}</span>
                </div>
                {entry.query_understanding.understood_query && (
                  <div className="flex gap-2">
                    <span className="text-gray-500">Understood:</span>
                    <span className="text-gray-300 truncate">{entry.query_understanding.understood_query}</span>
                  </div>
                )}
              </div>
            </div>
          )}
          
          <div className="mt-2 text-[10px] text-gray-600">
            {new Date(entry.timestamp).toLocaleString()} • {entry.mode}
          </div>
        </div>
      )}
    </div>
  );
}

export default function MetricsPanel({ isOpen, onClose }) {
  const [history, setHistory] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setHistory(getMetricsHistory());
    }
  }, [isOpen]);

  // Listen for new metrics
  useEffect(() => {
    const handleMetricsUpdate = () => {
      setHistory(getMetricsHistory());
    };
    window.addEventListener('metrics-updated', handleMetricsUpdate);
    return () => window.removeEventListener('metrics-updated', handleMetricsUpdate);
  }, []);

  const handleClear = () => {
    clearMetricsHistory();
    setHistory([]);
    setShowClearConfirm(false);
  };

  // Calculate aggregates
  const aggregates = history.length > 0 ? {
    totalQueries: history.length,
    avgLatency: Math.round(history.reduce((sum, h) => sum + (h.metrics?.total_ms || h.metrics?.llm_ms || 0), 0) / history.length),
    avgConfidence: (history.filter(h => h.confidence_score !== undefined).reduce((sum, h) => sum + h.confidence_score, 0) / history.filter(h => h.confidence_score !== undefined).length * 100).toFixed(0),
    guardrailBlocked: history.filter(h => h.guardrail_passed === false).length,
    localQueries: history.filter(h => h.mode === 'local').length,
    cloudQueries: history.filter(h => h.mode === 'cloud').length,
  } : null;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-cyan-400" />
            <span className="font-medium text-white">RAG Pipeline Metrics</span>
            <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
              {history.length} queries
            </span>
          </div>
          <div className="flex items-center gap-2">
            {history.length > 0 && (
              showClearConfirm ? (
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleClear}
                    className="text-xs text-red-400 hover:text-red-300 px-2 py-1"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setShowClearConfirm(false)}
                    className="text-xs text-gray-400 hover:text-gray-300 px-2 py-1"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowClearConfirm(true)}
                  className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded transition-colors"
                  title="Clear history"
                >
                  <Trash2 size={14} />
                </button>
              )
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Aggregates Summary */}
        {aggregates && (
          <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/30">
            <div className="grid grid-cols-4 gap-3 text-center">
              <div>
                <div className="text-lg font-bold text-white">{aggregates.totalQueries}</div>
                <div className="text-[10px] text-gray-500 uppercase">Queries</div>
              </div>
              <div>
                <div className="text-lg font-bold text-amber-400">{formatMs(aggregates.avgLatency)}</div>
                <div className="text-[10px] text-gray-500 uppercase">Avg Time</div>
              </div>
              <div>
                <div className="text-lg font-bold text-green-400">{aggregates.avgConfidence || '-'}%</div>
                <div className="text-[10px] text-gray-500 uppercase">Avg Conf.</div>
              </div>
              <div>
                <div className="text-lg font-bold text-red-400">{aggregates.guardrailBlocked}</div>
                <div className="text-[10px] text-gray-500 uppercase">Blocked</div>
              </div>
            </div>
            <div className="flex justify-center gap-4 mt-2 text-[10px]">
              <span className="flex items-center gap-1">
                <Database size={10} className="text-green-400" />
                <span className="text-gray-400">{aggregates.localQueries} local</span>
              </span>
              <span className="flex items-center gap-1">
                <Cloud size={10} className="text-blue-400" />
                <span className="text-gray-400">{aggregates.cloudQueries} cloud</span>
              </span>
            </div>
          </div>
        )}

        {/* Query History */}
        <div className="flex-1 overflow-y-auto p-4">
          {history.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <BarChart3 size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">No queries yet</p>
              <p className="text-xs mt-1">Metrics will appear here after you send messages</p>
            </div>
          ) : (
            history.map((entry) => (
              <QueryEntry
                key={entry.id}
                entry={entry}
                isExpanded={expandedId === entry.id}
                onToggle={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
              />
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-700 text-center">
          <span className="text-[10px] text-gray-600">
            Metrics stored locally • Last {MAX_HISTORY} queries
          </span>
        </div>
      </div>
    </div>
  );
}
