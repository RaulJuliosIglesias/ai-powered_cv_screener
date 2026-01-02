import { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, MessageSquare, Trash2, Send, Loader, Upload, FileText, X, Check, Edit2, Moon, Sun, Sparkles, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import useMode from './hooks/useMode';
import useTheme from './hooks/useTheme';
import { useLanguage } from './contexts/LanguageContext';
import SourceBadge from './components/SourceBadge';
import ModelSelector from './components/ModelSelector';
import { getSessions, createSession, getSession, deleteSession, updateSession, uploadCVsToSession, getSessionUploadStatus, removeCVFromSession, sendSessionMessage, getSessionSuggestions } from './services/api';

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [message, setMessage] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const { mode } = useMode();
  const { theme, toggleTheme } = useTheme();
  const { language } = useLanguage();

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [currentSession?.messages]);

  const loadSessions = useCallback(async () => {
    try { const data = await getSessions(); setSessions(data.sessions || []); } catch (e) { console.error(e); }
  }, []);

  const loadSession = useCallback(async (id) => {
    try {
      const data = await getSession(id);
      setCurrentSession(data);
      const sugg = await getSessionSuggestions(id, mode);
      setSuggestions(sugg.suggestions || []);
    } catch (e) { console.error(e); setCurrentSessionId(null); }
  }, [mode]);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { if (currentSessionId) loadSession(currentSessionId); else { setCurrentSession(null); setSuggestions([]); } }, [currentSessionId, loadSession]);

  const handleNewChat = async () => {
    const name = language === 'es' ? 'Nuevo chat' : 'New chat';
    const session = await createSession(name);
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
    await updateSession(id, { name: editName.trim() });
    await loadSessions();
    if (currentSessionId === id) await loadSession(id);
    setEditingId(null);
  };

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files).filter(f => f.name.endsWith('.pdf'));
    if (!files.length || !currentSessionId) return;
    setIsUploading(true);
    try {
      const res = await uploadCVsToSession(currentSessionId, files, mode);
      const poll = async () => {
        const status = await getSessionUploadStatus(currentSessionId, res.job_id);
        if (status.status === 'processing') setTimeout(poll, 1000);
        else { setIsUploading(false); await loadSession(currentSessionId); }
      };
      poll();
    } catch (e) { console.error(e); setIsUploading(false); }
    e.target.value = '';
  };

  const handleSend = async (text = message) => {
    if (!text.trim() || !currentSessionId || isChatLoading || !currentSession?.cvs?.length) return;
    setMessage('');
    setIsChatLoading(true);
    try { await sendSessionMessage(currentSessionId, text.trim(), mode); await loadSession(currentSessionId); } catch (e) { console.error(e); }
    setIsChatLoading(false);
  };

  const handleRemoveCV = async (cvId) => {
    await removeCVFromSession(currentSessionId, cvId, mode);
    await loadSession(currentSessionId);
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
            <div key={s.id} onClick={() => setCurrentSessionId(s.id)} className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer mb-0.5 ${currentSessionId === s.id ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800/50'}`}>
              <MessageSquare className="w-4 h-4 flex-shrink-0" />
              {editingId === s.id ? (
                <input value={editName} onChange={(e) => setEditName(e.target.value)} onBlur={() => handleRename(s.id)} onKeyDown={(e) => e.key === 'Enter' && handleRename(s.id)} className="flex-1 bg-gray-700 text-white text-sm px-2 py-0.5 rounded outline-none" autoFocus onClick={(e) => e.stopPropagation()} />
              ) : <span className="flex-1 text-sm truncate">{s.name}</span>}
              <div className="hidden group-hover:flex items-center gap-1">
                {deleteConfirm === s.id ? (
                  <><button onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }} className="p-1 hover:bg-red-500/20 rounded"><Check className="w-3.5 h-3.5 text-red-400" /></button><button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null); }} className="p-1"><X className="w-3.5 h-3.5" /></button></>
                ) : (
                  <><button onClick={(e) => { e.stopPropagation(); setEditingId(s.id); setEditName(s.name); }} className="p-1 hover:bg-gray-700 rounded"><Edit2 className="w-3.5 h-3.5" /></button><button onClick={(e) => { e.stopPropagation(); setDeleteConfirm(s.id); }} className="p-1 hover:bg-gray-700 rounded"><Trash2 className="w-3.5 h-3.5" /></button></>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-gray-800">
          <button onClick={toggleTheme} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 text-gray-300 text-sm">
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col bg-white dark:bg-gray-800 min-w-0">
        <div className="h-12 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{currentSession ? `${currentSession.name} · ${currentSession.cvs?.length || 0} CVs` : 'CV Screener'}</span>
          <div className="flex items-center gap-2">
            <ModelSelector />
            {currentSession && (<><input ref={fileInputRef} type="file" accept=".pdf" multiple onChange={handleUpload} className="hidden" /><button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-50">{isUploading ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}<span>{language === 'es' ? 'Añadir CVs' : 'Add CVs'}</span></button></>)}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {!currentSession ? (
            <div className="h-full flex items-center justify-center"><div className="text-center"><Sparkles className="w-12 h-12 text-blue-500 mx-auto mb-4" /><h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-2">CV Screener</h2><p className="text-gray-500 mb-6">{language === 'es' ? 'Crea un chat y sube CVs' : 'Create a chat and upload CVs'}</p><button onClick={handleNewChat} className="px-6 py-3 bg-blue-500 text-white rounded-xl">{language === 'es' ? 'Nuevo chat' : 'New chat'}</button></div></div>
          ) : currentSession.messages?.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center"><Sparkles className="w-10 h-10 text-blue-500 mb-4" /><h3 className="text-xl font-medium text-gray-800 dark:text-white mb-6">{currentSession.cvs?.length ? (language === 'es' ? '¿Qué quieres saber?' : 'What do you want to know?') : (language === 'es' ? 'Sube CVs para empezar' : 'Upload CVs to start')}</h3>
              {suggestions.length > 0 && <div className="grid grid-cols-2 gap-3 max-w-2xl">{suggestions.map((s, i) => (<button key={i} onClick={() => handleSend(s)} className="p-4 text-left text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl text-gray-700 dark:text-gray-200">{s}</button>))}</div>}
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {currentSession.messages.map((msg, idx) => (
                <div key={idx} className={msg.role === 'user' ? 'flex justify-end' : ''}>
                  <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-500' : 'bg-gradient-to-br from-blue-500 to-purple-600'}`}>{msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Sparkles className="w-4 h-4 text-white" />}</div>
                    <div className={`p-3 rounded-xl ${msg.role === 'user' ? 'bg-blue-500 text-white rounded-tr-sm' : 'bg-gray-100 dark:bg-gray-700 rounded-tl-sm'}`}>
                      <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : 'dark:prose-invert'}`}><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                      {msg.sources?.length > 0 && <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 flex flex-wrap gap-1">{msg.sources.map((src, i) => <SourceBadge key={i} filename={src.filename} score={src.relevance} />)}</div>}
                    </div>
                  </div>
                </div>
              ))}
              {isChatLoading && <div className="flex gap-3"><div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center"><Sparkles className="w-4 h-4 text-white" /></div><div className="bg-gray-100 dark:bg-gray-700 rounded-xl p-3"><Loader className="w-5 h-5 animate-spin text-blue-500" /></div></div>}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {currentSession && (
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <div className="max-w-3xl mx-auto flex gap-3">
              <textarea value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }}} placeholder={currentSession.cvs?.length ? (language === 'es' ? 'Pregunta sobre los CVs...' : 'Ask about the CVs...') : (language === 'es' ? 'Sube CVs primero' : 'Upload CVs first')} disabled={isChatLoading || !currentSession.cvs?.length} rows={1} className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
              <button onClick={() => handleSend()} disabled={!message.trim() || isChatLoading || !currentSession.cvs?.length} className="p-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl disabled:opacity-50">{isChatLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
