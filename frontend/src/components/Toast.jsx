import { memo, useEffect } from 'react';
import { Check, X, Sparkles, AlertCircle } from 'lucide-react';

const Toast = memo(({ message, type = 'info', duration = 3000, onClose }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <Check className="w-5 h-5" aria-hidden="true" />;
      case 'error':
        return <X className="w-5 h-5" aria-hidden="true" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5" aria-hidden="true" />;
      default:
        return <Sparkles className="w-5 h-5" aria-hidden="true" />;
    }
  };

  const getStyles = () => {
    switch (type) {
      case 'success':
        return 'bg-emerald-500 text-white';
      case 'error':
        return 'bg-red-500 text-white';
      case 'warning':
        return 'bg-amber-500 text-white';
      default:
        return 'bg-slate-800 text-white';
    }
  };

  return (
    <div 
      className="fixed bottom-4 right-4 z-50 slide-in-up"
      role="alert"
      aria-live="polite"
    >
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg ${getStyles()}`}>
        {getIcon()}
        <span className="text-sm font-medium">{message}</span>
        <button 
          onClick={onClose}
          className="ml-2 p-1 hover:bg-white/20 rounded transition-colors focus-ring"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
});

Toast.displayName = 'Toast';

export default Toast;
