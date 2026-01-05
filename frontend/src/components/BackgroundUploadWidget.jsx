import { memo, useEffect, useRef } from 'react';
import { 
  Minimize2, 
  Maximize2, 
  X, 
  Check, 
  Loader, 
  AlertCircle,
  Upload,
  FileText,
  ChevronDown,
  ChevronUp,
  Bell
} from 'lucide-react';
import { useBackgroundTask } from '../contexts/BackgroundTaskContext';
import { useLanguage } from '../contexts/LanguageContext';

const TaskItem = memo(({ task }) => {
  const { language } = useLanguage();
  
  const getStatusIcon = () => {
    switch (task.status) {
      case 'completed':
        return <Check className="w-4 h-4 text-emerald-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'cancelled':
        return <X className="w-4 h-4 text-gray-400" />;
      default:
        return <Loader className="w-4 h-4 text-blue-500 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (task.status) {
      case 'completed':
        return 'bg-emerald-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getStatusText = () => {
    switch (task.status) {
      case 'uploading':
        return language === 'es' ? 'Subiendo...' : 'Uploading...';
      case 'processing':
        return language === 'es' ? 'Procesando embeddings...' : 'Processing embeddings...';
      case 'completed':
        return language === 'es' ? '¡Completado!' : 'Completed!';
      case 'error':
        return 'Error';
      case 'cancelled':
        return language === 'es' ? 'Cancelado' : 'Cancelled';
      default:
        return '';
    }
  };

  return (
    <div className="p-3 border-b border-slate-200 dark:border-slate-700 last:border-b-0">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          {getStatusIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
            {task.sessionName}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {task.currentFile}/{task.totalFiles} {language === 'es' ? 'archivos' : 'files'} • {getStatusText()}
          </p>
        </div>
      </div>
      
      {/* Progress bar */}
      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-300 ${getStatusColor()}`}
          style={{ width: `${task.percent}%` }}
        />
      </div>

      {/* Latest log entry */}
      {task.logs && task.logs.length > 0 && (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 font-mono truncate">
          {task.logs[task.logs.length - 1]}
        </p>
      )}
    </div>
  );
});

TaskItem.displayName = 'TaskItem';

const BackgroundUploadWidget = memo(() => {
  const { 
    tasks, 
    isMinimized, 
    hasActiveTasks,
    activeTasksCount,
    completedTasksCount,
    toggleMinimize,
    removeTask
  } = useBackgroundTask();
  const { language } = useLanguage();
  const notifiedTasksRef = useRef(new Set());

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Send browser notification when task completes
  useEffect(() => {
    const taskList = Object.values(tasks);
    
    taskList.forEach(task => {
      // Only notify once per task when it completes
      if (task.status === 'completed' && !notifiedTasksRef.current.has(task.id)) {
        notifiedTasksRef.current.add(task.id);
        
        // Browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
          const title = language === 'es' ? '✅ CVs procesados' : '✅ CVs processed';
          const body = language === 'es' 
            ? `${task.totalFiles} CV(s) añadidos a "${task.sessionName}"`
            : `${task.totalFiles} CV(s) added to "${task.sessionName}"`;
          
          try {
            new Notification(title, {
              body,
              icon: '/vite.svg',
              tag: `cv-upload-${task.id}`,
              requireInteraction: false
            });
          } catch (e) {
            console.log('Notification error:', e);
          }
        }
      }
    });
    
    // Clean up old task IDs from the set
    const currentTaskIds = new Set(taskList.map(t => t.id));
    notifiedTasksRef.current.forEach(id => {
      if (!currentTaskIds.has(id)) {
        notifiedTasksRef.current.delete(id);
      }
    });
  }, [tasks, language]);

  const taskList = Object.values(tasks);
  
  // Don't render if no tasks
  if (taskList.length === 0) {
    return null;
  }

  // Minimized view - floating pill
  if (isMinimized) {
    return (
      <button
        onClick={toggleMinimize}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-full shadow-lg shadow-blue-500/30 transition-all hover:scale-105 animate-pulse-subtle"
        aria-label={language === 'es' ? 'Mostrar progreso de subida' : 'Show upload progress'}
      >
        <Loader className="w-4 h-4 animate-spin" />
        <span className="text-sm font-medium">
          {activeTasksCount > 0 
            ? (language === 'es' 
                ? `Subiendo ${activeTasksCount} tarea(s)...` 
                : `Uploading ${activeTasksCount} task(s)...`)
            : (language === 'es' ? 'Ver completados' : 'View completed')
          }
        </span>
        <Maximize2 className="w-4 h-4" />
      </button>
    );
  }

  // Expanded view - floating panel
  return (
    <div className="fixed bottom-4 right-4 z-50 w-80 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Upload className="w-4 h-4 text-blue-500" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {language === 'es' ? 'Subida en segundo plano' : 'Background Upload'}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {activeTasksCount > 0 
                ? (language === 'es' 
                    ? `${activeTasksCount} tarea(s) activa(s)` 
                    : `${activeTasksCount} active task(s)`)
                : (language === 'es' ? 'Todo completado' : 'All completed')
              }
            </p>
          </div>
        </div>
        <button
          onClick={toggleMinimize}
          className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
          aria-label={language === 'es' ? 'Minimizar' : 'Minimize'}
        >
          <Minimize2 className="w-4 h-4 text-slate-500" />
        </button>
      </div>

      {/* Info banner for active tasks */}
      {hasActiveTasks && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800">
          <p className="text-xs text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
            <Bell className="w-3.5 h-3.5" />
            {language === 'es' 
              ? 'Puedes minimizar y seguir trabajando. Te notificaremos cuando termine.'
              : 'You can minimize and keep working. We\'ll notify you when done.'}
          </p>
        </div>
      )}

      {/* Task list */}
      <div className="max-h-72 overflow-y-auto">
        {taskList.map(task => (
          <TaskItem key={task.id} task={task} />
        ))}
      </div>

      {/* Footer with minimize hint */}
      {hasActiveTasks && (
        <div className="px-4 py-2 bg-slate-50 dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={toggleMinimize}
            className="w-full flex items-center justify-center gap-2 text-xs text-slate-500 hover:text-blue-500 transition-colors"
          >
            <Minimize2 className="w-3.5 h-3.5" />
            {language === 'es' ? 'Minimizar y continuar trabajando' : 'Minimize and continue working'}
          </button>
        </div>
      )}
    </div>
  );
});

BackgroundUploadWidget.displayName = 'BackgroundUploadWidget';

export default BackgroundUploadWidget;
