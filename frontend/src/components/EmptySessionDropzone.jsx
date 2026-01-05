import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Cloud, FileText, Loader } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function EmptySessionDropzone({ onFilesDropped, isUploading }) {
  const { language } = useLanguage();

  const onDrop = useCallback(
    (acceptedFiles) => {
      const pdfFiles = acceptedFiles.filter((f) => f.name.toLowerCase().endsWith('.pdf'));
      if (pdfFiles.length > 0) {
        onFilesDropped(pdfFiles);
      }
    },
    [onFilesDropped]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    disabled: isUploading,
    noClick: false,
    noKeyboard: false,
  });

  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Cloud className="w-8 h-8 text-blue-500" aria-hidden="true" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">
            {language === 'es' ? 'Sube CVs para empezar' : 'Upload CVs to Start'}
          </h2>
          <p className="text-slate-500 dark:text-slate-400">
            {language === 'es'
              ? 'Arrastra y suelta archivos PDF para comenzar el análisis'
              : 'Drag and drop PDF files to start the analysis'}
          </p>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`
            relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
            ${
              isDragActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-[1.02] shadow-lg shadow-blue-500/20'
                : 'border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-slate-50 dark:hover:bg-slate-800/50'
            }
            ${isUploading ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}
          `}
        >
          <input {...getInputProps()} />
          
          {/* Animated background when dragging */}
          {isDragActive && (
            <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-cyan-500/10 to-blue-500/10 animate-pulse" />
            </div>
          )}

          <div
            className={`relative w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center transition-all duration-200 ${
              isDragActive
                ? 'bg-blue-500 text-white scale-110'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
            }`}
          >
            {isUploading ? (
              <Loader className="w-10 h-10 animate-spin" />
            ) : (
              <Upload className={`w-10 h-10 transition-transform ${isDragActive ? 'animate-bounce' : ''}`} />
            )}
          </div>

          {isDragActive ? (
            <div className="relative">
              <p className="text-blue-500 text-xl font-semibold mb-2">
                {language === 'es' ? '¡Suelta los archivos aquí!' : 'Drop the files here!'}
              </p>
              <p className="text-blue-400 text-sm">
                {language === 'es' ? 'Los CVs se subirán automáticamente' : 'CVs will be uploaded automatically'}
              </p>
            </div>
          ) : isUploading ? (
            <div className="relative">
              <p className="text-slate-600 dark:text-slate-300 text-lg font-medium mb-2">
                {language === 'es' ? 'Subiendo CVs...' : 'Uploading CVs...'}
              </p>
              <p className="text-slate-400 text-sm">
                {language === 'es' ? 'Por favor espera' : 'Please wait'}
              </p>
            </div>
          ) : (
            <div className="relative">
              <p className="text-slate-700 dark:text-slate-300 text-lg font-medium mb-2">
                {language === 'es' ? 'Arrastra archivos PDF aquí' : 'Drag PDF files here'}
              </p>
              <p className="text-slate-400 dark:text-slate-500 text-sm">
                {language === 'es' ? 'o ' : 'or '}
                <span className="text-blue-500 hover:underline font-medium">
                  {language === 'es' ? 'haz clic para seleccionar' : 'click to select'}
                </span>
              </p>
            </div>
          )}
        </div>

        {/* Tips */}
        <div className="mt-8 grid grid-cols-3 gap-4">
          {[
            { icon: FileText, textEs: 'Solo PDF', textEn: 'PDF only', color: 'text-red-500' },
            { icon: Cloud, textEs: 'Múltiples archivos', textEn: 'Multiple files', color: 'text-blue-500' },
            { icon: Upload, textEs: 'Proceso rápido', textEn: 'Fast processing', color: 'text-emerald-500' },
          ].map((tip, i) => (
            <div
              key={i}
              className="text-center p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
            >
              <tip.icon className={`w-6 h-6 ${tip.color} mx-auto mb-2`} />
              <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                {language === 'es' ? tip.textEs : tip.textEn}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
