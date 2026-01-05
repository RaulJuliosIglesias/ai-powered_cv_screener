import { useState } from 'react';
import { Plus, MessageSquare, Trash2, Check, X, Edit2, Loader, FileText, Database, Cloud, Sun, Moon, ChevronRight } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const Sidebar = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
  onOpenCVPanel,
  onOpenAllCVs,
  mode,
  onModeChange,
  theme,
  onThemeToggle,
  chatLoadingStates,
  deletingSessionId,
}) => {
  const { language, setLanguage } = useLanguage();
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const handleStartEdit = (session) => {
    setEditingId(session.id);
    setEditName(session.name);
  };

  const handleConfirmRename = (id) => {
    if (editName.trim()) {
      onRenameSession(id, editName.trim());
    }
    setEditingId(null);
  };

  const handleDeleteClick = (id) => {
    if (deleteConfirm === id) {
      onDeleteSession(id);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(id);
    }
  };

  return (
    <div className="w-64 flex-shrink-0 sidebar-bg border-r border-slate-200 dark:border-slate-800 flex flex-col">
      {/* New Chat Button */}
      <div className="p-3">
        <button 
          onClick={onNewChat} 
          className="w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-white transition-colors focus-ring"
          aria-label={language === 'es' ? 'Nuevo chat' : 'New chat'}
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm">{language === 'es' ? 'Nuevo chat' : 'New chat'}</span>
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-2">
        {sessions.map((session, index) => (
          <div key={session.id} className={`mb-1 stagger-item`} style={{ animationDelay: `${index * 30}ms` }}>
            <div 
              onClick={() => deletingSessionId !== session.id && onSelectSession(session.id)} 
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                deletingSessionId === session.id 
                  ? 'bg-red-50 dark:bg-red-900/20 opacity-60 cursor-not-allowed' 
                  : currentSessionId === session.id 
                    ? 'bg-blue-100 dark:bg-slate-800 text-blue-700 dark:text-white' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800/50'
              }`}
              role="button"
              tabIndex={0}
              aria-selected={currentSessionId === session.id}
            >
              {/* Icon */}
              {deletingSessionId === session.id ? (
                <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-red-400" aria-hidden="true" />
              ) : chatLoadingStates[session.id] ? (
                <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-cyan-400" aria-hidden="true" />
              ) : (
                <MessageSquare className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              )}

              {/* Name */}
              {editingId === session.id ? (
                <input 
                  value={editName} 
                  onChange={(e) => setEditName(e.target.value)} 
                  onBlur={() => handleConfirmRename(session.id)} 
                  onKeyDown={(e) => e.key === 'Enter' && handleConfirmRename(session.id)} 
                  className="flex-1 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm px-2 py-0.5 rounded outline-none border border-slate-300 dark:border-slate-600 focus-ring" 
                  autoFocus 
                  onClick={(e) => e.stopPropagation()} 
                  aria-label={language === 'es' ? 'Nombre del chat' : 'Chat name'}
                />
              ) : (
                <div className="flex-1 min-w-0">
                  <span className="text-sm truncate block">
                    {deletingSessionId === session.id 
                      ? (language === 'es' ? 'Eliminando...' : 'Deleting...') 
                      : session.name}
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    {session.cv_count || 0} CVs
                  </span>
                </div>
              )}

              {/* Action Buttons */}
              {deletingSessionId !== session.id && (
                <div className="hidden group-hover:flex items-center gap-1">
                  {deleteConfirm === session.id ? (
                    <>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDeleteClick(session.id); }} 
                        className="p-1 hover:bg-red-500/20 rounded focus-ring"
                        aria-label={language === 'es' ? 'Confirmar eliminar' : 'Confirm delete'}
                      >
                        <Check className="w-3.5 h-3.5 text-red-400" />
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }} 
                        className="p-1 focus-ring"
                        aria-label={language === 'es' ? 'Cancelar' : 'Cancel'}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        onClick={(e) => { e.stopPropagation(); onOpenCVPanel(session.id); }} 
                        className="p-1 hover:bg-slate-300 dark:hover:bg-slate-700 rounded transition-colors focus-ring" 
                        title={language === 'es' ? 'Ver CVs' : 'View CVs'}
                        aria-label={language === 'es' ? 'Ver CVs' : 'View CVs'}
                      >
                        <FileText className="w-3.5 h-3.5" />
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleStartEdit(session); }} 
                        className="p-1 hover:bg-slate-300 dark:hover:bg-slate-700 rounded transition-colors focus-ring"
                        aria-label={language === 'es' ? 'Renombrar' : 'Rename'}
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDeleteClick(session.id); }} 
                        className="p-1 hover:bg-slate-300 dark:hover:bg-slate-700 rounded transition-colors focus-ring"
                        aria-label={language === 'es' ? 'Eliminar' : 'Delete'}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Controls */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2">
        {/* Mode Selector */}
        <div className="flex items-center gap-2 px-2 py-2 bg-white dark:bg-slate-900 rounded-lg">
          <span className="text-xs text-slate-500 dark:text-slate-400 w-12 font-medium">Mode:</span>
          <button 
            onClick={() => onModeChange('local')} 
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors focus-ring ${
              mode === 'local' 
                ? 'bg-blue-500 text-white shadow-sm' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            aria-pressed={mode === 'local'}
          >
            <Database className="w-3 h-3" aria-hidden="true" /> Local
          </button>
          <button 
            onClick={() => onModeChange('cloud')} 
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-colors focus-ring ${
              mode === 'cloud' 
                ? 'bg-blue-500 text-white shadow-sm' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            aria-pressed={mode === 'cloud'}
          >
            <Cloud className="w-3 h-3" aria-hidden="true" /> Supabase
          </button>
        </div>

        {/* Language Selector */}
        <div className="flex items-center gap-2 px-2 py-2 bg-white dark:bg-slate-900 rounded-lg">
          <span className="text-xs text-slate-500 dark:text-slate-400 w-12 font-medium">Lang:</span>
          <button 
            onClick={() => setLanguage('en')} 
            className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors focus-ring ${
              language === 'en' 
                ? 'bg-blue-500 text-white shadow-sm' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            aria-pressed={language === 'en'}
          >
            EN
          </button>
          <button 
            onClick={() => setLanguage('es')} 
            className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors focus-ring ${
              language === 'es' 
                ? 'bg-blue-500 text-white shadow-sm' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            aria-pressed={language === 'es'}
          >
            ES
          </button>
        </div>

        {/* Theme Toggle */}
        <button 
          onClick={onThemeToggle} 
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium transition-colors focus-ring"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-slate-500" />}
          <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>

        {/* All CVs Button */}
        <button 
          onClick={onOpenAllCVs} 
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium transition-colors focus-ring"
          aria-label={language === 'es' ? 'Ver todos los CVs' : 'View all CVs'}
        >
          <FileText className="w-4 h-4 text-blue-500" aria-hidden="true" />
          <span>{language === 'es' ? 'Todos los CVs' : 'All CVs'}</span>
          <ChevronRight className="w-4 h-4 ml-auto text-slate-400" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
