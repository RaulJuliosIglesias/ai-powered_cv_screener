import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { uploadCVsToSession, getSessionUploadStatus } from '../services/api';

const BackgroundTaskContext = createContext(null);

export function useBackgroundTask() {
  const context = useContext(BackgroundTaskContext);
  if (!context) {
    throw new Error('useBackgroundTask must be used within a BackgroundTaskProvider');
  }
  return context;
}

export function BackgroundTaskProvider({ children }) {
  // Use ref for internal state to avoid re-renders, useState only for UI updates
  const tasksRef = useRef({});
  const [tasksVersion, setTasksVersion] = useState(0); // Increment to trigger re-render when needed
  const [isMinimized, setIsMinimized] = useState(false);
  const taskIdCounter = useRef(0);
  const onCompleteCallbacks = useRef({});
  const updateScheduled = useRef(false);

  // Get current tasks (from ref, not state)
  const getTasks = useCallback(() => tasksRef.current, []);

  // Schedule a UI update (batched)
  const scheduleUIUpdate = useCallback(() => {
    if (!updateScheduled.current) {
      updateScheduled.current = true;
      // Use requestIdleCallback if available, otherwise requestAnimationFrame
      const schedule = window.requestIdleCallback || requestAnimationFrame;
      schedule(() => {
        updateScheduled.current = false;
        setTasksVersion(v => v + 1);
      });
    }
  }, []);

  const generateTaskId = useCallback(() => {
    taskIdCounter.current += 1;
    return `upload-${Date.now()}-${taskIdCounter.current}`;
  }, []);

  const updateTaskInternal = useCallback((taskId, updates, triggerUI = false) => {
    if (!tasksRef.current[taskId]) return;
    tasksRef.current = {
      ...tasksRef.current,
      [taskId]: { ...tasksRef.current[taskId], ...updates }
    };
    if (triggerUI) scheduleUIUpdate();
  }, [scheduleUIUpdate]);

  const removeTask = useCallback((taskId) => {
    const newTasks = { ...tasksRef.current };
    delete newTasks[taskId];
    tasksRef.current = newTasks;
    delete onCompleteCallbacks.current[taskId];
    scheduleUIUpdate();
  }, [scheduleUIUpdate]);

  const startUploadTask = useCallback(({
    sessionId,
    sessionName,
    files,
    mode,
    language,
    onComplete,
    onError
  }) => {
    const taskId = generateTaskId();
    const filesArray = Array.from(files);
    const fileNames = filesArray.map(f => f.name);
    
    if (onComplete) {
      onCompleteCallbacks.current[taskId] = onComplete;
    }
    const storedOnError = onError;

    // Initialize task in ref (no re-render yet)
    tasksRef.current = {
      ...tasksRef.current,
      [taskId]: {
        id: taskId,
        sessionId,
        sessionName: sessionName || `Session ${sessionId.slice(0, 8)}`,
        files: fileNames,
        totalFiles: filesArray.length,
        currentFile: 0,
        percent: 0,
        status: 'uploading',
        phase: 'upload',
        logs: [language === 'es' ? `Subiendo ${filesArray.length} archivo(s)...` : `Uploading ${filesArray.length} file(s)...`],
        startTime: Date.now(),
        language
      }
    };

    // Now trigger UI update and expand
    setIsMinimized(false);
    scheduleUIUpdate();

    // Run upload completely detached using setTimeout(0)
    setTimeout(async () => {
      try {
        // Upload phase - NO UI updates during upload to avoid blocking
        const res = await uploadCVsToSession(sessionId, filesArray, mode);

        // Update to processing phase (single UI update)
        updateTaskInternal(taskId, {
          percent: 50,
          status: 'processing',
          phase: 'processing',
          logs: [language === 'es' ? 'Procesando en servidor...' : 'Processing on server...']
        }, true);

        const totalFiles = filesArray.length;
        let lastProcessed = 0;

        // Poll with minimal UI updates
        const poll = async () => {
          try {
            const status = await getSessionUploadStatus(sessionId, res.job_id);
            const processed = status.processed_files || 0;

            if (status.status === 'processing') {
              // Only update UI when a file completes
              if (processed > lastProcessed) {
                const percent = 50 + Math.round((processed / totalFiles) * 50);
                updateTaskInternal(taskId, {
                  currentFile: processed,
                  percent: Math.min(99, percent),
                  logs: [language === 'es' ? `Procesado ${processed}/${totalFiles}` : `Processed ${processed}/${totalFiles}`]
                }, true);
                lastProcessed = processed;
              }
              setTimeout(poll, 1000); // Poll every 1 second
            } else {
              // Completed - final UI update
              updateTaskInternal(taskId, {
                status: 'completed',
                currentFile: totalFiles,
                percent: 100,
                logs: [language === 'es' ? '✓ ¡Completado!' : '✓ Complete!'],
                endTime: Date.now()
              }, true);

              if (onCompleteCallbacks.current[taskId]) {
                onCompleteCallbacks.current[taskId]({ taskId, sessionId, filesCount: totalFiles });
              }

              setTimeout(() => removeTask(taskId), 5000);
            }
          } catch (pollError) {
            console.error('Polling error:', pollError);
            setTimeout(poll, 2000);
          }
        };

        poll();

      } catch (error) {
        console.error('Upload error:', error);
        updateTaskInternal(taskId, {
          status: 'error',
          error: error.message,
          logs: [`Error: ${error.message}`]
        }, true);

        if (storedOnError) storedOnError(error);
        setTimeout(() => removeTask(taskId), 10000);
      }
    }, 0);

    return taskId;
  }, [generateTaskId, updateTaskInternal, removeTask, scheduleUIUpdate]);

  const cancelTask = useCallback((taskId) => {
    updateTaskInternal(taskId, { status: 'cancelled' }, true);
    setTimeout(() => removeTask(taskId), 1000);
  }, [updateTaskInternal, removeTask]);

  const minimize = useCallback(() => setIsMinimized(true), []);
  const maximize = useCallback(() => setIsMinimized(false), []);
  const toggleMinimize = useCallback(() => setIsMinimized(prev => !prev), []);

  // Compute derived values from ref (re-computed when tasksVersion changes)
  const tasks = tasksRef.current;
  const hasActiveTasks = Object.values(tasks).some(t => 
    t.status === 'uploading' || t.status === 'processing'
  );
  const activeTasksCount = Object.values(tasks).filter(t => 
    t.status === 'uploading' || t.status === 'processing'
  ).length;
  const completedTasksCount = Object.values(tasks).filter(t => 
    t.status === 'completed'
  ).length;

  // tasksVersion is used to trigger re-renders - eslint-disable-next-line
  void tasksVersion;

  return (
    <BackgroundTaskContext.Provider value={{
      tasks,
      isMinimized,
      hasActiveTasks,
      activeTasksCount,
      completedTasksCount,
      startUploadTask,
      cancelTask,
      removeTask,
      minimize,
      maximize,
      toggleMinimize
    }}>
      {children}
    </BackgroundTaskContext.Provider>
  );
}

export default BackgroundTaskContext;
