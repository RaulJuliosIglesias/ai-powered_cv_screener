import React, { useState, useEffect, useRef, memo, useCallback } from 'react';
import { Brain, Search, FileText, Sparkles, Check, Loader, ChevronDown, ChevronUp, Zap, Users, Target } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Typewriter effect hook - shows text character by character
 */
export const useTypewriter = (text, speed = 3, enabled = true) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  
  useEffect(() => {
    if (!enabled || !text) {
      setDisplayedText(text || '');
      setIsComplete(true);
      return;
    }
    
    setDisplayedText('');
    setIsComplete(false);
    let i = 0;
    
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayedText(text.slice(0, i + 1));
        i++;
      } else {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, speed);
    
    return () => clearInterval(interval);
  }, [text, speed, enabled]);
  
  return { displayedText, isComplete };
};

/**
 * Dynamic typing indicator with phase awareness
 */
export const TypingIndicator = memo(({ phase, details, progress }) => {
  const { language } = useLanguage();
  
  const phases = {
    query_understanding: {
      icon: Brain,
      labelEs: 'Entendiendo tu consulta',
      labelEn: 'Understanding your query',
      color: 'text-purple-500'
    },
    multi_query: {
      icon: Brain,
      labelEs: 'Generando variaciones',
      labelEn: 'Generating variations',
      color: 'text-purple-500'
    },
    guardrail: {
      icon: Brain,
      labelEs: 'Validando consulta',
      labelEn: 'Validating query',
      color: 'text-purple-500'
    },
    embedding: {
      icon: Zap,
      labelEs: 'Preparando búsqueda',
      labelEn: 'Preparing search',
      color: 'text-yellow-500'
    },
    retrieval: {
      icon: Search,
      labelEs: 'Buscando candidatos',
      labelEn: 'Searching candidates',
      color: 'text-blue-500'
    },
    reranking: {
      icon: Target,
      labelEs: 'Ordenando resultados',
      labelEn: 'Ranking results',
      color: 'text-orange-500'
    },
    reasoning: {
      icon: Brain,
      labelEs: 'Analizando perfiles',
      labelEn: 'Analyzing profiles',
      color: 'text-indigo-500'
    },
    generation: {
      icon: Sparkles,
      labelEs: 'Generando respuesta',
      labelEn: 'Generating response',
      color: 'text-emerald-500'
    },
    verification: {
      icon: Check,
      labelEs: 'Verificando información',
      labelEn: 'Verifying information',
      color: 'text-teal-500'
    },
    refinement: {
      icon: Sparkles,
      labelEs: 'Estructurando respuesta',
      labelEn: 'Structuring response',
      color: 'text-pink-500'
    }
  };
  
  const currentPhase = phases[phase] || phases.query_understanding;
  const Icon = currentPhase.icon;
  const label = language === 'es' ? currentPhase.labelEs : currentPhase.labelEn;
  
  // Determine if we're in a retry/fallback state
  const isRetrying = progress === 'retrying' || progress === 'trying_fallback' || progress === 'timeout';
  const isFallback = progress === 'fallback' || progress === 'trying_fallback';
  
  return (
    <div className={`flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border ${
      isRetrying ? 'border-amber-200 dark:border-amber-700' : 
      isFallback ? 'border-orange-200 dark:border-orange-700' : 
      'border-gray-100 dark:border-gray-700'
    } animate-pulse-soft`}>
      <div className={`p-2 rounded-xl ${
        isRetrying ? 'bg-amber-100 dark:bg-amber-900/30' : 
        isFallback ? 'bg-orange-100 dark:bg-orange-900/30' : 
        'bg-gray-100 dark:bg-gray-700'
      } ${isRetrying ? 'text-amber-500' : isFallback ? 'text-orange-500' : currentPhase.color}`}>
        <Icon className="w-5 h-5 animate-pulse" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</span>
          {isRetrying && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded">
              RETRY
            </span>
          )}
          {isFallback && !isRetrying && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded">
              FALLBACK
            </span>
          )}
          <div className="flex gap-px items-end">
            <span className="w-[3px] h-[3px] bg-current opacity-60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-[3px] h-[3px] bg-current opacity-60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-[3px] h-[3px] bg-current opacity-60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
        {details && (
          <p className={`text-xs mt-0.5 ${
            isRetrying ? 'text-amber-600 dark:text-amber-400' : 
            isFallback ? 'text-orange-600 dark:text-orange-400' : 
            'text-gray-500 dark:text-gray-400'
          }`}>{details}</p>
        )}
      </div>
    </div>
  );
});

TypingIndicator.displayName = 'TypingIndicator';

/**
 * Mini pipeline progress shown inline in message
 * Shows only enabled steps based on pipeline configuration
 */
export const InlinePipelineProgress = memo(({ steps, currentStep, enabledSteps }) => {
  const { language } = useLanguage();
  
  const stepConfig = {
    query_understanding: { label: 'Query', icon: '🧠' },
    embedding: { label: 'Embed', icon: '⚡' },
    retrieval: { label: 'Search', icon: '🔍' },
    reranking: { label: 'Rank', icon: '📊' },
    reasoning: { label: 'Think', icon: '💭' },
    generation: { label: 'Write', icon: '✍️' },
    verification: { label: 'Verify', icon: '✓' },
    refinement: { label: 'Format', icon: '📋' }
  };
  
  // Default all steps, filter by enabled if provided
  const allSteps = ['query_understanding', 'embedding', 'retrieval', 'reranking', 'reasoning', 'generation', 'verification', 'refinement'];
  const orderedSteps = enabledSteps ? allSteps.filter(s => enabledSteps.includes(s)) : allSteps;
  
  // Map intermediate steps to their parent step for mini-bar display
  const stepMapping = {
    'multi_query': 'query_understanding',
    'guardrail': 'query_understanding'
  };
  const isIntermediateStep = !!stepMapping[currentStep];
  const effectiveCurrentStep = stepMapping[currentStep] || currentStep;
  const currentIndex = orderedSteps.indexOf(effectiveCurrentStep);
  
  return (
    <div className="flex items-center gap-1 px-3 py-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg mb-3 overflow-x-auto">
      {orderedSteps.map((step, idx) => {
        const config = stepConfig[step];
        const stepData = steps[step];
        // Don't mark as completed if we're still in an intermediate step that maps to this step
        const isCompleted = stepData?.status === 'completed' && !(isIntermediateStep && step === effectiveCurrentStep);
        // Mark as running if: explicitly running, OR this is the effective current step
        const isRunning = stepData?.status === 'running' || step === effectiveCurrentStep;
        const isPending = !isCompleted && !isRunning;
        
        return (
          <React.Fragment key={step}>
            <div 
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-all duration-300 ${
                isRunning && !isCompleted ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 animate-pulse' :
                isCompleted ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' :
                'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
              }`}
            >
              <span>{isRunning && !isCompleted ? '⏳' : isCompleted ? '✓' : config.icon}</span>
              <span className="hidden sm:inline">{config.label}</span>
            </div>
            {idx < orderedSteps.length - 1 && (
              <div className={`w-4 h-0.5 ${isCompleted ? 'bg-emerald-400' : 'bg-gray-200 dark:bg-gray-600'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
});

InlinePipelineProgress.displayName = 'InlinePipelineProgress';

/**
 * Candidate preview cards that appear during retrieval
 */
export const CandidatePreviewCards = memo(({ candidates, onViewCV }) => {
  const { language } = useLanguage();
  
  if (!candidates || candidates.length === 0) return null;
  
  // Parse filename to get name
  const parseName = (filename) => {
    if (!filename) return 'Unknown';
    const name = filename.replace('.pdf', '').replace('.PDF', '');
    const parts = name.split('_');
    if (parts.length >= 2) {
      return parts.slice(1, -1).join(' ') || parts[1] || name;
    }
    return name;
  };
  
  return (
    <div className="mt-3">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
        <Users className="w-3 h-3" />
        {language === 'es' ? 'Candidatos encontrados:' : 'Candidates found:'}
      </p>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {candidates.slice(0, 5).map((candidate, idx) => (
          <div 
            key={candidate.cv_id}
            className="flex-shrink-0 p-3 bg-white dark:bg-gray-700 rounded-xl border border-gray-200 dark:border-gray-600 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer hover:scale-105 stagger-item"
            style={{ animationDelay: `${idx * 100}ms` }}
            onClick={() => onViewCV?.(candidate.cv_id, candidate.filename)}
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <FileText className="w-4 h-4 text-blue-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-white truncate max-w-[120px]">
                  {parseName(candidate.filename)}
                </p>
                {candidate.score && (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400">
                    {Math.round(candidate.score * 100)}% match
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
        {candidates.length > 5 && (
          <div className="flex-shrink-0 p-3 bg-gray-100 dark:bg-gray-800 rounded-xl flex items-center justify-center">
            <span className="text-sm text-gray-500">+{candidates.length - 5}</span>
          </div>
        )}
      </div>
    </div>
  );
});

CandidatePreviewCards.displayName = 'CandidatePreviewCards';

/**
 * Reranking results display - shows reordered candidates with scores
 */
export const RerankingResultsPanel = memo(({ results, method }) => {
  const { language } = useLanguage();
  
  if (!results || results.length === 0) return null;
  
  return (
    <div className="mt-3">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
        <Zap className="w-3 h-3 text-yellow-500" />
        {language === 'es' ? 'Reranking completado:' : 'Reranking complete:'}
        <span className="ml-1 px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 text-[10px] rounded-full font-medium">
          {method === 'cross_encoder' ? '⚡ Cross-Encoder' : '🤖 LLM'}
        </span>
      </p>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {results.slice(0, 5).map((result, idx) => (
          <div 
            key={idx}
            className="flex-shrink-0 p-3 bg-gradient-to-br from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800 shadow-sm"
          >
            <div className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                idx === 0 ? 'bg-yellow-500 text-white' : 
                idx === 1 ? 'bg-gray-400 text-white' :
                idx === 2 ? 'bg-orange-600 text-white' :
                'bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300'
              }`}>
                #{result.rank}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-white truncate max-w-[100px]">
                  {result.candidate || 'Unknown'}
                </p>
                {result.score && (
                  <p className="text-xs text-yellow-600 dark:text-yellow-400 font-mono">
                    {(result.score * 100).toFixed(0)}% relevance
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

RerankingResultsPanel.displayName = 'RerankingResultsPanel';

/**
 * Query understanding display panel
 */
export const QueryUnderstandingPanel = memo(({ content, isExpanded, onToggle }) => {
  const { language } = useLanguage();
  
  if (!content) return null;
  
  return (
    <div className="mb-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-200 dark:border-purple-800 overflow-hidden">
      <button 
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-500" />
          <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
            {language === 'es' ? 'Interpretación de la consulta' : 'Query Understanding'}
          </span>
        </div>
        {isExpanded ? <ChevronUp className="w-4 h-4 text-purple-500" /> : <ChevronDown className="w-4 h-4 text-purple-500" />}
      </button>
      
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2 animate-slide-in-up">
          {content.understood_query && (
            <div>
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                {language === 'es' ? 'Consulta interpretada:' : 'Understood query:'}
              </span>
              <p className="text-sm text-gray-700 dark:text-gray-200 mt-1 italic">"{content.understood_query}"</p>
            </div>
          )}
          {content.intent && (
            <div>
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                {language === 'es' ? 'Tipo:' : 'Type:'}
              </span>
              <span className="ml-2 px-2 py-0.5 bg-purple-200 dark:bg-purple-800 text-purple-800 dark:text-purple-200 text-xs rounded-full">
                {content.intent}
              </span>
            </div>
          )}
          {content.keywords && content.keywords.length > 0 && (
            <div>
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                {language === 'es' ? 'Requisitos:' : 'Requirements:'}
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {content.keywords.map((kw, i) => (
                  <span key={i} className="px-2 py-0.5 bg-purple-200 dark:bg-purple-800 text-purple-800 dark:text-purple-200 text-xs rounded-full">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          {content.entities && Object.keys(content.entities).length > 0 && (
            <div>
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                {language === 'es' ? 'Entidades:' : 'Entities:'}
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {Object.entries(content.entities).map(([key, values]) => (
                  <span key={key} className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded">
                    {key}: {Array.isArray(values) ? values.join(', ') : String(values)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {/* Confidence removed - not a meaningful calculated value */}
        </div>
      )}
    </div>
  );
});

QueryUnderstandingPanel.displayName = 'QueryUnderstandingPanel';

/**
 * Streaming message component that shows progressive content
 * When showPreview=false, shows only minimal TypingIndicator
 */
const StreamingMessage = ({ 
  streamingState,
  onViewCV,
  enabledSteps,
  showPreview = true
}) => {
  const { language } = useLanguage();
  const [showUnderstanding, setShowUnderstanding] = useState(true);
  
  // V8: Use real-time streaming tokens if available, otherwise fall back to partialAnswer with typewriter
  const hasStreamingTokens = streamingState?.isStreaming && streamingState?.streamingAnswer;
  const displaySource = hasStreamingTokens ? streamingState.streamingAnswer : (streamingState?.partialAnswer || '');
  
  // Only use typewriter effect for non-streaming (partialAnswer) mode
  const { displayedText, isComplete } = useTypewriter(
    hasStreamingTokens ? '' : displaySource,
    3,
    !hasStreamingTokens && !!displaySource
  );
  
  // For streaming mode, show tokens directly without typewriter delay
  const textToShow = hasStreamingTokens ? streamingState.streamingAnswer : displayedText;
  
  // Auto-scroll state and refs
  const scrollContainerRef = useRef(null);
  const [userScrolled, setUserScrolled] = useState(false);
  const scrollTimeoutRef = useRef(null);
  
  // Auto-scroll to bottom when text updates (unless user has scrolled up)
  useEffect(() => {
    if (!userScrolled && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [displayedText, userScrolled]);
  
  // Reset userScrolled state when partialAnswer changes (new content stream)
  useEffect(() => {
    setUserScrolled(false);
  }, [streamingState?.partialAnswer]);
  
  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);
  
  // Handle user scroll - detect if user scrolled up manually
  const handleScroll = useCallback((e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 30; // 30px threshold
    
    if (!isAtBottom) {
      // User scrolled up - pause auto-scroll
      setUserScrolled(true);
      
      // Re-enable auto-scroll after 3 seconds of inactivity
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      scrollTimeoutRef.current = setTimeout(() => {
        setUserScrolled(false);
      }, 3000);
    } else {
      // User is at the bottom - re-enable auto-scroll immediately
      setUserScrolled(false);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    }
  }, []);
  
  if (!streamingState) return null;
  
  const { currentStep, steps, queryUnderstanding, candidates, rerankingResults, rerankingMethod, partialAnswer, currentProgress, streamingAnswer, isStreaming } = streamingState;
  
  // MINIMAL MODE: Only show TypingIndicator when preview is disabled
  if (!showPreview) {
    return (
      <div className="flex gap-3 message-fade-in">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-purple-100 dark:bg-purple-900/30">
            <Brain className="w-4 h-4 text-purple-500 animate-pulse" />
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <TypingIndicator phase={currentStep} details={steps[currentStep]?.details} progress={currentProgress} />
        </div>
      </div>
    );
  }
  
  // FULL PREVIEW MODE: Show everything
  return (
    <div className="flex gap-3 message-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors duration-300 ${
          currentStep === 'generation' ? 'bg-emerald-100 dark:bg-emerald-900/30' :
          currentStep === 'retrieval' ? 'bg-blue-100 dark:bg-blue-900/30' :
          'bg-purple-100 dark:bg-purple-900/30'
        }`}>
          {currentStep === 'generation' ? (
            <Sparkles className="w-4 h-4 text-emerald-500 animate-pulse" />
          ) : currentStep === 'retrieval' ? (
            <Search className="w-4 h-4 text-blue-500 animate-pulse" />
          ) : (
            <Brain className="w-4 h-4 text-purple-500 animate-pulse" />
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Inline Pipeline Progress - shows only enabled steps */}
        <InlinePipelineProgress steps={steps} currentStep={currentStep} enabledSteps={enabledSteps} />
        
        {/* Query Understanding Panel */}
        {queryUnderstanding && (
          <QueryUnderstandingPanel 
            content={queryUnderstanding}
            isExpanded={showUnderstanding}
            onToggle={() => setShowUnderstanding(!showUnderstanding)}
          />
        )}
        
        {/* Candidate Preview Cards */}
        {candidates && candidates.length > 0 && (
          <CandidatePreviewCards candidates={candidates} onViewCV={onViewCV} />
        )}
        
        {/* Reranking Results - shown after candidates are reordered */}
        {rerankingResults && rerankingResults.length > 0 && (
          <RerankingResultsPanel results={rerankingResults} method={rerankingMethod} />
        )}
        
        {/* Partial Answer with Typewriter or Real-time Streaming - shown in code block for raw markdown */}
        {(partialAnswer || streamingAnswer) && (
          <div className="mt-3 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-gray-100 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                {isStreaming 
                  ? (language === 'es' ? '⚡ Streaming en vivo...' : '⚡ Live streaming...') 
                  : (language === 'es' ? 'Generando respuesta...' : 'Generating response...')}
              </span>
              <Sparkles className={`w-3 h-3 text-emerald-500 ${isStreaming ? 'animate-spin' : 'animate-pulse'}`} />
            </div>
            <pre 
              ref={scrollContainerRef}
              onScroll={handleScroll}
              className="p-4 bg-gray-50 dark:bg-gray-800 overflow-x-auto max-h-64 overflow-y-auto scroll-smooth"
            >
              <code className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words font-mono">
                {textToShow}
                {(isStreaming || !isComplete) && <span className="animate-pulse text-emerald-500">▊</span>}
              </code>
            </pre>
          </div>
        )}
        
        {/* Loading indicator - show when no partial answer or streaming yet
            Always show to indicate pipeline is still running */}
        {!partialAnswer && !streamingAnswer && (
          <TypingIndicator phase={currentStep} details={steps[currentStep]?.details} progress={currentProgress} />
        )}
      </div>
    </div>
  );
};

export default memo(StreamingMessage);
