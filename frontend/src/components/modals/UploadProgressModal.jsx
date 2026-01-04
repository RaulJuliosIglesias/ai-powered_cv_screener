import { memo } from 'react';
import { Loader, Check, X } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const UploadProgressModal = memo(({ progress, onClose }) => {
  const { language } = useLanguage();
  
  if (!progress) return null;

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'completed':
        return <Check className="w-6 h-6 text-emerald-500" />;
      case 'error':
        return <X className="w-6 h-6 text-red-500" />;
      default:
        return <Loader className="w-6 h-6 text-blue-500 animate-spin" />;
    }
  };

  const getStatusBg = () => {
    switch (progress.status) {
      case 'completed':
        return 'bg-emerald-100 dark:bg-emerald-900/30';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/30';
      default:
        return 'bg-blue-100 dark:bg-blue-900/30';
    }
  };

  const getProgressBarColor = () => {
    switch (progress.status) {
      case 'completed':
        return 'bg-emerald-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getTitle = () => {
    switch (progress.status) {
      case 'uploading':
        return language === 'es' ? 'Subiendo CVs' : 'Uploading CVs';
      case 'processing':
        return language === 'es' ? 'Procesando CVs' : 'Processing CVs';
      case 'completed':
        return language === 'es' ? 'Completado' : 'Completed';
      case 'error':
        return 'Error';
      default:
        return language === 'es' ? 'Procesando' : 'Processing';
    }
  };

  return (
    <div className="modal-overlay overlay-enter" role="dialog" aria-modal="true" aria-labelledby="upload-progress-title">
      <div className="modal-content modal-enter w-full max-w-md p-6 mx-4">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${getStatusBg()}`}>
            {getStatusIcon()}
          </div>
          <div>
            <h3 id="upload-progress-title" className="font-semibold text-primary">
              {getTitle()}
            </h3>
            <p className="text-sm text-secondary">
              {progress.current} / {progress.total} {language === 'es' ? 'archivos' : 'files'}
            </p>
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden mb-4">
          <div 
            className={`h-full transition-all duration-300 ${getProgressBarColor()}`}
            style={{ width: `${progress.percent || 0}%` }}
            role="progressbar"
            aria-valuenow={progress.percent || 0}
            aria-valuemin="0"
            aria-valuemax="100"
          />
        </div>
        
        {/* Log messages */}
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 max-h-32 overflow-y-auto">
          {progress.logs?.map((log, i) => (
            <p key={i} className="text-xs text-secondary font-mono">
              {log}
            </p>
          ))}
        </div>
        
        {/* File list */}
        {progress.files && progress.files.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {progress.files.slice(0, 5).map((file, i) => (
              <span key={i} className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-secondary">
                {file.length > 20 ? file.slice(0, 20) + '...' : file}
              </span>
            ))}
            {progress.files.length > 5 && (
              <span className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-secondary">
                +{progress.files.length - 5} more
              </span>
            )}
          </div>
        )}

        {/* Close button for error state */}
        {progress.status === 'error' && (
          <button
            onClick={onClose}
            className="mt-4 w-full btn-secondary"
          >
            {language === 'es' ? 'Cerrar' : 'Close'}
          </button>
        )}
      </div>
    </div>
  );
});

UploadProgressModal.displayName = 'UploadProgressModal';

export default UploadProgressModal;
