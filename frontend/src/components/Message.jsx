import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SourceBadge from './SourceBadge';
import PipelineStepsPanel from './PipelineStepsPanel';
import { DirectAnswerSection, TableComponent } from './output';
import { User, Sparkles, ChevronDown, ChevronRight, Brain, Lightbulb, FileText, ExternalLink, CheckCircle, Search, BarChart3, Zap, Copy } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Parse message content to extract reasoning blocks and main content
 */
const parseMessageContent = (content) => {
  if (!content) return { thinking: null, conclusion: null, mainContent: '' };
  
  let thinking = null;
  let conclusion = null;
  let mainContent = content;
  
  // Try multiple patterns for thinking block
  // Pattern 1: :::thinking ... :::
  let thinkingMatch = content.match(/:::thinking\s*([\s\S]*?)\s*:::/);
  if (thinkingMatch) {
    thinking = thinkingMatch[1].trim();
    mainContent = mainContent.replace(thinkingMatch[0], '');
  } else {
    // Pattern 2: :::thinking ... (no closing, takes until next ::: or ## or end)
    thinkingMatch = content.match(/:::thinking\s*([\s\S]*?)(?=\n\n##|\n:::|\n\n\*\*[A-Z]|$)/);
    if (thinkingMatch) {
      thinking = thinkingMatch[1].trim();
      mainContent = mainContent.replace(/:::thinking\s*[\s\S]*?(?=\n\n##|\n:::|\n\n\*\*[A-Z]|$)/, '');
    }
  }
  
  // Try multiple patterns for conclusion block
  // Pattern 1: :::conclusion ... :::
  let conclusionMatch = mainContent.match(/:::conclusion\s*([\s\S]*?)\s*:::/);
  if (conclusionMatch) {
    conclusion = conclusionMatch[1].trim();
    mainContent = mainContent.replace(conclusionMatch[0], '');
  } else {
    // Pattern 2: :::conclusion ... (no closing)
    conclusionMatch = mainContent.match(/:::conclusion\s*([\s\S]*)$/);
    if (conclusionMatch) {
      conclusion = conclusionMatch[1].trim();
      mainContent = mainContent.replace(/:::conclusion\s*[\s\S]*$/, '');
    }
  }
  
  // Also look for markdown-style conclusion headers
  if (!conclusion) {
    const conclusionHeaders = [
      /\n##\s*Conclusi[oó]n\s*\n([\s\S]*)$/i,
      /\n\*\*Conclusi[oó]n:?\*\*\s*\n?([\s\S]*)$/i,
      /\nConclusion:?\s*\n([\s\S]*)$/i
    ];
    for (const pattern of conclusionHeaders) {
      const match = mainContent.match(pattern);
      if (match) {
        conclusion = match[1].trim();
        mainContent = mainContent.replace(pattern, '');
        break;
      }
    }
  }
  
  // Clean up any remaining ::: markers
  mainContent = mainContent.replace(/^:::thinking\s*/gm, '').replace(/^:::\s*$/gm, '').trim();
  
  return { thinking, conclusion, mainContent };
};

/**
 * Open CV PDF in new window
 */
const openCVPdf = (cvId) => {
  // Construct the PDF URL based on the API endpoint
  const baseUrl = window.location.origin.replace(':6001', ':8003');
  const pdfUrl = `${baseUrl}/api/cvs/${cvId}/pdf`;
  window.open(pdfUrl, '_blank');
};

/**
 * Custom link renderer for CV references
 */
const CVLink = ({ href, children }) => {
  // Check if it's a CV reference link (cv:ID format)
  if (href && href.startsWith('cv:')) {
    const cvId = href.replace('cv:', '');
    return (
      <button
        onClick={() => openCVPdf(cvId)}
        className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors font-medium text-sm border border-blue-200 dark:border-blue-800"
        title={`Ver CV: ${cvId}`}
      >
        <FileText className="w-3.5 h-3.5" />
        <span>{children}</span>
        <ExternalLink className="w-3 h-3 opacity-60" />
      </button>
    );
  }
  
  // Regular external link
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">
      {children}
    </a>
  );
};

/**
 * Parse reasoning content into structured steps
 */
const parseReasoningSteps = (content) => {
  if (!content) return [];
  
  const steps = [];
  const stepPatterns = [
    { pattern: /##?\s*Step\s*1[:\s]*UNDERSTAND/i, icon: Search, title: 'Entender', color: 'blue' },
    { pattern: /##?\s*Step\s*2[:\s]*INVENTORY/i, icon: BarChart3, title: 'Inventario', color: 'green' },
    { pattern: /##?\s*Step\s*3[:\s]*ANALYZE/i, icon: Zap, title: 'Análisis', color: 'yellow' },
    { pattern: /##?\s*Step\s*4[:\s]*SELF-?CHECK/i, icon: CheckCircle, title: 'Verificación', color: 'orange' },
    { pattern: /##?\s*Step\s*5[:\s]*SYNTHESIZE/i, icon: Lightbulb, title: 'Síntesis', color: 'purple' },
  ];
  
  // Find all step positions
  const stepPositions = [];
  for (const step of stepPatterns) {
    const match = content.match(step.pattern);
    if (match) {
      stepPositions.push({
        ...step,
        index: match.index,
        fullMatch: match[0]
      });
    }
  }
  
  // Sort by position
  stepPositions.sort((a, b) => a.index - b.index);
  
  // Extract content for each step
  for (let i = 0; i < stepPositions.length; i++) {
    const current = stepPositions[i];
    const next = stepPositions[i + 1];
    const startIdx = current.index + current.fullMatch.length;
    const endIdx = next ? next.index : content.length;
    const stepContent = content.slice(startIdx, endIdx).trim();
    
    if (stepContent) {
      steps.push({
        icon: current.icon,
        title: current.title,
        color: current.color,
        content: stepContent
      });
    }
  }
  
  // If no structured steps found, return as single block
  if (steps.length === 0 && content.trim()) {
    return [{ icon: Brain, title: 'Análisis', color: 'purple', content: content.trim() }];
  }
  
  return steps;
};

/**
 * Thinking/Reasoning Panel Component with structured steps
 */
const ReasoningPanel = ({ content, isExpanded, onToggle }) => {
  const { t } = useLanguage();
  
  if (!content) return null;
  
  const steps = useMemo(() => parseReasoningSteps(content), [content]);
  
  const colorClasses = {
    blue: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800',
    green: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
    orange: 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-800',
    purple: 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  };
  
  return (
    <div className="mb-4 rounded-xl border border-purple-200 dark:border-purple-800 overflow-hidden bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-2 hover:bg-purple-100/50 dark:hover:bg-purple-900/30 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-purple-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-purple-500" />
        )}
        <Brain className="w-4 h-4 text-purple-500" />
        <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
          {t('reasoning') || 'Proceso de Razonamiento'}
        </span>
        <span className="ml-2 px-2 py-0.5 text-xs bg-purple-200 dark:bg-purple-800 text-purple-700 dark:text-purple-300 rounded-full">
          {steps.length} {steps.length === 1 ? 'paso' : 'pasos'}
        </span>
        <span className="ml-auto text-xs text-purple-500 dark:text-purple-400">
          {isExpanded ? (t('collapse') || 'Contraer') : (t('expand') || 'Expandir')}
        </span>
      </button>
      
      {isExpanded && (
        <div className="border-t border-purple-200 dark:border-purple-800 bg-white/50 dark:bg-gray-900/50">
          <div className="p-4 space-y-3">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div key={idx} className={`rounded-lg border p-3 ${colorClasses[step.color] || colorClasses.purple}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="w-4 h-4" />
                    <span className="font-semibold text-sm">{step.title}</span>
                  </div>
                  <div className="text-sm opacity-90 prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: CVLink,
                        p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 my-1">{children}</ul>,
                        li: ({ children }) => <li className="text-sm">{children}</li>,
                      }}
                    >
                      {step.content}
                    </ReactMarkdown>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Conclusion Panel Component
 */
const ConclusionPanel = ({ content }) => {
  const { t } = useLanguage();
  
  if (!content) return null;
  
  return (
    <div className="mt-4 p-4 rounded-xl border-2 border-green-200 dark:border-green-800 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20">
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb className="w-5 h-5 text-green-600 dark:text-green-400" />
        <span className="font-semibold text-green-800 dark:text-green-300">
          {t('conclusion') || 'Conclusion'}
        </span>
      </div>
      <div className="prose prose-sm max-w-none dark:prose-invert prose-green">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: CVLink,
            p: ({ children }) => <p className="text-green-900 dark:text-green-100 mb-2 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="text-green-800 dark:text-green-200">{children}</strong>,
            ul: ({ children }) => <ul className="list-disc list-inside space-y-1 text-green-900 dark:text-green-100">{children}</ul>,
            li: ({ children }) => <li className="text-green-900 dark:text-green-100">{children}</li>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

/**
 * Main Message Component with Enhanced Markdown Rendering
 */
const Message = ({ message, onViewCV }) => {
  const { role, content, sources = [], pipeline_steps = [], structured_output } = message;
  const isUser = role === 'user';
  const { t, language } = useLanguage();
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);
  const [isPipelineExpanded, setIsPipelineExpanded] = useState(false);

  // Check if we have structured output (new modular format)
  const hasStructuredOutput = !isUser && structured_output;
  
  // DEBUG: Log structured output detection
  if (!isUser) {
    console.log('🔍 [Message] Structured output detection:', {
      hasStructuredOutput,
      structured_output_exists: !!structured_output,
      structured_output_keys: structured_output ? Object.keys(structured_output) : null,
      direct_answer: structured_output?.direct_answer?.substring(0, 50),
      table_exists: !!structured_output?.table_data,
      thinking_exists: !!structured_output?.thinking,
      conclusion_exists: !!structured_output?.conclusion
    });
  }

  // Parse message content for legacy messages (fallback)
  const { thinking, conclusion, mainContent } = useMemo(() => 
    parseMessageContent(content), [content]
  );

  // Custom markdown components for tables and links
  const markdownComponents = {
    a: CVLink,
    table: ({ children }) => (
      <div className="overflow-x-auto my-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-gray-100 dark:bg-gray-800">{children}</thead>
    ),
    th: ({ children }) => (
      <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wider border-b-2 border-gray-300 dark:border-gray-600">
        {children}
      </th>
    ),
    tbody: ({ children }) => (
      <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">{children}</tbody>
    ),
    tr: ({ children }) => (
      <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">{children}</tr>
    ),
    td: ({ children }) => (
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 whitespace-normal">
        {children}
      </td>
    ),
    h1: ({ children }) => <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-4 mb-2">{children}</h1>,
    h2: ({ children }) => <h2 className="text-lg font-bold text-gray-900 dark:text-white mt-4 mb-2">{children}</h2>,
    h3: ({ children }) => <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100 mt-3 mb-2">{children}</h3>,
    p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
    ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-3 ml-2">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-3 ml-2">{children}</ol>,
    li: ({ children }) => <li className="text-gray-700 dark:text-gray-300">{children}</li>,
    strong: ({ children }) => <strong className="font-semibold text-gray-900 dark:text-white">{children}</strong>,
    em: ({ children }) => <em className="italic text-gray-700 dark:text-gray-300">{children}</em>,
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 pl-4 py-1 my-3 bg-blue-50 dark:bg-blue-900/20 rounded-r-lg italic text-gray-700 dark:text-gray-300">
        {children}
      </blockquote>
    ),
    code: ({ inline, children }) => 
      inline ? (
        <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono text-pink-600 dark:text-pink-400">
          {children}
        </code>
      ) : (
        <pre className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-x-auto my-3">
          <code className="text-sm font-mono text-gray-800 dark:text-gray-200">{children}</code>
        </pre>
      ),
    hr: () => <hr className="my-4 border-gray-200 dark:border-gray-700" />,
  };

  return (
    <div className={`message-fade-in ${isUser ? 'flex justify-end' : ''}`}>
      <div className={`flex gap-3 max-w-4xl ${isUser ? 'flex-row-reverse' : ''}`}>
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
            isUser 
              ? 'bg-blue-500' 
              : 'bg-gradient-to-br from-blue-500 to-purple-600'
          }`}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Sparkles className="w-5 h-5 text-white" />
          )}
        </div>

        <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
            {isUser ? t('you') : t('assistant')}
          </span>

          <div
            className={`mt-1 p-4 rounded-2xl ${
              isUser
                ? 'bg-blue-500 text-white rounded-tr-sm'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm'
            }`}
          >
            {/* Pipeline Steps Panel (expandable) - Shows real backend execution steps */}
            {!isUser && pipeline_steps && pipeline_steps.length > 0 && (
              <PipelineStepsPanel 
                steps={pipeline_steps}
                isExpanded={isPipelineExpanded}
                onToggle={() => setIsPipelineExpanded(!isPipelineExpanded)}
              />
            )}

            {/* STRUCTURED OUTPUT (New modular system) */}
            {hasStructuredOutput ? (
              <>
                {/* Thinking from structured output */}
                {structured_output.thinking && (
                  <ReasoningPanel 
                    content={structured_output.thinking}
                    isExpanded={isReasoningExpanded}
                    onToggle={() => setIsReasoningExpanded(!isReasoningExpanded)}
                  />
                )}

                {/* Direct Answer - Always exists */}
                <DirectAnswerSection 
                  content={structured_output.direct_answer}
                  cvLinkRenderer={CVLink}
                />

                {/* Table - Only if exists */}
                {structured_output.table_data && (
                  <TableComponent 
                    tableData={structured_output.table_data}
                    cvLinkRenderer={CVLink}
                  />
                )}

                {/* Conclusion from structured output */}
                {structured_output.conclusion && (
                  <ConclusionPanel content={structured_output.conclusion} />
                )}
              </>
            ) : (
              <>
                {/* LEGACY RENDERING (Old messages) */}
                {!isUser && thinking && (
                  <ReasoningPanel 
                    content={thinking}
                    isExpanded={isReasoningExpanded}
                    onToggle={() => setIsReasoningExpanded(!isReasoningExpanded)}
                  />
                )}

                <div className={`prose prose-sm max-w-none dark:prose-invert ${isUser ? 'prose-invert' : ''}`}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={isUser ? {} : markdownComponents}
                  >
                    {mainContent || content}
                  </ReactMarkdown>
                </div>

                {!isUser && conclusion && (
                  <ConclusionPanel content={conclusion} />
                )}
              </>
            )}

            {/* Sources */}
            {!isUser && sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                  📎 {t('sources')}:
                </p>
                <div className="flex flex-wrap gap-2">
                  {sources.map((source, index) => (
                    <SourceBadge
                      key={index}
                      filename={source.filename}
                      score={source.relevance || source.relevance_score}
                      cvId={source.cv_id}
                      onViewCV={onViewCV ? () => onViewCV(source.cv_id) : undefined}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Message;
