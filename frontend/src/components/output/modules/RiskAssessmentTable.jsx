/**
 * RiskAssessmentTable - REUSABLE MODULE COMPONENT
 * 
 * This is a MODULE component that renders the 5-factor Risk Assessment TABLE.
 * 
 * ARCHITECTURE:
 * - This MODULE is used by multiple STRUCTURES:
 *   1. SingleCandidateProfile (embedded in full profile)
 *   2. RiskAssessmentProfile (standalone risk query)
 * 
 * The module ONLY renders the table. Structures combine this with other modules.
 * 
 * DO NOT duplicate this component. Import and use it in both contexts.
 */

import React from 'react';

/**
 * RiskAssessmentTable - Renders the 5-factor risk assessment table
 * 
 * @param {Object} props
 * @param {Array} props.data - Array of risk factors with {factor, status, details}
 * @param {string} props.className - Optional additional CSS classes
 */
const RiskAssessmentTable = ({ data, className = '' }) => {
  // Handle both array format and object with factors array
  const factors = Array.isArray(data) ? data : (data?.factors || []);
  
  if (!factors || factors.length === 0) {
    return null;
  }
  
  return (
    <div className={`risk-assessment-table ${className}`}>
      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-700/50 border-b border-slate-600">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Factor
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Details
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {factors.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-700/30 transition-colors">
                <td className="px-4 py-3 text-sm text-slate-200 font-medium">
                  {row.factor}
                </td>
                <td className="px-4 py-3 text-sm text-slate-300 text-center">
                  {row.status}
                </td>
                <td className="px-4 py-3 text-sm text-slate-400">
                  {row.details}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RiskAssessmentTable;
