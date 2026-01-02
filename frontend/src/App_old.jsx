import { useState, useEffect, useCallback } from 'react';
import Layout from './components/Layout';
import SessionList from './components/SessionList';
import SessionDetail from './components/SessionDetail';
import ModelSelector from './components/ModelSelector';
import useMode from './hooks/useMode';
import useTheme from './hooks/useTheme';
import { useLanguage } from './contexts/LanguageContext';
import { 
  getSessions, 
  createSession, 
  getSession, 
  deleteSession,
  uploadCVsToSession,
  getSessionUploadStatus,
  removeCVFromSession,
  sendSessionMessage 
} from './services/api';

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const { mode } = useMode();
  const { theme, toggleTheme } = useTheme();
  const { language } = useLanguage();

  // Load all sessions
  const loadSessions = useCallback(async () => {
    try {
      setIsLoadingSessions(true);
      const data = await getSessions();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      setSessions([]);
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  // Load a specific session
  const loadSession = useCallback(async (sessionId) => {
    try {
      setIsLoadingSession(true);
      const data = await getSession(sessionId);
      setCurrentSession(data);
    } catch (error) {
      console.error('Failed to load session:', error);
      setCurrentSession(null);
      setCurrentSessionId(null);
    } finally {
      setIsLoadingSession(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Load session when selected
  useEffect(() => {
    if (currentSessionId) {
      loadSession(currentSessionId);
    } else {
      setCurrentSession(null);
    }
  }, [currentSessionId, loadSession]);

  // Create new session
  const handleCreateSession = useCallback(async (name, description) => {
    try {
      const newSession = await createSession(name, description);
      await loadSessions();
      setCurrentSessionId(newSession.id);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  }, [loadSessions]);

  // Delete session
  const handleDeleteSession = useCallback(async (sessionId) => {
    try {
      await deleteSession(sessionId, mode);
      await loadSessions();
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  }, [mode, loadSessions, currentSessionId]);

  // Select session
  const handleSelectSession = useCallback((sessionId) => {
    setCurrentSessionId(sessionId);
  }, []);

  // Go back to session list
  const handleBack = useCallback(() => {
    setCurrentSessionId(null);
    loadSessions();
  }, [loadSessions]);

  // Upload CVs to session
  const handleUploadCVs = useCallback(async (files) => {
    if (!currentSessionId || files.length === 0) return;
    
    try {
      setIsUploading(true);
      setUploadProgress(0);
      
      const response = await uploadCVsToSession(
        currentSessionId, 
        files, 
        mode,
        (progress) => setUploadProgress(progress)
      );
      
      // Poll for completion
      const pollStatus = async () => {
        try {
          const status = await getSessionUploadStatus(currentSessionId, response.job_id);
          if (status.status === 'processing') {
            setTimeout(pollStatus, 1000);
          } else {
            setIsUploading(false);
            setUploadProgress(0);
            await loadSession(currentSessionId);
          }
        } catch (error) {
          console.error('Failed to get upload status:', error);
          setIsUploading(false);
        }
      };
      
      pollStatus();
    } catch (error) {
      console.error('Failed to upload CVs:', error);
      setIsUploading(false);
    }
  }, [currentSessionId, mode, loadSession]);

  // Remove CV from session
  const handleRemoveCV = useCallback(async (cvId) => {
    if (!currentSessionId) return;
    
    try {
      await removeCVFromSession(currentSessionId, cvId, mode);
      await loadSession(currentSessionId);
    } catch (error) {
      console.error('Failed to remove CV:', error);
    }
  }, [currentSessionId, mode, loadSession]);

  // Send message in session
  const handleSendMessage = useCallback(async (message) => {
    if (!currentSessionId) return;
    
    try {
      setIsChatLoading(true);
      await sendSessionMessage(currentSessionId, message, mode);
      await loadSession(currentSessionId);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsChatLoading(false);
    }
  }, [currentSessionId, mode, loadSession]);

  return (
    <Layout
      showAddButton={false}
      theme={theme}
      onThemeToggle={toggleTheme}
    >
      <div className="flex flex-col h-[calc(100vh-81px)]">
        {/* Header Bar with Model Selector */}
        <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="px-4 py-3 flex items-center justify-end">
            <ModelSelector />
          </div>
        </div>
        
        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {currentSessionId ? (
            <SessionDetail
              session={currentSession}
              isLoading={isLoadingSession}
              isChatLoading={isChatLoading}
              isUploading={isUploading}
              uploadProgress={uploadProgress}
              onBack={handleBack}
              onSendMessage={handleSendMessage}
              onUploadCVs={handleUploadCVs}
              onRemoveCV={handleRemoveCV}
            />
          ) : (
            <SessionList
              sessions={sessions}
              isLoading={isLoadingSessions}
              onSelectSession={handleSelectSession}
              onCreateSession={handleCreateSession}
              onDeleteSession={handleDeleteSession}
            />
          )}
        </div>
      </div>
    </Layout>
  );
}

export default App;
