import React, { useState } from 'react';
import { Search, FileText, ChevronDown, ChevronUp, Star, Briefcase, Award, Bookmark } from 'lucide-react';

/**
 * SearchResultsTable - Enhanced search results with hover cards, badges, and better UX
 */
const SearchResultsTable = ({ data, onOpenCV }) => {
  const [expanded, setExpanded] = useState(false);
  const [hoveredResult, setHoveredResult] = useState(null);
  const [savedItems, setSavedItems] = useState({});
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

  const getSeniorityBadge = (years) => {
    if (years >= 10) return { label: 'Principal', color: 'text-purple-400 bg-purple-500/20' };
    if (years >= 7) return { label: 'Senior', color: 'text-emerald-400 bg-emerald-500/20' };
    if (years >= 3) return { label: 'Mid', color: 'text-cyan-400 bg-cyan-500/20' };
    return { label: 'Junior', color: 'text-blue-400 bg-blue-500/20' };
  };

  const toggleSave = (cvId) => {
    setSavedItems(prev => ({ ...prev, [cvId]: !prev[cvId] }));
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

      {/* Results list */}
      <div className="space-y-1">
        {visibleResults.map((result, idx) => {
          const seniority = getSeniorityBadge(result.experience_years || 0);
          const isTopMatch = idx < 3 && result.match_score >= 75;
          const isHovered = hoveredResult === result.cv_id;
          
          return (
            <div 
              key={result.cv_id}
              className={`relative rounded-lg transition-all ${
                isTopMatch 
                  ? 'bg-gradient-to-r from-slate-700/60 to-slate-700/40 border border-emerald-500/20' 
                  : 'bg-slate-700/40 hover:bg-slate-700/60'
              }`}
              onMouseEnter={() => setHoveredResult(result.cv_id)}
              onMouseLeave={() => setHoveredResult(null)}
            >
              {/* Main row */}
              <div className="flex items-center justify-between px-3 py-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {/* Top match badge */}
                  {isTopMatch && (
                    <div className="flex-shrink-0">
                      <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                    </div>
                  )}
                  
                  <button
                    onClick={() => onOpenCV?.(result.cv_id)}
                    className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors truncate"
                  >
                    <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="font-medium text-sm truncate">{result.candidate_name}</span>
                  </button>

                  {/* Seniority badge */}
                  {result.experience_years > 0 && (
                    <span className={`px-1.5 py-0.5 rounded text-xs flex-shrink-0 ${seniority.color}`}>
                      {seniority.label}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Save button */}
                  <button
                    onClick={() => toggleSave(result.cv_id)}
                    className="p-1 hover:bg-slate-600/50 rounded transition-colors"
                  >
                    <Bookmark className={`w-3.5 h-3.5 ${
                      savedItems[result.cv_id] 
                        ? 'text-yellow-400 fill-yellow-400' 
                        : 'text-slate-500 hover:text-slate-400'
                    }`} />
                  </button>
                  
                  {/* Score */}
                  <div className={`px-2 py-0.5 rounded ${getScoreBg(result.match_score)}`}>
                    <span className={`text-sm font-semibold ${getScoreColor(result.match_score)}`}>
                      {result.match_score?.toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Hover preview card */}
              {isHovered && (result.current_role || result.matching_skills?.length > 0) && (
                <div className="px-3 pb-2 pt-0 border-t border-slate-600/50 animate-fadeIn">
                  {result.current_role && (
                    <div className="flex items-center gap-1 text-xs text-slate-400 mb-1">
                      <Briefcase className="w-3 h-3" />
                      <span>{result.current_role}</span>
                    </div>
                  )}
                  {result.matching_skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {result.matching_skills.slice(0, 4).map((skill, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 rounded text-xs">
                          ✓ {skill}
                        </span>
                      ))}
                      {result.matching_skills.length > 4 && (
                        <span className="text-xs text-slate-500">
                          +{result.matching_skills.length - 4} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
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

      {/* Footer stats */}
      <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <Star className="w-3 h-3 text-yellow-400" />
          {data.results.filter(r => r.match_score >= 75).length} top matches
        </span>
        <span>|</span>
        <span>Avg: {(data.results.reduce((a, r) => a + (r.match_score || 0), 0) / data.results.length).toFixed(0)}%</span>
      </div>
    </div>
  );
};

export default SearchResultsTable;
