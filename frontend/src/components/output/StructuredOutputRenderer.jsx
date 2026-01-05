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
// cvMap: opcional, mapa de nombres normalizados a cv_ids para resolver "📄 Name" sin link explícito
const ContentWithCVLinks = ({ content, onOpenCV, cvMap = {} }) => {
  if (!content) return null;
  
  const contentStr = String(content);
  
  // DEBUG: Log cvMap to see what we have
  console.log('[CV_LINKS] cvMap received:', cvMap);
  console.log('[CV_LINKS] Content to process:', contentStr.substring(0, 200));
  
  // Múltiples patrones para capturar diferentes formatos de CV links
  // Soporta nombres con guiones (Mei-Ling), apóstrofes (O'Brien), etc.
  const patterns = [
    // Patrón principal: [📄](cv:xxx) **Name** - emoji en link, nombre fuera
    { regex: /\[📄\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\s*\*\*([^*]+)\*\*/g, hasId: true, nameGroup: 2, idGroup: 1 },
    // Alternativas
    { regex: /\*\*\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)\*\*/g, hasId: true },   // **[Name](cv:xxx)**
    { regex: /\[([^\]]+)\]\(cv:(cv_[a-zA-Z0-9_-]+)\)/g, hasId: true },            // [Name](cv:xxx) donde nombre no es emoji
    { regex: /📄\s*\*\*([^*]+)\*\*/g, hasId: false },                              // 📄 **Name**
    { regex: /📄\s*([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+)+)/g, hasId: false },  // 📄 Name Surname (con guiones)
  ];
  
  // Normalizar nombre para buscar en cvMap
  const normalizeName = (name) => name.toLowerCase().trim().replace(/\s+/g, ' ');
  
  // Extraer todos los CV refs con todos los patrones
  const refs = [];
  for (const pattern of patterns) {
    const { regex, hasId, nameGroup = 1, idGroup = 2 } = pattern;
    let match;
    while ((match = regex.exec(contentStr)) !== null) {
      // Extraer nombre y cvId según los grupos definidos
      const name = match[nameGroup]?.trim();
      let cvId = hasId ? match[idGroup] : null;
      
      // Si no tiene cv_id explícito, buscar en cvMap
      if (!cvId && cvMap) {
        const normalizedName = normalizeName(name);
        cvId = cvMap[normalizedName];
        console.log(`[CV_LINKS] Looking for "${name}" -> normalized: "${normalizedName}" -> cvId: ${cvId}`);
      }
      
      // Validar que el nombre no sea un emoji solo y que tengamos cv_id
      if (name && name !== '📄' && cvId) {
        console.log(`[CV_LINKS] ✓ Found valid CV ref: ${name} -> ${cvId}`);
        // Evitar duplicados en la misma posición
        const exists = refs.some(r => Math.abs(r.index - match.index) < 5);
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
                className="inline-flex items-center justify-center w-5 h-5 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 rounded transition-colors cursor-pointer"
                title={`View CV: ${part.name}`}
              >
                <FileText className="w-3 h-3" />
              </button>
              <strong className="font-semibold text-blue-300 hover:text-blue-200 cursor-pointer" onClick={(e) => {
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
const DirectAnswerSection = ({ content, onOpenCV, cvMap }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border-l-4 border-amber-500 bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-amber-400" />
        <span className="font-semibold text-amber-400">Direct Answer</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert text-gray-200">
        <ContentWithCVLinks content={content} onOpenCV={onOpenCV} cvMap={cvMap} />
      </div>
    </div>
  );
};

// Section: Analysis (Cyan border)
const AnalysisSection = ({ content, onOpenCV, cvMap }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border-l-4 border-cyan-500 bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-cyan-400" />
        <span className="font-semibold text-cyan-400">Analysis</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert text-gray-300">
        <ContentWithCVLinks content={content} onOpenCV={onOpenCV} cvMap={cvMap} />
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
                
                {/* Dynamic Columns - filter out internal fields starting with _ */}
                {row.columns && Object.entries(row.columns)
                  .filter(([key]) => !key.startsWith('_'))
                  .map(([key, value], colIdx) => (
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
const ConclusionSection = ({ content, onOpenCV, cvMap }) => {
  if (!content) return null;
  
  return (
    <div className="mb-4 rounded-xl border border-emerald-700/50 bg-emerald-900/20 p-4">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        <span className="font-semibold text-emerald-400">Conclusion</span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert text-gray-200">
        <ContentWithCVLinks content={content} onOpenCV={onOpenCV} cvMap={cvMap} />
      </div>
    </div>
  );
};

// Build cvMap from table data - maps normalized names to cv_ids
const buildCvMapFromTable = (tableData) => {
  const cvMap = {};
  console.log('[CV_MAP] Building cvMap from tableData:', tableData);
  
  if (!tableData?.rows) {
    console.log('[CV_MAP] No rows in tableData');
    return cvMap;
  }
  
  for (const row of tableData.rows) {
    console.log('[CV_MAP] Processing row:', row);
    if (row.candidate_name && row.cv_id) {
      // Normalize name: lowercase, trim, single spaces
      const normalizedName = row.candidate_name.toLowerCase().trim().replace(/\s+/g, ' ');
      cvMap[normalizedName] = row.cv_id;
      console.log(`[CV_MAP] Added: "${normalizedName}" -> "${row.cv_id}"`);
    }
  }
  console.log('[CV_MAP] Final cvMap:', cvMap);
  return cvMap;
};

// Main Component
const StructuredOutputRenderer = ({ structuredOutput, onOpenCV }) => {
  if (!structuredOutput) return null;
  
  const { thinking, direct_answer, analysis, table_data, conclusion } = structuredOutput;
  
  // Build cvMap from table to resolve "📄 Name" patterns without explicit cv_id
  const cvMap = buildCvMapFromTable(table_data);
  
  return (
    <div className="space-y-2">
      {/* 1. Thinking Process (collapsible) */}
      <ThinkingSection content={thinking} />
      
      {/* 2. Direct Answer - usa ContentWithCVLinks con cvMap */}
      <DirectAnswerSection content={direct_answer} onOpenCV={onOpenCV} cvMap={cvMap} />
      
      {/* 3. Analysis - usa ContentWithCVLinks con cvMap */}
      <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={cvMap} />
      
      {/* 4. Candidate Table - botones directos en JSX */}
      <CandidateTable tableData={table_data} onOpenCV={onOpenCV} />
      
      {/* 5. Conclusion - usa ContentWithCVLinks con cvMap */}
      <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={cvMap} />
    </div>
  );
};

export default StructuredOutputRenderer;
