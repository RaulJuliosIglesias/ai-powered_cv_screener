import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, CheckCircle, Loader, Clock, Search, Database, Sparkles, Shield, Brain, FileText, Zap, Eye, Settings, X } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { usePipeline } from '../contexts/PipelineContext';

// Toast notification component
const Toast = ({ message, type, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-4 rounded-xl shadow-2xl animate-slide-in-up max-w-sm ${
      type === 'enabled' 
        ? 'bg-emerald-600 border border-emerald-400' 
        : 'bg-slate-800 border border-slate-600'
    }`}>
      <span className="text-base font-medium text-white leading-snug">{message}</span>
      <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-lg transition-colors flex-shrink-0">
        <X className="w-4 h-4 text-white" />
      </button>
    </div>
  );
};

// Switch toggle component
const Switch = ({ checked, onChange, label }) => (
  <label className="flex items-center justify-between gap-3 cursor-pointer group">
    <span className="text-xs text-slate-600 dark:text-slate-400 group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors">
      {label}
    </span>
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1 ${
        checked ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-5' : 'translate-x-1'
        }`}
      />
    </button>
  </label>
);

const STEP_CONFIG = {
  query_understanding: {
    icon: Search,
    labelEn: 'Understanding Query',
    labelEs: 'Entendiendo Consulta',
    color: 'blue'
  },
  multi_query: {
    icon: FileText,
    labelEn: 'Multi-Query',
    labelEs: 'Multi-Query',
    color: 'cyan'
  },
  guardrail: {
    icon: Shield,
    labelEn: 'Safety Check',
    labelEs: 'Seguridad',
    color: 'green',
    v7Label: (method) => method === 'zero_shot' ? '🚀 ML' : '📝 Regex'
  },
  embedding: {
    icon: Sparkles,
    labelEn: 'Embeddings',
    labelEs: 'Embeddings',
    color: 'purple'
  },
  retrieval: {
    icon: Database,
    labelEn: 'Searching CVs',
    labelEs: 'Buscando CVs',
    color: 'indigo'
  },
  reranking: {
    icon: Zap,
    labelEn: 'Re-ranking',
    labelEs: 'Reordenando',
    color: 'yellow',
    v7Label: (method) => method === 'cross_encoder' ? '⚡ Cross-Encoder' : '🤖 LLM'
  },
  reasoning: {
    icon: Brain,
    labelEn: 'Analyzing',
    labelEs: 'Analizando',
    color: 'pink'
  },
  generation: {
    icon: Sparkles,
    labelEn: 'Generating',
    labelEs: 'Generando',
    color: 'emerald'
  },
  verification: {
    icon: Eye,
    labelEn: 'Verifying',
    labelEs: 'Verificando',
    color: 'orange',
    v7Label: (method) => method === 'nli' ? '🧪 NLI' : '🤖 LLM'
  },
  refinement: {
    icon: Sparkles,
    labelEn: 'Refining',
    labelEs: 'Refinando',
    color: 'violet'
  }
};

const PipelineProgressPanel = ({ isExpanded, onToggleExpand, autoExpand, onToggleAutoExpand, showPreview, onTogglePreview, enabledSteps }) => {
  const { language } = useLanguage();
  const { activePipeline, isActiveStreaming, activeSessionId } = usePipeline();
  const [toast, setToast] = useState(null);
  
  // Get progress from context instead of prop
  const progress = activePipeline || {};
  
  // Determine if we're showing live data or historical data
  const isLiveData = isActiveStreaming && activePipeline?.isStreaming;
  const isHistoricalData = activePipeline?.derivedFromMessage === true;
  const hasData = activePipeline !== null && Object.keys(activePipeline).length > 0;

  const showToast = (key, enabled) => {
    const messages = {
      autoExpand: {
        enabled: language === 'es' 
          ? '✓ Auto-expandir activado: El panel se abrirá automáticamente al procesar' 
          : '✓ Auto-expand enabled: Panel will open automatically when processing',
        disabled: language === 'es' 
          ? '✗ Auto-expandir desactivado: El panel permanecerá cerrado' 
          : '✗ Auto-expand disabled: Panel will stay closed'
      },
      showPreview: {
        enabled: language === 'es' 
          ? '✓ Vista previa activada: Verás el progreso detallado con mini-bar' 
          : '✓ Preview enabled: You\'ll see detailed progress with mini-bar',
        disabled: language === 'es' 
          ? '✗ Vista previa desactivada: Solo indicador simple de carga' 
          : '✗ Preview disabled: Only simple loading indicator'
      }
    };
    setToast({
      message: enabled ? messages[key].enabled : messages[key].disabled,
      type: enabled ? 'enabled' : 'disabled'
    });
  };

  const handleAutoExpandToggle = () => {
    const newValue = !autoExpand;
    onToggleAutoExpand();
    showToast('autoExpand', newValue);
  };

  const handlePreviewToggle = () => {
    const newValue = !showPreview;
    onTogglePreview();
    showToast('showPreview', newValue);
  };

  const getStepStatus = (stepName) => {
    if (!progress || !progress[stepName]) return 'pending';
    return progress[stepName].status || 'pending';
  };

  // Filter steps based on enabledSteps prop (if provided)
  const allSteps = Object.keys(STEP_CONFIG);
  const steps = enabledSteps ? allSteps.filter(s => enabledSteps.includes(s)) : allSteps;
  const completedCount = steps.filter(s => getStepStatus(s) === 'completed').length;
  const currentStep = steps.find(s => getStepStatus(s) === 'running');

  return (
    <div className={`
      fixed top-0 right-0 h-full bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-xl
      transition-all duration-300 ease-in-out z-20
      ${isExpanded ? 'w-72' : 'w-11'}
    `}>
      <div className="flex flex-col h-full">
        {/* Header spacer to align with main header */}
        <div className="h-14 flex-shrink-0 bg-slate-100 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 flex items-center justify-center">
          {isExpanded ? (
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">RAG Pipeline</span>
              <span className="px-1.5 py-0.5 bg-gradient-to-r from-purple-500 to-emerald-500 text-white text-[9px] font-bold rounded">V5</span>
            </div>
          ) : (
            <Brain className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          )}
        </div>
        
        {/* Collapse/Expand Button */}
        <button
          onClick={onToggleExpand}
          className="flex items-center justify-center h-9 w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white transition-all duration-200 flex-shrink-0"
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium">{language === 'es' ? 'Colapsar' : 'Collapse'}</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>

        {/* Collapsed View */}
        {!isExpanded && (
          <div className="flex flex-col items-center py-4 gap-3 flex-1">
            {/* Mini progress indicator */}
            <div className="flex flex-col items-center gap-1">
              {currentStep ? (
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              ) : (
                <Brain className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              )}
            </div>
            
            {/* Vertical progress dots */}
            <div className="flex flex-col gap-1">
              {steps.slice(0, 5).map((stepName, i) => {
                const status = getStepStatus(stepName);
                return (
                  <div
                    key={stepName}
                    className={`w-1.5 h-1.5 rounded-full transition-colors ${
                      status === 'completed' ? 'bg-emerald-500' :
                      status === 'running' ? 'bg-emerald-400 animate-pulse' :
                      'bg-slate-300 dark:bg-slate-700'
                    }`}
                  />
                );
              })}
            </div>
            
            {/* Count */}
            <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-500">
              {completedCount}/{steps.length}
            </span>
          </div>
        )}

        {/* Expanded View */}
        {isExpanded && (
          <>
            {/* Header */}
            <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
              {/* Status indicator - Live vs Historical */}
              {hasData && (
                <div className={`mb-2 px-2 py-1 rounded-md text-[10px] font-medium ${
                  isLiveData 
                    ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' 
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                }`}>
                  {isLiveData 
                    ? (language === 'es' ? '🔴 EN VIVO' : '🔴 LIVE')
                    : (language === 'es' ? '📋 Última ejecución' : '📋 Last run')}
                </div>
              )}
              
              {/* Progress info */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  {completedCount}/{steps.length} {language === 'es' ? 'pasos' : 'steps'}
                </span>
                {isLiveData && currentStep && (
                  <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                    <Loader className="w-3 h-3 animate-spin" />
                    <span className="font-medium">{language === 'es' ? 'Procesando' : 'Processing'}</span>
                  </span>
                )}
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
                  style={{ width: `${(completedCount / steps.length) * 100}%` }}
                />
              </div>

              {/* Settings switches */}
              <div className="mt-3 space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                <Switch 
                  checked={autoExpand} 
                  onChange={handleAutoExpandToggle}
                  label={language === 'es' ? 'Auto-expandir' : 'Auto-expand'}
                />
                <Switch 
                  checked={showPreview} 
                  onChange={handlePreviewToggle}
                  label={language === 'es' ? 'Vista previa' : 'Show preview'}
                />
              </div>
            </div>

            {/* Steps List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {steps.map((stepName, index) => {
                const config = STEP_CONFIG[stepName];
                const status = getStepStatus(stepName);
                const Icon = config.icon;
                const isRunning = status === 'running';
                const isCompleted = status === 'completed';

                // Get v7 method from step metadata if available
                const stepData = progress[stepName] || {};
                const v7Method = stepData.metadata?.method;
                const v7Label = config.v7Label && v7Method ? config.v7Label(v7Method) : null;

                return (
                  <div key={stepName} className="space-y-1">
                    <div
                      className={`
                        rounded-lg px-2 py-1.5 transition-all duration-200 flex items-center gap-2
                        ${isRunning ? 'bg-emerald-50 dark:bg-emerald-900/30' : 
                          isCompleted ? 'bg-slate-50 dark:bg-slate-800/50' : 
                          'opacity-40'}
                      `}
                    >
                      {/* Status indicator */}
                      <div className={`
                        flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center
                        ${isCompleted ? 'bg-emerald-500 text-white' :
                          isRunning ? 'bg-emerald-500 text-white' :
                          'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-500'}
                      `}>
                        {isCompleted ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : isRunning ? (
                          <Loader className="w-3 h-3 animate-spin" />
                        ) : (
                          <span className="text-[9px] font-bold">{index + 1}</span>
                        )}
                      </div>

                      {/* Icon */}
                      <Icon className={`
                        w-3.5 h-3.5 flex-shrink-0
                        ${isRunning ? 'text-emerald-600 dark:text-emerald-400' :
                          isCompleted ? 'text-emerald-600 dark:text-emerald-400' :
                          'text-slate-400 dark:text-slate-600'}
                      `} />

                      {/* Label + V7 badge */}
                      <div className="flex-1 flex items-center gap-1.5 min-w-0">
                        <span className={`
                          text-xs truncate
                          ${isRunning ? 'text-slate-900 dark:text-white font-medium' :
                            isCompleted ? 'text-slate-600 dark:text-slate-400' :
                            'text-slate-500 dark:text-slate-600'}
                        `}>
                          {language === 'es' ? config.labelEs : config.labelEn}
                        </span>
                        {/* V7 Method Badge */}
                        {v7Label && isCompleted && (
                          <span className="text-[9px] px-1 py-0.5 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 font-medium whitespace-nowrap">
                            {v7Label}
                          </span>
                        )}
                      </div>

                      {/* Right status icon */}
                      {isCompleted && (
                        <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                      )}
                    </div>
                    
                    {/* Reranking Results - Show top candidates with scores */}
                    {stepName === 'reranking' && isCompleted && stepData.results && stepData.results.length > 0 && (
                      <div className="ml-7 p-2 bg-slate-100 dark:bg-slate-800 rounded-md">
                        <div className="text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                          {language === 'es' ? 'Top rerankeados:' : 'Top reranked:'}
                        </div>
                        <div className="space-y-0.5">
                          {stepData.results.slice(0, 3).map((result, idx) => (
                            <div key={idx} className="flex items-center justify-between text-[10px]">
                              <span className="text-slate-600 dark:text-slate-300 truncate max-w-[100px]">
                                #{result.rank} {result.candidate}
                              </span>
                              {result.score && (
                                <span className="text-emerald-600 dark:text-emerald-400 font-mono">
                                  {(result.score * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Toast notification */}
      {toast && (
        <Toast 
          message={toast.message} 
          type={toast.type} 
          onClose={() => setToast(null)} 
        />
      )}
    </div>
  );
};

export default PipelineProgressPanel;
