import React from 'react';
import { Target, CheckCircle, XCircle, AlertCircle, FileText } from 'lucide-react';

/**
 * MatchScoreCard - Displays job match scores for candidates
 */
const MatchScoreCard = ({ data, onOpenCV }) => {
  if (!data?.matches || data.matches.length === 0) return null;

  const getMatchColor = (score) => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 60) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getMatchTextColor = (score) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="rounded-xl bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Target className="w-5 h-5 text-blue-400" />
        <span className="font-semibold text-blue-300">Match Scores</span>
        <span className="text-sm text-gray-400">({data.total_requirements} requirements)</span>
      </div>

      <div className="space-y-3">
        {data.matches.map((match) => (
          <div key={match.cv_id} className="bg-slate-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => onOpenCV?.(match.cv_id)}
                className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
              >
                <FileText className="w-4 h-4" />
                <span className="font-medium">{match.candidate_name}</span>
              </button>
              <span className={`font-bold text-lg ${getMatchTextColor(match.overall_match)}`}>
                {match.overall_match?.toFixed(0)}%
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-slate-600 rounded-full overflow-hidden mb-2">
              <div 
                className={`h-full ${getMatchColor(match.overall_match)} transition-all`}
                style={{ width: `${match.overall_match}%` }}
              />
            </div>

            <div className="flex flex-wrap gap-4 text-xs">
              {match.met_requirements?.length > 0 && (
                <div className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle className="w-3 h-3" />
                  <span>{match.met_requirements.length} met</span>
                </div>
              )}
              {match.partial_requirements?.length > 0 && (
                <div className="flex items-center gap-1 text-amber-400">
                  <AlertCircle className="w-3 h-3" />
                  <span>{match.partial_requirements.length} partial</span>
                </div>
              )}
              {match.missing_requirements?.length > 0 && (
                <div className="flex items-center gap-1 text-red-400">
                  <XCircle className="w-3 h-3" />
                  <span>{match.missing_requirements.length} missing</span>
                </div>
              )}
            </div>

            {match.missing_requirements?.length > 0 && (
              <div className="mt-2 text-xs text-gray-400">
                <span className="text-red-400">Missing:</span>{' '}
                {match.missing_requirements.slice(0, 3).join(', ')}
                {match.missing_requirements.length > 3 && ` +${match.missing_requirements.length - 3} more`}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MatchScoreCard;
