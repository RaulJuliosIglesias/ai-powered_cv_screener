import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ChatWindow = ({ messages, isLoading, onSend }) => {
  return (
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900 overflow-hidden">
      <MessageList
        messages={messages}
        isLoading={isLoading}
      />
      <ChatInput onSend={onSend} isLoading={isLoading} />
    </div>
  );
};

export default ChatWindow;
