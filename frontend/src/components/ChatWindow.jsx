import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ChatWindow = ({ messages, isLoading, onSend, reasoningSteps = [], showReasoning = true }) => {
  const handleSuggestionClick = (suggestion) => {
    if (!isLoading) {
      onSend(suggestion);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900 overflow-hidden">
      <MessageList
        messages={messages}
        isLoading={isLoading}
        onSuggestionClick={handleSuggestionClick}
        reasoningSteps={reasoningSteps}
        showReasoning={showReasoning}
      />
      <ChatInput onSend={onSend} isLoading={isLoading} />
    </div>
  );
};

export default ChatWindow;
