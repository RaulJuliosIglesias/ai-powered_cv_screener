import React from 'react';

export default function MetricsBar({ metrics, mode }) {
  if (!metrics) return null;
  
  const formatMs = (ms) => {
    if (ms === undefined || ms === null) return '-';
    return `${Math.round(ms)}ms`;
  };
  
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-gray-900 text-gray-300 text-xs font-mono">
      <span className="flex items-center gap-1">
        <span className="text-gray-500">Embed:</span>
        <span className="text-green-400">{formatMs(metrics.embedding_ms)}</span>
      </span>
      
      <span className="text-gray-600">|</span>
      
      <span className="flex items-center gap-1">
        <span className="text-gray-500">Search:</span>
        <span className="text-blue-400">{formatMs(metrics.search_ms)}</span>
      </span>
      
      <span className="text-gray-600">|</span>
      
      <span className="flex items-center gap-1">
        <span className="text-gray-500">LLM:</span>
        <span className="text-purple-400">{formatMs(metrics.llm_ms)}</span>
      </span>
      
      <span className="text-gray-600">|</span>
      
      <span className="flex items-center gap-1">
        <span className="text-gray-500">Total:</span>
        <span className="text-yellow-400 font-bold">{formatMs(metrics.total_ms)}</span>
      </span>
      
      <span className="ml-auto flex items-center gap-1">
        <span className="text-gray-500">Mode:</span>
        <span className={mode === 'local' ? 'text-cyan-400' : 'text-orange-400'}>
          {mode}
        </span>
      </span>
      
      {metrics.prompt_tokens !== undefined && (
        <>
          <span className="text-gray-600">|</span>
          <span className="flex items-center gap-1">
            <span className="text-gray-500">Tokens:</span>
            <span className="text-gray-400">
              {(metrics.prompt_tokens || 0) + (metrics.completion_tokens || 0)}
            </span>
          </span>
        </>
      )}
    </div>
  );
}
