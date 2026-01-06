import React from 'react';
import { Users, TrendingUp, Code, MapPin } from 'lucide-react';

/**
 * PoolSummary - Displays talent pool statistics
 */
const PoolSummary = ({ data }) => {
  if (!data) return null;

  const { talent_pool, skill_distribution, experience_distribution } = data;

  const getBarWidth = (count, total) => {
    return total > 0 ? (count / total) * 100 : 0;
  };

  return (
    <div className="space-y-4">
      {/* Pool Overview */}
      {talent_pool && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-blue-400" />
            <span className="font-semibold text-blue-300">Talent Pool Overview</span>
          </div>
          
          <div className="text-center mb-4">
            <span className="text-4xl font-bold text-white">{talent_pool.total_candidates}</span>
            <span className="text-gray-400 ml-2">candidates</span>
          </div>

          {/* Experience Distribution */}
          {talent_pool.experience_distribution && (
            <div className="space-y-2">
              <span className="text-sm text-gray-400">Experience Distribution</span>
              {Object.entries(talent_pool.experience_distribution).map(([level, count]) => (
                <div key={level} className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-20">{level}</span>
                  <div className="flex-1 h-4 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 transition-all"
                      style={{ width: `${getBarWidth(count, talent_pool.total_candidates)}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-300 w-8">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Experience Levels */}
      {experience_distribution && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-emerald-300">Experience Levels</span>
          </div>

          <div className="text-center mb-4">
            <span className="text-2xl font-bold text-emerald-400">
              {experience_distribution.average_years?.toFixed(1)}
            </span>
            <span className="text-gray-400 ml-2">avg years</span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Junior', count: experience_distribution.junior, color: 'bg-blue-500' },
              { label: 'Mid', count: experience_distribution.mid, color: 'bg-cyan-500' },
              { label: 'Senior', count: experience_distribution.senior, color: 'bg-emerald-500' },
              { label: 'Principal', count: experience_distribution.principal, color: 'bg-purple-500' },
            ].map(({ label, count, color }) => (
              <div key={label} className="bg-slate-700/50 rounded-lg p-2 text-center">
                <div className={`w-3 h-3 ${color} rounded-full mx-auto mb-1`} />
                <div className="text-lg font-bold text-white">{count || 0}</div>
                <div className="text-xs text-gray-400">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Skills */}
      {skill_distribution?.skills?.length > 0 && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Code className="w-5 h-5 text-purple-400" />
            <span className="font-semibold text-purple-300">Top Skills</span>
          </div>

          <div className="space-y-2">
            {skill_distribution.skills.slice(0, 8).map((skill, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="text-sm text-gray-300 flex-1">{skill.skill}</span>
                <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-purple-500 transition-all"
                    style={{ width: `${skill.percentage}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-12 text-right">
                  {skill.candidate_count} ({skill.percentage?.toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PoolSummary;
