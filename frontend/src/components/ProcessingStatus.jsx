import React from 'react';
import { CheckCircle, XCircle, Loader, FileText, Cpu, Database, Sparkles } from 'lucide-react';

const PROCESSING_STEPS = [
  { id: 'upload', label: 'Uploading files', icon: FileText },
  { id: 'extract', label: 'Extracting text from PDFs', icon: FileText },
  { id: 'chunk', label: 'Chunking content', icon: Cpu },
  { id: 'embed', label: 'Generating embeddings', icon: Sparkles },
  { id: 'store', label: 'Storing in vector database', icon: Database },
];

export default function ProcessingStatus({ status }) {
  if (!status) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center p-8">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-blue-200 dark:border-blue-800 rounded-full animate-pulse mx-auto" />
            <Loader className="w-8 h-8 animate-spin text-blue-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <p className="text-gray-600 dark:text-gray-400 mt-4 text-lg">Iniciando procesamiento...</p>
          <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">Preparando archivos para análisis</p>
        </div>
      </div>
    );
  }

  const { total_files, processed_files, errors, status: jobStatus } = status;
  const progress = total_files > 0 ? (processed_files / total_files) * 100 : 0;
  const isComplete = jobStatus === 'completed' || jobStatus === 'completed_with_errors';
  const currentStep = Math.min(Math.floor((progress / 100) * PROCESSING_STEPS.length), PROCESSING_STEPS.length - 1);

  return (
    <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900 p-4">
      <div className="w-full max-w-lg">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="text-center mb-6">
            <div className={`w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center ${
              isComplete 
                ? 'bg-green-100 dark:bg-green-900/30' 
                : 'bg-blue-100 dark:bg-blue-900/30'
            }`}>
              {isComplete ? (
                <CheckCircle className="w-8 h-8 text-green-500" />
              ) : (
                <Loader className="w-8 h-8 animate-spin text-blue-500" />
              )}
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              {isComplete ? '¡Procesamiento Completado!' : 'Procesando CVs...'}
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              {isComplete 
                ? `${processed_files} archivo(s) procesado(s) correctamente`
                : `Procesando ${processed_files} de ${total_files} archivos`
              }
            </p>
          </div>

          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600 dark:text-gray-400">Progreso</span>
              <span className="font-medium text-gray-900 dark:text-white">{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  isComplete ? 'bg-green-500' : 'bg-blue-500'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Processing steps */}
          {!isComplete && (
            <div className="space-y-3 mb-6">
              {PROCESSING_STEPS.map((step, index) => {
                const Icon = step.icon;
                const isActive = index === currentStep;
                const isCompleted = index < currentStep;
                
                return (
                  <div 
                    key={step.id}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                      isActive 
                        ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800' 
                        : isCompleted
                          ? 'bg-green-50 dark:bg-green-900/20'
                          : 'bg-gray-50 dark:bg-gray-800/50'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      isActive 
                        ? 'bg-blue-500 text-white' 
                        : isCompleted
                          ? 'bg-green-500 text-white'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-400'
                    }`}>
                      {isCompleted ? (
                        <CheckCircle className="w-4 h-4" />
                      ) : isActive ? (
                        <Loader className="w-4 h-4 animate-spin" />
                      ) : (
                        <Icon className="w-4 h-4" />
                      )}
                    </div>
                    <span className={`text-sm font-medium ${
                      isActive 
                        ? 'text-blue-700 dark:text-blue-300' 
                        : isCompleted
                          ? 'text-green-700 dark:text-green-300'
                          : 'text-gray-400 dark:text-gray-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* File count badge */}
          <div className="flex items-center justify-center gap-4 text-sm">
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-full">
              <FileText className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <span className="text-gray-700 dark:text-gray-300">
                <span className="font-bold text-blue-600 dark:text-blue-400">{processed_files}</span>
                <span className="mx-1">/</span>
                <span>{total_files}</span>
                <span className="ml-1">archivos</span>
              </span>
            </div>
          </div>

          {/* Errors */}
          {errors && errors.length > 0 && (
            <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-5 h-5 text-red-500" />
                <p className="font-medium text-red-800 dark:text-red-300">Errores encontrados:</p>
              </div>
              <ul className="text-sm text-red-700 dark:text-red-400 space-y-1 ml-7">
                {errors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
