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

// CV Reference Renderer - FUNCIÓN ÚNICA para renderizar contenido con CVs
// Detecta múltiples patrones de CV links y los renderiza como botón clickeable + nombre
const ContentWithCVLinks = ({ content, onOpenCV }) => {
  if (!content) return null;
  
  const contentStr = String(content);
  
  // Múltiples patrones para capturar diferentes formatos de CV links
  // cv_id puede tener letras, números y guiones
  const patterns = [
    /\*\*\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*/g,  // **[Name](cv:xxx)**
    /\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)/g,          // [Name](cv:xxx)
  ];
  
  // Extraer todos los CV refs con todos los patrones
  const refs = [];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(contentStr)) !== null) {
      const name = match[1].trim();
      const cvId = match[2];
      
      // Validar que el nombre no sea un emoji solo
      if (name && name !== '📄' && cvId) {
        // Evitar duplicados en la misma posición
        const exists = refs.some(r => r.index === match.index);
        if (!exists) {
          refs.push({ 
            index: match.index, 
            length: match[0].length, 
            name, 
            cvId 
          });
        }
      }
    }
  }
  
  // Si no hay CVs válidos, renderizar todo como markdown
  if (refs.length === 0) {
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    );
  }
  
  // Ordenar por posición y eliminar solapamientos
  refs.sort((a, b) => a.index - b.index);
  const uniqueRefs = [];
  let lastEnd = 0;
  for (const ref of refs) {
    if (ref.index >= lastEnd) {
      uniqueRefs.push(ref);
      lastEnd = ref.index + ref.length;
    }
  }
  
  // Dividir el contenido en partes
  const parts = [];
  let lastIndex = 0;
  
  for (const ref of uniqueRefs) {
    // Añadir texto antes del match
    if (ref.index > lastIndex) {
      parts.push({
        type: 'text',
        content: contentStr.slice(lastIndex, ref.index)
      });
    }
    
    // Añadir el CV reference
    parts.push({
      type: 'cv',
      cvId: ref.cvId,
      name: ref.name
    });
    
    lastIndex = ref.index + ref.length;
  }
  
  // Añadir texto restante
  if (lastIndex < contentStr.length) {
    parts.push({
      type: 'text',
      content: contentStr.slice(lastIndex)
    });
  }
  
  // Renderizar partes mixtas - INLINE sin saltos de línea
  return (
    <span className="inline">
      {parts.map((part, idx) => {
        if (part.type === 'cv') {
          return (
            <span key={idx} className="inline-flex items-center gap-1 mx-0.5">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (onOpenCV) onOpenCV(part.cvId, part.name);
                }}
                className="inline-flex items-center justify-center w-5 h-5 bg-emerald-600/30 text-emerald-400 hover:bg-emerald-600/50 rounded transition-colors cursor-pointer"
                title={`View CV: ${part.name}`}
              >
                <FileText className="w-3 h-3" />
              </button>
              <strong className="font-semibold text-emerald-300 hover:text-emerald-200 cursor-pointer" onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (onOpenCV) onOpenCV(part.cvId, part.name);
              }}>{part.name}</strong>
            </span>
          );
        } else {
          // Renderizar texto sin crear bloques <p> - usar span inline
          return (
            <span key={idx} className="inline">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  // Convertir p a span para evitar saltos de línea
                  p: ({ children }) => <span>{children} </span>,
                }}
              >
                {part.content}
              </ReactMarkdown>
            </span>
          );
        }
      })}
    </span>
  );
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
const DirectAnswerSection = ({ content, onOpenCV }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border-l-4 border-amber-500 bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-amber-400" />
        <span className="font-semibold text-amber-400">Direct Answer</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert text-gray-200">
        <ContentWithCVLinks content={content} onOpenCV={onOpenCV} />
      </div>
    </div>
  );
};

// Section: Analysis (Cyan border)
const AnalysisSection = ({ content, onOpenCV }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border-l-4 border-cyan-500 bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-cyan-400" />
        <span className="font-semibold text-cyan-400">Analysis</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert text-gray-300">
        <ContentWithCVLinks content={content} onOpenCV={onOpenCV} />
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
const ConclusionSection = ({ content, onOpenCV }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border border-emerald-700/50 bg-emerald-900/20 p-4">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        <span className="font-semibold text-emerald-400">Conclusion</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert text-gray-200">
        <ContentWithCVLinks content={content} onOpenCV={onOpenCV} />
      </div>
    </div>
  );
};

// Main Component
const StructuredOutputRenderer = ({ structuredOutput, onOpenCV }) => {
  if (!structuredOutput) return null;
  
  const { thinking, direct_answer, analysis, table_data, conclusion } = structuredOutput;
  
  return (
    <div className="space-y-2">
      {/* 1. Thinking Process (collapsible) */}
      <ThinkingSection content={thinking} />
      
      {/* 2. Direct Answer - usa ContentWithCVLinks */}
      <DirectAnswerSection content={direct_answer} onOpenCV={onOpenCV} />
      
      {/* 3. Analysis - usa ContentWithCVLinks */}
      <AnalysisSection content={analysis} onOpenCV={onOpenCV} />
      
      {/* 4. Candidate Table - botones directos en JSX */}
      <CandidateTable tableData={table_data} onOpenCV={onOpenCV} />
      
      {/* 5. Conclusion - usa ContentWithCVLinks */}
      <ConclusionSection content={conclusion} onOpenCV={onOpenCV} />
    </div>
  );
};

export default StructuredOutputRenderer;
