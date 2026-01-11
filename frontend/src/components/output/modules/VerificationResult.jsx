import React from 'react';
import { CheckCircle, XCircle, AlertCircle, HelpCircle, FileSearch, Quote, GraduationCap, Award } from 'lucide-react';

/**
 * VerificationResult - Displays verification claim, evidence, and verdict
 * PHASE 8.1: Added support for education credentials table
 */
const VerificationResult = ({ data }) => {
  if (!data) return null;

  const { claim, evidence, verdict, credentials_table, education_data, statistics, analysis } = data;

  const getVerdictStyle = (status) => {
    switch (status) {
      case 'CONFIRMED':
        return { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/50' };
      case 'PARTIAL':
        return { icon: AlertCircle, color: 'text-amber-400', bg: 'bg-amber-500/20', border: 'border-amber-500/50' };
      case 'CONTRADICTED':
        return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/50' };
      default:
        return { icon: HelpCircle, color: 'text-gray-400', bg: 'bg-gray-500/20', border: 'border-gray-500/50' };
    }
  };

  const verdictStyle = verdict ? getVerdictStyle(verdict.status) : getVerdictStyle('NOT_FOUND');
  const VerdictIcon = verdictStyle.icon;

  // PHASE 8.1: Check if this is an education verification with table data
  const isEducationVerification = education_data && education_data.length > 0;

  return (
    <div className="space-y-4">
      {/* PHASE 8.1: Education Credentials Table */}
      {isEducationVerification && (
        <>
          {/* Statistics Header */}
          {statistics && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">{statistics.total_candidates}</div>
                <div className="text-xs text-gray-400">Candidates</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-emerald-400">{statistics.with_education}</div>
                <div className="text-xs text-gray-400">With Education</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-purple-400">{statistics.with_certifications}</div>
                <div className="text-xs text-gray-400">Certifications</div>
              </div>
            </div>
          )}

          {/* Education Table */}
          <div className="rounded-xl bg-slate-800/50 p-4">
            <div className="flex items-center gap-2 mb-4">
              <GraduationCap className="w-5 h-5 text-blue-400" />
              <span className="font-semibold text-blue-300">Education Credentials</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-600">
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Candidate</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Education</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Certifications</th>
                    <th className="text-right py-2 px-3 text-gray-400 font-medium">Experience</th>
                  </tr>
                </thead>
                <tbody>
                  {education_data.map((candidate, idx) => (
                    <tr key={idx} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                      <td className="py-3 px-3">
                        <span className="font-medium text-white">{candidate.name}</span>
                      </td>
                      <td className="py-3 px-3 text-gray-300">
                        {candidate.education !== 'Not specified' ? (
                          <span className="flex items-center gap-1">
                            <GraduationCap className="w-3 h-3 text-blue-400" />
                            {candidate.education}
                          </span>
                        ) : (
                          <span className="text-gray-500 italic">Not specified</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-gray-300">
                        {candidate.certifications !== 'None listed' ? (
                          <span className="flex items-center gap-1">
                            <Award className="w-3 h-3 text-purple-400" />
                            {candidate.certifications}
                          </span>
                        ) : (
                          <span className="text-gray-500 italic">None</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {candidate.experience_years > 0 ? (
                          <span className="text-emerald-400">{candidate.experience_years.toFixed(1)} yrs</span>
                        ) : (
                          <span className="text-gray-500">N/A</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Analysis */}
          {analysis && (
            <div className="rounded-xl bg-slate-800/50 p-4">
              <div className="flex items-center gap-2 mb-3">
                <FileSearch className="w-5 h-5 text-cyan-400" />
                <span className="font-semibold text-cyan-300">Analysis</span>
              </div>
              <div className="prose prose-invert prose-sm max-w-none">
                {analysis.split('\n').map((line, idx) => (
                  <p key={idx} className="text-gray-300 my-1" dangerouslySetInnerHTML={{ 
                    __html: line.replace(/\*\*([^*]+)\*\*/g, '<strong class="text-white">$1</strong>') 
                  }} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Standard Claim (for non-education verification) */}
      {claim && !isEducationVerification && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <FileSearch className="w-5 h-5 text-blue-400" />
            <span className="font-semibold text-blue-300">Claim to Verify</span>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-sm text-gray-400 mb-1">
              Subject: <span className="text-white">{claim.subject}</span>
            </div>
            <div className="text-sm text-gray-400 mb-1">
              Type: <span className="text-cyan-400 capitalize">{claim.claim_type}</span>
            </div>
            <div className="text-white font-medium">{claim.claim_value}</div>
          </div>
        </div>
      )}

      {/* Evidence */}
      {evidence?.evidence?.length > 0 && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Quote className="w-5 h-5 text-purple-400" />
            <span className="font-semibold text-purple-300">Evidence Found</span>
            <span className="text-sm text-gray-400">({evidence.total_found} items)</span>
          </div>
          <div className="space-y-2">
            {evidence.evidence.map((item, idx) => (
              <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-400">{item.source}</span>
                  <span className={`text-xs ${item.relevance >= 0.7 ? 'text-emerald-400' : item.relevance >= 0.4 ? 'text-amber-400' : 'text-gray-400'}`}>
                    {(item.relevance * 100).toFixed(0)}% relevance
                  </span>
                </div>
                <blockquote className="text-sm text-gray-300 border-l-2 border-purple-500 pl-3 italic">
                  {item.excerpt}
                </blockquote>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verdict */}
      {verdict && (
        <div className={`rounded-xl ${verdictStyle.bg} border ${verdictStyle.border} p-4`}>
          <div className="flex items-center gap-2 mb-3">
            <VerdictIcon className={`w-6 h-6 ${verdictStyle.color}`} />
            <span className={`font-bold text-lg ${verdictStyle.color}`}>
              {verdict.status}
            </span>
            <span className="text-sm text-gray-400">
              ({(verdict.confidence * 100).toFixed(0)}% confidence)
            </span>
          </div>
          <p className="text-gray-300">{verdict.explanation}</p>
        </div>
      )}
    </div>
  );
};

export default VerificationResult;
