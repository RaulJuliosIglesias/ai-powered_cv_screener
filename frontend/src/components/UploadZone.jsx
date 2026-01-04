import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, AlertCircle, Cloud, Loader } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function UploadZone({
  files,
  onFilesAdded,
  onFileRemove,
  onUpload,
  isUploading,
  uploadProgress,
  error,
}) {
  const { language } = useLanguage();
  const onDrop = useCallback(
    (acceptedFiles) => {
      onFilesAdded(acceptedFiles);
    },
    [onFilesAdded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    disabled: isUploading,
  });

  return (
    <div className="flex items-center justify-center h-full p-8 bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Cloud className="w-8 h-8 text-blue-500" aria-hidden="true" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {language === 'es' ? 'Subir CVs' : 'Upload CVs'}
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            {language === 'es' 
              ? 'Arrastra y suelta archivos PDF para comenzar el análisis' 
              : 'Drag and drop PDF files to start the analysis'}
          </p>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
            ${isDragActive
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-[1.02]'
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-gray-50 dark:hover:bg-gray-800/50'
            }
            ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          <div className={`w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center transition-colors ${
            isDragActive
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
          }`}>
            <Upload className="w-8 h-8" />
          </div>
          {isDragActive ? (
            <p className="text-blue-500 text-lg font-medium">
              {language === 'es' ? '¡Suelta los archivos aquí!' : 'Drop the files here!'}
            </p>
          ) : (
            <>
              <p className="text-gray-700 dark:text-gray-300 text-lg mb-2 font-medium">
                {language === 'es' ? 'Arrastra archivos PDF aquí' : 'Drag PDF files here'}
              </p>
              <p className="text-gray-400 dark:text-gray-500 text-sm">
                {language === 'es' ? 'o ' : 'or '}
                <span className="text-blue-500 hover:underline">
                  {language === 'es' ? 'haz clic para seleccionar' : 'click to select'}
                </span>
              </p>
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-center gap-3 text-red-700 dark:text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* File list */}
        {files.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {language === 'es' ? 'Archivos seleccionados' : 'Selected files'}
              </h3>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-medium rounded-full">
                {files.length} {language === 'es' ? (files.length > 1 ? 'archivos' : 'archivo') : (files.length > 1 ? 'files' : 'file')}
              </span>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                      <FileText className="w-5 h-5 text-red-500" />
                    </div>
                    <div>
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate max-w-xs block">
                        {file.name}
                      </span>
                      <span className="text-xs text-gray-400">
                        {(file.size / 1024).toFixed(1)} KB
                      </span>
                    </div>
                  </div>
                  {!isUploading && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onFileRemove(index);
                      }}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-gray-400 hover:text-red-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Upload button */}
            <button
              onClick={onUpload}
              disabled={isUploading || files.length === 0}
              className={`mt-6 w-full py-4 px-4 rounded-xl font-semibold text-lg transition-all flex items-center justify-center gap-3 focus-ring
                ${isUploading || files.length === 0
                  ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40'
                }
              `}
              aria-busy={isUploading}
            >
              {isUploading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" aria-hidden="true" />
                  <span>{language === 'es' ? 'Subiendo...' : 'Uploading...'} {uploadProgress}%</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" aria-hidden="true" />
                  <span>
                    {language === 'es' 
                      ? `Subir ${files.length} ${files.length > 1 ? 'archivos' : 'archivo'}` 
                      : `Upload ${files.length} ${files.length > 1 ? 'files' : 'file'}`}
                  </span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Tips */}
        {files.length === 0 && (
          <div className="mt-8 grid grid-cols-3 gap-4">
            {[
              { icon: '📄', textEs: 'Solo PDF', textEn: 'PDF only' },
              { icon: '📦', textEs: 'Múltiples archivos', textEn: 'Multiple files' },
              { icon: '⚡', textEs: 'Proceso rápido', textEn: 'Fast processing' },
            ].map((tip, i) => (
              <div key={i} className="text-center p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                <span className="text-2xl mb-1 block" aria-hidden="true">{tip.icon}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {language === 'es' ? tip.textEs : tip.textEn}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
