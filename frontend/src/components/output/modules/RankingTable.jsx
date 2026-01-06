import React from 'react';
import { Trophy, Medal, FileText } from 'lucide-react';

/**
 * RankingTable - Displays ranked candidates with scores
 */
const RankingTable = ({ data, onOpenCV }) => {
  if (!data?.ranked || data.ranked.length === 0) return null;

  const getRankIcon = (rank) => {
    if (rank === 1) return <Trophy className="w-5 h-5 text-yellow-400" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-gray-300" />;
    if (rank === 3) return <Medal className="w-5 h-5 text-amber-600" />;
    return <span className="text-gray-400 font-mono">{rank}</span>;
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-gray-400';
  };

  return (
    <div className="rounded-xl bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Trophy className="w-5 h-5 text-yellow-400" />
        <span className="font-semibold text-yellow-300">Candidate Ranking</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-600">
              <th className="px-3 py-2 text-left text-gray-400">Rank</th>
              <th className="px-3 py-2 text-left text-gray-400">Candidate</th>
              <th className="px-3 py-2 text-center text-gray-400">Overall</th>
              {data.criteria_names?.slice(0, 3).map((crit, i) => (
                <th key={i} className="px-3 py-2 text-center text-gray-400 hidden md:table-cell">
                  {crit.length > 10 ? crit.substring(0, 10) + '...' : crit}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.ranked.map((candidate) => (
              <tr key={candidate.cv_id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                <td className="px-3 py-3">
                  <div className="flex items-center justify-center w-8 h-8">
                    {getRankIcon(candidate.rank)}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <button
                    onClick={() => onOpenCV?.(candidate.cv_id)}
                    className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    <FileText className="w-4 h-4" />
                    <span className="font-medium">{candidate.candidate_name}</span>
                  </button>
                </td>
                <td className="px-3 py-3 text-center">
                  <span className={`font-bold ${getScoreColor(candidate.overall_score)}`}>
                    {candidate.overall_score?.toFixed(0)}%
                  </span>
                </td>
                {data.criteria_names?.slice(0, 3).map((crit, i) => (
                  <td key={i} className="px-3 py-3 text-center hidden md:table-cell">
                    <span className={getScoreColor(candidate.criterion_scores?.[crit] || 0)}>
                      {candidate.criterion_scores?.[crit]?.toFixed(0) || '-'}%
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RankingTable;
