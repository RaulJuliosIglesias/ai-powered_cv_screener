import { useEffect, useRef } from 'react';
import Message from './Message';
import { Bot, Sparkles, MessageCircle } from 'lucide-react';

const LoadingIndicator = () => (
  <div className="flex gap-3 max-w-3xl">
    <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
      <Sparkles className="w-5 h-5 text-white" />
    </div>
    <div className="flex-1">
      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Asistente</span>
      <div className="mt-1 p-4 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
          </div>
          <span className="text-sm text-gray-500 dark:text-gray-400">Analizando CVs...</span>
        </div>
      </div>
    </div>
  </div>
);

const WelcomeMessage = () => (
  <div className="flex flex-col items-center justify-center h-full py-12">
    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-6 shadow-xl">
      <MessageCircle className="w-10 h-10 text-white" />
    </div>
    <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">¡Hola! Soy tu asistente de CVs</h2>
    <p className="text-gray-500 dark:text-gray-400 text-center max-w-md mb-6">
      Puedo ayudarte a analizar y comparar los CVs que has subido. Pregúntame lo que necesites.
    </p>
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
      {[
        '¿Quién tiene más experiencia en Python?',
        '¿Qué candidatos tienen título universitario?',
        'Compara los 3 mejores candidatos',
        '¿Quién ha trabajado en startups?',
      ].map((suggestion, i) => (
        <div key={i} className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-600 cursor-pointer transition-colors">
          {suggestion}
        </div>
      ))}
    </div>
  </div>
);

const MessageList = ({ messages, isLoading }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {messages.length === 0 && !isLoading && <WelcomeMessage />}

      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}

      {isLoading && <LoadingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
