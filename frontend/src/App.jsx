import { useState, useEffect, useCallback } from 'react';
import Layout from './components/Layout';
import UploadZone from './components/UploadZone';
import ProcessingStatus from './components/ProcessingStatus';
import CVList from './components/CVList';
import ChatWindow from './components/ChatWindow';
import { useUpload } from './hooks/useUpload';
import { useChat } from './hooks/useChat';
import { getCVList, getWelcomeMessage } from './services/api';

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
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);

  const loadCVs = useCallback(async () => {
    try {
      setIsLoadingCvs(true);
      const response = await getCVList();
      setCvs(response.cvs || []);
      
      if (response.cvs && response.cvs.length > 0) {
        setAppState(APP_STATES.READY);
      } else {
        setAppState(APP_STATES.EMPTY);
      }
    } catch (error) {
      console.error('Failed to load CVs:', error);
    } finally {
      setIsLoadingCvs(false);
    }
  }, []);

  const loadWelcomeMessage = useCallback(async () => {
    try {
      const response = await getWelcomeMessage();
      setWelcomeMessage(response.message);
    } catch (error) {
      console.error('Failed to load welcome message:', error);
    }
  }, []);

  useEffect(() => {
    loadCVs();
    loadWelcomeMessage();
  }, [loadCVs, loadWelcomeMessage]);

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
  } = useUpload(handleProcessingComplete);

  const {
    messages,
    isLoading: isChatLoading,
    send: sendMessage,
  } = useChat();

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
            welcomeMessage={welcomeMessage}
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
    >
      <div className="h-[calc(100vh-73px)]">
        {renderContent()}
      </div>
    </Layout>
  );
}

export default App;
