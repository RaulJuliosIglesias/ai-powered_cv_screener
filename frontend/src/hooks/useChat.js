import { useState, useCallback } from 'react';
import { sendMessage } from '../services/api';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  const addMessage = useCallback((role, content, sources = []) => {
    const message = {
      id: Date.now(),
      role,
      content,
      sources,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  const send = useCallback(async (content) => {
    if (!content.trim()) return;

    setError(null);
    addMessage('user', content);
    setIsLoading(true);

    try {
      const response = await sendMessage(content, conversationId);
      
      setConversationId(response.conversation_id);
      addMessage('assistant', response.response, response.sources);
      
      return response;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to send message';
      setError(errorMessage);
      addMessage('assistant', `Error: ${errorMessage}`, []);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, addMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  const retryLast = useCallback(async () => {
    const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMessage) {
      setMessages((prev) => prev.slice(0, -1));
      await send(lastUserMessage.content);
    }
  }, [messages, send]);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    send,
    clearMessages,
    retryLast,
    addMessage,
  };
};
