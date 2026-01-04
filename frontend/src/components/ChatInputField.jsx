import { useState, memo, useCallback } from 'react';
import { Send, Loader } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const ChatInputField = memo(({ onSend, isLoading, hasCV, sessionName }) => {
  const [message, setMessage] = useState('');
  const { language } = useLanguage();

  const handleChange = useCallback((e) => {
    setMessage(e.target.value);
  }, []);

  const handleSubmit = useCallback(() => {
    if (message.trim() && !isLoading && hasCV) {
      onSend(message.trim());
      setMessage('');
    }
  }, [message, isLoading, hasCV, onSend]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const placeholder = hasCV 
    ? (language === 'es' ? 'Pregunta sobre los CVs...' : 'Ask about the CVs...')
    : (language === 'es' ? 'Sube CVs primero' : 'Upload CVs first');

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900">
      <div className="max-w-5xl mx-auto flex gap-3">
        <textarea 
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-sm"
        />
        <button 
          onClick={handleSubmit}
          disabled={!message.trim() || isLoading || !hasCV}
          className="p-3 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white rounded-xl disabled:opacity-50 shadow-sm"
        >
          {isLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );
});

ChatInputField.displayName = 'ChatInputField';

export default ChatInputField;
