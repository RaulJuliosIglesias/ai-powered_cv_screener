import { useEffect, useRef } from 'react';
import Message from './Message';
import { Bot } from 'lucide-react';

const LoadingIndicator = () => (
  <div className="flex gap-3 max-w-3xl">
    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
      <Bot className="w-4 h-4 text-gray-600" />
    </div>
    <div className="flex-1">
      <span className="text-xs font-medium text-gray-500 uppercase">Assistant</span>
      <div className="mt-1 p-4 rounded-2xl bg-white border border-gray-200 rounded-tl-sm">
        <div className="flex items-center gap-1">
          <span className="loading-dot w-2 h-2 bg-gray-400 rounded-full"></span>
          <span className="loading-dot w-2 h-2 bg-gray-400 rounded-full"></span>
          <span className="loading-dot w-2 h-2 bg-gray-400 rounded-full"></span>
          <span className="ml-2 text-sm text-gray-500">Analyzing CVs...</span>
        </div>
      </div>
    </div>
  </div>
);

const MessageList = ({ messages, isLoading, welcomeMessage }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {messages.length === 0 && !isLoading && welcomeMessage && (
        <div className="flex gap-3 max-w-3xl">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
            <Bot className="w-4 h-4 text-gray-600" />
          </div>
          <div className="flex-1">
            <span className="text-xs font-medium text-gray-500 uppercase">Assistant</span>
            <div className="mt-1 p-4 rounded-2xl bg-white border border-gray-200 rounded-tl-sm">
              <div className="prose prose-sm max-w-none whitespace-pre-line">
                {welcomeMessage}
              </div>
            </div>
          </div>
        </div>
      )}

      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}

      {isLoading && <LoadingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
