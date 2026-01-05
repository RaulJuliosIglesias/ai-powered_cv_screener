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
  // Active upload tasks: { taskId: { sessionId, files, progress, status, logs, ... } }
  const [tasks, setTasks] = useState({});
  const [isMinimized, setIsMinimized] = useState(false);
  const taskIdCounter = useRef(0);
  
  // Callbacks for task completion
  const onCompleteCallbacks = useRef({});

  const generateTaskId = useCallback(() => {
    taskIdCounter.current += 1;
    return `upload-${Date.now()}-${taskIdCounter.current}`;
  }, []);

  const updateTask = useCallback((taskId, updates) => {
    setTasks(prev => {
      if (!prev[taskId]) return prev;
      return {
        ...prev,
        [taskId]: { ...prev[taskId], ...updates }
      };
    });
  }, []);

  const removeTask = useCallback((taskId) => {
    setTasks(prev => {
      const newTasks = { ...prev };
      delete newTasks[taskId];
      return newTasks;
    });
    delete onCompleteCallbacks.current[taskId];
  }, []);

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
    // Convert FileList to Array immediately to avoid issues
    const filesArray = Array.from(files);
    const fileNames = filesArray.map(f => f.name);
    
    // Store callbacks
    if (onComplete) {
      onCompleteCallbacks.current[taskId] = onComplete;
    }
    const storedOnError = onError;

    // Initialize task immediately (synchronous)
    setTasks(prev => ({
      ...prev,
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
        logs: [language === 'es' ? `Iniciando subida de ${filesArray.length} archivo(s)...` : `Starting upload of ${filesArray.length} file(s)...`],
        startTime: Date.now(),
        language
      }
    }));

    // Auto-expand when starting
    setIsMinimized(false);

    // Use a proper async IIFE that doesn't block - runs completely detached
    // The key is to NOT await this, just fire and forget
    const runUpload = async () => {
      try {
        // Upload phase (0% to 50%)
        const res = await uploadCVsToSession(sessionId, filesArray, mode, (uploadPercent) => {
          const realPercent = Math.round(uploadPercent * 0.5);
          updateTask(taskId, { 
            percent: realPercent,
            phase: 'upload'
          });
        });

        // Processing phase - poll for real progress
        const phaseNames = {
          extracting: language === 'es' ? 'Extrayendo texto' : 'Extracting text',
          saving: language === 'es' ? 'Guardando PDF' : 'Saving PDF',
          chunking: language === 'es' ? 'Dividiendo en chunks' : 'Chunking',
          embedding: language === 'es' ? 'Creando embeddings' : 'Creating embeddings',
          indexing: language === 'es' ? 'Indexando' : 'Indexing',
          done: language === 'es' ? 'Completado' : 'Done'
        };

        setTasks(prev => {
          if (!prev[taskId]) return prev;
          return {
            ...prev,
            [taskId]: {
              ...prev[taskId],
              percent: 50,
              status: 'processing',
              phase: 'processing',
              logs: [...prev[taskId].logs, language === 'es' ? 'Procesando archivos...' : 'Processing files...']
            }
          };
        });

        let lastProcessed = 0;
        let lastPhase = '';
        const totalFiles = filesArray.length;

        const poll = async () => {
          try {
            const status = await getSessionUploadStatus(sessionId, res.job_id);
            const processed = status.processed_files || 0;
            const currentFile = status.current_file;
            const currentPhase = status.current_phase;

            const phaseProgress = { extracting: 10, saving: 20, chunking: 40, embedding: 80, indexing: 95, done: 100 };
            const fileProgress = processed / totalFiles;
            const currentFileProgress = currentPhase ? (phaseProgress[currentPhase] || 0) / 100 / totalFiles : 0;
            const totalProgress = 50 + ((fileProgress + currentFileProgress) * 50);

            if (status.status === 'processing') {
              setTasks(prev => {
                if (!prev[taskId]) return prev;
                let newLogs = [...prev[taskId].logs];

                if (currentFile && currentPhase && currentPhase !== lastPhase) {
                  const phaseName = phaseNames[currentPhase] || currentPhase;
                  const shortName = currentFile.length > 25 ? currentFile.slice(0, 22) + '...' : currentFile;
                  newLogs.push(`${phaseName}: ${shortName}`);
                  lastPhase = currentPhase;
                }

                if (processed > lastProcessed) {
                  const completedFile = fileNames[processed - 1] || `CV ${processed}`;
                  const shortName = completedFile.length > 25 ? completedFile.slice(0, 22) + '...' : completedFile;
                  newLogs.push(language === 'es' ? `✓ Completado: ${shortName}` : `✓ Done: ${shortName}`);
                  lastProcessed = processed;
                }

                return {
                  ...prev,
                  [taskId]: {
                    ...prev[taskId],
                    currentFile: processed,
                    percent: Math.min(99, Math.round(totalProgress)),
                    logs: newLogs.slice(-8)
                  }
                };
              });
              setTimeout(poll, 150);
            } else {
              // Completed
              setTasks(prev => {
                if (!prev[taskId]) return prev;
                return {
                  ...prev,
                  [taskId]: {
                    ...prev[taskId],
                    status: 'completed',
                    currentFile: totalFiles,
                    percent: 100,
                    logs: [...prev[taskId].logs.slice(-7), language === 'es' ? '✓ ¡Todo completado!' : '✓ All completed!'],
                    endTime: Date.now()
                  }
                };
              });

              // Execute completion callback
              if (onCompleteCallbacks.current[taskId]) {
                onCompleteCallbacks.current[taskId]({ taskId, sessionId, filesCount: totalFiles });
              }

              // Auto-remove completed task after delay
              setTimeout(() => {
                removeTask(taskId);
              }, 5000);
            }
          } catch (pollError) {
            console.error('Polling error:', pollError);
            setTimeout(poll, 500);
          }
        };

        poll();

      } catch (error) {
        console.error('Upload error:', error);
        setTasks(prev => {
          if (!prev[taskId]) return prev;
          return {
            ...prev,
            [taskId]: {
              ...prev[taskId],
              status: 'error',
              error: error.message,
              logs: [...prev[taskId].logs, `Error: ${error.message}`]
            }
          };
        });

        if (storedOnError) {
          storedOnError(error);
        }

        setTimeout(() => {
          removeTask(taskId);
        }, 10000);
      }
    };

    // Fire and forget - don't await, don't block
    // Using Promise.resolve().then() ensures it runs in the next microtask
    Promise.resolve().then(() => runUpload());

    // Return taskId immediately - upload runs in background
    return taskId;
  }, [generateTaskId, updateTask, removeTask]);

  const cancelTask = useCallback((taskId) => {
    // Mark as cancelled and remove
    setTasks(prev => {
      if (!prev[taskId]) return prev;
      return {
        ...prev,
        [taskId]: { ...prev[taskId], status: 'cancelled' }
      };
    });
    setTimeout(() => removeTask(taskId), 1000);
  }, [removeTask]);

  const minimize = useCallback(() => setIsMinimized(true), []);
  const maximize = useCallback(() => setIsMinimized(false), []);
  const toggleMinimize = useCallback(() => setIsMinimized(prev => !prev), []);

  const hasActiveTasks = Object.values(tasks).some(t => 
    t.status === 'uploading' || t.status === 'processing'
  );

  const activeTasksCount = Object.values(tasks).filter(t => 
    t.status === 'uploading' || t.status === 'processing'
  ).length;

  const completedTasksCount = Object.values(tasks).filter(t => 
    t.status === 'completed'
  ).length;

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
