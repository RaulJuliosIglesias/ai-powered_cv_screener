import { useState } from 'react';
import { 
  FolderPlus, MessageSquare, FileText, Trash2, 
  ChevronRight, Users, Calendar, Edit2, X, Check, Loader2 
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useBackgroundTask } from '../contexts/BackgroundTaskContext';

const SessionList = ({ 
  sessions = [], 
  isLoading, 
  onSelectSession, 
  onCreateSession, 
  onDeleteSession 
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [newSessionDesc, setNewSessionDesc] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const { language } = useLanguage();
  const { isSessionProcessing, getSessionProcessingInfo } = useBackgroundTask();

  const handleCreate = () => {
    if (newSessionName.trim()) {
      onCreateSession(newSessionName.trim(), newSessionDesc.trim());
      setNewSessionName('');
      setNewSessionDesc('');
      setShowCreateModal(false);
    }
  };

  const handleDelete = (e, sessionId) => {
    e.stopPropagation();
    if (deleteConfirm === sessionId) {
      onDeleteSession(sessionId);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(sessionId);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(language === 'es' ? 'es-ES' : 'en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">
          {language === 'es' ? 'Cargando sesiones...' : 'Loading sessions...'}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {language === 'es' ? 'Grupos de CVs' : 'CV Groups'}
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            {language === 'es' 
              ? 'Organiza tus CVs en grupos para hacer consultas específicas' 
              : 'Organize your CVs into groups for specific queries'}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {/* Create New Session Button */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="w-full mb-6 p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-2xl hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all group"
          >
            <div className="flex items-center justify-center gap-3 text-gray-500 dark:text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400">
              <FolderPlus className="w-8 h-8" />
              <span className="text-lg font-medium">
                {language === 'es' ? 'Crear nuevo grupo' : 'Create new group'}
              </span>
            </div>
          </button>

          {/* Sessions Grid */}
          {sessions.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400 text-lg">
                {language === 'es' ? 'No hay grupos de CVs' : 'No CV groups yet'}
              </p>
              <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
                {language === 'es' 
                  ? 'Crea un grupo y sube CVs para comenzar' 
                  : 'Create a group and upload CVs to start'}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {sessions.map((session) => {
                const processing = isSessionProcessing(session.id);
                const processingInfo = processing ? getSessionProcessingInfo(session.id) : null;
                
                return (
                  <div
                    key={session.id}
                    onClick={() => onSelectSession(session.id)}
                    className={`group rounded-2xl border p-5 cursor-pointer transition-all relative overflow-hidden
                      ${processing 
                        ? 'bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border-amber-300 dark:border-amber-600 shadow-amber-100 dark:shadow-amber-900/30 shadow-md' 
                        : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg'
                      }`}
                  >
                    {/* Processing indicator bar */}
                    {processing && processingInfo && (
                      <div className="absolute top-0 left-0 right-0 h-1 bg-amber-200 dark:bg-amber-800">
                        <div 
                          className="h-full bg-amber-500 transition-all duration-300 ease-out"
                          style={{ width: `${processingInfo.percent}%` }}
                        />
                      </div>
                    )}
                    
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900 dark:text-white truncate text-lg">
                            {session.name}
                          </h3>
                          {processing && (
                            <Loader2 className="w-4 h-4 text-amber-500 animate-spin flex-shrink-0" />
                          )}
                        </div>
                        {session.description && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-1">
                            {session.description}
                          </p>
                        )}
                        {processing && processingInfo && (
                          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1 font-medium">
                            {language === 'es' 
                              ? `Procesando CVs... ${processingInfo.percent}%` 
                              : `Processing CVs... ${processingInfo.percent}%`}
                          </p>
                        )}
                      </div>
                      <ChevronRight className={`w-5 h-5 transition-colors flex-shrink-0 ${processing ? 'text-amber-500' : 'text-gray-400 group-hover:text-blue-500'}`} />
                    </div>

                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex items-center gap-1.5">
                        <FileText className="w-4 h-4" />
                        <span>{session.cv_count} CVs</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <MessageSquare className="w-4 h-4" />
                        <span>{session.message_count} {language === 'es' ? 'msgs' : 'msgs'}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
                      <div className="flex items-center gap-1.5 text-xs text-gray-400">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>{formatDate(session.updated_at)}</span>
                      </div>
                      
                      {deleteConfirm === session.id ? (
                        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={(e) => handleDelete(e, session.id)}
                            className="p-1.5 bg-red-500 text-white rounded hover:bg-red-600"
                            title={language === 'es' ? 'Confirmar' : 'Confirm'}
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }}
                            className="p-1.5 bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 rounded"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); setDeleteConfirm(session.id); }}
                          className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all"
                          title={language === 'es' ? 'Eliminar' : 'Delete'}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {language === 'es' ? 'Crear nuevo grupo' : 'Create new group'}
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  {language === 'es' ? 'Nombre del grupo' : 'Group name'} *
                </label>
                <input
                  type="text"
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                  placeholder={language === 'es' ? 'Ej: Senior Engineers' : 'E.g.: Senior Engineers'}
                  className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  {language === 'es' ? 'Descripción (opcional)' : 'Description (optional)'}
                </label>
                <textarea
                  value={newSessionDesc}
                  onChange={(e) => setNewSessionDesc(e.target.value)}
                  placeholder={language === 'es' ? 'Describe el propósito de este grupo...' : 'Describe the purpose of this group...'}
                  rows={3}
                  className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3 justify-end">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors"
              >
                {language === 'es' ? 'Cancelar' : 'Cancel'}
              </button>
              <button
                onClick={handleCreate}
                disabled={!newSessionName.trim()}
                className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {language === 'es' ? 'Crear grupo' : 'Create group'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionList;
