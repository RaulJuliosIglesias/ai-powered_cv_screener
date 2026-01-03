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
      fixed top-0 right-0 h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-xl
      transition-all duration-300 ease-in-out z-30
      ${isExpanded ? 'w-80' : 'w-12'}
    `}>
      <div className="flex flex-col h-full">
        {/* Collapse/Expand Button */}
        <button
          onClick={onToggleExpand}
          className="absolute -left-6 top-4 w-6 h-12 bg-emerald-500 hover:bg-emerald-600 text-white rounded-l-lg flex items-center justify-center shadow-lg transition-colors z-10"
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        {/* Collapsed View */}
        {!isExpanded && (
          <div className="flex flex-col items-center py-6 gap-4">
            <Brain className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            <div className="writing-mode-vertical text-xs font-medium text-gray-600 dark:text-gray-400 transform rotate-180">
              RAG
            </div>
            {currentStep && (
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            )}
          </div>
        )}

        {/* Expanded View */}
        {isExpanded && (
          <>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-emerald-50 to-cyan-50 dark:from-gray-900 dark:to-gray-800">
              <div className="flex items-center gap-3 mb-3">
                <div className="relative">
                  <Brain className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                  {currentStep && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full animate-pulse" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                    {language === 'es' ? 'Pipeline RAG' : 'RAG Pipeline'}
                  </h3>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {completedCount}/{steps.length} {language === 'es' ? 'pasos' : 'steps'}
                  </p>
                </div>
              </div>

              {/* Auto-expand toggle */}
              <div className="flex items-center justify-between p-2 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoExpand}
                    onChange={onToggleAutoExpand}
                    className="w-4 h-4 text-emerald-600 bg-gray-100 border-gray-300 rounded focus:ring-emerald-500 dark:focus:ring-emerald-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                  />
                  <span className="text-xs text-gray-700 dark:text-gray-300">
                    {language === 'es' ? 'Auto-expandir' : 'Auto-expand'}
                  </span>
                </label>
                <Settings className="w-3.5 h-3.5 text-gray-400" />
              </div>

              {/* Progress Bar */}
              <div className="mt-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
                  style={{ width: `${(completedCount / steps.length) * 100}%` }}
                />
              </div>
            </div>

            {/* Steps List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
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
                      rounded-lg p-2 transition-all duration-200
                      ${isRunning ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-300 dark:border-emerald-700' : 
                        isCompleted ? 'bg-gray-50 dark:bg-gray-800/50' : 
                        'bg-gray-50/50 dark:bg-gray-800/30 opacity-50'}
                    `}
                  >
                    <div className="flex items-center gap-2">
                      {/* Step Number/Status */}
                      <div className={`
                        flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs
                        ${isCompleted ? 'bg-emerald-500 text-white' :
                          isRunning ? 'bg-emerald-500 text-white' :
                          'bg-gray-300 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}
                      `}>
                        {isCompleted ? (
                          <CheckCircle className="w-3.5 h-3.5" />
                        ) : isRunning ? (
                          <Loader className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <span className="text-[10px] font-bold">{index + 1}</span>
                        )}
                      </div>

                      {/* Icon */}
                      <div className="flex-shrink-0">
                        <Icon className={`
                          w-4 h-4
                          ${isRunning ? 'text-emerald-600 dark:text-emerald-400 animate-pulse' :
                            isCompleted ? 'text-emerald-600 dark:text-emerald-400' :
                            'text-gray-400 dark:text-gray-600'}
                        `} />
                      </div>

                      {/* Label */}
                      <div className="flex-1 min-w-0">
                        <p className={`
                          text-xs font-medium truncate
                          ${isRunning ? 'text-gray-900 dark:text-white' :
                            isCompleted ? 'text-gray-700 dark:text-gray-300' :
                            'text-gray-500 dark:text-gray-500'}
                        `}>
                          {language === 'es' ? config.labelEs : config.labelEn}
                        </p>
                      </div>

                      {/* Status */}
                      {isRunning && (
                        <Loader className="w-3.5 h-3.5 text-emerald-500 animate-spin flex-shrink-0" />
                      )}
                      {isCompleted && (
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                      )}
                      {!isRunning && !isCompleted && (
                        <Clock className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 flex-shrink-0" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            {currentStep && (
              <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gradient-to-r from-emerald-50 to-cyan-50 dark:from-gray-900 dark:to-gray-800">
                <div className="flex items-center gap-2">
                  <Loader className="w-3.5 h-3.5 animate-spin text-emerald-600 dark:text-emerald-400" />
                  <span className="text-xs text-gray-700 dark:text-gray-300">
                    {language === 'es' ? STEP_CONFIG[currentStep].labelEs : STEP_CONFIG[currentStep].labelEn}...
                  </span>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default PipelineProgressPanel;
