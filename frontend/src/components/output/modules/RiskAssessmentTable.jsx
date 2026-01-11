/**
 * RiskAssessmentTable - REUSABLE MODULE COMPONENT
 * Enhanced with visual severity indicators and better UX
 */

import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, AlertCircle, XCircle, ChevronDown, ChevronUp, Shield } from 'lucide-react';

/**
 * RiskAssessmentTable - Renders the 5-factor risk assessment table with visual indicators
 */
const RiskAssessmentTable = ({ data, className = '' }) => {
  const [expandedRow, setExpandedRow] = useState(null);
  
  // Handle both array format and object with factors array
  const factors = Array.isArray(data) ? data : (data?.factors || []);
  
  if (!factors || factors.length === 0) {
    return null;
  }

  // Determine severity from status text
  const getSeverity = (status) => {
    const s = status?.toLowerCase() || '';
    if (s.includes('✅') || s.includes('green') || s.includes('clear') || s.includes('good') || s.includes('strong') || s.includes('excellent')) {
      return 'low';
    }
    if (s.includes('⚠️') || s.includes('🟡') || s.includes('yellow') || s.includes('some') || s.includes('minor') || s.includes('moderate')) {
      return 'medium';
    }
    if (s.includes('🔴') || s.includes('❌') || s.includes('red') || s.includes('concern') || s.includes('gap') || s.includes('risk') || s.includes('missing')) {
      return 'high';
    }
    // Default based on common patterns
    if (s.includes('no ') || s.includes('none') || s.includes('lack')) return 'high';
    if (s.includes('limited') || s.includes('partial')) return 'medium';
    return 'low';
  };

  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'high':
        return { 
          icon: XCircle, 
          color: 'text-red-400', 
          bg: 'bg-red-500/20', 
          border: 'border-red-500/30',
          indicator: '🔴',
          label: 'Risk'
        };
      case 'medium':
        return { 
          icon: AlertCircle, 
          color: 'text-amber-400', 
          bg: 'bg-amber-500/20', 
          border: 'border-amber-500/30',
          indicator: '🟡',
          label: 'Caution'
        };
      default:
        return { 
          icon: CheckCircle, 
          color: 'text-emerald-400', 
          bg: 'bg-emerald-500/20', 
          border: 'border-emerald-500/30',
          indicator: '🟢',
          label: 'Clear'
        };
    }
  };

  const getFactorIcon = (factor) => {
    const f = factor?.toLowerCase() || '';
    if (f.includes('employment') || f.includes('stability') || f.includes('tenure')) return '📅';
    if (f.includes('skill') || f.includes('technical')) return '💻';
    if (f.includes('career') || f.includes('progression') || f.includes('growth')) return '📈';
    if (f.includes('education') || f.includes('credential')) return '🎓';
    if (f.includes('gap') || f.includes('inconsisten')) return '⏳';
    return '📋';
  };

  // Calculate overall risk score
  const riskCounts = factors.reduce((acc, f) => {
    const sev = getSeverity(f.status);
    acc[sev] = (acc[sev] || 0) + 1;
    return acc;
  }, {});
  
  const overallRisk = riskCounts.high > 1 ? 'high' : riskCounts.high === 1 || riskCounts.medium > 2 ? 'medium' : 'low';
  const overallStyle = getSeverityStyle(overallRisk);

  return (
    <div className={`risk-assessment-table ${className}`}>
      {/* Header with overall risk */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-slate-400" />
          <span className="font-semibold text-slate-300">Risk Assessment</span>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${overallStyle.bg} ${overallStyle.border} border`}>
          <span className="text-sm">{overallStyle.indicator}</span>
          <span className={`text-sm font-medium ${overallStyle.color}`}>
            {overallRisk === 'high' ? 'High Risk' : overallRisk === 'medium' ? 'Some Concerns' : 'Low Risk'}
          </span>
        </div>
      </div>

      {/* Risk factors as cards */}
      <div className="space-y-2">
        {factors.map((row, idx) => {
          const severity = getSeverity(row.status);
          const style = getSeverityStyle(severity);
          const Icon = style.icon;
          const isExpanded = expandedRow === idx;

          return (
            <div 
              key={idx} 
              className={`rounded-lg border ${style.border} ${style.bg} transition-all`}
            >
              <button
                onClick={() => setExpandedRow(isExpanded ? null : idx)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/20 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-lg flex-shrink-0">{getFactorIcon(row.factor)}</span>
                  <div className="flex flex-col items-start min-w-0">
                    <span className="font-medium text-slate-200">{row.factor}</span>
                    {/* Show status text inline for better visibility */}
                    {row.status_text && (
                      <span className={`text-xs ${style.color} truncate max-w-[200px]`}>
                        {row.status_text}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="flex items-center gap-1.5">
                    <Icon className={`w-4 h-4 ${style.color}`} />
                    <span className={`text-sm font-medium ${style.color}`}>{style.label}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>
              
              {/* Always show details if available, expandable for more */}
              {(row.details || isExpanded) && (
                <div className={`px-4 pb-3 pt-1 ${isExpanded ? 'border-t border-slate-700/50' : ''}`}>
                  {row.details && (
                    <div className="text-sm text-slate-400">
                      {row.details}
                    </div>
                  )}
                  {isExpanded && row.status && (
                    <div className="text-xs text-slate-500 mt-2">
                      <span className="text-slate-600">Full status:</span> {row.status}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Risk summary footer */}
      <div className="mt-3 flex items-center justify-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          {riskCounts.low || 0} Clear
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500"></span>
          {riskCounts.medium || 0} Caution
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
          {riskCounts.high || 0} Risk
        </span>
      </div>
    </div>
  );
};

export default RiskAssessmentTable;
