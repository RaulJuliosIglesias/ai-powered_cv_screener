import { useState, useMemo } from 'react';
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
import SingleCandidateProfile from './SingleCandidateProfile';
import { 
  RiskAssessmentTable,
  RankingTable,
  MatchScoreCard,
  TeamCompositionView,
  TeamBuildView,
  VerificationResult,
  PoolSummary,
  SearchResultsTable,
  TopPickCard,
  WinnerCard,
  ComparisonMatrix,
  ConfidenceIndicator,
  QuickActions
} from './modules';
import { 
  isSingleCandidateResponse, 
  parseSingleCandidateProfile,
  isRiskAssessmentResponse,
  parseRiskAssessmentResponse
} from './singleCandidateParser';

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

// Helper function to detect if content contains markdown table
const containsMarkdownTable = (content) => {
  if (!content) return false;
  const lines = content.split('\n');
  let tableLineCount = 0;
  
  for (const line of lines) {
    const trimmedLine = line.trim();
    // Check for table row pattern: | cell1 | cell2 | cell3 |
    if (trimmedLine.includes('|') && trimmedLine.split('|').length >= 3) {
      tableLineCount++;
    }
    // Check for table separator pattern: |---|---|---|
    else if (trimmedLine.includes('|') && trimmedLine.includes('---')) {
      tableLineCount++;
    }
  }
  
  // Consider it a table if we have at least 2 lines with table syntax
  return tableLineCount >= 2;
};

// CV Reference Renderer - FUNCIÓN ÚNICA para renderizar contenido con CVs
// Detecta múltiples patrones de CV links y los renderiza como botón clickeable + nombre
// cvMap: opcional, mapa de nombres normalizados a cv_ids para resolver "📄 Name" sin link explícito
const ContentWithCVLinks = ({ content, onOpenCV, cvMap = {} }) => {
  if (!content) return null;
  
  const contentStr = String(content);
  
  // Check if content contains markdown table - if so, render as full markdown
  if (containsMarkdownTable(contentStr)) {
    return (
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            // Handle CV links in tables
            const cvMatch = href?.match(/^cv:(cv_[a-zA-Z0-9_-]+)$/);
            if (cvMatch && onOpenCV) {
              const cvId = cvMatch[1];
              const name = typeof children === 'string' ? children : children?.props?.children || 'CV';
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onOpenCV(cvId, name);
                  }}
                  className="inline-flex items-center gap-1 text-blue-300 hover:text-blue-200 transition-colors"
                  title={`View CV: ${name}`}
                >
                  <FileText className="w-3 h-3" />
                  {name}
                </button>
              );
            }
            return <a href={href} className="text-blue-300 hover:text-blue-200">{children}</a>;
          }
        }}
      >
        {contentStr}
      </ReactMarkdown>
    );
  }
  
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

// Section: Analysis (Cyan border) - ENHANCED for large content
const AnalysisSection = ({ content, onOpenCV, cvMap }) => {
  if (!content) return null;
  
  const contentStr = String(content);
  const contentLength = contentStr.length;
  const isLargeContent = contentLength > 500;
  
  // FIX: If content contains markdown tables, render with ReactMarkdown directly
  // This prevents tables from being broken apart by section parsing
  const hasMarkdownTable = containsMarkdownTable(contentStr);
  
  if (hasMarkdownTable) {
    return (
      <div className="mb-4 rounded-xl border-l-4 border-cyan-500 bg-slate-800/50 p-4">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          <span className="font-semibold text-cyan-400">Analysis</span>
        </div>
        <div className="prose prose-sm max-w-none dark:prose-invert text-gray-300 
          prose-table:border-collapse prose-table:w-full
          prose-th:bg-slate-700/50 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:text-cyan-300 prose-th:text-xs prose-th:font-semibold prose-th:border prose-th:border-slate-600
          prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-slate-700 prose-td:text-sm
          prose-tr:even:bg-slate-800/30">
          <ContentWithCVLinks content={content} onOpenCV={onOpenCV} cvMap={cvMap} />
        </div>
      </div>
    );
  }
  
  // Helper: Check if content is empty/placeholder
  const isEmptyContent = (text) => {
    if (!text) return true;
    const cleaned = text.replace(/^[-•*\s]+/, '').trim();
    return cleaned === '' || cleaned === '--' || cleaned === '-' || cleaned === 'N/A' || cleaned === 'n/a';
  };
  
  // Parse content to detect sections for large content
  const parseContentSections = (text) => {
    const sections = [];
    const lines = text.split('\n');
    let currentSection = { title: null, content: [] };
    
    for (const line of lines) {
      // Detect section headers (bold text followed by colon or standalone)
      const headerMatch = line.match(/^\*\*([^*:]+):?\*\*:?\s*$/);
      const colonHeaderMatch = line.match(/^([A-Z][^:]{2,30}):\s*$/);
      
      if (headerMatch || colonHeaderMatch) {
        // Save previous section if it has VALID content (not just "--")
        const hasValidContent = currentSection.content.some(c => !isEmptyContent(c));
        if (hasValidContent || (currentSection.title && currentSection.content.length > 0)) {
          // Filter out empty lines from content
          currentSection.content = currentSection.content.filter(c => !isEmptyContent(c));
          if (currentSection.content.length > 0) {
            sections.push(currentSection);
          }
        }
        currentSection = { 
          title: headerMatch ? headerMatch[1].trim() : colonHeaderMatch[1].trim(), 
          content: [] 
        };
      } else if (line.trim() && !isEmptyContent(line)) {
        // Only add non-empty, non-placeholder lines
        currentSection.content.push(line);
      }
    }
    
    // Push last section if it has valid content
    currentSection.content = currentSection.content.filter(c => !isEmptyContent(c));
    if (currentSection.content.length > 0) {
      sections.push(currentSection);
    }
    
    return sections;
  };
  
  // For large content, render with structured sections
  if (isLargeContent) {
    const sections = parseContentSections(contentStr);
    
    return (
      <div className="mb-4 rounded-xl border-l-4 border-cyan-500 bg-slate-800/50 p-4">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          <span className="font-semibold text-cyan-400">Analysis</span>
        </div>
        
        <div className="space-y-4">
          {sections.map((section, idx) => (
            <div key={idx} className={section.title ? "bg-slate-700/30 rounded-lg p-3" : ""}>
              {section.title && (
                <h4 className="text-sm font-semibold text-cyan-300 mb-2 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full"></span>
                  {section.title}
                </h4>
              )}
              <div className="text-sm text-gray-300 space-y-1">
                {section.content.map((line, lineIdx) => {
                  // Detect list items
                  if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
                    return (
                      <div key={lineIdx} className="flex items-start gap-2 pl-2">
                        <span className="text-cyan-400 mt-1">•</span>
                        <span><ContentWithCVLinks content={line.replace(/^[-•]\s*/, '')} onOpenCV={onOpenCV} cvMap={cvMap} /></span>
                      </div>
                    );
                  }
                  // Detect key-value pairs (Key: Value)
                  const kvMatch = line.match(/^([^:]{2,25}):\s*(.+)$/);
                  if (kvMatch && !line.includes('http')) {
                    return (
                      <div key={lineIdx} className="flex items-start gap-2">
                        <span className="text-gray-400 font-medium min-w-[120px]">{kvMatch[1]}:</span>
                        <span className="text-gray-200"><ContentWithCVLinks content={kvMatch[2]} onOpenCV={onOpenCV} cvMap={cvMap} /></span>
                      </div>
                    );
                  }
                  // Regular line
                  return (
                    <div key={lineIdx}>
                      <ContentWithCVLinks content={line} onOpenCV={onOpenCV} cvMap={cvMap} />
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }
  
  // For small content, keep simple rendering
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

// Section: Adaptive Table (Dynamic columns from backend)
const AdaptiveTable = ({ tableData, onOpenCV }) => {
  if (!tableData || !tableData.rows || tableData.rows.length === 0) {
    return null;
  }
  
  const { title, columns, rows, row_entity } = tableData;
  
  // Get column headers from columns array
  const headers = columns?.map(col => col.name || col.key) || [];
  
  return (
    <div className="mb-4 rounded-xl bg-slate-800/50 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Table2 className="w-5 h-5 text-blue-400" />
        <span className="font-semibold text-blue-300">{title || 'Results'}</span>
        <span className="text-xs text-slate-500 ml-2">({rows.length} {row_entity || 'items'})</span>
      </div>
      
      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-700/50 border-b border-slate-600">
              {headers.map((header, idx) => (
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
            {rows.map((row, rowIdx) => {
              // Extract cv_id from row for linking
              const cvId = row.cv_id || row.cells?.find(c => c.column === 'cv_id')?.value;
              const candidateName = row.cells?.find(c => 
                c.column === 'candidate_name' || c.column === 'Candidate'
              )?.value || `Row ${rowIdx + 1}`;
              
              return (
                <tr 
                  key={rowIdx} 
                  className="hover:bg-slate-700/30 transition-colors"
                >
                  {row.cells?.map((cell, cellIdx) => {
                    // Check if this is the candidate name column - add CV link button
                    const isNameCol = cell.column === 'candidate_name' || cell.column === 'Candidate';
                    
                    if (isNameCol && cvId && onOpenCV) {
                      return (
                        <td key={cellIdx} className="px-4 py-3 text-sm text-slate-200">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => onOpenCV(cvId, cell.value)}
                              className="inline-flex items-center justify-center w-6 h-6 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 rounded transition-colors flex-shrink-0"
                              title={`View CV: ${cell.value}`}
                            >
                              <FileText className="w-3.5 h-3.5" />
                            </button>
                            <span className="font-semibold">{cell.value}</span>
                          </div>
                        </td>
                      );
                    }
                    
                    // Check if this is a score column
                    const isScoreCol = cell.column === 'score' || cell.column === 'Score' || cell.column === 'match_score';
                    if (isScoreCol) {
                      const scoreValue = parseFloat(cell.value) || 0;
                      // Normalize score to percentage (0-100)
                      const displayScore = scoreValue > 1 ? Math.min(100, Math.round(scoreValue)) : Math.round(scoreValue * 100);
                      return (
                        <td key={cellIdx} className="px-4 py-3">
                          <span className={`inline-flex px-3 py-1 rounded-full text-sm font-semibold ${getScoreColor(displayScore)}`}>
                            {displayScore}%
                          </span>
                        </td>
                      );
                    }
                    
                    // Regular cell
                    return (
                      <td key={cellIdx} className="px-4 py-3 text-sm text-slate-300">
                        {cell.display || cell.value || '-'}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
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

// =============================================================================
// RISK ASSESSMENT STANDALONE COMPONENT
// =============================================================================

/**
 * RiskAssessmentProfile - Renders standalone Risk Assessment queries
 * Used when user asks "give me risks about X" without full profile
 */
const RiskAssessmentProfile = ({ 
  candidateName, 
  cvId, 
  riskAnalysis, 
  riskAssessment, 
  conclusion,
  onOpenCV 
}) => {
  return (
    <div className="space-y-4">
      {/* Header with candidate name */}
      <div className="rounded-xl bg-gradient-to-r from-orange-900/30 to-red-900/30 border border-orange-700/50 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-600/30 flex items-center justify-center">
            <span className="text-xl">🚩</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-orange-300">Risk Analysis</h2>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              {cvId && onOpenCV && (
                <button
                  onClick={() => onOpenCV(cvId, candidateName)}
                  className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 transition-colors"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>{candidateName}</span>
                </button>
              )}
              {!onOpenCV && <span>{candidateName}</span>}
            </div>
          </div>
        </div>
      </div>
      
      {/* Risk Analysis Text */}
      {riskAnalysis && (
        <div className="rounded-xl border-l-4 border-orange-500 bg-slate-800/50 p-4">
          <div className="prose prose-sm max-w-none dark:prose-invert text-gray-200">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {riskAnalysis}
            </ReactMarkdown>
          </div>
        </div>
      )}
      
      {/* Risk Assessment Table - USES SHARED MODULE */}
      {riskAssessment && (Array.isArray(riskAssessment) ? riskAssessment.length > 0 : riskAssessment.factors?.length > 0) && (
        <div className="rounded-xl bg-slate-800/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">⚠️</span>
            <span className="font-semibold text-orange-300">Risk Assessment</span>
          </div>
          
          {/* REUSABLE MODULE: Same component used in SingleCandidateProfile */}
          <RiskAssessmentTable data={riskAssessment} />
        </div>
      )}
      
      {/* Conclusion */}
      {conclusion && (
        <div className="rounded-xl border border-emerald-700/50 bg-emerald-900/20 p-4">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="font-semibold text-emerald-400">Assessment</span>
          </div>
          <div className="prose prose-sm max-w-none dark:prose-invert text-gray-200">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {conclusion}
            </ReactMarkdown>
          </div>
        </div>
      )}
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
  
  const { 
    thinking, direct_answer, analysis, table_data, conclusion, raw_content, 
    risk_assessment,
    // NEW: Structure-based routing from backend
    structure_type,
    single_candidate_data,
    risk_assessment_data: backend_risk_data
  } = structuredOutput;
  
  // ==========================================================================
  // PRIORITY 0: Use structure_type from backend for EXPLICIT routing
  // This is the new architecture - backend tells frontend which structure to use
  // ==========================================================================
  
  // DEBUG: Log structure_type to understand routing
  console.log('[STRUCTURED_OUTPUT] Received structure_type:', structure_type, 'Keys:', Object.keys(structuredOutput));
  
  if (structure_type === 'single_candidate' && single_candidate_data) {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=single_candidate');
    return (
      <div className="space-y-2">
        <ThinkingSection content={thinking} />
        <SingleCandidateProfile
          candidateName={single_candidate_data.candidate_name}
          cvId={single_candidate_data.cv_id}
          summary={single_candidate_data.summary}
          highlights={single_candidate_data.highlights}
          career={single_candidate_data.career}
          skills={single_candidate_data.skills}
          credentials={single_candidate_data.credentials}
          assessment={single_candidate_data.conclusion}
          riskAssessment={single_candidate_data.risk_table?.factors || []}
          onOpenCV={onOpenCV}
        />
      </div>
    );
  }
  
  if (structure_type === 'risk_assessment' && backend_risk_data) {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=risk_assessment');
    return (
      <div className="space-y-2">
        <ThinkingSection content={thinking} />
        <RiskAssessmentProfile
          candidateName={backend_risk_data.candidate_name}
          cvId={backend_risk_data.cv_id}
          riskAnalysis={backend_risk_data.risk_analysis}
          riskAssessment={backend_risk_data.risk_table?.factors || []}
          conclusion={backend_risk_data.assessment}
          onOpenCV={onOpenCV}
        />
      </div>
    );
  }
  
  // NEW STRUCTURE TYPES (Phase 3-6)
  
  if (structure_type === 'comparison') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=comparison');
    console.log('[STRUCTURED_OUTPUT] table_data:', table_data);
    
    // Build cvMap from table_data for CV link resolution
    const compCvMap = table_data?.rows?.reduce((acc, r) => {
      if (r.candidate_name && r.cv_id) {
        acc[r.candidate_name.toLowerCase().trim()] = r.cv_id;
      }
      return acc;
    }, {}) || {};
    
    // Determine winner (highest score candidate)
    const candidates = table_data?.rows || [];
    const sortedCandidates = [...candidates].sort((a, b) => (b.match_score || b.score || 0) - (a.match_score || a.score || 0));
    const winner = sortedCandidates[0];
    const runnerUp = sortedCandidates[1];
    
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        {direct_answer && <DirectAnswerSection content={direct_answer} onOpenCV={onOpenCV} cvMap={compCvMap} />}
        {/* Show comparison table - this is critical for comparison queries */}
        {table_data?.rows?.length > 0 && (
          <CandidateTable tableData={table_data} onOpenCV={onOpenCV} />
        )}
        {/* Show winner card if we have candidates */}
        {winner && candidates.length >= 2 && <WinnerCard winner={{...winner, score: winner.match_score || winner.score}} runnerUp={runnerUp ? {...runnerUp, score: runnerUp.match_score || runnerUp.score} : null} onOpenCV={onOpenCV} />}
        {analysis && <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={compCvMap} />}
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={compCvMap} />}
      </div>
    );
  }
  
  if (structure_type === 'search') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=search');
    // Build cvMap from results_table for CV link resolution
    const searchCvMap = structuredOutput.results_table?.results?.reduce((acc, r) => {
      if (r.candidate_name && r.cv_id) {
        acc[r.candidate_name.toLowerCase().trim()] = r.cv_id;
      }
      return acc;
    }, {}) || {};
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        {direct_answer && <DirectAnswerSection content={direct_answer} onOpenCV={onOpenCV} cvMap={searchCvMap} />}
        <SearchResultsTable data={structuredOutput.results_table} onOpenCV={onOpenCV} />
        {analysis && <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={searchCvMap} />}
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={searchCvMap} />}
      </div>
    );
  }
  
  if (structure_type === 'ranking') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=ranking');
    const rankCvMap = structuredOutput.ranking_table?.ranked?.reduce((acc, r) => {
      if (r.candidate_name && r.cv_id) {
        acc[r.candidate_name.toLowerCase().trim()] = r.cv_id;
      }
      return acc;
    }, {}) || {};
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        {structuredOutput.top_pick && <TopPickCard data={structuredOutput.top_pick} onOpenCV={onOpenCV} />}
        <RankingTable data={structuredOutput.ranking_table} onOpenCV={onOpenCV} />
        {analysis && <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={rankCvMap} />}
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={rankCvMap} />}
      </div>
    );
  }
  
  if (structure_type === 'job_match') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=job_match');
    const matchCvMap = structuredOutput.match_scores?.matches?.reduce((acc, m) => {
      if (m.candidate_name && m.cv_id) {
        acc[m.candidate_name.toLowerCase().trim()] = m.cv_id;
      }
      return acc;
    }, {}) || {};
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        {structuredOutput.best_match && <TopPickCard data={structuredOutput.best_match} onOpenCV={onOpenCV} />}
        <MatchScoreCard data={structuredOutput.match_scores} onOpenCV={onOpenCV} />
        {analysis && <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={matchCvMap} />}
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={matchCvMap} />}
      </div>
    );
  }
  
  if (structure_type === 'team_build') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=team_build (V2)');
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        <TeamBuildView data={structuredOutput} onOpenCV={onOpenCV} />
      </div>
    );
  }
  
  if (structure_type === 'verification') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=verification');
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        <VerificationResult data={structuredOutput} />
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} />}
      </div>
    );
  }
  
  if (structure_type === 'summary') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=summary');
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        <PoolSummary data={structuredOutput} />
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} />}
      </div>
    );
  }
  
  // ==========================================================================
  // ADAPTIVE STRUCTURE - Dynamic tables and analysis
  // ==========================================================================
  if (structure_type === 'adaptive') {
    console.log('[STRUCTURED_OUTPUT] ROUTING: structure_type=adaptive');
    console.log('[STRUCTURED_OUTPUT] adaptive data:', structuredOutput);
    
    // Build cvMap from dynamic_table for CV link resolution
    const adaptiveCvMap = structuredOutput.dynamic_table?.rows?.reduce((acc, r) => {
      const name = r.cells?.find(c => c.column === 'candidate_name' || c.column === 'Candidate')?.value;
      const cvId = r.cv_id || r.cells?.find(c => c.column === 'cv_id')?.value;
      if (name && cvId) {
        acc[name.toLowerCase().trim()] = cvId;
      }
      return acc;
    }, {}) || {};
    
    // Extract key findings as bullet points
    const keyFindings = structuredOutput.key_findings || [];
    
    return (
      <div className="space-y-3">
        <ThinkingSection content={thinking} />
        
        {/* Direct Answer - Primary response */}
        {direct_answer && <DirectAnswerSection content={direct_answer} onOpenCV={onOpenCV} cvMap={adaptiveCvMap} />}
        
        {/* Dynamic Table - Core output */}
        {structuredOutput.dynamic_table?.rows?.length > 0 && (
          <AdaptiveTable tableData={structuredOutput.dynamic_table} onOpenCV={onOpenCV} />
        )}
        
        {/* Analysis sections */}
        {analysis && <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={adaptiveCvMap} />}
        
        {/* Key Findings */}
        {keyFindings.length > 0 && (
          <div className="border-l-2 border-blue-500/50 pl-3 py-2">
            <h4 className="text-sm font-medium text-blue-300 mb-2">Key Findings</h4>
            <ul className="space-y-1">
              {keyFindings.map((finding, idx) => (
                <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-blue-400">•</span>
                  <ContentWithCVLinks content={finding} onOpenCV={onOpenCV} cvMap={adaptiveCvMap} />
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Conclusion */}
        {conclusion && <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={adaptiveCvMap} />}
      </div>
    );
  }
  
  // ==========================================================================
  // FALLBACK: Legacy detection for backwards compatibility
  // IMPORTANT: Only use fallback if backend didn't provide a known structure_type
  // ==========================================================================
  
  // Known structure types from backend - if we have one of these, DON'T use fallback
  const knownStructureTypes = ['single_candidate', 'risk_assessment', 'comparison', 'search', 'ranking', 'job_match', 'team_build', 'verification', 'summary', 'adaptive'];
  const hasKnownStructureType = structure_type && knownStructureTypes.includes(structure_type);
  
  // PRIORITY 1: Use Risk Assessment data from backend MODULE (reusable component)
  // BUT ONLY if we don't have a known structure_type (fallback for legacy messages)
  const riskAssessmentData = useMemo(() => {
    // SKIP FALLBACK if backend provided a known structure_type
    if (hasKnownStructureType) {
      console.log('[STRUCTURED_OUTPUT] Skipping fallback - using structure_type:', structure_type);
      return null;
    }
    
    // First check if backend provided risk_assessment data (from RiskTableModule)
    if (risk_assessment && risk_assessment.factors && risk_assessment.factors.length > 0) {
      console.log('[STRUCTURED_OUTPUT] Using Risk Assessment from backend module:', risk_assessment.candidate_name);
      return {
        candidateName: risk_assessment.candidate_name || 'Unknown',
        cvId: risk_assessment.cv_id || '',
        riskAnalysis: risk_assessment.analysis_text || '',
        riskAssessment: risk_assessment.factors.map(f => ({
          factor: f.factor,
          status: f.status,
          details: f.details
        })),
        conclusion: risk_assessment.analysis_text || ''
      };
    }
    
    // Fallback: Parse from raw_content if backend didn't provide structured data
    if (raw_content && isRiskAssessmentResponse(raw_content)) {
      const parsed = parseRiskAssessmentResponse(raw_content);
      if (parsed) {
        console.log('[STRUCTURED_OUTPUT] Fallback: Parsed Risk Assessment from raw_content:', parsed.candidateName);
        return parsed;
      }
    }
    return null;
  }, [risk_assessment, raw_content, hasKnownStructureType, structure_type]);
  
  // PRIORITY 2: Detect single candidate profile response
  // ALSO skip if we have a known structure_type from backend
  const singleCandidateData = useMemo(() => {
    // Skip if backend provided a known structure_type
    if (hasKnownStructureType) return null;
    
    // Skip if we already detected Risk Assessment standalone query
    if (riskAssessmentData) return null;
    
    // Check raw_content for single candidate indicators
    if (raw_content && isSingleCandidateResponse(raw_content)) {
      const parsed = parseSingleCandidateProfile(raw_content);
      if (parsed && parsed.candidateName !== 'Unknown Candidate') {
        console.log('[STRUCTURED_OUTPUT] Detected single candidate response:', parsed.candidateName);
        
        // IMPORTANT: Use risk_assessment from backend MODULE if available
        // This ensures the SAME module is used for embedded Risk Assessment
        if (risk_assessment && risk_assessment.factors && risk_assessment.factors.length > 0) {
          parsed.riskAssessment = risk_assessment.factors.map(f => ({
            factor: f.factor,
            status: f.status,
            details: f.details
          }));
          console.log('[STRUCTURED_OUTPUT] Injected risk_assessment from backend module into SingleCandidateProfile');
        }
        
        return parsed;
      }
    }
    
    // Fallback: Check if table has only 1 row (legacy detection)
    if (table_data?.rows?.length === 1) {
      console.log('[STRUCTURED_OUTPUT] Single candidate detected via table (1 row)');
      return null; // Will use standard rendering but hide comparison table
    }
    
    return null;
  }, [raw_content, table_data, riskAssessmentData, risk_assessment]);
  
  // Build cvMap from table to resolve "📄 Name" patterns without explicit cv_id
  const cvMap = buildCvMapFromTable(table_data);
  
  // RENDER: Risk Assessment standalone profile
  if (riskAssessmentData) {
    return (
      <div className="space-y-2">
        {/* 1. Thinking Process (collapsible) */}
        <ThinkingSection content={thinking} />
        
        {/* 2. Risk Assessment Profile - specialized for risk queries */}
        <RiskAssessmentProfile
          candidateName={riskAssessmentData.candidateName}
          cvId={riskAssessmentData.cvId}
          riskAnalysis={riskAssessmentData.riskAnalysis}
          riskAssessment={riskAssessmentData.riskAssessment}
          conclusion={riskAssessmentData.conclusion}
          onOpenCV={onOpenCV}
        />
      </div>
    );
  }
  
  // RENDER: Single candidate with full profile
  if (singleCandidateData) {
    return (
      <div className="space-y-2">
        {/* 1. Thinking Process (collapsible) - still show for single candidate */}
        <ThinkingSection content={thinking} />
        
        {/* 2. Single Candidate Profile - replaces Direct Answer, Analysis, and Table */}
        <SingleCandidateProfile
          candidateName={singleCandidateData.candidateName}
          cvId={singleCandidateData.cvId}
          summary={singleCandidateData.summary}
          highlights={singleCandidateData.highlights}
          career={singleCandidateData.career}
          skills={singleCandidateData.skills}
          credentials={singleCandidateData.credentials}
          assessment={singleCandidateData.assessment}
          strengths={singleCandidateData.strengths}
          riskAssessment={singleCandidateData.riskAssessment}
          onOpenCV={onOpenCV}
        />
      </div>
    );
  }
  
  // RENDER: Standard multi-candidate response
  // Detect if we should hide comparison table (single candidate via table detection)
  const isSingleCandidateTable = table_data?.rows?.length === 1;
  
  return (
    <div className="space-y-2">
      {/* 1. Thinking Process (collapsible) */}
      <ThinkingSection content={thinking} />
      
      {/* 2. Direct Answer - usa ContentWithCVLinks con cvMap */}
      <DirectAnswerSection content={direct_answer} onOpenCV={onOpenCV} cvMap={cvMap} />
      
      {/* 3. Analysis - usa ContentWithCVLinks con cvMap */}
      <AnalysisSection content={analysis} onOpenCV={onOpenCV} cvMap={cvMap} />
      
      {/* 4. Candidate Table - only show for multiple candidates */}
      {!isSingleCandidateTable && (
        <CandidateTable tableData={table_data} onOpenCV={onOpenCV} />
      )}
      
      {/* 5. Conclusion - usa ContentWithCVLinks con cvMap */}
      <ConclusionSection content={conclusion} onOpenCV={onOpenCV} cvMap={cvMap} />
    </div>
  );
};

export default StructuredOutputRenderer;
