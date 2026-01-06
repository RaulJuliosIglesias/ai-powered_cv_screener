import React from 'react';
import { CheckCircle, XCircle, AlertCircle, HelpCircle, FileSearch, Quote } from 'lucide-react';

/**
 * VerificationResult - Displays verification claim, evidence, and verdict
 */
const VerificationResult = ({ data }) => {
  if (!data) return null;

  const { claim, evidence, verdict } = data;

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

  return (
    <div className="space-y-4">
      {/* Claim */}
      {claim && (
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
