import React from 'react';
import { Star, FileText, Award, ArrowRight } from 'lucide-react';

/**
 * TopPickCard - Highlights the #1 recommended candidate
 */
const TopPickCard = ({ data, onOpenCV }) => {
  if (!data) return null;

  return (
    <div className="rounded-xl bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border border-yellow-500/30 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Star className="w-6 h-6 text-yellow-400 fill-yellow-400" />
        <span className="font-bold text-yellow-300 text-lg">Top Recommendation</span>
      </div>

      <div className="bg-slate-800/50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => onOpenCV?.(data.cv_id)}
            className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
          >
            <FileText className="w-5 h-5" />
            <span className="font-bold text-xl text-white">{data.candidate_name}</span>
          </button>
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-yellow-400" />
            <span className="text-2xl font-bold text-emerald-400">
              {data.overall_score?.toFixed(0)}%
            </span>
          </div>
        </div>

        {data.justification && (
          <p className="text-gray-300 text-sm mb-3">{data.justification}</p>
        )}

        {data.key_strengths?.length > 0 && (
          <div className="space-y-1">
            <span className="text-sm text-gray-400">Key Strengths:</span>
            <div className="flex flex-wrap gap-2">
              {data.key_strengths.map((strength, i) => (
                <span 
                  key={i}
                  className="px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded text-sm"
                >
                  ✅ {strength}
                </span>
              ))}
            </div>
          </div>
        )}

        {data.runner_up && (
          <div className="mt-3 pt-3 border-t border-slate-600">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <ArrowRight className="w-4 h-4" />
              <span>Runner-up:</span>
              <button
                onClick={() => onOpenCV?.(data.runner_up_cv_id)}
                className="text-blue-400 hover:text-blue-300 transition-colors"
              >
                {data.runner_up}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TopPickCard;
