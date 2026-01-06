import { FileText, User, Briefcase, GraduationCap, Award, Wrench, Target, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { RiskAssessmentTable } from './modules';

/**
 * SingleCandidateProfile - Renders a single candidate's profile in a visually appealing format
 * 
 * This component is used when the query is about ONE specific candidate.
 * It displays highlights, career trajectory, skills, and credentials in a card-based layout.
 * 
 * Key differences from multi-candidate table:
 * - No comparison scores
 * - Focus on highlights and key information
 * - More detailed breakdown of the candidate's profile
 * - Visual sections with icons
 */

const CVButton = ({ cvId, name, onOpenCV }) => {
  if (!cvId || !onOpenCV) return null;
  
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onOpenCV(cvId, name);
      }}
      className="inline-flex items-center justify-center w-6 h-6 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 rounded transition-colors cursor-pointer ml-2"
      title={`View CV: ${name}`}
    >
      <FileText className="w-4 h-4" />
    </button>
  );
};

const SectionHeader = ({ icon: Icon, title, color = "cyan" }) => {
  const colorClasses = {
    cyan: "text-cyan-400 border-cyan-500/30",
    amber: "text-amber-400 border-amber-500/30",
    emerald: "text-emerald-400 border-emerald-500/30",
    purple: "text-purple-400 border-purple-500/30",
    blue: "text-blue-400 border-blue-500/30",
  };
  
  return (
    <div className={`flex items-center gap-2 pb-2 mb-3 border-b ${colorClasses[color]}`}>
      <Icon className={`w-5 h-5 ${colorClasses[color].split(' ')[0]}`} />
      <h3 className={`font-semibold ${colorClasses[color].split(' ')[0]}`}>{title}</h3>
    </div>
  );
};

const HighlightsTable = ({ content }) => {
  if (!content) return null;
  
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full">
        <tbody className="divide-y divide-slate-700/50">
          {content.map((row, idx) => (
            <tr key={idx} className="hover:bg-slate-700/20 transition-colors">
              <td className="px-4 py-3 text-sm font-medium text-slate-300 w-1/3 bg-slate-800/30">
                {row.category}
              </td>
              <td className="px-4 py-3 text-sm text-slate-200">
                {row.value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const SkillsTable = ({ content }) => {
  if (!content || content.length === 0) return null;
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {content.map((skill, idx) => (
        <div 
          key={idx} 
          className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-lg border border-slate-700/50"
        >
          <div className="flex-shrink-0 w-8 h-8 bg-cyan-500/20 rounded-full flex items-center justify-center">
            <Wrench className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <div className="font-medium text-slate-200 text-sm">{skill.area}</div>
            <div className="text-xs text-slate-400 mt-0.5">{skill.details}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

const CareerItem = ({ title, company, period, achievement }) => (
  <div className="relative pl-6 pb-4 border-l-2 border-slate-600 last:border-l-0 last:pb-0">
    <div className="absolute -left-[9px] top-0 w-4 h-4 bg-slate-700 rounded-full border-2 border-cyan-500"></div>
    <div className="flex flex-wrap items-baseline gap-2 mb-1">
      <span className="font-semibold text-slate-200">{title}</span>
      <span className="text-slate-400">—</span>
      <span className="text-cyan-400 italic">{company}</span>
      {period && <span className="text-xs text-slate-500">({period})</span>}
    </div>
    {achievement && (
      <div className="text-sm text-slate-400 flex items-start gap-2">
        <span className="text-cyan-500">→</span>
        <span>{achievement}</span>
      </div>
    )}
  </div>
);

const CredentialsList = ({ credentials }) => {
  if (!credentials || credentials.length === 0) return null;
  
  return (
    <div className="space-y-2">
      {credentials.map((cred, idx) => (
        <div 
          key={idx}
          className="flex items-center gap-3 p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20"
        >
          <Award className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span className="text-sm text-slate-200">{cred}</span>
        </div>
      ))}
    </div>
  );
};

/**
 * Risk Assessment Table - USES SHARED MODULE
 * 
 * The RiskAssessmentTable component is imported from ./modules/RiskAssessmentTable.jsx
 * This ensures the SAME component is used in both:
 * - SingleCandidateProfile (embedded, full profile view)
 * - RiskAssessmentProfile (standalone, risk-focused view)
 */

const SingleCandidateProfile = ({ 
  candidateName, 
  cvId, 
  summary, 
  highlights, 
  career, 
  skills, 
  credentials,
  assessment,
  strengths,
  riskAssessment,
  onOpenCV 
}) => {
  return (
    <div className="space-y-4">
      {/* Header with candidate name */}
      <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-blue-900/30 to-slate-800/50 rounded-xl border border-blue-500/30">
        <div className="w-12 h-12 bg-blue-600/30 rounded-full flex items-center justify-center">
          <User className="w-6 h-6 text-blue-400" />
        </div>
        <div className="flex-1">
          <div className="flex items-center">
            <h2 className="text-xl font-bold text-white">{candidateName}</h2>
            <CVButton cvId={cvId} name={candidateName} onOpenCV={onOpenCV} />
          </div>
          {cvId && <span className="text-xs text-slate-500">{cvId}</span>}
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="prose prose-sm max-w-none dark:prose-invert text-slate-300">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Highlights Table */}
      {highlights && highlights.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-amber-500/30">
          <SectionHeader icon={Target} title="Candidate Highlights" color="amber" />
          <HighlightsTable content={highlights} />
        </div>
      )}

      {/* Career Trajectory */}
      {career && career.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-cyan-500/30">
          <SectionHeader icon={Briefcase} title="Career Trajectory" color="cyan" />
          <div className="mt-4">
            {career.map((item, idx) => (
              <CareerItem 
                key={idx}
                title={item.title}
                company={item.company}
                period={item.period}
                achievement={item.achievement}
              />
            ))}
          </div>
        </div>
      )}

      {/* Skills */}
      {skills && skills.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-purple-500/30">
          <SectionHeader icon={Wrench} title="Skills Snapshot" color="purple" />
          <SkillsTable content={skills} />
        </div>
      )}

      {/* Credentials */}
      {credentials && credentials.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-emerald-500/30">
          <SectionHeader icon={GraduationCap} title="Credentials" color="emerald" />
          <CredentialsList credentials={credentials} />
        </div>
      )}

      {/* Assessment & Strengths (from conclusion) */}
      {(assessment || strengths) && (
        <div className="p-4 bg-emerald-900/20 rounded-xl border border-emerald-500/30">
          <SectionHeader icon={Award} title="Assessment" color="emerald" />
          {assessment && (
            <div className="mb-3 prose prose-sm max-w-none dark:prose-invert text-slate-200">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{assessment}</ReactMarkdown>
            </div>
          )}
          {strengths && strengths.length > 0 && (
            <div className="mt-3">
              <div className="text-sm font-medium text-emerald-400 mb-2">Key Strengths:</div>
              <ul className="space-y-1">
                {strengths.map((strength, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-emerald-400 mt-0.5">✓</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Risk Assessment - MANDATORY for single candidate */}
      {riskAssessment && riskAssessment.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-orange-500/30">
          <SectionHeader icon={AlertTriangle} title="Risk Assessment" color="amber" />
          <RiskAssessmentTable data={riskAssessment} />
        </div>
      )}
    </div>
  );
};

export default SingleCandidateProfile;
