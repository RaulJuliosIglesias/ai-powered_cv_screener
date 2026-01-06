import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Plus, MessageSquare, Trash2, Send, Loader, Upload, FileText, X, Check, CheckCircle, Edit2, Moon, Sun, Sparkles, User, Database, Cloud, Globe, Settings, ChevronRight, Copy, Eye, ExternalLink, Sliders, BarChart3, RotateCcw, Info, Github, Linkedin } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import useMode from './hooks/useMode';
import useTheme from './hooks/useTheme';
import useToast from './hooks/useToast';
import { useLanguage } from './contexts/LanguageContext';
import { useBackgroundTask } from './contexts/BackgroundTaskContext';
import { usePipeline } from './contexts/PipelineContext';
import SourceBadge from './components/SourceBadge';
import ModelSelector from './components/ModelSelector';
import RAGPipelineSettings, { getRAGPipelineSettings } from './components/RAGPipelineSettings';
import MetricsPanel, { saveMetricEntry } from './components/MetricsPanel';
import PipelineProgressPanel from './components/PipelineProgressPanel';
import ChatInputField from './components/ChatInputField';
import { StructuredOutputRenderer } from './components/output';
import Sidebar from './components/Sidebar';
import Toast from './components/Toast';
import BackgroundUploadWidget from './components/BackgroundUploadWidget';
import { AboutModal, SettingsModal } from './components/modals';
import { SessionSkeleton, MessageSkeleton } from './components/SkeletonLoader';
import { MemoizedTable, MemoizedCodeBlock } from './components/MemoizedTable';
import StreamingMessage from './components/StreamingMessage';
import SuggestionsPanel from './components/SuggestionsPanel';
import EmptySessionDropzone from './components/EmptySessionDropzone';
import { preprocessContent, parseCVFilename } from './utils/contentProcessor';
import { getSessions, createSession, getSession, deleteSession, updateSession, uploadCVsToSession, getSessionUploadStatus, removeCVFromSession, sendSessionMessage, getSessionSuggestions, getCVList, clearSessionCVs, deleteAllCVsFromDatabase, deleteCV, deleteMessage, deleteMessagesFrom, generateSessionName } from './services/api';
import { getSettings } from './components/modals/SettingsModal';

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [chatLoadingStates, setChatLoadingStates] = useState({});
  const [pendingMessages, setPendingMessages] = useState({}); // {sessionId: {userMsg, status}}
  const isChatLoading = currentSessionId ? chatLoadingStates[currentSessionId] : false;
  const currentSessionIdRef = useRef(currentSessionId);
  
  // Keep ref in sync with state
  useEffect(() => {
    currentSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);
    const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [deletingSessionId, setDeletingSessionId] = useState(null);
  const [deleteMessageConfirm, setDeleteMessageConfirm] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [aiRenamingSessionId, setAiRenamingSessionId] = useState(null);
  const [allCVs, setAllCVs] = useState([]);
  const [showCVPanel, setShowCVPanel] = useState(false);
  const [cvPanelSessionId, setCvPanelSessionId] = useState(null);
  const [cvPanelSession, setCvPanelSession] = useState(null);
  const cvPanelFileInputRef = useRef(null);
  const [isLoadingMode, setIsLoadingMode] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const [pdfViewerUrl, setPdfViewerUrl] = useState(null);
  const [pdfViewerTitle, setPdfViewerTitle] = useState('');
  const [showRAGSettings, setShowRAGSettings] = useState(false);
  const [ragPipelineSettings, setRagPipelineSettings] = useState(getRAGPipelineSettings());
  const [showMetricsPanel, setShowMetricsPanel] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [showPipelinePanel, setShowPipelinePanel] = useState(true);
  const [isPipelineExpanded, setIsPipelineExpanded] = useState(false);
  const [autoExpandPipeline, setAutoExpandPipeline] = useState(() => {
    const saved = localStorage.getItem('autoExpandPipeline');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [showStreamingPreview, setShowStreamingPreview] = useState(() => {
    const saved = localStorage.getItem('showStreamingPreview');
    return saved !== null ? JSON.parse(saved) : true;
  });
  // Pipeline state moved to PipelineContext for per-session tracking
  
  // Streaming state for progressive message display - PER SESSION
  const [streamingStateBySession, setStreamingStateBySession] = useState({});
  // { sessionId: { currentStep: 'query_understanding', steps: {}, queryUnderstanding: null, candidates: [], partialAnswer: null } }
  
  // Get streaming state for current session
  const streamingState = currentSessionId ? streamingStateBySession[currentSessionId] : null;
  
  // Delete progress modal state (for bulk deletion)
  const [deleteProgress, setDeleteProgress] = useState(null);
  // { current: 0, total: 5, status: 'deleting' | 'completed', logs: ['Deleting CV 1/5...'] }
  
  // State for collapsible sessions in CV panel
  const [expandedSessions, setExpandedSessions] = useState({});
  const [loadedSessionCVs, setLoadedSessionCVs] = useState({}); // Cache loaded CVs per session
  
  
  const toggleSessionExpand = async (sessionId) => {
    const willExpand = !expandedSessions[sessionId];
    setExpandedSessions(prev => ({ ...prev, [sessionId]: willExpand }));
    
    // Load CVs when expanding if not already loaded
    if (willExpand && !loadedSessionCVs[sessionId]) {
      try {
        const sessionData = await getSession(sessionId, mode);
        setLoadedSessionCVs(prev => ({ ...prev, [sessionId]: sessionData.cvs || [] }));
      } catch (err) {
        console.error('Failed to load session CVs:', err);
      }
    }
  };

  const openPdfViewer = (cvId, filename) => {
    // Use port 8002 to match backend, or use proxy via /api
    const url = `/api/cvs/${cvId}/pdf`;
    // Open directly in new tab
    window.open(url, '_blank');
  };

  const closePdfViewer = () => {
    setPdfViewerUrl(null);
    setPdfViewerTitle('');
  };

  const { toast: toastState, showToast: showToastMessage, hideToast } = useToast();
  const { startUploadTask, hasActiveTasks, isSessionProcessing } = useBackgroundTask();
  const { initPipeline, updateStep, completePipeline, clearPipeline, setActiveSession, activePipeline } = usePipeline();
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const { mode, setMode } = useMode();
  const { theme, toggleTheme } = useTheme();
  const { language, setLanguage } = useLanguage();

  // Auto-scroll to bottom when messages change or when loading starts
  useEffect(() => { 
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); 
  }, [currentSession?.messages]);
  
  // Scroll to bottom when user sends a message (loading starts)
  useEffect(() => {
    if (isChatLoading) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isChatLoading]);

  const loadSessions = useCallback(async () => {
    try { 
      // Only show skeleton on initial load, never on updates
      if (!initialLoadDone) setIsLoadingSessions(true);
      const data = await getSessions(mode); 
      setSessions(data.sessions || []); 
    } catch (e) { 
      console.error(e); 
    } finally {
      setIsLoadingSessions(false);
      if (!initialLoadDone) setInitialLoadDone(true);
    }
  }, [mode, initialLoadDone]);

  const loadSession = useCallback(async (id) => {
    try {
      const data = await getSession(id, mode);
      // Only update if this is still the selected session (avoid race conditions)
      if (currentSessionIdRef.current === id) {
        setCurrentSession(data);
        // Sync pipeline state with this session's messages
        setActiveSession(id, data.messages || []);
        const sugg = await getSessionSuggestions(id, mode);
        if (currentSessionIdRef.current === id) {
          setSuggestions(sugg.suggestions || []);
        }
      }
    } catch (e) { 
      console.error(e); 
      if (currentSessionIdRef.current === id) setCurrentSessionId(null); 
    }
  }, [mode, setActiveSession]);

  // Reload sessions when mode changes
  useEffect(() => { 
    const switchMode = async () => {
      setIsLoadingMode(true);
      setCurrentSessionId(null);
      setCurrentSession(null);
      setSuggestions([]);
      await loadSessions();
      setIsLoadingMode(false);
      showToastMessage(mode === 'cloud' ? (language === 'es' ? 'Modo Supabase activado' : 'Supabase mode activated') : (language === 'es' ? 'Modo Local activado' : 'Local mode activated'));
    };
    switchMode();
  }, [mode]); // eslint-disable-line
  
  useEffect(() => { 
    if (currentSessionId) loadSession(currentSessionId); 
    else { setCurrentSession(null); setSuggestions([]); } 
  }, [currentSessionId, loadSession]);
  
  // Auto-load CVs when panel opens
  useEffect(() => { 
    if (showCVPanel) { 
      getCVList(mode).then(data => setAllCVs(data.cvs || [])).catch(() => {}); 
      // Load specific session if cvPanelSessionId is set
      if (cvPanelSessionId) {
        getSession(cvPanelSessionId, mode).then(data => setCvPanelSession(data)).catch(() => {});
      } else {
        setCvPanelSession(null);
      }
    } else {
      setCvPanelSessionId(null);
      setCvPanelSession(null);
    }
  }, [showCVPanel, cvPanelSessionId, mode]);

  const handleNewChat = async () => {
    const name = language === 'es' ? 'Nuevo chat' : 'New chat';
    const session = await createSession(name, '', mode);
    await loadSessions();
    setCurrentSessionId(session.id);
  };

  const handleDelete = (id) => {
    // If user is viewing the session being deleted, clear it immediately
    if (currentSessionIdRef.current === id) {
      currentSessionIdRef.current = null;
      setCurrentSessionId(null);
      setCurrentSession(null);
    }
    setDeletingSessionId(id);
    setDeleteConfirm(null);
    
    // Run deletion in background - completely non-blocking
    deleteSession(id, mode)
      .then(() => loadSessions())
      .finally(() => setDeletingSessionId(null));
  };

  const handleRename = async (id) => {
    if (!editName.trim()) return;
    await updateSession(id, { name: editName.trim() }, mode);
    await loadSessions();
    if (currentSessionId === id) await loadSession(id);
    setEditingId(null);
  };

  const handleAIRename = async (sessionId) => {
    if (aiRenamingSessionId) return; // Already renaming another session
    setAiRenamingSessionId(sessionId);
    try {
      const settings = getSettings();
      const result = await generateSessionName(sessionId, settings.autoNamingModel, mode);
      if (result && result.full_name) {
        await updateSession(sessionId, { name: result.full_name }, mode);
        await loadSessions();
        if (currentSessionId === sessionId) await loadSession(sessionId);
        showToastMessage(language === 'es' ? `Renombrado: ${result.full_name}` : `Renamed: ${result.full_name}`, 'success');
      }
    } catch (error) {
      console.error('AI rename failed:', error);
      showToastMessage(language === 'es' ? 'Error al renombrar con IA' : 'AI rename failed', 'error');
    } finally {
      setAiRenamingSessionId(null);
    }
  };

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files).filter(f => f.name.endsWith('.pdf'));
    if (!files.length || !currentSessionId) return;
    
    const targetSessionId = currentSessionId;
    const targetSessionName = currentSession?.name || (language === 'es' ? 'Chat actual' : 'Current chat');
    
    // Check if this is the first upload (session has no CVs yet)
    const isFirstUpload = !currentSession?.cvs || currentSession.cvs.length === 0;
    
    // Start background upload task
    startUploadTask({
      sessionId: targetSessionId,
      sessionName: targetSessionName,
      files,
      mode,
      language,
      isFirstUpload,  // Only auto-name if this is the first upload
      onComplete: async ({ sessionId, filesCount }) => {
        // Reload session data when upload completes
        if (currentSessionIdRef.current === sessionId) {
          await loadSession(sessionId);
        }
        await loadSessions();
        showToastMessage(
          language === 'es' 
            ? `✅ ${filesCount} CV(s) procesados correctamente` 
            : `✅ ${filesCount} CV(s) processed successfully`,
          'success'
        );
      },
      onError: (error) => {
        showToastMessage(
          language === 'es' 
            ? `❌ Error al subir CVs: ${error.message}` 
            : `❌ Error uploading CVs: ${error.message}`,
          'error'
        );
      }
    });
    
    e.target.value = '';
  };

  // Handle files dropped from EmptySessionDropzone
  const handleDropzoneFiles = useCallback((files) => {
    if (!files.length || !currentSessionId) return;
    
    const targetSessionId = currentSessionId;
    const targetSessionName = currentSession?.name || (language === 'es' ? 'Chat actual' : 'Current chat');
    
    // Check if this is the first upload (session has no CVs yet)
    const isFirstUpload = !currentSession?.cvs || currentSession.cvs.length === 0;
    
    // Start background upload task
    startUploadTask({
      sessionId: targetSessionId,
      sessionName: targetSessionName,
      files,
      mode,
      language,
      isFirstUpload,
      onComplete: async ({ sessionId, filesCount }) => {
        if (currentSessionIdRef.current === sessionId) {
          await loadSession(sessionId);
        }
        await loadSessions();
        showToastMessage(
          language === 'es' 
            ? `✅ ${filesCount} CV(s) procesados correctamente` 
            : `✅ ${filesCount} CV(s) processed successfully`,
          'success'
        );
      },
      onError: (error) => {
        showToastMessage(
          language === 'es' 
            ? `❌ Error al subir CVs: ${error.message}` 
            : `❌ Error uploading CVs: ${error.message}`,
          'error'
        );
      }
    });
  }, [currentSessionId, currentSession, mode, language, startUploadTask, loadSession, loadSessions, showToastMessage]);

  const handleSend = async (text) => {
    if (!text.trim() || !currentSessionId || isChatLoading || !currentSession?.cvs?.length) return;
    const userMessage = text.trim();
    const targetSessionId = currentSessionId;
    
    // Add pending message for this specific session
    setPendingMessages(prev => ({
      ...prev,
      [targetSessionId]: { userMsg: userMessage, status: 'sending' }
    }));
    
    setChatLoadingStates(prev => ({ ...prev, [targetSessionId]: true }));
    
    // Open pipeline panel if auto-expand is enabled
    if (autoExpandPipeline) {
      setShowPipelinePanel(true);
      setIsPipelineExpanded(true);
    }
    
    // Initialize pipeline progress for this specific session (via context)
    initPipeline(targetSessionId);
    
    // Initialize streaming state for progressive display - FOR THIS SESSION
    setStreamingStateBySession(prev => ({
      ...prev,
      [targetSessionId]: {
        currentStep: 'query_understanding',
        steps: {},
        queryUnderstanding: null,
        candidates: [],
        partialAnswer: null
      }
    }));
    
    setPendingMessages(prev => ({
      ...prev,
      [targetSessionId]: { 
        userMsg: userMessage, 
        status: 'analyzing'
      }
    }));
    
    try {
      // Use SSE endpoint for real-time progress with pipeline settings
      const payload = { 
        message: userMessage,
        understanding_model: ragPipelineSettings.understanding,
        reranking_model: ragPipelineSettings.reranking,
        reranking_enabled: ragPipelineSettings.reranking_enabled,
        generation_model: ragPipelineSettings.generation,
        verification_model: ragPipelineSettings.verification,
        verification_enabled: ragPipelineSettings.verification_enabled
      };
      
      console.log('🚀 Sending query with settings:', payload);
      
      const response = await fetch(`/api/sessions/${targetSessionId}/chat-stream?mode=${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error('Stream request failed');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalResult = null;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (!line.trim() || line.startsWith(':')) continue;
          
          if (line.startsWith('event:')) {
            const eventType = line.substring(6).trim();
            continue;
          }
          
          if (line.startsWith('data:')) {
            const data = JSON.parse(line.substring(5).trim());
            
            // Handle step events - UPDATE PIPELINE PANEL AND STREAMING STATE
            if (data.step) {
              const stepName = data.step;
              const stepStatus = data.status;
              
              console.log(`🔄 REAL Step: ${stepName} - ${stepStatus}`, data);
              
              // Update pipeline for this specific session (via context)
              updateStep(targetSessionId, stepName, stepStatus, data.details);
              
              // Update streaming state with progressive content - FOR THIS SESSION
              setStreamingStateBySession(prev => {
                const sessionState = prev[targetSessionId];
                if (!sessionState) return prev;
                const newState = { 
                  ...sessionState, 
                  currentStep: stepName,
                  steps: { ...sessionState.steps, [stepName]: { status: stepStatus, details: data.details, progress: data.progress } },
                  // Track progress state for retry/fallback visualization
                  currentProgress: data.progress || null
                };
                
                // Capture query understanding content
                if (stepName === 'query_understanding' && data.content) {
                  newState.queryUnderstanding = data.content;
                }
                
                // Capture candidate previews from retrieval
                if (stepName === 'retrieval' && data.candidates) {
                  newState.candidates = data.candidates;
                }
                
                // Capture partial answer from generation
                if (stepName === 'generation' && data.partial_answer) {
                  newState.partialAnswer = data.partial_answer;
                }
                
                return { ...prev, [targetSessionId]: newState };
              });
            }
            
            // Handle complete event
            if (data.response || data.answer) {
              finalResult = data;
              console.log('✅ Stream complete, received final result:', {
                has_answer: !!data.answer,
                has_response: !!data.response,
                has_sources: !!data.sources,
                source_count: data.sources?.length || 0
              });
            }
          }
        }
      }
      
      if (finalResult) {
        // Save metrics with confidence explanation
        saveMetricEntry({
          query: userMessage,
          mode: mode,
          metrics: finalResult.metrics || {},
          confidence_score: finalResult.confidence_score,
          guardrail_passed: finalResult.guardrail_passed,
          confidence_explanation: finalResult.confidence_explanation,
          query_understanding: finalResult.query_understanding,
          session_id: targetSessionId,
          timestamp: new Date().toISOString(),
        });
        window.dispatchEvent(new Event('metrics-updated'));
      }
      
      console.log('🔄 Reloading session and clearing pending messages...');
      
      // Small delay to let user see final pipeline step before clearing
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mark pipeline as complete for this session
      completePipeline(targetSessionId);
      
      // Clear streaming state for this session
      setStreamingStateBySession(prev => {
        const newState = { ...prev };
        delete newState[targetSessionId];
        return newState;
      });
      
      // IMPORTANT: Reload session FIRST to get new messages from server
      // This prevents the user message from disappearing during the transition
      console.log('🔄 Current session ID:', currentSessionIdRef.current, 'Target:', targetSessionId);
      if (currentSessionIdRef.current === targetSessionId) {
        console.log('🔄 Reloading session to fetch new messages...');
        await loadSession(targetSessionId);
        console.log('✅ Session reloaded');
      } else {
        console.log('⚠️ Session IDs do not match, skipping reload');
      }
      
      // Clear pending message AFTER session is reloaded
      // This ensures no gap where the user message disappears
      setPendingMessages(prev => {
        const newState = { ...prev };
        delete newState[targetSessionId];
        return newState;
      });
      
      // Reload sessions list to reorder by last activity
      await loadSessions();
      
    } catch (e) {
      console.error('❌ Stream error:', e);
      // Clear pipeline state on error
      clearPipeline(targetSessionId);
      // Clear streaming state for this session on error to prevent UI from being stuck
      setStreamingStateBySession(prev => {
        const newState = { ...prev };
        delete newState[targetSessionId];
        return newState;
      });
      // Reload session FIRST before clearing pending message
      if (currentSessionIdRef.current === targetSessionId) {
        await loadSession(targetSessionId);
      }
      // Clear pending message AFTER session reload
      setPendingMessages(prev => {
        const newState = { ...prev };
        delete newState[targetSessionId];
        return newState;
      });
    }
    
    setChatLoadingStates(prev => ({ ...prev, [targetSessionId]: false }));
  };

  const handleRemoveCV = async (cvId) => {
    await removeCVFromSession(currentSessionId, cvId, mode);
    await loadSession(currentSessionId);
    await loadSessions();
    showToastMessage(language === 'es' ? 'CV eliminado' : 'CV removed', 'success');
  };

  const handleDeleteMessage = async (messageIndex) => {
    if (!currentSessionId) return;
    // If not confirmed, show confirmation
    if (deleteMessageConfirm !== messageIndex) {
      setDeleteMessageConfirm(messageIndex);
      return;
    }
    // Confirmed, proceed with deletion
    setDeleteMessageConfirm(null);
    try {
      await deleteMessage(currentSessionId, messageIndex, mode);
      await loadSession(currentSessionId);
      showToastMessage(language === 'es' ? 'Mensaje eliminado' : 'Message deleted', 'success');
    } catch (e) {
      console.error(e);
      showToastMessage(language === 'es' ? 'Error al eliminar mensaje' : 'Error deleting message', 'error');
    }
  };

  const handleCopyMessage = (content) => {
    navigator.clipboard.writeText(content);
    showToastMessage(language === 'es' ? 'Mensaje copiado' : 'Message copied', 'success');
  };

  const cancelDeleteMessage = () => {
    setDeleteMessageConfirm(null);
  };

  const handleRetryMessage = async (messageContent, messageIndex) => {
    if (!currentSessionId || isChatLoading) return;
    try {
      // Delete this message and all after it, then resend
      await deleteMessagesFrom(currentSessionId, messageIndex, mode);
      await loadSession(currentSessionId);
      // Resend the message
      handleSend(messageContent);
    } catch (e) {
      console.error(e);
      showToastMessage(language === 'es' ? 'Error al reintentar' : 'Error retrying', 'error');
    }
  };

  const handleRemoveCVFromPanel = async (sessionId, cvId) => {
    await removeCVFromSession(sessionId, cvId, mode);
    // Refresh panel session data
    const data = await getSession(sessionId, mode);
    setCvPanelSession(data);
    await loadSessions();
    if (currentSessionId === sessionId) await loadSession(sessionId);
    showToastMessage(language === 'es' ? 'CV eliminado' : 'CV removed', 'success');
  };

  const handleUploadToPanel = async (e) => {
    const files = Array.from(e.target.files).filter(f => f.name.endsWith('.pdf'));
    const targetSessionId = cvPanelSessionId || currentSessionId;
    if (!files.length || !targetSessionId) return;
    
    // Find session name for display
    const targetSession = sessions.find(s => s.id === targetSessionId);
    const targetSessionName = targetSession?.name || cvPanelSession?.name || (language === 'es' ? 'Sesión' : 'Session');
    
    // Check if this is the first upload (session has no CVs yet)
    const sessionCvCount = cvPanelSession?.cvs?.length || targetSession?.cv_count || 0;
    const isFirstUpload = sessionCvCount === 0;
    
    // Start background upload task
    startUploadTask({
      sessionId: targetSessionId,
      sessionName: targetSessionName,
      files,
      mode,
      language,
      isFirstUpload,  // Only auto-name if this is the first upload
      onComplete: async ({ sessionId, filesCount }) => {
        // Refresh panel session data
        const sessionData = await getSession(sessionId, mode);
        setCvPanelSession(sessionData);
        await loadSessions();
        if (currentSessionIdRef.current === sessionId) {
          await loadSession(sessionId);
        }
        showToastMessage(
          language === 'es' 
            ? `✅ ${filesCount} CV(s) procesados correctamente` 
            : `✅ ${filesCount} CV(s) processed successfully`,
          'success'
        );
      },
      onError: (error) => {
        showToastMessage(
          language === 'es' 
            ? `❌ Error al subir CVs: ${error.message}` 
            : `❌ Error uploading CVs: ${error.message}`,
          'error'
        );
      }
    });
    
    e.target.value = '';
  };

  const handleClearSessionCVs = async () => {
    if (!currentSessionId) return;
    try {
      await clearSessionCVs(currentSessionId, mode);
      await loadSession(currentSessionId);
      showToastMessage(language === 'es' ? 'Todos los CVs eliminados del chat' : 'All CVs removed from chat', 'success');
    } catch (e) { console.error(e); showToastMessage('Error', 'error'); }
  };

  const handleDeleteAllCVsFromDB = async () => {
    const cvCount = allCVs.length;
    if (!cvCount) return;
    if (!window.confirm(language === 'es' ? `¿Eliminar ${cvCount} CVs de la base de datos?` : `Delete ${cvCount} CVs from database?`)) return;
    
    // Show delete progress modal
    setDeleteProgress({
      current: 0,
      total: cvCount,
      percent: 0,
      status: 'deleting',
      logs: [language === 'es' ? `Eliminando ${cvCount} CVs...` : `Deleting ${cvCount} CVs...`]
    });
    
    // Animate progress
    let fakeProgress = 0;
    const progressInterval = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + Math.random() * 8, 85);
      setDeleteProgress(prev => prev ? { ...prev, percent: fakeProgress } : null);
    }, 150);
    
    try {
      await deleteAllCVsFromDatabase(mode);
      clearInterval(progressInterval);
      
      setDeleteProgress(prev => ({
        ...prev,
        percent: 100,
        status: 'completed',
        logs: [...prev.logs, language === 'es' ? '✓ ¡Eliminación completada!' : '✓ Deletion completed!']
      }));
      
      await loadSessions();
      if (currentSessionId) await loadSession(currentSessionId);
      const data = await getCVList(mode);
      setAllCVs(data.cvs || []);
      
      setTimeout(() => setDeleteProgress(null), 1500);
    } catch (e) { 
      clearInterval(progressInterval);
      console.error(e); 
      setDeleteProgress(prev => prev ? { ...prev, status: 'error', logs: [...prev.logs, `Error: ${e.message}`] } : null);
      setTimeout(() => setDeleteProgress(null), 3000);
    }
  };

  const handleDeleteCVFromDB = async (cvId) => {
    try {
      await deleteCV(cvId, mode);
      const data = await getCVList(mode);
      setAllCVs(data.cvs || []);
      await loadSessions();
      if (currentSessionId) await loadSession(currentSessionId);
      // Also refresh cvPanelSession if viewing a specific session
      if (cvPanelSessionId) {
        const sessionData = await getSession(cvPanelSessionId, mode);
        setCvPanelSession(sessionData);
      }
      showToastMessage(language === 'es' ? 'CV eliminado de la base de datos' : 'CV deleted from database', 'success');
    } catch (e) { console.error(e); showToastMessage('Error', 'error'); }
  };

  return (
    <div className={`h-screen flex ${theme === 'dark' ? 'dark' : ''}`}>
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 bg-slate-100 dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 flex flex-col">
        <div className="p-3">
          <button onClick={handleNewChat} className="w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-white transition-colors">
            <Plus className="w-4 h-4" /><span className="text-sm">{language === 'es' ? 'Nuevo chat' : 'New chat'}</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2">
          {isLoadingSessions ? (
            <SessionSkeleton />
          ) : sessions.map((s) => (
            <div key={s.id} className="mb-1">
              <div 
                onClick={() => {
                  currentSessionIdRef.current = s.id;
                  setCurrentSessionId(s.id);
                  // Cargar la sesión directamente con getSession para evitar cualquier interferencia
                  getSession(s.id, mode).then(data => {
                    if (currentSessionIdRef.current === s.id) {
                      setCurrentSession(data);
                    }
                  }).catch(console.error);
                }} 
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  deletingSessionId === s.id 
                    ? 'bg-red-50 dark:bg-red-900/20 opacity-60 cursor-not-allowed' 
                    : isSessionProcessing(s.id)
                      ? 'bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 text-amber-800 dark:text-amber-200 cursor-pointer'
                      : currentSessionId === s.id 
                        ? 'bg-blue-100 dark:bg-slate-800 text-blue-700 dark:text-white cursor-pointer' 
                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800/50 cursor-pointer'
                }`}
              >
                {deletingSessionId === s.id ? (
                  <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-red-400" />
                ) : isSessionProcessing(s.id) ? (
                  <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-amber-500" />
                ) : chatLoadingStates[s.id] ? (
                  <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-cyan-400" />
                ) : (
                  <MessageSquare className="w-4 h-4 flex-shrink-0" />
                )}
                {editingId === s.id ? (
                  <input value={editName} onChange={(e) => setEditName(e.target.value)} onBlur={() => handleRename(s.id)} onKeyDown={(e) => e.key === 'Enter' && handleRename(s.id)} className="flex-1 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm px-2 py-0.5 rounded outline-none border border-slate-300 dark:border-slate-600" autoFocus onClick={(e) => e.stopPropagation()} />
                ) : (
                  <div className="flex-1 min-w-0">
                    <span className="text-sm truncate block">
                      {deletingSessionId === s.id ? (language === 'es' ? 'Eliminando...' : 'Deleting...') : s.name}
                    </span>
                    <span className={`text-xs ${isSessionProcessing(s.id) ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400 dark:text-slate-500'}`}>
                      {isSessionProcessing(s.id) 
                        ? (language === 'es' ? 'Procesando...' : 'Processing...') 
                        : `${s.cv_count || 0} CVs`}
                    </span>
                  </div>
                )}
                {deletingSessionId !== s.id && (
                  <div className="hidden group-hover:flex items-center gap-1">
                    {deleteConfirm === s.id ? (
                      <><button onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }} className="p-1 hover:bg-red-500/20 rounded"><Check className="w-3.5 h-3.5 text-red-400" /></button><button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }} className="p-1"><X className="w-3.5 h-3.5" /></button></>
                    ) : (
                      <><button onClick={(e) => { e.stopPropagation(); setCvPanelSessionId(s.id); setShowCVPanel(true); }} className="p-1 hover:bg-slate-300 dark:hover:bg-slate-700 rounded transition-colors" title={language === 'es' ? 'Ver CVs' : 'View CVs'}><FileText className="w-3.5 h-3.5" /></button><button onClick={(e) => { e.stopPropagation(); setEditingId(s.id); setEditName(s.name); }} className="p-1 hover:bg-slate-300 dark:hover:bg-slate-700 rounded transition-colors" title={language === 'es' ? 'Renombrar' : 'Rename'}><Edit2 className="w-3.5 h-3.5" /></button><button onClick={(e) => { e.stopPropagation(); handleAIRename(s.id); }} className="p-1 hover:bg-purple-200 dark:hover:bg-purple-900/50 rounded transition-colors" title={language === 'es' ? 'Renombrar con IA' : 'AI Rename'} disabled={aiRenamingSessionId === s.id || (s.cv_count || 0) === 0}>{aiRenamingSessionId === s.id ? <Loader className="w-3.5 h-3.5 text-purple-500 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-purple-500" />}</button><button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(s.id); }} className="p-1 hover:bg-slate-300 dark:hover:bg-slate-700 rounded transition-colors"><Trash2 className="w-3.5 h-3.5" /></button></>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2">
          {/* Mode Selector */}
          <div className="flex items-center gap-2 px-2 py-2 bg-white dark:bg-slate-900 rounded-lg">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-12 font-medium">Mode:</span>
            <button onClick={() => setMode('local')} className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${mode === 'local' ? 'bg-blue-500 text-white shadow-sm' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>
              <Database className="w-3 h-3" /> Local
            </button>
            <button onClick={() => setMode('cloud')} className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${mode === 'cloud' ? 'bg-blue-500 text-white shadow-sm' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>
              <Cloud className="w-3 h-3" /> Supabase
            </button>
          </div>
          {/* Language Selector */}
          <div className="flex items-center gap-2 px-2 py-2 bg-white dark:bg-slate-900 rounded-lg">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-12 font-medium">Lang:</span>
            <button onClick={() => setLanguage('en')} className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${language === 'en' ? 'bg-blue-500 text-white shadow-sm' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>EN</button>
            <button onClick={() => setLanguage('es')} className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${language === 'es' ? 'bg-blue-500 text-white shadow-sm' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}`}>ES</button>
          </div>
          {/* Theme Toggle */}
          <button onClick={toggleTheme} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium transition-colors">
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-slate-500" />}
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
          {/* All CVs Button */}
          <button onClick={() => { setCvPanelSessionId(null); setShowCVPanel(true); }} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium transition-colors">
            <FileText className="w-4 h-4 text-blue-500" />
            <span>{language === 'es' ? 'Todos los CVs' : 'All CVs'}</span>
            <ChevronRight className="w-4 h-4 ml-auto text-slate-400" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className={`flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-950 transition-all duration-300 ${
        showPipelinePanel && isPipelineExpanded ? 'mr-72' : showPipelinePanel ? 'mr-11' : ''
      }`}>
        <div className="h-14 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold ${mode === 'cloud' ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300' : 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'}`}>
              {mode === 'cloud' ? <Cloud className="w-3.5 h-3.5" /> : <Database className="w-3.5 h-3.5" />}
              {mode === 'cloud' ? 'Supabase' : 'Local'}
            </div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{currentSession ? `${currentSession.name} · ${currentSession.cvs?.length || 0} CVs` : 'CV Screener'}</span>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors group"
              title={language === 'es' ? 'Configuración' : 'Settings'}
            >
              <Settings className="w-4 h-4 text-slate-600 dark:text-slate-400" />
            </button>
            <button 
              onClick={() => setShowAbout(true)}
              className="flex items-center gap-2 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded-lg transition-colors group"
              title={language === 'es' ? 'Acerca de' : 'About'}
            >
              <Info className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </button>
            <button 
              onClick={() => setShowMetricsPanel(true)}
              className="flex items-center gap-2 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-cyan-100 dark:hover:bg-cyan-900/30 rounded-lg transition-colors group"
              title={language === 'es' ? 'Ver métricas RAG' : 'View RAG Metrics'}
            >
              <BarChart3 className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span className="text-xs font-medium text-slate-600 dark:text-slate-400 group-hover:text-cyan-700 dark:group-hover:text-cyan-300 hidden sm:inline">{language === 'es' ? 'Métricas' : 'Metrics'}</span>
            </button>
            <button 
              onClick={() => setShowRAGSettings(true)}
              className="flex items-center gap-2 px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded-lg transition-colors group"
              title={language === 'es' ? 'Configurar Pipeline RAG' : 'Configure RAG Pipeline'}
            >
              <Sliders className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span className="text-xs font-medium text-slate-600 dark:text-slate-400 group-hover:text-purple-700 dark:group-hover:text-purple-300 hidden sm:inline">{language === 'es' ? 'Pipeline' : 'Pipeline'}</span>
            </button>
            {currentSession && (<><input ref={fileInputRef} type="file" accept=".pdf" multiple onChange={handleUpload} className="hidden" /><button onClick={() => fileInputRef.current?.click()} disabled={isSessionProcessing(currentSessionId)} className="flex items-center gap-2 px-4 py-2 text-sm bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg disabled:opacity-50 font-medium transition-colors shadow-sm">{isSessionProcessing(currentSessionId) ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}<span>{language === 'es' ? 'Añadir CVs' : 'Add CVs'}</span></button></>)}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {!currentSession ? (
            <div className="h-full flex items-center justify-center"><div className="text-center"><Sparkles className="w-12 h-12 text-blue-500 mx-auto mb-4" /><h2 className="text-2xl font-semibold text-slate-800 dark:text-white mb-2">CV Screener</h2><p className="text-slate-500 mb-6">{language === 'es' ? 'Crea un chat y sube CVs' : 'Create a chat and upload CVs'}</p><button onClick={handleNewChat} className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl transition-colors">{language === 'es' ? 'Nuevo chat' : 'New chat'}</button></div></div>
          ) : (currentSession.messages?.length === 0 && !pendingMessages[currentSessionId]) ? (
            currentSession.cvs?.length ? (
              <div className="h-full flex flex-col items-center justify-center">
                <Sparkles className="w-10 h-10 text-blue-500 mb-4" />
                <h3 className="text-xl font-medium text-slate-800 dark:text-white mb-6">
                  {language === 'es' ? '¿Qué quieres saber?' : 'What do you want to know?'}
                </h3>
                {suggestions.length > 0 && (
                  <div className="grid grid-cols-2 gap-3 max-w-2xl">
                    {suggestions.map((s, i) => (
                      <button key={i} onClick={() => handleSend(s)} className="p-4 text-left text-sm bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition-colors">{s}</button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <EmptySessionDropzone 
                onFilesDropped={handleDropzoneFiles}
                isUploading={isSessionProcessing(currentSessionId)}
              />
            )
          ) : (
            <div className="max-w-5xl mx-auto space-y-6">
              {/* Processing Banner - shown when CVs are being uploaded */}
              {isSessionProcessing(currentSessionId) && (
                <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/30 dark:to-orange-900/30 border border-amber-200 dark:border-amber-700 rounded-xl p-4 flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 dark:bg-amber-800 rounded-full flex items-center justify-center">
                    <Loader className="w-4 h-4 text-amber-600 dark:text-amber-400 animate-spin" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-200">
                      {language === 'es' ? 'Procesando CVs...' : 'Processing CVs...'}
                    </h4>
                    <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
                      {language === 'es' 
                        ? 'La base de datos está siendo actualizada. Puedes seguir haciendo consultas, pero las respuestas estarán limitadas a los CVs ya procesados.' 
                        : 'Database is being updated. You can continue making queries, but responses will be limited to already processed CVs.'}
                    </p>
                  </div>
                </div>
              )}
              {/* Combine actual messages with pending message for THIS session only */}
              {/* FIX: ALWAYS show pending message during loading to prevent it from disappearing */}
              {(() => {
                const sessionMsgs = currentSession.messages || [];
                const pending = pendingMessages[currentSessionId];
                
                // During loading (isChatLoading), ALWAYS show the pending message
                // This prevents the user message from disappearing during streaming
                if (isChatLoading && pending) {
                  // Check if pending is already in session (to avoid duplicate)
                  const alreadyInSession = sessionMsgs.some(
                    m => m.role === 'user' && m.content === pending.userMsg
                  );
                  if (alreadyInSession) {
                    // Already in session, just return session messages
                    return sessionMsgs;
                  }
                  // Not in session yet, add pending message at the end
                  return [
                    ...sessionMsgs,
                    { role: 'user', content: pending.userMsg, isPending: true }
                  ];
                }
                
                // Not loading: check for duplicates before adding pending
                const pendingAlreadySaved = pending && sessionMsgs.some(
                  m => m.role === 'user' && m.content === pending.userMsg
                );
                
                return [
                  ...sessionMsgs,
                  ...(pending && !pendingAlreadySaved ? [{ role: 'user', content: pending.userMsg, isPending: true }] : [])
                ];
              })().map((msg, idx) => (
                <div key={idx} className={msg.role === 'user' ? 'flex justify-end' : ''}>
                  <div className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse max-w-[70%]' : 'w-full'}`}>
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-500' : 'bg-gradient-to-br from-emerald-400 to-cyan-500'}`}>{msg.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Sparkles className="w-5 h-5 text-white" />}</div>
                    <div className={`flex-1 ${msg.role === 'user' ? '' : 'min-w-0'}`}>
                      <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-slate-900 border border-slate-700 shadow-sm text-slate-100'}`}>
                        
                        {/* USE STRUCTURED OUTPUT RENDERER for assistant messages with structured_output */}
                        {msg.role === 'assistant' && msg.structured_output ? (
                          <StructuredOutputRenderer 
                            structuredOutput={msg.structured_output}
                            onOpenCV={(cvId, name) => openPdfViewer(cvId, name || cvId)}
                          />
                        ) : msg.role === 'assistant' ? (
                          /* FALLBACK: Old thinking collapsible for messages without structured_output */
                          (() => {
                            const { thinkingContent } = preprocessContent(msg.content);
                            if (thinkingContent) {
                              return (
                                <details className="mb-4 group">
                                  <summary className="flex items-center gap-2 cursor-pointer text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 select-none">
                                    <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                                    <span className="font-medium">{language === 'es' ? 'Ver razonamiento interno' : 'View internal reasoning'}</span>
                                  </summary>
                                  <div className="mt-2 p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 italic">
                                    {thinkingContent}
                                  </div>
                                </details>
                              );
                            }
                            return null;
                          })()
                        ) : null}
                        
                        {/* Only render ReactMarkdown for user messages OR assistant messages WITHOUT structured_output */}
                        {(msg.role === 'user' || !msg.structured_output) && (
                        <div className={`max-w-none ${msg.role === 'user' ? '' : '[&_p]:text-gray-700 dark:[&_p]:text-gray-200 [&_h1]:text-gray-900 dark:[&_h1]:text-white [&_h2]:text-gray-900 dark:[&_h2]:text-white [&_h3]:text-gray-900 dark:[&_h3]:text-white [&_li]:text-gray-700 dark:[&_li]:text-gray-200 [&_strong]:text-gray-900 dark:[&_strong]:text-white'}`}>
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              table: ({node, ...props}) => <MemoizedTable {...props} />,
                              thead: ({node, ...props}) => <thead className="bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white" {...props} />,
                              th: ({node, ...props}) => <th className="px-4 py-3 text-left font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700" {...props} />,
                              td: ({node, ...props}) => <td className="px-4 py-3 text-gray-700 dark:text-gray-200 border-b border-gray-100 dark:border-gray-700/50" {...props} />,
                              tr: ({node, ...props}) => <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50" {...props} />,
                              code: ({node, inline, className, children, ...props}) => (
                                <MemoizedCodeBlock inline={inline} className={className} {...props}>{children}</MemoizedCodeBlock>
                              ),
                              a: ({node, href, children, ...props}) => {
                                // Handle cv_id format (from preprocessed [📄](cv_xxx))
                                if (href?.startsWith('cv_')) {
                                  return (
                                    <button
                                      onClick={() => openPdfViewer(href, href)}
                                      className="inline-flex items-center justify-center w-5 h-5 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800 rounded transition-colors border border-blue-200 dark:border-blue-600"
                                      title={language === 'es' ? 'Ver CV' : 'View CV'}
                                    >
                                      <FileText className="w-3 h-3" />
                                    </button>
                                  );
                                }
                                // Handle cvlink: format (legacy)
                                if (href?.startsWith('cvlink:')) {
                                  const cvId = href.replace('cvlink:', '');
                                  return (
                                    <button
                                      onClick={() => openPdfViewer(cvId, cvId)}
                                      className="inline-flex items-center justify-center w-5 h-5 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800 rounded transition-colors border border-blue-200 dark:border-blue-600"
                                      title={language === 'es' ? 'Ver CV' : 'View CV'}
                                    >
                                      <FileText className="w-3 h-3" />
                                    </button>
                                  );
                                }
                                return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline" {...props}>{children}</a>;
                              },
                            }}
                          >
                            {preprocessContent(msg.content).mainContent}
                          </ReactMarkdown>
                          
                          {/* Render Conclusion Block Separately */}
                          {(() => {
                            const { conclusionContent } = preprocessContent(msg.content);
                            if (conclusionContent) {
                              return (
                                <div className="mt-6 p-5 bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 dark:from-emerald-900/30 dark:via-teal-900/30 dark:to-cyan-900/30 rounded-xl border-2 border-emerald-300 dark:border-emerald-600 shadow-lg">
                                  <div className="flex items-center gap-3 mb-4 pb-3 border-b border-emerald-200 dark:border-emerald-700">
                                    <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-xl flex items-center justify-center shadow-md">
                                      <Check className="w-6 h-6 text-white" />
                                    </div>
                                    <span className="font-bold text-emerald-800 dark:text-emerald-200 text-xl">
                                      {language === 'es' ? 'Conclusión' : 'Conclusion'}
                                    </span>
                                  </div>
                                  <div className="text-gray-800 dark:text-gray-100 text-base">
                                    <ReactMarkdown 
                                      remarkPlugins={[remarkGfm]}
                                      components={{
                                        p: ({children}) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                                        strong: ({children}) => <strong className="text-emerald-800 dark:text-emerald-200">{children}</strong>,
                                        ul: ({children}) => <ul className="list-disc list-inside space-y-1 mt-2">{children}</ul>,
                                        li: ({children}) => <li className="text-gray-700 dark:text-gray-200">{children}</li>,
                                        a: ({href, children}) => {
                                          // Handle cv_id format
                                          if (href?.startsWith('cv_')) {
                                            return (
                                              <button onClick={() => openPdfViewer(href, href)} className="inline-flex items-center justify-center w-5 h-5 bg-emerald-200 dark:bg-emerald-700 text-emerald-700 dark:text-emerald-200 hover:bg-emerald-300 dark:hover:bg-emerald-600 rounded transition-colors border border-emerald-300 dark:border-emerald-600">
                                                <FileText className="w-3 h-3" />
                                              </button>
                                            );
                                          }
                                          return <a href={href} className="text-emerald-600 underline">{children}</a>;
                                        },
                                      }}
                                    >
                                      {/* Process conclusion content to convert CV references to clickable links (no emoji, just link) */}
                                      {conclusionContent
                                        .replace(/\*\*\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)')
                                        .replace(/\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)')
                                        .replace(/\*\*\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)')
                                        .replace(/\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)')
                                        .replace(/\[CV:(cv_[a-z0-9_-]+)\]/gi, '[$1]($1)')
                                        .replace(/\(cv:(cv_[a-z0-9_-]+)\)/gi, ' [$1]($1)')}
                                    </ReactMarkdown>
                                  </div>
                                </div>
                              );
                            }
                            return null;
                          })()}
                        </div>
                        )}
                        {/* Referencias eliminadas - solo se muestran junto al nombre del candidato */}
                      </div>
                      {/* Message action buttons - only for non-pending messages */}
                      {!msg.isPending && (
                        <div className={`flex items-center gap-1 mt-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          {msg.role === 'user' && (
                            <button
                              onClick={() => handleRetryMessage(msg.content, idx)}
                              disabled={isChatLoading}
                              className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors disabled:opacity-50"
                              title={language === 'es' ? 'Repetir pregunta' : 'Retry question'}
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => handleCopyMessage(msg.content)}
                            className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                            title={language === 'es' ? 'Copiar mensaje' : 'Copy message'}
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                          {deleteMessageConfirm === idx ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleDeleteMessage(idx)}
                                className="p-1.5 bg-red-500 text-white rounded-lg transition-colors"
                                title={language === 'es' ? 'Confirmar eliminar' : 'Confirm delete'}
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={cancelDeleteMessage}
                                className="p-1.5 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg transition-colors"
                                title={language === 'es' ? 'Cancelar' : 'Cancel'}
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => handleDeleteMessage(idx)}
                              className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                              title={language === 'es' ? 'Eliminar mensaje' : 'Delete message'}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {/* Streaming Message - Progressive content display */}
              {/* When showStreamingPreview=false, shows minimal TypingIndicator only */}
              {isChatLoading && streamingState && (
                <StreamingMessage 
                  streamingState={streamingState}
                  onViewCV={openPdfViewer}
                  showPreview={showStreamingPreview}
                  enabledSteps={[
                    'query_understanding',
                    'embedding', 
                    'retrieval',
                    ...(ragPipelineSettings.reranking_enabled ? ['reranking'] : []),
                    'reasoning',
                    'generation',
                    ...(ragPipelineSettings.verification_enabled ? ['verification'] : []),
                    'refinement'
                  ]}
                />
              )}
              
              {/* Suggestions Panel - appears after response */}
              {!isChatLoading && currentSession?.messages?.length > 0 && currentSession.cvs?.length > 0 && (
                <SuggestionsPanel 
                  suggestions={suggestions}
                  onSelectSuggestion={handleSend}
                  cvCount={currentSession.cvs?.length || 0}
                />
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {currentSession && (
          <ChatInputField 
            onSend={handleSend}
            isLoading={isChatLoading}
            hasCV={currentSession.cvs?.length > 0}
            sessionName={currentSession.name}
          />
        )}
      </div>

      {/* CV Panel Modal - Collapsible Sessions & Compact Cards */}
      {showCVPanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowCVPanel(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-6xl max-h-[90vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                  {language === 'es' ? 'Gestión de CVs' : 'CV Management'}
                </h2>
                <p className="text-xs text-gray-500">
                  {mode === 'cloud' ? '☁️ Supabase' : '💾 Local'} · {sessions.length} {language === 'es' ? 'chats' : 'chats'} · {allCVs.length} CVs
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={async () => { const data = await getCVList(mode); setAllCVs(data.cvs || []); }} className="p-2 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg" title="Reload">
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button onClick={() => setShowCVPanel(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"><X className="w-5 h-5" /></button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {/* All Sessions - Collapsible */}
              {sessions.map(session => {
                const isExpanded = expandedSessions[session.id] || false;
                const sessionCVs = loadedSessionCVs[session.id] || session.cvs || [];
                
                return (
                  <div key={session.id} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                    {/* Session Header - Clickable to expand/collapse */}
                    <button
                      onClick={() => toggleSessionExpand(session.id)}
                      className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                        <MessageSquare className="w-4 h-4 text-blue-500" />
                        <span className="font-medium text-sm text-gray-900 dark:text-white">{session.name}</span>
                        <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full">
                          {session.cv_count || sessionCVs.length} CVs
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded cursor-pointer" onClick={e => e.stopPropagation()}>
                          <Upload className="w-3 h-3" />
                          <span>{language === 'es' ? 'Subir' : 'Upload'}</span>
                          <input type="file" multiple accept=".pdf" onChange={(e) => { setCvPanelSessionId(session.id); handleUploadToPanel(e); }} className="hidden" />
                        </label>
                      </div>
                    </button>
                    
                    {/* Session CVs - Collapsible Content */}
                    {isExpanded && (
                      <div className="p-3 bg-white dark:bg-gray-800">
                        {sessionCVs.length > 0 ? (
                          <div className="grid grid-cols-5 gap-2">
                            {sessionCVs.map(cv => {
                              const { fileId, candidateName, role } = parseCVFilename(cv.filename);
                              return (
                                <div 
                                  key={cv.id} 
                                  className="group relative bg-gray-50 dark:bg-gray-900 rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all cursor-pointer border border-transparent hover:border-blue-300 dark:hover:border-blue-600"
                                  onClick={() => openPdfViewer(cv.id, cv.filename)}
                                >
                                  <button 
                                    onClick={(e) => { e.stopPropagation(); handleRemoveCVFromPanel(session.id, cv.id); }} 
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow z-10"
                                  >
                                    <X className="w-3 h-3" />
                                  </button>
                                  <div className="text-center">
                                    <p className="text-[10px] text-gray-400 font-mono truncate">{cv.id}</p>
                                    <p className="text-xs font-semibold text-gray-900 dark:text-white truncate mt-0.5" title={candidateName}>{candidateName}</p>
                                    {role && <p className="text-[10px] text-blue-500 truncate" title={role}>{role}</p>}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="text-xs text-gray-400 text-center py-2">{language === 'es' ? 'Sin CVs' : 'No CVs'}</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              
              {sessions.length === 0 && (
                <div className="text-center py-8">
                  <MessageSquare className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">{language === 'es' ? 'No hay chats' : 'No chats'}</p>
                </div>
              )}
            </div>
            
            {/* Footer */}
            <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  {language === 'es' ? 'Clic en chat para expandir · Hover en CV para eliminar' : 'Click chat to expand · Hover CV to delete'}
                </p>
                {allCVs.length > 0 && (
                  <button onClick={handleDeleteAllCVsFromDB} className="flex items-center gap-1 px-3 py-1.5 text-xs text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg">
                    <Trash2 className="w-3 h-3" />
                    {language === 'es' ? 'Vaciar DB' : 'Clear DB'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}




      {/* Loading Overlay for Mode Switch */}
      {isLoadingMode && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-2xl flex items-center gap-4">
            <Loader className="w-6 h-6 animate-spin text-blue-500" />
            <span className="text-gray-700 dark:text-gray-300">{language === 'es' ? 'Cambiando modo...' : 'Switching mode...'}</span>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastState && (
        <Toast 
          message={toastState.message} 
          type={toastState.type} 
          duration={toastState.duration}
          onClose={hideToast} 
        />
      )}

      {/* PDF Viewer Modal */}
      {pdfViewerUrl && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[60] p-4" onClick={closePdfViewer}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-xl flex items-center justify-center">
                  <FileText className="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{pdfViewerTitle}</h3>
                  <p className="text-xs text-gray-500">{language === 'es' ? 'Vista previa del CV' : 'CV Preview'}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <a 
                  href={pdfViewerUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  {language === 'es' ? 'Abrir en nueva pestaña' : 'Open in new tab'}
                </a>
                <button onClick={closePdfViewer} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors">
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="flex-1 bg-gray-100 dark:bg-gray-900">
              <iframe 
                src={pdfViewerUrl} 
                className="w-full h-full rounded-b-2xl"
                title={pdfViewerTitle}
              />
            </div>
          </div>
        </div>
      )}

      {/* Delete Progress Modal */}
      {deleteProgress && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[70]">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md p-6 shadow-2xl mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                deleteProgress.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-900/30' :
                deleteProgress.status === 'error' ? 'bg-red-100 dark:bg-red-900/30' :
                'bg-red-100 dark:bg-red-900/30'
              }`}>
                {deleteProgress.status === 'completed' ? (
                  <Check className="w-6 h-6 text-emerald-500" />
                ) : deleteProgress.status === 'error' ? (
                  <X className="w-6 h-6 text-red-500" />
                ) : (
                  <Trash2 className="w-6 h-6 text-red-500 animate-pulse" />
                )}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  {deleteProgress.status === 'deleting' ? (language === 'es' ? 'Eliminando CVs' : 'Deleting CVs') :
                   deleteProgress.status === 'completed' ? (language === 'es' ? 'Completado' : 'Completed') :
                   'Error'}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {deleteProgress.total} {language === 'es' ? 'CVs' : 'CVs'}
                </p>
              </div>
            </div>
            
            {/* Progress bar */}
            <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-4">
              <div 
                className={`h-full transition-all duration-150 ${
                  deleteProgress.status === 'completed' ? 'bg-emerald-500' :
                  deleteProgress.status === 'error' ? 'bg-red-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${deleteProgress.percent || 0}%` }}
              />
            </div>
            
            {/* Log messages */}
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
              {deleteProgress.logs.map((log, i) => (
                <p key={i} className="text-xs text-gray-600 dark:text-gray-400 font-mono">
                  {log}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* RAG Pipeline Settings Modal */}
      <RAGPipelineSettings 
        isOpen={showRAGSettings}
        onClose={() => setShowRAGSettings(false)}
        onSave={(settings) => {
          setRagPipelineSettings(settings);
          showToastMessage(language === 'es' ? 'Configuración guardada' : 'Settings saved', 'success');
        }}
      />

      {/* Metrics Panel */}
      <MetricsPanel 
        isOpen={showMetricsPanel}
        onClose={() => setShowMetricsPanel(false)}
        sessionId={currentSessionId}
        sessionName={currentSession?.name}
      />

      {/* Pipeline Progress Panel */}
      {showPipelinePanel && (
        <PipelineProgressPanel
          isExpanded={isPipelineExpanded}
          onToggleExpand={() => {
            // Just toggle expanded state, don't touch auto-expand
            setIsPipelineExpanded(!isPipelineExpanded);
          }}
          autoExpand={autoExpandPipeline}
          onToggleAutoExpand={() => {
            const newValue = !autoExpandPipeline;
            setAutoExpandPipeline(newValue);
            localStorage.setItem('autoExpandPipeline', JSON.stringify(newValue));
          }}
          showPreview={showStreamingPreview}
          onTogglePreview={() => {
            const newValue = !showStreamingPreview;
            setShowStreamingPreview(newValue);
            localStorage.setItem('showStreamingPreview', JSON.stringify(newValue));
          }}
          enabledSteps={[
            'query_understanding',
            'multi_query',
            'guardrail',
            'embedding', 
            'retrieval',
            ...(ragPipelineSettings.reranking_enabled ? ['reranking'] : []),
            'reasoning',
            'generation',
            ...(ragPipelineSettings.verification_enabled ? ['verification'] : []),
            'refinement'
          ]}
        />
      )}

      {/* About Modal */}
      <AboutModal isOpen={showAbout} onClose={() => setShowAbout(false)} />

      {/* Settings Modal */}
      <SettingsModal 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)}
        onSave={() => {
          showToastMessage(language === 'es' ? 'Configuración guardada' : 'Settings saved', 'success');
        }}
      />

      {/* Background Upload Widget - floating minimizable panel */}
      <BackgroundUploadWidget />
    </div>
  );
}

export default App;
