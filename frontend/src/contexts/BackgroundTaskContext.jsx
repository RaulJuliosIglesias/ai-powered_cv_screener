import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { uploadCVsToSession, getSessionUploadStatus, generateSessionName, updateSession } from '../services/api';
import { getSettings } from '../components/modals/SettingsModal';

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
    isFirstUpload = false,  // Only auto-name if this is the first upload to the session
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

        // Check for duplicates in response
        const duplicates = res.duplicates || [];
        const filesProcessing = res.files_processing || 0;
        
        // If all files are duplicates, complete immediately
        if (filesProcessing === 0 && duplicates.length > 0) {
          const dupList = duplicates.length <= 3 
            ? duplicates.join(', ') 
            : `${duplicates.slice(0, 3).join(', ')} +${duplicates.length - 3}`;
          
          updateTaskInternal(taskId, {
            status: 'completed',
            percent: 100,
            duplicates: duplicates,
            logs: [language === 'es' 
              ? `⚠️ CVs duplicados (ya existen): ${dupList}` 
              : `⚠️ Duplicate CVs (already exist): ${dupList}`],
            endTime: Date.now()
          }, true);

          if (onCompleteCallbacks.current[taskId]) {
            onCompleteCallbacks.current[taskId]({ taskId, sessionId, filesCount: 0, duplicates });
          }

          setTimeout(() => removeTask(taskId), 8000);
          return;
        }

        // Build log message including duplicates if any
        let logMsg = language === 'es' ? 'Procesando en servidor...' : 'Processing on server...';
        if (duplicates.length > 0) {
          const dupList = duplicates.length <= 2 
            ? duplicates.join(', ') 
            : `${duplicates.slice(0, 2).join(', ')} +${duplicates.length - 2}`;
          logMsg = language === 'es' 
            ? `⚠️ ${duplicates.length} duplicado(s): ${dupList}. Procesando ${filesProcessing}...`
            : `⚠️ ${duplicates.length} duplicate(s): ${dupList}. Processing ${filesProcessing}...`;
        }

        // Update to processing phase (single UI update)
        updateTaskInternal(taskId, {
          percent: 50,
          status: 'processing',
          phase: 'processing',
          duplicates: duplicates,
          logs: [logMsg]
        }, true);

        const totalFiles = filesProcessing;
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
              // Completed - final UI update with duplicate info
              let finalLog = language === 'es' ? '✓ ¡Completado!' : '✓ Complete!';
              if (duplicates.length > 0) {
                finalLog += language === 'es' 
                  ? ` (${duplicates.length} duplicado(s) omitido(s))` 
                  : ` (${duplicates.length} duplicate(s) skipped)`;
              }
              
              updateTaskInternal(taskId, {
                status: 'completed',
                currentFile: totalFiles,
                percent: 100,
                logs: [finalLog],
                endTime: Date.now()
              }, true);

              // Auto-naming: Generate name for the session if enabled
              const settings = getSettings();
              if (settings.autoNamingEnabled && totalFiles > 0) {
                try {
                  updateTaskInternal(taskId, {
                    logs: [language === 'es' ? '🤖 Generando nombre...' : '🤖 Generating name...']
                  }, true);
                  
                  const nameResult = await generateSessionName(sessionId, settings.autoNamingModel, mode);
                  if (nameResult && nameResult.full_name) {
                    await updateSession(sessionId, { name: nameResult.full_name }, mode);
                    updateTaskInternal(taskId, {
                      logs: [language === 'es' ? `✓ Nombre: ${nameResult.full_name}` : `✓ Named: ${nameResult.full_name}`]
                    }, true);
                  }
                } catch (nameError) {
                  console.error('Auto-naming failed:', nameError);
                  // Don't fail the whole upload if naming fails
                }
              }

              if (onCompleteCallbacks.current[taskId]) {
                onCompleteCallbacks.current[taskId]({ taskId, sessionId, filesCount: totalFiles, duplicates });
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

  // Get set of session IDs that are currently processing
  const getProcessingSessionIds = useCallback(() => {
    const ids = new Set();
    Object.values(tasksRef.current).forEach(t => {
      if (t.status === 'uploading' || t.status === 'processing') {
        ids.add(t.sessionId);
      }
    });
    return ids;
  }, []);

  // Check if a specific session is processing
  const isSessionProcessing = useCallback((sessionId) => {
    return Object.values(tasksRef.current).some(t => 
      t.sessionId === sessionId && (t.status === 'uploading' || t.status === 'processing')
    );
  }, []);

  // Get processing info for a session
  const getSessionProcessingInfo = useCallback((sessionId) => {
    const task = Object.values(tasksRef.current).find(t => 
      t.sessionId === sessionId && (t.status === 'uploading' || t.status === 'processing')
    );
    if (!task) return null;
    return {
      percent: task.percent,
      phase: task.phase,
      currentFile: task.currentFile,
      totalFiles: task.totalFiles,
      status: task.status
    };
  }, []);

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
      toggleMinimize,
      getProcessingSessionIds,
      isSessionProcessing,
      getSessionProcessingInfo
    }}>
      {children}
    </BackgroundTaskContext.Provider>
  );
}

export default BackgroundTaskContext;
