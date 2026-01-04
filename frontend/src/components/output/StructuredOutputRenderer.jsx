import { useState } from 'react';
import { 
  Brain, 
  FileText, 
  BarChart3, 
  Table2, 
  CheckCircle2,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * StructuredOutputRenderer - Visual structured output component
 * 
 * Renders LLM output in 5 distinct visual sections:
 * 1. Thinking Process (collapsible, purple)
 * 2. Direct Answer (yellow/gold border)
 * 3. Analysis (cyan border)
 * 4. Candidate Table (with colored match scores)
 * 5. Conclusion (green border)
 */

// Match Score color helper
const getScoreColor = (score) => {
  if (score >= 90) return 'bg-emerald-500 text-white';
  if (score >= 70) return 'bg-amber-500 text-white';
  return 'bg-gray-500 text-white';
};

const getScoreBgColor = (score) => {
  if (score >= 90) return 'bg-emerald-500/10 border-emerald-500/30';
  if (score >= 70) return 'bg-amber-500/10 border-amber-500/30';
  return 'bg-gray-500/10 border-gray-500/30';
};

// Section: Thinking Process (Collapsible)
const ThinkingSection = ({ content }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl overflow-hidden border border-purple-700/50 bg-purple-900/20">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-purple-800/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <span className="font-semibold text-purple-300">Thinking Process</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-5 h-5 text-purple-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-purple-400" />
        )}
      </button>
      {isOpen && (
        <div className="px-4 pb-4 border-t border-purple-700/30">
          <div className="mt-3 font-mono text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
            {content}
          </div>
        </div>
      )}
    </div>
  );
};

// Section: Direct Answer (Yellow/Gold border)
const DirectAnswerSection = ({ content, cvLinkRenderer }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border-l-4 border-amber-500 bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-amber-400" />
        <span className="font-semibold text-amber-400">Direct Answer</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: cvLinkRenderer,
            p: ({ children }) => (
              <p className="mb-2 text-gray-200 leading-relaxed">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-white">{children}</strong>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

// Section: Analysis (Cyan border)
const AnalysisSection = ({ content, cvLinkRenderer }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border-l-4 border-cyan-500 bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-cyan-400" />
        <span className="font-semibold text-cyan-400">Analysis</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: cvLinkRenderer,
            p: ({ children }) => (
              <p className="mb-2 text-gray-300 leading-relaxed">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-white">{children}</strong>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

// Section: Candidate Comparison Table (with colored match scores)
const CandidateTable = ({ tableData, onOpenCV }) => {
  if (!tableData || !tableData.rows || tableData.rows.length === 0) {
    return null;
  }
  
  const { title, headers, rows } = tableData;
  
  return (
    <div className="mb-4 rounded-xl bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Table2 className="w-5 h-5 text-slate-400" />
        <span className="font-semibold text-slate-300">{title || 'Candidate Comparison Table'}</span>
      </div>
      
      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-700/50 border-b border-slate-600">
              {headers && headers.map((header, idx) => (
                <th 
                  key={idx} 
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {rows.map((row, rowIdx) => (
              <tr 
                key={rowIdx} 
                className={`hover:bg-slate-700/30 transition-colors ${getScoreBgColor(row.match_score)}`}
              >
                {/* Candidate Name Column with CV Link */}
                <td className="px-4 py-3 text-sm text-slate-200 font-medium">
                  <div className="flex items-center gap-2">
                    {/* CV Document Icon Button */}
                    {row.cv_id && onOpenCV && (
                      <button
                        onClick={() => onOpenCV(row.cv_id, row.candidate_name)}
                        className="inline-flex items-center justify-center w-6 h-6 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 rounded transition-colors flex-shrink-0"
                        title={`View CV: ${row.candidate_name}`}
                      >
                        <FileText className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <span className="font-semibold">{row.candidate_name}</span>
                    {row.cv_id && (
                      <span className="text-xs text-slate-500">
                        ({row.cv_id})
                      </span>
                    )}
                  </div>
                </td>
                
                {/* Dynamic Columns */}
                {row.columns && Object.values(row.columns).map((value, colIdx) => (
                  <td key={colIdx} className="px-4 py-3 text-sm text-slate-300">
                    {value}
                  </td>
                ))}
                
                {/* Match Score Column */}
                <td className="px-4 py-3">
                  <span className={`inline-flex px-3 py-1 rounded-full text-sm font-semibold ${getScoreColor(row.match_score)}`}>
                    {row.match_score}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Section: Conclusion (Green border)
const ConclusionSection = ({ content, cvLinkRenderer }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border border-emerald-700/50 bg-emerald-900/20 p-4">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        <span className="font-semibold text-emerald-400">Conclusion</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: cvLinkRenderer,
            p: ({ children }) => (
              <p className="mb-2 text-gray-200 leading-relaxed">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-white">{children}</strong>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

// Main Component
const StructuredOutputRenderer = ({ structuredOutput, cvLinkRenderer, onOpenCV }) => {
  if (!structuredOutput) return null;
  
  const { thinking, direct_answer, analysis, table_data, conclusion } = structuredOutput;
  
  // Default CV link renderer if none provided
  const linkRenderer = cvLinkRenderer || (({ href, children }) => (
    <a 
      href={href} 
      className="text-blue-400 hover:text-blue-300 underline"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ));
  
  return (
    <div className="space-y-2">
      {/* 1. Thinking Process (collapsible) */}
      <ThinkingSection content={thinking} />
      
      {/* 2. Direct Answer */}
      <DirectAnswerSection content={direct_answer} cvLinkRenderer={linkRenderer} />
      
      {/* 3. Analysis */}
      <AnalysisSection content={analysis} cvLinkRenderer={linkRenderer} />
      
      {/* 4. Candidate Table */}
      <CandidateTable tableData={table_data} onOpenCV={onOpenCV} />
      
      {/* 5. Conclusion */}
      <ConclusionSection content={conclusion} cvLinkRenderer={linkRenderer} />
    </div>
  );
};

export default StructuredOutputRenderer;
