import ReactMarkdown from 'react-markdown';
import SourceBadge from './SourceBadge';
import { User, Sparkles } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const Message = ({ message }) => {
  const { role, content, sources = [] } = message;
  const isUser = role === 'user';
  const { t } = useLanguage();

  return (
    <div className={`message-fade-in ${isUser ? 'flex justify-end' : ''}`}>
      <div className={`flex gap-3 max-w-3xl ${isUser ? 'flex-row-reverse' : ''}`}>
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
            isUser 
              ? 'bg-blue-500' 
              : 'bg-gradient-to-br from-blue-500 to-purple-600'
          }`}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Sparkles className="w-5 h-5 text-white" />
          )}
        </div>

        <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
            {isUser ? t('you') : t('assistant')}
          </span>

          <div
            className={`mt-1 p-4 rounded-2xl ${
              isUser
                ? 'bg-blue-500 text-white rounded-tr-sm'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm'
            }`}
          >
            <div className={`prose prose-sm max-w-none dark:prose-invert ${isUser ? 'prose-invert' : ''}`}>
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>

            {!isUser && sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1">
                  📎 {t('sources')}:
                </p>
                <div className="flex flex-wrap gap-2">
                  {sources.map((source, index) => (
                    <SourceBadge
                      key={index}
                      filename={source.filename}
                      score={source.relevance || source.relevance_score}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Message;
