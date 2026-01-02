import { useEffect, useRef, useState } from 'react';
import Message from './Message';
import { Bot, Sparkles, MessageCircle, ChevronDown, ChevronRight, Search, Cpu, Database, Zap } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const ThinkingPanel = ({ steps, isExpanded, onToggle }) => {
  const { t } = useLanguage();
  
  return (
    <div className="flex gap-3 max-w-3xl">
      <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
        <Sparkles className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('assistant')}</span>
        <div className="mt-1 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm overflow-hidden">
          {/* Thinking Header */}
          <button 
            onClick={onToggle}
            className="w-full px-4 py-3 flex items-center gap-2 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-purple-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-purple-500" />
            )}
            <Cpu className="w-4 h-4 text-purple-500 animate-pulse" />
            <span className="text-sm font-medium text-purple-600 dark:text-purple-400">{t('thinking')}...</span>
          </button>
          
          {/* Thinking Steps */}
          {isExpanded && (
            <div className="px-4 py-3 space-y-2 bg-gray-50/50 dark:bg-gray-800/50">
              {steps.map((step, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  {step.status === 'active' ? (
                    <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                  ) : step.status === 'done' ? (
                    <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                      <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                  )}
                  <span className={step.status === 'active' ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'}>
                    {step.text}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const LoadingIndicator = ({ reasoningSteps, showReasoning }) => {
  const { t } = useLanguage();
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (showReasoning && reasoningSteps.length > 0) {
    return <ThinkingPanel steps={reasoningSteps} isExpanded={isExpanded} onToggle={() => setIsExpanded(!isExpanded)} />;
  }
  
  return (
    <div className="flex gap-3 max-w-3xl">
      <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
        <Sparkles className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">{t('assistant')}</span>
        <div className="mt-1 p-4 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm">
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">{t('analyzingCvs')}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const WelcomeMessage = ({ onSuggestionClick }) => {
  const { t } = useLanguage();
  const suggestions = t('suggestions');
  
  return (
    <div className="flex flex-col items-center justify-center h-full py-12">
      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-6 shadow-xl">
        <MessageCircle className="w-10 h-10 text-white" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{t('welcomeTitle')}</h2>
      <p className="text-gray-500 dark:text-gray-400 text-center max-w-md mb-6">
        {t('welcomeSubtitle')}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
        {suggestions.map((suggestion, i) => (
          <button
            key={i}
            onClick={() => onSuggestionClick(suggestion)}
            className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-all text-left"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
};

const MessageList = ({ messages, isLoading, onSuggestionClick, reasoningSteps = [], showReasoning = true }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, reasoningSteps]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {messages.length === 0 && !isLoading && <WelcomeMessage onSuggestionClick={onSuggestionClick} />}

      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}

      {isLoading && <LoadingIndicator reasoningSteps={reasoningSteps} showReasoning={showReasoning} />}

      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
