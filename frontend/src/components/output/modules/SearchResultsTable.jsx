import React from 'react';
import { Search, FileText, CheckCircle } from 'lucide-react';

/**
 * SearchResultsTable - Displays search results with match scores
 */
const SearchResultsTable = ({ data, onOpenCV }) => {
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

  return (
    <div className="rounded-xl bg-slate-800/50 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Search className="w-5 h-5 text-cyan-400" />
          <span className="font-semibold text-cyan-300">Search Results</span>
        </div>
        <span className="text-sm text-gray-400">
          {data.total_candidates} candidates found
        </span>
      </div>

      {data.query_terms?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {data.query_terms.map((term, i) => (
            <span key={i} className="px-2 py-0.5 bg-cyan-500/20 text-cyan-300 rounded text-xs">
              {term}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-2">
        {data.results.map((result) => (
          <div 
            key={result.cv_id} 
            className="bg-slate-700/50 rounded-lg p-3 hover:bg-slate-700/70 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <button
                  onClick={() => onOpenCV?.(result.cv_id)}
                  className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors mb-1"
                >
                  <FileText className="w-4 h-4" />
                  <span className="font-medium">{result.candidate_name}</span>
                </button>
                
                {result.current_role && (
                  <div className="text-sm text-gray-400 mb-1">{result.current_role}</div>
                )}

                {result.matching_skills?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {result.matching_skills.map((skill, i) => (
                      <span 
                        key={i} 
                        className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 rounded text-xs flex items-center gap-1"
                      >
                        <CheckCircle className="w-3 h-3" />
                        {skill}
                      </span>
                    ))}
                  </div>
                )}

                {result.relevance_reason && (
                  <div className="text-xs text-gray-500 mt-2">{result.relevance_reason}</div>
                )}
              </div>

              <div className={`px-3 py-1 rounded-lg ${getScoreBg(result.match_score)}`}>
                <span className={`font-bold ${getScoreColor(result.match_score)}`}>
                  {result.match_score?.toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SearchResultsTable;
