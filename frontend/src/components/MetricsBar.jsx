import React from 'react';
import { Cpu, Search, Sparkles, Clock, Gauge } from 'lucide-react';

export default function MetricsBar({ metrics, mode }) {
  if (!metrics) return null;
  
  const formatMs = (ms) => {
    if (ms === undefined || ms === null) return '-';
    return `${Math.round(ms)}ms`;
  };

  const getPerformanceColor = (ms) => {
    if (ms < 100) return 'text-green-500';
    if (ms < 500) return 'text-yellow-500';
    return 'text-orange-500';
  };
  
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-gray-900 dark:bg-gray-950 text-xs font-mono overflow-x-auto">
      <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-800 rounded">
        <Cpu className="w-3 h-3 text-green-400" />
        <span className="text-gray-500">Embed:</span>
        <span className={getPerformanceColor(metrics.embedding_ms)}>{formatMs(metrics.embedding_ms)}</span>
      </div>
      
      <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-800 rounded">
        <Search className="w-3 h-3 text-blue-400" />
        <span className="text-gray-500">Search:</span>
        <span className={getPerformanceColor(metrics.search_ms)}>{formatMs(metrics.search_ms)}</span>
      </div>
      
      <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-800 rounded">
        <Sparkles className="w-3 h-3 text-purple-400" />
        <span className="text-gray-500">LLM:</span>
        <span className={getPerformanceColor(metrics.llm_ms)}>{formatMs(metrics.llm_ms)}</span>
      </div>
      
      <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-900/50 rounded border border-blue-800">
        <Clock className="w-3 h-3 text-yellow-400" />
        <span className="text-gray-400">Total:</span>
        <span className="text-yellow-400 font-bold">{formatMs(metrics.total_ms)}</span>
      </div>
      
      <div className="ml-auto flex items-center gap-1.5 px-2 py-1 bg-gray-800 rounded">
        <Gauge className="w-3 h-3" />
        <span className="text-gray-500">Modo:</span>
        <span className={`font-medium ${mode === 'local' ? 'text-cyan-400' : 'text-orange-400'}`}>
          {mode === 'local' ? 'Local' : 'Cloud'}
        </span>
      </div>
    </div>
  );
}
