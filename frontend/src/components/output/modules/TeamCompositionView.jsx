import React from 'react';
import { Users, UserCheck, AlertTriangle, FileText, CheckCircle } from 'lucide-react';

/**
 * TeamCompositionView - Displays team composition with roles and assignments
 */
const TeamCompositionView = ({ data, onOpenCV }) => {
  if (!data) return null;

  const { team_composition, skill_coverage, team_risks } = data;

  const getFitColor = (score) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'text-red-400 bg-red-500/20';
      case 'medium': return 'text-amber-400 bg-amber-500/20';
      case 'low': return 'text-emerald-400 bg-emerald-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  return (
    <div className="space-y-4">
      {/* Team Assignments */}
      {team_composition?.assignments?.length > 0 && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-purple-400" />
            <span className="font-semibold text-purple-300">Proposed Team</span>
          </div>

          <div className="space-y-3">
            {team_composition.assignments.map((assignment, idx) => (
              <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-300">{assignment.role_name}</span>
                  <span className={`text-sm font-bold ${getFitColor(assignment.fit_score)}`}>
                    {assignment.fit_score?.toFixed(0)}% fit
                  </span>
                </div>
                <button
                  onClick={() => onOpenCV?.(assignment.cv_id)}
                  className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  <span>{assignment.candidate_name}</span>
                </button>
                {assignment.matching_skills?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {assignment.matching_skills.slice(0, 4).map((skill, i) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-600 rounded text-xs text-gray-300">
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {team_composition.unassigned_roles?.length > 0 && (
            <div className="mt-3 p-2 bg-amber-500/20 rounded-lg">
              <div className="flex items-center gap-2 text-amber-400 text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>Unfilled roles: {team_composition.unassigned_roles.join(', ')}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Skill Coverage */}
      {skill_coverage && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <span className="font-semibold text-emerald-300">Skill Coverage</span>
            </div>
            <span className="text-lg font-bold text-emerald-400">
              {skill_coverage.overall_coverage?.toFixed(0)}%
            </span>
          </div>

          {skill_coverage.gaps?.length > 0 && (
            <div className="p-2 bg-red-500/20 rounded-lg">
              <span className="text-sm text-red-400">
                ⚠️ Skill gaps: {skill_coverage.gaps.join(', ')}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Team Risks */}
      {team_risks?.risks?.length > 0 && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-orange-400" />
            <span className="font-semibold text-orange-300">Team Risks</span>
            <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(team_risks.overall_risk_level)}`}>
              {team_risks.overall_risk_level}
            </span>
          </div>

          <div className="space-y-2">
            {team_risks.risks.map((risk, idx) => (
              <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(risk.severity)}`}>
                    {risk.severity}
                  </span>
                  <span className="text-sm font-medium text-gray-300">
                    {risk.risk_type?.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-xs text-gray-400">{risk.description}</p>
                {risk.mitigation && (
                  <p className="text-xs text-emerald-400 mt-1">💡 {risk.mitigation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamCompositionView;
