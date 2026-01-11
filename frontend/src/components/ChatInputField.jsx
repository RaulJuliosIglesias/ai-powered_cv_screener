import { useState, memo, useCallback, useRef } from 'react';
import { Send, Loader, ListPlus, Clock, X, Plus, Trash, Trash2, GripHorizontal, Beaker } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const TEST_QUERIES_BY_TYPE = {
  // ADAPTIVE queries - Dynamic tables with variable columns (NEW DEFAULT)
  adaptive: [
    "What technologies do the candidates have?",
    "What skills do the candidates possess?",
    "Show me all candidate certifications",
    "What languages do the candidates speak?",
    "Find Python developers",
    "Who knows React?",
    "Candidates with AWS experience",
    "Show me backend engineers",
    "Who has machine learning experience?",
    "List all frontend developers",
    "Candidates with cloud computing skills",
    "Who has worked with databases?",
    "Show me data scientists",
    "Find DevOps engineers",
    "Who has project management experience?"
  ],
  single_candidate: [
    "Give me the full profile of the top candidate",
    "Tell me everything about the best match",
    "Analyze the first candidate in detail",
    "Full profile of the most experienced person"
  ],
  red_flags: [
    "Show me the red flags in the candidate pool",
    "Analyze job hopping patterns",
    "Do a risk assessment of the candidates",
    "Make a risk assessment of the top candidate"
  ],
  ranking: [
    "Rank all candidates by experience",
    "Who is the best for a senior role?",
    "Give me the top 5 candidates",
    "Who has the best leadership potential?"
  ],
  comparison: [
    "Compare the top 2 candidates",
    "What are the differences between the senior candidates?",
    "Senior vs Junior candidates analysis"
  ],
  job_match: [
    "Who fits best for a project manager position?",
    "Match candidates to the senior developer requirements",
    "Who is suitable for a team lead role?"
  ],
  team_build: [
    "Build a team with the top 3 candidates",
    "Create a development team from the pool",
    "Form a complementary team for the project"
  ],
  verification: [
    "Verify if anyone has worked at Google",
    "Check if the candidate has AWS certification",
    "Did anyone work at Microsoft?"
  ],
  summary: [
    "Give me a summary of the candidate pool",
    "Overview of all candidates",
    "How many candidates have technical skills?"
  ]
};

const getRandomTestQueries = () => {
  const result = [];
  
  // Add 6 adaptive queries (the new default system)
  const adaptiveQueries = [...TEST_QUERIES_BY_TYPE.adaptive];
  for (let i = 0; i < 6 && adaptiveQueries.length > 0; i++) {
    const idx = Math.floor(Math.random() * adaptiveQueries.length);
    result.push(adaptiveQueries.splice(idx, 1)[0]);
  }
  
  // Add 1 query from each of 8 other categories (8 more queries)
  const otherTypes = Object.keys(TEST_QUERIES_BY_TYPE).filter(t => t !== 'adaptive').slice(0, 8);
  otherTypes.forEach(type => {
    const queries = TEST_QUERIES_BY_TYPE[type];
    result.push(queries[Math.floor(Math.random() * queries.length)]);
  });
  
  // Total: 6 adaptive + 8 other = 14, shuffle for variety
  return result.sort(() => Math.random() - 0.5);
};

const ChatInputField = memo(({ 
  onSend, 
  isLoading, 
  hasCV, 
  sessionName,
  queue = [],
  queueLength = 0,
  onAddToQueue,
  onRemoveFromQueue,
  onClearQueue
}) => {
  const [message, setMessage] = useState('');
  const [showQueuePanel, setShowQueuePanel] = useState(false);
  const [queueInput, setQueueInput] = useState('');
  const [textareaHeight, setTextareaHeight] = useState(100);
  const { language } = useLanguage();
  const isDraggingRef = useRef(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);

  const handleResizeStart = useCallback((e) => {
    e.preventDefault();
    isDraggingRef.current = true;
    startYRef.current = e.clientY || e.touches?.[0]?.clientY;
    startHeightRef.current = textareaHeight;
    
    const handleMove = (moveEvent) => {
      if (!isDraggingRef.current) return;
      const currentY = moveEvent.clientY || moveEvent.touches?.[0]?.clientY;
      const delta = startYRef.current - currentY;
      const newHeight = Math.min(300, Math.max(60, startHeightRef.current + delta));
      setTextareaHeight(newHeight);
    };
    
    const handleEnd = () => {
      isDraggingRef.current = false;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleEnd);
      document.removeEventListener('touchmove', handleMove);
      document.removeEventListener('touchend', handleEnd);
    };
    
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleEnd);
    document.addEventListener('touchmove', handleMove);
    document.addEventListener('touchend', handleEnd);
  }, [textareaHeight]);

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

  const handleAddToQueue = useCallback(() => {
    if (queueInput.trim() && onAddToQueue) {
      onAddToQueue(queueInput.trim());
      setQueueInput('');
    }
  }, [queueInput, onAddToQueue]);

  const handleQueueKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAddToQueue();
    }
  }, [handleAddToQueue]);

  const placeholder = hasCV 
    ? (language === 'es' ? 'Pregunta sobre los CVs...' : 'Ask about the CVs...')
    : (language === 'es' ? 'Sube CVs primero' : 'Upload CVs first');

  return (
    <>
      <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-5xl mx-auto flex items-end gap-3">
          {/* Textarea with custom resize handle at top */}
          <div className="flex-1 relative">
            {/* Resize handle at top-right */}
            <div 
              onMouseDown={handleResizeStart}
              onTouchStart={handleResizeStart}
              className="absolute -top-2 left-1/2 -translate-x-1/2 z-10 cursor-ns-resize px-3 py-1 bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 rounded-t-lg transition-colors group"
              title={language === 'es' ? 'Arrastra para cambiar tamaño' : 'Drag to resize'}
            >
              <GripHorizontal className="w-4 h-3 text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-200" />
            </div>
            <textarea 
              value={message}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-sm"
              style={{ height: `${textareaHeight}px`, minHeight: '60px', maxHeight: '300px' }}
            />
          </div>
          <button 
            onClick={handleSubmit}
            disabled={!message.trim() || isLoading || !hasCV}
            className="p-3 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-600 hover:to-cyan-600 text-white rounded-xl disabled:opacity-50 shadow-sm flex-shrink-0"
          >
            {isLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
          
          {/* Queue Button - appears when processing */}
          {isLoading && onAddToQueue && (
            <button
              type="button"
              onClick={() => setShowQueuePanel(true)}
              className="relative p-3 bg-amber-500 hover:bg-amber-600 text-white rounded-xl transition-colors shadow-lg shadow-amber-500/25 flex-shrink-0 animate-pulse"
              title={language === 'es' ? 'Añadir a cola' : 'Add to queue'}
            >
              <ListPlus className="w-5 h-5" />
              {queueLength > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                  {queueLength}
                </span>
              )}
            </button>
          )}
          
          {/* Queue indicator when not loading but has items */}
          {!isLoading && queueLength > 0 && onAddToQueue && (
            <button
              type="button"
              onClick={() => setShowQueuePanel(true)}
              className="relative p-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 rounded-xl transition-colors flex-shrink-0"
              title={language === 'es' ? `${queueLength} en cola` : `${queueLength} queued`}
            >
              <Clock className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                {queueLength}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Queue Panel Modal */}
      {showQueuePanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-lg shadow-2xl max-h-[80vh] flex flex-col">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl">
                  <ListPlus className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {language === 'es' ? 'Cola de Mensajes' : 'Message Queue'}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {language === 'es' 
                      ? `${queueLength} mensaje(s) en espera` 
                      : `${queueLength} message(s) waiting`}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setShowQueuePanel(false)} 
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            
            {/* Add to queue input */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
              <div className="flex gap-2">
                <textarea
                  value={queueInput}
                  onChange={(e) => setQueueInput(e.target.value)}
                  onKeyDown={handleQueueKeyDown}
                  placeholder={language === 'es' ? 'Escribe un mensaje para añadir a la cola...' : 'Type a message to add to queue...'}
                  rows={2}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-amber-500 text-sm"
                />
                <button
                  onClick={handleAddToQueue}
                  disabled={!queueInput.trim()}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Plus className="w-5 h-5" />
                </button>
              </div>
              
              {/* Auto-populate test queries button */}
              <button
                onClick={() => {
                  const testQueries = getRandomTestQueries();
                  testQueries.forEach(q => onAddToQueue && onAddToQueue(q));
                }}
                className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-100 dark:bg-purple-900/30 hover:bg-purple-200 dark:hover:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded-xl transition-colors text-sm font-medium"
              >
                <Beaker className="w-4 h-4" />
                {language === 'es' ? '🧪 Añadir Test Queries (14 queries)' : '🧪 Add Test Queries (14 queries)'}
              </button>
            </div>

            {/* Queue list */}
            <div className="flex-1 overflow-y-auto p-4">
              {queue.length === 0 ? (
                <div className="text-center py-8">
                  <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500 dark:text-gray-400">
                    {language === 'es' ? 'La cola está vacía' : 'Queue is empty'}
                  </p>
                  <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                    {language === 'es' 
                      ? 'Los mensajes se enviarán automáticamente cuando termine la respuesta actual' 
                      : 'Messages will be sent automatically when the current response finishes'}
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {queue.map((msg, idx) => (
                    <div 
                      key={idx}
                      className="group flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="flex-shrink-0 w-6 h-6 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-full flex items-center justify-center text-xs font-bold">
                        {idx + 1}
                      </div>
                      <p className="flex-1 text-sm text-gray-700 dark:text-gray-300 break-words">
                        {msg}
                      </p>
                      <button
                        onClick={() => onRemoveFromQueue && onRemoveFromQueue(idx)}
                        className="flex-shrink-0 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                        title={language === 'es' ? 'Eliminar' : 'Remove'}
                      >
                        <Trash className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer with clear button */}
            {queue.length > 0 && (
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center flex-shrink-0">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {language === 'es' 
                    ? 'Los mensajes se envían en orden' 
                    : 'Messages are sent in order'}
                </p>
                <button
                  onClick={() => onClearQueue && onClearQueue()}
                  className="flex items-center gap-2 px-3 py-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-sm transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  {language === 'es' ? 'Limpiar cola' : 'Clear queue'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
});

ChatInputField.displayName = 'ChatInputField';

export default ChatInputField;
