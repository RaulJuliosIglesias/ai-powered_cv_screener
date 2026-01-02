import { useState, useEffect, useCallback } from 'react';
import Layout from './components/Layout';
import UploadZone from './components/UploadZone';
import ProcessingStatus from './components/ProcessingStatus';
import CVList from './components/CVList';
import ChatWindow from './components/ChatWindow';
import ModeSwitch from './components/ModeSwitch';
import MetricsBar from './components/MetricsBar';
import { useUpload } from './hooks/useUpload';
import { useChat } from './hooks/useChat';
import useMode from './hooks/useMode';
import useTheme from './hooks/useTheme';
import { getCVList } from './services/api';

const APP_STATES = {
  EMPTY: 'empty',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  READY: 'ready',
};

function App() {
  const [appState, setAppState] = useState(APP_STATES.EMPTY);
  const [cvs, setCvs] = useState([]);
  const [isLoadingCvs, setIsLoadingCvs] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  // Mode and theme management
  const { mode, setMode } = useMode();
  const { theme, toggleTheme } = useTheme();

  const loadCVs = useCallback(async () => {
    try {
      setIsLoadingCvs(true);
      const response = await getCVList(mode);
      setCvs(response.cvs || []);
      
      if (response.cvs && response.cvs.length > 0) {
        setAppState(APP_STATES.READY);
      } else {
        setAppState(APP_STATES.EMPTY);
      }
    } catch (error) {
      console.error('Failed to load CVs:', error);
      setCvs([]);
      setAppState(APP_STATES.EMPTY);
    } finally {
      setIsLoadingCvs(false);
    }
  }, [mode]);

  // Reload CVs when mode changes
  useEffect(() => {
    loadCVs();
  }, [loadCVs]);

  const handleProcessingComplete = useCallback(() => {
    loadCVs();
    setShowUploadModal(false);
  }, [loadCVs]);

  const {
    files,
    isUploading,
    isProcessing,
    uploadProgress,
    processingStatus,
    error: uploadError,
    addFiles,
    removeFile,
    upload,
    reset: resetUpload,
  } = useUpload(handleProcessingComplete, mode);

  const {
    messages,
    isLoading: isChatLoading,
    lastMetrics,
    send: sendMessage,
    clearMessages,
  } = useChat(mode);

  // Clear chat when mode changes
  useEffect(() => {
    clearMessages();
  }, [mode, clearMessages]);

  useEffect(() => {
    if (isUploading) {
      setAppState(APP_STATES.UPLOADING);
    } else if (isProcessing) {
      setAppState(APP_STATES.PROCESSING);
    } else if (cvs.length > 0) {
      setAppState(APP_STATES.READY);
    } else {
      setAppState(APP_STATES.EMPTY);
    }
  }, [isUploading, isProcessing, cvs.length]);

  const handleAddClick = () => {
    setShowUploadModal(true);
    resetUpload();
  };

  const handleModeChange = (newMode) => {
    if (!isUploading && !isProcessing && !isChatLoading) {
      setMode(newMode);
    }
  };

  const renderContent = () => {
    if (showUploadModal || appState === APP_STATES.EMPTY) {
      if (isProcessing) {
        return <ProcessingStatus status={processingStatus} />;
      }
      return (
        <UploadZone
          files={files}
          onFilesAdded={addFiles}
          onFileRemove={removeFile}
          onUpload={upload}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
          error={uploadError}
        />
      );
    }

    if (appState === APP_STATES.PROCESSING) {
      return <ProcessingStatus status={processingStatus} />;
    }

    if (appState === APP_STATES.READY) {
      return (
        <div className="flex h-full">
          <CVList cvs={cvs} isLoading={isLoadingCvs} />
          <ChatWindow
            messages={messages}
            isLoading={isChatLoading}
            onSend={sendMessage}
          />
        </div>
      );
    }

    return null;
  };

  return (
    <Layout
      showAddButton={appState === APP_STATES.READY && !showUploadModal}
      onAddClick={handleAddClick}
      theme={theme}
      onThemeToggle={toggleTheme}
    >
      <div className="flex flex-col h-[calc(100vh-81px)]">
        {/* Mode Switch and Metrics Bar */}
        <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="px-4 py-3">
            <ModeSwitch
              mode={mode}
              onModeChange={handleModeChange}
              disabled={isUploading || isProcessing || isChatLoading}
            />
          </div>
          {lastMetrics && <MetricsBar metrics={lastMetrics} mode={mode} />}
        </div>
        
        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {renderContent()}
        </div>
      </div>
    </Layout>
  );
}

export default App;
