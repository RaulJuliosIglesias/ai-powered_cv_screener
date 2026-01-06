import React, { useState } from 'react';
import { Trophy, Medal, FileText, ChevronDown, ChevronUp, Crown, TrendingUp, Bookmark, Sparkles } from 'lucide-react';

/**
 * RankingTable - Enhanced ranked candidates with prominent #1 highlight
 */
const RankingTable = ({ data, onOpenCV }) => {
  const [expanded, setExpanded] = useState(false);
  const [savedItems, setSavedItems] = useState({});
  const INITIAL_SHOW = 5;

  if (!data?.ranked || data.ranked.length === 0) return null;

  const toggleSave = (cvId) => {
    setSavedItems(prev => ({ ...prev, [cvId]: !prev[cvId] }));
  };

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

  const visibleCandidates = expanded ? data.ranked : data.ranked.slice(0, INITIAL_SHOW);
  const hasMore = data.ranked.length > INITIAL_SHOW;
  const topCandidate = data.ranked[0];

  return (
    <div className="rounded-xl bg-slate-800/50 p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-yellow-400" />
          <span className="font-medium text-yellow-300 text-sm">Candidate Ranking</span>
        </div>
        <span className="text-xs text-gray-400">{data.ranked.length} ranked</span>
      </div>

      {/* #1 Candidate - Prominent display */}
      {topCandidate && (
        <div className="relative mb-3 p-3 rounded-lg bg-gradient-to-r from-yellow-500/20 via-amber-500/15 to-orange-500/10 border border-yellow-500/30 overflow-hidden">
          <Sparkles className="absolute top-1 right-1 w-5 h-5 text-yellow-400/30" />
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 bg-yellow-500/30 rounded-full">
              <Crown className="w-5 h-5 text-yellow-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs text-yellow-400/70 uppercase tracking-wider">#1 Top Pick</span>
              </div>
              <button
                onClick={() => onOpenCV?.(topCandidate.cv_id)}
                className="flex items-center gap-1.5 text-white hover:text-yellow-300 transition-colors"
              >
                <FileText className="w-4 h-4 text-yellow-400" />
                <span className="font-bold text-lg truncate">{topCandidate.candidate_name}</span>
              </button>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-emerald-400">
                {topCandidate.overall_score?.toFixed(0)}%
              </div>
              <div className="text-xs text-gray-400">Overall Score</div>
            </div>
          </div>
          {topCandidate.key_strengths?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {topCandidate.key_strengths.slice(0, 3).map((s, i) => (
                <span key={i} className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 rounded text-xs">
                  ✓ {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Rest of ranking */}
      <div className="space-y-1">
        {visibleCandidates.slice(1).map((candidate, idx) => {
          const rank = idx + 2;
          const isTopThree = rank <= 3;
          
          return (
            <div 
              key={candidate.cv_id} 
              className={`flex items-center gap-2 rounded-lg px-3 py-2 transition-colors ${
                isTopThree 
                  ? 'bg-slate-700/50 border border-slate-600/50' 
                  : 'bg-slate-700/30 hover:bg-slate-700/50'
              }`}
            >
              {/* Rank badge */}
              <div className="flex items-center justify-center w-6">
                {rank === 2 ? (
                  <div className="flex items-center justify-center w-5 h-5 bg-gray-400/20 rounded-full">
                    <span className="text-xs font-bold text-gray-300">2</span>
                  </div>
                ) : rank === 3 ? (
                  <div className="flex items-center justify-center w-5 h-5 bg-amber-600/20 rounded-full">
                    <span className="text-xs font-bold text-amber-500">3</span>
                  </div>
                ) : (
                  <span className="text-xs text-gray-500 font-medium">{rank}</span>
                )}
              </div>

              {/* Candidate info */}
              <button
                onClick={() => onOpenCV?.(candidate.cv_id)}
                className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors flex-1 min-w-0"
              >
                <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="font-medium text-sm truncate">{candidate.candidate_name}</span>
              </button>

              {/* Score diff from #1 */}
              {topCandidate && (
                <span className="text-xs text-gray-500 flex-shrink-0">
                  -{(topCandidate.overall_score - candidate.overall_score).toFixed(0)}%
                </span>
              )}

              {/* Save button */}
              <button
                onClick={() => toggleSave(candidate.cv_id)}
                className="p-1 hover:bg-slate-600/50 rounded transition-colors flex-shrink-0"
              >
                <Bookmark className={`w-3.5 h-3.5 ${
                  savedItems[candidate.cv_id] 
                    ? 'text-yellow-400 fill-yellow-400' 
                    : 'text-slate-500 hover:text-slate-400'
                }`} />
              </button>

              {/* Score */}
              <div className={`px-2 py-0.5 rounded ${getScoreBg(candidate.overall_score)} flex-shrink-0`}>
                <span className={`text-sm font-semibold ${getScoreColor(candidate.overall_score)}`}>
                  {candidate.overall_score?.toFixed(0)}%
                </span>
              </div>
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
              Show {data.ranked.length - INITIAL_SHOW} more
            </>
          )}
        </button>
      )}

      {/* Score distribution footer */}
      <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-500">
        <span>Score range: {data.ranked[data.ranked.length - 1]?.overall_score?.toFixed(0)}% - {topCandidate?.overall_score?.toFixed(0)}%</span>
        <span className="flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          Avg: {(data.ranked.reduce((a, c) => a + (c.overall_score || 0), 0) / data.ranked.length).toFixed(0)}%
        </span>
      </div>
    </div>
  );
};

export default RankingTable;
