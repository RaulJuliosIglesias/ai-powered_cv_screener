import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  ArrowLeft, FileText, Trash2, Plus, Send, Loader, 
  Sparkles, User, X, Check, Upload, ChevronDown, ChevronUp
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useLanguage } from '../contexts/LanguageContext';
import SourceBadge from './SourceBadge';

const SessionDetail = ({
  session,
  isLoading,
  isChatLoading,
  onBack,
  onSendMessage,
  onUploadCVs,
  onRemoveCV,
  uploadProgress,
  isUploading,
}) => {
  const [message, setMessage] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [showAllCVs, setShowAllCVs] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const { language } = useLanguage();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [session?.messages, scrollToBottom]);

  const handleSend = (e) => {
    e.preventDefault();
    if (message.trim() && !isChatLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  const handleFilesSelected = (e) => {
    const files = Array.from(e.target.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleUpload = async () => {
    if (selectedFiles.length > 0) {
      await onUploadCVs(selectedFiles);
      setSelectedFiles([]);
      setShowUploadPanel(false);
    }
  };

  const handleDeleteCV = (cvId) => {
    if (deleteConfirm === cvId) {
      onRemoveCV(cvId);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(cvId);
    }
  };

  if (isLoading || !session) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const displayedCVs = showAllCVs ? session.cvs : session.cvs.slice(0, 5);
  const hasMoreCVs = session.cvs.length > 5;

  return (
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {session.name}
            </h1>
            {session.description && (
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                {session.description}
              </p>
            )}
          </div>
          <button
            onClick={() => setShowUploadPanel(!showUploadPanel)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">
              {language === 'es' ? 'Añadir CVs' : 'Add CVs'}
            </span>
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* CV Sidebar */}
        <div className="w-64 flex-shrink-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                CVs ({session.cvs.length})
              </span>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2">
            {session.cvs.length === 0 ? (
              <div className="text-center py-8 px-4">
                <FileText className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {language === 'es' ? 'Sin CVs' : 'No CVs'}
                </p>
                <button
                  onClick={() => setShowUploadPanel(true)}
                  className="mt-2 text-sm text-blue-500 hover:text-blue-600"
                >
                  {language === 'es' ? 'Subir CVs' : 'Upload CVs'}
                </button>
              </div>
            ) : (
              <>
                {displayedCVs.map((cv) => (
                  <div
                    key={cv.id}
                    className="group flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 mb-1"
                  >
                    <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />
                    <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 truncate">
                      {cv.filename.replace('.pdf', '')}
                    </span>
                    {deleteConfirm === cv.id ? (
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleDeleteCV(cv.id)}
                          className="p-1 bg-red-500 text-white rounded text-xs"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="p-1 bg-gray-200 dark:bg-gray-600 rounded text-xs"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleDeleteCV(cv.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
                {hasMoreCVs && (
                  <button
                    onClick={() => setShowAllCVs(!showAllCVs)}
                    className="w-full mt-2 p-2 text-xs text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg flex items-center justify-center gap-1"
                  >
                    {showAllCVs ? (
                      <>
                        <ChevronUp className="w-3 h-3" />
                        {language === 'es' ? 'Ver menos' : 'Show less'}
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3 h-3" />
                        {language === 'es' ? `Ver todos (${session.cvs.length - 5} más)` : `Show all (${session.cvs.length - 5} more)`}
                      </>
                    )}
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4">
            {session.messages.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center max-w-md">
                  <Sparkles className="w-12 h-12 text-blue-500 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    {language === 'es' ? `Chat de ${session.name}` : `${session.name} Chat`}
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400">
                    {session.cvs.length > 0 
                      ? (language === 'es' 
                          ? `Haz preguntas sobre los ${session.cvs.length} CVs de este grupo` 
                          : `Ask questions about the ${session.cvs.length} CVs in this group`)
                      : (language === 'es' 
                          ? 'Sube CVs para comenzar a hacer preguntas' 
                          : 'Upload CVs to start asking questions')
                    }
                  </p>
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-4">
                {session.messages.map((msg, idx) => (
                  <div key={msg.id || idx} className={msg.role === 'user' ? 'flex justify-end' : ''}>
                    <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                      <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                        msg.role === 'user' 
                          ? 'bg-blue-500' 
                          : 'bg-gradient-to-br from-blue-500 to-purple-600'
                      }`}>
                        {msg.role === 'user' 
                          ? <User className="w-4 h-4 text-white" />
                          : <Sparkles className="w-4 h-4 text-white" />
                        }
                      </div>
                      <div className={`flex-1 ${msg.role === 'user' ? 'text-right' : ''}`}>
                        <div className={`p-3 rounded-xl ${
                          msg.role === 'user'
                            ? 'bg-blue-500 text-white rounded-tr-sm'
                            : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm'
                        }`}>
                          <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : 'dark:prose-invert'}`}>
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </div>
                          {msg.role !== 'user' && msg.sources?.length > 0 && (
                            <div className="mt-3 pt-2 border-t border-gray-100 dark:border-gray-700">
                              <p className="text-xs text-gray-500 mb-1.5">📎 {language === 'es' ? 'Fuentes' : 'Sources'}:</p>
                              <div className="flex flex-wrap gap-1.5">
                                {msg.sources.map((src, i) => (
                                  <SourceBadge key={i} filename={src.filename} score={src.relevance} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl rounded-tl-sm p-3">
                      <Loader className="w-5 h-5 animate-spin text-blue-500" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
            <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-3">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={session.cvs.length > 0 
                  ? (language === 'es' ? 'Pregunta sobre los CVs...' : 'Ask about the CVs...')
                  : (language === 'es' ? 'Sube CVs primero...' : 'Upload CVs first...')
                }
                disabled={isChatLoading || session.cvs.length === 0}
                rows={1}
                className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!message.trim() || isChatLoading || session.cvs.length === 0}
                className="p-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isChatLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Upload Panel */}
      {showUploadPanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {language === 'es' ? 'Subir CVs' : 'Upload CVs'}
              </h2>
              <button onClick={() => setShowUploadPanel(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFilesSelected}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="w-full p-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-blue-400 transition-colors"
              >
                <Upload className="w-10 h-10 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-600 dark:text-gray-400">
                  {language === 'es' ? 'Haz clic para seleccionar PDFs' : 'Click to select PDFs'}
                </p>
              </button>

              {selectedFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {selectedFiles.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <FileText className="w-4 h-4 text-red-500" />
                      <span className="flex-1 text-sm truncate">{file.name}</span>
                      <button
                        onClick={() => setSelectedFiles(prev => prev.filter((_, i) => i !== idx))}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {isUploading && (
                <div className="mt-4">
                  <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-2 text-center">
                    {language === 'es' ? 'Procesando...' : 'Processing...'}
                  </p>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowUploadPanel(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl"
              >
                {language === 'es' ? 'Cancelar' : 'Cancel'}
              </button>
              <button
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || isUploading}
                className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl disabled:opacity-50"
              >
                {isUploading 
                  ? (language === 'es' ? 'Subiendo...' : 'Uploading...')
                  : (language === 'es' ? `Subir ${selectedFiles.length} archivo(s)` : `Upload ${selectedFiles.length} file(s)`)
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionDetail;
