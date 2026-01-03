import { useState } from 'react';
import { ChevronDown, ChevronRight, Search, Database, Brain, FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Pipeline Steps Panel - Shows real execution steps from backend
 */
const PipelineStepsPanel = ({ steps, isExpanded, onToggle }) => {
  const { language } = useLanguage();
  
  if (!steps || steps.length === 0) return null;
  
  const stepConfig = {
    query_understanding: {
      icon: Search,
      label: language === 'es' ? 'Entendiendo consulta' : 'Understanding query',
      color: 'blue'
    },
    retrieval: {
      icon: Database,
      label: language === 'es' ? 'Buscando en CVs' : 'Searching CVs',
      color: 'green'
    },
    analysis: {
      icon: Brain,
      label: language === 'es' ? 'Analizando candidatos' : 'Analyzing candidates',
      color: 'yellow'
    },
    generation: {
      icon: FileText,
      label: language === 'es' ? 'Generando respuesta' : 'Generating response',
      color: 'purple'
    }
  };
  
  const statusIcons = {
    completed: CheckCircle,
    running: Clock,
    error: AlertCircle,
    pending: Clock
  };
  
  const totalTime = steps.reduce((acc, s) => acc + (s.duration_ms || 0), 0);
  
  return (
    <div className="mb-3 rounded-lg border border-emerald-200 dark:border-emerald-800 overflow-hidden bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20">
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 flex items-center gap-2 hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-emerald-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-emerald-500" />
        )}
        <Database className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
          {language === 'es' ? 'Pasos del Análisis' : 'Analysis Steps'}
        </span>
        <span className="ml-2 px-2 py-0.5 text-xs bg-emerald-200 dark:bg-emerald-800 text-emerald-700 dark:text-emerald-300 rounded-full">
          {(totalTime / 1000).toFixed(1)}s
        </span>
        <span className="ml-auto text-xs text-emerald-500 dark:text-emerald-400">
          {isExpanded ? (language === 'es' ? 'Ocultar' : 'Hide') : (language === 'es' ? 'Ver' : 'View')}
        </span>
      </button>
      
      {isExpanded && (
        <div className="border-t border-emerald-200 dark:border-emerald-800 bg-white/50 dark:bg-gray-900/50 p-3">
          <div className="space-y-2">
            {steps.map((step, idx) => {
              const config = stepConfig[step.name] || { icon: CheckCircle, label: step.name, color: 'gray' };
              const Icon = config.icon;
              const StatusIcon = statusIcons[step.status] || CheckCircle;
              const isComplete = step.status === 'completed';
              const isError = step.status === 'error';
              
              return (
                <div 
                  key={idx} 
                  className={`flex items-center gap-3 p-2 rounded-lg ${
                    isError 
                      ? 'bg-red-50 dark:bg-red-900/20' 
                      : isComplete 
                        ? 'bg-emerald-50 dark:bg-emerald-900/20' 
                        : 'bg-gray-50 dark:bg-gray-800'
                  }`}
                >
                  <div className={`p-1.5 rounded-full ${
                    isError 
                      ? 'bg-red-100 dark:bg-red-900/40' 
                      : isComplete 
                        ? 'bg-emerald-100 dark:bg-emerald-900/40' 
                        : 'bg-gray-100 dark:bg-gray-700'
                  }`}>
                    <Icon className={`w-4 h-4 ${
                      isError 
                        ? 'text-red-500' 
                        : isComplete 
                          ? 'text-emerald-500' 
                          : 'text-gray-400'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${
                        isError 
                          ? 'text-red-700 dark:text-red-300' 
                          : isComplete 
                            ? 'text-emerald-700 dark:text-emerald-300' 
                            : 'text-gray-500'
                      }`}>
                        {config.label}
                      </span>
                      {step.duration_ms > 0 && (
                        <span className="text-xs text-gray-400">
                          {step.duration_ms.toFixed(0)}ms
                        </span>
                      )}
                    </div>
                    {step.details && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {step.details}
                      </p>
                    )}
                  </div>
                  <StatusIcon className={`w-4 h-4 ${
                    isError 
                      ? 'text-red-500' 
                      : isComplete 
                        ? 'text-emerald-500' 
                        : 'text-gray-300'
                  }`} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default PipelineStepsPanel;
