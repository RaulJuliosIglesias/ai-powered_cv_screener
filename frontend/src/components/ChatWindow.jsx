import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ChatWindow = ({ messages, isLoading, onSend, welcomeMessage }) => {
  return (
    <div className="flex-1 flex flex-col bg-gray-50 overflow-hidden">
      <MessageList
        messages={messages}
        isLoading={isLoading}
        welcomeMessage={welcomeMessage}
      />
      <ChatInput onSend={onSend} isLoading={isLoading} />
    </div>
  );
};

export default ChatWindow;
