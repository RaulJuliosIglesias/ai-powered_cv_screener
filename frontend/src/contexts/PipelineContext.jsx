import { createContext, useContext, useState, useCallback, useRef, useMemo } from 'react';

const PipelineContext = createContext(null);

export function usePipeline() {
  const context = useContext(PipelineContext);
  if (!context) {
    throw new Error('usePipeline must be used within a PipelineProvider');
  }
  return context;
}

const INITIAL_PIPELINE_STATE = {
  query_understanding: { status: 'pending' },
  multi_query: { status: 'pending' },
  guardrail: { status: 'pending' },
  embedding: { status: 'pending' },
  retrieval: { status: 'pending' },
  reranking: { status: 'pending' },
  reasoning: { status: 'pending' },
  generation: { status: 'pending' },
  verification: { status: 'pending' },
  refinement: { status: 'pending' }
};

export function PipelineProvider({ children }) {
  // Pipeline state PER SESSION (same pattern as BackgroundTaskContext)
  const pipelineBySessionRef = useRef({});
  const [version, setVersion] = useState(0);
  
  // Currently active session (the one user is viewing)
  const [activeSessionId, setActiveSessionId] = useState(null);
  
  // MULTIPLE streaming sessions - using Set to track ALL active pipelines
  const streamingSessionsRef = useRef(new Set());
  const [streamingVersion, setStreamingVersion] = useState(0);

  const triggerUpdate = useCallback(() => {
    setVersion(v => v + 1);
  }, []);
  
  const triggerStreamingUpdate = useCallback(() => {
    setStreamingVersion(v => v + 1);
  }, []);

  // Initialize pipeline for a session (called when query starts)
  const initPipeline = useCallback((sessionId) => {
    console.log(`[Pipeline] Initializing pipeline for session ${sessionId.slice(0,8)}`);
    pipelineBySessionRef.current[sessionId] = {
      ...INITIAL_PIPELINE_STATE,
      isStreaming: true,
      startedAt: Date.now()
    };
    // Add to streaming sessions Set (supports multiple)
    streamingSessionsRef.current.add(sessionId);
    triggerUpdate();
    triggerStreamingUpdate();
  }, [triggerUpdate, triggerStreamingUpdate]);

  // Update a step during SSE streaming
  const updateStep = useCallback((sessionId, stepName, status, details = null) => {
    if (!pipelineBySessionRef.current[sessionId]) {
      // Initialize if not exists (edge case)
      pipelineBySessionRef.current[sessionId] = {
        ...INITIAL_PIPELINE_STATE,
        isStreaming: true,
        startedAt: Date.now()
      };
    }
    
    pipelineBySessionRef.current[sessionId] = {
      ...pipelineBySessionRef.current[sessionId],
      [stepName]: { status, details }
    };
    triggerUpdate();
  }, [triggerUpdate]);

  // Complete pipeline (mark as finished and CLEAR from memory)
  // The next time user switches to this chat, it will derive from saved messages
  const completePipeline = useCallback((sessionId) => {
    console.log(`[Pipeline] Completing pipeline for session ${sessionId.slice(0,8)}`);
    // Clear from memory so next load derives from messages
    delete pipelineBySessionRef.current[sessionId];
    // Remove from streaming sessions Set
    streamingSessionsRef.current.delete(sessionId);
    triggerUpdate();
    triggerStreamingUpdate();
  }, [triggerUpdate, triggerStreamingUpdate]);

  // Clear pipeline for a session (called on error or reset)
  const clearPipeline = useCallback((sessionId) => {
    console.log(`[Pipeline] Clearing pipeline for session ${sessionId.slice(0,8)}`);
    if (pipelineBySessionRef.current[sessionId]) {
      delete pipelineBySessionRef.current[sessionId];
    }
    // Remove from streaming sessions Set
    streamingSessionsRef.current.delete(sessionId);
    triggerUpdate();
    triggerStreamingUpdate();
  }, [triggerUpdate, triggerStreamingUpdate]);

  // Derive pipeline from last message (called when switching chats)
  const derivePipelineFromMessages = useCallback((sessionId, messages) => {
    console.log(`[Pipeline] Deriving state for session ${sessionId.slice(0,8)} from ${messages?.length || 0} messages`);
    
    if (!messages || messages.length === 0) {
      // No messages = no pipeline to show
      pipelineBySessionRef.current[sessionId] = null;
      triggerUpdate();
      return;
    }
    
    // Find last assistant message with pipeline_steps
    const lastAssistant = [...messages]
      .reverse()
      .find(m => m.role === 'assistant' && m.pipeline_steps?.length > 0);
    
    if (lastAssistant?.pipeline_steps && lastAssistant.pipeline_steps.length > 0) {
      console.log(`[Pipeline] Found ${lastAssistant.pipeline_steps.length} steps in last message`);
      
      // Start with all steps as completed (default for finished pipelines)
      const derivedState = {};
      Object.keys(INITIAL_PIPELINE_STATE).forEach(key => {
        derivedState[key] = { status: 'completed' };
      });
      
      // Override with actual data from saved steps
      lastAssistant.pipeline_steps.forEach(step => {
        const stepName = step.name || step.step;
        if (stepName && derivedState[stepName] !== undefined) {
          derivedState[stepName] = {
            status: step.status || 'completed',
            details: step.details,
            duration_ms: step.duration_ms
          };
        }
      });
      
      derivedState.isStreaming = false;
      derivedState.derivedFromMessage = true;
      derivedState.completedAt = Date.now();
      pipelineBySessionRef.current[sessionId] = derivedState;
      
      console.log(`[Pipeline] Derived state:`, Object.keys(derivedState).filter(k => !['isStreaming', 'derivedFromMessage', 'completedAt'].includes(k)).map(k => `${k}:${derivedState[k]?.status}`).join(', '));
    } else {
      // No pipeline_steps in messages = show empty/null state
      console.log(`[Pipeline] No pipeline_steps found in messages`);
      pipelineBySessionRef.current[sessionId] = null;
    }
    triggerUpdate();
  }, [triggerUpdate]);

  // Set active session (called when user switches chat)
  const setActiveSession = useCallback((sessionId, messages = []) => {
    setActiveSessionId(sessionId);
    
    // CRITICAL: Check if this session is CURRENTLY streaming (using Set)
    const isCurrentlyStreaming = streamingSessionsRef.current.has(sessionId);
    
    if (isCurrentlyStreaming) {
      // Session is actively streaming - keep the real-time state
      // FORCE update to ensure UI shows current state immediately
      console.log(`[Pipeline] Session ${sessionId.slice(0,8)} is STREAMING - forcing UI update`);
      triggerUpdate(); // Force re-render to show current pipeline state
    } else {
      // Session is NOT streaming - ALWAYS derive from saved messages
      // This ensures we show the correct final state or reset
      console.log(`[Pipeline] Session ${sessionId.slice(0,8)} is IDLE - deriving from messages`);
      derivePipelineFromMessages(sessionId, messages);
    }
  }, [derivePipelineFromMessages, triggerUpdate]);

  // Get pipeline for current active session
  // Returns a fresh copy to ensure React detects changes
  const activePipeline = useMemo(() => {
    if (!activeSessionId) return null;
    const pipeline = pipelineBySessionRef.current[activeSessionId];
    if (!pipeline) return null;
    // Return a shallow copy to ensure React sees it as a new object
    return { ...pipeline };
  }, [activeSessionId, version]); // eslint-disable-line react-hooks/exhaustive-deps

  // Is current session streaming? (using Set)
  const isActiveStreaming = useMemo(() => {
    return activeSessionId ? streamingSessionsRef.current.has(activeSessionId) : false;
  }, [activeSessionId, streamingVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  // Clean up old sessions (memory management)
  const cleanupOldSessions = useCallback((keepSessionIds) => {
    const keep = new Set(keepSessionIds);
    Object.keys(pipelineBySessionRef.current).forEach(id => {
      if (!keep.has(id)) {
        delete pipelineBySessionRef.current[id];
      }
    });
  }, []);

  // Get pipeline for any specific session
  const getPipelineForSession = useCallback((sessionId) => {
    return pipelineBySessionRef.current[sessionId] || null;
  }, [version]); // eslint-disable-line react-hooks/exhaustive-deps

  // Check if a specific session is streaming (using Set)
  const isSessionStreaming = useCallback((sessionId) => {
    return streamingSessionsRef.current.has(sessionId);
  }, [streamingVersion]); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Get count of currently streaming sessions
  const streamingCount = useMemo(() => {
    return streamingSessionsRef.current.size;
  }, [streamingVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <PipelineContext.Provider value={{
      // State
      activePipeline,
      activeSessionId,
      isActiveStreaming,
      streamingCount,
      
      // Actions
      initPipeline,
      updateStep,
      completePipeline,
      clearPipeline,
      setActiveSession,
      derivePipelineFromMessages,
      cleanupOldSessions,
      
      // Getters for any session
      getPipelineForSession,
      isSessionStreaming
    }}>
      {children}
    </PipelineContext.Provider>
  );
}

export default PipelineContext;
