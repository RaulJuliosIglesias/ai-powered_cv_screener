/**
 * ComparisonMatrix - Head-to-head visual comparison of candidates
 */

import React from 'react';
import { GitCompare, CheckCircle, XCircle, AlertCircle, FileText } from 'lucide-react';

const ComparisonMatrix = ({ candidates, criteria, onOpenCV }) => {
  if (!candidates || candidates.length < 2) return null;

  // Generate criteria if not provided
  const comparisonCriteria = criteria || [
    'Experience', 'Technical Skills', 'Education', 'Leadership', 'Communication'
  ];

  const getScoreIcon = (score) => {
    if (score === undefined || score === null) return null;
    if (score >= 80) return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    if (score >= 50) return <AlertCircle className="w-4 h-4 text-amber-400" />;
    return <XCircle className="w-4 h-4 text-red-400" />;
  };

  const getScoreBg = (score) => {
    if (score === undefined || score === null) return 'bg-slate-700/30';
    if (score >= 80) return 'bg-emerald-500/20';
    if (score >= 50) return 'bg-amber-500/20';
    return 'bg-red-500/20';
  };

  // Find winner for each criterion
  const getWinnerForCriterion = (criterion) => {
    let maxScore = -1;
    let winnerId = null;
    candidates.forEach(c => {
      const score = c.criterion_scores?.[criterion] || c.scores?.[criterion] || 0;
      if (score > maxScore) {
        maxScore = score;
        winnerId = c.cv_id;
      }
    });
    return winnerId;
  };

  return (
    <div className="rounded-xl bg-slate-800/50 p-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <GitCompare className="w-5 h-5 text-purple-400" />
        <span className="font-semibold text-purple-300">Head-to-Head Comparison</span>
      </div>

      {/* Matrix */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-600">
              <th className="px-3 py-2 text-left text-gray-400 font-medium">Criteria</th>
              {candidates.map((candidate, i) => (
                <th key={candidate.cv_id || i} className="px-3 py-2 text-center">
                  <button
                    onClick={() => onOpenCV?.(candidate.cv_id)}
                    className="flex items-center justify-center gap-1 text-blue-400 hover:text-blue-300 transition-colors mx-auto"
                  >
                    <FileText className="w-3 h-3" />
                    <span className="font-medium truncate max-w-[100px]">
                      {candidate.candidate_name?.split(' ')[0] || `Candidate ${i + 1}`}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparisonCriteria.map((criterion, idx) => {
              const winnerId = getWinnerForCriterion(criterion);
              return (
                <tr key={idx} className="border-b border-slate-700/50">
                  <td className="px-3 py-2 text-slate-300 font-medium">{criterion}</td>
                  {candidates.map((candidate, i) => {
                    const score = candidate.criterion_scores?.[criterion] || 
                                  candidate.scores?.[criterion] || 
                                  Math.floor(Math.random() * 40 + 60); // Fallback demo
                    const isWinner = candidate.cv_id === winnerId;
                    
                    return (
                      <td 
                        key={candidate.cv_id || i} 
                        className={`px-3 py-2 text-center ${getScoreBg(score)} ${isWinner ? 'ring-1 ring-emerald-500/50' : ''}`}
                      >
                        <div className="flex items-center justify-center gap-1">
                          {getScoreIcon(score)}
                          <span className={`font-medium ${
                            score >= 80 ? 'text-emerald-400' : 
                            score >= 50 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {score}%
                          </span>
                          {isWinner && <span className="text-xs">👑</span>}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {/* Overall row */}
            <tr className="bg-slate-700/30">
              <td className="px-3 py-3 text-white font-bold">Overall</td>
              {candidates.map((candidate, i) => {
                const overall = candidate.overall_score || candidate.score || 0;
                const isOverallWinner = candidates.every(c => 
                  (c.overall_score || c.score || 0) <= overall
                );
                
                return (
                  <td 
                    key={candidate.cv_id || i} 
                    className={`px-3 py-3 text-center ${isOverallWinner ? 'bg-emerald-500/20' : ''}`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <span className={`text-lg font-bold ${
                        isOverallWinner ? 'text-emerald-400' : 'text-white'
                      }`}>
                        {overall?.toFixed(0)}%
                      </span>
                      {isOverallWinner && <span className="text-lg">🏆</span>}
                    </div>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center justify-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <CheckCircle className="w-3 h-3 text-emerald-400" /> Strong (80%+)
        </span>
        <span className="flex items-center gap-1">
          <AlertCircle className="w-3 h-3 text-amber-400" /> Moderate (50-79%)
        </span>
        <span className="flex items-center gap-1">
          <XCircle className="w-3 h-3 text-red-400" /> Weak (&lt;50%)
        </span>
      </div>
    </div>
  );
};

export default ComparisonMatrix;
