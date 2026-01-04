import { useState } from 'react';
import { ChevronLeft, ChevronRight, CheckCircle, Loader, Clock, Search, Database, Sparkles, Shield, Brain, FileText, Zap, Eye, Settings } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

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
    color: 'green'
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
    color: 'yellow'
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
    color: 'orange'
  },
  refinement: {
    icon: Sparkles,
    labelEn: 'Refining',
    labelEs: 'Refinando',
    color: 'violet'
  }
};

const PipelineProgressPanel = ({ isExpanded, onToggleExpand, progress, autoExpand, onToggleAutoExpand }) => {
  const { language } = useLanguage();

  const getStepStatus = (stepName) => {
    if (!progress || !progress[stepName]) return 'pending';
    return progress[stepName].status || 'pending';
  };

  const steps = Object.keys(STEP_CONFIG);
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
              {/* Progress info */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  {completedCount}/{steps.length} {language === 'es' ? 'pasos' : 'steps'}
                </span>
                {currentStep && (
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

              {/* Auto-expand toggle */}
              <label className="flex items-center gap-2 mt-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoExpand}
                  onChange={onToggleAutoExpand}
                  className="w-3.5 h-3.5 text-emerald-600 bg-slate-100 border-slate-300 rounded focus:ring-emerald-500 dark:bg-slate-700 dark:border-slate-600"
                />
                <span className="text-xs text-slate-600 dark:text-slate-400">
                  {language === 'es' ? 'Auto-expandir' : 'Auto-expand'}
                </span>
              </label>
            </div>

            {/* Steps List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {steps.map((stepName, index) => {
                const config = STEP_CONFIG[stepName];
                const status = getStepStatus(stepName);
                const Icon = config.icon;
                const isRunning = status === 'running';
                const isCompleted = status === 'completed';

                return (
                  <div
                    key={stepName}
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

                    {/* Label */}
                    <span className={`
                      text-xs truncate flex-1
                      ${isRunning ? 'text-slate-900 dark:text-white font-medium' :
                        isCompleted ? 'text-slate-600 dark:text-slate-400' :
                        'text-slate-500 dark:text-slate-600'}
                    `}>
                      {language === 'es' ? config.labelEs : config.labelEn}
                    </span>

                    {/* Right status icon */}
                    {isCompleted && (
                      <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default PipelineProgressPanel;
