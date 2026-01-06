import React, { useState } from 'react';
import { Trophy, Medal, FileText, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * RankingTable - Compact ranked candidates with expandable list
 */
const RankingTable = ({ data, onOpenCV }) => {
  const [expanded, setExpanded] = useState(false);
  const INITIAL_SHOW = 5;

  if (!data?.ranked || data.ranked.length === 0) return null;

  const getRankBadge = (rank) => {
    if (rank === 1) return <Trophy className="w-4 h-4 text-yellow-400" />;
    if (rank === 2) return <Medal className="w-4 h-4 text-gray-300" />;
    if (rank === 3) return <Medal className="w-4 h-4 text-amber-600" />;
    return <span className="text-xs text-gray-500 w-4 text-center">{rank}</span>;
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

  return (
    <div className="rounded-xl bg-slate-800/50 p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-yellow-400" />
          <span className="font-medium text-yellow-300 text-sm">Ranking</span>
        </div>
        <span className="text-xs text-gray-400">{data.ranked.length} ranked</span>
      </div>

      {/* Compact ranking list */}
      <div className="space-y-1">
        {visibleCandidates.map((candidate) => (
          <div 
            key={candidate.cv_id} 
            className="flex items-center gap-2 bg-slate-700/40 rounded-lg px-3 py-2 hover:bg-slate-700/60 transition-colors"
          >
            <div className="flex items-center justify-center w-5">
              {getRankBadge(candidate.rank)}
            </div>
            <button
              onClick={() => onOpenCV?.(candidate.cv_id)}
              className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 transition-colors flex-1 min-w-0 truncate"
            >
              <FileText className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="font-medium text-sm truncate">{candidate.candidate_name}</span>
            </button>
            <div className={`px-2 py-0.5 rounded ${getScoreBg(candidate.overall_score)} flex-shrink-0`}>
              <span className={`text-sm font-semibold ${getScoreColor(candidate.overall_score)}`}>
                {candidate.overall_score?.toFixed(0)}%
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
              Show {data.ranked.length - INITIAL_SHOW} more
            </>
          )}
        </button>
      )}
    </div>
  );
};

export default RankingTable;
