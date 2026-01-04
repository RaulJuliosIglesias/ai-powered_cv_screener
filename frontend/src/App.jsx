import { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, MessageSquare, Trash2, Send, Loader, Upload, FileText, X, Check, CheckCircle, Edit2, Moon, Sun, Sparkles, User, Database, Cloud, Globe, Settings, ChevronRight, Copy, Eye, ExternalLink, Sliders, BarChart3, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import useMode from './hooks/useMode';
import useTheme from './hooks/useTheme';
import { useLanguage } from './contexts/LanguageContext';
import SourceBadge from './components/SourceBadge';
import ModelSelector from './components/ModelSelector';
import RAGPipelineSettings, { getRAGPipelineSettings } from './components/RAGPipelineSettings';
import MetricsPanel, { saveMetricEntry } from './components/MetricsPanel';
import PipelineProgressPanel from './components/PipelineProgressPanel';
import ChatInputField from './components/ChatInputField';
import { getSessions, createSession, getSession, deleteSession, updateSession, uploadCVsToSession, getSessionUploadStatus, removeCVFromSession, sendSessionMessage, getSessionSuggestions, getCVList, clearSessionCVs, deleteAllCVsFromDatabase, deleteCV, deleteMessage, deleteMessagesFrom } from './services/api';

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
  const [isUploading, setIsUploading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [allCVs, setAllCVs] = useState([]);
  const [showCVPanel, setShowCVPanel] = useState(false);
  const [cvPanelSessionId, setCvPanelSessionId] = useState(null);
  const [cvPanelSession, setCvPanelSession] = useState(null);
  const cvPanelFileInputRef = useRef(null);
  const [isLoadingMode, setIsLoadingMode] = useState(false);
  const [toast, setToast] = useState(null);
  const [pdfViewerUrl, setPdfViewerUrl] = useState(null);
  const [pdfViewerTitle, setPdfViewerTitle] = useState('');
  const [showRAGSettings, setShowRAGSettings] = useState(false);
  const [ragPipelineSettings, setRagPipelineSettings] = useState(getRAGPipelineSettings());
  const [showMetricsPanel, setShowMetricsPanel] = useState(false);
  const [showPipelinePanel, setShowPipelinePanel] = useState(true);
  const [isPipelineExpanded, setIsPipelineExpanded] = useState(false);
  const [autoExpandPipeline, setAutoExpandPipeline] = useState(() => {
    const saved = localStorage.getItem('autoExpandPipeline');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [pipelineProgress, setPipelineProgress] = useState({});
  
  // Upload progress modal state
  const [uploadProgress, setUploadProgress] = useState(null);
  // { files: ['file1.pdf', 'file2.pdf'], current: 1, total: 3, status: 'uploading' | 'processing' | 'completed', logs: ['Processing file1.pdf...'] }
  
  // Delete progress modal state (for bulk deletion)
  const [deleteProgress, setDeleteProgress] = useState(null);
  // { current: 0, total: 5, status: 'deleting' | 'completed', logs: ['Deleting CV 1/5...'] }
  
  // State for collapsible sessions in CV panel
  const [expandedSessions, setExpandedSessions] = useState({});
  const [loadedSessionCVs, setLoadedSessionCVs] = useState({}); // Cache loaded CVs per session
  
  // Helper to parse CV filename into components
  const parseCVFilename = (filename) => {
    const name = filename.replace('.pdf', '').replace('.PDF', '');
    const parts = name.split('_');
    
    if (parts.length >= 3) {
      const fileId = parts[0];
      const role = parts[parts.length - 1].replace(/-/g, ' ');
      const candidateName = parts.slice(1, -1).join(' ');
      return { fileId, candidateName, role };
    } else if (parts.length === 2) {
      return { fileId: parts[0], candidateName: parts[1], role: '' };
    }
    return { fileId: '', candidateName: name, role: '' };
  };
  
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

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Preprocess message content to handle special blocks and CV links
  const preprocessContent = (content) => {
    if (!content) return { mainContent: content || '', conclusionContent: null, thinkingContent: null };
    
    let text = content;
    let thinkingContent = null;
    let conclusionContent = null;
    
    // Extract thinking block - try with closing ::: first, then without
    const thinkingMatch = text.match(/:::thinking\s*\n?([\s\S]*?):::/);
    if (thinkingMatch) {
      thinkingContent = thinkingMatch[1].trim();
      text = text.replace(thinkingMatch[0], '');
    }
    
    // Extract conclusion block - multiple patterns
    // Pattern 1: :::conclusion ... ::: (with closing)
    let conclusionMatch = text.match(/:::conclusion\s*\n?([\s\S]*?):::/);
    if (conclusionMatch) {
      conclusionContent = conclusionMatch[1].trim();
      text = text.replace(conclusionMatch[0], '');
    } else {
      // Pattern 2: :::conclusion at start of line followed by content (no closing)
      conclusionMatch = text.match(/:::conclusion\s+(.+)$/m);
      if (conclusionMatch) {
        conclusionContent = conclusionMatch[1].trim();
        text = text.replace(conclusionMatch[0], '');
      }
    }
    
    // Also remove any remaining :::conclusion text that wasn't matched
    text = text.replace(/:::conclusion\s*/g, '');
    
    // Convert various CV reference formats to: Name + icon link (no emoji, just link that renders as button)
    // Format 1: [CV:cv_id] -> link only (renders as FileText icon button)
    text = text.replace(/\[CV:(cv_[a-z0-9_-]+)\]/gi, '[$1]($1)');
    
    // Format 2: **[Name](cv:cv_id)** -> **Name** + icon link
    text = text.replace(/\*\*\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)');
    
    // Format 3: [Name](cv:cv_id) -> Name + icon link
    text = text.replace(/\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)');
    
    // Format 4: **[Name](cv_id)** direct link -> **Name** + icon link
    text = text.replace(/\*\*\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)\*\*/gi, '**$1** [$2]($2)');
    
    // Format 5: [Name](cv_id) direct link -> Name + icon link (CRITICAL - prevents name as link)
    text = text.replace(/\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)/gi, '$1 [$2]($2)');
    
    // Format 6: (cv:cv_id) standalone -> icon link
    text = text.replace(/\(cv:(cv_[a-z0-9_-]+)\)/gi, ' [$1]($1)');
    
    // Clean up multiple newlines
    text = text.replace(/\n{3,}/g, '\n\n').trim();
    
    return { 
      mainContent: text, 
      conclusionContent,
      thinkingContent 
    };
  };
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const { mode, setMode } = useMode();
  const { theme, toggleTheme } = useTheme();
  const { language, setLanguage } = useLanguage();

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [currentSession?.messages]);

  const loadSessions = useCallback(async () => {
    try { const data = await getSessions(mode); setSessions(data.sessions || []); } catch (e) { console.error(e); }
  }, [mode]);

  const loadSession = useCallback(async (id) => {
    try {
      const data = await getSession(id, mode);
      setCurrentSession(data);
      const sugg = await getSessionSuggestions(id, mode);
      setSuggestions(sugg.suggestions || []);
    } catch (e) { console.error(e); setCurrentSessionId(null); }
  }, [mode]);

  // Reload sessions when mode changes
  useEffect(() => { 
    const switchMode = async () => {
      setIsLoadingMode(true);
      setCurrentSessionId(null);
      setCurrentSession(null);
      setSuggestions([]);
      await loadSessions();
      setIsLoadingMode(false);
      showToast(mode === 'cloud' ? (language === 'es' ? 'Modo Supabase activado' : 'Supabase mode activated') : (language === 'es' ? 'Modo Local activado' : 'Local mode activated'));
    };
    switchMode();
  }, [mode]); // eslint-disable-line
  
  useEffect(() => { if (currentSessionId) loadSession(currentSessionId); else { setCurrentSession(null); setSuggestions([]); } }, [currentSessionId, loadSession]);
  
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

  const handleDelete = async (id) => {
    await deleteSession(id, mode);
    await loadSessions();
    if (currentSessionId === id) setCurrentSessionId(null);
    setDeleteConfirm(null);
  };

  const handleRename = async (id) => {
    if (!editName.trim()) return;
    await updateSession(id, { name: editName.trim() }, mode);
    await loadSessions();
    if (currentSessionId === id) await loadSession(id);
    setEditingId(null);
  };

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files).filter(f => f.name.endsWith('.pdf'));
    if (!files.length || !currentSessionId) return;
    setIsUploading(true);
    
    // Initialize progress modal
    const fileNames = files.map(f => f.name);
    setUploadProgress({
      files: fileNames,
      current: 0,
      total: files.length,
      percent: 0,
      status: 'uploading',
      logs: [language === 'es' ? `Subiendo ${files.length} archivo(s)...` : `Uploading ${files.length} file(s)...`]
    });
    
    try {
      // Upload phase (0% to 50%) - REAL upload progress from HTTP
      const res = await uploadCVsToSession(currentSessionId, files, mode, (uploadPercent) => {
        // Upload is 0-50% of total progress
        const realPercent = Math.round(uploadPercent * 0.5);
        setUploadProgress(prev => prev ? { ...prev, percent: realPercent } : null);
      });
      
      // Processing phase - poll for REAL progress from backend
      let lastProcessed = 0;
      let lastPhase = '';
      const phaseNames = {
        extracting: language === 'es' ? 'Extrayendo texto' : 'Extracting text',
        saving: language === 'es' ? 'Guardando PDF' : 'Saving PDF',
        chunking: language === 'es' ? 'Dividiendo en chunks' : 'Chunking',
        embedding: language === 'es' ? 'Creando embeddings' : 'Creating embeddings',
        indexing: language === 'es' ? 'Indexando' : 'Indexing',
        done: language === 'es' ? 'Completado' : 'Done'
      };
      
      const poll = async () => {
        const status = await getSessionUploadStatus(currentSessionId, res.job_id);
        const processed = status.processed_files || 0;
        const currentFile = status.current_file;
        const currentPhase = status.current_phase;
        
        // Calculate real progress: each file has 5 phases
        // processed_files * 100 + current phase progress (0-100)
        const phaseProgress = { extracting: 10, saving: 20, chunking: 40, embedding: 80, indexing: 95, done: 100 };
        const fileProgress = processed / files.length;
        const currentFileProgress = currentPhase ? (phaseProgress[currentPhase] || 0) / 100 / files.length : 0;
        const totalProgress = 50 + ((fileProgress + currentFileProgress) * 50);
        
        if (status.status === 'processing') {
          setUploadProgress(prev => {
            let newLogs = [...prev.logs];
            
            // Log when a new file starts or phase changes
            if (currentFile && currentPhase && currentPhase !== lastPhase) {
              const phaseName = phaseNames[currentPhase] || currentPhase;
              const shortName = currentFile.length > 25 ? currentFile.slice(0, 22) + '...' : currentFile;
              newLogs.push(`${phaseName}: ${shortName}`);
              lastPhase = currentPhase;
            }
            
            // Log when a file completes
            if (processed > lastProcessed) {
              const completedFile = fileNames[processed - 1] || `CV ${processed}`;
              const shortName = completedFile.length > 25 ? completedFile.slice(0, 22) + '...' : completedFile;
              newLogs.push(language === 'es' ? `✓ Completado: ${shortName}` : `✓ Done: ${shortName}`);
              lastProcessed = processed;
            }
            
            return {
              ...prev,
              current: processed,
              percent: Math.min(99, Math.round(totalProgress)),
              status: 'processing',
              logs: newLogs.slice(-6)
            };
          });
          setTimeout(poll, 150); // Poll very fast to catch all phases
        } else {
          setUploadProgress(prev => ({
            ...prev,
            status: 'completed',
            current: files.length,
            percent: 100,
            logs: [...prev.logs.slice(-5), language === 'es' ? '✓ ¡Todo completado!' : '✓ All completed!']
          }));
          setTimeout(() => setUploadProgress(null), 1200);
          setIsUploading(false);
          await loadSession(currentSessionId);
          await loadSessions();
        }
      };
      
      // Start polling immediately
      setUploadProgress(prev => ({
        ...prev,
        percent: 50,
        status: 'processing',
        logs: [...prev.logs, language === 'es' ? 'Procesando archivos...' : 'Processing files...']
      }));
      poll();
    } catch (e) { 
      console.error(e); 
      setIsUploading(false); 
      setUploadProgress(prev => prev ? {...prev, status: 'error', logs: [...prev.logs, `Error: ${e.message}`]} : null);
      setTimeout(() => setUploadProgress(null), 3000);
    }
    e.target.value = '';
  };

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
    
    // Initialize pipeline progress
    setPipelineProgress({
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
    });
    
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
            
            // Handle step events - UPDATE PIPELINE PANEL
            if (data.step) {
              const stepName = data.step;
              const stepStatus = data.status;
              
              console.log(`🔄 REAL Step: ${stepName} - ${stepStatus}`);
              
              setPipelineProgress(prev => ({
                ...prev,
                [stepName]: { status: stepStatus, details: data.details }
              }));
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
      
      console.log('🔄 Clearing pending messages and reloading session...');
      
      // Clear pending message
      setPendingMessages(prev => {
        const newState = { ...prev };
        delete newState[targetSessionId];
        return newState;
      });
      
      // Reload session to show final result
      console.log('🔄 Current session ID:', currentSessionIdRef.current, 'Target:', targetSessionId);
      if (currentSessionIdRef.current === targetSessionId) {
        console.log('🔄 Reloading session to fetch new messages...');
        await loadSession(targetSessionId);
        console.log('✅ Session reloaded');
      } else {
        console.log('⚠️ Session IDs do not match, skipping reload');
      }
      
    } catch (e) {
      console.error('❌ Stream error:', e);
      setPendingMessages(prev => {
        const newState = { ...prev };
        delete newState[targetSessionId];
        return newState;
      });
      if (currentSessionIdRef.current === targetSessionId) {
        await loadSession(targetSessionId);
      }
    }
    
    setChatLoadingStates(prev => ({ ...prev, [targetSessionId]: false }));
  };

  const handleRemoveCV = async (cvId) => {
    await removeCVFromSession(currentSessionId, cvId, mode);
    await loadSession(currentSessionId);
    await loadSessions();
    showToast(language === 'es' ? 'CV eliminado' : 'CV removed', 'success');
  };

  const handleDeleteMessage = async (messageIndex) => {
    if (!currentSessionId) return;
    try {
      await deleteMessage(currentSessionId, messageIndex, mode);
      await loadSession(currentSessionId);
      showToast(language === 'es' ? 'Mensaje eliminado' : 'Message deleted', 'success');
    } catch (e) {
      console.error(e);
      showToast(language === 'es' ? 'Error al eliminar mensaje' : 'Error deleting message', 'error');
    }
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
      showToast(language === 'es' ? 'Error al reintentar' : 'Error retrying', 'error');
    }
  };

  const handleRemoveCVFromPanel = async (sessionId, cvId) => {
    await removeCVFromSession(sessionId, cvId, mode);
    // Refresh panel session data
    const data = await getSession(sessionId, mode);
    setCvPanelSession(data);
    await loadSessions();
    if (currentSessionId === sessionId) await loadSession(sessionId);
    showToast(language === 'es' ? 'CV eliminado' : 'CV removed', 'success');
  };

  const handleUploadToPanel = async (e) => {
    const files = Array.from(e.target.files).filter(f => f.name.endsWith('.pdf'));
    const targetSessionId = cvPanelSessionId || currentSessionId;
    if (!files.length || !targetSessionId) return;
    setIsUploading(true);
    
    const fileNames = files.map(f => f.name);
    setUploadProgress({
      files: fileNames,
      current: 0,
      total: files.length,
      percent: 0,
      status: 'uploading',
      logs: [language === 'es' ? `Subiendo ${files.length} archivo(s)...` : `Uploading ${files.length} file(s)...`]
    });
    
    try {
      // Upload phase (0% to 50%) - REAL upload progress
      const res = await uploadCVsToSession(targetSessionId, files, mode, (uploadPercent) => {
        const realPercent = Math.round(uploadPercent * 0.5);
        setUploadProgress(prev => prev ? { ...prev, percent: realPercent } : null);
      });
      
      // Processing phase - poll for REAL progress
      let lastProcessed = 0;
      let lastPhase = '';
      const phaseNames = {
        extracting: language === 'es' ? 'Extrayendo texto' : 'Extracting text',
        saving: language === 'es' ? 'Guardando PDF' : 'Saving PDF',
        chunking: language === 'es' ? 'Dividiendo en chunks' : 'Chunking',
        embedding: language === 'es' ? 'Creando embeddings' : 'Creating embeddings',
        indexing: language === 'es' ? 'Indexando' : 'Indexing',
        done: language === 'es' ? 'Completado' : 'Done'
      };
      
      const poll = async () => {
        const status = await getSessionUploadStatus(targetSessionId, res.job_id);
        const processed = status.processed_files || 0;
        const currentFile = status.current_file;
        const currentPhase = status.current_phase;
        
        const phaseProgress = { extracting: 10, saving: 20, chunking: 40, embedding: 80, indexing: 95, done: 100 };
        const fileProgress = processed / files.length;
        const currentFileProgress = currentPhase ? (phaseProgress[currentPhase] || 0) / 100 / files.length : 0;
        const totalProgress = 50 + ((fileProgress + currentFileProgress) * 50);
        
        if (status.status === 'processing') {
          setUploadProgress(prev => {
            let newLogs = [...prev.logs];
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
            return { ...prev, current: processed, percent: Math.min(99, Math.round(totalProgress)), logs: newLogs.slice(-6) };
          });
          setTimeout(poll, 150);
        } else {
          setUploadProgress(prev => ({
            ...prev,
            status: 'completed',
            current: files.length,
            percent: 100,
            logs: [...prev.logs.slice(-5), language === 'es' ? '✓ ¡Todo completado!' : '✓ All completed!']
          }));
          setTimeout(() => setUploadProgress(null), 1200);
          setIsUploading(false);
          const sessionData = await getSession(targetSessionId, mode);
          setCvPanelSession(sessionData);
          await loadSessions();
          if (currentSessionId === targetSessionId) await loadSession(targetSessionId);
        }
      };
      
      setUploadProgress(prev => ({
        ...prev,
        percent: 50,
        status: 'processing',
        logs: [...prev.logs, language === 'es' ? 'Procesando archivos...' : 'Processing files...']
      }));
      poll();
    } catch (e) { console.error(e); setIsUploading(false); }
    e.target.value = '';
  };

  const handleClearSessionCVs = async () => {
    if (!currentSessionId) return;
    try {
      await clearSessionCVs(currentSessionId, mode);
      await loadSession(currentSessionId);
      showToast(language === 'es' ? 'Todos los CVs eliminados del chat' : 'All CVs removed from chat', 'success');
    } catch (e) { console.error(e); showToast('Error', 'error'); }
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
      showToast(language === 'es' ? 'CV eliminado de la base de datos' : 'CV deleted from database', 'success');
    } catch (e) { console.error(e); showToast('Error', 'error'); }
  };

  return (
    <div className={`h-screen flex ${theme === 'dark' ? 'dark' : ''}`}>
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 bg-gray-900 flex flex-col">
        <div className="p-3">
          <button onClick={handleNewChat} className="w-full flex items-center gap-3 px-3 py-3 rounded-lg border border-gray-700 hover:bg-gray-800 text-white">
            <Plus className="w-4 h-4" /><span className="text-sm">{language === 'es' ? 'Nuevo chat' : 'New chat'}</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2">
          {sessions.map((s) => (
            <div key={s.id} className="mb-1">
              <div onClick={() => setCurrentSessionId(s.id)} className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer ${currentSessionId === s.id ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800/50'}`}>
                {chatLoadingStates[s.id] ? (
                  <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-cyan-400" />
                ) : (
                  <MessageSquare className="w-4 h-4 flex-shrink-0" />
                )}
                {editingId === s.id ? (
                  <input value={editName} onChange={(e) => setEditName(e.target.value)} onBlur={() => handleRename(s.id)} onKeyDown={(e) => e.key === 'Enter' && handleRename(s.id)} className="flex-1 bg-gray-700 text-white text-sm px-2 py-0.5 rounded outline-none" autoFocus onClick={(e) => e.stopPropagation()} />
                ) : (
                  <div className="flex-1 min-w-0">
                    <span className="text-sm truncate block">{s.name}</span>
                    <span className="text-xs text-gray-500">{s.cv_count || 0} CVs</span>
                  </div>
                )}
                <div className="hidden group-hover:flex items-center gap-1">
                  {deleteConfirm === s.id ? (
                    <><button onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }} className="p-1 hover:bg-red-500/20 rounded"><Check className="w-3.5 h-3.5 text-red-400" /></button><button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }} className="p-1"><X className="w-3.5 h-3.5" /></button></>
                  ) : (
                    <><button onClick={(e) => { e.stopPropagation(); setCvPanelSessionId(s.id); setShowCVPanel(true); }} className="p-1 hover:bg-gray-700 rounded" title={language === 'es' ? 'Ver CVs' : 'View CVs'}><FileText className="w-3.5 h-3.5" /></button><button onClick={(e) => { e.stopPropagation(); setEditingId(s.id); setEditName(s.name); }} className="p-1 hover:bg-gray-700 rounded"><Edit2 className="w-3.5 h-3.5" /></button><button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(s.id); }} className="p-1 hover:bg-gray-700 rounded"><Trash2 className="w-3.5 h-3.5" /></button></>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-gray-800 space-y-1">
          {/* Mode Selector */}
          <div className="flex items-center gap-2 px-3 py-2">
            <span className="text-xs text-gray-500 w-12">Mode:</span>
            <button onClick={() => setMode('local')} className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs ${mode === 'local' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
              <Database className="w-3 h-3" /> Local
            </button>
            <button onClick={() => setMode('cloud')} className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs ${mode === 'cloud' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
              <Cloud className="w-3 h-3" /> Supabase
            </button>
          </div>
          {/* Language Selector */}
          <div className="flex items-center gap-2 px-3 py-2">
            <span className="text-xs text-gray-500 w-12">Lang:</span>
            <button onClick={() => setLanguage('en')} className={`flex-1 px-2 py-1.5 rounded text-xs ${language === 'en' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>EN</button>
            <button onClick={() => setLanguage('es')} className={`flex-1 px-2 py-1.5 rounded text-xs ${language === 'es' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>ES</button>
          </div>
          {/* Theme Toggle */}
          <button onClick={toggleTheme} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 text-gray-300 text-sm">
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
          {/* All CVs Button */}
          <button onClick={() => { setCvPanelSessionId(null); setShowCVPanel(true); }} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 text-gray-300 text-sm">
            <FileText className="w-4 h-4" />
            <span>{language === 'es' ? 'Todos los CVs' : 'All CVs'}</span>
            <ChevronRight className="w-4 h-4 ml-auto" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className={`flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-900 transition-all duration-300 ${
        showPipelinePanel && isPipelineExpanded ? 'mr-80' : showPipelinePanel ? 'mr-12' : ''
      }`}>
        <div className="h-14 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${mode === 'cloud' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300' : 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'}`}>
              {mode === 'cloud' ? <Cloud className="w-3.5 h-3.5" /> : <Database className="w-3.5 h-3.5" />}
              {mode === 'cloud' ? 'Supabase' : 'Local'}
            </div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{currentSession ? `${currentSession.name} · ${currentSession.cvs?.length || 0} CVs` : 'CV Screener'}</span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setShowMetricsPanel(true)}
              className="flex items-center gap-1.5 px-2.5 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-cyan-300 dark:hover:border-cyan-600 transition-colors text-sm"
              title={language === 'es' ? 'Ver métricas RAG' : 'View RAG Metrics'}
            >
              <BarChart3 className="w-4 h-4 text-cyan-500" />
            </button>
            <button 
              onClick={() => setShowRAGSettings(true)}
              className="flex items-center gap-1.5 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-purple-300 dark:hover:border-purple-600 transition-colors text-sm"
              title={language === 'es' ? 'Configurar Pipeline RAG' : 'Configure RAG Pipeline'}
            >
              <Sliders className="w-4 h-4 text-purple-500" />
              <span className="text-gray-600 dark:text-gray-300 text-xs hidden sm:inline">{language === 'es' ? 'Pipeline' : 'Pipeline'}</span>
            </button>
            {currentSession && (<><input ref={fileInputRef} type="file" accept=".pdf" multiple onChange={handleUpload} className="hidden" /><button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-50">{isUploading ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}<span>{language === 'es' ? 'Añadir CVs' : 'Add CVs'}</span></button></>)}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {!currentSession ? (
            <div className="h-full flex items-center justify-center"><div className="text-center"><Sparkles className="w-12 h-12 text-blue-500 mx-auto mb-4" /><h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-2">CV Screener</h2><p className="text-gray-500 mb-6">{language === 'es' ? 'Crea un chat y sube CVs' : 'Create a chat and upload CVs'}</p><button onClick={handleNewChat} className="px-6 py-3 bg-blue-500 text-white rounded-xl">{language === 'es' ? 'Nuevo chat' : 'New chat'}</button></div></div>
          ) : (currentSession.messages?.length === 0 && !pendingMessages[currentSessionId]) ? (
            <div className="h-full flex flex-col items-center justify-center"><Sparkles className="w-10 h-10 text-blue-500 mb-4" /><h3 className="text-xl font-medium text-gray-800 dark:text-white mb-6">{currentSession.cvs?.length ? (language === 'es' ? '¿Qué quieres saber?' : 'What do you want to know?') : (language === 'es' ? 'Sube CVs para empezar' : 'Upload CVs to start')}</h3>
              {suggestions.length > 0 && <div className="grid grid-cols-2 gap-3 max-w-2xl">{suggestions.map((s, i) => (<button key={i} onClick={() => handleSend(s)} className="p-4 text-left text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl text-gray-700 dark:text-gray-200">{s}</button>))}</div>}
            </div>
          ) : (
            <div className="max-w-5xl mx-auto space-y-6">
              {/* Combine actual messages with pending message for THIS session only */}
              {[
                ...(currentSession.messages || []),
                ...(pendingMessages[currentSessionId] ? [{ role: 'user', content: pendingMessages[currentSessionId].userMsg, isPending: true }] : [])
              ].map((msg, idx) => (
                <div key={idx} className={msg.role === 'user' ? 'flex justify-end' : ''}>
                  <div className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse max-w-[70%]' : 'w-full'}`}>
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-500' : 'bg-gradient-to-br from-emerald-400 to-cyan-500'}`}>{msg.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Sparkles className="w-5 h-5 text-white" />}</div>
                    <div className={`flex-1 ${msg.role === 'user' ? '' : 'min-w-0'}`}>
                      <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm text-gray-800 dark:text-gray-100'}`}>
                        
                        {/* Thinking/Reasoning Collapsible - Only for assistant messages */}
                        {msg.role === 'assistant' && (() => {
                          const { thinkingContent } = preprocessContent(msg.content);
                          if (thinkingContent) {
                            return (
                              <details className="mb-4 group">
                                <summary className="flex items-center gap-2 cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 select-none">
                                  <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                                  <span className="font-medium">{language === 'es' ? 'Ver razonamiento interno' : 'View internal reasoning'}</span>
                                </summary>
                                <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 italic">
                                  {thinkingContent}
                                </div>
                              </details>
                            );
                          }
                          return null;
                        })()}
                        
                        <div className={`max-w-none ${msg.role === 'user' ? '' : '[&_p]:text-gray-700 dark:[&_p]:text-gray-200 [&_h1]:text-gray-900 dark:[&_h1]:text-white [&_h2]:text-gray-900 dark:[&_h2]:text-white [&_h3]:text-gray-900 dark:[&_h3]:text-white [&_li]:text-gray-700 dark:[&_li]:text-gray-200 [&_strong]:text-gray-900 dark:[&_strong]:text-white'}`}>
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              table: ({node, ...props}) => {
                                const tableRef = useRef(null);
                                const [copied, setCopied] = useState(false);
                                const copyTable = () => {
                                  if (tableRef.current) {
                                    const rows = tableRef.current.querySelectorAll('tr');
                                    let text = '';
                                    rows.forEach(row => {
                                      const cells = row.querySelectorAll('th, td');
                                      text += Array.from(cells).map(c => c.textContent).join('\t') + '\n';
                                    });
                                    navigator.clipboard.writeText(text);
                                    setCopied(true);
                                    setTimeout(() => setCopied(false), 2000);
                                  }
                                };
                                return (
                                  <div className="my-4 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900">
                                    <div className="flex items-center justify-between px-3 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-600">
                                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Table</span>
                                      <button onClick={copyTable} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                                        {copied ? <><Check className="w-3.5 h-3.5" /> Copied!</> : <><Copy className="w-3.5 h-3.5" /> Copy table</>}
                                      </button>
                                    </div>
                                    <div className="overflow-x-auto">
                                      <table ref={tableRef} className="w-full text-sm" {...props} />
                                    </div>
                                  </div>
                                );
                              },
                              thead: ({node, ...props}) => <thead className="bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white" {...props} />,
                              th: ({node, ...props}) => <th className="px-4 py-3 text-left font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700" {...props} />,
                              td: ({node, ...props}) => <td className="px-4 py-3 text-gray-700 dark:text-gray-200 border-b border-gray-100 dark:border-gray-700/50" {...props} />,
                              tr: ({node, ...props}) => <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50" {...props} />,
                              code: ({node, inline, className, children, ...props}) => {
                                const [copied, setCopied] = useState(false);
                                const codeText = String(children).replace(/\n$/, '');
                                if (inline) return <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-pink-600 dark:text-pink-400 text-sm" {...props}>{children}</code>;
                                return (
                                  <div className="my-3 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 bg-gray-900">
                                    <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
                                      <span className="text-xs text-gray-400">{className?.replace('language-', '') || 'code'}</span>
                                      <button onClick={() => { navigator.clipboard.writeText(codeText); setCopied(true); setTimeout(() => setCopied(false), 2000); }} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white">
                                        {copied ? <><Check className="w-3.5 h-3.5" /> Copied!</> : <><Copy className="w-3.5 h-3.5" /> Copy code</>}
                                      </button>
                                    </div>
                                    <pre className="p-4 overflow-x-auto text-sm text-gray-100"><code {...props}>{children}</code></pre>
                                  </div>
                                );
                              },
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
                            onClick={() => handleDeleteMessage(idx)}
                            className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title={language === 'es' ? 'Eliminar mensaje' : 'Delete message'}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {isChatLoading && pendingMessages[currentSessionId] && (
                <div className="flex gap-3 items-start animate-fade-in">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl p-4 shadow-sm">
                    <div className="flex items-center gap-2">
                      <Loader className="w-5 h-5 animate-spin text-emerald-500" />
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                        {(() => {
                          // Show active pipeline step
                          const activeStep = Object.entries(pipelineProgress).find(([_, v]) => v.status === 'running');
                          if (activeStep) {
                            const stepLabels = {
                              query_understanding: language === 'es' ? 'Entendiendo consulta...' : 'Understanding query...',
                              multi_query: language === 'es' ? 'Generando multi-query...' : 'Generating multi-query...',
                              guardrail: language === 'es' ? 'Verificando seguridad...' : 'Safety check...',
                              embedding: language === 'es' ? 'Generando embeddings...' : 'Generating embeddings...',
                              retrieval: language === 'es' ? 'Recuperando CVs...' : 'Retrieving CVs...',
                              reranking: language === 'es' ? 'Reordenando resultados...' : 'Reranking results...',
                              reasoning: language === 'es' ? 'Razonando...' : 'Reasoning...',
                              generation: language === 'es' ? 'Generando respuesta...' : 'Generating response...',
                              verification: language === 'es' ? 'Verificando respuesta...' : 'Verifying response...',
                              refinement: language === 'es' ? 'Refinando...' : 'Refining...'
                            };
                            return stepLabels[activeStep[0]] || (language === 'es' ? 'Procesando...' : 'Processing...');
                          }
                          return language === 'es' ? 'Analizando CVs...' : 'Analyzing CVs...';
                        })()}
                      </span>
                    </div>
                  </div>
                </div>
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


      {/* Legacy CV Panel for specific session view - kept for backward compatibility */}
      {false && showCVPanel && cvPanelSessionId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowCVPanel(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">Legacy panel</p>
                {(cvPanelSessionId || currentSessionId) ? (
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">
                      {language === 'es' ? 'Subir a:' : 'Upload to:'} <span className="font-medium text-blue-600">{cvPanelSession?.name || currentSession?.name}</span>
                    </span>
                    <label className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl cursor-pointer transition-colors">
                      {isUploading ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                      <span className="text-sm font-medium">{isUploading ? (language === 'es' ? 'Subiendo...' : 'Uploading...') : (language === 'es' ? 'Subir CVs' : 'Upload CVs')}</span>
                      <input ref={cvPanelFileInputRef} type="file" multiple accept=".pdf" onChange={handleUploadToPanel} className="hidden" disabled={isUploading} />
                    </label>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <MessageSquare className="w-4 h-4" />
                    <span className="text-sm">{language === 'es' ? 'Crea o selecciona un chat para subir CVs' : 'Create or select a chat to upload CVs'}</span>
                  </div>
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
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-2">
          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg ${
            toast.type === 'error' ? 'bg-red-500 text-white' : 
            toast.type === 'success' ? 'bg-emerald-500 text-white' : 
            'bg-gray-800 text-white'
          }`}>
            {toast.type === 'success' ? <Check className="w-5 h-5" /> : 
             toast.type === 'error' ? <X className="w-5 h-5" /> : 
             <Sparkles className="w-5 h-5" />}
            <span className="text-sm font-medium">{toast.message}</span>
          </div>
        </div>
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

      {/* Upload Progress Modal */}
      {uploadProgress && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[70]">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md p-6 shadow-2xl mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                uploadProgress.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-900/30' :
                uploadProgress.status === 'error' ? 'bg-red-100 dark:bg-red-900/30' :
                'bg-blue-100 dark:bg-blue-900/30'
              }`}>
                {uploadProgress.status === 'completed' ? (
                  <Check className="w-6 h-6 text-emerald-500" />
                ) : uploadProgress.status === 'error' ? (
                  <X className="w-6 h-6 text-red-500" />
                ) : (
                  <Loader className="w-6 h-6 text-blue-500 animate-spin" />
                )}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  {uploadProgress.status === 'uploading' ? (language === 'es' ? 'Subiendo CVs' : 'Uploading CVs') :
                   uploadProgress.status === 'processing' ? (language === 'es' ? 'Procesando CVs' : 'Processing CVs') :
                   uploadProgress.status === 'completed' ? (language === 'es' ? 'Completado' : 'Completed') :
                   'Error'}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {uploadProgress.current} / {uploadProgress.total} {language === 'es' ? 'archivos' : 'files'}
                </p>
              </div>
            </div>
            
            {/* Progress bar */}
            <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-4">
              <div 
                className={`h-full transition-all duration-300 ${
                  uploadProgress.status === 'completed' ? 'bg-emerald-500' :
                  uploadProgress.status === 'error' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}
                style={{ width: `${uploadProgress.percent || (uploadProgress.current / uploadProgress.total) * 100}%` }}
              />
            </div>
            
            {/* Log messages */}
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 max-h-32 overflow-y-auto">
              {uploadProgress.logs.map((log, i) => (
                <p key={i} className="text-xs text-gray-600 dark:text-gray-400 font-mono">
                  {log}
                </p>
              ))}
            </div>
            
            {/* File list */}
            <div className="mt-3 flex flex-wrap gap-1">
              {uploadProgress.files.slice(0, 5).map((file, i) => (
                <span key={i} className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-300">
                  {file.length > 20 ? file.slice(0, 20) + '...' : file}
                </span>
              ))}
              {uploadProgress.files.length > 5 && (
                <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-300">
                  +{uploadProgress.files.length - 5} more
                </span>
              )}
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
          showToast(language === 'es' ? 'Configuración guardada' : 'Settings saved', 'success');
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
          progress={pipelineProgress}
          autoExpand={autoExpandPipeline}
          onToggleAutoExpand={() => {
            const newValue = !autoExpandPipeline;
            setAutoExpandPipeline(newValue);
            localStorage.setItem('autoExpandPipeline', JSON.stringify(newValue));
          }}
        />
      )}
    </div>
  );
}

export default App;
