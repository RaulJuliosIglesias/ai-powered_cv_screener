/**
 * ConfidenceIndicator - Shows AI analysis confidence level
 */

import React from 'react';
import { Brain, Database, Target, Info } from 'lucide-react';

const ConfidenceIndicator = ({ 
  dataQuality = 75, 
  analysisConfidence = 80, 
  matchRelevance = 70,
  compact = false 
}) => {
  const getConfidenceColor = (value) => {
    if (value >= 80) return 'bg-emerald-500';
    if (value >= 60) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getConfidenceTextColor = (value) => {
    if (value >= 80) return 'text-emerald-400';
    if (value >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const metrics = [
    { 
      label: 'Data Quality', 
      value: dataQuality, 
      icon: Database,
      tooltip: 'Quality and completeness of CV data'
    },
    { 
      label: 'Analysis Confidence', 
      value: analysisConfidence, 
      icon: Brain,
      tooltip: 'AI confidence in the analysis'
    },
    { 
      label: 'Match Relevance', 
      value: matchRelevance, 
      icon: Target,
      tooltip: 'Relevance to your query'
    },
  ];

  const avgConfidence = Math.round((dataQuality + analysisConfidence + matchRelevance) / 3);

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Brain className="w-3 h-3" />
        <span>AI Confidence:</span>
        <div className="flex items-center gap-1">
          <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getConfidenceColor(avgConfidence)} transition-all`}
              style={{ width: `${avgConfidence}%` }}
            />
          </div>
          <span className={getConfidenceTextColor(avgConfidence)}>{avgConfidence}%</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-slate-800/30 border border-slate-700/50 p-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-purple-300">AI Confidence</span>
        </div>
        <div className={`text-sm font-bold ${getConfidenceTextColor(avgConfidence)}`}>
          {avgConfidence}% Overall
        </div>
      </div>

      <div className="space-y-2">
        {metrics.map(({ label, value, icon: Icon, tooltip }) => (
          <div key={label} className="group relative">
            <div className="flex items-center gap-2">
              <Icon className="w-3 h-3 text-slate-500" />
              <span className="text-xs text-slate-400 w-28">{label}</span>
              <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getConfidenceColor(value)} transition-all`}
                  style={{ width: `${value}%` }}
                />
              </div>
              <span className={`text-xs font-medium w-8 text-right ${getConfidenceTextColor(value)}`}>
                {value}%
              </span>
            </div>
            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-slate-900 rounded text-xs text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
              {tooltip}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConfidenceIndicator;
