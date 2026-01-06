import React from 'react';
import { Users, TrendingUp, Code, Briefcase, Award, BarChart3, PieChart } from 'lucide-react';

/**
 * PoolSummary - Enhanced talent pool statistics with better visualizations
 */
const PoolSummary = ({ data }) => {
  if (!data) return null;

  const { talent_pool, skill_distribution, experience_distribution } = data;

  const getBarWidth = (count, total) => {
    return total > 0 ? (count / total) * 100 : 0;
  };

  // Colors for experience levels
  const levelColors = {
    junior: { bg: 'bg-blue-500', text: 'text-blue-400', fill: '#3b82f6' },
    mid: { bg: 'bg-cyan-500', text: 'text-cyan-400', fill: '#06b6d4' },
    senior: { bg: 'bg-emerald-500', text: 'text-emerald-400', fill: '#10b981' },
    principal: { bg: 'bg-purple-500', text: 'text-purple-400', fill: '#8b5cf6' },
  };

  // Calculate donut chart segments
  const DonutChart = ({ data, total }) => {
    if (!data || total === 0) return null;
    
    const segments = Object.entries(data).filter(([_, count]) => count > 0);
    let currentAngle = 0;
    
    return (
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          {segments.map(([level, count], idx) => {
            const percentage = (count / total) * 100;
            const strokeDasharray = `${percentage} ${100 - percentage}`;
            const strokeDashoffset = -currentAngle;
            currentAngle += percentage;
            const color = levelColors[level.toLowerCase()]?.fill || '#64748b';
            
            return (
              <circle
                key={level}
                cx="18"
                cy="18"
                r="15.9"
                fill="none"
                stroke={color}
                strokeWidth="3"
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-500"
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold text-white">{total}</span>
          <span className="text-xs text-gray-400">total</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Pool Overview with Donut Chart */}
      {talent_pool && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-blue-400" />
            <span className="font-semibold text-blue-300">Talent Pool Overview</span>
          </div>
          
          <div className="flex items-center justify-between">
            {/* Donut chart */}
            <DonutChart 
              data={talent_pool.experience_distribution} 
              total={talent_pool.total_candidates} 
            />
            
            {/* Legend and stats */}
            <div className="flex-1 ml-4">
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(talent_pool.experience_distribution || {}).map(([level, count]) => {
                  const colors = levelColors[level.toLowerCase()] || { bg: 'bg-gray-500', text: 'text-gray-400' };
                  const percentage = talent_pool.total_candidates > 0 
                    ? ((count / talent_pool.total_candidates) * 100).toFixed(0) 
                    : 0;
                  
                  return (
                    <div key={level} className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${colors.bg}`} />
                      <div className="text-sm">
                        <span className="text-white font-medium">{count}</span>
                        <span className={`ml-1 ${colors.text}`}>{level}</span>
                        <span className="text-gray-500 text-xs ml-1">({percentage}%)</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
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
