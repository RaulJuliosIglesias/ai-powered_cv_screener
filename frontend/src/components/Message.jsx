import ReactMarkdown from 'react-markdown';
import SourceBadge from './SourceBadge';
import { User, Bot } from 'lucide-react';

const Message = ({ message }) => {
  const { role, content, sources = [] } = message;
  const isUser = role === 'user';

  return (
    <div className={`message-fade-in ${isUser ? 'flex justify-end' : ''}`}>
      <div className={`flex gap-3 max-w-3xl ${isUser ? 'flex-row-reverse' : ''}`}>
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-primary-600' : 'bg-gray-200'
          }`}
        >
          {isUser ? (
            <User className="w-4 h-4 text-white" />
          ) : (
            <Bot className="w-4 h-4 text-gray-600" />
          )}
        </div>

        <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
          <span className="text-xs font-medium text-gray-500 uppercase">
            {isUser ? 'You' : 'Assistant'}
          </span>

          <div
            className={`mt-1 p-4 rounded-2xl ${
              isUser
                ? 'bg-primary-600 text-white rounded-tr-sm'
                : 'bg-white border border-gray-200 rounded-tl-sm'
            }`}
          >
            <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : ''}`}>
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>

            {!isUser && sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
                  📎 Sources:
                </p>
                <div className="flex flex-wrap gap-2">
                  {sources.map((source, index) => (
                    <SourceBadge
                      key={index}
                      filename={source.filename}
                      score={source.relevance_score}
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
