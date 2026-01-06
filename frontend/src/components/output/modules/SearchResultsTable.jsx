import React, { useState } from 'react';
import { Search, FileText, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * SearchResultsTable - Compact search results with expandable list
 */
const SearchResultsTable = ({ data, onOpenCV }) => {
  const [expanded, setExpanded] = useState(false);
  const INITIAL_SHOW = 5;

  if (!data?.results || data.results.length === 0) return null;

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-gray-400';
  };

  const getScoreBg = (score) => {
    if (score >= 80) return 'bg-emerald-500/20';
    if (score >= 60) return 'bg-amber-500/20';
    return 'bg-gray-500/20';
  };

  const visibleResults = expanded ? data.results : data.results.slice(0, INITIAL_SHOW);
  const hasMore = data.results.length > INITIAL_SHOW;

  return (
    <div className="rounded-xl bg-slate-800/50 p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-cyan-400" />
          <span className="font-medium text-cyan-300 text-sm">Search Results</span>
        </div>
        <span className="text-xs text-gray-400">
          {data.total_candidates} found
        </span>
      </div>

      {/* Query terms */}
      {data.query_terms?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {data.query_terms.map((term, i) => (
            <span key={i} className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-300 rounded text-xs">
              {term}
            </span>
          ))}
        </div>
      )}

      {/* Compact results list */}
      <div className="space-y-1">
        {visibleResults.map((result) => (
          <div 
            key={result.cv_id} 
            className="flex items-center justify-between bg-slate-700/40 rounded-lg px-3 py-2 hover:bg-slate-700/60 transition-colors"
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <button
                onClick={() => onOpenCV?.(result.cv_id)}
                className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors truncate"
              >
                <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="font-medium text-sm truncate">{result.candidate_name}</span>
              </button>
              {result.experience_years > 0 && (
                <span className="text-xs text-gray-500 flex-shrink-0">
                  {result.experience_years}+ yrs
                </span>
              )}
            </div>
            <div className={`px-2 py-0.5 rounded ${getScoreBg(result.match_score)} flex-shrink-0 ml-2`}>
              <span className={`text-sm font-semibold ${getScoreColor(result.match_score)}`}>
                {result.match_score?.toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Show more/less button */}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full mt-2 py-1.5 text-xs text-gray-400 hover:text-gray-300 flex items-center justify-center gap-1 hover:bg-slate-700/30 rounded transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              Show {data.results.length - INITIAL_SHOW} more
            </>
          )}
        </button>
      )}
    </div>
  );
};

export default SearchResultsTable;
