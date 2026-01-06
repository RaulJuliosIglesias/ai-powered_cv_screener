/**
 * WinnerCard - Highlights the clear winner in a comparison
 */

import React from 'react';
import { Crown, FileText, TrendingUp, Award, Sparkles } from 'lucide-react';

const WinnerCard = ({ winner, runnerUp, onOpenCV }) => {
  if (!winner) return null;

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-yellow-500/20 via-amber-500/15 to-orange-500/20 border border-yellow-500/40 p-4">
      {/* Sparkle effects */}
      <div className="absolute top-2 right-2 text-yellow-400/30">
        <Sparkles className="w-8 h-8" />
      </div>
      <div className="absolute bottom-2 left-2 text-yellow-400/20">
        <Sparkles className="w-6 h-6" />
      </div>

      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 bg-yellow-500/30 rounded-lg">
          <Crown className="w-6 h-6 text-yellow-400" />
        </div>
        <div>
          <span className="font-bold text-yellow-300 text-lg">Winner</span>
          <p className="text-xs text-yellow-400/70">Best overall candidate</p>
        </div>
      </div>

      {/* Winner info */}
      <div className="bg-slate-800/60 rounded-lg p-4 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => onOpenCV?.(winner.cv_id)}
            className="flex items-center gap-2 text-white hover:text-yellow-300 transition-colors group"
          >
            <FileText className="w-5 h-5 text-yellow-400 group-hover:scale-110 transition-transform" />
            <span className="font-bold text-xl">{winner.candidate_name}</span>
          </button>
          <div className="flex items-center gap-2 bg-emerald-500/20 px-3 py-1 rounded-full">
            <Award className="w-4 h-4 text-emerald-400" />
            <span className="text-xl font-bold text-emerald-400">
              {winner.overall_score?.toFixed(0) || winner.score?.toFixed(0) || '—'}%
            </span>
          </div>
        </div>

        {/* Winning reasons */}
        {winner.winning_reasons?.length > 0 && (
          <div className="space-y-2 mb-3">
            <span className="text-xs text-slate-400 uppercase tracking-wider">Why they win:</span>
            <div className="flex flex-wrap gap-2">
              {winner.winning_reasons.map((reason, i) => (
                <span 
                  key={i}
                  className="px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded text-sm flex items-center gap-1"
                >
                  <TrendingUp className="w-3 h-3" />
                  {reason}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Key strengths */}
        {winner.strengths?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {winner.strengths.slice(0, 4).map((strength, i) => (
              <span 
                key={i}
                className="px-2 py-0.5 bg-slate-700/50 text-slate-300 rounded text-xs"
              >
                ✓ {strength}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Runner-up */}
      {runnerUp && (
        <div className="mt-3 pt-3 border-t border-slate-600/50">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-lg">🥈</span>
              <span>Runner-up:</span>
              <button
                onClick={() => onOpenCV?.(runnerUp.cv_id)}
                className="text-blue-400 hover:text-blue-300 transition-colors font-medium"
              >
                {runnerUp.candidate_name}
              </button>
            </div>
            <span className="text-slate-400">
              {runnerUp.overall_score?.toFixed(0) || runnerUp.score?.toFixed(0) || '—'}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default WinnerCard;
