import { useState, useEffect, useRef } from 'react';
import { BarChart3, X, Clock, Zap, Search, Brain, Shield, AlertTriangle, DollarSign, Trash2, ChevronDown, ChevronUp, Database, Cloud, Shuffle, ShieldCheck, MessageSquare, CheckCircle, XCircle, Activity, Calendar } from 'lucide-react';
import { calculateOpenRouterCost, formatCost } from '../utils/openRouterPricing';

const STORAGE_KEY = 'cv-screener-metrics-history';
const MAX_HISTORY = 50;

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
  const stages = metrics.stages || {};
  const confidence = entry.confidence_score;
  const guardrail = entry.guardrail_passed;
  const timestamp = entry.timestamp;
  const mode = entry.mode;
  
  // Extract latencies from stages (original backend structure)
  const latencies = {
    understand_ms: stages.query_understanding?.duration_ms,
    search_ms: stages.search?.duration_ms,
    rerank_ms: stages.reranking?.duration_ms,
    llm_ms: (stages.reasoning?.duration_ms || 0) + (stages.generation?.duration_ms || 0) || undefined,
    verify_ms: stages.claim_verification?.duration_ms,
    total_ms: metrics.total_ms
  };
  
  // Determine which features were used based on stages presence
  const featuresEnabled = {
    query_understanding: !!stages.query_understanding,
    reranking: !!stages.reranking,
    reasoning: !!stages.reasoning,
    claim_verification: !!stages.claim_verification
  };
  
  // Extract tokens from generation stage metadata (REAL data from backend)
  const promptTokens = stages.generation?.metadata?.prompt_tokens || 0;
  const completionTokens = stages.generation?.metadata?.completion_tokens || 0;
  
  // Build cost breakdown by RAG component
  const costBreakdown = [
    {
      name: "Understanding",
      active: !!stages.query_understanding,
      cost: stages.query_understanding?.metadata?.openrouter_cost || 0,
      tokens: stages.query_understanding?.metadata?.total_tokens || 0
    },
    {
      name: "Reasoning",
      active: !!stages.reasoning,
      cost: stages.reasoning?.metadata?.openrouter_cost || 0,
      tokens: stages.reasoning?.metadata?.total_tokens || 0
    },
    {
      name: "Generation",
      active: !!stages.generation,
      cost: stages.generation?.metadata?.openrouter_cost || 0,
      tokens: stages.generation?.metadata?.total_tokens || 0
    },
    {
      name: "Verification",
      active: !!stages.claim_verification,
      cost: stages.claim_verification?.metadata?.openrouter_cost || 0,
      tokens: stages.claim_verification?.metadata?.total_tokens || 0
    }
  ];
  
  // Calculate totals from REAL costs
  const totalCost = costBreakdown.reduce((sum, item) => sum + (item.active ? item.cost : 0), 0);
  const totalTokens = costBreakdown.reduce((sum, item) => sum + (item.active ? item.tokens : 0), 0);
  const hasRealCost = costBreakdown.some(item => item.active && item.cost > 0);
  
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
          {mode === 'cloud' ? (
            <Cloud size={12} className="text-blue-400 flex-shrink-0" />
          ) : (
            <Database size={12} className="text-green-400 flex-shrink-0" />
          )}
          <span className="text-xs text-gray-300 truncate">{truncateQuery(entry.query)}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <span className="text-[10px] text-gray-500">{formatMs(metrics.total_ms)}</span>
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
          {/* TIMESTAMP */}
          <div className="mb-3 pb-2 border-b border-gray-700/30">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Calendar size={14} className="text-cyan-400" />
              <span className="font-semibold">{timestamp ? new Date(timestamp).toLocaleString('es-ES', { 
                dateStyle: 'short', 
                timeStyle: 'medium' 
              }) : 'Unknown time'}</span>
              <span className="text-gray-600">•</span>
              <span className="uppercase text-[10px]">{mode || 'unknown'} mode</span>
            </div>
          </div>
          
          {/* TABLES SIDE BY SIDE */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            {/* LATENCIES TABLE */}
            <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">⏱️ Latency Breakdown</div>
            <div className="bg-gray-900/50 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-800/50">
                    <th className="text-left px-2 py-1.5 text-gray-400 font-medium">Stage</th>
                    <th className="text-right px-2 py-1.5 text-gray-400 font-medium">Time</th>
                    <th className="text-center px-2 py-1.5 text-gray-400 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-gray-700/30">
                    <td className="px-2 py-1.5 text-gray-300">🧠 Understand</td>
                    <td className="px-2 py-1.5 text-right font-mono text-amber-400">{formatMs(latencies.understand_ms)}</td>
                    <td className="px-2 py-1.5 text-center">{latencies.understand_ms ? <CheckCircle size={12} className="inline text-green-400" /> : <span className="text-gray-600">-</span>}</td>
                  </tr>
                  <tr className="border-t border-gray-700/30">
                    <td className="px-2 py-1.5 text-gray-300">🔍 Search</td>
                    <td className="px-2 py-1.5 text-right font-mono text-blue-400">{formatMs(latencies.search_ms)}</td>
                    <td className="px-2 py-1.5 text-center">{latencies.search_ms ? <CheckCircle size={12} className="inline text-green-400" /> : <span className="text-gray-600">-</span>}</td>
                  </tr>
                  <tr className="border-t border-gray-700/30">
                    <td className="px-2 py-1.5 text-gray-300">🔄 Rerank</td>
                    <td className="px-2 py-1.5 text-right font-mono text-purple-400">{featuresEnabled.reranking === false ? <span className="text-gray-600">OFF</span> : formatMs(latencies.rerank_ms)}</td>
                    <td className="px-2 py-1.5 text-center">{featuresEnabled.reranking === false ? <XCircle size={12} className="inline text-gray-600" /> : latencies.rerank_ms ? <CheckCircle size={12} className="inline text-green-400" /> : <span className="text-gray-600">-</span>}</td>
                  </tr>
                  <tr className="border-t border-gray-700/30">
                    <td className="px-2 py-1.5 text-gray-300">💬 LLM</td>
                    <td className="px-2 py-1.5 text-right font-mono text-cyan-400">{formatMs(latencies.llm_ms)}</td>
                    <td className="px-2 py-1.5 text-center">{latencies.llm_ms ? <CheckCircle size={12} className="inline text-green-400" /> : <span className="text-gray-600">-</span>}</td>
                  </tr>
                  <tr className="border-t border-gray-700/30">
                    <td className="px-2 py-1.5 text-gray-300">✅ Verify</td>
                    <td className="px-2 py-1.5 text-right font-mono text-green-400">{featuresEnabled.claim_verification === false ? <span className="text-gray-600">OFF</span> : formatMs(latencies.verify_ms)}</td>
                    <td className="px-2 py-1.5 text-center">{featuresEnabled.claim_verification === false ? <XCircle size={12} className="inline text-gray-600" /> : latencies.verify_ms ? <CheckCircle size={12} className="inline text-green-400" /> : <span className="text-gray-600">-</span>}</td>
                  </tr>
                  <tr className="border-t-2 border-gray-600 bg-gray-800/30">
                    <td className="px-2 py-1.5 text-white font-semibold">⚡ Total</td>
                    <td className="px-2 py-1.5 text-right font-mono text-white font-bold">{formatMs(metrics.total_ms)}</td>
                    <td className="px-2 py-1.5 text-center"><CheckCircle size={12} className="inline text-green-400" /></td>
                  </tr>
                </tbody>
              </table>
            </div>
            </div>
            
            {/* COST BY COMPONENT TABLE */}
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">💰 Cost Breakdown</div>
              <div className="bg-gray-900/50 rounded-lg overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-800/50">
                      <th className="text-left px-2 py-1.5 text-gray-400 font-medium">Component</th>
                      <th className="text-center px-2 py-1.5 text-gray-400 font-medium">Status</th>
                      <th className="text-right px-2 py-1.5 text-gray-400 font-medium">Tokens</th>
                      <th className="text-right px-2 py-1.5 text-gray-400 font-medium">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {costBreakdown.map(item => (
                      <tr key={item.name} className="border-t border-gray-700/30">
                        <td className="px-2 py-1.5 text-gray-300">{item.name}</td>
                        <td className="px-2 py-1.5 text-center">
                          {item.active ? <CheckCircle size={10} className="inline text-green-400" /> : <span className="text-gray-600 text-[10px]">OFF</span>}
                        </td>
                        <td className="px-2 py-1.5 text-right font-mono text-cyan-400">
                          {item.active ? item.tokens.toLocaleString() : '-'}
                        </td>
                        <td className="px-2 py-1.5 text-right font-mono text-emerald-400">
                          {item.active ? formatCost(item.cost) : '-'}
                        </td>
                      </tr>
                    ))}
                    <tr className="border-t-2 border-gray-600 bg-gray-800/30">
                      <td className="px-2 py-1.5 text-white font-semibold">💵 Total</td>
                      <td className="px-2 py-1.5 text-center"></td>
                      <td className="px-2 py-1.5 text-right font-mono text-white font-bold">{totalTokens.toLocaleString()}</td>
                      <td className="px-2 py-1.5 text-right font-mono text-white font-bold">{formatCost(totalCost)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="mt-1 text-[10px] text-gray-500 italic">
                {hasRealCost ? '✓ Real cost from OpenRouter API' : '⚠ Cost data unavailable'}
              </div>
            </div>
          </div>
          
          {/* QUALITY METRICS & RAG COMPONENTS SIDE BY SIDE */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            {/* QUALITY METRICS */}
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">📊 Quality Metrics</div>
              <div className="bg-gray-900/50 rounded-lg p-2.5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield size={14} className={guardrail ? 'text-green-400' : 'text-red-400'} />
                    <span className="text-xs text-gray-400">Guardrail</span>
                  </div>
                  <span className={`text-xs font-medium ${guardrail ? 'text-green-400' : 'text-red-400'}`}>
                    {guardrail === undefined ? '-' : guardrail ? '✓ Pass' : '✗ Block'}
                  </span>
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle size={14} className={getConfidenceColor(confidence)} />
                      <span className="text-xs text-gray-400">Confidence</span>
                    </div>
                    <span className={`text-xs font-mono font-bold ${getConfidenceColor(confidence)}`}>
                      {confidence !== undefined ? `${Math.round(confidence * 100)}%` : '-'}
                    </span>
                  </div>
                  {entry.confidence_explanation && (
                    <div className="mt-1.5 p-1.5 bg-gray-800/50 rounded text-[10px]">
                      <div className="text-gray-400 mb-0.5">Based on:</div>
                      <div className="text-gray-300">
                        • {entry.confidence_explanation.source === 'claim_verification' ? 'Claim Verification' : entry.confidence_explanation.source}
                        {entry.confidence_explanation.details?.verified_claims !== undefined && (
                          <>
                            <br />• {entry.confidence_explanation.details.verified_claims}/{entry.confidence_explanation.details.total_claims} claims verified
                          </>
                        )}
                        {entry.confidence_explanation.note && (
                          <>
                            <br /><span className="text-gray-500 italic">{entry.confidence_explanation.note}</span>
                          </>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* RAG COMPONENTS (VERTICAL) */}
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">🔧 RAG Components</div>
              <div className="bg-gray-900/50 rounded-lg p-2.5">
                <div className="space-y-1.5 text-xs">
                  {featuresEnabled.query_understanding !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className={featuresEnabled.query_understanding ? 'text-gray-300' : 'text-gray-600'}>Understanding</span>
                      {featuresEnabled.query_understanding ? <CheckCircle size={12} className="text-green-400" /> : <XCircle size={12} className="text-gray-600" />}
                    </div>
                  )}
                  {featuresEnabled.reranking !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className={featuresEnabled.reranking ? 'text-gray-300' : 'text-gray-600'}>Reranking</span>
                      {featuresEnabled.reranking ? <CheckCircle size={12} className="text-green-400" /> : <XCircle size={12} className="text-gray-600" />}
                    </div>
                  )}
                  {featuresEnabled.reasoning !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className={featuresEnabled.reasoning ? 'text-gray-300' : 'text-gray-600'}>Reasoning</span>
                      {featuresEnabled.reasoning ? <CheckCircle size={12} className="text-green-400" /> : <XCircle size={12} className="text-gray-600" />}
                    </div>
                  )}
                  {featuresEnabled.claim_verification !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className={featuresEnabled.claim_verification ? 'text-gray-300' : 'text-gray-600'}>Verification</span>
                      {featuresEnabled.claim_verification ? <CheckCircle size={12} className="text-green-400" /> : <XCircle size={12} className="text-gray-600" />}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
          
        </div>
      )}
    </div>
  );
}

export default function MetricsPanel({ isOpen, onClose, sessionId = null, sessionName = null }) {
  const [history, setHistory] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showAllSessions, setShowAllSessions] = useState(false);
  const panelRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      const allHistory = getMetricsHistory();
      // Filter by session if sessionId provided and not showing all
      if (sessionId && !showAllSessions) {
        setHistory(allHistory.filter(h => h.session_id === sessionId));
      } else {
        setHistory(allHistory);
      }
    }
  }, [isOpen, sessionId, showAllSessions]);

  // Click outside to close
  useEffect(() => {
    if (!isOpen) return;
    
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        onClose();
      }
    };
    
    // Add a small delay to avoid immediate close on open
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);
    
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  // Listen for new metrics
  useEffect(() => {
    const handleMetricsUpdate = () => {
      const allHistory = getMetricsHistory();
      if (sessionId && !showAllSessions) {
        setHistory(allHistory.filter(h => h.session_id === sessionId));
      } else {
        setHistory(allHistory);
      }
    };
    window.addEventListener('metrics-updated', handleMetricsUpdate);
    return () => window.removeEventListener('metrics-updated', handleMetricsUpdate);
  }, [sessionId, showAllSessions]);

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
      <div ref={panelRef} className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-cyan-400" />
            <span className="font-medium text-white">RAG Metrics</span>
            {sessionId && (
              <span className="text-xs text-cyan-400 bg-cyan-900/30 px-2 py-0.5 rounded-full truncate max-w-[120px]" title={sessionName}>
                {sessionName || 'This chat'}
              </span>
            )}
            <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
              {history.length} queries
            </span>
          </div>
          <div className="flex items-center gap-2">
            {sessionId && (
              <button
                onClick={() => setShowAllSessions(!showAllSessions)}
                className={`text-[10px] px-2 py-1 rounded transition-colors ${
                  showAllSessions 
                    ? 'bg-cyan-600 text-white' 
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                {showAllSessions ? 'All sessions' : 'This chat only'}
              </button>
            )}
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
