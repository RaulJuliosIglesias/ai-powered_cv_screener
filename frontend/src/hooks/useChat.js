import { useState, useCallback } from 'react';
import { sendMessage } from '../services/api';

export function useChat(mode = 'local') {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [lastMetrics, setLastMetrics] = useState(null);

  const send = useCallback(async (message) => {
    if (!message.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage(message, mode, conversationId);
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        sources: response.sources || [],
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConversationId(response.conversation_id);
      setLastMetrics(response.metrics);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message');
      // Remove the user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  }, [mode, conversationId, isLoading]);

  const addMessage = useCallback((message) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      ...message,
    }]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    setLastMetrics(null);
  }, []);

  const retry = useCallback(async () => {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    if (lastUserMessage) {
      setMessages(prev => prev.filter(m => m.id !== lastUserMessage.id));
      await send(lastUserMessage.content);
    }
  }, [messages, send]);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    lastMetrics,
    send,
    addMessage,
    clearMessages,
    retry,
  };
}
