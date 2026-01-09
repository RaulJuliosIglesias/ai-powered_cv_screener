import React, { useState } from 'react';
import { 
  Users, UserCheck, AlertTriangle, FileText, CheckCircle, 
  TrendingUp, Award, Target, Zap, Shield, BarChart3,
  ChevronDown, ChevronUp, Star, Clock, Briefcase
} from 'lucide-react';

/**
 * TeamBuildView V2 - Enhanced visual team building display
 * Shows: Overview, Member Cards, Synergy Analysis, Skill Matrix, Risks
 */
const TeamBuildView = ({ data, onOpenCV }) => {
  const [expandedMember, setExpandedMember] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  if (!data) return null;

  const { 
    team_overview, 
    team_members, 
    team_synergy, 
    skill_matrix,
    team_risks,
    team_composition,
    direct_answer,
    conclusion
  } = data;

  const members = team_members?.cards || team_composition?.assignments || [];
  const overview = team_overview || {};
  const synergy = team_synergy || {};
  const matrix = skill_matrix || {};
  const risks = team_risks || {};

  // Compute metrics from members if not in overview
  const computedTotalExp = members.reduce((sum, m) => 
    sum + (m.experience_years || m.experience || 0), 0);
  const computedAvgExp = members.length > 0 ? computedTotalExp / members.length : 0;
  const computedTeamScore = members.length > 0 
    ? Math.min(100, 60 + (computedTotalExp / members.length) * 2) 
    : 75;

  // Use computed values as fallback
  const totalExp = overview.total_experience_years || computedTotalExp;
  const avgExp = overview.average_experience || computedAvgExp;
  const teamScore = overview.team_score || computedTeamScore;

  // Collect all skills from members for synergy/matrix fallback
  const allMemberSkills = members.flatMap(m => 
    m.matching_skills || m.skills || m.top_skills || []
  );
  const uniqueSkills = [...new Set(allMemberSkills)];

  // Color utilities
  const getScoreColor = (score) => {
    if (score >= 85) return 'text-emerald-400';
    if (score >= 70) return 'text-blue-400';
    if (score >= 55) return 'text-amber-400';
    return 'text-red-400';
  };

  const getScoreBg = (score) => {
    if (score >= 85) return 'bg-emerald-500/20 border-emerald-500/30';
    if (score >= 70) return 'bg-blue-500/20 border-blue-500/30';
    if (score >= 55) return 'bg-amber-500/20 border-amber-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  const getRiskColor = (level) => {
    switch(level) {
      case 'minimal': return 'text-emerald-400 bg-emerald-500/20';
      case 'low': return 'text-blue-400 bg-blue-500/20';
      case 'medium': return 'text-amber-400 bg-amber-500/20';
      case 'high': return 'text-red-400 bg-red-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  // Tab navigation
  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'members', label: 'Team Members', icon: Users },
    { id: 'synergy', label: 'Synergy', icon: Zap },
    { id: 'skills', label: 'Skills Matrix', icon: Target },
  ];

  return (
    <div className="space-y-4">
      {/* Direct Answer Header */}
      {direct_answer && (
        <div className="rounded-xl bg-gradient-to-r from-purple-900/50 to-indigo-900/50 border border-purple-500/30 p-4">
          <div className="prose prose-invert prose-sm max-w-none">
            <div dangerouslySetInnerHTML={{ 
              __html: direct_answer
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
                .replace(/\n/g, '<br/>')
            }} />
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id 
                ? 'bg-purple-600 text-white' 
                : 'bg-slate-700/50 text-gray-400 hover:bg-slate-700 hover:text-white'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard 
              icon={Users} 
              label="Team Size" 
              value={members.length} 
              suffix="members"
              color="purple"
            />
            <MetricCard 
              icon={Clock} 
              label="Combined Exp" 
              value={totalExp.toFixed(0)} 
              suffix="years"
              color="blue"
            />
            <MetricCard 
              icon={TrendingUp} 
              label="Avg Experience" 
              value={avgExp.toFixed(1)} 
              suffix="years"
              color="emerald"
            />
            <MetricCard 
              icon={Award} 
              label="Team Score" 
              value={teamScore.toFixed(0)} 
              suffix="%"
              color={teamScore >= 80 ? 'emerald' : teamScore >= 65 ? 'blue' : 'amber'}
            />
          </div>

          {/* Team Score Visual */}
          {teamScore > 0 && (
            <div className={`rounded-xl border p-4 ${getScoreBg(teamScore)}`}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-300">Team Readiness</span>
                <span className={`text-2xl font-bold ${getScoreColor(teamScore)}`}>
                  {teamScore.toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div 
                  className={`h-3 rounded-full transition-all ${
                    teamScore >= 85 ? 'bg-emerald-500' :
                    teamScore >= 70 ? 'bg-blue-500' :
                    teamScore >= 55 ? 'bg-amber-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(100, teamScore)}%` }}
                />
              </div>
              {overview.recommendation && (
                <p className="mt-3 text-sm text-gray-300">{overview.recommendation}</p>
              )}
            </div>
          )}

          {/* Key Strengths */}
          {overview.key_strengths?.length > 0 && (
            <div className="rounded-xl bg-slate-800/50 p-4">
              <h4 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                <Star className="w-4 h-4" /> Team Strengths
              </h4>
              <div className="space-y-2">
                {overview.key_strengths.map((strength, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    {strength}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Seniority Distribution */}
          {overview.seniority_summary && (
            <div className="rounded-xl bg-slate-800/50 p-4">
              <div className="flex items-center gap-2 text-sm">
                <Briefcase className="w-4 h-4 text-blue-400" />
                <span className="text-gray-400">Composition:</span>
                <span className="text-gray-200">{overview.seniority_summary}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Members Tab */}
      {activeTab === 'members' && (
        <div className="space-y-3">
          {members.map((member, idx) => (
            <MemberCard 
              key={idx} 
              member={member} 
              rank={idx + 1}
              isExpanded={expandedMember === idx}
              onToggle={() => setExpandedMember(expandedMember === idx ? null : idx)}
              onOpenCV={onOpenCV}
            />
          ))}
        </div>
      )}

      {/* Synergy Tab */}
      {activeTab === 'synergy' && (
        <div className="space-y-4">
          {/* Synergy Highlights - with fallback */}
          <div className="rounded-xl bg-gradient-to-br from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 p-4">
            <h4 className="text-sm font-semibold text-indigo-400 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4" /> Synergy Highlights
            </h4>
            <div className="space-y-2">
              {synergy.synergy_highlights?.length > 0 ? (
                synergy.synergy_highlights.map((highlight, idx) => (
                  <div key={idx} className="text-sm text-gray-300">{highlight}</div>
                ))
              ) : (
                <>
                  <div className="text-sm text-gray-300">🎯 Combined {totalExp.toFixed(0)} years of experience</div>
                  {uniqueSkills.length > 0 && (
                    <div className="text-sm text-gray-300">🌟 {uniqueSkills.length} unique skills across the team</div>
                  )}
                  <div className="text-sm text-gray-300">⚖️ Team of {members.length} professionals ready to collaborate</div>
                </>
              )}
            </div>
          </div>

          {/* Scores - with computed fallback */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-slate-800/50 p-4 text-center">
              <div className="text-2xl font-bold text-emerald-400">
                {synergy.skill_coverage_score?.toFixed(0) || Math.min(100, uniqueSkills.length * 10)}%
              </div>
              <div className="text-xs text-gray-400 mt-1">Skill Coverage</div>
            </div>
            <div className="rounded-xl bg-slate-800/50 p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">
                {synergy.team_diversity_score?.toFixed(0) || Math.min(100, 50 + uniqueSkills.length * 5)}%
              </div>
              <div className="text-xs text-gray-400 mt-1">Team Diversity</div>
            </div>
          </div>

          {/* All Skills from members */}
          {uniqueSkills.length > 0 && (
            <div className="rounded-xl bg-slate-800/50 p-4">
              <h4 className="text-sm font-semibold text-purple-400 mb-3">🛠️ Team Skills</h4>
              <div className="flex flex-wrap gap-2">
                {uniqueSkills.slice(0, 15).map((skill, idx) => (
                  <span key={idx} className="px-3 py-1 bg-purple-500/20 border border-purple-500/30 rounded-full text-sm text-purple-300">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Experience Distribution */}
          <div className="rounded-xl bg-slate-800/50 p-4">
            <h4 className="text-sm font-semibold text-blue-400 mb-3">📊 Experience Distribution</h4>
            <div className="space-y-2">
              {members.map((member, idx) => {
                const exp = member.experience_years || member.experience || 0;
                const name = (member.candidate_name || member.name || 'Member').split(' ')[0];
                return (
                  <div key={idx} className="flex items-center gap-3">
                    <span className="text-sm text-gray-400 w-20 truncate">{name}</span>
                    <div className="flex-1 bg-slate-700 rounded-full h-2">
                      <div 
                        className="h-2 rounded-full bg-blue-500"
                        style={{ width: `${Math.min(100, exp * 3)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-12">{exp.toFixed(0)}y</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Potential Gaps */}
          {(synergy.potential_gaps?.length > 0 || uniqueSkills.length < 5) && (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4">
              <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Areas to Consider
              </h4>
              <div className="space-y-2">
                {synergy.potential_gaps?.length > 0 ? (
                  synergy.potential_gaps.map((gap, idx) => (
                    <div key={idx} className="text-sm text-gray-300">• {gap}</div>
                  ))
                ) : uniqueSkills.length < 5 ? (
                  <div className="text-sm text-gray-300">• Consider expanding team skill diversity</div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Skills Matrix Tab */}
      {activeTab === 'skills' && (
        <div className="space-y-4">
          {/* Strongest Areas - with fallback */}
          <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4">
            <h4 className="text-sm font-semibold text-emerald-400 mb-2">🎯 Team Strengths</h4>
            <div className="flex flex-wrap gap-2">
              {(matrix.strongest_areas?.length > 0 ? matrix.strongest_areas : uniqueSkills.slice(0, 5)).map((skill, idx) => (
                <span key={idx} className="px-3 py-1 bg-emerald-500/20 rounded-full text-sm text-emerald-300">
                  {skill}
                </span>
              ))}
              {uniqueSkills.length === 0 && (
                <span className="text-sm text-gray-400">Skills data will be extracted from team members</span>
              )}
            </div>
          </div>

          {/* Skills Matrix Table - Fallback version */}
          <div className="rounded-xl bg-slate-800/50 p-4 overflow-x-auto">
            <h4 className="text-sm font-semibold text-gray-300 mb-3">📊 Skills Distribution</h4>
            {matrix.matrix?.length > 0 ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-2 text-gray-400">Skill</th>
                    {matrix.members?.map((member, idx) => (
                      <th key={idx} className="text-center py-2 px-2 text-gray-400">
                        {member.split(' ')[0]}
                      </th>
                    ))}
                    <th className="text-center py-2 px-2 text-gray-400">Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {matrix.matrix.slice(0, 10).map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-700/50">
                      <td className="py-2 px-2 text-gray-300 capitalize">{row.skill}</td>
                      {matrix.members?.map((member, mIdx) => (
                        <td key={mIdx} className="text-center py-2 px-2">
                          {row.members?.[member]?.has_skill ? (
                            <span className="text-emerald-400">✓</span>
                          ) : (
                            <span className="text-gray-600">·</span>
                          )}
                        </td>
                      ))}
                      <td className="text-center py-2 px-2">
                        <div className="flex justify-center gap-0.5">
                          {Array.from({ length: matrix.members?.length || 0 }).map((_, i) => (
                            <div 
                              key={i} 
                              className={`w-2 h-2 rounded-full ${
                                i < row.coverage ? 'bg-emerald-500' : 'bg-slate-600'
                              }`}
                            />
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              /* Fallback: Generate matrix from members */
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-2 text-gray-400">Skill</th>
                    {members.map((member, idx) => (
                      <th key={idx} className="text-center py-2 px-2 text-gray-400">
                        {(member.candidate_name || member.name || 'M' + idx).split(' ')[0]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {uniqueSkills.slice(0, 10).map((skill, idx) => (
                    <tr key={idx} className="border-b border-slate-700/50">
                      <td className="py-2 px-2 text-gray-300 capitalize">{skill}</td>
                      {members.map((member, mIdx) => {
                        const memberSkills = (member.matching_skills || member.skills || member.top_skills || []).map(s => s.toLowerCase());
                        const hasSkill = memberSkills.includes(skill.toLowerCase());
                        return (
                          <td key={mIdx} className="text-center py-2 px-2">
                            {hasSkill ? (
                              <span className="text-emerald-400">✓</span>
                            ) : (
                              <span className="text-gray-600">·</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Member Skill Counts - with fallback */}
          <div className="rounded-xl bg-slate-800/50 p-4">
            <h4 className="text-sm font-semibold text-gray-300 mb-3">👤 Skills per Member</h4>
            <div className="space-y-2">
              {(matrix.member_skill_counts && Object.keys(matrix.member_skill_counts).length > 0) ? (
                Object.entries(matrix.member_skill_counts).map(([name, count], idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm text-gray-300">{name.split(' ')[0]}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-slate-700 rounded-full h-2">
                        <div 
                          className="h-2 rounded-full bg-blue-500"
                          style={{ width: `${Math.min(100, count * 10)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 w-8">{count}</span>
                    </div>
                  </div>
                ))
              ) : (
                members.map((member, idx) => {
                  const skillCount = (member.matching_skills || member.skills || member.top_skills || []).length;
                  const name = (member.candidate_name || member.name || 'Member').split(' ')[0];
                  return (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">{name}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-700 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full bg-blue-500"
                            style={{ width: `${Math.min(100, skillCount * 10)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400 w-8">{skillCount}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* Risk Assessment - Always visible at bottom */}
      {risks.risks?.length > 0 && (
        <div className="rounded-xl bg-slate-800/50 border border-slate-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-orange-400 flex items-center gap-2">
              <Shield className="w-4 h-4" /> Risk Assessment
            </h4>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(risks.overall_risk_level)}`}>
              {risks.overall_risk_level} risk
            </span>
          </div>
          <div className="space-y-2">
            {risks.risks.map((risk, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span>{risk.icon || '⚠️'}</span>
                <span className="text-gray-300">{risk.description}</span>
              </div>
            ))}
          </div>
          {risks.mitigations?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-700">
              <p className="text-xs text-gray-400 mb-2">Recommendations:</p>
              {risks.mitigations.map((mit, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm text-emerald-400">
                  <span>💡</span>
                  <span>{mit}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Conclusion */}
      {conclusion && (
        <div className="rounded-xl bg-slate-800/30 border border-slate-700 p-4">
          <p className="text-sm text-gray-300 italic">{conclusion}</p>
        </div>
      )}
    </div>
  );
};

// Metric Card Component
const MetricCard = ({ icon: Icon, label, value, suffix, color = 'blue' }) => {
  const colors = {
    purple: 'text-purple-400 bg-purple-500/20',
    blue: 'text-blue-400 bg-blue-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/20',
    amber: 'text-amber-400 bg-amber-500/20',
  };

  return (
    <div className={`rounded-xl ${colors[color]} p-3`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`w-4 h-4 ${colors[color].split(' ')[0]}`} />
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-xl font-bold ${colors[color].split(' ')[0]}`}>{value}</span>
        <span className="text-xs text-gray-500">{suffix}</span>
      </div>
    </div>
  );
};

// Member Card Component
const MemberCard = ({ member, rank, isExpanded, onToggle, onOpenCV }) => {
  const getFitBadge = (score) => {
    if (score >= 90) return { text: 'Excellent', color: 'bg-emerald-500/20 text-emerald-400' };
    if (score >= 80) return { text: 'Strong', color: 'bg-blue-500/20 text-blue-400' };
    if (score >= 70) return { text: 'Good', color: 'bg-amber-500/20 text-amber-400' };
    return { text: 'Fair', color: 'bg-gray-500/20 text-gray-400' };
  };

  const fitBadge = getFitBadge(member.fit_score);
  const displayName = member.name || member.candidate_name || 'Unknown';
  const cleanName = displayName.replace(/ (Research|Associate|UX|Lab|Manager|Developer)$/, '');

  return (
    <div className="rounded-xl bg-slate-800/50 border border-slate-700 overflow-hidden">
      {/* Header */}
      <div 
        className="p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white font-bold">
              #{rank}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenCV?.(member.cv_id); }}
                  className="font-semibold text-white hover:text-blue-400 transition-colors"
                >
                  {cleanName}
                </button>
                {member.badge && (
                  <span className="text-xs">{member.badge}</span>
                )}
              </div>
              <div className="text-sm text-gray-400">{member.role || member.role_name}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${fitBadge.color}`}>
              {member.fit_score?.toFixed(0)}% {fitBadge.text}
            </span>
            {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="flex gap-4 mt-3 text-sm">
          <div className="flex items-center gap-1 text-gray-400">
            <Clock className="w-3 h-3" />
            <span>{member.experience_years?.toFixed(0) || member.experience?.toFixed(0) || 0}y exp</span>
          </div>
          <div className="flex items-center gap-1 text-gray-400">
            <Briefcase className="w-3 h-3" />
            <span className="capitalize">{member.seniority || 'mid'}</span>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-slate-700">
          {/* Strengths */}
          {member.strengths?.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-2">Strengths</p>
              <div className="space-y-1">
                {member.strengths.map((strength, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle className="w-3 h-3 text-emerald-500" />
                    {strength}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Skills */}
          {(member.top_skills?.length > 0 || member.matching_skills?.length > 0) && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-2">Skills</p>
              <div className="flex flex-wrap gap-1">
                {(member.top_skills || member.matching_skills || []).slice(0, 6).map((skill, idx) => (
                  <span key={idx} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-gray-300">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Contribution */}
          {member.contribution && (
            <p className="mt-3 text-sm text-gray-400 italic">{member.contribution}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default TeamBuildView;
